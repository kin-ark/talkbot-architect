"""The chat loop: call the model, execute tool calls, feed results back."""
from __future__ import annotations

import json
from collections.abc import Iterator

from llm.base import LLMClient, LLMResponse, Message
from session import Session
from tools import registry

_ATTACH_TOOLS = ("import_intents_xlsx", "import_kb_xlsx")


def _attachment_note(att: dict) -> str:
    kind = att["kind"]
    name = att["name"]
    if kind == "intent-xlsx":
        return (f"The user attached an intent Excel named {name!r}. To import its intents "
                f"into the current bot, call the import_intents_xlsx tool (it uses the "
                f"attached file automatically). It is a proposal the user then applies.")
    if kind == "kb-xlsx":
        return (f"The user attached a KB Excel named {name!r}. To import its knowledge bases, "
                f"call the import_kb_xlsx tool (it uses the attached file automatically). "
                f"Proposal only.")
    return (f"The user attached a file named {name!r}. Its contents:\n```\n"
            f"{att.get('excerpt') or ''}\n```\nUse this to answer the user.")


_SYSTEM = (
    "You are a WIZ.AI talkbot dialogue assistant. You help the user understand, "
    "validate, create, and edit a dialogue export. You never see the raw JSON; use "
    "the tools.\n\n"
    "Tools:\n"
    "- validate / summarize / read_node: inspect the current dialogue.\n"
    "- get_facts: WIZ.AI product facts. get_schema: the manifest schema, node "
    "labels, and op names. get_playbook: corpus-derived blueprints for known bot "
    "verticals (e.g., debt_collection).\n"
    "- scaffold_bot: create a BRAND-NEW dialogue from typed parameters (name, "
    "language, branch, canvases of nodes+edges). Prefer this over raw `build`.\n"
    "- add_component / add_node / add_intent / add_variable: edit an EXISTING bot "
    "(typed params; dry-run proposals). Nodes accept type: talk|exit|transfer|goto; "
    "goto requires config.target = another component name.\n"
    "- connect_components: shorthand to wire a goto node from one component to another "
    "(cross-component jump; dry-run proposal).\n"
    "- apply_mods / set_path / delete_path / build: lower-level escape hatches "
    "(raw YAML); use only when no typed tool fits.\n\n"
    "All editing tools only PROPOSE changes (a diff + checker delta) — the user must "
    "apply them. Always validate after a structural change.\n\n"
    "When the user asks for a whole new bot (e.g. 'make me a Debt Collector "
    "talkbot'): FIRST check whether it targets a known vertical — call "
    "get_playbook(<vertical>) (e.g. 'debt_collection'). Use its `playbook` if a domain matches, "
    "and ALWAYS follow its `general` guidance (the maturity bar). If a blueprint is "
    "returned, base your OUTLINE and the eventual scaffold/build on it: use its "
    "funnel skeleton, the stage tuning matching the user's ask, its intents/KBs, "
    "and its script archetypes (keep the /-rotation variants and {placeholders}). "
    "Then reply with a short dialogue OUTLINE (components, key nodes, intents, "
    "language) and ask the user to CONFIRM or tweak. Only AFTER they confirm, call "
    "scaffold_bot (or build for the full manifest). If no blueprint exists, proceed "
    "generically (but still follow the general playbook maturity bar). For a targeted edit, act directly (still a proposal the user applies)."
    "\n\nWhen you mention a specific node in your reply, render it as a markdown "
    "link of the form [label](#node:<uuid>) using the node's uuid (from summarize "
    "or read_node) — the dashboard turns these into clickable links that open the "
    "node. Only link nodes that exist in the current dialogue."
    "\n\nWIZ best-practice — author conformant flows (from the general playbook):\n"
    "- Every flow path must END in an Exit (hangup) or Transfer node. Each component needs its own Exit.\n"
    "- Every Talk node needs a connected \"Unclassified\" answer branch (the catch-all) plus its answer branches.\n"
    "- Declare intents (add_intent) BEFORE a KB that triggers on them; assign a variable (assign node) "
    "BEFORE a conditional reads it.\n"
    "- IDN language only. Use only supported node types (talk, exit, transfer, goto, goto_kb, goto_mr, "
    "talk_continue, conditional, assign, nested, exit_port).\n"
    "- Call get_schema (and get_facts when unsure) BEFORE authoring scaffold_bot params or ops.\n\n"
    "Fix loop — never present a broken proposal:\n"
    "- Every edit/build/scaffold result has a checker_delta and, when problems exist, a `findings` list "
    "(code, severity, id, message).\n"
    "- If a proposal's result has any severity:\"error\" findings, FIX them — call the right tool to revise "
    "(e.g. complete_component to add an Exit + wire branches, connect_components/rewire_edge to fix routes) "
    "and re-propose — before finishing your turn. Never end with an error-carrying proposal.\n"
    "- severity:\"warning\" findings (missing Unclassified branch, no component Exit) are best-practice "
    "nudges: address when sensible; they don't block."
)

