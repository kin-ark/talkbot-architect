"""The chat loop: call the model, execute tool calls, feed results back."""
from __future__ import annotations

import json

from llm.base import LLMClient, Message
from session import Session
from tools import registry

_SYSTEM = (
    "You are a WIZ.AI talkbot dialogue assistant. You help the user understand, "
    "validate, and edit a dialogue export. You never see the raw JSON; use the "
    "tools. Editing tools only PROPOSE changes (a diff + checker delta) — the user "
    "must apply them. Prefer apply_mods registry ops; use set_path/delete_path only "
    "when no op fits. Always validate after proposing a structural change."
)

_MAX_TOOL_ITERS = 8


def run_turn(client: LLMClient, session: Session, user_message: str) -> dict:
    session.transcript.append(Message(role="user", content=user_message))
    messages = [Message(role="system", content=_SYSTEM), *session.transcript]
    tool_trace: list[dict] = []
    proposal: dict | None = None

    for _ in range(_MAX_TOOL_ITERS):
        resp = client.chat(messages, registry.tool_specs())
        assistant = Message(role="assistant", content=resp.text, tool_calls=resp.tool_calls)
        messages.append(assistant)
        session.transcript.append(assistant)
        if not resp.tool_calls:
            return {"text": resp.text or "", "tool_trace": tool_trace, "proposal": proposal}
        for call in resp.tool_calls:
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
    return {"text": "(stopped after tool-iteration limit)", "tool_trace": tool_trace,
            "proposal": proposal}
