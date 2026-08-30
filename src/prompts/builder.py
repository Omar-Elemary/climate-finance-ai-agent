from typing import Any


def build_context_block(
    records: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    context_parts = []
    sources = []
    for i, r in enumerate(records, 1):
        url = r.get("source_url", "Unknown Source")
        text = r.get("chunk_text", "")
        sources.append(url)
        context_parts.append(f"[Context {i}] (Source: {url}):\n{text}\n")
    return "\n".join(context_parts), sources


def build_system_message(
    persona_context: str = "",
    memory_context: str = "",
    tool_instructions: str = "",
    grounding_rules: str = "",
) -> str:
    parts = []

    parts.append(
        "You are a professional climate finance analyst providing "
        "grounded, evidence-based analysis."
    )

    if persona_context:
        parts.append(f"\nPERSONA:\n{persona_context}")

    if grounding_rules:
        parts.append(f"\nGROUNDING RULES:\n{grounding_rules}")
    else:
        parts.append(
            "\nGROUNDING RULES:\n"
            "- Answer using ONLY verified context when evidence is provided.\n"
            "- If context is insufficient, state that you lack sufficient data.\n"
            "- Do not hallucinate or invent sources.\n"
            "- Cite context numbers when referencing evidence.\n"
            "- Clearly distinguish between retrieved evidence and your analysis."
        )

    if tool_instructions:
        parts.append(f"\nAVAILABLE TOOLS:\n{tool_instructions}")

    if memory_context:
        parts.append(f"\nCONVERSATION HISTORY:\n{memory_context}")

    return "\n".join(parts)


def build_evidence_block(
    evidence: list[dict[str, Any]],
) -> str:
    if not evidence:
        return "No relevant evidence retrieved."
    context_text, _ = build_context_block(evidence)
    return f"RETRIEVED EVIDENCE:\n{context_text}"


def build_chat_messages(
    persona_context: str = "",
    memory_context: str = "",
    evidence: list[dict[str, Any]] | None = None,
    user_message: str = "",
    tool_instructions: str = "",
) -> list[dict[str, str]]:
    system = build_system_message(
        persona_context=persona_context,
        memory_context=memory_context,
        tool_instructions=tool_instructions,
    )

    messages = [{"role": "system", "content": system}]

    if evidence:
        evidence_block = build_evidence_block(evidence)
        messages.append({"role": "system", "content": evidence_block})

    messages.append({"role": "user", "content": user_message})
    return messages


def build_opinion_messages(
    persona_context: str = "",
    memory_context: str = "",
    evidence: list[dict[str, Any]] | None = None,
    topic: str = "",
) -> list[dict[str, str]]:
    system = build_system_message(
        persona_context=persona_context,
        memory_context=memory_context,
    )

    messages = [{"role": "system", "content": system}]

    if evidence:
        evidence_block = build_evidence_block(evidence)
        messages.append({"role": "system", "content": evidence_block})

    messages.append({
        "role": "user",
        "content": (
            f"Provide your grounded initial opinion on the following topic.\n\n"
            f"TOPIC: {topic}\n\n"
            f"Structure your response as:\n"
            f"1. YOUR OPINION: State your position clearly.\n"
            f"2. EVIDENCE: Reference specific evidence from the provided context.\n"
            f"3. REASONING: Explain your analysis connecting evidence to your position.\n"
            f"4. CAVEATS: Note any limitations or uncertainties."
        ),
    })
    return messages
