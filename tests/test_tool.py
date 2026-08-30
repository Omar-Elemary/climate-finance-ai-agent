from unittest.mock import patch, MagicMock
from src.tools.base import Tool, ToolResult


def test_tool_result_dataclass():
    r = ToolResult(success=True, data=[1, 2, 3])
    assert r.success
    assert r.data == [1, 2, 3]
    assert r.error is None

    r2 = ToolResult(success=False, error="fail")
    assert not r2.success
    assert r2.error == "fail"


def _get_retrieval_tool():
    from src.tools.retrieval import RetrievalTool
    return RetrievalTool


def test_tool_base_has_schema():
    RetrievalTool = _get_retrieval_tool()
    t = RetrievalTool()
    schema = t.to_schema()
    assert "name" in schema
    assert "description" in schema
    assert schema["name"] == "climate_knowledge_search"


def test_retrieval_tool_no_query():
    RetrievalTool = _get_retrieval_tool()
    tool = RetrievalTool()
    mock_fn = MagicMock(return_value=[])
    with patch("src.tools.retrieval._get_hybrid_search", return_value=mock_fn):
        result = tool.run()
        assert not result.success
        assert "No query" in result.error


def test_retrieval_tool_retriever_unavailable():
    RetrievalTool = _get_retrieval_tool()
    with patch("src.tools.retrieval._get_hybrid_search", return_value=None):
        tool = RetrievalTool()
        result = tool.run(query="test")
        assert not result.success
        assert "not available" in result.error


def test_retrieval_tool_success():
    RetrievalTool = _get_retrieval_tool()
    mock_results = [
        {"id": 1, "source_url": "https://example.com", "chunk_text": "text", "rerank_score": 0.9}
    ]
    mock_fn = MagicMock(return_value=mock_results)
    with patch("src.tools.retrieval._get_hybrid_search", return_value=mock_fn):
        tool = RetrievalTool()
        result = tool.run(query="climate finance")
        assert result.success
        assert len(result.data) == 1
        assert result.data[0]["source_url"] == "https://example.com"


def test_retrieval_tool_exception():
    RetrievalTool = _get_retrieval_tool()
    mock_fn = MagicMock(side_effect=DBError("db down"))
    with patch("src.tools.retrieval._get_hybrid_search", return_value=mock_fn):
        tool = RetrievalTool()
        result = tool.run(query="test")
        assert not result.success


class DBError(Exception):
    pass
