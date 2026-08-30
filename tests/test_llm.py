import os
from unittest.mock import patch, MagicMock
from src.llm.base import LLMProvider, LLMResponse
from src.llm import get_provider, list_providers


def test_base_provider_cannot_be_instantiated():
    from abc import ABCMeta
    assert isinstance(LLMProvider, ABCMeta)


def test_list_providers():
    providers = list_providers()
    assert isinstance(providers, list)
    assert "openrouter" in providers
    assert "gemini" in providers
    assert "openai_compat" in providers


def test_get_provider_mock():
    with patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
        from src.llm.openrouter import OpenRouterProvider
        mock_provider = MagicMock(spec=OpenRouterProvider)
        mock_provider.provider_name = "mock"
        mock_provider.from_env.return_value = mock_provider


def test_llm_response_dataclass():
    resp = LLMResponse(text="hello", provider="test", model="m1")
    assert resp.text == "hello"
    assert resp.provider == "test"
    assert resp.model == "m1"
    assert resp.usage == {}
    assert resp.raw is None


def test_provider_from_env_missing_key():
    env = {
        "LLM_PROVIDER": "openrouter",
        "LLM_API_KEY": "",
    }
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("LLM_API_KEY", None)
        try:
            from src.llm.openrouter import OpenRouterProvider
            OpenRouterProvider.from_env()
        except (ValueError, SystemExit):
            pass


def test_provider_base_defaults():
    from src.llm.openrouter import OpenRouterProvider
    p = OpenRouterProvider(api_key="test", model="test-model")
    assert p._default_base_url() == "https://openrouter.ai/api/v1"
    assert p._default_model() == "anthropic/claude-3.5-sonnet"


def test_provider_generates_response():
    from src.llm.openrouter import OpenRouterProvider

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    with patch("src.llm.openrouter.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        p = OpenRouterProvider(api_key="test-key", model="test-model")
        result = p.generate([{"role": "user", "content": "Hello"}])

        assert isinstance(result, LLMResponse)
        assert result.text == "Test response"
        assert result.provider == "openrouter"
        assert result.model == "test-model"
        assert result.usage["total_tokens"] == 30
