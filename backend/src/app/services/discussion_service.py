def _default_agent_factory(self, persona: Any) -> Any:
        try:
            from src.agent import Agent
            from src.llm import get_provider
            from src.tools import RetrievalTool
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Core agent subsystem unavailable: {exc}"
            ) from exc
        try:
            logger.info(f"=== LLM PROVIDER DEBUG ===")
            logger.info(f"Getting LLM provider...")
            llm = get_provider()
            logger.info(f"Got LLM provider: {llm}")
            logger.info(f"LLM provider type: {type(llm)}")
            logger.info(f"LLM provider model: {getattr(llm, 'model', 'NOT SET')}")
            logger.info(f"LLM provider base_url: {getattr(llm, 'base_url', 'NOT SET')}")
            logger.info(f"LLM provider api_key present: {bool(getattr(llm, 'api_key', None))}")
        except ValueError as exc:
            # Missing/unknown provider or API key — a 503, not a 500.
            raise ServiceUnavailableError(
                "LLM provider unavailable (missing API key or unknown provider). "
                f"Set LLM_PROVIDER/LLM_API_KEY. Detail: {exc}"
            ) from exc
        except Exception as exc:
            raise ServiceUnavailableError(f"LLM provider failed: {exc}") from exc
        try:
            logger.info(f"Creating agent for persona: {getattr(persona, 'name', 'unknown')}")
            return Agent(persona=persona, llm=llm, tools=[RetrievalTool()])
        except Exception as exc:
            raise ServiceUnavailableError(f"Failed to build agent: {exc}") from exc