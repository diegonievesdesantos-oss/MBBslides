# ARCHITECTURE.md — Consulting Presentation Engine

## 1. Principle: THINKING separated from RENDERING

The system has an explicit boundary: the **deck spec** (JSON). On one side the agent reasons
(what to communicate, storyline, the intent of each slide, evidence); on the other, the engine
draws, renders and checks. Nothing is drawn without a complete *slide intent* (`validate_structure`
blocks it), and every later change is expressed as a **patch on the spec**, never as an edit to
the PPTX. The result is reproducible, diffable and auditable.

```
                THINKING (agent + core/)                                 RENDERING (engine)
┌──────────────────────────────────────────────────────┐   ┌──────────────────────────────────────────────┐
│ INPUT ──ingest──► inventory (blocks, tables, numbers)│   │ SLIDE SPECIFICATION (resolved.json)          │
│   │                                                  │   │   │                                          │
│   ▼  CONTENT UNDERSTANDING (triage, SKILL §1)        │   │   ▼ pptx/builder ─► painter ─► components    │
│ STORYLINE  core/storyline  (framework, key line,     │   │      text · charts(native) · tables · diag.  │
│            ghost deck, horizontal lint)              │   │   ▼ deck.pptx + build_manifest.json          │
│   ▼                                                  │   │ RENDER  render/renderer (LibreOffice→PDF→PNG)│
│ SLIDE INTENT (purpose, headline, message_type,       │   │   ▼                                          │
│               evidence)  core/headline (lint)        │   │ QA  qa/geometry · qa/render_checks ·         │
│   ▼                                                  │   │     content (planner)  → qa/report (gate)    │
│ VISUAL ENCODING  core/visual_reasoning               │   │   ▼                                          │
│   ▼                                                  │   │ ITERATION qa/autofix → form patches ─────────┼──┐
│ LAYOUT SELECTION core/layout_selector + layouts/*.json│  │         + review packet → agent patches      │  │
│   ▼                                                  │   └──────────────────────────────────────────────┘  │
│ DENSITY core/density  →  PLANNER core/planner ───────┼──► (resolved.json)                                  │
└──────────────────────────────────────────────────────┘◄──────────────── patched spec ─────────────────────┘
```

## 2. Modules

```
MBBslides/
├── SKILL.md                 the agent's operating manual
├── layouts/01_…/…16_…/      43 declarative layouts (JSON) in 16 families
├── src/cpe/
│   ├── spec.py              vocabulary (kinds, 45 visual types, 20 message types, 14 deck types),
│   │                        structural validation, patches
│   ├── ingest/readers.py    txt/md/csv/xlsx/json/pdf/docx/pptx → inventory with traceable numbers
│   ├── core/
│   │   ├── storyline.py     7 frameworks, 14 deck blueprints, archetypes, scaffold, ghost deck, lint
│   │   ├── headline.py      headline lint + check of headline numbers against the evidence
│   │   ├── visual_reasoning.py  message × data shape → visual (with reasons); critique of choices
│   │   ├── layout_selector.py   roles × compatibility × capacity × variety
│   │   ├── density.py       per-zone capacity with real metrics; layout switch; splitting
│   │   └── planner.py       spec → resolved spec (visual, layout, fitting, `_plan` traces)
│   ├── design/
│   │   ├── tokens.py        12-col grid, bands, XS–XXL spacing, type scale, floors, lines,
│   │   │                    WCAG contrast, colour scales
│   │   ├── themes/*.json    meridian · graphite · harbor
│   │   ├── profiles.json    density per profile (board/standard/analytical/status) and deck type
│   │   └── text_metrics.py  text measurement with real glyphs (Liberation Sans ≡ Arial)
│   ├── layout/engine.py     loads the library and resolves zones to boxes in inches
│   ├── pptx/
│   │   ├── painter.py       the only layer touching python-pptx: tokens, no p:style, names
│   │   │                    `cpe|zone|kind|n`, text fitting down to the floor, manifest
│   │   ├── text_components.py  chrome, balanced headline, KPIs, statements, columns, takeaway
│   │   └── builder.py       orchestrates slides → .pptx + manifest
│   ├── charts/              native.py (native charts with a deterministic plot area + overlays),
│   │                        numfmt.py (Excel ⇄ Python formats, round scales, CAGR)
│   ├── tables/table.py      native tables: heatmap, deltas, subtotals, Harvey balls, RAG
│   ├── diagrams/diagrams.py process, timeline, gantt, 2x2, trees, org chart, funnel, pyramid,
│   │                        tile map, flow, journey, layers/operating model, mekko
│   ├── render/renderer.py   headless LibreOffice → PDF → PNG (PyMuPDF) → contact sheet
│   ├── qa/
│   │   ├── geometry.py      ~20 checks on the PPTX
│   │   ├── render_checks.py checks on what LibreOffice drew (PDF spans + ink)
│   │   ├── composition.py   composition metrics on the render (v1.1)
│   │   ├── autofix.py       issues → form patches / author actions
│   │   └── report.py        score, `passed` gate, scoped exemptions, report, review packet
│   ├── compose.py           composition engine: candidates → one render pass → scoring → best (v1.1)
│   ├── evals.py             visual-quality benchmark vs baseline (v1.1)
│   ├── brand/ingest.py      corporate template → brand theme + compatibility report (v1.1)
│   ├── pipeline.py          compose → generate → render → inspect → patch → render loop
│   └── cli.py               `cpe` (ingest, scaffold, outline, lint, recommend, plan, build,
│                            render, qa, run, patch, review, catalog, themes)
├── examples/alvora/         demo deck (draft → QA → patches → final), PPTX and renders
├── examples/gallery/        every exhibit type (26 slides), PPTX and renders
├── examples/brand/          the demo deck on a fictitious corporate template (v1.1)
├── evals/                   stress decks, baseline, results per version (v1.1)
├── .github/workflows/ci.yml lint · tests · regression decks · eval gate
├── tests/                   50 tests (unit, QA stress, render, loop, brand, composition, evals)
└── docs/                    detailed audit, layout catalogue, visual guide, spec, QA codes
```

