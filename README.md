# Consulting Presentation Engine

A consulting-grade presentation engine: it turns information (notes, documents, PDFs, Excel,
CSV, analyses, business cases) into a **native, editable PowerPoint** built on consulting logic —
an explicit storyline (pyramid principle), one idea per slide with conclusion headlines, visuals
chosen by the message, grid-based layouts — plus an **automatic render → QA → fix loop** whose
pass/fail verdict is computed by code.

It is the synthesis of an audit of four reference skills ([AUDIT.md](AUDIT.md)); the
architecture is described in [ARCHITECTURE.md](ARCHITECTURE.md) and the agent's operating
manual is [SKILL.md](SKILL.md).

| | |
|---|---|
| ![demo](examples/alvora/output/2_final/contact_sheet.png) | Demo deck (12 slides, consistent fictitious data): executive summary, market (stacked columns + CAGR), KPIs + combo chart, mekko, waterfall, heatmap, 2×2 positioning matrix, operating model, roadmap, financial impact and decisions. **QA: PASSED, 99.8/100, 0 errors, 0 warnings; visual review: 12/12 slides approved.** |

## What makes it different

- **Thinking before rendering.** Nothing is drawn without a *slide intent* (purpose, headline,
  message type, evidence). The storyline is an object (governing thought + key line + framework)
  and is checked by reading the headlines alone (the *ghost deck*).
- **Verified headlines.** Topic titles and double messages are rejected, and every number in a
  headline must be derivable from the evidence or the exhibit data (values, sums, shares, deltas,
  growth rates, CAGRs).
- **Explainable visual reasoning.** 20 message types × data shape → visual, with the why and
  the why-not recorded.
- **Native and editable.** Native charts (editable data), native tables, diagrams built from
  shapes; no slide is ever an image. No theme shadows, no rounded corners, a single accent colour.
- **Real QA.** Geometry checks with real font metrics, plus a comparison with what LibreOffice
  *actually* draws (overflowing text, collisions, headline line breaks), plus a guided semantic
  review.
- **Bounded self-correction.** The engine fixes form (visual type, layout, splitting); anything
  that requires rewriting is returned as a concrete action. It never truncates sentences.

## Languages

Code and documentation are in English; the engine is **bilingual (English / Spanish)** for
content. The headline lint (verbs, topic nouns, vague words), the number check (durations and
identifiers such as "24 months" / "24 meses", "wave 1" / "fase 1"), the storyline lint and the
ingestion number parser (`1,234.5` and `1.234,5`) understand both languages, so decks can be
written in either.

## Installation

```bash
git clone https://github.com/diegonievesdesantos-oss/MBBslides && cd MBBslides
pip install -r requirements.txt            # python-pptx, Pillow, lxml, PyMuPDF, openpyxl
# rendering: LibreOffice with Impress + Liberation fonts (Arial metrics)
sudo apt-get install -y libreoffice-impress fonts-liberation    # Debian/Ubuntu
# macOS: brew install --cask libreoffice   (Arial is already installed)
pip install pytest && python -m pytest -q  # 44 tests
```

Optional: `pip install -e .` installs the `cpe` command. Without installing: `scripts/cpe <command>`.

## Quick start

```bash
scripts/cpe ingest notes.md data.xlsx report.pdf -o work/inventory.json      # 1. understand the input
scripts/cpe scaffold --deck-type board_presentation --title "…" -o deck.json  # 2. storyline skeleton
#   … the agent writes the governing thought, key line and each slide's intent (SKILL.md §2–§5)
scripts/cpe outline deck.json               # 3. ghost deck: does the story hold from the headlines alone?
scripts/cpe lint deck.json                  # 4. intents, headlines, numbers, visuals, density
scripts/cpe run deck.json -o out/           # 5. plan → pptx → render → QA → autofix (≤3 rounds)
#   review out/contact_sheet.png and out/review.md; write out/review.json and patches.json
scripts/cpe review out/review.json          # 6. semantic visual review
scripts/cpe patch deck.json patches.json && scripts/cpe run deck.json -o out/   # 7. iterate
```

