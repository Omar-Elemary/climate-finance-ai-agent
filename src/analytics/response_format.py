"""
src/analytics/response_format.py
OWNER: HANAA — Week 5, analytics response format

The exact JSON shape the frontend receives from
    GET /discussions/{discussion_id}/analytics
(or from the Streamlit page calling the adapter directly).

Rules:
  1. Every section is ALWAYS present, even when its metric failed.
  2. Every section carries its own "status" and "error".
     The frontend checks status == "ok"; anything else -> show a message.
  3. Data is chart-ready: lists of points / rows / nodes / edges,
     never nested Python objects.
  4. No calculation happens here. This file only defines shapes.

Status values (same vocabulary as Week 4):
  "ok"                 section has data, draw it
  "insufficient_data"  metric ran, but too few rounds/agents to say anything
  "unavailable"        metric module not present / not run
  "error"              metric raised, or its output could not be read

Field names follow the real Week 4 modules (opinion.py, agreement.py,
influence.py, sentiment.py). Rounds are numbered as Week 3 numbers them
(the demo run uses 0, 1, 2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

RESPONSE_SCHEMA_VERSION = "1.1"

SECTION_OK = "ok"
SECTION_INSUFFICIENT = "insufficient_data"
SECTION_UNAVAILABLE = "unavailable"
SECTION_ERROR = "error"

KNOWN_STATUSES = (SECTION_OK, SECTION_INSUFFICIENT, SECTION_UNAVAILABLE, SECTION_ERROR)


# --------------------------------------------------------------------------- #
# Opinion trajectory  ->  line chart (x = round, y = stance, one line per agent)
# source: opinion.calculate_opinion_change -> OpinionChangeResult
# --------------------------------------------------------------------------- #

class StancePointOut(TypedDict):
    round: int
    stance: Optional[float]        # -1 against .. +1 in favor; None = missing/invalid
    change: Optional[float]        # vs previous round; None for first/missing


class AgentSeriesOut(TypedDict):
    agent_id: str
    agent_name: str
    points: List[StancePointOut]   # sorted by round
    initial: Optional[float]
    final: Optional[float]
    total_change: Optional[float]
    direction: Optional[str]       # up | down | flat | mixed | insufficient


class OpinionTrajectorySection(TypedDict):
    status: str
    error: Optional[str]
    series: List[AgentSeriesOut]


# --------------------------------------------------------------------------- #
# Agreement  ->  line chart or bars (x = round, y = 0..1)
# source: agreement.calculate_agreement -> list[AgreementRound]
# --------------------------------------------------------------------------- #

class AgreementRoundOut(TypedDict):
    round: int
    score: Optional[float]         # AgreementRound.agreement_score
    status: str
    n_valid: Optional[int]


class AgreementSection(TypedDict):
    status: str
    error: Optional[str]
    rounds: List[AgreementRoundOut]
    final: Optional[float]         # last round with a score
    mean: Optional[float]          # average over rounds with a score


# --------------------------------------------------------------------------- #
# Influence  ->  bar chart / ranked list (sorted, highest first)
# source: influence.calculate_influence -> dict[str, AgentInfluence]
# --------------------------------------------------------------------------- #

class InfluenceRowOut(TypedDict):
    agent_id: str
    agent_name: str
    score: Optional[float]         # AgentInfluence.influence_score (sums to 1.0)
    raw_pull: Optional[float]
    messages_sent: Optional[int]
    status: str


class InfluenceSection(TypedDict):
    status: str
    error: Optional[str]
    agents: List[InfluenceRowOut]
    all_equal: bool                # True -> "no agent stood out" (e.g. all 0.25)


# --------------------------------------------------------------------------- #
# Sentiment  ->  distribution + bars by agent / round + per-message table
# source: sentiment.get_sentiment_series -> list of message rows
# --------------------------------------------------------------------------- #

class SentimentDistributionOut(TypedDict):
    positive: int
    negative: int
    neutral: int
    total: int


class SentimentGroupOut(TypedDict):
    key: str                       # agent_id, or the round number as text
    label: str                     # agent_name, or "Round 2"
    mean_polarity: Optional[float] # -1 negative tone .. +1 positive tone
    n_messages: int
    dominant: Optional[str]        # most common label in the group


class SentimentMessageOut(TypedDict):
    round: Optional[int]
    agent_id: str
    agent_name: str
    sentiment: str
    polarity: Optional[float]
    summary: str


class SentimentSection(TypedDict):
    status: str
    error: Optional[str]
    distribution: SentimentDistributionOut
    by_agent: List[SentimentGroupOut]
    by_round: List[SentimentGroupOut]
    messages: List[SentimentMessageOut]


# --------------------------------------------------------------------------- #
# Interaction graph  ->  network (works with pyvis, networkx, plotly,
#                        streamlit-agraph, cytoscape, react-force-graph, ...)
# source: Week 3 messages (edges) + influence (node size)
# --------------------------------------------------------------------------- #

class GraphNodeOut(TypedDict):
    id: str
    label: str
    influence: Optional[float]     # node size
    messages_sent: int


class GraphEdgeOut(TypedDict):
    source: str
    target: str
    weight: int
    kind: str                      # "messages" | "co_participation"


class InteractionGraphSection(TypedDict):
    status: str
    error: Optional[str]
    edge_basis: str                # "messages" | "co_participation" | "none"
    directed: bool
    nodes: List[GraphNodeOut]
    edges: List[GraphEdgeOut]


# --------------------------------------------------------------------------- #
# The full response
# --------------------------------------------------------------------------- #

class AnalyticsResponse(TypedDict):
    schema_version: str
    generated_at: str
    discussion_id: Optional[str]
    topic: Optional[str]
    agents: List[str]
    agent_names: Dict[str, str]    # {"investor": "Climate Investor", ...}
    rounds: List[int]
    status: Dict[str, str]         # one-glance: {"opinion_trajectory": "ok", ...}
    opinion_trajectory: OpinionTrajectorySection
    agreement: AgreementSection
    influence: InfluenceSection
    sentiment: SentimentSection
    interaction_graph: InteractionGraphSection
    warnings: List[str]
    errors: List[str]


SECTION_NAMES = (
    "opinion_trajectory",
    "agreement",
    "influence",
    "sentiment",
    "interaction_graph",
)


def empty_section(name: str, status: str = SECTION_UNAVAILABLE,
                  error: Optional[str] = None) -> Dict[str, Any]:
    """A section with the right keys and no data. Used when a metric is missing."""
    base: Dict[str, Any] = {"status": status, "error": error}
    if name == "opinion_trajectory":
        base["series"] = []
    elif name == "agreement":
        base.update(rounds=[], final=None, mean=None)
    elif name == "influence":
        base.update(agents=[], all_equal=False)
    elif name == "sentiment":
        base.update(
            distribution={"positive": 0, "negative": 0, "neutral": 0, "total": 0},
            by_agent=[], by_round=[], messages=[],
        )
    elif name == "interaction_graph":
        base.update(edge_basis="none", directed=False, nodes=[], edges=[])
    else:
        raise ValueError(f"unknown section: {name}")
    return base


# --------------------------------------------------------------------------- #
# Example — generated by running the real adapter on a demo-shaped run.
# The frontend team builds against this before the backend is ready.
# --------------------------------------------------------------------------- #

EXAMPLE_RESPONSE: Dict[str, Any] = {'schema_version': '1.1',
 'generated_at': '2026-09-21T10:15:32+00:00',
 'discussion_id': 'test-run-001',
 'topic': 'Should developed countries increase climate finance?',
 'agents': ['cfo_agent', 'investor', 'policy_expert', 'scientist'],
 'agent_names': {'cfo_agent': 'CFO Agent',
                 'investor': 'Climate Investor',
                 'policy_expert': 'Policy Expert',
                 'scientist': 'Environmental Scientist'},
 'rounds': [0, 1, 2],
 'status': {'opinion_trajectory': 'ok',
            'agreement': 'ok',
            'influence': 'ok',
            'sentiment': 'ok',
            'interaction_graph': 'ok'},
 'opinion_trajectory': {'status': 'ok',
                        'error': None,
                        'series': [{'agent_id': 'cfo_agent',
                                    'agent_name': 'CFO Agent',
                                    'points': [{'round': 0,
                                                'stance': 0.0,
                                                'change': None},
                                               {'round': 1,
                                                'stance': -1.0,
                                                'change': -1.0},
                                               {'round': 2,
                                                'stance': 0.0,
                                                'change': 1.0}],
                                    'initial': 0.0,
                                    'final': 0.0,
                                    'total_change': 0.0,
                                    'direction': 'mixed'},
                                   {'agent_id': 'investor',
                                    'agent_name': 'Climate Investor',
                                    'points': [{'round': 0,
                                                'stance': 1.0,
                                                'change': None},
                                               {'round': 1,
                                                'stance': -1.0,
                                                'change': -2.0},
                                               {'round': 2,
                                                'stance': 0.0,
                                                'change': 1.0}],
                                    'initial': 1.0,
                                    'final': 0.0,
                                    'total_change': -1.0,
                                    'direction': 'mixed'},
                                   {'agent_id': 'policy_expert',
                                    'agent_name': 'Policy Expert',
                                    'points': [{'round': 0,
                                                'stance': 1.0,
                                                'change': None},
                                               {'round': 1,
                                                'stance': 1.0,
                                                'change': 0.0},
                                               {'round': 2,
                                                'stance': 1.0,
                                                'change': 0.0}],
                                    'initial': 1.0,
                                    'final': 1.0,
                                    'total_change': 0.0,
                                    'direction': 'flat'},
                                   {'agent_id': 'scientist',
                                    'agent_name': 'Environmental Scientist',
                                    'points': [{'round': 0,
                                                'stance': 1.0,
                                                'change': None},
                                               {'round': 1,
                                                'stance': 1.0,
                                                'change': 0.0},
                                               {'round': 2,
                                                'stance': 1.0,
                                                'change': 0.0}],
                                    'initial': 1.0,
                                    'final': 1.0,
                                    'total_change': 0.0,
                                    'direction': 'flat'}]},
 'agreement': {'status': 'ok',
               'error': None,
               'rounds': [{'round': 0, 'score': 0.75, 'status': 'ok', 'n_valid': 4},
                          {'round': 1, 'score': 0.3333, 'status': 'ok', 'n_valid': 4},
                          {'round': 2, 'score': 0.6667, 'status': 'ok', 'n_valid': 4}],
               'final': 0.6667,
               'mean': 0.5833},
 'influence': {'status': 'ok',
               'error': None,
               'agents': [{'agent_id': 'cfo_agent',
                           'agent_name': 'CFO Agent',
                           'score': 0.25,
                           'raw_pull': 0.0,
                           'messages_sent': 3,
                           'status': 'ok'},
                          {'agent_id': 'investor',
                           'agent_name': 'Climate Investor',
                           'score': 0.25,
                           'raw_pull': 0.0,
                           'messages_sent': 3,
                           'status': 'ok'},
                          {'agent_id': 'policy_expert',
                           'agent_name': 'Policy Expert',
                           'score': 0.25,
                           'raw_pull': 0.0,
                           'messages_sent': 3,
                           'status': 'ok'},
                          {'agent_id': 'scientist',
                           'agent_name': 'Environmental Scientist',
                           'score': 0.25,
                           'raw_pull': 0.0,
                           'messages_sent': 3,
                           'status': 'ok'}],
               'all_equal': True},
 'sentiment': {'status': 'ok',
               'error': None,
               'distribution': {'positive': 6,
                                'negative': 2,
                                'neutral': 4,
                                'total': 12},
               'by_agent': [{'key': 'cfo_agent',
                             'label': 'CFO Agent',
                             'mean_polarity': -0.2,
                             'n_messages': 3,
                             'dominant': 'neutral'},
                            {'key': 'investor',
                             'label': 'Climate Investor',
                             'mean_polarity': 0.0333,
                             'n_messages': 3,
                             'dominant': 'positive'},
                            {'key': 'policy_expert',
                             'label': 'Policy Expert',
                             'mean_polarity': 0.6,
                             'n_messages': 3,
                             'dominant': 'positive'},
                            {'key': 'scientist',
                             'label': 'Environmental Scientist',
                             'mean_polarity': 0.3333,
                             'n_messages': 3,
                             'dominant': 'positive'}],
               'by_round': [{'key': '0',
                             'label': 'Round 0',
                             'mean_polarity': 0.375,
                             'n_messages': 4,
                             'dominant': 'positive'},
                            {'key': '1',
                             'label': 'Round 1',
                             'mean_polarity': -0.05,
                             'n_messages': 4,
                             'dominant': 'negative'},
                            {'key': '2',
                             'label': 'Round 2',
                             'mean_polarity': 0.25,
                             'n_messages': 4,
                             'dominant': 'neutral'}],
               'messages': [{'round': 0,
                             'agent_id': 'cfo_agent',
                             'agent_name': 'CFO Agent',
                             'sentiment': 'neutral',
                             'polarity': 0.0,
                             'summary': 'CFO Agent round 0 summary.'},
                            {'round': 0,
                             'agent_id': 'investor',
                             'agent_name': 'Climate Investor',
                             'sentiment': 'positive',
                             'polarity': 0.5,
                             'summary': 'Climate Investor round 0 summary.'},
                            {'round': 0,
                             'agent_id': 'policy_expert',
                             'agent_name': 'Policy Expert',
                             'sentiment': 'positive',
                             'polarity': 0.6,
                             'summary': 'Policy Expert round 0 summary.'},
                            {'round': 0,
                             'agent_id': 'scientist',
                             'agent_name': 'Environmental Scientist',
                             'sentiment': 'positive',
                             'polarity': 0.4,
                             'summary': 'Environmental Scientist round 0 summary.'},
                            {'round': 1,
                             'agent_id': 'cfo_agent',
                             'agent_name': 'CFO Agent',
                             'sentiment': 'negative',
                             'polarity': -0.5,
                             'summary': 'CFO Agent round 1 summary.'},
                            {'round': 1,
                             'agent_id': 'investor',
                             'agent_name': 'Climate Investor',
                             'sentiment': 'negative',
                             'polarity': -0.4,
                             'summary': 'Climate Investor round 1 summary.'},
                            {'round': 1,
                             'agent_id': 'policy_expert',
                             'agent_name': 'Policy Expert',
                             'sentiment': 'positive',
                             'polarity': 0.6,
                             'summary': 'Policy Expert round 1 summary.'},
                            {'round': 1,
                             'agent_id': 'scientist',
                             'agent_name': 'Environmental Scientist',
                             'sentiment': 'neutral',
                             'polarity': 0.1,
                             'summary': 'Environmental Scientist round 1 summary.'},
                            {'round': 2,
                             'agent_id': 'cfo_agent',
                             'agent_name': 'CFO Agent',
                             'sentiment': 'neutral',
                             'polarity': -0.1,
                             'summary': 'CFO Agent round 2 summary.'},
                            {'round': 2,
                             'agent_id': 'investor',
                             'agent_name': 'Climate Investor',
                             'sentiment': 'neutral',
                             'polarity': 0.0,
                             'summary': 'Climate Investor round 2 summary.'},
                            {'round': 2,
                             'agent_id': 'policy_expert',
                             'agent_name': 'Policy Expert',
                             'sentiment': 'positive',
                             'polarity': 0.6,
                             'summary': 'Policy Expert round 2 summary.'},
                            {'round': 2,
                             'agent_id': 'scientist',
                             'agent_name': 'Environmental Scientist',
                             'sentiment': 'positive',
                             'polarity': 0.5,
                             'summary': 'Environmental Scientist round 2 summary.'}]},
 'interaction_graph': {'status': 'ok',
                       'error': None,
                       'edge_basis': 'messages',
                       'directed': True,
                       'nodes': [{'id': 'cfo_agent',
                                  'label': 'CFO Agent',
                                  'influence': 0.25,
                                  'messages_sent': 3},
                                 {'id': 'investor',
                                  'label': 'Climate Investor',
                                  'influence': 0.25,
                                  'messages_sent': 3},
                                 {'id': 'policy_expert',
                                  'label': 'Policy Expert',
                                  'influence': 0.25,
                                  'messages_sent': 3},
                                 {'id': 'scientist',
                                  'label': 'Environmental Scientist',
                                  'influence': 0.25,
                                  'messages_sent': 3}],
                       'edges': [{'source': 'cfo_agent',
                                  'target': 'investor',
                                  'weight': 3,
                                  'kind': 'messages'},
                                 {'source': 'investor',
                                  'target': 'policy_expert',
                                  'weight': 3,
                                  'kind': 'messages'},
                                 {'source': 'policy_expert',
                                  'target': 'scientist',
                                  'weight': 3,
                                  'kind': 'messages'},
                                 {'source': 'scientist',
                                  'target': 'cfo_agent',
                                  'weight': 3,
                                  'kind': 'messages'}]},
 'warnings': ['sentiment values in this example are illustrative, not LLM output'],
 'errors': []}
