# Composition scoring — archetype fitness

v1.1 scored every slide against one universal ideal ("fill the canvas, have a focal point…").
That rewarded the same composition everywhere: a statement slide with generous air lost points,
and a table stretched to fill the slide won them. v1.2 asks a different question:

> Is the composition of THIS slide appropriate for what the slide is trying to be?

```
SLIDE INTENT → ARCHETYPE → EXPECTED VISUAL PROFILE → RENDER → OBSERVED VISUAL PROFILE
             → DEVIATION → COMPOSITION FITNESS (0–100)
```

Code: `src/cpe/qa/archetypes.py` (taxonomy, profiles, fitness) and `src/cpe/qa/composition.py`
(measurement on the render).

## 1. Archetype

The archetype comes from the slide's **content** (kind + main exhibit type + text roles), never
from its layout. Alternative layouts of the same content are therefore judged against the same
expectations, which is what makes candidate selection meaningful.

`statement · kpi_hero · kpi_dashboard · executive_summary · chart · waterfall · table · matrix ·
comparison · process · roadmap · timeline · operating_model · architecture · hierarchy ·
segmentation · text_exhibit`

(`hierarchy` covers org charts, driver trees and pyramids; `kpi_dashboard` separates a KPI grid
from a single hero figure.)

## 2. Observed profile (measured on the PNG + PDF of the render, body band only)

| metric | meaning |
|---|---|
| `utilization` | share of the body band covered by the content's bounding box |
| `empty` | largest empty rectangle as a share of the body band (hairline table rules count as structure) |
| `ink` | ink coverage of the body band |
| `offcentre` | distance of the ink's centre of mass from the body centre (horizontal, plus vertical beyond ±0.1) |
| `emphasis` | share of ink in the focus colours — one-sided: it can say "nothing stands out" only, because the primary colour is also the default data ink |
| `regions` | separate solid regions in the **accent** colour — several competing masses = noisy emphasis |
| `ratio` | headline size ÷ largest wordy body size (hierarchy; big figures are not counted as competing text) |
| `edges` | number of distinct left edges of text lines (alignment rhythm) |
| `proof` | share of the headline's numbers / highlighted items visible in the body (structural counts such as "twelve plants" = 12 rows count as proven) |

## 3. Expected profiles

Each entry is a target range, a softness (how fast fitness decays outside the range) and a weight
(how much the metric matters for that archetype). Generated from the code:

| archetype | utilization | empty | ink | offcentre | emphasis | regions | ratio | edges | proof |
|---|---|---|---|---|---|---|---|---|---|
| statement | 0.15–0.75 (w6) | 0–0.8 (w4) | 0.01–0.12 (w6) | 0–0.25 (w4) | — | 0–3 (w2) | — | 0–5 (w6) | — |
| kpi_hero | 0.25–0.95 (w8) | 0–0.5 (w12) | 0.02–0.2 (w6) | 0–0.22 (w10) | 0.1–1 (w12) | 0–2 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| kpi_dashboard | 0.5–1 (w12) † | 0–0.36 (w14) † | 0.04–0.3 (w8) | 0–0.12 (w8) | 0.05–0.7 (w6) | 0–6 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| executive_summary | 0.5–1 (w12) | 0–0.32 (w14) | 0.02–0.35 (w8) | 0–0.1 (w12) | — | 0–6 (w2) | 1.35–9 (w10) | 0–6 (w10) | — |
| chart | 0.72–1 (w12) | 0–0.28 (w16) | 0.01–0.45 (w6) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| waterfall | 0.78–1 (w14) | 0–0.25 (w16) | 0.03–0.4 (w6) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| table | 0.75–1 (w16) | 0–0.2 (w20) | 0.02–0.32 (w6) | 0–0.14 (w6) | — | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| matrix | 0.65–1 (w12) | 0–0.32 (w12) | 0.04–0.28 (w6) | 0–0.1 (w14) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| comparison | 0.55–1 (w12) ‡ | 0–0.35 (w14) ‡ | 0.06–0.3 (w8) | 0–0.1 (w12) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–6 (w10) | 0.5–1 (w14) |
| process | 0.5–1 (w12) ‡ | 0–0.36 (w14) ‡ | 0.06–0.3 (w8) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–8 (w6) | 0.5–1 (w14) |
| roadmap | 0.78–1 (w16) | 0–0.28 (w12) | 0.04–0.3 (w6) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| timeline | 0.35–1 (w10) | 0–0.5 (w10) | 0.01–0.25 (w6) | 0–0.18 (w6) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| operating_model | 0.78–1 (w14) | 0–0.22 (w14) | 0.06–0.4 (w8) | 0–0.35 (w3) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–10 (w4) | 0.5–1 (w14) |
| architecture | 0.75–1 (w14) | 0–0.25 (w14) | 0.06–0.4 (w8) | 0–0.35 (w3) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–10 (w4) | 0.5–1 (w14) |
| hierarchy | 0.65–1 (w12) | 0–0.35 (w12) | 0.03–0.3 (w6) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–10 (w4) | 0.5–1 (w14) |
| segmentation | 0.72–1 (w12) | 0–0.28 (w14) | 0.06–0.3 (w8) | 0–0.12 (w8) | 0.05–1 (w8) | 0–5 (w4) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |
| text_exhibit | 0.55–1 (w12) | 0–0.4 (w14) | 0.03–0.25 (w8) | 0–0.12 (w8) | 0–0.5 (w2) | 0–4 (w2) | 1.35–9 (w10) | 0–5 (w6) | 0.5–1 (w14) |

