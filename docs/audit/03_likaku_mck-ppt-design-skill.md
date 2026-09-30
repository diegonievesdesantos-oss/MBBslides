# Audit — likaku/Mck-ppt-design-skill (v2.3.3-harness)

Repo: `/tmp/claude-0/ref/Mck-ppt-design-skill` (HEAD `e190e08`). Artifacts produced during audit: `/tmp/claude-0/ref/out_likaku/` (qa_all.pptx/pdf = 68-slide engine test deck, ai_enterprise.pptx/pdf = 33-slide shipped storyline, `qa_report.json`, `ai_qa.json`, `gate/gate_result.json`, per-slide PNGs, contact sheets `sheet1..6.png`).

Size: `mck_ppt/engine.py` 3,249 lines, `qa.py` 915, `review.py` 722, `core.py` 302, `deck_builder.py` 159, `constants.py` 82, `cover_image.py` 318, storyline `ai_enterprise.py` 601; `run_qa_tests.py` 335; gate scripts 169 + 359; docs ≈ 1.1k lines (SKILL.md 303, README 406, CHANGELOG 367, references ≈ 600, experiences ≈ 150). Mostly Chinese-language docs; Chinese-first defaults inside the engine.

---

## A. Problem it solves

An LLM writing raw python-pptx code for every slide produces slow, token-heavy, inconsistent, and sometimes corrupt decks (v1 drew donuts with 2,800 `add_rect` calls — CHANGELOG 2.0.0). This repo:

1. Puts a **fixed "McKinsey-like" design system** (navy/grays, Georgia/Arial/KaiTi, 13.333×7.5 in, fixed vertical grid) into constants.
2. Wraps python-pptx in **one method per slide archetype** (`MckEngine.<layout>(...)`, 67 methods). The LLM only picks a layout and fills its arguments. README calls this the "GPU→CPU shift": about 20 tokens per chart instead of thousands.
3. Adds a **"Harness"** process: a 5-stage flow (brief → outline.json → content.json → render → deliver), with *machine-readable gates* (`gate_check_s3.py`, `gate_check.py` write JSON `passed` booleans). The goal is to stop the LLM from declaring "QA passed" on its own authority.
4. Adds **post-render geometric QA** (`qa.py`) plus a narrative/density review and a regex-based auto-fix (`review.py`).
5. Adds a **self-refinement memory** (`experiences/*.md`). The LLM is told to append "pattern-level" lessons.

It is aimed at Chinese business/strategy decks produced by an agent (WorkBuddy/Codebuddy, Claude, Cursor).

---

## B. Architecture

```
SKILL.md (router + hard rules + anti-patterns)
  └─ references/ (INDEX.md stage→file map, team/, framework/, layout-matrix.yaml, scripts/)
  └─ experiences/*.md (lesson log)
mck_ppt/
  constants.py   design tokens (colors, grid, type scale, fonts)
  core.py        primitives + XML sanitation
  engine.py      MckEngine: 67 layout methods, save()
  deck_builder.py DeckBuilder: storyline(list[dict]) → getattr(eng, type)(**data)
  qa.py          PptQA: geometric/text heuristics → QAReport(score, errors)
  review.py      NarrativeReviewer + SlideReviewer + AutoFixPipeline
  cover_image.py Tencent Hunyuan image gen + rembg + tint + Bézier curves (optional)
  storylines/ai_enterprise.py  33-slide sample STORYLINE
references/scripts/gate_check_s3.py  content.json validator → gate_s3.json
references/scripts/gate_check.py     wraps PptQA, whitelists categories → gate_result.json
run_qa_tests.py  builds one slide per method, runs PptQA, maps scores
```

### Key modules and functions