Other commands: `plan`, `build`, `render`, `qa`, `recommend <message_type>`, `catalog`, `themes`.

## Examples

- **`examples/alvora/`** — the end-to-end test deck. `deck_draft.json` is a first draft with real
  problems (bars with time on the vertical axis, commentary that is too long, a topic headline,
  a three-line headline, a missing source). `output/1_draft/` shows the loop: the engine fixes
  form on its own (`VIS_TIME_VERTICAL`: stacked bars → stacked columns, round 2) and returns 6
  author actions that require rewriting (cut words, topic headline, long / double-message /
  three-line headline, missing source). `agent_patches.json` holds the agent's corrections;
  applied to `deck.autofixed.json` they produce exactly `deck.json`, whose final output is in
  `output/2_final/` (PPTX, PDF, one PNG per slide, contact sheet, QA report, visual review).
- **`examples/gallery/`** — 26 slides exercising every exhibit type, the structural slides
  (agenda, dividers, statement) and the `harbor` theme. QA: PASSED, 99.7.

## Deck types

strategy deck · business review · investment memo · board presentation · market analysis ·
commercial due diligence · transformation program · operating model · product strategy ·
financial analysis · sales strategy · implementation roadmap · executive update ·
project steering committee. Each has a default storyline framework, slide archetypes and a
density profile (board / standard / analytical / status). Themes: `meridian`, `graphite`, `harbor`.

## Documentation

| | |
|---|---|
| [SKILL.md](SKILL.md) | the agent's operating manual (when to use, analysis, storyline, headlines, visuals, layouts, density, loop, review, mistakes to avoid) |
| [AUDIT.md](AUDIT.md) · [docs/audit/](docs/audit/) | audit of the 4 reference skills, capability matrix, decisions |
| [ARCHITECTURE.md](ARCHITECTURE.md) | architecture, modules, implementation decisions, how to extend |
| [docs/VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md) | every exhibit type, its data shape and rules |
| [docs/SPEC_REFERENCE.md](docs/SPEC_REFERENCE.md) | deck spec and patch reference |
| [docs/LAYOUT_CATALOG.md](docs/LAYOUT_CATALOG.md) | 43 layouts in 16 families |
| [docs/QA_CODES.md](docs/QA_CODES.md) | every QA code, its severity and remedy |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `RENDER_UNAVAILABLE`, "source file could not be loaded" | The Impress component is missing: `apt-get install libreoffice-impress`. Meanwhile `cpe run --no-render` still runs the geometry QA. |
| Rendering is slow or hangs | Another LibreOffice instance is running: the engine uses a temporary profile per conversion; kill stray instances (`pkill soffice`). |
| Text widths differ from PowerPoint | Install Liberation Sans (or Arial). Without them the engine falls back to an estimator and QA is less precise. |
| `HEADLINE_NUMBER_UNSUPPORTED` | The headline number does not come from the data: add `evidence[].value(s)` or correct the number. |
| `CONTENT_OVER_CAPACITY` | The text does not fit even at the minimum size: cut the indicated number of words or split the slide. |
| `LAYOUT_NONE` | No layout accepts that combination of roles: move the commentary into `takeaway` or split the slide. |
| `AUTO_SPLIT` | The table was split mechanically: better to summarise it (top N + "Other"). |
| PowerPoint offers to "repair" the PPTX | Keep the `deck.json` and reproduce it: the tests reopen every PPTX with python-pptx, but PowerPoint is stricter than LibreOffice about XML ordering. |

## Known limitations

- Verification rendering uses LibreOffice; PowerPoint may break lines slightly differently
  (the engine keeps a 3% safety margin on headlines and uses metric-identical fonts).
- Maps are editable *tile maps* (cartograms) with Europe/Spain presets or custom tiles, not
  choropleth maps with real borders.
- CJK text: measurement uses Liberation Sans; review the render of CJK decks more carefully.
- Storyline quality depends on the agent; the engine structures and checks it, it does not
  invent it.
