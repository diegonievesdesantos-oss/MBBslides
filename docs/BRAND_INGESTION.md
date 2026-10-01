# Corporate template intelligence (`cpe brand ingest`)

```bash
scripts/cpe brand ingest corporate.pptx -o brands/acme [--name "Acme"]
# deck.json: "meta": {"brand": "brands/acme", …}
```

The goal is not "apply the corporate colours to an engine layout" but to **understand the
PowerPoint system** — its masters, layouts, typography, palette, grid, assets and conventions —
and generate slides *on the template's own layouts* when they fit.

## Outputs

| file | content |
|---|---|
| `theme.json` | engine theme: fonts, colour roles, grid overrides, reserved areas, template, **corporate layout catalogue** for the matcher |
| `brand_model.json` | the full model (machine-readable) with evidence and confidence |
| `layout_catalog.json` | every layout: features, classification, observed usage |
| `compatibility.md` / `.json` | the human report (below) |
| `template.pptx` | the template's masters and layouts (example slides removed; rescaled if needed) |

## What is analysed — across ALL masters

Nothing assumes `slide_masters[0]`: every master, its theme part, placeholders, artwork and
layouts are read, plus the example slides (the strongest evidence of how the system is used).

**Layout features:** master and layout id, name, OOXML type, placeholder count and types, title
geometry and position, body geometry, picture / chart / table placeholders, table-compatible
regions, column headers, columns, rows, symmetry, orientation, background (solid / gradient /
picture / full-bleed shape; dark / coloured), content capacity, reserved artwork, artwork inside
the body, footer placeholders, logo.

**Classification:** `cover · section · content · statement · one_column · two_column ·
three_column · image_split · chart · chart_commentary · table · comparison · matrix · process ·
roadmap · timeline · conclusion · closing · special · unknown` with up to three labels and
confidences. Evidence: geometry, placeholder types, background, OOXML type, name hints (weak:
real templates use names like `CUSTOM_4_1_2`) and — weighted more as examples accumulate — the
**observed use** of the layout on the example slides (a two-area layout always used for picture +
text is learned as `image_split`, keeping `two_column` as a lower alternative).

**Typography:** theme fonts (declared), master text styles and master placeholder styles, layout
styles, the characters actually set on the example slides — each run attributed to the font it is
**really drawn in**, following PowerPoint's inheritance (run → shape list style → layout placeholder
→ master placeholder → master text styles → presentation default → theme), with weight-named
families merged ("Inter Black" → Inter) — and **style-guide slides**
(text that names a typeface next to "typography / typeface / font / tipografía"). Weighted
(usage 45%, guide 20%, theme 15%, master 10%, layouts 10%) into a primary font with confidence.
When theme and usage disagree it reports the contradiction, e.g. *"The theme declares Arial, but
95% of the text on the example slides is set in Inter by direct formatting; style-guide slides
name Inter."*

**Palette:** theme scheme per master vs area-weighted fills (slides, layouts, master artwork),
character-weighted text colours **as drawn** (inheritance resolved) and slide backgrounds →
primary brand colour, the page colour (background of the content layouts), the text colour on it,
supporting colours (fills, brand-colour backgrounds, coloured text), neutrals, share of
brand-colour slides; conflicts with the theme reported. Theme slot names are not trusted (some
templates use dk1 / lt1 unconventionally): engine roles are built from the real page / text pair,
so every derived grey keeps its contrast, and each role records its source.

**Grid:** margins from the titles of the content layouts (symmetric when content reaches the
mirrored margin); the column system (4–16 columns × gutter) that best explains the edges of text
and placeholders (pictures and full-bleed artwork excluded), finer grids penalised unless they
explain clearly more, with the share explained as confidence.

**Assets:** logos (the same image on several layouts, small, near a corner, or named so), icons
(distinct small images on slides), vector groups, reserved artwork per master/layout.

**Brand rules:** dominant headline case, bookend (first and last slides in the brand colour),
share of brand-colour slides, text alignment, content headline position and width, rounded share
of rectangles, chevrons. Bookend and brand-colour share are checked on generated decks as editorial
advice (`BRAND_BOOKEND`, `BRAND_COLOUR_SHARE`); a layout used for the last example slide keeps a
`closing` label so closings are generated on it.

## Canvas size

Same size → masters used as they are. Same **16:9 ratio** but a different page (e.g. 10 × 5.625 in)
→ masters and layouts are **rescaled** to 13.333 × 7.5 in (positions, sizes, font sizes, spacing,
insets, line widths) and the report says so; PowerPoint's Slide Size dialog scales the output
back without distortion. Other ratios → colours and fonts only, and the report says the masters
are not used.

## Fonts — never silently different

For each corporate font: declared? observed? installed? renderable (installed or metric-compatible)?
what LibreOffice will draw instead (`fc-match`), what the engine measures with, exact or
approximate. A missing font produces a **FONT WARNING** with the expected risk (line wrapping and
box fits may differ where the font is installed). Any installed font is measured with its own
file. The Docker environment ships common open-licence corporate typefaces (Inter, Roboto, Open
Sans, Lato, Montserrat) and nothing proprietary, so warnings are reproducible.

## Corporate layout matching (builder)

```
SLIDE INTENT → ARCHETYPE → CORPORATE LAYOUT CANDIDATES → CAPACITY / GEOMETRY MATCH
             → COMPOSITION CANDIDATES → RENDER → QA + ARCHETYPE SCORE → BEST CORPORATE LAYOUT
```

| mode | when | what |
|---|---|---|
| **native** | cover, section divider, closing, statement — a corporate layout of that class with confidence ≥ 0.35 | the layout's own placeholders carry the text: typography, colours and positions are the template's (font size fitted to the placeholder; if the template's own text/background pair is unreadable, the text colour is corrected and noted as `NATIVE_TEXT_COLOR`) |
| **adaptive** | content slides — a corporate content layout able to host the body | the layout supplies background, artwork, logo, footer and title position; the engine composes the body in the free area, with per-slide headline / footer limits and reserved areas |
| **cpe** | nothing corporate fits | engine layout on the template's base layout with the corporate theme |

A layout is only a candidate when it is technically able to carry the slide: right class,
light background for engine-drawn bodies, no artwork inside the body, title near the headline
band, and no artwork across the engine's headline or footer bands — every rejection is recorded
with its reason (`build_manifest.json` → `corporate`). The composition engine can render the
next-best corporate layouts as candidates and keep the one with the best QA + archetype fitness.

## Testing without corporate material

`src/cpe/brand/fixtures.py` builds a synthetic **three-master** template (executive / analytical /
narrative masters, each with its own theme and artwork; poorly named layouts; example slides that
reveal usage; contradictory typography — theme fonts vs Inter set by direct formatting and named
on a style-guide slide). `tests/test_corporate_templates.py` checks: all masters and layouts
detected, classification by geometry and usage, font conflict, missing-font warning, logos,
rules, rescaling, and matching that picks layouts from different masters.