- **constants.py** (whole file): tokens (see "Design tokens" below). `ACCENT_PAIRS` (constants.py:37-42) is a list of (accent, light bg) pairs for iterating over parallel items.
- **core.py**
  - `_clean_shape` (core.py:25) removes `p:style` from each shape.
  - `full_cleanup(outpath)` (core.py:33-53) rewrites the zip after save. It removes every `p:style` in every XML part and strips `outerShdw/innerShdw/scene3d/sp3d` from theme parts. It is called by `MckEngine.save` (engine.py:3242-3250), by DeckBuilder, and after each autofix save.
  - `set_ea_font` (core.py:60) injects `<a:ea typeface="KaiTi">` into each run.
  - `add_text` (core.py:74-104) is the single text primitive:
    - word_wrap on, `auto_size=None` (no autofit), all insets 45720 EMU (0.05").
    - anchor set by writing `bodyPr@anchor` directly.
    - a list[str] becomes one paragraph per item, with `space_before=line_spacing` (default 6pt).
    - **line spacing rule (core.py:100)**: ≥18pt uses a multiple of 0.93; smaller sizes use fixed `Pt(size*1.35)`. This fixed value is the CJK line-overlap fix from v1.5.0.
    - EA font is set on every run.
  - `add_rect` (flat fill, no line, cleaned) and `add_hline` (lines are drawn as thin rects, never connectors; core.py:117-120).
  - `add_oval` (numbered badge, 0.45", 14pt bold, zero insets).
  - `add_image_placeholder` (gray D9D9D9 box, crosshair, `[ label ]`).
  - `add_action_title` (core.py:163-171): 22pt bold Georgia black, **bottom-anchored** in a 0.9" box at y=0.15, with a 0.5pt black rule at y=1.05.
  - `add_source` (9pt MED_GRAY at y=7.05), `add_page_number` ("n/total" at 12.2,7.1), `add_bottom_bar` (BG_GRAY bar 0.65" at y=6.2 with navy label and body).
  - `add_block_arc` (core.py:212-261): BLOCK_ARC preset with `adj1/adj2/adj3`. It converts math-convention degrees to PPT convention (clockwise from 12 o'clock, 60000ths of a degree). `inner_ratio` 0-50000 sets the ring thickness.
  - `add_color_legend`, and `draw_harvey_ball` (a quarter/half fill made by masking with white rectangles, core.py:276-302).
- **engine.py `MckEngine`**:
  - `__init__` builds a blank `Presentation()` at 16:9 and uses layout 6 (Blank) for every slide (engine.py:38-44).
  - `_ns()` adds a slide and increments the page counter; `_footer()` adds source and page number.
  - Every layout method is **imperative absolute-coordinate drawing**, mostly hard-coded inches, with a few dynamic sizes:
    - `data_table` row_h = `min(0.95", avail/n)`, and the font drops to 10pt if row_h < 0.6" (engine.py:292-299).
    - `table_insight` row_h = `min(1.55", avail/n)`, font 14→12 (engine.py:358-363).
    - `process_chevron` implements Guard-Rail 10 (engine.py:734-743): `step_w=min(2.6", (CW-0.35"(n-1))/n)`, header font 18→14 if step_w < 2.0", desc 14→12 if < 1.8".
    - `vertical_steps` step_h = `min(1.1", avail/n)`, small fonts if step_h < 0.85" (engine.py:1206-1214).
    - `checklist` row_h = `min(0.85", avail/n)` (engine.py:1622-1628).
    - `value_chain` fills CW and the height down to the bar/source (engine.py:1658-1666).
    - `numbered_list_panel` clamps row_h to [0.85", 1.8"] (engine.py:2927-2935).
    - `cover` title height = 0.8" + 0.62"×(lines-1), counting only explicit `\n` (engine.py:98-104).
  - Charts are **not native charts**; they are drawn with rectangles and ovals (grouped_bar engine.py:1691, stacked_bar 1757, waterfall 2050, line_chart 2104 draws the line as *rectangles spanning each segment's bbox*, pareto 2154 has no cumulative line, stacked_area 2477 is really stacked columns, bubble 2250 uses ovals). Donut, pie and gauge use BLOCK_ARC. `grep add_chart|XL_CHART|add_table` returns nothing, so there are **no native charts and no native tables**.
  - `multi_bar_panel` (engine.py:2982-3236) is the most sophisticated method. It draws 2-3 panels with int-coerced EMU coordinates, `**bold**` markup in titles, headroom (`usable_h = chart_h*0.82`), and CAGR arrows made from a rotated RIGHT_ARROW whose shaft and head are tuned through `adj1/adj2` XML.
  - `table_insight` (312-468) is the "flagship": a table on the left, a chevron, and a gray insight panel on the right. It supports `**bold**` in cells.
  - `save()` (3242) runs `prs.save` and then `full_cleanup`.
- **deck_builder.py**: `DeckBuilder.build(storyline, path)` (lines 37-94) dispatches `{'type','data'}` to engine methods and swallows exceptions per slide. Its `qa_validate` (96-145) checks only off-slide bounds with a ±0.5" slack and negative sizes. It prints "✓ QA passed" even when `PptQA` reports 28 errors on the same file (verified; see E).
- **qa.py `PptQA`**: 9 per-slide checks plus 1 global check (listed in detail in F.1). `_estimate_text_height` (qa.py:217-261) is the shared text-fit model. `QAReport.passed` = no ERRORs. Score = 100 minus a penalty per issue.
- **review.py**:
  - `NarrativeReviewer` runs 3 checks.
  - `SlideReviewer` combines layout and narrative reports.
  - `AutoFixPipeline.run` (review.py:350-396) loops up to 3 rounds over text_overflow ERRORs. The fix chain is redundancy regex → language map (disabled, empty) → compression regex → restructure (truncates clauses) → shrink 1pt steps up to 4 times, respecting floors. It then runs `_harmonize_peer_fonts`, which sets each peer group to its min size.
- **gate_check.py**: runs PptQA, then subtracts `ENGINE_BUG_WHITELIST={"peer_font_inconsistency","chart_legend_overflow"}` (gate_check.py:46-49). `passed = user_code_errors==0`, written to `gate_result.json`.
- **gate_check_s3.py**: per-layout validators routed through `LAYOUT_CHECKERS` (413-437), plus a source check and a "title >10 chars" check. Unknown layouts only get `check_source`.

### Data flow

User brief → (LLM) `brief.md` → (LLM) `outline.json` {slides:[{idx,layout,title,key_point}]} → (LLM) `content.json` (per-slide args + source) → `gate_check_s3.py` → gate_s3.json → (LLM) writes a Python render script calling `eng.<layout>(**args)`, *or* `DeckBuilder.build(STORYLINE)` → `.pptx` (`full_cleanup`) → `gate_check.py` (PptQA) → gate_result.json → [fix code and re-render] → deliver, and append to experiences/*.md.

Note: content.json is **not consumed by any code**. The LLM hand-translates it into a render script; DeckBuilder takes a Python list, not the JSON. The S3 gate validates a JSON schema that nothing then executes.

---

## C. Operating flow (as specified in SKILL.md)

- **S1 Brief.** Read brand-guide. Collect audience, goal, duration (1 min per slide), up to 5 key messages, and data sources. Write `ppt-project-{slug}/brief.md`. Gate: the LLM self-checks that 3 fields are non-empty.
- **S2 Structure.** Read engine-api.md and layout-matrix.yaml. Page count comes from duration. Pick a layout per slide and write a one-sentence `key_point`. Gate: LLM self-check that
  - a cover exists,
  - `count ≤ duration*1.2`,
  - every layout is in the matrix,
  - titles are sentences (>10 chars, contain a verb),
  - `two_column_text ≤ 1`.
- **S3 Content.** Read guard-rails and experiences. Write copy, data and a source for every slide, respecting the char_budget. Gate: `gate_check_s3.py` must print `"passed": true`.
- **S4 Render+QA.** Generate a render script, run it, then run `gate_check.py`. Fix `user_code_errors` and repeat until passed.
- **S5 Deliver + self-refine.** Confirm that `gate_result.json` passed. Any pattern-level fix must be appended to `experiences/{overflow|chart-limits|layout-pitfalls|cjk-issues}.md` using a Problem / Root Cause / Fix / Rule template.
- **Other flow elements.** A fast track (≤5 slides, no charts, user says "quick") skips the S2/S3 gates. Checkpoint/resume infers the stage from which files exist (SKILL.md "Checkpoint"). "TaskCreate" drives progress with 5 tasks.
- **Anti-pattern preamble.** The file opens with three observed failure modes: (1) verbal "gate passed", (2) S3 "checked in my head", (3) using the "engine_bug" label as an escape hatch. Each is answered with "run the script and read the JSON".

---

## D. Strengths

1. **Clear separation of decisions from deterministic drawing.** The LLM chooses layouts and content; Python owns coordinates. This yields big token and latency savings and repeatable output.
2. **Machine-derived gates.** "passed is a Python bool, not an LLM claim", the exemption list lives in code, and there is an explicit anti-pattern list. This is the best idea in the repo and ports directly.
3. **Corruption hardening.**
   - No connectors (lines are thin rects).
   - `p:style` is removed per shape *and* by a post-save zip sweep.
   - Theme shadows and 3D are stripped.
   - QA flags `<p:cxnSp>` and leftover `p:style`.
   - `multi_bar_panel` coerces coordinates to int EMU (float EMU produces invalid XML).
4. **CJK specifics that actually matter.**
   - `a:ea` typeface on every run.
   - Fixed-point line spacing (1.35×) to prevent wrapped CJK lines from overlapping.
   - CJK=1.0 em / Latin=0.55 em width heuristic.
   - CJK line-height factor of 1.4 in estimates.
5. **BLOCK_ARC donut/pie/gauge** math (`add_block_arc`). Native, editable, 1 shape per segment.
6. **Useful QA ideas beyond bbox checks.** Peer-font consistency (shapes sharing a y are "peers"), text–separator-line collision, grid-based whitespace coverage with named dead zones, and legend-label overflow.
7. **Dynamic-sizing patterns.** Guard-rails 8/10: `(CW - gap*(n-1))/n`, `min(max_h, avail/n)`, and font step-down when cells get small.
8. **Layout capacity matrix.** Max items and char budget per field (e.g., donut ≤6 segments, chevron ≤5 steps, four_column ≤4). This is a good *concept* for pre-render validation.
9. **Editorial layouts worth copying visually.** `table_insight` (table, chevron, gray "implications" panel), `multi_bar_panel` (small multiples with CAGR arrows), `before_after` (vertical divider with a circled ">"), the staircase `pyramid`, and bottom "takeaway" bars.
10. **Honest engineering journal.** The CHANGELOG and experiences document concrete failure causes (e.g., the 0.45" oval cannot hold a `\n` label; the cover subtitle was fixed-y).

---

## E. Weaknesses (concrete, verified)

**Rendering evidence.** `run_qa_tests.py` (68 slides) scores **82/100 with 41 ERRORs**. `gate_check.py` on the same deck reports 15 user_code_errors, 26 whitelisted and 62 warnings, i.e. **FAIL on its own showcase**. The shipped storyline deck scores 89/100 with **28 ERRORs**, while `DeckBuilder` printed "✓ QA passed".

Visual defects I saw in rendered PNGs (sheets 1-6):

- **cover_long** (qa_all s2): a 5-line wrapped title overlaps the subtitle, author and date. Title height counts only `\n`, not wrapping.
- **pyramid/staircase** (s18): runs off the right edge by 0.83". `col_w` is a fixed 3.6"×n and centering pushes x negative; "Vision" is clipped on the left.
- **process_chevron** (s19): "Discover/y" breaks mid-word in a 2.6" box. The storyline s6 badges contain CJK 2-char labels that overflow the 0.45" ovals.
- **funnel** (s23): "Decision/Purchase" labels render as vertical one-letter columns (width becomes ≤0.4" after the inset).
- **pros_cons** (s26): the "Recommendation" label wraps in a fixed 1.5" box.
- **timeline** (s36, storyline s4): the last label overflows by 0.47". This is *documented* as an engine bug and then whitelisted instead of fixed. The fix is trivial: clamp the label box to CW.
- **waterfall** (s49): the test passes colors where the API expects 'base'/'up'/'down' strings. Everything renders red and the base bar is pushed below the slide by 1.59". There is no input validation. With correct input (storyline s29) it works, but the value labels use Georgia.
- **line_chart** (s50): `values` must be normalized 0-1 (undocumented; the engine-api doc gives a different signature). Values like 20…88 produce no visible line, and the line itself is a stack of bbox rectangles, not a line.
- **pareto** (s51): no cumulative % line despite the name.
- **gauge** (s55): renders as a half-doughnut facing *right*, not a dial, and the score overlaps it. Retired but still shipped.
- **checklist** (s62): with a mis-shaped row input, the columns collapse into a vertical letter soup. There is no schema validation.
- **value_chain** (s66): text overflow; arrows float in the middle with empty boxes.
- **Storyline s10 case_study**: body text overflows the S/A/R cards into the result box.
- **Storyline s11 horizontal_bar**: the 8th bar collides with the unit/summary bar (rows at a fixed 0.65" with no bottom check).
- **Storyline s12 donut**: legend labels are duplicated ("35% 35%", because the data already contained %), and the summary box overlaps the last legend entry.
- **Storyline s27 action_items** with 8 cards: headers overflow upward and are clipped (n is unbounded).

**Structural weaknesses.**

1. **Hard-coded geometry everywhere.**
   - Most methods have fixed y/heights (e.g., `side_by_side` bullets box 3.8", `timeline` label boxes 2.0" wide, `horizontal_bar` rh 0.65", `icon_grid` celh 2.2").
   - There is no layout solver, no measure-then-place, and no content-aware sizing; only about 8 methods have dynamic sizing.
   - Overflow is *detected after the fact*, never prevented at draw time.
2. **No autofit and no real text measurement.**
   - `auto_size=None`. The width model is 0.55 em Latin / 1.0 em CJK, with no font metrics, no bold factor and no per-word wrapping.
   - It ignores `space_before` and the actual `line_spacing` (always 1.4×). It ignores kana/hangul/fullwidth punctuation beyond U+3000-303F and U+4E00-9FFF.
   - Usable width subtracts only 0.1" and is floored at 1": `max(box_w-0.1", 1")`, so narrow boxes are *under*-estimated.
3. **Charts are not native charts.**
   - They cannot be edited as data in PowerPoint, have no axes objects, and no data labels linked to values.
   - The line and area charts are approximations, and there is no scatter with real axes scale.
   - Combo, clustered-stacked, Marimekko and bar-with-line charts are missing.
4. **No native tables.** Tables are text boxes plus hlines, so users cannot edit them as tables and nothing reflows when content changes.
5. **Docs and code drift.**
   - `engine-api.md` lists 8 methods that don't exist (`dashboard_kpi, dashboard_table, harvey_ball, hero_image, left_image_content, progress_bars, staircase, two_col_image_text`) and wrong signatures (`line_chart`, `content_right_image(image_path)`: the engine only draws placeholders and has **no real image insertion** except on the cover and pyramid icons).
   - `references/layouts/*.md` is referenced by SKILL/INDEX as the S4 reading but **the directory doesn't exist**.
   - `layout-matrix.yaml` is Markdown, not YAML, so it can't be loaded.
   - The S3 gate **does not implement char_budget** checks although the docs say it is "the core basis of the S3 gate".
   - Pattern numbers conflict (#71 is both table_insight and multi_bar_panel; #15 is both pyramid and staircase).
   - `__version__='2.3.0'` vs SKILL 2.3.3.
   - The catalog says 72, the SKILL says 67.
   - "Retired" layouts (venn, cycle, funnel, pie, gauge) are still callable, and venn is a set of rectangles.
6. **Whitelist hides real bugs.**
   - The comment says `chart_legend_overflow` is exempt "only for timeline", but the code exempts it **globally** (gate_check.py:46-49).
   - `peer_font_inconsistency` is exempted wholesale because the check itself is noisy: it groups an Oval badge (14pt) with its adjacent title (18pt) because they share a y. The right fix is to scope peer groups by role/column, not to whitelist.
7. **QA gaps.**
   - `_check_fonts` checks only the minimum size (MAX_FONT_SIZE is unused). There is no font-family or color-palette check, although the docstring promises one.
   - The overlap check is text-on-text only (it misses text-over-foreign-rect and rect-rect collisions).
   - Whitespace coverage counts background rects as "content".
   - There is no margin check (the safe zone is the full slide, so content in the 0.8" margin passes).
   - There is no render-based check, and no check for the title-vs-rule or the 6.1–6.4" bottom-bar rule of Guard Rail 3.
8. **AutoFix is semantically destructive.**
   - `_fix_restructure` drops every clause after the 2nd "；" or the 3rd "，" (review.py:633-645), and the regexes rewrite Chinese phrasing.
   - It is Chinese-only. It changes content without the author's knowledge.
   - It also edits only the first paragraph for peer harmonization.
9. **Storyline intelligence is thin.**
   - There is no pyramid-principle or SCQA engine, no governing-thought tree, no MECE check, and no headline generator. Guidance is prose (planning-guide) plus a >10-char check on titles.
   - `NarrativeReviewer` has 3 checks: jargon list, density, title length.
   - review.py's "Page Brief" stage is described in the docstring but not implemented.
10. **Visual choice is a static lookup table** ("content type → layout") plus rules ("data with dates must be chart", "adjacent slides differ"). No content analysis is coded.
11. **No template/master support.** It uses the default python-pptx theme and a blank layout, and ignores placeholders, so the output has no real title placeholders (accessibility and outline view suffer).
12. **Chinese hard-coded strings in the engine**: '解决路径', '协同机制分析', '负责人：', '技术领域', '之前/之后', '¥' axis labels, '趋势分析', '关键发现', '应对措施'. These are unusable for English decks without editing the code.
13. **Georgia** is used for numbers and titles and **KaiTi** as the EA font (a calligraphic font, unusual for business decks). The fonts are not embedded, and there is no fallback check.
14. **Self-refinement writes Markdown notes** that nobody enforces. Most "Rules" in experiences are not reflected in gate code (e.g., the CJK 1.4 density factor).
15. `cover_image.py` depends on Tencent Cloud credentials, rembg and a Chinese keyword→metaphor map. It is vendor-locked and irrelevant.

---

## F. Reusable elements (port these)

### F.1 Complete QA check inventory with thresholds

**qa.py (PptQA)**

Constants (qa.py:68-73):
- `OVERFLOW_TOLERANCE` = 18288 EMU (0.02")
- `WHITESPACE_THRESHOLD` = 0.55
- `TEXT_OVERFLOW_LINE_RATIO` = 1.15
- `MIN_FONT_SIZE` = 8pt
- `MAX_FONT_SIZE` = 48pt (unused)
- `OVERLAP_TOLERANCE` = 0.02"

Content area: y 1.3"→7.05", x 0.8"→12.533".

| # | Check (fn, line) | Logic | Severity |
|---|---|---|---|
| 1 | `body_overflow` (`_check_body_overflow`, 318) | shape right > slide W + 0.02" or bottom > slide H + 0.02" | ERROR |
| | | left < -0.02" or top < -0.02" | WARNING |
| 2 | `text_overflow` (375) | `_estimate_text_height(tf, w)` > 1.15 × box_h | ERROR if overflow > 30%, else WARNING |
| 3 | `text_line_collision` (591) | "Lines" are shapes with no text, h ≤ 3pt (38100 EMU) and w > 1". Text shapes are skipped if text ≤ 2 chars, if smaller than 0.25"×0.25", or if anchored ctr/b. `text_bottom = top + min(est_h, box_h + 0.05")`. Only lines below the box top and with ≥ 0.5" horizontal overlap count. gap = line_top − text_bottom; fires when −0.2" < gap < 0.03". | ERROR if gap < 0, else WARNING |
| 4 | `dead_whitespace` (413) | Shapes intersecting the content area are rasterized onto a 20×20 grid (bbox cells marked). Fires if empty > 55%. Dead zones are labeled bottom_third / right_third / left_third / center when > 80% of that region is empty, else "scattered". | WARNING |
| 5 | `shape_overlap` (519) | text-shape pairs only; overlap beyond 0.02" tolerance and overlap area / min(area) > 15% | WARNING |
| 6 | `font_issue` (562) | run size < 8pt | WARNING |
| 7 | `peer_font_inconsistency` (665) | Text shapes grouped by top y within 0.02" (greedy, first-paragraph effective font: run first, then paragraph). Groups of ≥ 3 with > 1 distinct size, or > 1 distinct font name. | ERROR |
| 8 | `chart_legend_overflow` (772) | Small text (h ≤ 0.5", w ≤ 2.5", len ≤ 20, top ≤ 6.8", not matching `^\d+/\d+$`) whose right edge > content right (12.533") + 0.02" | ERROR |
| 9 | `guard_rail` connectors (822) | `<p:cxnSp` in slide XML | ERROR |
| 10 | `guard_rail` p:style (global, 837) | `<p:style` count > 0 | WARNING |

Scoring (qa.py:853-877), starting from 100 per slide:
- ERRORs: body_overflow −25, text_overflow −20, guard_rail −30, other −15.
- WARNINGs: dead_whitespace −10, text_overflow −8, shape_overlap −10, other −5.
- INFO: −1.
- Floor at 0. Deck score = mean of slide scores. `passed` = 0 ERRORs.

**review.py**

- `density`: box height bucket → char cap {0.2:15, 0.3:30, 0.4:50, 0.5:70, 0.6:90, 0.8:130, 1.0:180, 1.5:300, 2.0:450, 3.0:700, 5.0:1200}. WARNING if chars > 1.3 × cap.
- `title_long`: any run ≥ 20pt whose paragraph is > 45 chars → WARNING (`SUBTITLE_MAX_CHARS=30` is unused).
- `lang_mix`: text ≥ 20% CJK containing English jargon from a regex list → INFO.
- Autofix floors: title ≥ 20pt, body (13-19pt) ≥ 11pt, small ≥ 9pt. Shrink in 1pt steps, at most 4 steps. Peer groups are harmonized to the min size.
- Combined gate: layout ERRORs == 0 (narrative issues never block).

**gate_check.py**
- Blocking = PptQA ERRORs not in the whitelist {peer_font_inconsistency, chart_legend_overflow}.
- `MAX_WARNINGS_ALLOWED=3` (declared, unused).
- Exit code 0/1 and JSON with `passed`, `overall_score`, `checklist`, `verdict`, `user_code_error_detail`, `engine_bug_detail` and `warnings_detail`.

**gate_check_s3.py** (pre-render, on content.json)
- four_column / executive_summary items must be 3-tuples.
- matrix_2x2: exactly 4 quadrants, each a 3-tuple.
- process_chevron: ≤ 5 steps, 3-tuples, no `\n` in the label, desc ≤ 50 chars.
- donut/pie: ≤ 6 segments.
- grouped_bar: ≤ 6 categories and ≤ 3 series.
- timeline: last label ≤ 6 chars.
- source non-empty (except cover/toc/section_divider/closing/appendix_title).
- title length > 10 (same exceptions).
- Any fail blocks.

**DeckBuilder.qa_validate**: top < -0.2", bottom > 8.0", left < -0.5", right > 13.83", negative w/h. Too lax; discard.

**Worth porting** (with fixes):
- body/margin overflow, but checked against the **content safe zone**, not the slide edge;
- text-fit estimation, upgraded;
- text–rule collision;
- grid coverage for whitespace, ignoring background panels, or computed as "ink" coverage from the render;
- peer consistency, grouped by role/column and not by y alone;
- legend/label overflow against the content box;
- the connector and p:style guards;
- per-slide scoring with category weights;
- a JSON gate with exit code;
- a code-level exemption list (scoped per layout and category, with a reason).

### F.2 Text width/height estimation (qa.py:217-261)

- Per paragraph: font = the first run size, else the paragraph size, else 14pt. Line height = size × 1.4.
- An empty paragraph costs 1 line.
- Width: `(latin*0.55 + cjk*1.0) * size`, where CJK covers U+4E00–U+9FFF and U+3000–U+303F.
- Usable width = `max(box_w − 0.1", 1")`.
- Lines = `ceil(width / usable)`; height = Σ lines × lh.

Port the idea, but improve it:
- use real advance widths from font files (PIL `ImageFont.getlength` or fontTools hmtx) with bold, and word-boundary wrapping for Latin;
- extend CJK ranges (3040–30FF kana, AC00–D7AF hangul, FF00–FFEF fullwidth);
- respect the actual insets, `space_before/after` and line spacing;
- set the ratio threshold to 1.0 plus a safety margin rather than 1.15.

### F.3 CJK handling

- `a:ea` typeface on every run (core.py:60-67). Also consider setting `a:cs` and `lang="zh-CN"`/`altLang`.
- Fixed-point line spacing of `Pt(size×1.35)` for body text (<18pt) and a 0.93 multiple for titles (core.py:100). This fixes CJK wrapped-line overlap in some renderers.
- A CJK line-height factor of 1.4 in estimates (experiences/cjk-issues.md).
- Character budgets are expressed in characters, which roughly equals em for CJK. Keep separate budgets for Latin vs CJK: about 1.8× chars for Latin at the same width.

### F.4 Guard rails (condensed from framework/guard-rails.md)

1. Keep ≥ 0.15" (0.2" recommended) between the last content and the bottom takeaway bar.
2. Stay within right = 12.533" and bottom = 6.95". Text inside a colored block is inset ≥ 0.15". Column width = `(CW − gap(n−1))/n`, not CW/n.
3. The bottom bar y is clamped to [6.1", 6.4"]: `max(content_bottom+0.15, 6.1)` then `min(…, 6.4)`.
4. Legend swatches are rects in the *exact* series color (never a "■" glyph).
5. Every content slide uses the white action title with a black underline (the navy title bar is banned). Content starts at 1.25–1.3".
6. Axis labels are centered on the full axis span, not placed at a fixed offset.
7. Decks with ≥ 8 slides include at least one image or image placeholder.
8. Variable-count layouts compute sizes dynamically: `item_w=(CW−gap(n−1))/n`, `item_h=min(MAX, avail/max(n,1))`.
9. Circular charts use BLOCK_ARC (3–5 shapes), never rect stacking.
10. Horizontal N items: `MIN_GAP=0.35"`, `item_w=min(PREFERRED, (CW−MIN_GAP·max(n−1,1))/max(n,1))`, which prevents negative widths.

Anti-corruption rules:
- no `add_connector`;
- `_clean_shape` on every shape;
- `full_cleanup` after save;
- `set_ea_font` on CJK runs.

README adds three more:
- (11) peer font consistency;
- (12) a post-generation QA gate;
- (13) the chart-legend overflow check.

### F.5 Layout-matrix selection logic

- `layout-matrix.yaml` (actually Markdown) sets per-layout **Max Items** and **char budget per field**. Examples:
  - title 40 chars (30 for charts);
  - toc 6 items, title 20, desc 40;
  - data_table 8 rows, header 15, cell 40;
  - table_insight 6 rows, insight 60;
  - process_chevron 5 steps, label 10, title 20, desc 50;
  - executive_summary 4 items, headline 60, item title 25, desc 80;
  - timeline 6 milestones, label 8, desc 40;
  - donut/pie 6 segments, label 15;
  - grouped_bar 6×3;
  - horizontal_bar 8;
  - four_column 4, desc 120;
  - icon_grid 8 or 9;
  - swot 4×4 points of 50;
  - checklist 7 rows;
  - two_column_text 2×5 bullets of 60, at most once per deck.
- Default for an unknown field is 80.
- Selection itself happens in `engine-api.md` "Content-to-Layout Quick Match":
  - single number → big_number;
  - 2 options → side_by_side/before_after;
  - 3–4 parallel → table_insight (preferred), metric_cards, four_column;
  - process → chevron, vertical_steps, value_chain;
  - time → timeline;
  - table → data_table, scorecard;
  - case → case_study;
  - summary → executive_summary, key_takeaway;
  - multi-KPI → three_stat, dashboard;
  - time series → grouped_bar, line, stacked;
  - share → donut/pie;
  - risk → risk_matrix, swot, 2×2;
  - openers → table_insight > big_number > key_takeaway.

Port it as a machine-readable capacity registry (YAML/JSON with per-field budgets in em units and max_items). Validate it both **pre-render** (budget) and **post-render** (measurement), and run capacity-based **layout fallback** (e.g., 7 steps → vertical_steps, or split the slide).

### F.6 Planning-guide rules

- Standard deck of 10–12 slides: cover, toc, exec summary / table_insight, 4 argument slides (vary the layouts), 3 evidence slides (case_study / side_by_side), a roadmap (timeline / chevron), and key takeaway plus closing. Short deck of 6–8 slides.
- Minimum of 8 slides for a substantive topic. Generate everything at once with no truncation. The TOC lists all sections.
- About 1 minute per slide, with count ≤ duration × 1.2.
- Openers (slides 2–5) use high-impact layouts.
- Date/period plus numeric data *must* be a chart.
- Decks of ≥ 8 slides need at least one image layout.
- **Adjacent slides must not share a layout.** `two_column_text` ≤ 1.
- Density:
  - ≥ 3 visual blocks per content slide;
  - content-area usage ≥ 50%;
  - the action title is a full insight sentence;
  - user numbers are highlighted;
  - every slide has a source ("Source: [org/report year]").
- Accent colors only when there are ≥ 3 parallel items. Body text inside cards is always DARK_GRAY.

### F.7 Other techniques worth porting

- The machine-gate plus anti-pattern preamble pattern: "passed is derived by code".
- Checkpoint/resume by artifact existence.
- Staged context loading (INDEX router).
- An `experiences/` lesson template: Problem / Root Cause / Fix / Rule, where the Rule should become a gate check.
- `add_block_arc` angle conversion.
- Harvey balls via masking. Better: use native PIE/CHORD shapes with adj values.
- A rotated RIGHT_ARROW with `adj1=12000, adj2=75000` as a thin sloped CAGR arrow.
- `**bold**` inline markup parsing into runs (engine.py:390-407).
- Int-coercion of every EMU.
- Bottom-anchored action title that sits flush on the rule.
- Image placeholder convention: gray box, crosshair, `[label]`.
- Test harness: one slide per layout with normal and stress fixtures, then a score table per method (`run_qa_tests.py`).

---

## G. Discard

- `cover_image.py` (Tencent Hunyuan/rembg/vendor metaphor map).
- The `deliver_to_channel` / OpenClaw notes.
- `DeckBuilder.qa_validate` (misleading "QA passed").
- The whitelist-as-exemption approach for noisy checks. Fix the check or the engine instead.
- The regex AutoFix text rewriting (clause truncation, Chinese-specific compressions) as an automatic step.
- Rect-approximated line and area charts; rect "venn"; the gauge; the funnel implementation.
- Chinese hard-coded labels inside layout code.
- Georgia/KaiTi as defaults.
- Fixed per-method absolute coordinates as the core layout strategy.
- The Markdown file named `.yaml`, the phantom `references/layouts/`, and the out-of-date engine-api tables.
- `sys.path.insert(~/.workbuddy/...)` hard-coded install paths.
- Page numbering via a manually passed `total_slides`. Compute it at save time.

## H. Reinterpret

- **Layout methods → layout *specs* plus a solver.** Keep the catalog of archetypes, but express each as regions (grid slots with min/max sizes and a role per text box). A measurement-driven fitter then picks font sizes (within tier floors), row heights and item widths *before* drawing, and falls back to an alternative archetype or a split when capacity is exceeded. The planner consumes the existing `max_items` and `char_budget` numbers.
- **Charts → native python-pptx charts** (`add_chart`: clustered/stacked bar and column, line, XY/bubble, doughnut/pie, area, combo via XML). This makes them editable in Excel. Keep BLOCK_ARC and shapes only for decorative or non-chart visuals (harvey balls, gauges). Build waterfalls as stacked columns with an invisible base series (native and editable). Build bridges and Marimekko the same way, or as shapes with data-bound code.
- **Tables → native `add_table`** with styled cells (hlines through cell borders), keeping the `table_insight` composition.
- **QA → two layers.**
  1. A model-based check (the qa.py checks, fixed: safe-zone bounds, role-scoped peer groups, any-shape collisions, real font metrics).
  2. A **render-based** check: LibreOffice → PDF → PyMuPDF. Extract text spans and bboxes to detect actual overflow and clipping, compare the rendered text bbox to the shape bbox, measure ink coverage and whitespace, and produce PNG contact sheets for visual review by a VLM.

  The gate stays a JSON boolean. Exemptions are scoped per layout and check, with an expiry.
- **AutoFix → a structured iterate loop.** On overflow, re-plan (reduce items, move detail to the appendix or notes, split the slide, change layout, shrink within tier floors). Have the LLM *rewrite* copy under explicit char or em budgets, rather than regex truncation. Show the diffs.
- **S3 content.json → the actual render input.** A typed schema per layout (pydantic/JSON Schema) is validated and then executed directly by the builder, so validation and rendering use one source of truth. Budgets are in em units with separate Latin and CJK handling.
- **Storyline → an explicit pyramid.** Governing thought → key lines (MECE check) → per-slide action titles. The title length and verb rules become checks, plus "title states a so-what with a number" heuristics, horizontal/vertical logic checks, and generation of an exec-summary slide from the titles.
- **experiences/ → a regression test corpus.** Each lesson becomes a fixture in `run_qa_tests`-style stress tests and a gate rule, not prose.
- **Design tokens → a theme object**, with brand swap, font fallbacks, and locale-driven EA/CS fonts. Use a real .potx master with title placeholders so the outline and accessibility work.

---

## Full list of layouts (engine methods; 67)

Structure
1. `cover(title, subtitle, author, date, cover_image)`: navy top rule, 44pt Georgia title (height from `\n` count), subtitle 22pt, author/date, 4.6" navy rule at 6.8"; optional full-bleed AI image.
2. `section_divider(label, title, subtitle)`: 0.6" navy left bar, label 18pt gray, title 28pt navy.
3. `toc(title, items[(num,title,desc)])`: oval numbers, 18pt titles, gray descriptions, rules at a 1.0" pitch (no overflow control).
4. `appendix_title(title, subtitle)`: centered 36pt title with a short navy rule.
5. `closing(title, message, source_text)`: centered 28pt title, rules.

Data and stats
6. `big_number(title, number, unit, description, detail_items, bottom_bar)`: 3.5×1.8" navy box with a 44pt number, text on the right, gray detail panel.
7. `two_stat(stats[(num,label,is_navy)])`: two 5.5" stat boxes.
8. `three_stat(stats)`: three 3.5" stat boxes plus detail text.
9. `data_table(headers, rows, col_widths, bottom_bar)`: text-box table with adaptive row height and 12/10pt fonts.
10. `metric_cards(cards[(letter,title,desc[,accent,light])])`: n equal cards 4.8" tall, badge, title, rule, description.
11. `table_insight(headers, rows, insights, insight_title='启示：')`: 7.2" table, chevron, gray insight panel, `**bold**` supported.
12. `scorecard(items[(name,score,pct)])`: rows with progress bars colored by threshold (≥.7 navy, ≥.5 orange, else red); headers hard-coded in Chinese.
13. `metric_comparison(metrics[(label,before,after,delta)])`: before/after cards plus a green/red delta badge.

Frameworks
14. `matrix_2x2(quadrants[(label,bg,desc)], axis_labels, bottom_bar)`: 4.5×2.0" cells.
15. `pyramid(levels[(label,desc,icon)], detail_rows, detail_headers)`: ascending *staircase* with icons and an optional detail table (3.6"/column, overflows at n = 4).
16. `process_chevron(steps[(label,title,desc)])`: n boxes with "→" glyphs; the last box is navy; dynamic width.
17. `temple(roof_text, pillar_names, foundation_text)`: roof bar, n pillars, foundation bar.
18. `venn(circles[(label,pts,x,y,w,h)])` (RETIRED): positioned rectangles.
19. `cycle(phases[(label,x,y)], right_panel)` (RETIRED): positioned boxes plus arrow glyphs.
20. `funnel(stages[(name,count,pct)])` (RETIRED): centered bars whose width is proportional to pct.
21. `swot(quadrants[(label,accent,bg,points)])`: 2×2 tinted cells.
22. `stakeholder_map(quadrants[(cn,en,bg,members)])`: 2×2 with numbered members.
23. `decision_tree(root, branches[(t,metric,color,children)], right_panel)`: 3-level tree with elbow lines made from rects.
24. `risk_matrix(grid_colors, grid_lights, risks, notes)`: 3×3 heat grid with labels and a notes panel.
25. `harvey_ball_table(criteria, options, scores 0-4)`: matrix of Harvey balls.

Comparison
26. `side_by_side(options[(title,points)])`: two navy-headed gray columns.
27. `before_after(before_title, before_points, after_title, after_points, ...)`: white editorial layout with a vertical rule and a circled ">"; dict rows (brand/value) or bullets.
28. `pros_cons(pros_title, pros, cons_title, cons, conclusion)`.
29. `rag_status(headers, rows[(name,color,*vals,note)])`: status dots.
30. `checklist(columns, col_widths, rows, status_map)`: zebra rows plus a status pill.

Narrative
31. `executive_summary(headline, items[(num,title,desc)])`: navy headline bar plus numbered rows (fixed 0.9" pitch).
32. `key_takeaway(left_text, takeaways)`: left analysis (hard-coded Chinese header) plus a gray Key Takeaways panel.
33. `quote(quote_text, attribution)`.
34. `two_column_text(columns[(letter,title,points)])`.
35. `four_column(items[(num,title,desc)])`: n gray cards with centered text.
36. `numbered_list_panel(items[(title,desc)], panel{subtitle,big_number,big_label,metrics})`: list plus a navy KPI panel.
37. `agenda(headers[(label,w)], items[(*vals,type)])`: agenda table with key and break rows.

Timeline and process
38. `timeline(milestones[(label,desc)])`: gray line, numbered ovals, labels above and descriptions below (last label overflows).
39. `vertical_steps(steps[(num,title,desc)], bottom_bar)`: adaptive rows.
40. `value_chain(stages[(title,desc,color)], bottom_bar)`: full-width stage columns plus "→".

Team and cases
41. `meet_the_team(members[(name,role,bio)])`: cards with an initial oval.
42. `case_study(sections[(letter,title,desc)], result_box)`: S/A/R cards (the last is navy) plus a result box.
43. `action_items(actions[(title,timeline,desc,owner)])`: n cards (unbounded n).

Images (placeholders only)
44. `content_right_image(title, subtitle, bullets, takeaway, image_label)`.
45. `three_images(items[(cap,desc,label)])`.
46. `image_four_points(image_label, points[(t,desc[,color])])`: central image plus 4 corner callouts.
47. `full_width_image(image_label, overlay_text, attribution)`: 70%-alpha navy overlay band.
48. `case_study_image(sections[(label,text,color)], image_label, kpis)`.
49. `quote_bg_image(image_label, quote_text, attribution)`.
50. `goals_illustration(goals[(t,desc,color)], image_label)`.
51. `two_col_image_grid(items[(t,desc,color,label)])`: 2×2 image and text cards.

Charts (shape-drawn)
52. `grouped_bar(categories, series[(name,color)], data, max_val, y_ticks, summary)`: bars as rects; value labels only if ≥ 50 (!).
53. `stacked_bar(periods, series, data %, summary)`: 100%-stacked with 0–100 ticks.
54. `horizontal_bar(items[(name,pct,color)], summary)`: ranked bars (0.65" rows, unbounded).
55. `donut(segments[(pct,color,label)], center_label, center_sub, summary)`: BLOCK_ARC ring plus a legend.
56. `pie(segments[(pct,color,label,sub)], summary)` (RETIRED): solid BLOCK_ARC.
57. `gauge(score, benchmarks)` (RETIRED): 3 BLOCK_ARC zones.
58. `waterfall(items[(label,value,'base'|'up'|'down')], legend_items, summary)`: bridge with connector rules.
59. `line_chart(x_labels, y_labels, values 0–1, legend_label, summary)`: single series, rect segments.
60. `pareto(items[(label,value)], summary)`: descending bars with value and % labels (no cumulative line).
61. `kpi_tracker(kpis[(name,pct,detail,status)], summary)`: progress bars with on/risk/off status.
62. `bubble(bubbles[(x%,y%,size_in,label,color)], x_label, y_label, legend_items)`: ovals on L-axes, no ticks.
63. `stacked_area(years, series_data[(name,values,color)], summary)`: stacked columns (¥ axis hard-coded).
64. `multi_bar_panel(panels[{title,unit,legend,categories,values,cagr,highlight_idx,...}], footnotes)`: 2–3 small-multiple bar panels with CAGR arrows.

Dashboards
65. `dashboard_kpi_chart(kpi_cards[(val,label,detail,color)], chart_data{labels,actual,target}, summary)`: KPI row, actual-vs-target bars, findings bar.
66. `dashboard_table_chart(table_data{headers,col_widths,rows}, chart_data{title,items}, factoids)`: table, mini bars, factoid cards.
67. `icon_grid(items[(title,desc,color)], cols=3)`: cards with a letter-in-circle "icon" (no real icons).

(`layout-catalog.md` lists 72 numbered patterns including retired or reserved slots: #2 action title page, #14 retired, #36 reserved. The API doc has 8 phantom names; see E.5.)

---

## Design tokens (verbatim)

**Colors** (constants.py)

| Token | Hex |
|---|---|
| NAVY | #051C2C |
| BLACK | #000000 |
| WHITE | #FFFFFF |
| DARK_GRAY | #333333 (body) |
| MED_GRAY | #666666 (secondary, source) |
| LINE_GRAY | #CCCCCC (separators) |
| BG_GRAY | #F2F2F2 (panels) |
| ACCENT_BLUE | #006BA6, paired with LIGHT_BLUE #E3F2FD |
| ACCENT_GREEN | #007A53, paired with LIGHT_GREEN #E8F5E9 |
| ACCENT_ORANGE | #D46A00, paired with LIGHT_ORANGE #FFF3E0 |
| ACCENT_RED | #C62828, paired with LIGHT_RED #FFEBEE |
| CYAN #00A9F4 | deprecated |

Ad hoc colors in the engine:
- placeholder #D9D9D9 / #BBBBBB / #999999;
- zebra rows #FAFAFA;
- gridlines #E8E8E8;
- navy panel text #CCCCCC / #AAAAAA;
- navy panel rule #334455.

**Fonts**: FONT_HEADER = 'Georgia' (titles, big numbers), FONT_BODY = 'Arial', FONT_EA = 'KaiTi' (brand guide lists SimSun as a fallback).

**Sizes**: COVER 44, SECTION 28, ACTION_TITLE 22 (bold), SUB_HEADER 18, EMPHASIS 16, BODY 14 (primary), SMALL 12, FOOTNOTE 9. The brand guide adds a cover subtitle of 24; the engine uses 22.
- The engine also uses 11, 13, 15, 10, 20, 24 and 36pt in places, although the brand guide says "no other sizes".
- Line spacing: ≥ 18pt uses a 0.93 multiple; < 18pt uses a fixed 1.35 × size. Paragraph gap is 6pt by default (4–10 in layouts).
- Text box insets are 0.05" (45720 EMU); ovals have 0 insets.

**Grid / margins**:
- Slide 13.333 × 7.5 in; LM = RM = 0.8"; CW = 11.733" (content right = 12.533").
- TITLE_TOP 0.15", TITLE_H 0.9", TITLE_LINE_Y 1.05" (0.5pt black rule, title width 11.7").
- CONTENT_TOP 1.3" (docs: 1.25–1.4"). Content zone runs to about 6.5" (conventions) or 6.95" (guard rail 2).
- BOTTOM_BAR_Y 6.2", BOTTOM_BAR_H 0.65", clamped to 6.1–6.4".
- SOURCE_Y 7.05" (9pt MED_GRAY); page number at x 12.2" (right-aligned 1" box), y 7.1".
- Standard gaps:
  - 0.2" between cards;
  - 0.733" between two columns (two 5.5" columns fill CW);
  - 0.15" between grid cells;
  - MIN_GAP 0.35" for horizontal flows;
  - oval badge 0.45".

---

## Guard rails (summary)

See F.4 for the 10 rules plus the anti-corruption rules. In short:
- bottom-bar gap ≥ 0.15";
- content within 12.533 × 6.95 with ≥ 0.15" text inset in colored blocks and gap-aware column width;
- bottom bar at 6.1–6.4";
- legend swatches as rects in the exact series color;
- a single white action-title style, content from 1.25–1.3";
- axis labels centered on the axis span;
- at least one image placeholder in decks of ≥ 8 slides;
- dynamic sizing for variable counts;
- BLOCK_ARC for circular charts;
- non-negative horizontal widths via MIN_GAP;
- no connectors, `_clean_shape` on all shapes, `full_cleanup` after save, EA font on CJK runs.

README adds peer-font consistency, text-line collision, a post-generation QA gate and a legend overflow check.

Experiences rules:
- title ≤ 40 chars;
- four_column desc ≤ 120;
- chevron ≤ 5 steps, desc ≤ 50, no `\n` in the label;
- four_column items are 3-tuples;
- timeline last label ≤ 6;
- donut/pie ≤ 6 segments, merging the rest into top-5 + "Other";
- grouped_bar ≤ 6 × 3;
- two_column_text ≤ 1;
- content start 1.25–1.3";
- bottom bar `max(last+0.2, 6.1)` capped at 6.4;
- CJK line height 1.4.

---

## Capability scoring (0 = absent, 1 = weak, 2 = solid, 3 = strong)

| Capability | Score | Justification |
|---|---|---|
| Content ingestion | 1 | S1 is a manual brief.md by the LLM; no parsing of source docs or data files, and no data model. |
| Storyline | 1 | Planning-guide templates (10–12 / 6–8 slide skeletons) and the outline.json idea; no storyline logic in code. |
| Pyramid principle | 0 | Not mentioned in code; no governing thought, key-line or MECE checks. |
| Slide planning | 2 | outline.json per slide (layout + key_point), count ≤ duration × 1.2, adjacency diversity, opener rules, capacity matrix. Mostly LLM-enforced. |
| Headline generation | 1 | Rule "action title = full insight sentence" plus title >10 and ≤ 40–45 char checks; no generator or so-what check. |
| Executive communication | 2 | Action-title plus takeaway-bar conventions, source on every slide, exec-summary and insight-panel layouts; guidance only. |
| Visual choice | 1 | Static content-type → layout table and "dates + numbers must be a chart"; no content analysis. |
| Layout selection | 1 | Manual choice by the LLM from the lookup table; no automatic fallback on capacity. |
| Layout library | 2 | 67 methods, broad coverage, but many rigid or buggy, several retired but callable, docs out of sync. |
| Charts | 1 | All shape-drawn (not native or editable-as-data); line/area/pareto are approximations; limited axes. |
| Tables | 1 | Text boxes plus hlines (not native tables); adaptive row height in 2 layouts. |
| Waterfalls | 2 | Works with correct 'base'/'up'/'down' input and draws connector rules; no totals or subtotal logic, no negative-crossing handling, no input validation. |
| Bridges | 1 | Same waterfall only; no multi-period or price-volume-mix variants. |
| Timelines | 1 | One horizontal milestone layout with a known last-label overflow; no Gantt or swimlanes. |
| Matrices | 2 | 2×2, SWOT, stakeholder map, 3×3 risk heat map, Harvey-ball matrix; fixed sizes. |
| Trees | 1 | Single decision_tree with a fixed 3-level geometry (no auto layout, overflows with more branches). |
| Processes | 2 | Chevron (dynamic width), vertical steps, value chain, staircase; the "chevron" uses rect + "→" glyphs. |
| Maps | 0 | None. |
| Org charts | 0 | None (meet_the_team is profile cards only). |
| Bubble charts | 1 | Ovals on a bare L-axis; the caller supplies inches for size; no scale ticks. |
| Combo charts | 0 | None (dashboard actual vs target is paired bars; pareto has no cumulative line). |
| Conceptual diagrams | 2 | Temple, staircase, before/after, cycle, venn (rects), icon grid, table_insight chevron; mostly fixed. |
| SVG | 0 | No SVG support (the `.svg` icon path is accepted in a check but `add_picture` can't insert SVG). |
| PPTX generation | 2 | Reliable python-pptx output with corruption hardening; blank layout, no master or placeholders. |
| Editability | 2 | All native shapes and text boxes (editable), but charts and tables are not data-editable and there are no placeholders. |
| Visual consistency | 2 | Strong tokens and a single title style; engine-internal size drift (11/13/15pt) and hard-coded Chinese labels. |
| Fonts | 2 | Clear hierarchy plus EA font injection; Georgia/KaiTi choices, no embedding or fallback checks. |
| Colors | 2 | Tight palette with accent pairs; no contrast or palette-compliance QA. |
| Spacing | 2 | Explicit grid and gap rules, bottom-bar clamping; many fixed offsets break with content. |
| Alignment | 2 | Consistent LM/CW grid, bottom-anchored titles, centered axis rule; no alignment QA. |
| Density | 2 | Char budgets, density buckets, whitespace coverage check, "≥ 3 blocks / ≥ 50% usage" rule. |
| Overflow | 1 | Detected post hoc by a crude estimator; the engine's own test deck has 41 errors; no prevention or autofit. |
| Collisions | 1 | Text–text overlap (> 15%) and text–rule collision only; misses text-over-shape; peer check is noisy. |
| Rendering | 0 | No render step in the pipeline (no LibreOffice/PDF/PNG); QA is purely model-based. |
| QA | 2 | 10 geometric checks with severities, scores and a JSON report; heuristics are rough. |
| Auto review | 1 | Narrative review has 3 shallow checks; no visual/VLM review. |
| Iteration | 1 | AutoFix loop (≤ 3 rounds) is regex/truncation and 1pt shrinking only; re-render iteration is manual by the LLM. |
| Final validation | 2 | Machine-readable gate with a JSON bool and exit code (strong concept), weakened by a global whitelist and by DeckBuilder's false "QA passed". |
