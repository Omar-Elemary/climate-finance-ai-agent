import sys
import os
import logging

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)


def _get_hybrid_search():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        from retriever import hybrid_search_with_metadata
        return hybrid_search_with_metadata
    except (ImportError, Exception) as e:
        logger.warning("Could not import Week 1 retriever: %s", e)
        return None


class RetrievalTool(Tool):
    name = "climate_knowledge_search"
    description = (
        "Search the Week 1 climate finance knowledge base. "
        "Returns relevant evidence chunks with source URLs."
    )

    def __init__(self, top_k: int = 30, rrf_k: int = 60, final_k: int = 3):
        self.top_k = top_k
        self.rrf_k = rrf_k
        self.final_k = final_k

    def run(self, query: str = "", **kwargs) -> ToolResult:
        hybrid_search = _get_hybrid_search()
        if hybrid_search is None:
            return ToolResult(
                success=False,
                error="Week 1 retriever not available. Make sure retriever.py is importable.",
            )

        if not query:
            return ToolResult(success=False, error="No query provided.")

        actual_top_k = kwargs.get("top_k", self.top_k)
        actual_final_k = kwargs.get("final_k", self.final_k)

        try:
            results = hybrid_search(
                query, top_k=actual_top_k, rrf_k=self.rrf_k, final_k=actual_final_k
            )
            logger.info("Retrieved %d chunks for query: %s", len(results), query[:50])
            return ToolResult(success=True, data=results)
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            return ToolResult(success=False, error=str(e))
