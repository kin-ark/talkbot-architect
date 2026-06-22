from __future__ import annotations

import json

from llm.base import LLMClient, LLMResponse, Message, ToolCall, ToolSpec


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        api_tools = [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        resp = self._client.chat.completions.create(
            model=self._model, messages=self._to_openai_messages(messages),
            tools=api_tools or None)
        msg = resp.choices[0].message
        calls = [ToolCall(id=tc.id, name=tc.function.name,
                          arguments=json.loads(tc.function.arguments or "{}"))
                 for tc in (msg.tool_calls or [])]
        return LLMResponse(text=msg.content, tool_calls=calls)

    @staticmethod
    def _to_openai_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content or ""})
            elif m.role == "assistant" and m.tool_calls:
                out.append({"role": "assistant", "content": m.content,
                            "tool_calls": [{"id": c.id, "type": "function",
                                            "function": {"name": c.name,
                                                         "arguments": json.dumps(c.arguments)}}
                                           for c in m.tool_calls]})
            else:
                out.append({"role": m.role, "content": m.content or ""})
        return out
