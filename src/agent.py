import logging
import json
import re
from typing import Any

from .llm.base import LLMProvider
from .llm import get_provider
from .personas.base import Persona
from .tools.base import Tool, ToolResult
from .prompts.builder import build_chat_messages, build_opinion_messages

logger = logging.getLogger(__name__)

# Keywords that indicate the user is asking for a financial calculation
# rather than general knowledge retrieval.
FINANCIAL_KEYWORDS = [
    "roi", "npv", "return on investment", "net present value",
    "calculate", "payback", "financial return", "investment return",
]

# Keywords that indicate the user wants current/recent information
# that the internal (static) knowledge base is unlikely to cover.
WEB_SEARCH_KEYWORDS = [
    "latest", "recent", "recently", "current", "currently", "today",
    "this week", "this month", "this year", "breaking", "news",
    "2026", "2027",  # adjust/extend as years pass
]


class Agent:
    def __init__(
        self,
        persona: Persona,
        llm: LLMProvider | None = None,
        memory: Any | None = None,
        tools: list[Tool] | None = None,
    ):
        self.persona = persona
        self.llm = llm or get_provider()
        self.memory = memory
        self.tools = tools or []
        self._tool_map = {t.name: t for t in self.tools}
        logger.info(
            "Agent initialized: persona=%s, llm=%s/%s, tools=%d",
            self.persona.name,
            self.llm.provider_name,
            self.llm.model,
            len(self.tools),
        )

    def respond(self, message: str) -> str:
        logger.info("Agent.respond: %s", message[:80])

        memory_context = ""
        if self.memory:
            try:
                memory_context = self.memory.get_context()
            except Exception as e:
                logger.warning("Memory context failed: %s", e)

        tool_instructions = self._format_tool_descriptions()

        messages = build_chat_messages(
            persona_context=self.persona.to_prompt_context(),
            memory_context=memory_context,
            user_message=message,
            tool_instructions=tool_instructions,
        )

        response = self.llm.generate(messages)

        if self.memory:
            try:
                self.memory.add("user", message)
                self.memory.add("assistant", response.text)
            except Exception as e:
                logger.warning("Memory store failed: %s", e)

        return response.text

    def generate_opinion(self, topic: str, **financial_params) -> dict[str, Any]:
        """
        Generate a grounded opinion on a topic.

        Tool selection is rule-based (not true LLM function-calling):
        - If the topic looks like a financial calculation request (contains
          keywords like 'ROI' or 'NPV'), the financial_calculator tool is used.
          Numeric inputs must be passed via **financial_params.
        - Else if the topic looks like it needs current/recent information
          (contains keywords like 'latest', 'recent', '2026'), the web_search
          tool is used instead of the internal knowledge base.
        - Otherwise, the climate_knowledge_search (retrieval) tool is used,
          as before.

        Known limitation: this is a simple keyword-based router, not a
        model-driven tool choice. A future improvement would use LLM function
        calling so the model itself decides which tool to invoke and extracts
        the required arguments from natural language.
        """
        logger.info("Agent.generate_opinion: %s", topic)

        evidence = []
        sources = []
        calculation_result = None
        web_results = None

        if self._looks_financial(topic):
            calc_result = self._use_tool(
                "financial_calculator",
                calculation=financial_params.get("calculation", "roi"),
                **{k: v for k, v in financial_params.items() if k != "calculation"},
            )
            if calc_result.success:
                calculation_result = calc_result.data
            else:
                logger.warning("Financial calculation failed: %s", calc_result.error)

        elif self._looks_like_web_search(topic):
            search_result = self._use_tool("web_search", query=topic)
            if search_result.success and search_result.data:
                web_results = search_result.data
                sources = list(dict.fromkeys(
                    r.get("url", "") for r in web_results if r.get("url")
                ))
            else:
                logger.warning("Web search failed: %s", search_result.error)

        else:
            retrieval_result = self._use_tool("climate_knowledge_search", query=topic)
            if retrieval_result.success and retrieval_result.data:
                evidence = retrieval_result.data
                sources = list(dict.fromkeys(
                    r.get("source_url", "") for r in evidence if r.get("source_url")
                ))

        memory_context = ""
        if self.memory:
            try:
                memory_context = self.memory.get_context()
            except Exception:
                pass

        messages = build_opinion_messages(
            persona_context=self.persona.to_prompt_context(),
            memory_context=memory_context,
            evidence=evidence,
            topic=topic,
            calculation_result=calculation_result,
            web_results=web_results,
        )

        response = self.llm.generate(messages)

        opinion_text = response.text
        evidence_texts = [r.get("chunk_text", "") for r in evidence]

        result = {
            "topic": topic,
            "persona": self.persona.name,
            "opinion": opinion_text,
            "evidence": evidence_texts,
            "sources": sources,
            "calculation": calculation_result,
            "web_results": web_results,
            "provider": self.llm.provider_name,
            "model": self.llm.model,
        }

        if self.memory:
            try:
                self.memory.add("user", f"[Opinion request] {topic}")
                self.memory.add("assistant", opinion_text)
            except Exception:
                pass

        return result

    def _looks_financial(self, topic: str) -> bool:
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in FINANCIAL_KEYWORDS)

    def _looks_like_web_search(self, topic: str) -> bool:
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in WEB_SEARCH_KEYWORDS)

    def _use_tool(self, tool_name: str, **kwargs) -> ToolResult:
        if tool_name not in self._tool_map:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not available.")
        try:
            result = self._tool_map[tool_name].run(**kwargs)
            logger.info(
                "Tool '%s' result: success=%s, items=%s",
                tool_name,
                result.success,
                len(result.data) if result.success and isinstance(result.data, list) else "N/A",
            )
            return result
        except Exception as e:
            logger.error("Tool '%s' failed: %s", tool_name, e)
            return ToolResult(success=False, error=str(e))

    def _format_tool_descriptions(self) -> str:
        if not self.tools:
            return "No tools available."
        lines = []
        for tool in self.tools:
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)