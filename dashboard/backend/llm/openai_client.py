from __future__ import annotations

import json
from collections.abc import Iterator

from llm.base import LLMClient, LLMResponse, Message, StreamChunk, ToolCall, ToolSpec


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self.model = model

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

    def stream_chat(self, messages: list[Message], tools: list[ToolSpec]) -> Iterator[StreamChunk]:
        api_tools = [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        stream = self._client.chat.completions.create(
            model=self._model, messages=self._to_openai_messages(messages),
            tools=api_tools or None, stream=True, stream_options={"include_usage": True})
        text = ""
        acc: dict[int, dict] = {}     # index -> {id, name, args}
        usage_obj = None
        for chunk in stream:
            usage_obj = getattr(chunk, "usage", None) or usage_obj
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None):
                text += delta.content
                yield StreamChunk(text_delta=delta.content)
            for tc in (getattr(delta, "tool_calls", None) or []):
                slot = acc.setdefault(tc.index, {"id": None, "name": None, "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments
        calls = [ToolCall(id=s["id"], name=s["name"], arguments=json.loads(s["args"] or "{}"))
                 for s in (acc[k] for k in sorted(acc)) if s["name"]]
        usage = {"input_tokens": getattr(usage_obj, "prompt_tokens", 0),
                 "output_tokens": getattr(usage_obj, "completion_tokens", 0)} if usage_obj else None
        yield StreamChunk(response=LLMResponse(text=text or None, tool_calls=calls), usage=usage)

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
