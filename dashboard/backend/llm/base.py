"""Provider-agnostic LLM client interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    @classmethod
    def from_dict(cls, d: dict) -> "ToolCall":
        return cls(id=d["id"], name=d["name"], arguments=d.get("arguments", {}))


@dataclass
class Message:
    role: str                    # "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None   # set when role == "tool"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_call_id": self.tool_call_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            role=d["role"],
            content=d.get("content"),
            tool_calls=[ToolCall.from_dict(tc) for tc in d.get("tool_calls", [])],
            tool_call_id=d.get("tool_call_id"),
        )


@dataclass
class LLMResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class StreamChunk:
    text_delta: str | None = None       # incremental assistant text
    response: LLMResponse | None = None  # set once, on the final chunk
    usage: dict | None = None


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse: ...

    def stream_chat(self, messages: list[Message], tools: list[ToolSpec]) -> Iterator[StreamChunk]:
        """Default: no token streaming — emit the whole response as one final chunk."""
        yield StreamChunk(response=self.chat(messages, tools))


class FakeLLMClient(LLMClient):
    """Returns scripted responses in order. For tests, no network."""

    def __init__(self, script: list[LLMResponse], usage=None):
        self._script = list(script)
        self._usage = list(usage) if usage else None
        self._i = 0

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        r = self._script[self._i]
        self._i += 1
        return r

    def stream_chat(self, messages: list[Message], tools: list[ToolSpec]) -> Iterator[StreamChunk]:
        r = self._script[self._i]
        u = (self._usage[self._i] if self._usage and self._i < len(self._usage)
             else {"input_tokens": 0, "output_tokens": 0})
        self._i += 1
        if r.text:
            for k, w in enumerate(r.text.split(" ")):
                yield StreamChunk(text_delta=(w if k == 0 else " " + w))
        yield StreamChunk(response=r, usage=u)
