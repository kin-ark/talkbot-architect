from __future__ import annotations

import time
from collections.abc import Iterator

from llm import retry
from llm.base import LLMClient, LLMResponse, Message, StreamChunk, ToolCall, ToolSpec


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None,
                 thinking_budget: int | None = None, attempts: int = 3, sleep=time.sleep):
        import anthropic
        # max_retries=0: with_retry is the single retry authority. Without this
        # the SDK's own default (2) compounds under our loop → up to ~9 calls.
        kwargs: dict = {"api_key": api_key, "max_retries": 0}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self.model = model
        self._thinking_budget = thinking_budget or None
        self._attempts = attempts
        self._sleep = sleep

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        import anthropic
        if isinstance(exc, anthropic.RateLimitError):
            return True
        if isinstance(exc, anthropic.APIConnectionError):
            return True
        if isinstance(exc, anthropic.APIStatusError):
            return getattr(exc, "status_code", 0) >= 500
        return False

    def _max_tokens(self) -> int:
        return (self._thinking_budget + 4096) if self._thinking_budget else 4096

    def _thinking_arg(self) -> dict | None:
        if self._thinking_budget:
            return {"type": "enabled", "budget_tokens": self._thinking_budget}
        return None

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        sys_msgs = [m.content for m in messages if m.role == "system"]
        api_msgs = self._to_anthropic_messages([m for m in messages if m.role != "system"])
        api_tools = [{"name": t.name, "description": t.description,
                      "input_schema": t.parameters} for t in tools]

        def _call():
            return self._client.messages.create(
                model=self._model, max_tokens=4096,
                system="\n".join(sys_msgs) or None,
                messages=api_msgs, tools=api_tools or None,
            )

        attempts = getattr(self, "_attempts", 1)
        sleep_fn = getattr(self, "_sleep", lambda s: None)
        resp = retry.with_retry(_call, attempts=attempts, is_retryable=self._is_retryable,
                                sleep=sleep_fn, retry_after=retry.retry_after_seconds)
        text, calls = None, []
        for block in resp.content:
            if block.type == "text":
                text = (text or "") + block.text
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
        return LLMResponse(text=text, tool_calls=calls)

    def stream_chat(self, messages: list[Message], tools: list[ToolSpec]) -> Iterator[StreamChunk]:
        sys_msgs = [m.content for m in messages if m.role == "system"]
        api_msgs = self._to_anthropic_messages([m for m in messages if m.role != "system"])
        api_tools = [{"name": t.name, "description": t.description,
                      "input_schema": t.parameters} for t in tools]
        thinking = self._thinking_arg() if hasattr(self, "_thinking_budget") else None

        attempt = 0
        while True:
            emitted = False
            try:
                max_tokens = self._max_tokens() if hasattr(self, "_thinking_budget") else 4096
                create_kw: dict = dict(
                    model=self._model, max_tokens=max_tokens,
                    system="\n".join(sys_msgs) or None,
                    messages=api_msgs, tools=api_tools or None,
                )
                if thinking:
                    create_kw["thinking"] = thinking
                with self._client.messages.stream(**create_kw) as stream:
                    for event in stream:
                        etype = getattr(event, "type", None)
                        if etype == "content_block_delta":
                            dtype = getattr(event.delta, "type", None)
                            if dtype == "text_delta":
                                emitted = True
                                yield StreamChunk(text_delta=event.delta.text)
                            elif dtype == "thinking_delta":
                                emitted = True
                                yield StreamChunk(thinking_delta=event.delta.thinking)
                            # signature_delta / other: ignore
                    try:
                        final = stream.get_final_message()
                    except AssertionError as e:
                        raise RuntimeError(
                            "model returned no response (the endpoint may not "
                            f"support model {self._model!r}): {e}") from e
                text, calls, tblocks = None, [], []
                for block in final.content:
                    if block.type == "text":
                        text = (text or "") + block.text
                    elif block.type == "tool_use":
                        calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
                    elif block.type in ("thinking", "redacted_thinking"):
                        tblocks.append(_thinking_block_to_dict(block))
                u = getattr(final, "usage", None)
                usage = {"input_tokens": getattr(u, "input_tokens", 0),
                         "output_tokens": getattr(u, "output_tokens", 0)} if u else None
                yield StreamChunk(response=LLMResponse(text=text, tool_calls=calls, thinking_blocks=tblocks),
                                  usage=usage)
                return
            except Exception as e:  # noqa: BLE001
                attempt += 1
                attempts = getattr(self, "_attempts", 1)
                if emitted or not self._is_retryable(e) or attempt >= attempts:
                    raise
                sleep_fn = getattr(self, "_sleep", lambda s: None)
                sleep_fn(retry.backoff_wait(attempt, 1.0, retry.retry_after_seconds(e)))

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        i = 0
        n = len(messages)
        while i < n:
            m = messages[i]
            if m.role == "tool":
                results: list[dict] = []
                seen: set[str | None] = set()
                while i < n and messages[i].role == "tool":
                    tm = messages[i]
                    if tm.tool_call_id not in seen:
                        seen.add(tm.tool_call_id)
                        results.append({"type": "tool_result",
                                        "tool_use_id": tm.tool_call_id,
                                        "content": tm.content or ""})
                    i += 1
                out.append({"role": "user", "content": results})
                continue
            if m.role == "assistant" and m.tool_calls:
                seen_ids: set[str] = set()
                tool_use: list[dict] = []
                for c in m.tool_calls:
                    if c.id in seen_ids:
                        continue
                    seen_ids.add(c.id)
                    tool_use.append({"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments})
                # Extended-thinking + tools: the original thinking blocks MUST be
                # replayed (with signatures) or Anthropic 400s on the tool follow-up.
                # Order: thinking blocks, then text, then tool_use.
                content = (list(m.thinking_blocks)
                           + ([{"type": "text", "text": m.content}] if m.content else [])
                           + tool_use)
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": m.role, "content": m.content or ""})
            i += 1
        return out


def _thinking_block_to_dict(block) -> dict:
    """Normalize an SDK thinking/redacted_thinking block to a plain replayable dict."""
    if getattr(block, "type", None) == "redacted_thinking":
        return {"type": "redacted_thinking", "data": getattr(block, "data", "")}
    return {"type": "thinking",
            "thinking": getattr(block, "thinking", ""),
            "signature": getattr(block, "signature", "")}
