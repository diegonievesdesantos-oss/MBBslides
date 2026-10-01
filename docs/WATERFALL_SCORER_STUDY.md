# Waterfall scorer blind spot — study (v1.7)

**Data.** Human round r3 (v1.4.0 vs v1.5.0rc1, one expert rater, blind), marked development data
before this study. 12 waterfall pairs: 7 v1.5 wins, 0 v1.4 wins, 5 ties.

**Symptom.** In four pairs the expert preferred v1.5 while the composition scorer gave both renders
≈ 100 (wa07, wa04, wa02, v053).

**Pattern (all four, and wa01, wa03, wa10).** The v1.4 renders of waterfalls with negative
running totals were *numerically wrong*: negative total bars not drawn, bars that do not chain the
bridge arithmetic, labels inside bars or below the axis. Not a matter of taste.

**Root cause — in the scorer's architecture, not in a range.** v1.4's own QA had flagged every
one of them (OFF_SLIDE, OUTSIDE_ZONE, RENDER_TEXT_COLLISION, WATERFALL_NEGATIVE), but composition
fitness measures only layout properties (occupancy, balance, hierarchy, proof). A broken chart with
good proportions scored 100.

**Fix (generic, no slide or archetype exception).** A critical `integrity` metric in every profile
(`archetype_profiles.json`, base, weight 16, range 1–1), observed **only** when the slide has a
*broken* QA finding — content off the slide or outside its zone, overflowing, colliding,
truncated, a placeholder, or a chart that cannot encode its data (WATERFALL_NEGATIVE) — and then
0. An intact slide does not observe it at all, so its score is exactly what it was: a first
version that observed 1 on intact slides diluted every other penalty and lifted the development
regression from 95.1 to 95.5 — score inflation, rejected. `cpe measure` recomputes it with
the CURRENT checks on stored renders. Other QA errors (low contrast, small type, palette) still fail
the QA gate but are not "broken".

| r3, re-measured with the current scorer | before | after |
|---|---|---|
| decisive pairs where scorer agrees with the expert (|gap| ≥ 1) | 5 / 10 | **9 / 10** |
| waterfall decisive pairs agreeing | 2 / 7 | **7 / 7** |
| tied pairs with a score gap ≥ 5 (false positives) | 0 | **0** |

**Rejected variant.** "Any non-authoring QA error → integrity 0" created 5 false positives on
tied pairs: four KPI dashboards whose only defect was low contrast on a small delta, and one
statement whose "spill" was the v1.4 trailing-space false positive fixed in v1.5. The expert tied
all five; the narrower definition is what the evidence supports.

**Remaining miss.** p006 (KPI dashboard): the expert preferred v1.4 by a margin the scorer sees as
0.6 points. One vote; no pattern.

**Development effect.** Regression, examples and robustness slides have no broken findings, so
their scores do not change. The metric exists so that a future broken render can never hide behind
good proportions again.
