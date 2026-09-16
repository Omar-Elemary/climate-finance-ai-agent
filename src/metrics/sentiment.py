"""
Week 4 — Sentiment Analytics.

For every message in a Week 3 discussion, computes:
- sentiment: positive / negative / neutral (the message's TONE, separate
  from the agent's stance/opinion on the topic)
- polarity: a numeric score from -1.0 (very negative tone) to +1.0
  (very positive tone)
- summary: a short one-sentence summary of what the message said

Uses an LLM call (not a lexicon library like VADER/TextBlob) because:
- it needs to also produce a short summary in the same call (the task
  explicitly asks for "sentiment + summaries")
- climate-finance language is domain-specific and nuanced; keyword-based
  lexicons often misclassify financial/technical phrasing
"""

from dotenv import load_dotenv
load_dotenv()

import os
# Force a model known to reliably follow structured-output instructions.
# Some free models (e.g. liquid/lfm-2.5-2.6b:free) have been observed to
# literally copy placeholder text from the prompt instead of following
# it — forcing a known-reliable model avoids that failure mode.
os.environ["LLM_MODEL"] = "inclusionai/ling-3.0-flash-fin:free"

import logging
import re

from src.llm import get_provider
from src.persistence import FilePersistence

logger = logging.getLogger(__name__)


def _clean_message_content(content: str) -> str:
    """
    Strip hallucinated <tool_call>...</tool_call> boilerplate that
    Agent.respond() sometimes emits as literal text (a known, documented
    limitation from Week 3 — respond() describes tools to the model but
    has no real function-calling execution loop). Without this cleanup,
    sentiment analysis judges the tone of raw tool-call syntax instead
    of the agent's actual expressed intent.

    If stripping the tool_call block leaves nothing meaningful behind,
    the original content is kept as a fallback (better to analyze
    something than nothing).
    """
    if "<tool_call>" not in content:
        return content

    before_tool_call = content.split("<tool_call>")[0].strip()
    return before_tool_call if len(before_tool_call) >= 15 else content

SENTIMENT_PROMPT_TEMPLATE = (
    "Analyze the TONE of the following message (not its stance/opinion on "
    "the topic — just how positive, negative, or neutral it SOUNDS).\n\n"
    "MESSAGE:\n{content}\n\n"
    "Respond in EXACTLY this format, nothing else:\n"
    "SENTIMENT: <positive|negative|neutral> (<a polarity score from -1.0 to 1.0>)\n"
    "SUMMARY: <one short sentence summarizing what the message said>\n\n"
    "Example:\n"
    "SENTIMENT: positive (0.6)\n"
    "SUMMARY: The agent expressed strong support for increased funding."
)

_SENTIMENT_PATTERN = re.compile(
    r"SENTIMENT:\s*(positive|negative|neutral)\s*\(([-0-9.]+)\)",
    re.IGNORECASE,
)
_SUMMARY_PATTERN = re.compile(r"SUMMARY:\s*(.+)", re.IGNORECASE)


def analyze_message_sentiment(llm, content: str) -> dict:
    """
    Analyze a single message's tone and produce a short summary.

    Returns:
        {"sentiment": "positive"|"negative"|"neutral", "polarity": float,
         "summary": str}

    Falls back to a safe neutral result if the LLM call fails or the
    response doesn't match the expected format — this must never crash
    the analytics pipeline over one malformed message.
    """
    messages = [
        {"role": "system", "content": "You are a precise tone/sentiment classifier."},
        {"role": "user", "content": SENTIMENT_PROMPT_TEMPLATE.format(content=content)},
    ]

    try:
        response = llm.generate(messages)
        text = response.text.strip()
    except Exception as e:
        logger.error("Sentiment LLM call failed: %s", e)
        return {"sentiment": "neutral", "polarity": 0.0, "summary": ""}

    sentiment_match = _SENTIMENT_PATTERN.search(text)
    summary_match = _SUMMARY_PATTERN.search(text)

    if not sentiment_match:
        logger.warning("Sentiment response didn't match expected format: %r", text)
        return {"sentiment": "neutral", "polarity": 0.0, "summary": text[:150]}

    label = sentiment_match.group(1).lower()
    try:
        polarity = float(sentiment_match.group(2))
    except ValueError:
        polarity = 0.0

    summary = summary_match.group(1).strip() if summary_match else ""

    return {"sentiment": label, "polarity": polarity, "summary": summary}


