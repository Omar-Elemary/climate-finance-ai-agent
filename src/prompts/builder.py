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


def build_calculation_block(calculation_result: dict[str, Any] | None) -> str:
    if not calculation_result:
        return ""
    metric = calculation_result.get("metric", "Unknown metric")
    value = calculation_result.get("value", "N/A")
    unit = calculation_result.get("unit", "")
    lines = [f"CALCULATED RESULT:", f"- {metric}: {value}{' ' + unit if unit else ''}"]
    for key, val in calculation_result.items():
        if key not in ("metric", "value", "unit"):
            lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def build_web_results_block(web_results: list[dict[str, Any]] | None) -> str:
    if not web_results:
        return ""
    lines = ["WEB SEARCH RESULTS (recent/current information):"]
    for i, r in enumerate(web_results, 1):
        title = r.get("title", "Untitled")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        lines.append(f"[Web {i}] {title} (Source: {url}):\n{snippet}\n")
    return "\n".join(lines)


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
    calculation_result: dict[str, Any] | None = None,
    web_results: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    system = build_system_message(
        persona_context=persona_context,
        memory_context=memory_context,
    )

    messages = [{"role": "system", "content": system}]

    if evidence:
        evidence_block = build_evidence_block(evidence)
        messages.append({"role": "system", "content": evidence_block})

    if calculation_result:
        calculation_block = build_calculation_block(calculation_result)
        messages.append({"role": "system", "content": calculation_block})

    if web_results:
        web_block = build_web_results_block(web_results)
        messages.append({"role": "system", "content": web_block})

    messages.append({
        "role": "user",
        "content": (
            f"Provide your grounded initial opinion on the following topic.\n\n"
            f"TOPIC: {topic}\n\n"
            f"Structure your response as:\n"
            f"1. YOUR OPINION: State your position clearly.\n"
            f"2. EVIDENCE: Reference specific evidence from the provided context "
            f"(retrieved evidence, calculated result, or web search results — "
            f"whichever was provided).\n"
            f"3. REASONING: Explain your analysis connecting evidence to your position.\n"
            f"4. CAVEATS: Note any limitations or uncertainties."
        ),
    })
    return messages