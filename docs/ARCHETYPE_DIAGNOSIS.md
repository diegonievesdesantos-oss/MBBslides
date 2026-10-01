# Archetype diagnosis — v1.4

For every weak archetype the question was the same: **is the slide bad, or is the metric wrong?**
Method: render the archetype's contact sheet (`archetype_sheets/`, worst slide first), read the
penalty attribution (`archetype_diagnostics.md`), compare with accepted development slides, and only
then decide whether to fix the metric, the profile, the component, the content adaptation or the
candidate selection. Everything here was done on development data (regression suite + archetype
battery); the sealed holdout v2 was not opened.

## Before / after

Development battery, v1.3.3 engine and scorer (`evals/results/history/v1.3.3_battery_report.md`)
vs the full v1.4 regression suite (battery + the ten stress decks, v1.4 engine and scorer). Not
strictly like-for-like: the suite grew and some slides were reclassified (below). The clean
comparison is the 2×2 on the sealed holdout at the end.

| archetype | v1.3.3 mean (min) | v1.4 mean (min) | dominant v1.3.3 penalty | diagnosis | what changed |
|---|---|---|---|---|---|
| text_exhibit | 30.8 (20.5) | 85.1 (53.4) | utilization −43 | **engine** (+ classification) | text was drawn as side commentary: 8–9 pt, top-left, empty slide; bullets were silently dropped when the slide also had commentary. New `text` role and `tc.text_exhibit` (argument / list / narrative / quote); one short argument and short quotes are statements |
| process | 42.1 (36.4) | 81.0 (55.1) | utilization −34, empty −19 | **engine**, then **profile (provisional)** | steps were a thin strip of small type under the headline; impact row pinned to the zone's foot. Adaptive scale, optical centring, numerals for sparse flows, title-only steps may wrap; then process judged as a band (like timeline) |
| comparison | 48.2 (36.4) | 84.6 (76.4) | utilization −27, offcentre −12 | **engine**, then **profile (provisional)** | each column drawn independently, small, top-anchored. Columns now share one scale and one top edge, centred; then comparison judged as text columns (like text_exhibit) |
| kpi_dashboard | 61.4 (36.8) | 79.8 (61.6) | utilization −21, empty −13 | **engine**, then **profile (provisional)** | a strip of small figures under the headline. KPI cards on the optical centre; then a set of figures allowed air like a KPI hero. Still the weakest archetype |
| roadmap | 65.3 (41.1) | 93.5 (80.1) | utilization −28 | **engine** | gantt rows capped at 0.62 in from the top. Rows sized by their number, larger type when rows are tall, plan centred |
| kpi_hero | 73.9 (50.5) | 97.4 (94.2) | empty −20 | **engine** | hero figure stuck top-left. Group on the optical centre; centred when there is no note |
| architecture | 90.1 (47.3) | 91.4 (49.4) | utilization (one slide) | **classification**, profile unchanged | the outlier was a single-row flow (A → B → C → D): a sequence, now a process. Layered architectures fill the band by construction; the brief's question "do utilization / dead space weigh too much for diagrams?" — not for layered diagrams (all ≥ 85); for one-row flows the process band logic applies |
| hierarchy | 91.0 (53.1) | 93.2 (67.6) | utilization (small org chart) | **engine** | small org charts sit on the optical centre with larger type |
| waterfall / chart | 88.9 / 96.7 | 90.6 / 94.2 | proof | **metric** | "€1.2bn" was not proven by "1,210" in €M; "€61,000,000" not by "61" — scaled proof added (found by the battery and the robustness suite). Derived numbers (sums, ratios) remain a known limitation |
| (all) | | | ratio | **metric** | "4.5 days", "2 min" were counted as text competing with the headline; figures with short units are figures |

Metric fixes changed the measurement, not the targets. Profile changes are documented in
`evals/profile_changes.md`, marked provisional, and tested by human round r2.

## What remains weak (v1.4)

- **kpi_dashboard** (79.8 on development, 71.6 on the holdout): cards with 3–5 bare figures still
  read as a thin band; one holdout slide has a hard LOW_CONTRAST error on the card. v1.5.
- **process** with title-only steps (chevrons) and very short labels: an honest "thin content"
  signal (~55). Not hidden.
- **text_exhibit** below the provisional mean floor on a few slides (a two-quote slide, a short
  paragraph): thin content again.
- **PROOF_NOT_VISIBLE** dominates the low tail on the holdout: derived numbers.

## Engine vs scorer on the sealed holdout (the clean comparison)

158 slides of `evals/holdout/v2`, rendered by both engines, each scored by both scorers
(slide mean / macro archetype / P10):

| | v1.3.3 scorer (frozen before v1.4) | v1.4 scorer |
|---|---|---|
| v1.3.3 engine (a2f4dbc) | 77.3 / 78.9 / 36.5 | 77.9 / 79.6 / 40.0 |
| v1.4 engine (430176d) | 87.1 / 87.7 / 53.6 | 91.4 / 91.8 / 73.7 |

Under the scorer that existed before any v1.4 work, the engine change alone adds ~10 points of
mean and 17 of P10 on decks it was never tuned on. The remaining 20 points of P10 come from the
provisional profile changes — exactly what only human votes can confirm or reject.
