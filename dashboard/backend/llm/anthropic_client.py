from __future__ import annotations

from collections.abc import Iterator

from llm.base import LLMClient, LLMResponse, Message, StreamChunk, ToolCall, ToolSpec


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        import anthropic
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self.model = model

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        sys_msgs = [m.content for m in messages if m.role == "system"]
        api_msgs = self._to_anthropic_messages([m for m in messages if m.role != "system"])
        api_tools = [{"name": t.name, "description": t.description,
                      "input_schema": t.parameters} for t in tools]
        resp = self._client.messages.create(
            model=self._model, max_tokens=4096,
            system="\n".join(sys_msgs) or None,
            messages=api_msgs, tools=api_tools or None,
        )
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
        with self._client.messages.stream(
            model=self._model, max_tokens=4096,
            system="\n".join(sys_msgs) or None,
            messages=api_msgs, tools=api_tools or None,
        ) as stream:
            for event in stream:
                if getattr(event, "type", None) == "content_block_delta" \
                        and getattr(event.delta, "type", None) == "text_delta":
                    yield StreamChunk(text_delta=event.delta.text)
            final = stream.get_final_message()
        text, calls = None, []
        for block in final.content:
            if block.type == "text":
                text = (text or "") + block.text
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
        u = getattr(final, "usage", None)
        usage = {"input_tokens": getattr(u, "input_tokens", 0), "output_tokens": getattr(u, "output_tokens", 0)} if u else None
        yield StreamChunk(response=LLMResponse(text=text, tool_calls=calls), usage=usage)

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        i = 0
        n = len(messages)
        while i < n:
            m = messages[i]
            if m.role == "tool":
                # Anthropic requires the tool_results that answer ONE assistant
                # turn to live in a SINGLE user message — one tool_result block
                # per tool_use, never duplicated. Coalesce the run of consecutive
                # tool messages and dedupe by tool_use_id (defends against a model
                # that reissues the same tool_use id).
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
                content = ([{"type": "text", "text": m.content}] if m.content else []) + tool_use
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": m.role, "content": m.content or ""})
            i += 1
        return out
