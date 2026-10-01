# Changelog

## Unreleased — 1.7.0.dev0: consulting intelligence (development)

- **Experiment 01 (docs/S2D_EXPERIMENT_01.md):** 4 development cases, independent agents without
  (A) and with (B) the reasoning protocol. Substance tie (3/3 conclusions, 0 traps each); B
  verifiable (every number a fact or a recomputed formula), fewer untraced numbers. Blind
  storyline round `s1` built for the expert rater. Two new cases with PDF and DOCX sources.
- Fact model: period per number ("38% in FY2025, up from 29% in FY2024"), comparison bases ("15%
  more than in 2025" is a 2026 figure), forecast words (prevista, expected, target), units in prose
  and headers (días, horas, minutos, meses), "12 M€"; Spanish thousands in headline numbers; "100
  EUR" is money. `cpe reason eval-text` scores any system's storyline.md (negation- and
  reported-speech-aware trap detection).

- **Evidence standard (owner decision):** one expert rater. r3 closed (blind v1.5 result preserved
  in `VALIDATION_v1.5.json`) and marked development data.
- **Waterfall scorer blind spot fixed:** new critical `integrity` metric — a broken slide (content
  off-slide, colliding or overflowing; a chart that cannot encode its data) cannot score well. On r3
  scorer–expert agreement 5/10 → 9/10 (waterfalls 7/7), no false positive on tied pairs; `cpe
  measure` uses the current checks. docs/WATERFALL_SCORER_STUDY.md. KPI-dashboard profile stays
  provisional (4–2 expert votes, 5 ties).

- `src/cpe/reasoning/` + `cpe reason facts | check | ghost | trace | eval`: structured fact model
  (cell ranges, periods with basis — actual / estimate / budget / forecast —, units, derived
  changes with lineage), business-question object, hypotheses, insights, storyline candidates,
  deck plan (slide architecture), computed facts (formulas recomputed) and explicit assumptions.
- Hard factuality gates: fabricated fact, unsupported number (insight, governing thought, plan or
  deck headline), wrong source attribution, arithmetic error, claim resting on a rejected hypothesis.
- Evidence graph and `trace`: any sentence → insight → facts → source cells.
- Source-to-deck benchmark (`evals/source_to_deck/{development,sealed,external}`), dimensions
  reported separately; one development case (margin recovery) with traps; one development run by
  the developing agent (not evidence). docs/REASONING_PROTOCOL.md (protocol 1.0: 12 passes, 5
  critic roles, stopping criteria), docs/SOURCE_TO_DECK.md.
- Conflicting sources: `fact_conflicts.json` (forecast vs actual, value mismatch for one measure
  and period); an unresolved conflict touching a used fact is an error. Critic findings
  (`critique.json`, five roles); an unresolved high-severity finding stops the loop. Both are
  stopping criteria. Hedged headline numbers ("about 1.1 pp") that rest on assumptions are info,
  unhedged ones a warning.
- Blind A/B of reasoning before rendering: `cpe human build-text` (storylines or deck outlines,
  with business-question context), same private key and voting packages.
- Second development case (`churn_es`: Spanish, multi-sheet Excel, M€, decimal commas) — no run
  yet; it found two fact-model bugs, fixed: a unit in one column spread to the whole table;
  "30.000" was read as 30.
- The margin-recovery development run went through a real critic loop: RED TEAM found that the
  governing thought claimed the full 1.5 pp target from two levers that size to about 1.1 pp; the
  storyline was revised (RUN.json records the iterations). Still the developing agent's own run.
- Ingest: numbers in prose are read whole ("2026" was split into "202" + "6"); Spanish thousands.
  Headline lint verb lexicon: recover, sell, combine, serve, handle.

## 1.6.0rc1 — External validation infrastructure (awaiting external input)

v1.6 answers *does the existing engine generalise?* It adds almost no rendering functionality on
purpose. **No v1.6 validation claim exists yet**: the three inputs that would make one (raters 2–4
on r3, an externally authored holdout, an unseen corporate template) must come from outside.
The engine is frozen on the `release/v1.6.0rc1` branch for those runs; v1.7 development continues on `main`.

