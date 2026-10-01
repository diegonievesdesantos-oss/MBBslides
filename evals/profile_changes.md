# Archetype profile changes

Every change to `src/cpe/qa/archetype_profiles.json` is recorded here: what changed, why, on which
evidence, and its status. `tests/test_quality.py` checks that every metric marked
`"last_changed": "<version>"` in the profile file has an entry under that version here.

Rules (docs/COMPOSITION_SCORING.md#governance):

- A range changes only after the ENGINE has been fixed and the renders inspected: a low score is
  first a question ("is the slide bad, or is the metric wrong?"), never a reason by itself.
- Evidence is development data only (regression suite, archetype battery, example decks) and human
  A/B votes when they exist. The sealed holdout (`evals/holdout/v2`) is never used.
- A change without human evidence is `provisional`. The next human round samples the affected
  archetypes; if people disagree, the change is reverted or revised in the next version.

---

## 1.5.0

Status changes driven by human round r2 (blind, **one evaluator**, 38 pairs + 2 repeats, v1.3.3 vs
v1.4 engine on the sealed holdout v2 decks). r2 was marked development data
(`rounds/r2/STATUS.json`) in the same change; its blind v1.4 result is preserved in
`rounds/r2/VALIDATION_v1.4.json`. No range below changed.

### process.utilization / process.empty: provisional → human_supported_single_rater
- **Evidence.** Engine: v1.4 adaptive composition (mean 42.1 → 50.5 before any profile change, on the
  battery). Development: 12 process slides in the regression suite. Human: r2 process pairs 8/8
  decisive votes for v1.4, 0 ties.
- **Limitation.** One rater, n = 8. Directional support for the "band" expectation, not
  multi-rater validation. Absolute gates (mean floor 70, 25% below floor) are NOT promoted: they
  measure something else and still need calibration.

### comparison.utilization / comparison.empty: provisional → human_supported_single_rater
- **Evidence.** Engine: joint column composition (48.2 → 66.3 before any profile change). Development:
  11 comparison slides. Human: r2 comparison pairs 7/7 decisive votes for v1.4.
- **Limitation.** One rater, n = 7.

### kpi_dashboard: stays provisional
- **Evidence.** Human: 2/3 for v1.4 (n too small), and the strongest scorer–human disagreement of
  r2 (p034: v1.4 scored 26.2 points lower, the evaluator preferred it). Diagnosis and any change:
  docs/KPI_DASHBOARD_DIAGNOSIS.md.
- **Range unchanged.** After the measurement fix below, a centred row of KPI cards occupies exactly
  50% of the body — the lower edge of the provisional range; under the original 0.70 it would score
  ≈ 74. One rater, 2/3: not enough to decide. Round r3 includes KPI-dashboard pairs.

### Not a range change: occupancy measurement (utilization / empty)
- Visible filled panels (≠ the page colour) count as occupied area; isolated thin vertical lines
  running through empty cells do not. Measurement correction found by the r2 disagreement p034
  (separators made a top strip look full; light cards were invisible). Effect on r2 renders
  (development data): agreement 33/34 → 35/35, no slide −3 or worse. `qa/composition.py:_occupancy`.

## 1.4.0

All three changes are **provisional** — no human votes exist yet. Round r2 samples
process, comparison and kpi_dashboard pairs (old vs new) to test them.

### process.utilization 0.72–1.0 → 0.50–1.0 · process.empty max 0.28 → 0.36

- **Reason.** With few, short steps a process is a horizontal BAND, like a timeline: air above
  and below a centred band is inherent. The real failures — the band glued under the headline, or
  off-balance — stay penalised by `empty` (still bounded) and `offcentre`.
- **Engine first.** v1.3.3 drew steps at fixed size from the top of the zone (10 battery slides:
  mean 42.1, every slide DEAD_SPACE). v1.4 sizes the steps adaptively and centres the block
  (`pptx/adaptive.py`): mean 50.5 before this change, with type already at the hierarchy cap.
  The remaining penalty came almost entirely from `utilization` (−42 points per slide).
- **Evidence.** `evals/regression/cases/209_battery_process.json` (10 slides) contact sheets,
  out/v14/it1–it3 (not committed); precedent: `timeline` (0.35–1.0, empty ≤ 0.5) and
  `kpi_hero`, set in v1.2 for the same reason.
- **Human.** None yet → r2.

### comparison.utilization 0.72–1.0 → 0.55–1.0 · comparison.empty max 0.28 → 0.35

- **Reason.** Comparison columns are text. A text exhibit was already allowed utilization from
  0.55 and empty up to 0.40; comparison asked for chart-like filling. Aligned with text
  (empty kept slightly stricter, balance still weighted 12).
- **Engine first.** v1.3.3 drew each column independently, small and top-anchored (mean 48.2).
  v1.4 composes all columns at one scale and one top edge, centred (`tc.columns`): mean 66.3
  before this change; remaining penalty from `utilization` on columns of 3 short bullets.
- **Evidence.** `208_battery_comparison.json` (10 slides).
- **Human.** None yet → r2.

### kpi_dashboard.utilization 0.70–1.0 → 0.50–1.0 · kpi_dashboard.empty max 0.30 → 0.36

- **Reason.** A set of 3–5 figures shown as KPI cards needs air like a KPI hero; the 0.70 lower
  bound was written for dense grids, which still fill the band and still score ≥ 89.
- **Engine first.** v1.3.3 drew a strip of small figures under the headline (mean 61.4, worst
  36.8). v1.4 draws KPI cards on the optical centre (`tc.kpis`): mean 66.6 before this change.
- **Evidence.** `202_battery_kpi_dashboard.json` (8 slides).
- **Human.** None yet → r2.

### Not a range change, recorded for completeness

- **Metric fix — hierarchy `ratio`.** A figure with a short unit ("4.5 days", "2 min", "−3 pts")
  was counted as body text competing with the headline; figures were already exempt ("€13M").
  Found on `209_battery_process/pr10` (impact row). `qa/composition.py:FIGURE_RE`.
- **Metric fix — `proof`.** "€1.2bn" in the headline is now proven by "1,210" in an exhibit in €M
  (same number at another scale, within the headline's precision). Found on
  `205_battery_waterfall/wf05`. `qa/composition.py:_scaled_match`.
- **Classification.** One short argument (a single bullet ≤ 40 words, nothing else) and short
  quotations (≤ 3, ≤ 45 words) are `statement`, not `text_exhibit`; a single-row `flow` is a
  `process`, not an `architecture`. These are semantic corrections (text_exhibit had become a
  fallback bucket); scores of reclassified slides are NOT like-for-like with v1.3.3.

## 1.3.2

### executive_summary.utilization 0.72 → 0.50 · empty 0.28 → 0.32 · offcentre weight 8 → 12

- **Reason.** Human feedback on gallery slide 3: short summaries read better as one compact,
  centred block than spread over the full height; balance matters more than filling.
- **Evidence.** Gallery slide 3 (development set); explicit preference of the user.
- **Human.** One reviewer, one slide — recorded as human feedback, not as a validated A/B result.

## 1.2.0

Initial profiles: design reasoning, checked against the v1.2 calibration set (example decks
reviewed slide by slide + the regression suite). The v1.2 public holdout was sealed before.
