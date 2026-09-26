from src.prompts.builder import (
    build_context_block,
    build_system_message,
    build_evidence_block,
    build_chat_messages,
    build_opinion_messages,
)


def test_build_context_block():
    records = [
        {"source_url": "https://a.com", "chunk_text": "text a"},
        {"source_url": "https://b.com", "chunk_text": "text b"},
    ]
    text, sources = build_context_block(records)
    assert "[Context 1]" in text
    assert "https://a.com" in text
    assert "text b" in text
    assert sources == ["https://a.com", "https://b.com"]


def test_build_context_block_empty():
    text, sources = build_context_block([])
    assert text == ""
    assert sources == []


def test_build_system_message():
    msg = build_system_message(persona_context="You are an investor.")
    assert "climate finance analyst" in msg
    assert "You are an investor." in msg
    assert "GROUNDING RULES" in msg


def test_build_system_message_all_parts():
    msg = build_system_message(
        persona_context="Persona info",
        memory_context="Previous chat",
        tool_instructions="Tool A: does X",
        grounding_rules="Rule 1",
    )
    assert "Persona info" in msg
    assert "Previous chat" in msg
    assert "Tool A: does X" in msg
    assert "Rule 1" in msg


def test_build_evidence_block():
    evidence = [{"source_url": "https://x.com", "chunk_text": "evidence text"}]
    block = build_evidence_block(evidence)
    assert "RETRIEVED EVIDENCE" in block
    assert "evidence text" in block


def test_build_evidence_block_empty():
    block = build_evidence_block([])
    assert "No relevant evidence" in block


def test_build_chat_messages():
    msgs = build_chat_messages(
        persona_context="investor",
        user_message="What is climate finance?",
    )
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert "What is climate finance?" in msgs[-1]["content"]


def test_build_opinion_messages():
    msgs = build_opinion_messages(
        persona_context="investor",
        topic="Adaptation finance",
    )
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "system"
    assert "Adaptation finance" in msgs[-1]["content"]
    assert "OPINION" in msgs[-1]["content"]