† provisional (v1.4; human evidence too small — kpi_dashboard 2/3 in r2, one rater; round r3 tests it).
‡ human_supported_single_rater (v1.5): blind round r2, one evaluator — process 8/8, comparison 7/7
decisive votes for the v1.4 composition. Directional support, not multi-rater validation.

Since v1.5 `utilization` and `empty` are measured on an **occupancy** grid: visible filled panels
(cards, step headers — anything distinct from the page colour) count as occupied, isolated thin
vertical lines through empty space do not (docs/KPI_DASHBOARD_DIAGNOSIS.md).

The ranges live in data — `src/cpe/qa/archetype_profiles.json` — with, per archetype, *why*, the
development and human evidence, and per metric the version that last changed it (and `provisional`
when no human evidence exists). Every change is recorded in `evals/profile_changes.md`; tests fail if
the file and the changelog disagree, or if the file is not in its one-metric-per-line canonical
format (calibration changes must be readable diffs).

### Governance (v1.4)

1. A low score is a question, not a reason: render the archetype's contact sheet, read the
   attribution (§4), compare with accepted development slides.
2. Decide which of these is wrong: the **metric** (it measures something else than intended), the
   **profile** (the expectation does not fit what the archetype is), the **layout / component**, the
   **content adaptation**, or the **candidate selection** — and fix that one, engine first.
3. A profile change needs a design reason and development evidence, is `provisional` until human
   votes exist, and is never made on the sealed holdout.
4. Human votes calibrate patterns across many pairs, never a single slide.

v1.4 decisions (docs/ARCHETYPE_DIAGNOSIS.md): engine fixes for text, process, comparison, KPI and
gantt components; metric fixes for `ratio` (figures with units) and `proof` (scaled numbers);
semantic reclassification (one short argument / short quotes → statement; one-row flow → process);
provisional profile changes for process, comparison and kpi_dashboard.

## 4. Fitness

Per metric: 1 inside the range, decaying linearly to 0 at `soft` outside it.

```
score = 100 × [ 0.7 × weighted mean fitness  +  0.3 × worst fitness among the critical metrics (weight ≥ 10) ]
```

**Attribution (v1.4).** Every score explains itself (`attribution` per slide in `qa_report.json`
and eval reports): for each metric the expected range, observed value, fitness, weight and the
points it costs — `(1 − 0.3)·100·w·(1 − f)/Σw`, plus `0.3·100·(1 − f)` charged to the worst critical
metric. The penalties sum to 100 − score (tested). Per-archetype means of these penalties are the
first table of `archetype_diagnostics.md`.

