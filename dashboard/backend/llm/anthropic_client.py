from __future__ import annotations

from llm.base import LLMClient, LLMResponse, Message, ToolCall, ToolSpec


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

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

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.role == "tool":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content or ""}]})
            elif m.role == "assistant" and m.tool_calls:
                content = ([{"type": "text", "text": m.content}] if m.content else []) + [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in m.tool_calls]
                out.append({"role": "assistant", "content": content})
            else:
                out.append({"role": m.role, "content": m.content or ""})
        return out
