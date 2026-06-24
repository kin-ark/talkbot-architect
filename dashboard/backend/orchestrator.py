"""The chat loop: call the model, execute tool calls, feed results back."""
from __future__ import annotations

import json

from llm.base import LLMClient, Message
from session import Session
from tools import registry

_SYSTEM = (
    "You are a WIZ.AI talkbot dialogue assistant. You help the user understand, "
    "validate, create, and edit a dialogue export. You never see the raw JSON; use "
    "the tools.\n\n"
    "Tools:\n"
    "- validate / summarize / read_node: inspect the current dialogue.\n"
    "- get_facts: WIZ.AI product facts. get_schema: the manifest schema, node "
    "labels, and op names — call it before authoring scaffold_bot params or ops.\n"
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
    "talkbot'): FIRST reply with a short dialogue OUTLINE (components, key nodes, "
    "intents, language) and ask the user to CONFIRM or tweak. Only AFTER they "
    "confirm, call scaffold_bot. For a targeted edit, act directly (still a "
    "proposal the user applies)."
)

_MAX_TOOL_ITERS = 8


def run_turn(client: LLMClient, session: Session, user_message: str) -> dict:
    mark = len(session.transcript)                      # pre-turn snapshot
    session.transcript.append(Message(role="user", content=user_message))
    messages = [Message(role="system", content=_SYSTEM), *session.transcript]
    tool_trace: list[dict] = []
    proposal: dict | None = None

    def _rollback_canceled():
        del session.transcript[mark:]                   # discard partial turn
        session.cancel_requested = False
        return {"text": "(canceled)", "tool_trace": tool_trace,
                "proposal": None, "canceled": True}

    for _ in range(_MAX_TOOL_ITERS):
        if session.cancel_requested:
            return _rollback_canceled()
        resp = client.chat(messages, registry.tool_specs())
        assistant = Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls)
        messages.append(assistant)
        session.transcript.append(assistant)
        if not resp.tool_calls:
            session.cancel_requested = False
            return {"text": resp.text or "", "tool_trace": tool_trace,
                    "proposal": proposal, "canceled": False}
        seen_call_ids: set[str] = set()
        for call in resp.tool_calls:
            if call.id in seen_call_ids:
                continue  # a model may echo a tool_use id twice; one result per id
            seen_call_ids.add(call.id)
            out = registry.dispatch(call.name, call.arguments, session.current())
            tool_trace.append({"name": call.name, "arguments": call.arguments,
                               "result": out["result"]})
            if out["proposal"] is not None:
                proposal = out["proposal"]
                session.pending = proposal
            tool_msg = Message(role="tool", tool_call_id=call.id,
                               content=json.dumps(out["result"], ensure_ascii=False, default=str))
            messages.append(tool_msg)
            session.transcript.append(tool_msg)
    session.cancel_requested = False
    return {"text": "(stopped after tool-iteration limit)", "tool_trace": tool_trace,
            "proposal": proposal, "canceled": False}
