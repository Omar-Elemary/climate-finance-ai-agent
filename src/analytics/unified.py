"""Unified Analytics Engine (Week 4).

Combines opinion change, agreement, influence, and sentiment analytics
into a single reusable interface.
"""

import logging
from typing import Any, Dict

from src.metrics.opinion import calculate_opinion_change
from src.metrics.agreement import calculate_agreement
from src.metrics.influence import calculate_influence
from src.metrics.sentiment import get_sentiment_series

logger = logging.getLogger(__name__)


def _create_mock_llm():
    """Create a mock LLM for demo/testing purposes when no API key is available."""
    from unittest.mock import MagicMock

    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Return a neutral sentiment as a safe fallback
    mock_response.text = "SENTIMENT: neutral (0.0)\nSUMMARY: Message content analyzed."
    mock_llm.generate.return_value = mock_response
    return mock_llm


def _get_llm_instance():
    """Get an LLM instance, falling back to a mock if no API keys are configured."""
    try:
        from src.llm import get_provider
        return get_provider()
    except ValueError as e:
        if "No API key found" in str(e):
            logger.warning("No API key found for LLM, using mock LLM for sentiment analysis")
            return _create_mock_llm()
        else:
            # Re-raise if it's a different ValueError
            raise


class AnalyticsEngine:
    """Unified analytics engine for Week 3 discussion history.

    Provides a single interface to compute all four metric categories:
    opinion change, agreement/disagreement, influence, and sentiment.
    """

    def __init__(self):
        """Initialize the analytics engine."""
        logger.info("Initialized Unified Analytics Engine")

    def analyze(self, discussion_history: Any) -> Dict[str, Any]:
        """Run all four analytics on the provided discussion history.

        Args:
            discussion_history: Week 3 DiscussionState object or compatible dict
                               containing 'opinions' and 'messages' data

        Returns:
            Dictionary containing all four metric categories:
            {
                'opinion_change': OpinionChangeResult,
                'agreement': List[AgreementRound],
                'influence': Dict[str, AgentInfluence],
                'sentiment': List[Dict]
            }
        """
        logger.info("Starting unified analytics analysis")

        # Compute all four metric categories
        opinion_change = calculate_opinion_change(discussion_history)
        agreement = calculate_agreement(discussion_history)
        influence = calculate_influence(discussion_history)

        # Get LLM instance (real or mock) for sentiment analysis
        llm = _get_llm_instance()
        sentiment = get_sentiment_series(
            discussion_history.discussion_id if hasattr(discussion_history, 'discussion_id') else "unknown",
            llm=llm
        )

        result = {
            'opinion_change': opinion_change,
            'agreement': agreement,
            'influence': influence,
            'sentiment': sentiment
        }

        logger.info("Completed unified analytics analysis")
        return result

    def analyze_to_dict(self, discussion_history: Any) -> Dict[str, Any]:
        """Run analytics and return results as dictionaries (JSON-serializable).

        Args:
            discussion_history: Week 3 DiscussionState object or compatible dict

        Returns:
            Dictionary with all results converted to dict format
        """
        result = self.analyze(discussion_history)

        # Convert to dict format for easy serialization
        return {
            'opinion_change': result['opinion_change'].to_dict() if hasattr(result['opinion_change'], 'to_dict') else result['opinion_change'],
            'agreement': [r.to_dict() for r in result['agreement']] if result['agreement'] else [],
            'influence': {agent_id: influence.to_dict() for agent_id, influence in result['influence'].items()} if result['influence'] else {},
            'sentiment': result['sentiment']
        }


def create_analytics_engine() -> AnalyticsEngine:
    """Factory function to create an analytics engine instance.

    Returns:
        Configured AnalyticsEngine instance
    """
    return AnalyticsEngine()


# Convenience function for direct usage
def analyze_discussion(discussion_history: Any) -> Dict[str, Any]:
    """Convenience function to run unified analytics on a discussion.

    Args:
        discussion_history: Week 3 DiscussionState object or compatible dict

    Returns:
        Dictionary containing all four metric categories
    """
    engine = create_analytics_engine()
    return engine.analyze(discussion_history)


def analyze_discussion_to_dict(discussion_history: Any) -> Dict[str, Any]:
    """Convenience function to run unified analytics and return dict format.

    Args:
        discussion_history: Week 3 DiscussionState object or compatible dict

    Returns:
        Dictionary with all results converted to dict format (JSON-serializable)
    """
    engine = create_analytics_engine()
    return engine.analyze_to_dict(discussion_history)