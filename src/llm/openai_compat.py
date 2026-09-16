import os
import logging
from openai import OpenAI

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    provider_name = "openai_compat"

    @staticmethod
    def _default_model() -> str:
        return "deepseek/deepseek-chat"

    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        base_url = (
            self.base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or os.getenv("LLM_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
        api_key = (
            self.api_key
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
        )

        client = OpenAI(api_key=api_key, base_url=base_url)

        temperature = kwargs.get("temperature", getattr(self, "temperature", 0.2))
        max_tokens = kwargs.get("max_tokens", getattr(self, "max_tokens", 2048))
        model = kwargs.get("model", self.model) or os.getenv("LLM_MODEL", "deepseek/deepseek-chat")

        logger.info("OpenAI-compat: calling %s via %s", model, base_url)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            text=choice.message.content or "",
            provider=self.provider_name,
            model=model,
            usage=usage,
            raw=response,
        )


class OpenAIProvider(OpenAICompatProvider):
    provider_name = "openai"
    _DEFAULT_BASE_URL = "https://api.openai.com/v1"

    @staticmethod
    def _default_model() -> str:
        return "gpt-4o-mini"

    @staticmethod
    def _default_base_url() -> str | None:
        return OpenAIProvider._DEFAULT_BASE_URL


class OllamaProvider(OpenAICompatProvider):
    provider_name = "ollama"
    _DEFAULT_BASE_URL = "http://localhost:11434/v1"

    @staticmethod
    def _default_model() -> str:
        return "llama3.1"

    @staticmethod
    def _default_base_url() -> str | None:
        return OllamaProvider._DEFAULT_BASE_URL


class AnthropicProvider(OpenAICompatProvider):
    provider_name = "anthropic"
    _DEFAULT_BASE_URL = "https://api.anthropic.com/v1"

    @staticmethod
    def _default_model() -> str:
        return "claude-3-5-sonnet-20241022"

    @staticmethod
    def _default_base_url() -> str | None:
        return AnthropicProvider._DEFAULT_BASE_URL
    