## 3. Key implementation decisions

**Fixed grid and bands.** Slide 13.333″×7.5″; 0.55″ margins; 12 columns with a 0.22″ gutter;
bands: tracker 0.30″ · headline 0.52″ (2 lines) · body 1.62–6.78″ · footer 6.86″. Layouts only
declare columns and vertical fractions of the body; the engine adds exactly one gutter between
adjacent zones. Result: every slide shares the same alignments without manual coordinates.

**Real metrics in both directions.** `text_metrics` wraps text using the glyph advances of
Liberation Sans (metrics identical to Arial). The same calculation decides *before* (density,
fitting to the floor, balanced headline) and verifies *after* (geometric QA), and the LibreOffice
render checks it against reality.

**Native charts with deterministic geometry.** Every chart fixes its (round) scale and its *plot
area* (`c:manualLayout`, `layoutTarget=inner`). The engine therefore knows the data→inch mapping
and places exact overlays: stacked totals, direct end-of-series labels (no legend), CAGR arrows,
reference lines, forecast shading, connectors and axis-break marks on waterfalls. The data stays
in the embedded workbook (editable). The combo chart is two aligned native panels instead of a
dual axis.

**100% native waterfall.** A stacked bar with an invisible base series; totals/subtotals;
coloured or neutral deltas; the axis is truncated automatically when deltas would be slivers,
with visible break marks so the eye is not misled.

**Shape names as a contract with QA.** `cpe|<zone>|<kind>|<n>` tells QA which zone each shape
belongs to (zone escape), which overlaps are intentional (text on a fill, a label on its leader
line) and which are not (text ink over text ink).

**Three-layer QA + semantic review.** (1a) content on the spec; (1b) geometry on the PPTX;
(1c) render: the text spans of the LibreOffice PDF are compared with the PPTX boxes (overflowing
text, real collisions, real headline line breaks) and the PNG gives ink coverage. (2) The agent
reviews the PNGs with 8 questions and 4 lenses. The `passed` verdict is computed by code;
exemptions require slide + code + reason.

**Bounded self-correction.** The loop applies only form changes (visual type with a concrete fix,
layout alternative, table splitting), records every patch and stops when there are no new patches
or the budget is exhausted. Anything that requires rewording is returned as a precise author
action (e.g. "cut ≈90 words").

**Bilingual (English / Spanish).** The engine's code and documentation are in English, but the
thinking checks understand both languages: the headline lint's verb, generic-noun and
vague-word lexicons, the duration/identifier words ignored by the number check, the storyline
stopwords and the ingestion number parser include English and Spanish forms (`crece`,
`representa`, `resumen`, `mes`, `fase`, `€1.234,5`…). Decks can be written in either language.

## 4. v1.1 — visual intelligence

