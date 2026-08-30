import logging

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    _DEFAULT_MODEL = "gemini-3.5-flash"

    @staticmethod
    def _default_model() -> str:
        return GeminiProvider._DEFAULT_MODEL

    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai is required for Gemini provider. "
                "Install it with: pip install google-genai"
            )

        client = genai.Client(api_key=self.api_key)
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        logger.info("Gemini: calling %s (temp=%.2f)", model, temperature)

        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "system") else "model"
            if msg["role"] == "system":
                contents.append(msg["content"])
            else:
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

        if len(contents) == 1 and isinstance(contents[0], str):
            prompt = contents[0]
        else:
            prompt = "\n".join(
                c if isinstance(c, str) else c.parts[0].text
                for c in contents
            )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
            ),
        )

        return LLMResponse(
            text=response.text.strip() if response.text else "",
            provider=self.provider_name,
            model=model,
            usage={},
            raw=response,
        )
