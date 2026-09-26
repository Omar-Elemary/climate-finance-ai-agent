import os
import logging
import time
from openai import OpenAI

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Retryable provider errors: TPM/RPM rate limits are per-minute windows,
# so waiting out the window and retrying the identical request succeeds.
_RETRY_DELAYS = (15, 30, 60, 120)


def _is_rate_limit(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) in (408, 413, 429, 500, 502, 503, 504):
        return True
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "rate_limit_exceeded",
            "rate limit",
            "resource_exhausted",
            "too large",
            "tpm",
            "rpm",
            "429",
            "413",
            "503",
            "overloaded",
        )
    )


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

        logger.info(f"=== OPENAI COMPAT PROVIDER DEBUG ===")
        logger.info(f"Self.base_url: {getattr(self, 'base_url', 'NOT SET')}")
        logger.info(f"OPENAI_BASE_URL env: {os.getenv('OPENAI_BASE_URL', 'NOT SET')}")
        logger.info(f"LLM_BASE_URL env: {os.getenv('LLM_BASE_URL', 'NOT SET')}")
        logger.info(f"Final base_url: {base_url}")
        logger.info(f"API key present: {bool(api_key)}")
        logger.info(f"API key prefix: {api_key[:10] if api_key else 'None'}")

        logger.info(f"Initializing OpenAI client with base_url: {base_url}")
        client = OpenAI(api_key=api_key, base_url=base_url)

        temperature = kwargs.get("temperature", getattr(self, "temperature", 0.2))
        max_tokens = kwargs.get("max_tokens", getattr(self, "max_tokens", 2048))
        model = kwargs.get("model", self.model) or os.getenv("LLM_MODEL", "deepseek/deepseek-chat")

        logger.info(f"OpenAI-compat: calling model {model} via {base_url}")
        logger.info(f"Messages count: {len(messages)}")
        logger.info(f"First message: {messages[0] if messages else 'None'}")

        response = None
        last_error: Exception | None = None
        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                break
            except Exception as e:
                last_error = e
                if attempt < len(_RETRY_DELAYS) and _is_rate_limit(e):
                    wait = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "OpenAI-compat: rate-limited (attempt %d), waiting %ds: %s",
                        attempt + 1, wait, str(e)[:160],
                    )
                    time.sleep(wait)
                    continue
                logger.error(f"OpenAI-compat: Error calling {model}: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                # Re-raise to let higher levels handle it
                raise
        if response is None:
            logger.error("OpenAI-compat: exhausted retries for %s", model)
            raise last_error if last_error is not None else RuntimeError(
                "OpenAI-compat: exhausted retries without response"
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