- **Human, multi-rater.** `cpe human package` builds a self-contained voting package (bundle +
  stdlib-only server + Windows launcher + instructions, never a key) — r3's key is in the
  repository, so new raters vote from the package, not the repo. `cpe human import` takes the
  returned `votes/<id>.jsonl` (idempotent). Reports separate WITHIN-rater self-consistency from
  BETWEEN-rater agreement. New rounds: `--identical-controls K` (same image twice; tie rate =
  evaluator noise, reported per rater, never used to drop anyone). r3 reopened for raters 2–4,
  pairs unchanged (docs/HUMAN_EVALUATORS.md).
- **External holdout.** `.private/holdouts/external/` with attested provenance;
  `cpe holdout external-seal` (hashes, never rewritten) and `external-run` (refuses unsealed or
  edited decks, a dirty engine, and a second run per engine version). Author brief for the
  external author (docs/EXTERNAL_AUTHOR_BRIEF.md).
- **Unseen corporate templates.** `.private/holdouts/corporate_unseen/<name>/template.pptx`, any
  number; known development templates refused by hash; run once per engine version.
- **Derived proof across exhibits** (development): a headline figure may combine two explicit
  single quantities of two different exhibits (KPI value, table total row, waterfall start/end,
  one-value series) with one operation (sum, difference, share, ratio); never more than 10
  candidates, ambiguity → unproven; lineage recorded.
- **Not done, by rule:** KPI-dashboard profile and the waterfall scorer blind spot wait for r3's
  additional raters (r3 is not development data yet); absolute gates stay provisional until the
  external-holdout distribution exists (docs/EVALS.md, "v1.6 status").

## 1.5.0rc1 — Human alignment, real failure modes, independent evidence pending

A deliberately small release. It ends as a **release candidate awaiting external validation**: the
independent evidence that could confirm it (an externally authored holdout, an unseen corporate
template, human round r3) can only come from someone else. Nothing below is independent evidence
for v1.5 (docs/EVALS.md, first table).

### Governance
- Round r2's blind result is preserved as the **single-rater blind validation of v1.4.0**
  (`rounds/r2/VALIDATION_v1.4.json`: 35/1/2, 97.2% [85.8–99.5], scorer agreement 33/34; a test
  recomputes it from the hashed votes). r2 was then marked **development data** (`mark-used`).
- Profiles: process and comparison `utilization`/`empty` → `human_supported_single_rater` (8/8 and
  7/7 decisive votes, one rater). kpi_dashboard stays `provisional`, range unchanged. Absolute
  gates (mean ≥ 70, ≤ 25% below floor) stay provisional. `evals/profile_changes.md`.

### KPI dashboards (docs/KPI_DASHBOARD_DIAGNOSIS.md)
- r2's largest disagreement (p034, −26.2) was the **metric**: separators extended the "used" area;
  light card panels were invisible. New occupancy measurement (`qa/composition.py:_occupancy`):
  panels count as occupied, isolated thin lines do not. r2 re-measured (development data): 35/35.