def get_sentiment_series(run_id: str, llm=None) -> list[dict]:
    """
    Compute sentiment + summary for every message in a discussion run.

    Returns a list of dicts, one per message:
        [
          {"message_id": "m1", "agent_id": "cfo_agent", "round": 1,
           "sentiment": "negative", "polarity": -0.4,
           "summary": "The CFO expressed skepticism about ROI.",
           "content": "..."},
          ...
        ]

    This satisfies the acceptance test: "Every message row in the
    discussion history has an associated sentiment value."
    """
    store = FilePersistence()
    state = store.load(run_id)
    if state is None:
        raise ValueError(f"No discussion found for run_id: {run_id}")

    llm = llm or get_provider()

    rows = []
    for message in state.messages:
        cleaned_content = _clean_message_content(message.content)
        result = analyze_message_sentiment(llm, cleaned_content)
        rows.append({
            "message_id": message.message_id,
            "agent_id": message.agent_id,
            "agent_name": message.agent_name,
            "round": message.round,
            "sentiment": result["sentiment"],
            "polarity": result["polarity"],
            "summary": result["summary"],
            "content": message.content,
        })
        logger.info(
            "Sentiment for %s (round %d): %s (%.2f)",
            message.agent_id, message.round, result["sentiment"], result["polarity"],
        )

    return rows


def get_opinion_sentiment_series(run_id: str, llm=None) -> list[dict]:
    """
    Compute sentiment + summary for every agent's OPINION (the actual
    grounded position from generate_opinion()), not the short turn-taking
    message from respond(). Opinions carry the agent's real stance and
    tone (e.g. "not merely a moral imperative but a necessity"), so this
    is where meaningful sentiment variation actually shows up.

    Returns a list of dicts, one per opinion record:
        [
          {"agent_id": "cfo_agent", "round": 1,
           "sentiment": "positive", "polarity": 0.4,
           "summary": "...", "opinion": "..."},
          ...
        ]
    """
    store = FilePersistence()
    state = store.load(run_id)
    if state is None:
        raise ValueError(f"No discussion found for run_id: {run_id}")

    llm = llm or get_provider()

    rows = []
    for agent_id, records in state.opinions.items():
        for record in records:
            result = analyze_message_sentiment(llm, record.opinion)
            rows.append({
                "agent_id": agent_id,
                "agent_name": record.agent_name,
                "round": record.round,
                "sentiment": result["sentiment"],
                "polarity": result["polarity"],
                "summary": result["summary"],
                "opinion": record.opinion,
            })
            logger.info(
                "Opinion sentiment for %s (round %d): %s (%.2f)",
                agent_id, record.round, result["sentiment"], result["polarity"],
            )

    rows.sort(key=lambda r: (r["agent_id"], r["round"]))
    return rows


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else "sample-week4-run"

    print(f"Analyzing MESSAGE sentiment for run '{run_id}'...\n")
    message_series = get_sentiment_series(run_id)
    for row in message_series:
        print(f"[Round {row['round']}] {row['agent_name']}")
        print(f"  Sentiment: {row['sentiment']} ({row['polarity']:+.2f})")
        print(f"  Summary:   {row['summary']}")
        print()

    print("=" * 70)
    print(f"Analyzing OPINION sentiment for run '{run_id}'...\n")
    opinion_series = get_opinion_sentiment_series(run_id)
    for row in opinion_series:
        print(f"[Round {row['round']}] {row['agent_name']}")
        print(f"  Sentiment: {row['sentiment']} ({row['polarity']:+.2f})")
        print(f"  Summary:   {row['summary']}")
        print()