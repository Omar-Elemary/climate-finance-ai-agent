from .base import DiscussionPersistence, InMemoryPersistence

__all__ = ["DiscussionPersistence", "InMemoryPersistence", "FilePersistence"]


def __getattr__(name: str):
    if name == "FilePersistence":
        from .file_persistence import FilePersistence
        return FilePersistence
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")