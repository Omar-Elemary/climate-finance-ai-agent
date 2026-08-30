from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    name: str = "base_tool"
    description: str = "A base tool."

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        ...

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }
