# Opinion + Agreement Metrics (Week 4 — Opinion/Agreement scope)

Implements **only**: Opinion Change Analytics + Agreement/Disagreement
Analytics (`src/metrics/`). Out of scope: influence, sentiment, reporting,
visualization, unified engine, Week 5 frontend.

Consume from the future unified engine as:

```python
from src.metrics import calculate_opinion_change, calculate_agreement

result.opinion_change = calculate_opinion_change(history)
result.agreement = calculate_agreement(history)
```

`history` is a Week 3 `DiscussionState`
(`src/orchestration/models.py`) **or** its `to_dict()` plain dict
(e.g. loaded from `data/discussions/*.json` via `FilePersistence`).
No Week 3 code was modified; the modules only read the existing
`opinions` mapping. No new dependencies.

---

## 1. Opinion Trajectory Metric

**Purpose.** Measure how each agent's stance evolves across rounds:
Agent → Round → Stance → Change.

**Input.** Week 3 opinion snapshots (`OpinionRecord`: free-text `opinion`
+ evidence/sources). Week 3 stores **no numeric stance**, and per the
spec ("do not assume information not present") none is invented — stance
is derived deterministically from the text:

1. Count support cues `P` and oppose cues `N` (word-boundary regex,
   case-insensitive; overlaps resolved longest-first). Cue lists live in
   `src/metrics/opinion.py` and are tuned to this repo's climate-finance
   language (bankable/unbankable, taxonomy, guarantees, additionality…).
   Topic action verbs (increase/expand/accelerate) are deliberately
   excluded — everything here is about increasing finance, so they carry
   no signal.
2. Negation flip: a cue with a negator (not/no/never/without/cannot/…)
   within the previous 3 tokens flips polarity
   ("not bankable" → oppose; "no board will approve" → oppose).
3. `stance = (P − N) / (P + N)`; zero cues → `0.0` (neutral, no signal).
4. Conditional dampening: with markers (conditional/only if/however/…)
   and nonzero stance, magnitude × 0.8 (qualified positions).
5. Numeric opinions in [-1, 1] (future Week 3 field) are reused directly;
   out-of-range numerics/bools → invalid.

**Range.** [-1.0, +1.0]: −1 = strongly against the topic as framed,
0 = neutral/no signal, +1 = strongly in favor.

**Change.** `change = current − previous`, only between consecutive round
numbers with both stances valid; first valid round → `None`.

**Output.** `OpinionChangeResult.trajectories: {agent_id: [StancePoint]}`,
each with `agent_id, round, stance, change, status (ok|missing|invalid),
n_cues, n_snapshots`; plus `summaries: {agent_id: AgentTrajectorySummary}`
with `initial/final stance, total_movement (final−initial),
largest_movement (max |change|), direction (up|down|flat|mixed|
insufficient), n_valid_rounds`.

**Missing-data behavior (never invents values).** Empty opinion →
`missing`; invalid round → snapshot skipped with warning; absent
(agent, round) → `missing` point; duplicate snapshots → **last wins**,
count kept in `n_snapshots`; non-consecutive rounds → `change = None`.

**Limitations.** Lexicon scoring is a proxy: sarcasm, wide negation
scope, and implicit/diplomatic positions are missed or compressed toward
0. Fully deterministic (no LLM). If Week 3 gains a numeric stance field,
prefer it.

---

## 2. Agreement Score Metric

**Purpose.** One alignment score per discussion round.

**Method.** Per round: collect valid stances (invalid/missing excluded,
duplicates last-wins) → all unique pairwise `|stance_i − stance_j|` →
mean → normalize by max difference 2 → agreement.

**Formula.**

```
mean_difference = mean(all pairwise absolute stance differences)
agreement       = 1 − (mean_difference / 2), clamped to [0, 1]
```

**Output.** `list[AgreementRound]`: `round, agreement_score,
mean_pairwise_difference, n_agents, n_valid, n_invalid,
status (ok|insufficient_data)`.

**Range/interpretation.** 0–1; 1 = maximum agreement (identical stances),
0 = maximum disagreement (−1 vs +1).

**Edge cases.** 0–1 valid stances → `insufficient_data`, score `None`
(never reports 1.0 for a single agent); rounds with no opinions are not
emitted (no fabrication).

**Limitations.** Agreement is only as good as the stance extraction
above; short/hedged opinions compress toward 0, which inflates agreement.
Pairwise-mean treats all agent pairs equally (no influence weighting —
teammate's scope).
