# QA codes

Every issue has `level` (error blocks the gate · warning · info), `code`, `message`, `slide`.
`passed` in `qa_report.json` is true only when there are **zero errors** after scoped exemptions.

## Layer 1a — content (spec, before drawing)

| code | level | remedy |
|---|---|---|
| `AUTO_SPLIT` | warning | Replace the mechanical split by a summary table (top rows + 'Other'). |
| `CONTENT_OVER_CAPACITY` | error | Cut the text (see excess_words) or split the argument across two slides. |
| `DENSITY_AXIS_LABELS` | warning | see message |
| `DENSITY_BULLETS` | warning | Keep the 3-4 bullets that prove the headline. |
| `DENSITY_GANTT_ROWS` | warning | see message |
| `DENSITY_LONG_BULLET` | info | see message |
| `DENSITY_MATRIX_ITEMS` | warning | see message |
| `DENSITY_PROCESS_STEPS` | warning | see message |
| `DENSITY_SHRINK` | info | see message |
| `DENSITY_TABLE_COLS` | warning | see message |
| `DENSITY_TABLE_ROWS` | warning | see message |
| `DENSITY_TREE` | warning | see message |
| `DENSITY_WORDS` | warning | Cut words: keep only what proves the headline. |
| `DUP_ID` | error | see message |
| `SPEC_DATA_SHAPE` | warning | Exhibit data fields given at the top level were moved under `data` (the documented shape); fix the spec. |
| `HEADLINE_LONG` | warning | Cut the headline to the claim. |
| `HEADLINE_NO_VERB` | warning | see message |
| `HEADLINE_NUMBER_UNSUPPORTED` | warning | Add the evidence that produces this number (evidence[].value) or correct the number. |
| `HEADLINE_PLACEHOLDER` | error | Write the headline. |
| `HEADLINE_QUESTION` | info | see message |
| `HEADLINE_SHORT` | info | see message |
| `HEADLINE_TITLE_CASE` | info | see message |
| `HEADLINE_TOPIC` | error | Replace the topic label with a conclusion: what does the data show, and so what? |
| `HEADLINE_TWO_MESSAGES` | warning | Keep one claim in the headline; move the other to the commentary or its own slide. |
| `HEADLINE_UNQUANTIFIED` | info | see message |
| `HEADLINE_VAGUE` | warning | Quantify the claim. |
| `INTENT_EVIDENCE` | warning | see message |
| `INTENT_MISSING` | error | Complete the slide intent (purpose + headline) before rendering. |
| `KIND` | error | see message |
| `LAYOUT_NONE` | error | see message |
| `LAYOUT_SWITCH_DENSITY` | info | see message |
| `MESSAGE_TYPE` | warning | see message |
| `META_DECK_TYPE` | warning | see message |
| `META_TITLE` | error | see message |
| `NO_BODY` | error | see message |
| `NO_SLIDES` | error | see message |
| `SECTION_UNKNOWN` | warning | see message |
| `SOURCE_MISSING` | error | Add the source line (data slides must cite their source). |
| `STORY_DUP_HEADLINE` | warning | see message |
| `STORY_ES_COVERAGE` | warning | see message |
| `STORY_ES_GT` | info | see message |
| `STORY_EXEC_LATE` | warning | see message |
| `STORY_FRAMEWORK` | warning | see message |
| `STORY_GOVERNING` | error | see message |
| `STORY_GT_LONG` | warning | see message |
| `STORY_KEYLINE` | error | see message |
| `STORY_KEYLINE_SIZE` | warning | see message |
| `STORY_LAYOUT_MONOTONY` | warning | see message |
| `STORY_NO_ASK` | info | see message |
| `STORY_NO_EXEC_SUMMARY` | error | Add an executive summary slide after the cover (answer first). |
| `STORY_SECTION_ORDER` | warning | see message |
| `STORY_SECTION_SEQUENCE` | info | see message |
| `STORY_UNSUPPORTED_KEYLINE` | warning | Add a slide proving this key-line point or remove the point. |
| `TABLE_OVER_CAPACITY` | error | Summarise the table to the rows that prove the headline. |
| `VISUAL_TYPE` | error | see message |
| `VIS_BETTER_OPTION` | info | see message |
| `VIS_COLUMN_LABELS` | warning | see message |
| `VIS_COMBO_AXIS` | warning | see message |
| `VIS_DATA_MISMATCH` | error | see message |
| `VIS_LINE_FEW_POINTS` | warning | see message |
| `VIS_NO_TITLE` | info | see message |
| `VIS_OFF_MESSAGE` | info | see message |
| `VIS_PIE_NEGATIVE` | error | see message |
| `VIS_PIE_SLICES` | warning | see message |
| `VIS_STACK_SEGMENTS` | warning | see message |
| `VIS_TIME_VERTICAL` | warning | see message |
| `VIS_TOO_MANY_CATEGORIES` | warning | see message |
| `VIS_TOO_MANY_SERIES` | warning | see message |
| `VIS_UNSORTED` | info | see message |


## Layer 1b — geometry (the .pptx, real font metrics) and 1c — render (what LibreOffice drew)

