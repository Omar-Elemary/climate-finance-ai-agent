"""
Retriever Protocol — interface for Week 1 knowledge retrieval.

The orchestrator depends on this abstraction, NOT on the concrete
Week 1 RAG pipeline. Any retriever that implements this protocol
can be injected.

OWNER: Member 1 — Knowledge Infrastructure (Week 1 RAG pipeline)
STATUS: Protocol defined. Concrete implementation exists in src/tools/retrieval.py.
"""

from typing import Protocol, Any


class Retriever(Protocol):
    """Protocol for knowledge retrieval during discussion."""

    def retrieve(self, query: str, top_k: int = 3, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Retrieve relevant knowledge chunks for a query.

        Args:
            query: The search query.
            top_k: Maximum number of results to return.
            **kwargs: Additional provider-specific parameters.

        Returns:
            List of result dicts, each containing at minimum:
            - chunk_text: str
            - source_url: str
            - rerank_score: float (optional)
        """
        ...
