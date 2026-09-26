from .base import Memory

__all__ = ["Memory", "ConversationMemory"]


def __getattr__(name: str):
    if name == "ConversationMemory":
        from .conversation import ConversationMemory
        return ConversationMemory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")