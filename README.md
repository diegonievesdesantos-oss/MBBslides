# MBBslides — Consulting Presentation Engine

[![CI](https://github.com/diegonievesdesantos-oss/MBBslides/actions/workflows/ci.yml/badge.svg)](https://github.com/diegonievesdesantos-oss/MBBslides/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

![Demo deck: 12 slides generated, rendered and QA-checked by the engine](examples/alvora/output/2_final/contact_sheet.png)

**Raw files → storyline → native PPTX → visual QA → corrected deck.**

MBBslides turns notes, documents, PDFs, spreadsheets and analyses into a **native, editable
PowerPoint** built the way strategy consultants build decks: an explicit storyline, one message
per slide with conclusion headlines, and visuals chosen by the message. It then renders the deck,
measures its visual quality, and corrects what it can. The pass/fail verdict is computed by code.

> **v1.1** makes visual quality *testable rather than subjective*, adapts the composition to the
> amount of content, and can inherit the visual identity of an existing corporate PowerPoint.

| | Demo deck above (fictitious data) |
|---|---|
| QA gate | **PASSED** · 0 errors · 0 warnings · 99.8/100 |
| Composition score (v1.1 metrics) | **94.4** (v1.0 engine: 91.3) |
| Visual review | 12/12 slides approved |
| Editability | native charts (data editable), native tables, shapes — no slide is an image |

## What's new in v1.1

- **Visual-quality evals** (`cpe eval`). Eight stress decks built to break the engine: sparse
  content, text overload, small and large tables, many series, very long numbers, Spanish content,
  dense diagrams, waterfalls and long headlines. Every render gets a composition score from eight
  metrics: dead space, canvas use, balance, density, focal-point strength, visible proof of the
  headline, hierarchy and alignment rhythm. CI blocks a merge if a case crashes, gains QA errors,
  or loses composition points against [`evals/baseline.json`](evals/baseline.json).
  Measured with the same metrics, the suite went from **77.6 (v1.0) to 83.8 (v1.1)**
  ([details](evals/results/v1.0_vs_v1.1.md)).
- **Composition engine.** Layout selection finds the layouts that are *compatible* with the
  content. The composition engine then renders the candidates (layout × content scale × table
  stretch), scores them, and keeps the one that reads best with *this amount* of content. It also
  names the options that are "technically compatible but editorially weak". Example: on the demo's
  decisions slide, v1.0 left half the slide empty; v1.1 scores its choice 23 points higher.
- **Corporate templates** (`cpe brand ingest template.pptx`). The engine reads the template's theme
  colours, fonts, masters, layouts, placeholders and logos, and writes a compatibility report:
  fonts detected / installed / missing, the substitute used for measuring and for rendering, and
  what is not supported. It never silently produces a different deck. Decks are then generated on
  the template's own masters. [See the example](examples/brand/).
- **Proof on the slide.** When the headline quotes a change, a CAGR, the last period's growth, a
  waterfall's total delta or a top-k share, the exhibit shows it. One-series charts get a single
  default focus instead of all bars in the accent colour.
- **Repo hygiene.** Apache-2.0 license, GitHub Actions (lint, tests, regression decks and evals),
  and 50 tests.

## How it works

```
INPUT → UNDERSTAND → STORYLINE → SLIDE INTENT → VISUAL ENCODING → LAYOUT CANDIDATES
      → COMPOSITION CANDIDATES → RENDER → COMPOSITION SCORING → BEST CANDIDATE
      → PPTX → RENDER → QA (content · geometry · render · composition) → PATCH → FINAL PPTX
```

- **Thinking before rendering.** Nothing is drawn without a *slide intent* (purpose, headline,
  message type, evidence). The storyline is an explicit object (governing thought + key line +
  framework), and you can check it by reading the headlines alone (the *ghost deck*).
- **Verified headlines.** Topic titles and double messages are rejected. Every number in a
  headline must be derivable from the evidence or the exhibit data.
- **Explainable visual reasoning.** 20 message types × data shape → visual, with the why and the
  why-not recorded.
- **Real QA.** Geometry is checked with real font metrics and compared with what LibreOffice
  actually draws; then comes composition scoring and a guided semantic review. The engine fixes
  form on its own; anything that needs rewording comes back as a concrete author action.

## Installation

```bash
git clone https://github.com/diegonievesdesantos-oss/MBBslides && cd MBBslides
pip install -r requirements.txt            # python-pptx, Pillow, lxml, PyMuPDF, openpyxl
# rendering: LibreOffice with Impress + metric-compatible fonts
sudo apt-get install -y libreoffice-impress fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea
# macOS: brew install --cask libreoffice
pip install pytest && python -m pytest -q  # 50 tests
```

Optional: `pip install -e .` installs the `cpe` command. Without installing: `scripts/cpe <command>`.

## Quick start

```bash
scripts/cpe ingest notes.md data.xlsx report.pdf -o work/inventory.json      # 1. understand the input
scripts/cpe scaffold --deck-type board_presentation --title "…" -o deck.json  # 2. storyline skeleton
#   … the agent writes the governing thought, key line and each slide's intent (SKILL.md §2–§5)
scripts/cpe outline deck.json               # 3. ghost deck: does the story hold from the headlines alone?
scripts/cpe lint deck.json                  # 4. intents, headlines, numbers, visuals, density
scripts/cpe run deck.json -o out/           # 5. compose → pptx → render → QA → autofix (≤3 rounds)
#   review out/contact_sheet.png, out/composition.md and out/review.md; write review.json / patches.json
scripts/cpe review out/review.json          # 6. semantic visual review
scripts/cpe patch deck.json patches.json && scripts/cpe run deck.json -o out/   # 7. iterate
```

Corporate identity:

```bash
scripts/cpe brand ingest corporate.pptx -o brands/acme     # theme.json + compatibility.md
# in deck.json:  "meta": {"brand": "brands/acme", …}
```

Quality benchmark:

```bash
scripts/cpe eval                                  # evals/cases vs evals/baseline.json (exit 1 on regression)
scripts/cpe eval --update-baseline                # accept an intentional change
scripts/cpe measure out/                          # composition metrics of any existing run
```

Other commands: `plan`, `build`, `render`, `qa`, `recommend <message_type>`, `catalog`, `themes`.

## Examples

- **[`examples/alvora/`](examples/alvora/)**: the end-to-end test deck. `deck_draft.json` is a
  first draft with real problems (bars with time on the vertical axis, commentary that is too
  long, a topic headline, a three-line headline, a missing source). `output/1_draft/` shows the
  loop: the engine fixes form on its own and returns 6 author actions that require rewriting.
  `agent_patches.json` holds the agent's corrections; applied to `deck.autofixed.json` they
  reproduce `deck.json` (plus the engine's recorded composition choices). The final result is in
  `output/2_final/`: PPTX, PDF, one PNG per slide, QA report, composition decisions and visual
  review.
- **[`examples/brand/`](examples/brand/)**: the same deck generated on a fictitious corporate
  template (Kestrel Capital: Georgia/Calibri, its own colours, a logo and a bar on the master),
  with the ingestion's compatibility report.
- **[`examples/gallery/`](examples/gallery/)**: 26 slides exercising every exhibit type, the
  structural slides and the `harbor` theme.

## Languages

Code and documentation are in English. The engine is **bilingual (English / Spanish)** for content:
the headline lint (verbs, topic nouns, vague words), the number check (durations and identifiers
such as "24 months" / "24 meses", "wave 1" / "fase 1", decimal commas such as "4,1%"), the storyline
lint and the ingestion number parser understand both languages.

## Deck types

strategy deck · business review · investment memo · board presentation · market analysis ·
commercial due diligence · transformation program · operating model · product strategy ·
financial analysis · sales strategy · implementation roadmap · executive update ·
project steering committee. Each has a default storyline framework, slide archetypes and a
density profile (board / standard / analytical / status). Themes: `meridian`, `graphite`,
`harbor`, or any ingested brand.

## Documentation

| | |
|---|---|
| [SKILL.md](SKILL.md) | the agent's operating manual |
| [ARCHITECTURE.md](ARCHITECTURE.md) | architecture, modules, implementation decisions, how to extend |
| [AUDIT.md](AUDIT.md) · [docs/audit/](docs/audit/) | audit of the 4 reference skills, capability matrix, decisions |
| [CHANGELOG.md](CHANGELOG.md) | release notes |
| [docs/VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md) | every exhibit type, its data shape and rules |
| [docs/SPEC_REFERENCE.md](docs/SPEC_REFERENCE.md) | deck spec and patch reference |
| [docs/LAYOUT_CATALOG.md](docs/LAYOUT_CATALOG.md) | 43 layouts in 16 families |
| [docs/QA_CODES.md](docs/QA_CODES.md) | every QA code, its severity and remedy |
| [evals/](evals/) | the benchmark, baseline and results |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `RENDER_UNAVAILABLE`, "source file could not be loaded" | The Impress component is missing: `apt-get install libreoffice-impress`. Meanwhile `cpe run --no-render` still runs the geometry QA (no composition engine). |
| Rendering is slow or hangs | Another LibreOffice instance is running: the engine uses a temporary profile per conversion; kill stray instances (`pkill soffice`). |
| Text widths differ from PowerPoint | Install the fonts (or their metric twins: Liberation for Arial/Times, Carlito for Calibri, Caladea for Cambria). The brand report says which fonts are measured exactly and which only approximately. |
| `cpe eval` fails after an intended change | Read `eval_report.md`; if the change is intended, run `cpe eval --update-baseline` and commit the new baseline with the change. |
| `COMPOSITION_DEAD_SPACE` / `COMPOSITION_UNDERUSED_CANVAS` | Even the best composition leaves the slide half empty: the content is too thin; add the proof or merge the slide. |
| `BRAND_RESERVED_OVERLAP` | Content covers the template's logo or artwork: shorten the element or pick another layout. |
| `HEADLINE_NUMBER_UNSUPPORTED` | The headline number does not come from the data: add `evidence[].value(s)` or correct the number. |
| `CONTENT_OVER_CAPACITY` | The text does not fit even at the minimum size: cut the indicated number of words or split the slide. |
| PowerPoint offers to "repair" the PPTX | Keep the `deck.json` and reproduce it: the tests reopen every PPTX with python-pptx, but PowerPoint is stricter than LibreOffice about XML ordering. |

## Known limitations

- Verification rendering uses LibreOffice; PowerPoint may break lines slightly differently.
- Brand templates must use the 13.333×7.5 in canvas for their masters to be used. Other sizes get
  colours and fonts only, and the report says so.
- Maps are editable *tile maps* (cartograms), not choropleth maps with real borders.
- Composition metrics are heuristics calibrated on this engine's own output; they catch the
  failures in the eval suite but do not replace a human visual review.
- Storyline quality depends on the agent; the engine structures and checks it, it does not invent it.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