- Engine: cards arranged by measured width (one row up to 4, 5 when legible, else rows of 3,
  centred short last row), height from content, every text colour made legible against the card
  fill (the holdout's 2.8:1 delta). Development KPI dashboards 77.5 → 98.6.

### Derived-number proof (qa/proof.py)
- Deterministic, unit-aware arithmetic lineage: sum, sum of the 2/3 largest, difference, ratio,
  percent change, percentage-point change, part ÷ total, waterfall increases / decreases / net
  change. €/$/£, k/M/bn, %, pp, bps, ×; never across currencies or kinds. Tolerance = the headline's
  written precision + 0.5%. No subset search; plain integers < 10 never derived; different kinds of
  derivation matching one figure → "ambiguous", not proven. Machine-readable provenance per figure.
  The direct match now honours the headline's rounding.

### Render fixes (minimised repros in `evals/regression/cases/11_render_edges.json`)
- **Waterfall**: running totals and totals below zero / crossing zero (were drawn off-slide, labels
  at y = 18–66 in). Every bar is a span; positive and negative parts stack from zero; labels above
  positive bars and under negative totals, clamped inside the plot frame; zero line on the axis.
  `WATERFALL_NEGATIVE` is no longer emitted.
- **Statement**: fallback ladder — measure with a renderer margin → 30/28/26/24/22 pt (22 = floor)
  → optical placement → if it still does not read as a statement, set as body text with a
  `STATEMENT_TOO_LONG` warning. Never clipped.
- **QA measurement**: rendered spans are measured on visible glyphs; a trailing space's advance at
  a line break was reported as `RENDER_TEXT_SPILL`.

### QA semantics, reporting, provenance
- `visual_qa_passed`, `authoring_qa_passed`, `benchmark_passed` reported separately; lint-stress
  cases declare `eval.lint_stress`. Slides authored / resolved / measured reported apart.
- Benchmark specs made editorially valid: the archetype battery is a declared slide
  **collection** (no executive-summary rule; every other storyline rule applies), its 11 real topic
  headlines were rewritten as claims, and the headline lint's verb lexicon gained common verbs it
  missed ("rate", "beat", "bajó", "tiene", "cubre", …). Lint coverage is unchanged
  ("Lessons from the pilot" is still a topic).
- Provenance names `evaluated_source_commit`/`evaluated_source_dirty` and
  `working_tree_commit`/`working_tree_dirty`; result files never make the evaluated source "dirty".

### Human evaluation
- Private-key architecture for new rounds: key in `.private/human_reference/keys/<round>/`,
  SHA-256 commitment in the bundle, `cpe human report --key`, `cpe human close`; test that the
  bundle reveals no version, role, layout, score or mapping. r1/r2 history untouched.
- Per-rater and pooled statistics; a rater voting twice counts once. Windows: UTF-8 everywhere,
  `votes/` created on demand (the "Vote not saved" bug of the first r2 session).

### Robustness
- Median / P90 / P95 / max drop, meaningful (≥ 5) and large (≥ 10) drop rates, new-visual-error,
  font-drop, layout-change and layout-change-with-drop, new-flag rates — global, per perturbation,
  per archetype. Enforced: no new visual QA error, no catastrophic variant, no coverage loss.
  Provisional relative gates for P90, large drops, font drops, layout instability.

### Human round r3 (voted after the freeze; single rater)
- 38 blind pairs + 4 repeats, v1.4.0 vs v1.5.0rc1, one evaluator: v1.5 preferred 9, v1.4 1,
  **28 ties** (decisive preference 0.90, 95% CI 0.60–0.98; ties-as-half 0.61); 4/4 repeats
  consistent; left share 0.50. Waterfalls 7–0 (5 ties); KPI dashboards 2–1 (4 ties); long
  statements 19 ties — the statement change is not visible to this rater. Fresh content 8–0;
  holdout-v2 content (development-known) 1–1. Scorer agrees on 5 of 6 decisive pairs; Kendall
  τ-b 0.37 [−0.22, 0.83] (directional only). Not used for calibration.

### Intake (awaiting input)
- `cpe holdout intake | v15-external | v15-corporate` and docs/EXTERNAL_HOLDOUT_PROTOCOL.md.
  External decks need attested outside authorship; a known development template (JET) is refused.

## 1.4.0 — Generalisation and visual intelligence

Engine frozen at `430176d`; every number below was evaluated on that clean commit
(`evals/results/latest.json`, `provenance.evaluated_commit`).

### Evaluation
- **Quality profile** in every eval (`quality.py`): macro-archetype score, weakest archetype,
  P10/P25/median/P75/P90, shares ≥ 90/80/70, per-archetype n/mean/median/min/P10/flags, coverage
  (insufficient < 5, provisional < 8, gate-eligible ≥ 8), health, and `archetype_diagnostics.md` +
  contact sheets per weak archetype. The overall mean is kept for continuity, no longer the headline.
- **Absolute archetype gates** (`evals/archetype_gates.json`) on top of the relative baseline:
  catastrophic minimum 35 enforced; mean floor 70 and ≤ 25% of slides below it provisional
  (reported until human evidence exists); coverage regression fails CI. v1.3.3 would have failed
  the enforced gate (text slide at 20.5) while passing its relative baseline.
- **Penalty attribution**: every score explains itself per metric (expected, observed, fitness,
  weight, points lost); penalties sum to 100 − score.
- **Archetype battery**: 17 decks / 154 slides (`scripts/make_archetype_battery.py`), every archetype
  gate-eligible. Regression: 27 decks, 194 slides.
- **Robustness** (`cpe robustness`, CI job): 8 metamorphic perturbations × 22 development seeds;
  median / P90 drop, catastrophic rate, own baseline.
- **Holdout v2**: 26 decks / 157 slides sealed in `40a0589` before any v1.4 change, run once on the
  frozen engine; guarded runner (release candidate, seal, clean tree, once per version). H01–H05
  retired as blind evidence. External deck holdouts: `cpe holdout external` (sanitized, never
  baselined). The private corporate template is recorded as development data, never as a holdout.
- **Human**: round r1 preserved (awaiting votes); round r2 (40 pairs: v1.3.3 vs v1.4 engine on the
  sealed holdout decks, both scored by the v1.4 scorer, quotas on comparison / process / KPI /
  text / roadmap + controls) awaiting votes; per-pair scorer/human agreement, Kendall τ-b with
  bootstrap CI, `human_score_disagreements.md`, round status (development data once used).
- **Provenance**: evaluated commit, tree, dirty flag, container digest, fingerprint, timestamp on
  every release signal; dirty runs cannot be recorded as release truth; `cpe results verify` in CI.
- Profiles moved to `qa/archetype_profiles.json` with rationale and evidence; `evals/profile_changes.md`.

### Engine (fixed on development data only; docs/ARCHETYPE_DIAGNOSIS.md)
- Adaptive vertical composition (`pptx/adaptive.py`): largest readable scale that fits, block on
  the optical centre, body type capped below the headline. Process (numerals for sparse flows,
  metric row under the steps), comparison (one scale and top edge for all columns), KPI strip →
  cards, KPI hero centred, gantt rows sized by count, small org charts centred.
- Text slides: own `text` role and component (argument / list / narrative / quote) instead of side
  commentary. **Bug fixed**: bullets were silently dropped when the slide also had commentary.
- **Bug fixed**: combo chart without a secondary axis crashed (found by the battery).
- Classification: one short argument and short quotations are statements; a one-row flow is a process.
- Metric fixes: figures with short units ("4.5 days") no longer count against hierarchy; the proof
  check accepts the same number at another scale ("€1.2bn" ↔ "1,210" in €M; "€61,000,000" ↔ "61").
- Provisional profile changes (process, comparison, kpi_dashboard), evidence and reasons in
  `evals/profile_changes.md`; human round r2 tests them.

### Results (v1.4 scorer unless stated)
- Regression: overall 92.8, **macro 92.4, P10 75.4, weakest kpi_dashboard 79.8**; 17/17 archetypes
  gate-eligible; QA visual errors 0. Battery before (v1.3.3): macro 80.4, P10 37.8, text 30.8,
  process 42.1, comparison 48.2.
- Robustness: 78 variants, median drop 0.0, P90 drop 0.0, catastrophic 0 (2 before the scaled-proof
  fix, both "€61M" → "€61,000,000").
- **Holdout v2** (run once): 26/26 decks built, overall 91.4, **macro 91.8, P10 74.5, weakest
  kpi_dashboard 71.6 (n=5)**; 4 visual QA errors.
- Engine vs scorer on the holdout (slide mean / macro / P10): v1.3.3 engine 77.3 / 78.9 / 36.5 with
  the v1.3.3 scorer; v1.4 engine **87.1 / 87.7 / 53.6 with the same v1.3.3 scorer**; 91.4 / 91.8 /
  73.7 with the v1.4 scorer. The engine alone explains ~10 points of mean and 17 of P10; the rest
  depends on the provisional profile changes.
- Examples (fixtures, not benchmark): Alvora 99.8, Gallery 99.1, Kestrel 99.5, QA passed.
- Human: no votes yet (r1, r2 awaiting votes).

### Holdout v2 findings (recorded, NOT tuned in this cycle → v1.5)
- KPI dashboards weakest (71.6); one dashboard slide has a hard LOW_CONTRAST error (likely a
  coloured delta on the new KPI card fill).
- PROOF_NOT_VISIBLE causes 7 of the 8 slides below 62: derived numbers (sums, differences).
- OUTSIDE_ZONE ×2 on a Spanish waterfall; RENDER_TEXT_SPILL on a long statement.

## 1.3.3 — Balanced cover

- Built-in cover: the title block (accent bar, title, subtitle) is measured and set on the optical
  centre of the upper field, so a one-line title no longer floats above a fixed gap; client, date
  and confidentiality sit in a primary-colour band across the foot of the slide (the lower half
  used to be empty). Corporate templates keep their native cover.
- Executive summary numbering (Alvora slide 2) checked at full resolution: the numbers are already
  centred on their claims; the misalignment seen on the contact sheet was a thumbnail artefact.
  No change.
- Regression unchanged (87.5); examples regenerated (Alvora final 99.8, gallery 99.8).

## 1.3.2 — Compact executive summaries

- Short executive summaries are set as ONE compact block on the optical centre (rows at their
  natural height plus breathing space, framed by rules) instead of being spread over the full
  height; dense summaries still share the height evenly.
- Archetype profile change, driven by explicit human feedback on gallery slide 3 (development
  set): `executive_summary` accepts a compact, balanced block (utilization from 0.50, empty space
  up to 0.32, balance weighted higher). A summary using under half the canvas is still flagged.
- Regression 87.3 → 87.5 (no regressions; the two-line summary case 41.8 → 75.1, still flagged as
  thin); gallery slide 3 scores 100.

## 1.3.1 — Agenda, executive summary and statement layout

- Agenda: a compact index set on the optical centre of the body (not stacked from the top),
  aligned with the headline's left margin, with larger numbers and titles.
- Executive summary rows: content sits on each row's centre line, so short rows read as an even
  table instead of text stuck to the top of tall empty bands.
- Statement slides: bar, statement and support are placed as one block on the optical centre of
  the zone (the text used to fall into the lower half).
- Gallery slides 2, 3 and 26 regenerated; regression unchanged (87.3, no new flags).

## 1.3.0 — Corporate templates read through their inheritance chain

Fixes for the structural findings of the v1.2 private corporate holdout. Because those findings
drove the changes, that template is **development data from now on**, not a holdout; the fixes are
generic and are tested on a synthetic template built to reproduce the same patterns
(`brand/fixtures.py::make_inherited_styles`). The public holdout cases were reviewed during v1.2
and are no longer blind either: v1.4 needs new sealed cases.

### Typography
- Text is attributed to the font it is really drawn in, following PowerPoint's inheritance:
  run → shape list style → layout placeholder → master placeholder → master text styles →
  presentation default → theme (`brand/model.py::effective_style`). The report says where the
  inherited text gets its font from.
- Weight-named families are one family ("Inter Black", "Inter ExtraBold" → Inter); a different
  family such as "Inter Tight" stays separate.
- Any INSTALLED font is now measured with its own file (fontconfig, exact family match), not only
  the built-in metric twins.
- The visual environment ships widely used open-licence corporate typefaces (Inter, Roboto,
  Open Sans, Lato, Montserrat; pinned) so brands set in them render and measure exactly.
  Regression renders are unchanged (87.3 before and after the image change).

### Colour roles
- Page and text colours come from what the template draws (the background of its content
  layouts, the colour its text resolves to) instead of theme slot names, which some templates use
  unconventionally (dk1 = accent, lt1 = text). All derived greys come from that real pair, the
  secondary data colour is darkened until white labels reach 4.5:1, and the dark data colour is a
  template colour (the text colour when the brand has no other dark).
- Supporting colours include brand-colour slide backgrounds and coloured text; pale brand tints
  are no longer mistaken for greys.

### Grid, layouts, brand rules
- Margins from the titles of the content layouts (symmetric when the content reaches the mirrored
  margin); finer column systems must earn their extra columns; pictures and full-bleed artwork no
  longer vote.
- A layout used for the last example slide keeps a `closing` label, even when it looks like a divider.
- Deck-level brand advice (editorial, never QA): `BRAND_BOOKEND` (the brand opens and closes on its
  colour) and `BRAND_COLOUR_SHARE` (share of brand-colour slides vs the template's examples).
- Render QA no longer judges text that belongs to the template's own artwork (e.g. a "Confidential"
  mark on a corporate cover layout).
- Bounded a contrast loop that could hang on templates with unconventional colour slots.

### Results on the (former) private holdout — development data, not a holdout result
- Agreement with the human-written brand spec: 13/22 → 21/22 claims (the remaining one: the
  closing layout is a divider-class layout used last, counted under "section").
- Test deck generated on it: QA failed with 112 errors → passed, 0 errors; with dividers and a
  closing slide, 0 errors, 0 warnings, no brand advice.
- Regression unchanged (87.3); public holdout 81.0 → 81.2 (the Spanish "todo" false error fixed
  after v1.2), now reported as no longer blind.

## 1.2.0 — Reproducible, archetype-aware, independently evaluated, corporate-template aware

**Goal:** make visual quality reproducible, archetype-aware, independently evaluable, and capable
of understanding real corporate PowerPoint systems. Not a higher score for its own sake: a higher
score should correspond more closely to a genuinely better composition on unseen slides.

### Reproducibility
- `docker/Dockerfile`: the visual environment pinned end to end (base image digest, Ubuntu archive
  snapshot, exact LibreOffice / fontconfig / FreeType / HarfBuzz / FriBiDi / font versions,
  `requirements.lock`). `scripts/cpe-docker` runs it locally; CI uses the same image (built once
  per commit and published to GHCR).
- Silent drift found and fixed: without FriBiDi, Pillow falls back from RAQM to BASIC text layout
  (no kerning) and every text measurement shifts ~0.2%.
- `environment.py`: manifest + render fingerprint recorded with every eval; `scripts/check_environment.py`.
- `cpe repro`: render twice, compare slide count, dimensions, PNG hashes, pixels, PDF spans,
  composition metrics and QA. Observed and required: pixel-identical.
- CI on `ubuntu-24.04`; actions on Node 24 pinned to SHAs; jobs lint · package · image · tests ·
  regression · reproducibility.
- `evals/results/latest.json` is the single source of truth; the README table is generated from
  it (`cpe results readme`, checked in CI).

### Composition
- `qa/archetypes.py`: 17 archetypes from content; expected visual profiles; score = fitness to the
  archetype (weighted mean + worst critical metric). v1.1 universal score kept as `score_v1`.
- Measurement fixes: hairline table rules, accent-only regions, one-sided emphasis, continuation
  markers, structural counts in the proof check.
- Composition is editorial advice (`editorial_advice`), never part of the hard-QA verdict or score.
- Candidate selection: hard-QA filter → archetype fitness; explicit "technically compatible but
  inappropriate for this content volume / archetype" verdicts; corporate layouts as candidates.
- Engine fixes from the development set: exhibit data given at the top level is normalised
  (`SPEC_DATA_SHAPE`) instead of crashing the build; table decimals follow the data; table splits
  are balanced; layouts are packaged so an installed wheel works.

### Evaluation
- `evals/regression/` (10 decks, +currencies/negatives/multi-source, +one slide per archetype),
  `evals/holdout/public/` (5 decks, sealed before the metric work), `evals/human_reference/`.
- `cpe eval --suite regression|holdout|examples [--docker] [--record]`; the holdout can never be
  baselined; `cpe holdout private` for corporate templates in `.private/` (git-ignored).
- `cpe human build|serve|import|report`: blind A/B page (random sides and order, no version /
  layout / score, keyboard, anonymous evaluators, resumable), Wilson intervals, Fleiss' κ, left
  bias, self-consistency, agreement between the automatic score and people. Round r1: 40 pairs.

### Corporate templates
- Every master analysed (no `slide_masters[0]` assumption); layout features → 20 classes with
  confidences, refined by observed usage; typography from theme + masters + layouts + usage +
  style-guide slides with conflicts; palette, grid, assets and brand rules with confidence.
- 16:9 templates on the 10 in page are rescaled and their masters used.
- Layout matching: native (placeholders filled) → adaptive (corporate layout + engine body) →
  CPE layout + theme; rejections recorded; per-slide reserved areas and headline/footer limits.
- New brand report (FONT WARNING with declared / observed / installed / renderable / fallback / risk).
- Synthetic three-master fixture for tests (`brand/fixtures.py`).

### Results (frozen for this release; current numbers live in `evals/results/latest.json`)
- Regression (archetype fitness): 87.3 over 10 decks / 39 slides, 0 QA errors. Not comparable to
  v1.1's 84.0 (a different metric); the v1.1 universal score of the v1.1.1 engine in the pinned
  environment reproduced 84.0 exactly (`evals/results/history/v1.1.1_pinned_env_*.json`).
- Holdout, public (rules frozen at e3b63e1): 81.0 over 5 decks / 27 slides, 1 QA error —
  a generalisation gap of 6.3 points.
- Holdout, private corporate template (sanitized): 1 master, 54 layouts, 32% of layouts classified
  with confidence ≥ 0.5; 13/22 claims of the human-written brand spec confirmed; the test deck
  generated on it failed QA (contrast).
- Human preference: tool and round r1 ready; no votes yet.

### Holdout findings (reported, not tuned on in this release)
- Typography inheritance stops at the master text styles: a template whose master placeholders
  are styled in another font (and whose weight variants are named as families, e.g. "Inter Black")
  is read as the theme font. Detected on the private holdout.
- Colour roles can put dark template accents under dark text (110 contrast errors on the private
  holdout test deck; the QA caught all of them).
- Grid inference over-fits finer column systems; closing layouts on brand colour are read as
  section dividers.
- `PROOF_NOT_VISIBLE` fires on derived headline numbers (sums, ratios) that the exhibit supports
  (≈ 4 of 7 flags on the public holdout).
- Fixed as correctness bugs, holdout results not re-recorded: layout classifier crash when all
  evidence is weak (private holdout); `TODO` placeholder check matched the Spanish word "todo"
  (public holdout).

## 1.1.1 — Full-width headlines and sparse-slide fixes

### Changed
- **Headlines run to the right margin.** The old "balanced" headline narrowed two-line titles to as
  little as 55% of the width, which pushed them to the left. Headlines now use the full width (or
  stop before a template logo). A single-word last line is fixed by the smallest possible
  narrowing (at most 15%), which is validated against a ±1.2% renderer tolerance so LibreOffice
  and PowerPoint cannot reintroduce it.
- Harvey balls use the secondary colour; the primary colour is kept for the highlighted column.
- The hierarchy metric ignores big figures ("€13M", "85%"): they are deliberate emphasis, not text
  competing with the headline.

### Added
- Process diagrams: an optional per-step `metric` / `metric_label` impact row, aligned with the steps.
- Timelines: an optional per-event `detail` line (owner / what the milestone unlocks).
- Takeaway columns under an exhibit show the commentary `title`.
- Composition variants (content scale) for text-bearing diagrams.
- Automatic proof ignores forecast periods: the claim is proven on actuals.

### Gallery
- g07, g13, g14, g18 and g19 no longer carry composition warnings: 0 warnings, composition
  87.0 → 92.1. g14, g18 and g19 got richer content (the impact per step, the goal of each
  phase, the critical-path read-out) rather than padding.

## 1.1.0 — Visual intelligence, corporate templates, quality evals

**Goal:** make visual quality testable rather than subjective, adapt composition to content, and
inherit the visual identity of an existing corporate PowerPoint.

### Added
- `qa/composition.py`: eight composition metrics measured on the real render (dead space, canvas
  utilization, balance, density, focal-point strength, visible headline proof, hierarchy,
  alignment rhythm) → 0–100 score + named flags; unfixable flags become `COMPOSITION_*` author actions.
- `compose.py`: composition engine (layout candidates × composition variants → one render pass →
  scoring → best candidate; rejects QA-failing and "compatible but editorially weak" candidates;
  consistency margin and repetition penalty). On by default in `cpe run` (`--no-compose` to skip).
- `evals/`: 8 stress decks, `cpe eval` with baseline comparison (crash / QA errors / composition
  drop / new flags → exit 1), `cpe measure` for any existing run, v1.0 vs v1.1 comparison.
- `brand/ingest.py` + `cpe brand ingest`: theme colours, heading/body fonts, masters, layouts,
  placeholders, logos → brand theme + compatibility report (fonts detected/installed/missing, the
  substitute used for measurement and rendering, unsupported elements); generation on the
  template's masters; `BRAND_RESERVED_OVERLAP` check.
- Font-aware text measurement (Carlito ≡ Calibri, Caladea ≡ Cambria, render-substitute measurement
  for missing fonts), heading vs body fonts.
- Automatic proof annotations (first→last change, CAGR, last-period change, waterfall total delta,
  pie top-k share); default single focus on one-series charts; KPI hero and single-statement
  treatments for sparse slides; content scale and table stretch knobs.
- QA: `RENDER_LABEL_TRUNCATED`, `RENDER_LABEL_ROTATED`; legible accent text (WCAG) for light brand colours.
- Apache-2.0 `LICENSE` + `NOTICE`; GitHub Actions CI (lint, tests, regression decks, evals).

### Changed
- README leads with the rendered demo; Spanish decimal commas understood by the number checks.

### Results (same metrics for both versions)
- Eval suite composition 77.6 → 83.8; flagged slides 30 → 20. Demo deck 91.3 → 94.4; gallery 84.1 → 87.0.

## 1.0.0 — Consulting presentation engine
Storyline-first engine: deck spec contract, storyline frameworks, headline lint, visual reasoning,
43 layouts in 16 families, native charts/tables/diagrams, LibreOffice rendering, three-layer QA
with a self-correction loop, CLI, docs, demo and gallery decks, 44 tests.
