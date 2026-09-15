# Discussion Analytics Report

*Generated on: 2026-09-15 16:08:24*

## Discussion Overview

- **Discussion ID:** test-run-001
- **Topic:** Should developed countries increase climate finance?
- **Number of Agents:** 4
- **Number of Rounds:** 3

## Opinion Dynamics

### Agent Stance Trajectories

**Climate Investor** (`investor`):
  Round 0: +1.000 → Round 1: -1.000 (Δ-2.000) → Round 2: +0.000 (Δ+1.000)

**Policy Expert** (`policy_expert`):
  Round 0: +1.000 → Round 1: +1.000 (Δ+0.000) → Round 2: +1.000 (Δ+0.000)

**Environmental Scientist** (`scientist`):
  Round 0: +1.000 → Round 1: +1.000 (Δ+0.000) → Round 2: +1.000 (Δ+0.000)

**CFO Agent** (`cfo_agent`):
  Round 0: +0.000 → Round 1: -1.000 (Δ-1.000) → Round 2: +0.000 (Δ+1.000)


## Agreement / Disagreement Analysis

### Agreement Scores by Round

| Round | Agreement Score | Status | Valid Agents |
|-------|-----------------|--------|--------------|
| 0 | 0.750 | ok | 4 |
| 1 | 0.333 | ok | 4 |
| 2 | 0.667 | ok | 4 |

### Interpretation

- **Agreement Score Range:** 0.0 (maximum disagreement) to 1.0 (maximum agreement)
- **Score Interpretation:** Higher scores indicate greater alignment among agents' stances
- **Score Calculation:** Based on mean pairwise differences in agent stances

## Influence Analysis

### Influence Scores

| Agent ID | Influence Score | Status | Messages Sent |
|----------|-----------------|--------|---------------|
| cfo_agent | 0.250 | ok | 3 |
| investor | 0.250 | ok | 3 |
| policy_expert | 0.250 | ok | 3 |
| scientist | 0.250 | ok | 3 |

### Interpretation

- **Influence Score Range:** 0.0 to 1.0 (normalized so sum of all scores = 1.0)
- **Score Interpretation:** Higher scores indicate greater estimated influence on other agents' stance changes
- **Methodology:** Correlation-based measurement of stance convergence toward agents who spoke in previous rounds
- **Important Note:** This measures statistical association, not causation

## Sentiment Analysis

### Sentiment Distribution

- **Total Messages Analyzed:** 12
- **Positive:** 0 messages (0.0%)
- **Negative:** 0 messages (0.0%)
- **Neutral:** 12 messages (100.0%)

### Sample Message Sentiments

| Round | Agent | Sentiment | Polarity | Summary |
|-------|-------|-----------|----------|---------|
| 0 | Climate Investor | neutral | +0.00 | Message content analyzed. |
| 0 | Policy Expert | neutral | +0.00 | Message content analyzed. |
| 0 | Environmental Scientist | neutral | +0.00 | Message content analyzed. |
| 0 | CFO Agent | neutral | +0.00 | Message content analyzed. |
| 1 | Climate Investor | neutral | +0.00 | Message content analyzed. |

## Key Findings

- **Opinion Stability:** Agents showed minimal stance changes throughout the discussion
- **Moderate Agreement:** Showed partial alignment with some convergence (avg score: 0.583)
- **Most Influential Agent:** cfo_agent (influence score: 0.250)
- **Neutral Tone:** All expressions in the discussion were neutral in sentiment
