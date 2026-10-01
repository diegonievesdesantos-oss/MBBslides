# MBBslides — Consulting Presentation Engine

[![CI](https://github.com/diegonievesdesantos-oss/MBBslides/actions/workflows/ci.yml/badge.svg)](https://github.com/diegonievesdesantos-oss/MBBslides/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

![Demo deck: 12 slides generated, rendered and QA-checked by the engine](examples/alvora/output/2_final/contact_sheet.png)

**Raw files → storyline → native PPTX → visual QA → corrected deck.**

MBBslides turns notes, documents, PDFs, spreadsheets and analyses into a **native, editable
PowerPoint** built the way strategy consultants build decks: an explicit storyline, one message
per slide with conclusion headlines, and visuals chosen by the message. It then renders the deck,
measures its visual quality, and corrects what it can. The pass/fail verdict is computed by code.

> **v1.2** makes visual quality *reproducible, archetype-aware and independently evaluable*, and
> understands real corporate PowerPoint systems — every master, layout, font and convention.

<!-- metrics:start (generated from evals/results/latest.json by `cpe results readme`; do not edit) -->

Three independent signals, never combined into one number ([why](docs/EVALS.md)):

| signal | what it measures | current |
|---|---|---|
| **Regression** | archetype-fitness composition score over the development suite (10 decks, 39 slides); gates CI | **87.3**/100 · QA errors 0 |
| **Holdout** | archetype-fitness composition score on public cases kept out of development (5 decks, 27 slides); reported, never tuned on — **no longer blind**: v1.3 re-run. These cases were reviewed visually during v1.2, so they are no longer blind: the v1.2 result (81.0, rules frozen at e3b63e1) is the last unbiased holdout number (CHANGELOG 1.2.0). New sealed cases are needed for v1.4. | **81.2**/100 · QA errors 0 |
| **Human preference** | blind A/B votes (`cpe human`) | round r1 built (40 blind pairs, 3 comparisons) — awaiting votes |
| Private corporate template | brand-ingest understanding of a real corporate template (sanitized) | development data since v1.3 (its v1.2 findings drove the fixes, so it is no longer a holdout): 1 master(s), 54 layouts, 32% classified with confidence ≥ 0.5; font conflict detected; test deck QA passed; agreement with the human brand spec 21/22 |

| example deck | QA gate | QA score | archetype-fitness composition score |
|---|---|---|---|
| `alvora` | PASSED · 0 errors · 0 warnings | 99.8 | 99.8 |
| `gallery` | PASSED · 0 errors · 0 warnings | 99.8 | 99.0 |
| `alvora_on_kestrel` | PASSED · 0 errors · 0 warnings | 99.7 | 99.5 |

<sub>engine 1.3.1 · LibreOffice 24.2.7.2 420(Build:2) · fontconfig 2.15.0 · container `mbbslides-visual:1.3@sha256:bb5bbbdd55bcec5db567781c63574da1a4b2fc4504446d6fea23f5197f59d278` · render fingerprint `f98cee49d123ed5f`</sub>

<!-- metrics:end -->

## What's new in v1.3

Corporate templates are read through PowerPoint's inheritance chain: the font and colour text is
really drawn in (not what the theme declares), weight-named families merged, page and text colours
from what the template draws, grid from its content layouts, closings learned from use, and
deck-level brand advice (bookend, share of brand-colour slides). Open-licence corporate typefaces
(Inter, Roboto, Open Sans, Lato, Montserrat) are in the visual environment. See
[CHANGELOG.md](CHANGELOG.md).

## What's new in v1.2

- **Reproducible benchmark.** One pinned visual environment (`docker/Dockerfile`: base image by
  digest, Ubuntu archive snapshot, exact LibreOffice / fontconfig / FreeType / HarfBuzz / FriBiDi /
  font versions, locked Python packages) used locally (`scripts/cpe-docker`) and in CI. Every eval
  records an environment manifest and render fingerprint; `cpe repro` renders twice and requires
  pixel-identical output. CI runs on `ubuntu-24.04` with Node 24 actions pinned to SHAs.
  [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)
- **Archetype-aware composition.** A statement slide should breathe; a table should not float in
  half an empty slide. 17 archetypes, each with an expected visual profile; the composition score is
  now *fitness to the archetype*. Composition is editorial advice, separate from hard QA; candidate
  selection names layouts that are "technically compatible but inappropriate for this content
  volume". [docs/COMPOSITION_SCORING.md](docs/COMPOSITION_SCORING.md)
- **Three separate evaluation signals.** Regression (development set, gates CI) ≠ holdout (sealed
  unseen cases + private corporate templates, reported, never tuned on) ≠ human preference (a blind
  A/B tool with Wilson intervals and inter-rater agreement). Never merged into one number.
  [docs/EVALS.md](docs/EVALS.md)
- **Corporate template intelligence.** `cpe brand ingest` reads every master, classifies every
  layout by geometry and by how the example slides use it, infers typography (theme vs actual
  usage, with conflicts), palette, grid, logos and brand rules, and generates slides on the
  template's own layouts (native → adaptive → fallback). [docs/BRAND_INGESTION.md](docs/BRAND_INGESTION.md)
- `evals/results/latest.json` is the single source of truth: the table above is generated from it.

v1.1 introduced the composition metrics, the composition engine, `cpe eval` and brand ingestion;
see [CHANGELOG.md](CHANGELOG.md).

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
pip install pytest && python -m pytest -q  # 85 tests
```

Reproducible renders (recommended for benchmarks): `scripts/cpe-docker <command>` runs the same
pinned environment as CI (Docker required; the image is built on first use).

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

Evaluation (three separate signals, [docs/EVALS.md](docs/EVALS.md)):

```bash
scripts/cpe-docker eval --suite regression        # development set vs baseline (exit 1 on regression)
scripts/cpe-docker eval --suite regression --update-baseline --record   # accept an intended change
scripts/cpe-docker eval --suite holdout --record  # sealed unseen cases: reported, never baselined
scripts/cpe holdout private                       # corporate templates in .private/ (git-ignored)
scripts/cpe human serve evals/human_reference/rounds/r1   # blind A/B page on localhost
scripts/cpe human report evals/human_reference/rounds/r1 --record
scripts/cpe repro examples/alvora/deck.json       # render twice, require identical output
scripts/cpe results readme                        # regenerate the metrics table from latest.json
scripts/cpe measure out/                          # composition metrics of any existing run
```

Other commands: `plan`, `build`, `render`, `qa`, `recommend <message_type>`, `catalog`, `themes`.

## Examples

- **[`examples/alvora/`](examples/alvora/)**: the end-to-end test deck. `deck_draft.json` is a
  first draft with real problems (bars with time on the vertical axis, commentary that is too
  long, a topic headline, an over-long double-message headline, a missing source). `output/1_draft/`
  shows the loop: the engine fixes form on its own and returns 5 author actions that require rewriting.
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
| [docs/EVALS.md](docs/EVALS.md) | regression ≠ holdout ≠ human evaluation, holdout protocol, A/B statistics |
| [docs/COMPOSITION_SCORING.md](docs/COMPOSITION_SCORING.md) | archetypes, expected profiles, fitness, hard QA vs preference |
| [docs/BRAND_INGESTION.md](docs/BRAND_INGESTION.md) | corporate template intelligence and layout matching |
| [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) | pinned environment, manifest, reproducibility test, CI |
| [evals/](evals/) | the suites, baseline and results |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `RENDER_UNAVAILABLE`, "source file could not be loaded" | The Impress component is missing: `apt-get install libreoffice-impress`. Meanwhile `cpe run --no-render` still runs the geometry QA (no composition engine). |
| Rendering is slow or hangs | Another LibreOffice instance is running: the engine uses a temporary profile per conversion; kill stray instances (`pkill soffice`). |
| Text widths differ from PowerPoint | Install the fonts (or their metric twins: Liberation for Arial/Times, Carlito for Calibri, Caladea for Cambria). The brand report says which fonts are measured exactly and which only approximately. |
| `cpe eval` fails after an intended change | Read `eval_report.md`; if the change is intended, run `cpe eval --update-baseline` and commit the new baseline with the change. |
| `COMPOSITION_*` in "Editorial advice" | A preference, not a QA defect (the verdict is unaffected): the composition does not fit what the slide is (e.g. a table using half the slide). Add the proof, merge the slide or accept it. |
| `FONT WARNING` in the brand report | The corporate font is not installed here: text is measured and rendered with a substitute. Install the font or accept approximate line breaks. |
| Scores differ from CI / the README | Run through `scripts/cpe-docker`; `eval_report.md` names what differs in the environment. |
| `BRAND_RESERVED_OVERLAP` | Content covers the template's logo or artwork: shorten the element or pick another layout. |
| `HEADLINE_NUMBER_UNSUPPORTED` | The headline number does not come from the data: add `evidence[].value(s)` or correct the number. |
| `CONTENT_OVER_CAPACITY` | The text does not fit even at the minimum size: cut the indicated number of words or split the slide. |
| PowerPoint offers to "repair" the PPTX | Keep the `deck.json` and reproduce it: the tests reopen every PPTX with python-pptx, but PowerPoint is stricter than LibreOffice about XML ordering. |

## Known limitations

- Verification rendering uses LibreOffice; PowerPoint may break lines slightly differently.
- Brand templates must be 16:9 for their masters to be used (10 in pages are rescaled). Other
  ratios get colours and fonts only, and the report says so.
- Brand inference has been validated on one real corporate template (which is now development
  data) and on synthetic templates; a new unseen corporate template is needed to measure how it
  generalises.
- The proof check does not yet recognise derived headline numbers (a sum, a ratio) as proven.
- Human-preference results depend on the votes collected; round r1 is built and awaiting votes.
- Maps are editable *tile maps* (cartograms), not choropleth maps with real borders.
- Composition fitness is a heuristic calibrated on the development set; the holdout gap and the
  human A/B rounds exist to tell how well it generalises. It does not replace a visual review.
- Storyline quality depends on the agent; the engine structures and checks it, it does not invent it.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