**Composition as a measured decision.** The layout selector only decides compatibility (roles,
visual family, capacity). `compose.py` then turns each content slide into candidates, from its
compatible layouts × variants (content scale for sparse text/tables/KPIs, table rows stretched to
the zone). It builds all candidates of the deck into one scratch PPTX, renders it once, runs
geometry + render QA per candidate and scores the survivors with `qa/composition.py`. The default
wins ties (by 1.5 points for a variant, 3 points for a different layout, minus 2.5 for repeating
the previous slide's layout), so decks stay consistent. Candidates below 70 are labelled
"compatible but editorially weak". The choice is written back to the spec (`layout`, `_compose`,
`_composed`) and explained in `composition.md`.

**Metrics.** They are computed on a 0.1-inch grid of the body band of the rendered PNG plus the
PDF text spans:
- dead space: largest empty rectangle;
- utilization: ink bounding box;
- balance: ink centre of mass;
- density: dark-ink coverage;
- focal-point strength: focus-colour share × number of solid focus regions;
- visible proof: headline numbers and highlighted items present in the rendered body text;
- hierarchy: headline vs body sizes;
- alignment rhythm: distinct left edges in text zones.

They are heuristics, calibrated on the engine's own output; the eval suite keeps them honest.

**Evals as a gate.** `evals/regression/cases` are decks designed to break the engine. `cpe eval` compares
each case with `evals/regression/baseline.json` (crash, render failure, more QA errors, composition drop,
new flags → exit 1), and CI runs it on every push and pull request. `cpe measure` scores any
existing run, which is how v1.0's renders were compared with v1.1's using the same metrics.

**Brand ingestion.** `brand/ingest.py` reads the theme part (colour scheme, major/minor fonts), the
masters and layouts (placeholders, artwork, backgrounds) and the slide size. It maps colours to
engine roles: dark brand colour → primary, the most saturated non-signal accent → highlight,
reds/greens → negative/positive, derived greys with contrast guarantees. It then picks the
emptiest layout that still shows the master artwork as the base layout, derives margins from the
title placeholder, and turns logos and bars into reserved areas protected by QA. Fonts are
measured with their metric twin when one exists, otherwise with the font fontconfig will render
with; the report states which measurements are exact.

## 5. v1.2 — reproducible, archetype-aware, independently evaluated, template-aware

```
                    ┌──────────── docker/Dockerfile (pinned renderer, fonts, libs) ────────────┐
deck.json → plan → compose ─┬─ candidates: layouts × variants × corporate layouts          │
                            ├─ render once → hard QA filter (geometry + render)           │
                            └─ archetype fitness (qa/archetypes.py) → choose             │
          → build (brand/matching: native · adaptive · cpe) → render → QA → editorial advice │
          → evals: regression (gate) · holdout (report) · human A/B (independent)           │
                    └──────────── environment manifest + fingerprint with every eval ──────┘
```

| module | role |
|---|---|
| `environment.py` | manifest of everything that can move a pixel; render fingerprint; manifest diff |
| `reproducibility.py` | `cpe repro`: render twice, compare hashes, pixels, spans, metrics, QA |
| `results_report.py` | README metrics block generated from `evals/results/latest.json` |
| `qa/archetypes.py` | archetype taxonomy from content, expected profiles, fitness, deviation meanings |
| `qa/composition.py` | measures the observed profile; archetype fitness as score; `score_v1`; `advice_from` |
| `evals.py` | suites (regression / holdout / examples), baseline compare, `record_result` |
| `human.py` | blind A/B rounds: build, local server, votes, statistics (Wilson, Fleiss' κ) |
| `private_holdout.py` | corporate templates in `.private/` → `private_results/`, sanitized summary |
| `brand/model.py` | multi-master analysis: layout features, classification with usage, typography, palette, grid, assets, rules |
| `brand/rescale.py` | 16:9 templates on other page sizes rescaled to the engine canvas |
| `brand/matching.py` | corporate layout candidates per slide, rejections with reasons, per-slide limits |
| `brand/fixtures.py` | synthetic three-master template for tests |

**Decisions.**
- *The archetype comes from content, not from the layout*, so every candidate layout of a slide is
  judged against the same expectations; otherwise the metric would move with the choice it judges.
- *Composition is advice, hard QA is a gate.* Mixing them let a preference (a sparse statement)
  lower a quality score and let a defect be traded against good whitespace.
- *Worst critical metric in the score.* A mean dilutes one severe failure.
- *No overall score.* Regression, holdout and human preference answer different questions with
  different reliability; the README shows them side by side.
- *Holdout discipline in code*: holdout cases are sealed by hash; the holdout suite cannot be
  baselined; the private runner never touches baselines; human votes cannot enter the score.
- *Native corporate layouts only where the template's placeholders can carry the content*
  (structural slides); content slides reuse the corporate layout for its frame and let the engine
  compose the body; everything else falls back explicitly, with the reason recorded.
- *Same environment locally and in CI.* A benchmark whose renderer changes under it measures the
  renderer.

## 5b. v3.1 — Editorial Logic Layer

```
INPUT → CONTENT UNDERSTANDING → FACT MODEL → ANALYSIS → HYPOTHESES / INSIGHTS → STORYLINE
→ SLIDE INTENT → PROPOSITION → ACTION TITLE ENGINE → PARALLEL WORDING GUARANTEE → EDITORIAL QA
→ EVIDENCE → VISUAL ENCODING → LAYOUT SELECTION → SLIDE SPECIFICATION → PPTX GENERATION
→ RENDER → VISUAL QA → ITERATION → FINAL PPTX
```

`src/cpe/editorial/` (compiler, proposition, action_titles, parallel, signatures, qa, report) runs in
`pipeline.run` before `compose()` and `plan()`: the wording contract is settled before any layout is
chosen, every composition candidate gets the same compiled headline, and visual autofix cannot change
wording. `core/headline.lint_headline` remains both the ATE's first layer and the planner's independent
check; `EDITORIAL_NOT_COMPILED` flags a strict spec planned without the compiler. Editorial QA is its
own verdict next to Factual, Visual, Authoring and Brand QA (`qa_report.dimensions`); there is no
composite. In the update workflow `reasoning/messages.py` keeps deciding whether a message holds and
hands the claim that holds now to the ATE (docs/EDITORIAL_LAYER.md).

## 6. Data flow and artefacts

| Step | Input | Output |
|---|---|---|
| ingest | files | `inventory.json/.md` |
| scaffold / editing | deck type | `deck.json` |
| outline / lint | `deck.json` | ghost deck, issues |
| plan | `deck.json` | `resolved.json` (visual, layout, fitting, reasons) |
| build | `resolved.json` | `deck.pptx`, `build_manifest.json` |
| render | `deck.pptx` | `deck.pdf`, `renders/*.png`, `contact_sheet.png` |
| qa | pptx + manifest + pdf/png | `qa_report.json/.md` |
| run | `deck.json` | all of the above + iterations + `review.md` + `deck.autofixed.json` |
| patch / review | patches / `review.json` | corrected spec / semantic verdict |

## 7. Extending the engine

- **New layout:** add a JSON file in `layouts/<family>/` (zones by columns and fractions,
  `accepts`, `compatible_visuals`, `capacity`, `when_to_use`). The library test checks that no
  zone overlaps another or crosses the margins.
- **New visual:** implement `render(p, box, ex)` using only `Painter`, register it in
  `spec.VISUAL_TYPES` and in `diagrams.RENDERERS` / `charts.native.render`, add rules to
  `visual_reasoning.BASE` and an example to the gallery.
- **New theme:** copy `design/themes/meridian.json`; the tests require contrast ≥7:1 (text) and
  ≥4.5:1 (secondary text).
- **New check:** return `issue(level, CODE, message, slide)` from `qa/`; document the code in
  `docs/QA_CODES.md` and, if it can be fixed without touching the message, add the rule to
  `qa/autofix.py`.
- **New eval case:** add a deck to `evals/regression/cases/` with `"eval": {"purpose": …}` (never to the
  holdout during a cycle — see docs/EVALS.md), run
  `cpe eval --update-baseline` and commit the baseline with the case.
- **New language:** extend the lexicons in `core/headline.py` (`VERBS`, `GENERIC_NOUNS`,
  `VAGUE`, `DURATION_RE`) and the stopwords in `core/storyline.py`.


## Reasoning layer (v1.7, in development)

`src/cpe/reasoning/` makes the agent's thinking observable: `facts.py` (sources → atomic facts with
period, basis, unit and cell ranges; derived changes), `grounding.py` (is a number grounded in the
facts a sentence cites — directly or by one bounded operation?), `checks.py` (validators for
project, facts, computed facts, assumptions, hypotheses, insights, storyline, deck plan and the
render spec; hard factuality gates; stopping criteria), `graph.py` (evidence graph and `trace`),
`ghost.py` (ghost deck, evidence enrichment), `benchmark.py` (source-to-deck dimensions, no total).
The deterministic engine stays model-agnostic; the protocol (docs/REASONING_PROTOCOL.md) is
versioned and recorded with every run.
