import logging
from openai import OpenAI

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):
    provider_name = "openrouter"
    _DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    _DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

    @staticmethod
    def _default_model() -> str:
        return OpenRouterProvider._DEFAULT_MODEL

    @staticmethod
    def _default_base_url() -> str | None:
        return OpenRouterProvider._DEFAULT_BASE_URL

    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url or self._DEFAULT_BASE_URL,
        )

        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        model = kwargs.get("model", self.model)

        logger.info("OpenRouter: calling %s (temp=%.2f)", model, temperature)

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
