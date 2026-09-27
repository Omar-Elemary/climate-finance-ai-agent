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
        # Use the instance variables that were set in the constructor via from_env()
        base_url = self.base_url
        api_key = self.api_key
        model = kwargs.get("model", self.model)

        logger.info(f"=== OPENAI COMPAT PROVIDER DEBUG ===")
        logger.info(f"Using base_url: {base_url}")
        logger.info(f"Using model: {model}")
        logger.info(f"API key present: {bool(api_key)}")
        if api_key:
            logger.info(f"API key prefix: {api_key[:10]}")

        logger.info(f"Initializing OpenAI client with base_url: {base_url}")
        client = OpenAI(api_key=api_key, base_url=base_url)

        temperature = kwargs.get("temperature", getattr(self, "temperature", 0.2))
        max_tokens = kwargs.get("max_tokens", getattr(self, "max_tokens", 2048))

        logger.info(f"OpenAI-compat: calling model {model} via {base_url}")
        logger.info(f"Messages count: {len(messages)}")
        logger.info(f"First message: {messages[0] if messages else 'None'}")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            logger.info(f"OpenAI-compat: successful response from {model}")

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
        except Exception as e:
            logger.error(f"OpenAI-compat: Error calling {model}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error args: {e.args}")
            # Re-raise to let higher levels handle it
            raise


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