| code | level | layer | what it detects |
|---|---|---|---|
| `OFF_SLIDE` | error | geometry | shape extends beyond the slide |
| `OUTSIDE_SAFE_AREA` | error | geometry | shape outside the margins (except full-bleed) |
| `OUTSIDE_ZONE` | error | geometry | shape escapes the layout zone it belongs to |
| `TEXT_OVERFLOW` | error | geometry | text needs more height than its box |
| `TEXT_COLLISION` | error | geometry | the ink of two text boxes overlaps |
| `CONNECTOR_THROUGH_TEXT` | warning | geometry | a connector crosses text |
| `FONT_TOO_SMALL` | error/warn | geometry | below 8 pt / below 9 pt outside the footer |
| `FONT_FAMILY` | warning | geometry | font other than the theme font |
| `COLOR_OFF_PALETTE` | warning | geometry | text colour not in the theme palette |
| `LOW_CONTRAST` | error/warn | geometry | contrast < 3.0 / < 4.5 against the fill behind |
| `PLACEHOLDER_TEXT` | error | geometry | TODO / lorem / xx / [..] left in the deck |
| `HEADLINE_LINES` | error | geometry | headline wraps to more than 2 lines |
| `HEADLINE_WIDOW` | warning | geometry | last headline line is a single short word |
| `MISALIGNED` | warning | geometry | left edges that almost (but not exactly) align |
| `SHAPE_COUNT` | warning | geometry | more shapes than the density profile allows |
| `TINY_ELEMENT` | warning | geometry | non-line shape smaller than 0.03 in |
| `EMPTY_ZONE` | warning | geometry | a layout zone received no content |
| `FIT_SHRUNK` | info | geometry | text was shrunk towards the floor to fit |
| `RENDER_TEXT_SPILL` | error | render | rendered text lies outside every text box / table / chart frame |
| `RENDER_OFF_SLIDE` | error | render | rendered text beyond the page |
| `RENDER_OUTSIDE_SAFE` | error | render | rendered text in the margins |
| `RENDER_TEXT_COLLISION` | error | render | two rendered spans overlap |
| `RENDER_HEADLINE_LINES` | error | render | headline renders on more than 2 lines |
| `RENDER_HEADLINE_WIDOW` | warn | render | one short word alone on the last headline line |
| `RENDER_SMALL_TEXT` | error | render | rendered text below 7.5 pt |
| `RENDER_LABEL_TRUNCATED` | error | render | chart axis labels cut with an ellipsis by the renderer |
| `RENDER_LABEL_ROTATED` | error | render | chart axis labels rotated because they do not fit |
| `RENDER_TOO_EMPTY` | warning | render | body ink coverage very low |
| `RENDER_UNBALANCED` | info | render | large empty region next to dense content |
| `BRAND_RESERVED_OVERLAP` | error | geometry | content covers template artwork (logo, bars) of the slide's corporate layout |
| `NATIVE_TEXT_COLOR` | info | geometry | a native corporate layout's own text/background pair was unreadable; the text colour was set for contrast |

## Layer 1d — composition (v1.2: editorial ADVICE, not QA)

Measured on the render as **fitness to the slide's archetype** ([docs/COMPOSITION_SCORING.md](COMPOSITION_SCORING.md)).
Level `advice`: listed under "Editorial advice" in `qa_report.md` / `editorial_advice` in
`qa_report.json`; never counted as errors or warnings, never changes `passed` or the QA score.
Each message states the archetype, the deviation and the expected range.

| code | remedy |
|---|---|
| `COMPOSITION_DEAD_SPACE` | Even the best composition leaves a large empty area: the content is too thin for this kind of slide — add the proof (numbers, comparison) or merge it into a neighbouring slide. |
| `COMPOSITION_UNDERUSED_CANVAS` | The content uses little of the slide for what it is: give it more data/proof, or turn it into a different slide type (statement, KPI). |
| `COMPOSITION_OVERFILLED` | The content crowds the canvas for this kind of slide: cut or split. |
| `COMPOSITION_PROOF_NOT_VISIBLE` | The headline's number or highlighted item is not visible in the exhibit: label it or highlight it. |
| `COMPOSITION_NO_FOCAL_POINT` | Nothing stands out: highlight the one element that proves the headline. |
| `COMPOSITION_NOISY_EMPHASIS` | Too much in the focus colour: keep one highlight and grey the context. |
| `COMPOSITION_OVERDENSE` | Very dense for this kind of slide: cut or split. |
| `COMPOSITION_SPARSE` | Very little ink for this kind of slide: add the proof or merge the slide. |
| `COMPOSITION_OFF_BALANCE` | The visual weight sits on one side: check the layout choice. |
| `COMPOSITION_WEAK_HIERARCHY` | The body text competes with the headline: reduce it or reword as a statement slide. |
| `COMPOSITION_RAGGED_ALIGNMENT` | Many unrelated left edges: align the text blocks. |

### Brand conventions (v1.3, advice)

| code | remedy |
|---|---|
| `BRAND_BOOKEND` | The template's decks open and close on the brand colour: add a closing slide (kind: closing). |
| `BRAND_COLOUR_SHARE` | Fewer brand-colour slides than the template's examples: mark sections with dividers. |

## Layer 2 — semantic visual review (agent)

Eight questions per slide scored 0/1/2 in `review.json` (pass ≥13/16, no 0): one idea · five-second read · hierarchy · no decoration · exhibit proves headline · single focus · right layout · partner-ready. Plus four deck lenses (CEO, CFO, partner, visual editor). `scripts/cpe review review.json`.

## Autofix scope

The loop may change: visual type / sort (when the reasoning engine attached a `fix`), layout (next eligible alternative when body text or an exhibit does not fit), table split, and — before the loop — the composition (layout + content scale + table stretch) chosen by the composition engine. It never rewrites text; those issues become *Actions for the author*.
