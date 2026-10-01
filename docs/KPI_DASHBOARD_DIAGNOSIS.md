# KPI dashboard diagnosis — v1.5

KPI dashboards were the weakest archetype of v1.4 (development 79.8, holdout v2 71.6) and produced
the strongest scorer–human disagreement of round r2. r2 is development data for v1.5 (it was marked
`used_for_calibration` before this study); nothing here is independent evidence for v1.5.

## The three r2 pairs

Scores by the v1.4 scorer (as recorded in r2's `key.json`) and by the corrected v1.5 metric.
All six renders use the `kpi_grid` layout.

| pair | deck / slide | KPIs | v1.3.3 render | v1.4 render | human | v1.4 scorer (old / new) | v1.5 scorer (old / new) |
|---|---|---|---|---|---|---|---|
| p032 | V05 / v025 | 3, strip | thin strip at the top, 8 pt labels, separators to the foot | 3 cards, centred | **v1.4** | 37.5 / 61.2 | 37.5 / 98.3 |
| p033 | V14 / v084 | 4, `grid` style | 2×2 tiles, small labels | 2×2 tiles, larger type, centred | v1.3.3 | 97.6 / 98.5 | ≈ equal (gap < 1) |
| p034 | V02 / v008 | 4, strip | thin strip at the top, separators to the foot | 4 cards, centred | **v1.4** | **89.7 / 63.5** (−26.2) | 38.5 / 98.9 |

Attribution of the v1.4 scores (points lost):

| render | utilization (observed → penalty) | empty | ink | offcentre |
|---|---|---|---|---|
| p034 v1.3.3 | 0.861 → 0 | 0.394 → −5.1 | −2.2 | −3.0 |
| p034 v1.4 | **0.225 → −33.3** | 0.404 → −2.1 | −1.1 | — |
| p032 v1.3.3 | 0.170 → −11.7 | **0.769 → −44.4** | −2.5 | −3.9 |
| p032 v1.4 | **0.211 → −35.0** | 0.404 → −2.1 | −1.8 | — |

## Which metric caused the −26.2 disagreement, and why

**`utilization`** — and the cause is in the measurement, not the expectation:

1. **Separators were read as content.** The v1.3.3 strip draws thin vertical separators from the
   figures down to the foot of the zone. Each one marks a column of cells as "ink", so the content
   bounding box covered 86% of the body: a thin strip at the top looked like a full slide (p034,
   89.7). In p032 the same pattern left a large empty rectangle beside the separators, so the old
   render was penalised there — the metric was inconsistent between two near-identical slides.
2. **Cards were invisible.** The v1.4 cards are light panels (`surface`, #F4F6F8). The ink
   threshold ignores light fills, so only the text inside the cards counted: a centred row of cards
   measured as a strip of text (utilization 0.21–0.23).

Pattern check on all development KPI dashboards (battery + regression, 9 slides): every v1.4 card
row lost 33–35 points on `utilization` for reason 2; no other archetype draws light panels as its
main structure except process step headers and org-chart nodes (small effect, below).

## Engine or scorer?

| recurring issue | slide visually bad? | metric wrong? | fix |
|---|---|---|---|
| strip of small figures under the headline, empty below (v1.3.3) | **yes** | no (but separators hid it on p034) | engine fixed in v1.4 (cards) |
| separators extend the "used" area through empty space | — | **yes** | v1.5 occupancy: isolated vertical lines through empty cells do not count |
| light card panels not counted as occupied | — | **yes** | v1.5 occupancy: visible panels (≠ page colour) count as occupied, not as ink |
| delta "0 pts" in neutral grey on the card: 2.8:1 (LOW_CONTRAST error in holdout v2, p032's slide) | **yes** | no | v1.5 engine: every text colour on a card is made legible against the card fill |
| 5+ figures squeezed into one row | potentially | no | v1.5 engine: one row while every figure stays legible, else rows of 3 (5 → 3 + 2, centred) |
| card height independent of content | minor | no | v1.5 engine: height from content (+ notes), bounded |

The metric change is a **measurement correction** (`qa/composition.py:_occupancy`), not a profile
change. Its effect on all r2 renders (re-measured; r2 is development data): directional agreement
with the human 33/34 → 35/35; no slide lost more than 3 points; slides that gained > 3: the four
KPI-card dashboards (+27 to +37), six process slides (+3 to +8, step headers are panels), one org
chart (+13). Regression suite: no regression, KPI dashboards 79.8 → 98.6.

## The profile question (left open on purpose)

With the corrected measurement, a centred row of KPI cards occupies exactly 50% of the body band —
the lower edge of the provisional v1.4 range (0.50–1.0). Under the original v1.3.3 range
(0.70–1.0) the same slides would score ≈ 74. One r2 vote (p033, a 2×2 grid) went the other way and
the r2 evidence is 2/3 from one rater. Therefore the kpi_dashboard profile **stays provisional and
unchanged** in v1.5; round r3 includes KPI-dashboard pairs to test it. No rule was added for any
specific slide or pair.
