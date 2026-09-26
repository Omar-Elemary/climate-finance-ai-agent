import os
import importlib
import inspect
from pathlib import Path
from typing import Type

from .base import LLMProvider

_provider_registry: dict[str, Type[LLMProvider]] = {}


def _discover_providers() -> None:
    llm_dir = Path(__file__).parent
    for py_file in llm_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        module_name = f"src.llm.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, LLMProvider) and obj is not LLMProvider:
                key = getattr(obj, "provider_name", py_file.stem)
                _provider_registry[key] = obj


def get_provider(name: str | None = None) -> LLMProvider:
    if name is None:
        name = os.getenv("LLM_PROVIDER", "openrouter")

    if not _provider_registry:
        _discover_providers()

    name = name.lower()
    if name not in _provider_registry:
        available = list(_provider_registry.keys())
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: {available}"
        )

    provider_cls = _provider_registry[name]
    return provider_cls.from_env()


def list_providers() -> list[str]:
    if not _provider_registry:
        _discover_providers()
    return list(_provider_registry.keys())


__all__ = ["LLMProvider", "get_provider", "list_providers"]
