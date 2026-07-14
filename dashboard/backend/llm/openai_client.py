from __future__ import annotations

import json
import time as _time
from collections.abc import Iterator

from llm.base import LLMClient, LLMResponse, Message, StreamChunk, ToolCall, ToolSpec

_CALL_TIMEOUT = 120.0


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None,
                 attempts: int = 3, sleep=None):
        from openai import OpenAI
        # max_retries=0: with_retry is the single retry authority (SDK default 2
        # would compound under our loop).
        kwargs: dict = {"api_key": api_key, "max_retries": 0, "timeout": _CALL_TIMEOUT}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model
        self.model = model
        self._attempts = attempts
        self._sleep = sleep or _time.sleep

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        import openai
        if isinstance(exc, openai.RateLimitError):
            return True
        if isinstance(exc, openai.APIConnectionError):
            return True
        if isinstance(exc, openai.APIStatusError):
            return getattr(exc, "status_code", 0) >= 500
        return False

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        from llm import retry
        api_tools = [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        resp = retry.with_retry(
            lambda: self._client.chat.completions.create(
                model=self._model, messages=self._to_openai_messages(messages),
                tools=api_tools or None),
            attempts=self._attempts, is_retryable=self._is_retryable,
            sleep=self._sleep, retry_after=retry.retry_after_seconds)
        msg = resp.choices[0].message
        calls = [ToolCall(id=tc.id, name=tc.function.name,
                          arguments=json.loads(tc.function.arguments or "{}"))
                 for tc in (msg.tool_calls or [])]
        return LLMResponse(text=msg.content, tool_calls=calls)

    def stream_chat(self, messages: list[Message], tools: list[ToolSpec]) -> Iterator[StreamChunk]:
        from llm import retry
        api_tools = [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters}} for t in tools]
        attempt = 0
        while True:
            emitted = False
            try:
                stream = self._client.chat.completions.create(
                    model=self._model, messages=self._to_openai_messages(messages),
                    tools=api_tools or None, stream=True, stream_options={"include_usage": True})
                text = ""
                acc: dict[int, dict] = {}
                usage_obj = None
                for chunk in stream:
                    usage_obj = getattr(chunk, "usage", None) or usage_obj
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if getattr(delta, "content", None):
                        emitted = True
                        text += delta.content
                        yield StreamChunk(text_delta=delta.content)
                    for tc in (getattr(delta, "tool_calls", None) or []):
                        emitted = True
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
                return
            except Exception as e:  # noqa: BLE001
                attempt += 1
                attempts = getattr(self, "_attempts", 1)
                if emitted or not self._is_retryable(e) or attempt >= attempts:
                    raise
                wait = retry.backoff_wait(attempt, 1.0, retry.retry_after_seconds(e))
                yield StreamChunk(status={"kind": "retrying", "attempt": attempt,
                                          "attempts": attempts, "wait": round(wait, 1)})
                self._sleep(wait)

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
            elif m.role == "user" and m.images:
                parts = [{"type": "image_url",
                          "image_url": {"url": f"data:{im['media_type']};base64,{im['data']}"}}
                         for im in m.images]
                if m.content:
                    parts.append({"type": "text", "text": m.content})
                out.append({"role": "user", "content": parts})
            else:
                out.append({"role": m.role, "content": m.content or ""})
        return out
