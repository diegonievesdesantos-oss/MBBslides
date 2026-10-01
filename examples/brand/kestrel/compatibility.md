# Brand ingest report — Kestrel Capital

Template: `kestrel_template.pptx`

**Verdict:** ⚠️ compatible with approximations (see below)

## Presentation

- Canvas: 13.333 × 7.5 in
- Masters: **1** detected · Layouts: **11** · Example slides: **1**
  - m1 `` — 11 layouts, theme `Office Theme` (heading Georgia, body Calibri)

## Typography

- Primary observed: **Georgia** (confidence 0.821, high)
- heading: **Georgia** — declared (too little example text to observe); theme declares Georgia
- body: **Calibri** — declared (too little example text to observe); theme declares Calibri

| candidate | score | declared | observed chars | direct formatting | style-guide mentions | installed |
|---|---|---|---|---|---|---|
| Georgia | 0.821 | yes | 24 | 0 | 0 | no |
| Calibri | 0.179 | yes | 0 | 0 | 0 | no |

Evidence weights: `{"theme": 0.214, "master": 0.143, "usage": 0.643}` · most used sizes: [] pt

## Fonts in this environment

| role | font | declared | observed | installed | renderable | measured with | measurement | LibreOffice fallback |
|---|---|---|---|---|---|---|---|---|
| heading | Georgia | yes | no | no | substituted | DejaVuSerif | approximate | DejaVu Serif |
| body | Calibri | yes | no | no | yes | Carlito | exact | Carlito |

> ⚠️ FONT WARNING — corporate font Georgia is not available in the authoring environment. LibreOffice renders it with DejaVu Serif; text is measured with DejaVuSerif (approximate). Expected risk: line wrapping and box fits may differ in the corporate environment where the font is installed.

> ⚠️ FONT WARNING — corporate font Calibri is not available in the authoring environment. LibreOffice renders it with Carlito; text is measured with Carlito (exact). Expected risk: none for widths (metric-compatible).

## Colours

- Primary brand colour (observed): `#None` · text: `#222222` · supporting: — · neutrals: —
- Share of example slides on a brand-colour background: 0.0

| engine role | colour | source |
|---|---|---|
| primary | `#1B3A2F` | theme |
| secondary | `#2E6B4F` | theme mapping |
| highlight | `#C8A24A` | theme |
| text | `#222222` | theme |
| text_muted | `#6F6F6F` | theme mapping |
| background | `#FFFFFF` | theme mapping |
| positive | `#2E6B4F` | theme mapping |
| negative | `#A33A2B` | theme mapping |

## Grid

- Likely **12-column** system, margins 0.667 / 0.667 in, gutter 0.267 in (explains 1.0 of 4 shape edges; confidence 0.95, high)
- Engine grid overrides: `{"margin_l": 0.7, "margin_r": 0.7, "headline_right_limit": 11.05}`

## Layout families

- one_column: 3
- content: 2
- cover: 1
- section: 1
- two_column: 1
- comparison: 1
- chart_commentary: 1
- image_split: 1

| id | layout | classification (confidence) | observed use on example slides |
|---|---|---|---|
| m1.l1 | Title Slide | cover (0.92) | cover×1 |
| m1.l2 | Title and Content | one_column (0.95) | — |
| m1.l3 | Section Header | section (0.8) | — |
| m1.l4 | Two Content | two_column (0.8) | — |
| m1.l5 | Comparison | comparison (0.8) | — |
| m1.l6 | Title Only | content (0.97) | — |
| m1.l7 | Blank | content (0.8) | — |
| m1.l8 | Content with Caption | chart_commentary (0.45), content (0.35) | — |
| m1.l9 | Picture with Caption | image_split (0.8) | — |
| m1.l10 | Title and Vertical Text | one_column (0.5) | — |
| m1.l11 | Vertical Title and Text | one_column (0.5) | — |

## Assets

- Logos: 1 (top-right×1)
- Icons (distinct small images on slides): 0 · pictures on slides: 0 · vector groups: 0
- Reserved artwork on masters/layouts: 1
- Base layout for engine-drawn slides: **Blank**

## Inferred brand rules

- Headline case: **sentence** ({"sentence": 1.0}, 1 titles)
- Bookend: first and last slides in the brand colour: False (same colour: True; ['1B3A2F', '1B3A2F'])
- Slides on a brand-colour background: 0.0
- Text alignment: {"l": 1.0}
- Content headline: top at 0.0 in, width 0.895 of the slide
- Shapes: rounded share of rectangles None, chevrons 0, most used {}

## Reserved areas (protected by QA)

- picture `Kestrel logo` at (11.2, 0.26) 1.45×0.35 in
- shape `Brand bar` at (0.0, 7.4) 13.333×0.1 in

## Unsupported / not used

- Layout 'Title Slide' has a gradient background (not used as the base layout).

## Notes

- Highlight #C8A24A has contrast 2.4:1 — used for fills only; text in it may be flagged by QA.
- Margins taken from the title placeholder: left 0.70 in, right 0.70 in.
- Headline width limited to end at 11.05 in to keep clear of master artwork.