_MAX_TOOL_ITERS = 8
_MAX_FIX_BACKSTOPS = 2


def _summarize_tool_result(name: str, result) -> str:
    if isinstance(result, dict):
        if result.get("proposal") is not None or "diff" in result:
            return "proposal ready"
        if name == "validate" and isinstance(result.get("findings"), list):
            return f"{len(result['findings'])} findings"
        if "error" in result:
            return "error"
    if isinstance(result, list):
        return f"{len(result)} items"
    return "done"


def run_turn_stream(client, session, user_message: str) -> Iterator[dict]:
    mark = len(session.transcript)
    session.transcript.append(Message(role="user", content=user_message))
    messages = [Message(role="system", content=_SYSTEM), *session.transcript]
    if session.attachment:
        messages.append(Message(role="user", content=_attachment_note(session.attachment)))
    proposal: dict | None = None
    text_acc = ""
    turn_usage: dict = {"input_tokens": 0, "output_tokens": 0}
    fix_rounds = 0
    coverage_nudged = False

    def _rollback():
        del session.transcript[mark:]
        session.cancel_requested = False

    for _ in range(_MAX_TOOL_ITERS):
        if session.cancel_requested:
            _rollback()
            if session.attachment:
                from pathlib import Path as _P
                _P(session.attachment.get("path", "")).unlink(missing_ok=True) if session.attachment.get("path") else None
                session.attachment = None
            yield {"type": "done", "canceled": True, "text": ""}
            return

        resp = None
        turn_text = ""
        for chunk in client.stream_chat(messages, registry.tool_specs()):
            if session.cancel_requested:
                _rollback()
                if session.attachment:
                    from pathlib import Path as _P
                    _P(session.attachment.get("path", "")).unlink(missing_ok=True) if session.attachment.get("path") else None
                    session.attachment = None
                yield {"type": "done", "canceled": True, "text": ""}
                return
            if chunk.thinking_delta:
                yield {"type": "thinking", "delta": chunk.thinking_delta}
            if chunk.text_delta:
                turn_text += chunk.text_delta
                yield {"type": "token", "delta": chunk.text_delta}
            if chunk.response is not None:
                resp = chunk.response
            if chunk.usage:
                turn_usage["input_tokens"] += chunk.usage.get("input_tokens", 0)
                turn_usage["output_tokens"] += chunk.usage.get("output_tokens", 0)
        if resp is None:                       # defensive: empty stream
            resp = LLMResponse(text=turn_text or None, tool_calls=[])

        assistant = Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls,
                            thinking_blocks=getattr(resp, "thinking_blocks", []))
        messages.append(assistant)
        session.transcript.append(assistant)
        if resp.text:
            text_acc = resp.text

        if not resp.tool_calls:
            # Soft enrichment nudge: one-shot coverage advisory (BEFORE hard backstops)
            # Only nudge if model produced no text (hasn't already finished the turn)
            if not coverage_nudged and not resp.text and proposal and "feature_coverage" in proposal:
                missing = proposal.get("feature_coverage", {}).get("missing", [])
                if missing:
                    coverage_nudged = True
                    nudge_msg = (
                        "This bot doesn't use: " + ", ".join(missing) + ". "
                        "If any of these fit the domain, add them (e.g. disposition tags for call "
                        "outcomes, a KB for FAQs/objections, hot-words for domain terms, "
                        "conditional/assign for routing). Only add what genuinely fits — do NOT "
                        "force features. Then finish."
                    )
                    messages.append(Message(role="user", content=nudge_msg))
                    yield {"type": "autofix", "count": 0, "round": 0}
                    continue
            errs = [f for f in (proposal or {}).get("findings", []) if f.get("severity") == "error"]
            maturity_blockers = (proposal or {}).get("maturity", {}).get("residual_blockers", [])
            # Avoid double-counting: extract blocker codes from errs to exclude from count
            err_codes = {e.get("code") for e in errs}
            unique_blockers = [b for b in maturity_blockers if b.get("code") not in err_codes]
            if (errs or maturity_blockers) and fix_rounds < _MAX_FIX_BACKSTOPS:
                fix_rounds += 1
                messages_to_add = []
                if errs:
                    msg = (f"The current proposal still has {len(errs)} "
                           f"error{'s' if len(errs) != 1 else ''} and cannot be applied as-is:\n"
                           + "\n".join(f"- {e['code']} ({e.get('id') or '-'}): {e['message']}" for e in errs[:10])
                           + "\nFix these (call the right tool to revise) and re-propose before finishing.")
                    messages_to_add.append(msg)
                if unique_blockers:
                    msg = (f"{len(unique_blockers)} maturity gap{'s' if len(unique_blockers) != 1 else ''} remain:\n"
                           + "\n".join(f"- {b['code']} ({b.get('id') or '-'}): {b['message']}" for b in unique_blockers[:10])
                           + "\nFix these and re-propose.")
                    messages_to_add.append(msg)
                note = "\n\n".join(messages_to_add)
                messages.append(Message(role="user", content=note))   # messages-only, NOT session.transcript
                yield {"type": "autofix", "count": len(errs) + len(unique_blockers), "round": fix_rounds}
                continue
            session.cancel_requested = False
            session.usage["input_tokens"] += turn_usage["input_tokens"]
            session.usage["output_tokens"] += turn_usage["output_tokens"]
            session.usage["turns"] += 1
            session.usage["model"] = getattr(client, "model", session.usage.get("model"))
            if session.attachment:
                from pathlib import Path as _P
                _P(session.attachment.get("path", "")).unlink(missing_ok=True) if session.attachment.get("path") else None
                session.attachment = None
            yield {"type": "usage", **session.usage}
            yield {"type": "done", "canceled": False, "text": text_acc}
            return

        seen_call_ids: set[str] = set()
        for call in resp.tool_calls:
            if call.id in seen_call_ids:
                continue
            seen_call_ids.add(call.id)
            yield {"type": "tool_start", "name": call.name, "args": call.arguments}
            call_args = dict(call.arguments)
            if call.name in _ATTACH_TOOLS and session.attachment:
                call_args["path"] = session.attachment["path"]
            out = registry.dispatch(call.name, call_args, session.current())
            yield {"type": "tool_result", "name": call.name, "result": out["result"],
                   "summary": _summarize_tool_result(call.name, out["result"])}
            if out["proposal"] is not None:
                proposal = out["proposal"]
                session.pending = proposal
                yield {"type": "proposal", "proposal": proposal}
            tool_msg = Message(role="tool", tool_call_id=call.id,
                               content=json.dumps(out["result"], ensure_ascii=False, default=str))
            messages.append(tool_msg)
            session.transcript.append(tool_msg)

    session.cancel_requested = False
    session.usage["input_tokens"] += turn_usage["input_tokens"]
    session.usage["output_tokens"] += turn_usage["output_tokens"]
    session.usage["turns"] += 1
    session.usage["model"] = getattr(client, "model", session.usage.get("model"))
    if session.attachment:
        from pathlib import Path as _P
        _P(session.attachment.get("path", "")).unlink(missing_ok=True) if session.attachment.get("path") else None
        session.attachment = None
    yield {"type": "usage", **session.usage}
    yield {"type": "done", "canceled": False, "text": text_acc or "(stopped after tool-iteration limit)"}


def run_turn(client: LLMClient, session: Session, user_message: str) -> dict:
    """Blocking drainer over run_turn_stream — same return shape as before."""
    text = ""
    tool_trace: list[dict] = []
    proposal: dict | None = None
    canceled = False
    usage: dict = {}
    for ev in run_turn_stream(client, session, user_message):
        t = ev["type"]
        if t == "token":
            pass  # text comes from the final done event
        elif t == "tool_start":
            tool_trace.append({"name": ev["name"], "arguments": ev["args"], "result": None})
        elif t == "tool_result":
            if tool_trace and tool_trace[-1]["result"] is None:
                tool_trace[-1]["result"] = ev["result"]
            else:
                tool_trace.append({"name": ev["name"], "arguments": {}, "result": ev["result"]})
        elif t == "proposal":
            proposal = ev["proposal"]
        elif t == "usage":
            usage = {k: ev[k] for k in ("input_tokens", "output_tokens", "turns", "model")}
        elif t == "done":
            text = ev["text"]
            canceled = ev["canceled"]
    return {"text": text, "tool_trace": tool_trace, "proposal": proposal, "canceled": canceled,
            "usage": usage}