A plain mean lets many "fine" metrics dilute one severe failure (half the slide empty, the proof
invisible). Composition quality is bounded by its worst failure, so the worst critical metric
carries 30% of the score. A metric whose fitness falls below 0.6 becomes a named flag
(`DEAD_SPACE`, `UNDERUSED_CANVAS`, `OVERFILLED`, `SPARSE`, `OVERDENSE`, `OFF_BALANCE`,
`NO_FOCAL_POINT`, `NOISY_EMPHASIS`, `WEAK_HIERARCHY`, `RAGGED_ALIGNMENT`, `PROOF_NOT_VISIBLE`) with
its archetype-specific meaning, e.g. *"table: a large area is left empty (empty 0.52 vs expected
0–0.2)"*.

The v1.1 universal score is still computed (`score_v1`) for continuity and for the human A/B
comparison "universal-score selection vs archetype selection".

## 5. How the numbers were derived (and what was NOT used)

1. **Design reasoning first**: what each archetype is for (a statement needs air; a roadmap reads
   across the full width; a 2×2 is a square field where balance matters more than corners; a
   layered diagram carries a label column, so its ink is left-weighted by construction; solid bars
   are data ink, not clutter; a timeline is a one-dimensional band).
2. **Checked against the calibration set**: the example decks (reviewed and approved slide by slide)
   and the regression suite (development set). Approved slides should fall inside the ranges;
   the known failures of the regression suite (a KPI stuck in a corner, columns using the top half,
   a near-empty table continuation, a one-line text slide) should fall outside.
3. **Measurement validity fixes found while calibrating** (these changed the measurement, not the
   targets): hairline table rules were missed by 2-px sampling and read as dead space; "regions"
   counted every bar of the primary colour; `(1/2)` continuation markers were read as headline
   numbers; counts ("twelve plants") were not recognised as proven.
4. **Not used**: the public holdout (`evals/holdout/public`) was written and sealed *before* this
   file existed and was never run while setting these numbers; private corporate holdouts were run
   only after the rules were frozen.

Known weakness found by the v1.2 holdout: headline numbers that are *derived* (a sum of the steps,
a conversion ratio) are not recognised as proven. v1.4 fixed the scaled case ("€1.2bn" proven by
"1,210" in €M; "€61,000,000" by "61") found by the battery and the robustness suite; true derived
numbers (sums, ratios) remain a known limitation.

## 6. Hard QA vs composition

| | hard QA | composition fitness |
|---|---|---|
| what | objective defects: clipping, overflow, overlap, off-canvas, unreadable size or contrast, missing source, invalid chart geometry, broken render, placeholder text, covering template artwork | editorial preference: use of space, whitespace, balance, focal point, rhythm, hierarchy, density |
| effect | errors fail the gate (`passed = false`) | never changes `passed` or the QA score; reported as **editorial advice** (`editorial_advice` in `qa_report.json`) |
| in candidate selection | candidates with QA errors are rejected before scoring | ranks the surviving candidates |

A slide with a mediocre composition can still be valid. A slide with clipping cannot.

## 7. Candidate selection (`src/cpe/compose.py`)

```
content → compatible layouts (selector) → composition variants (scale, table stretch,
corporate layout) → render all candidates in one pass → hard-QA filter → archetype fitness
→ choose
```

A different layout must beat the default by `LAYOUT_SWITCH_MARGIN` (3 points), a variant by
`TIE_MARGIN` (1.5); repeating the previous slide's layout costs `REPEAT_PENALTY` (2.5). Candidates
below `EDITORIAL_FLOOR` (70) are named explicitly:

> `table_commentary` 29.9 — technically compatible with the content, but the composition is
> inappropriate for this content volume / table archetype: a large area is left empty (empty 0.635
> vs 0.0–0.2); content uses too little of the canvas (utilization 0.344 vs 0.75–1.0)

Every decision and rejected alternative is written to `composition.md`.
