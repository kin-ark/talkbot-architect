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


@dataclass
class Message:
    role: str                    # "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None   # set when role == "tool"


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
