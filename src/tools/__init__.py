from .base import Tool, ToolResult

__all__ = ["Tool", "ToolResult", "RetrievalTool"]


def __getattr__(name: str):
    if name == "RetrievalTool":
        from .retrieval import RetrievalTool
        return RetrievalTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
