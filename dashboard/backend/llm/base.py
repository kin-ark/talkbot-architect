"""Provider-agnostic LLM client interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
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


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse: ...


class FakeLLMClient(LLMClient):
    """Returns scripted responses in order. For tests, no network."""

    def __init__(self, script: list[LLMResponse]):
        self._script = list(script)
        self._i = 0

    def chat(self, messages: list[Message], tools: list[ToolSpec]) -> LLMResponse:
        r = self._script[self._i]
        self._i += 1
        return r
