# Changelog

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
