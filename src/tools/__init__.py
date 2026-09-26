from .base import Tool, ToolResult

__all__ = ["Tool", "ToolResult", "RetrievalTool", "FinancialCalculatorTool", "WebSearchTool"]


def __getattr__(name: str):
    if name == "RetrievalTool":
        from .retrieval import RetrievalTool
        return RetrievalTool
    if name == "FinancialCalculatorTool":
        from .financial_calculator import FinancialCalculatorTool
        return FinancialCalculatorTool
    if name == "WebSearchTool":
        from .web_search import WebSearchTool
        return WebSearchTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")