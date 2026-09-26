"""Report Generator (Week 4).

Creates human-readable Markdown reports from analytics results.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def generate_report(
    analytics_results: Dict[str, Any],
    discussion_id: str = "unknown",
    topic: str = "unknown",
    output_path: str = "reports/discussion_report.md"
) -> str:
    """Generate a human-readable Markdown report from analytics results.

    Args:
        analytics_results: Dictionary containing all four metric categories
                          from the unified analytics engine
        discussion_id: ID of the discussion being reported on
        topic: Topic of the discussion
        output_path: Path where the Markdown report should be saved

    Returns:
        Path to the generated report file

    The report includes:
    - Discussion information (ID, topic, agent count, round count)
    - Opinion change analysis (trajectories, important changes, observations)
    - Agreement/disagreement analysis (scores by round, trends)
    - Influence analysis (scores, highest/lowest influence)
    - Sentiment analysis (distribution, trends, message summaries)
    """
    logger.info(f"Generating report for discussion {discussion_id}")

    # Extract data from analytics results
    opinion_change_data = analytics_results.get('opinion_change', {})
    agreement_data = analytics_results.get('agreement', [])
    influence_data = analytics_results.get('influence', {})
    sentiment_data = analytics_results.get('sentiment', [])

    # Generate report content
    report_lines = []

    # Header
    report_lines.append("# Discussion Analytics Report")
    report_lines.append("")
    report_lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report_lines.append("")

    # Discussion Overview
    report_lines.append("## Discussion Overview")
    report_lines.append("")
    report_lines.append(f"- **Discussion ID:** {discussion_id}")
    report_lines.append(f"- **Topic:** {topic}")

    # Extract agent and round information
    agent_count = _extract_agent_count(opinion_change_data, influence_data)
    round_count = _extract_round_count(opinion_change_data, agreement_data)

    report_lines.append(f"- **Number of Agents:** {agent_count}")
    report_lines.append(f"- **Number of Rounds:** {round_count}")
    report_lines.append("")

    # Opinion Change Section
    report_lines.append("## Opinion Dynamics")
    report_lines.append("")
    report_lines.append(_format_opinion_change_section(opinion_change_data))
    report_lines.append("")

    # Agreement/Disagreement Section
    report_lines.append("## Agreement / Disagreement Analysis")
    report_lines.append("")
    report_lines.append(_format_agreement_section(agreement_data))
    report_lines.append("")

    # Influence Section
    report_lines.append("## Influence Analysis")
    report_lines.append("")
    report_lines.append(_format_influence_section(influence_data))
    report_lines.append("")

    # Sentiment Section
    report_lines.append("## Sentiment Analysis")
    report_lines.append("")
    report_lines.append(_format_sentiment_section(sentiment_data))
    report_lines.append("")

    # Key Findings Section
    report_lines.append("## Key Findings")
    report_lines.append("")
    report_lines.append(_generate_key_findings(
        opinion_change_data, agreement_data, influence_data, sentiment_data
    ))
    report_lines.append("")

    # Join all lines
    report_content = "\n".join(report_lines)

    # Save to file
    import os
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logger.info(f"Report generated and saved to {output_path}")
    return output_path


def _extract_agent_count(opinion_change_data: Dict, influence_data: Dict) -> int:
    """Extract the number of unique agents from the data."""
    agents = set()

    # From opinion change trajectories
    if isinstance(opinion_change_data, dict):
        if 'trajectories' in opinion_change_data:
            agents.update(opinion_change_data['trajectories'].keys())
        else:
            agents.update(opinion_change_data.keys())

    # From influence data
    if isinstance(influence_data, dict):
        agents.update(influence_data.keys())

    return len(agents)


def _extract_round_count(opinion_change_data: Dict, agreement_data: List) -> int:
    """Extract the number of rounds from the data."""
    rounds = set()

    # From opinion change data
    if isinstance(opinion_change_data, dict):
        if 'trajectories' in opinion_change_data:
            for agent_trajectories in opinion_change_data['trajectories'].values():
                if isinstance(agent_trajectories, list):
                    for point in agent_trajectories:
                        if isinstance(point, dict) and 'round' in point:
                            rounds.add(point['round'])
        else:
            for agent_data in opinion_change_data.values():
                if isinstance(agent_data, list):
                    for point in agent_data:
                        if isinstance(point, dict) and 'round' in point:
                            rounds.add(point['round'])

    # From agreement data
    if isinstance(agreement_data, list):
        for round_data in agreement_data:
            if isinstance(round_data, dict) and 'round' in round_data:
                rounds.add(round_data['round'])

    return len(rounds) if rounds else 0


def _format_opinion_change_section(opinion_change_data: Dict) -> str:
    """Format the opinion change section of the report."""
    if not opinion_change_data:
        return "*No opinion change data available*"

    lines = []

    # Handle different data formats
    trajectories = {}
    summaries = {}

    if isinstance(opinion_change_data, dict):
        if 'trajectories' in opinion_change_data:
            trajectories = opinion_change_data['trajectories']
        else:
            # Assume it might be agent_id -> list format
            trajectories = opinion_change_data

        if 'summaries' in opinion_change_data:
            summaries = opinion_change_data['summaries']

    if not trajectories:
        return "*No opinion trajectory data available*"

    lines.append("### Agent Stance Trajectories")
    lines.append("")

    # Show trajectory for each agent
    for agent_id, trajectory in trajectories.items():
        if not isinstance(trajectory, list) or not trajectory:
            continue

        # Get agent name from first point if available
        agent_name = agent_id
        if trajectory and isinstance(trajectory[0], dict):
            agent_name = trajectory[0].get('agent_name', agent_id)

        lines.append(f"**{agent_name}** (`{agent_id}`):")

        # Show stance values for each round
        stance_values = []
        for point in trajectory:
            if isinstance(point, dict):
                round_num = point.get('round', '?')
                stance = point.get('stance')
                change = point.get('change')
                if stance is not None:
                    stance_str = f"{stance:+.3f}"
                    if change is not None:
                        stance_str += f" (Δ{change:+.3f})"
                    stance_values.append(f"Round {round_num}: {stance_str}")
                else:
                    stance_values.append(f"Round {round_num}: No data")

        if stance_values:
            lines.append("  " + " → ".join(stance_values))
        lines.append("")

    # Add summary statistics if available
    if summaries:
        lines.append("### Movement Summary")
        lines.append("")

        for agent_id, summary in summaries.items():
            if not isinstance(summary, dict):
                continue

            agent_name = summary.get('agent_name', agent_id)
            initial = summary.get('initial_stance')
            final = summary.get('final_stance')
            total_movement = summary.get('total_movement')
            direction = summary.get('direction', 'insufficient')

            if initial is not None and final is not None:
                lines.append(f"- **{agent_name}**: {initial:+.3f} → {final:+.3f} "
                           f"(total: {total_movement:+.3f}, direction: {direction})")
            else:
                lines.append(f"- **{agent_name}**: Insufficient data for trajectory analysis")

    return "\n".join(lines) if lines else "*No opinion change data to display*"


def _format_agreement_section(agreement_data: List) -> str:
    """Format the agreement/disagreement section of the report."""
    if not agreement_data:
        return "*No agreement/disagreement data available*"

    lines = []

    lines.append("### Agreement Scores by Round")
    lines.append("")
    lines.append("| Round | Agreement Score | Status | Valid Agents |")
    lines.append("|-------|-----------------|--------|--------------|")

    for round_data in agreement_data:
        if not isinstance(round_data, dict):
            continue

        round_num = round_data.get('round', '?')
        score = round_data.get('agreement_score')
        status = round_data.get('status', 'unknown')
        n_valid = round_data.get('n_valid', 0)

        score_str = f"{score:.3f}" if score is not None else "N/A"
        lines.append(f"| {round_num} | {score_str} | {status} | {n_valid} |")

    # Add interpretation
    lines.append("")
    lines.append("### Interpretation")
    lines.append("")
    lines.append("- **Agreement Score Range:** 0.0 (maximum disagreement) to 1.0 (maximum agreement)")
    lines.append("- **Score Interpretation:** Higher scores indicate greater alignment among agents' stances")
    lines.append("- **Score Calculation:** Based on mean pairwise differences in agent stances")

    return "\n".join(lines)


def _format_influence_section(influence_data: Dict) -> str:
    """Format the influence section of the report."""
    if not influence_data:
        return "*No influence data available*"

    lines = []

    lines.append("### Influence Scores")
    lines.append("")
    lines.append("| Agent ID | Influence Score | Status | Messages Sent |")
    lines.append("|----------|-----------------|--------|---------------|")

    # Sort agents by influence score (descending)
    sorted_agents = []
    if isinstance(influence_data, dict):
        for agent_id, influence_obj in influence_data.items():
            if isinstance(influence_obj, dict):
                sorted_agents.append((agent_id, influence_obj))

    sorted_agents.sort(key=lambda x: x[1].get('influence_score') or 0.0, reverse=True)

    for agent_id, influence_obj in sorted_agents:
        score = influence_obj.get('influence_score')
        status = influence_obj.get('status', 'unknown')
        messages = influence_obj.get('messages_sent', 0)

        score_str = f"{score:.3f}" if score is not None else "N/A"
        lines.append(f"| {agent_id} | {score_str} | {status} | {messages} |")

    # Add interpretation
    lines.append("")
    lines.append("### Interpretation")
    lines.append("")
    lines.append("- **Influence Score Range:** 0.0 to 1.0 (normalized so sum of all scores = 1.0)")
    lines.append("- **Score Interpretation:** Higher scores indicate greater estimated influence on other agents' stance changes")
    lines.append("- **Methodology:** Correlation-based measurement of stance convergence toward agents who spoke in previous rounds")
    lines.append("- **Important Note:** This measures statistical association, not causation")

    return "\n".join(lines)


def _format_sentiment_section(sentiment_data: List) -> str:
    """Format the sentiment section of the report."""
    if not sentiment_data:
        return "*No sentiment data available*"

    lines = []

    # Count sentiment distribution
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    total_messages = len(sentiment_data)

    if isinstance(sentiment_data, list):
        for msg in sentiment_data:
            if isinstance(msg, dict):
                sentiment = msg.get('sentiment', 'neutral')
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1

    lines.append("### Sentiment Distribution")
    lines.append("")
    lines.append(f"- **Total Messages Analyzed:** {total_messages}")
    for sentiment, count in sentiment_counts.items():
        percentage = (count / total_messages * 100) if total_messages > 0 else 0
        lines.append(f"- **{sentiment.capitalize()}:** {count} messages ({percentage:.1f}%)")

    lines.append("")
    lines.append("### Sample Message Sentiments")
    lines.append("")
    lines.append("| Round | Agent | Sentiment | Polarity | Summary |")
    lines.append("|-------|-------|-----------|----------|---------|")

    # Show first few messages as examples
    sample_count = min(5, len(sentiment_data)) if isinstance(sentiment_data, list) else 0
    if isinstance(sentiment_data, list):
        for i in range(sample_count):
            msg = sentiment_data[i]
            if isinstance(msg, dict):
                round_num = msg.get('round', '?')
                agent_name = msg.get('agent_name', 'Unknown')
                sentiment = msg.get('sentiment', 'neutral')
                polarity = msg.get('polarity', 0.0)
                summary = msg.get('summary', '')
                # Truncate summary if too long
                if len(summary) > 50:
                    summary = summary[:47] + "..."

                polarity_str = f"{polarity:+.2f}"
                lines.append(f"| {round_num} | {agent_name} | {sentiment} | {polarity_str} | {summary} |")

    if sample_count == 0:
        lines.append("| N/A | N/A | N/A | N/A | No sentiment data |")

    return "\n".join(lines)


def _generate_key_findings(
    opinion_change_data: Dict,
    agreement_data: List,
    influence_data: Dict,
    sentiment_data: List
) -> str:
    """Generate key findings section based on all analytics data."""
    lines = []

    findings = []

    # Opinion change findings
    if opinion_change_data:
        # Check for significant movements
        significant_movers = []
        if isinstance(opinion_change_data, dict) and 'summaries' in opinion_change_data:
            for agent_id, summary in opinion_change_data['summaries'].items():
                if isinstance(summary, dict):
                    total_movement = summary.get('total_movement')
                    if total_movement is not None and abs(total_movement) > 0.3:  # Arbitrary threshold
                        agent_name = summary.get('agent_name', agent_id)
                        direction = "increased" if total_movement > 0 else "decreased"
                        significant_movers.append(f"{agent_name} ({direction} stance by {abs(total_movement):.3f})")

        if significant_movers:
            findings.append(f"**Significant Opinion Shifts:** {', '.join(significant_movers)}")
        else:
            findings.append("**Opinion Stability:** Agents showed minimal stance changes throughout the discussion")

    # Agreement findings
    if agreement_data and isinstance(agreement_data, list):
        scores = [r.get('agreement_score') for r in agreement_data if isinstance(r, dict) and r.get('agreement_score') is not None]
        if scores:
            avg_agreement = sum(scores) / len(scores)
            if avg_agreement > 0.7:
                findings.append(f"**High Agreement:** Maintained strong alignment throughout (avg score: {avg_agreement:.3f})")
            elif avg_agreement < 0.3:
                findings.append(f"**Persistent Disagreement:** Agents remained largely divided (avg score: {avg_agreement:.3f})")
            else:
                findings.append(f"**Moderate Agreement:** Showed partial alignment with some convergence (avg score: {avg_agreement:.3f})")

            # Check for trends
            if len(scores) >= 3:
                if scores[-1] > scores[0] + 0.1:
                    findings.append("**Increasing Alignment:** Group agreement strengthened over time")
                elif scores[0] > scores[-1] + 0.1:
                    findings.append("**Decreasing Alignment:** Group agreement weakened over time")

    # Influence findings
    if influence_data and isinstance(influence_data, dict):
        # Find most influential agent
        max_influence = None
        max_agent = None
        for agent_id, influence_obj in influence_data.items():
            if isinstance(influence_obj, dict):
                score = influence_obj.get('influence_score')
                if score is not None and (max_influence is None or score > max_influence):
                    max_influence = score
                    max_agent = influence_obj.get('agent_name', agent_id)

        if max_agent and max_influence is not None:
            findings.append(f"**Most Influential Agent:** {max_agent} (influence score: {max_influence:.3f})")

    # Sentiment findings
    if sentiment_data and isinstance(sentiment_data, list):
        positive_count = sum(1 for msg in sentiment_data if isinstance(msg, dict) and msg.get('sentiment') == 'positive')
        negative_count = sum(1 for msg in sentiment_data if isinstance(msg, dict) and msg.get('sentiment') == 'negative')
        neutral_count = sum(1 for msg in sentiment_data if isinstance(msg, dict) and msg.get('sentiment') == 'neutral')

        if positive_count > negative_count * 1.5 and positive_count > 0:
            findings.append("**Positive Tone:** Discussion featured predominantly constructive and supportive language")
        elif negative_count > positive_count * 1.5 and negative_count > 0:
            findings.append("**Critical Tone:** Discussion featured predominantly skeptical or concerned language")
        elif positive_count == 0 and negative_count == 0:
            findings.append("**Neutral Tone:** All expressions in the discussion were neutral in sentiment")
        else:
            findings.append("**Balanced Tone:** Discussion maintained a mix of positive, negative, and neutral expressions")

    # If no specific findings, provide general ones
    if not findings:
        findings.append("**Discussion Completed:** All analytic dimensions were successfully computed")
        findings.append("**Data Quality:** Sufficient data was available for meaningful analysis across all dimensions")

    # Format findings as bullet points
    for finding in findings:
        lines.append(f"- {finding}")

    return "\n".join(lines) if lines else "- No significant findings identified"