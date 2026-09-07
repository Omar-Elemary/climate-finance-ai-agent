"""
Discussion Orchestrator — core coordination layer for multi-agent discussions.

This module owns the discussion lifecycle:
- Initialization
- Round execution
- Agent scheduling
- Context propagation
- Opinion tracking
- Retrieval integration
- Persistence coordination
- Termination

It does NOT own:
- Agent implementation (Week 2)
- LLM implementation (Week 2)
- Graph/routing algorithms
- Week 1 retrieval pipeline
- Database/storage backend
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from .models import (
    DiscussionConfig,
    DiscussionResult,
    DiscussionState,
    DiscussionStatus,
    Message,
    OpinionRecord,
    RetrievalEvent,
)
from .context import DiscussionContextBuilder
from .scheduler import SequentialScheduler, AgentScheduler
from .termination import MaxRoundsTermination, TerminationPolicy
from .persistence import DiscussionPersistence, InMemoryPersistence
from .router import Router, PassthroughRouter
from .retriever import Retriever

logger = logging.getLogger(__name__)


class DiscussionOrchestrator:
    """
    Coordinates multi-round discussions between multiple agents.

    The orchestrator manages the full lifecycle without implementing
    agent logic, routing algorithms, or retrieval internals.

    Usage:
        orchestrator = DiscussionOrchestrator()
        result = orchestrator.start_discussion(
            topic="Should developed countries increase climate finance?",
            agents=[agent_a, agent_b, agent_c],
            config=DiscussionConfig(num_rounds=3),
        )
    """

    def __init__(
        self,
        router: Router | None = None,
        retriever: Retriever | None = None,
        persistence: DiscussionPersistence | None = None,
        scheduler: AgentScheduler | None = None,
        termination: TerminationPolicy | None = None,
        context_builder: DiscussionContextBuilder | None = None,
    ) -> None:
        self.router = router or PassthroughRouter()
        self.retriever = retriever
        self.persistence = persistence or InMemoryPersistence()
        self.scheduler = scheduler or SequentialScheduler()
        self.termination = termination or MaxRoundsTermination()
        self.context_builder = context_builder or DiscussionContextBuilder()

        logger.info(
            "DiscussionOrchestrator initialized: router=%s, retriever=%s, persistence=%s",
            type(self.router).__name__,
            type(self.retriever).__name__ if self.retriever else "None",
            type(self.persistence).__name__,
        )

    def start_discussion(
        self,
        topic: str,
        agents: list[Any],
        config: DiscussionConfig | None = None,
    ) -> DiscussionResult:
        """
        Start and execute a complete multi-round discussion.

        Args:
            topic: The discussion topic.
            agents: List of Agent instances (Week 2 Agent class).
            config: Discussion configuration. Uses defaults if None.

        Returns:
            DiscussionResult with the complete discussion record.
        """
        config = config or DiscussionConfig()

        # 1. Generate discussion ID and initialize state
        discussion_id = str(uuid.uuid4())
        state = DiscussionState(
            discussion_id=discussion_id,
            topic=topic,
            participants=[self._get_agent_id(a) for a in agents],
            total_rounds=config.num_rounds,
            status=DiscussionStatus.RUNNING,
        )

        logger.info(
            "Discussion started: id=%s, topic='%s', agents=%d, rounds=%d",
            discussion_id,
            topic[:60],
            len(agents),
            config.num_rounds,
        )

        # 2. Persist initial state
        self._safe_persist(state)

        try:
            # 3. Execute rounds
            for round_num in range(1, config.num_rounds + 1):
                state.current_round = round_num
                logger.info("--- Round %d/%d ---", round_num, config.num_rounds)

                # Get scheduled agents for this round
                scheduled_agents = self.scheduler.get_agents_for_round(round_num, agents)

                # Each agent participates
                for agent in scheduled_agents:
                    self._process_agent_turn(
                        agent=agent,
                        state=state,
                        config=config,
                    )

                # Persist after each round
                self._safe_persist(state)

                # Check termination
                if self.termination.should_terminate(state):
                    logger.info("Termination policy triggered after round %d", round_num)
                    break

            # 4. Complete
            state.status = DiscussionStatus.COMPLETED
            state.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("Discussion failed: %s", e, exc_info=True)
            state.status = DiscussionStatus.FAILED
            state.error = str(e)
            state.completed_at = datetime.now(timezone.utc)

        # 5. Final persist
        self._safe_persist(state)

        logger.info(
            "Discussion completed: id=%s, status=%s, rounds=%d, messages=%d",
            discussion_id,
            state.status.value,
            state.current_round,
            len(state.messages),
        )

        return DiscussionResult.from_state(state)

    def _process_agent_turn(
        self,
        agent: Any,
        state: DiscussionState,
        config: DiscussionConfig,
    ) -> None:
        """
        Process a single agent's turn in the current round.

        1. Build context for the agent.
        2. Optionally retrieve knowledge.
        3. Get agent response.
        4. Route the response.
        5. Record messages.
        6. Track opinion.
        """
        agent_id = self._get_agent_id(agent)
        agent_name = self._get_agent_name(agent)

        logger.info("Agent turn: %s (Round %d)", agent_name, state.current_round)

        # 1. Retrieve knowledge if enabled
        retrieved_knowledge: list[dict[str, Any]] | None = None
        if config.enable_retrieval and self.retriever is not None:
            retrieved_knowledge = self._retrieve_knowledge(
                agent_id=agent_id,
                topic=state.topic,
                state=state,
            )

        # 2. Build context
        context = self.context_builder.build(
            agent_id=agent_id,
            agent_name=agent_name,
            state=state,
            retrieved_knowledge=retrieved_knowledge,
        )

        # 3. Get agent response
        response_text = self._safe_agent_respond(agent, context)

        # 4. Route the response
        agent_message_dict = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": response_text,
            "round": state.current_round,
            "discussion_id": state.discussion_id,
        }

        routed_messages = self._safe_route(agent_message_dict, state)

        # 5. Record messages
        for routed in routed_messages:
            msg = Message(
                message_id=str(uuid.uuid4()),
                discussion_id=state.discussion_id,
                round=state.current_round,
                agent_id=routed.get("agent_id", agent_id),
                agent_name=routed.get("agent_name", agent_name),
                content=routed.get("content", response_text),
                metadata=routed.get("metadata", {}),
            )
            state.add_message(msg)

        # 6. Track opinion
        if config.enable_opinion_tracking:
            self._track_opinion(agent, agent_id, agent_name, state)

    def _retrieve_knowledge(
        self,
        agent_id: str,
        topic: str,
        state: DiscussionState,
    ) -> list[dict[str, Any]]:
        """Retrieve knowledge and record the retrieval event."""
        query = f"Topic: {topic}. Round: {state.current_round}."
        try:
            results = self.retriever.retrieve(query=query, top_k=3)  # type: ignore[union-attr]

            event = RetrievalEvent(
                event_id=str(uuid.uuid4()),
                discussion_id=state.discussion_id,
                round=state.current_round,
                agent_id=agent_id,
                query=query,
                results=results,
            )
            state.add_retrieval_event(event)

            logger.info(
                "Retrieved %d chunks for agent %s in round %d",
                len(results),
                agent_id,
                state.current_round,
            )
            return results

        except Exception as e:
            logger.warning("Retrieval failed for agent %s: %s", agent_id, e)
            return []

    def _track_opinion(
        self,
        agent: Any,
        agent_id: str,
        agent_name: str,
        state: DiscussionState,
    ) -> None:
        """Extract and record the agent's opinion for this round."""
        try:
            # Use the agent's generate_opinion method if available
            if hasattr(agent, "generate_opinion"):
                opinion_result = agent.generate_opinion(state.topic)
                record = OpinionRecord(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    round=state.current_round,
                    opinion=opinion_result.get("opinion", ""),
                    evidence=opinion_result.get("evidence", []),
                    sources=opinion_result.get("sources", []),
                )
            else:
                # Fallback: extract from the last message
                last_messages = state.get_messages_for_round(state.current_round)
                agent_messages = [m for m in last_messages if m.agent_id == agent_id]
                opinion_text = agent_messages[-1].content if agent_messages else ""

                record = OpinionRecord(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    round=state.current_round,
                    opinion=opinion_text,
                )

            state.add_opinion(record)
            logger.info(
                "Opinion recorded: agent=%s, round=%d",
                agent_name,
                state.current_round,
            )

        except Exception as e:
            logger.warning("Opinion tracking failed for agent %s: %s", agent_id, e)

    def _safe_agent_respond(self, agent: Any, context: str) -> str:
        """Safely call agent.respond() with error handling."""
        try:
            return agent.respond(context)
        except Exception as e:
            logger.error("Agent respond failed: %s", e)
            return f"[Agent error: {e}]"

    def _safe_route(
        self, message: dict[str, Any], state: DiscussionState
    ) -> list[dict[str, Any]]:
        """Safely call router.route() with error handling."""
        try:
            return self.router.route(message=message, state=state)
        except Exception as e:
            logger.error("Router failed: %s", e)
            return [message]

    def _safe_persist(self, state: DiscussionState) -> None:
        """Safely call persistence.save() with error handling."""
        try:
            self.persistence.save(state)
        except Exception as e:
            logger.error("Persistence failed: %s", e)

    @staticmethod
    def _get_agent_id(agent: Any) -> str:
        """Extract agent ID, falling back to persona name or repr."""
        if hasattr(agent, "persona") and hasattr(agent.persona, "name"):
            return agent.persona.name.lower().replace(" ", "_")
        if hasattr(agent, "id"):
            return str(agent.id)
        return repr(agent)

    @staticmethod
    def _get_agent_name(agent: Any) -> str:
        """Extract human-readable agent name."""
        if hasattr(agent, "persona") and hasattr(agent.persona, "name"):
            return agent.persona.name
        if hasattr(agent, "name"):
            return str(agent.name)
        return repr(agent)
