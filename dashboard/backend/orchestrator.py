"""The chat loop: call the model, execute tool calls, feed results back."""
from __future__ import annotations

import json
import os
import time
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
    "- validate / summarize / read_node: inspect the current dialogue. list_intents / "
    "list_variables: check what already exists BEFORE declaring (declare-before-use).\n"
    "- get_facts: WIZ.AI product facts. get_schema: the manifest schema, node "
    "labels, and op names. get_playbook: corpus-derived blueprints for known bot "
    "verticals (e.g., debt_collection).\n"
    "- list_samples / get_sample: real, deployed-faithful starter manifests (get_sample "
    "returns full manifest YAML). get_debt_corpus: prevalence-ranked debt intents/KBs/"
    "scripts/engines/stage-tuning/objections/tags.\n"
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
    "SEED-FIRST: if a sample matches the vertical/stage (use list_samples to pick the "
    "closest — its description names the DPD stage), call get_sample and ADAPT that "
    "manifest (brand, amounts, stage tone) then call `build`, RATHER THAN composing "
    "scaffold_bot from scratch. Use get_debt_corpus to confirm the top intents/KBs/tags "
    "and pull stage tuning. If no sample matches, fall back to scaffold_bot from the playbook. "
    "Then reply with a short dialogue OUTLINE (components, key nodes, intents, "
    "language) and ask the user to CONFIRM or tweak. Only AFTER they confirm, call "
    "scaffold_bot (or build for the full manifest). If no blueprint exists, proceed "
    "generically (but still follow the general playbook maturity bar). For a targeted edit, act directly (still a proposal the user applies)."
    "\n\nWhen you mention a specific node in your reply, render it as a markdown "
    "link of the form [label](#node:<uuid>) using the node's uuid (from summarize "
    "or read_node) — the dashboard turns these into clickable links that open the "
    "node. Only link nodes that exist in the current dialogue."
    "\n\nWIZ authoring rules — MUST (breaking one makes the build or deploy FAIL):\n"
    "- DECLARE BEFORE USE: define a component/canvas, KB, variable, or intent BEFORE anything references it "
    "— a goto/goto_kb/goto_mr/nested target, a KB's triggering intent, a conditional's variable, and a talk "
    "custom branch must all already exist.\n"
    "- TALK BRANCHES: the five system branches (Positive, Negative, Reject, Unclassified, No answer) are "
    "BUILT-IN — wire edges directly to them and NEVER put a system name inside config.branch_intents. Use "
    "branch_intents ONLY for NON-system intent routes (e.g. ServiceIssue) on the SOURCE talk node: "
    "config.branch_intents = {Label: [customIntentName, ...]}. Then ALL must hold: (a) each Label differs from "
    "the five system names; (b) every intent named is ALSO declared in custom_intents; (c) that node ALSO has a "
    "connected Unclassified edge; (d) an edge's branch is a system name OR a branch_intents label declared on "
    "its source node. If you don't need intent routing, use ONLY the five system branches.\n"
    "- Every talk node has a connected Unclassified branch (catch-all). Every component ends every path in an "
    "Exit (hangup) or Transfer, and has its OWN Exit.\n"
    "- A conditional may branch on a variable ONLY if it is system-collected OR set by an assign node EARLIER "
    "in the flow; branching on a never-assigned variable deploys broken.\n"
    "- IDN or ENG language only. Use ONLY these node types: talk, exit, transfer, goto, goto_kb, goto_mr, "
    "talk_continue, conditional, assign, nested, exit_port. Do not invent node types or branch names.\n"
    "\nWIZ authoring — SHOULD (quality; the maturity bar from the general playbook):\n"
    "- Structure the bot as MANY SMALL components (target <=~8 nodes each), one per funnel stage, wired with "
    "goto; real production bots average ~12 components (0 of 33 use a single component). Extract reusable "
    "subflows (a closing, an ID check, a persuasion loop) into nested components.\n"
    "- Use multi-round components for real back-and-forth (negotiation, clarification); put recurring "
    "questions/objections in intent-triggered KBs, NOT deep branch chains. Record call outcomes as "
    "disposition tags.\n"
    "\nAlways call get_schema (and get_facts when unsure) BEFORE authoring scaffold_bot params or ops. After "
    "any structural change: validate; if the result has error findings OR a build/scaffold is REJECTED, FIX "
    "and retry before finishing — never hand over a broken or failed build.\n"
    "\nMinimal valid scaffold_bot (system branches only) — follow this shape:\n"
    "  name: Support Bot | language: IDN | branch: dev\n"
    "  canvases: [{name: Main, nodes: [\n"
    "    {id: greet, type: talk, prompt: \"Hello, how can I help?\"},\n"
    "    {id: bye, type: exit, prompt: \"Thank you, goodbye.\"}],\n"
    "   edges: [{from: greet, branch: Positive, to: bye},\n"
    "           {from: greet, branch: Unclassified, to: bye}]}]\n\n"
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
# Wall-clock ceiling for one turn. 8 iters x a 120s per-call timeout could run
# ~16 min holding the session lock; cap it so a stuck turn can't block the
# session indefinitely. Env-overridable.
_TURN_DEADLINE_S = int(os.getenv("TURN_DEADLINE_S", "300"))


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
    from pathlib import Path as _P

    mark = len(session.transcript)
    # Transcript keeps a CLEAN text-only user turn — images are one-turn and
    # must NOT be persisted to disk, replayed on reload, or re-sent on later
    # turns (spec: per-session in-memory, cleared after the turn).
    session.transcript.append(Message(role="user", content=user_message))
    messages = [Message(role="system", content=_SYSTEM), *session.transcript]
    if session.images:
        # Attach images to THIS send's user message only (a copy, not the
        # persisted transcript object) so the model sees them this turn.
        messages[-1] = Message(role="user", content=user_message,
                               images=list(session.images))
    if session.attachment:
        messages.append(Message(role="user", content=_attachment_note(session.attachment)))
    proposal: dict | None = None
    text_acc = ""
    turn_usage: dict = {"input_tokens": 0, "output_tokens": 0}
    fix_rounds = 0
    coverage_nudged = False
    last_tool_error: str | None = None

    def _rollback():
        del session.transcript[mark:]
        session.cancel_requested = False

    def _clear_attachment():
        if session.attachment:
            _P(session.attachment.get("path", "")).unlink(missing_ok=True) if session.attachment.get("path") else None
            session.attachment = None
        session.images = []

    try:
        yield {"type": "phase", "phase": "planning"}
        tools_phase_announced = False
        t_start = time.monotonic()
        for _ in range(_MAX_TOOL_ITERS):
            if session.cancel_requested:
                _rollback()
                yield {"type": "done", "canceled": True, "text": "", "stop_reason": "canceled"}
                return
            if time.monotonic() - t_start > _TURN_DEADLINE_S:
                # Stuck/too-long turn: stop cleanly, keep any proposal already made.
                session.cancel_requested = False
                session.usage["input_tokens"] += turn_usage["input_tokens"]
                session.usage["output_tokens"] += turn_usage["output_tokens"]
                session.usage["turns"] += 1
                session.usage["model"] = getattr(client, "model", session.usage.get("model"))
                yield {"type": "usage", **session.usage}
                yield {"type": "done", "canceled": False,
                       "text": text_acc or "(stopped: turn exceeded the time limit)",
                       "stop_reason": "timeout"}
                return

            resp = None
            turn_text = ""
            try:
                chunk_iter = client.stream_chat(messages, registry.tool_specs())
                for chunk in chunk_iter:
                    if session.cancel_requested:
                        _rollback()
                        yield {"type": "done", "canceled": True, "text": "", "stop_reason": "canceled"}
                        return
                    if chunk.status:
                        yield {"type": "status", **chunk.status}
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
            except Exception as e:  # LLM stream failure (retries already exhausted)
                _rollback()
                yield {"type": "error", "kind": "transient",
                       "recovery": ["retry"], "message": str(e)}
                yield {"type": "done", "canceled": False, "text": "", "stop_reason": "complete"}
                return

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
                        yield {"type": "phase", "phase": "finalizing"}
                        continue
                errs = [f for f in (proposal or {}).get("findings", []) if f.get("severity") == "error"]
                maturity_blockers = (proposal or {}).get("maturity", {}).get("residual_blockers", [])
                # Avoid double-counting: extract blocker codes from errs to exclude from count
                err_codes = {e.get("code") for e in errs}
                unique_blockers = [b for b in maturity_blockers if b.get("code") not in err_codes]
                tool_rejected = proposal is None and bool(last_tool_error)
                if (errs or maturity_blockers or tool_rejected) and fix_rounds < _MAX_FIX_BACKSTOPS:
                    fix_rounds += 1
                    messages_to_add = []
                    if tool_rejected:
                        messages_to_add.append(
                            "The last tool call was REJECTED and produced no proposal:\n"
                            f"- {last_tool_error}\n"
                            "Diagnose the error and correct the arguments, then call the tool again. "
                            "Common fixes: declare a custom branch's config.branch_intents + its backing "
                            "custom_intent + a connected Unclassified edge; remove a system-name label from "
                            "branch_intents; define a goto/KB/variable/intent target before referencing it. "
                            "Do not give up.")
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
                    yield {"type": "phase", "phase": "fixing",
                           "round": fix_rounds, "errors": len(errs) or (1 if tool_rejected else 0),
                           "blockers": len(unique_blockers)}
                    continue
                if errs:
                    yield {"type": "error", "kind": "proposal_blocked",
                           "recovery": ["fix", "discard"],
                           "message": (f"The proposal still has {len(errs)} error"
                                       f"{'s' if len(errs) != 1 else ''} and cannot be applied as-is.")}
                elif proposal is None and last_tool_error:
                    yield {"type": "error", "kind": "tool_arg",
                           "recovery": ["edit", "retry"],
                           "message": last_tool_error}
                session.cancel_requested = False
                session.usage["input_tokens"] += turn_usage["input_tokens"]
                session.usage["output_tokens"] += turn_usage["output_tokens"]
                session.usage["turns"] += 1
                session.usage["model"] = getattr(client, "model", session.usage.get("model"))
                yield {"type": "usage", **session.usage}
                yield {"type": "done", "canceled": False, "text": text_acc, "stop_reason": "complete"}
                return

            if not tools_phase_announced:
                tools_phase_announced = True
                yield {"type": "phase", "phase": "tools"}
            seen_call_ids: set[str] = set()
            for call in resp.tool_calls:
                if call.id in seen_call_ids:
                    continue
                seen_call_ids.add(call.id)
                yield {"type": "tool_start", "name": call.name, "args": call.arguments,
                       "call_id": call.id, "ts": time.monotonic()}
                call_args = dict(call.arguments)
                if call.name in _ATTACH_TOOLS:
                    call_args["path"] = session.attachment["path"] if session.attachment else None
                try:
                    out = registry.dispatch(call.name, call_args, session.current())
                except Exception as e:  # noqa: BLE001 - a tool crash must not kill the turn
                    out = {"result": {"ok": False, "error": f"{type(e).__name__}: {e}"},
                           "proposal": None}
                res = out["result"]
                if isinstance(res, dict) and res.get("error"):
                    last_tool_error = str(res["error"])
                elif out.get("proposal") is not None:
                    last_tool_error = None
                yield {"type": "tool_result", "name": call.name, "result": out["result"],
                       "summary": _summarize_tool_result(call.name, out["result"]),
                       "call_id": call.id, "ts": time.monotonic()}
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
        yield {"type": "usage", **session.usage}
        yield {"type": "done", "canceled": False,
               "text": text_acc or "(stopped after tool-iteration limit)",
               "stop_reason": "limit"}
    finally:
        _clear_attachment()


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
        elif t == "error" and ev.get("kind") == "transient":
            # Pre-Task-3 behavior: an unhandled LLM/provider failure propagates
            # so callers (e.g. /chat) can surface it as a 502. Other error kinds
            # (proposal_blocked, tool_arg) are non-exceptional turn outcomes.
            raise RuntimeError(ev["message"])
        elif t == "done":
            text = ev["text"]
            canceled = ev["canceled"]
    return {"text": text, "tool_trace": tool_trace, "proposal": proposal, "canceled": canceled,
            "usage": usage}
