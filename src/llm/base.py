from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


class LLMProvider(ABC):
    provider_name: str = "base"

    def __init__(self, api_key: str, model: str, base_url: str | None = None,
                 temperature: float = 0.2, max_tokens: int = 2048):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "LLMProvider":
        api_key = (
            os.getenv(f"{cls.provider_name.upper()}_API_KEY")
            or os.getenv("LLM_API_KEY", "")
        )
        if not api_key:
            raise ValueError(
                f"No API key found. Set LLM_API_KEY or "
                f"{cls.provider_name.upper()}_API_KEY in your .env file."
            )

        model = os.getenv("LLM_MODEL", cls._default_model())
        base_url = os.getenv("LLM_BASE_URL") or cls._default_base_url()
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        ...

    @staticmethod
    def _default_model() -> str:
        return ""

    @staticmethod
    def _default_base_url() -> str | None:
        return None


import os
