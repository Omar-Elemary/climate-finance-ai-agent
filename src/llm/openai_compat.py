import logging
from openai import OpenAI

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    provider_name = "openai_compat"

    @staticmethod
    def _default_model() -> str:
        return "gpt-4o-mini"

    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        base_url = self.base_url or "https://api.openai.com/v1"
        client = OpenAI(api_key=self.api_key, base_url=base_url)

        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        model = kwargs.get("model", self.model)

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
