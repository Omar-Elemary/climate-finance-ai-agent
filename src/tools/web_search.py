import logging

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(Tool):
    """
    Searches the web for current information not present in the
    Week 1 knowledge base (e.g. recent news, statistics, events).
    Uses DuckDuckGo (free, no API key required).
    """

    name = "web_search"
    description = (
        "Search the web for current or recent information not covered by the "
        "internal climate finance knowledge base. Useful for recent news, "
        "statistics, or events. Returns a list of results with title, snippet, "
        "and URL."
    )

    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def run(self, query: str = "", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="No query provided.")

        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return ToolResult(
                    success=False,
                    error=(
                        "Web search library not installed. "
                        "Run: pip install ddgs"
                    ),
                )

        actual_max_results = kwargs.get("max_results", self.max_results)

        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=actual_max_results))

            results = [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in raw_results
            ]

            if not results:
                return ToolResult(
                    success=False,
                    error=f"No web results found for query: {query}",
                )

            logger.info("Web search returned %d results for: %s", len(results), query[:50])
            return ToolResult(success=True, data=results)

        except Exception as e:
            logger.error("Web search failed: %s", e)
            return ToolResult(success=False, error=str(e))