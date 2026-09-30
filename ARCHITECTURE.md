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
│   │   ├── autofix.py       issues → form patches / author actions
│   │   └── report.py        score, `passed` gate, scoped exemptions, report, review packet
│   ├── pipeline.py          generate → render → inspect → patch → render loop
│   └── cli.py               `cpe` (ingest, scaffold, outline, lint, recommend, plan, build,
│                            render, qa, run, patch, review, catalog, themes)
├── examples/alvora/         demo deck (draft → QA → patches → final), PPTX and renders
├── examples/gallery/        every exhibit type (26 slides), PPTX and renders
├── tests/                   44 tests (unit, QA stress, render, loop)
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

## 4. Data flow and artefacts

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

## 5. Extending the engine

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
- **New language:** extend the lexicons in `core/headline.py` (`VERBS`, `GENERIC_NOUNS`,
  `VAGUE`, `DURATION_RE`) and the stopwords in `core/storyline.py`.
