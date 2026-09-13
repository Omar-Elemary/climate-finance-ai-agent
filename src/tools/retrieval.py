import sys
import os
import logging

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)


def _ensure_repo_root_on_path():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _get_hybrid_search():
    _ensure_repo_root_on_path()
    try:
        from retriever import hybrid_search_with_metadata
        return hybrid_search_with_metadata
    except (ImportError, Exception) as e:
        logger.warning("Could not import Week 1 retriever: %s", e)
        return None


def _get_bm25_fallback_search():
    """Lexical fallback (no torch / no Postgres needed)."""
    _ensure_repo_root_on_path()
    try:
        from retriever import bm25_only_search
        return bm25_only_search
    except (ImportError, Exception) as e:
        logger.warning("BM25 fallback unavailable: %s", e)
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
        if not query:
            return ToolResult(success=False, error="No query provided.")

        actual_top_k = kwargs.get("top_k", self.top_k)
        actual_final_k = kwargs.get("final_k", self.final_k)

        # 1. Full hybrid path (BM25 + vector + re-rank, degrades internally).
        hybrid_search = _get_hybrid_search()
        if hybrid_search is not None:
            try:
                results = hybrid_search(
                    query, top_k=actual_top_k, rrf_k=self.rrf_k, final_k=actual_final_k
                )
                logger.info("Retrieved %d chunks for query: %s", len(results), query[:50])
                return ToolResult(success=True, data=results)
            except Exception as e:
                logger.warning(
                    "Hybrid retrieval failed (%s); trying BM25 fallback.", e
                )
                hybrid_error = str(e)
        else:
            hybrid_error = "hybrid search import failed (see warning above)"

        # 2. Lexical fallback: no torch, no Postgres — fixes Hanaa's
        # "PreTrainedModel" env issue and missing-DB setups.
        bm25_search = _get_bm25_fallback_search()
        if bm25_search is not None:
            try:
                results = bm25_search(query, final_k=actual_final_k)
                logger.info(
                    "BM25 fallback retrieved %d chunks for query: %s",
                    len(results), query[:50],
                )
                return ToolResult(success=True, data=results)
            except Exception as e:
                logger.error("BM25 fallback failed: %s", e)
                fallback_error = str(e)
        else:
            fallback_error = "bm25_only_search not importable"

        return ToolResult(
            success=False,
            error=(
                "Week 1 retriever not available. Hybrid error: "
                f"{hybrid_error}. BM25 fallback error: {fallback_error}. "
                "If you see 'PreTrainedModel', fix torch/transformers versions "
                "(pip install -U sentence-transformers transformers torch "
                "torchvision). For vector search also need Postgres+pgvector "
                "(setup_postgres.py) and embedder.py output."
            ),
        )
