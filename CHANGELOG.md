# Changelog

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
