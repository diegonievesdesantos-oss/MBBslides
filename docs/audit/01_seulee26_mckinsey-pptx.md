# Audit: seulee26/mckinsey-pptx ("axlabs-mckinsey-pptx" v0.2.0)

Repo: /tmp/claude-0/ref/mckinsey-pptx (HEAD 201ef49 "Fix slide layout overflow and polish template rendering (v0.2.0)")
Size: about 4.3k LOC Python + 885-line CATALOG.md + 236-line agent prompt. Only dependency is `python-pptx>=1.0.0` (requirements.txt). No tests.
Render evidence: /tmp/claude-0/ref/out_seulee/ (demo_full 15 slides, demo_korean 21 slides, test_real.py = 16-slide realistic + stress deck I wrote; PDFs, per-slide PNGs, contact sheets `sheet_*.png`).
Note: the container's LibreOffice had no Impress component, so `soffice` failed with "source file could not be loaded". I installed `libreoffice-impress` to render. Fonts fall back to Liberation Sans (Arial) and DejaVu Sans ("Apple SD Gothic Neo").

---

## A. Problem it solves

It is a Claude Code plugin (Korean-market product by "AX Labs") that turns a chat brief (a sentence, or xlsx/docx/pdf/md in the CWD) into a McKinsey-*looking* 16:9 `.pptx`. It has three parts:
1. A **template library**: 40 hand-coded slide functions drawn with python-pptx primitives (`mckinsey_pptx/slides/*.py`).
2. A **catalog/playbook** (`mckinsey_pptx/agent/CATALOG.md`) that lists "Use when / Don't use when / Required inputs / Example" per template, plus a "Choosing between similar templates" decision list.
3. A **subagent prompt** (`agents/mckinsey-slide-agent.md`) and a slash command (`commands/mckinsey-deck.md`). The LLM plans the arc, picks one template per slide with a written rationale, writes a Python build script, runs it, renders PNGs and eyeballs 2 or 3 of them.

The goal is a fast consulting-style first draft from a single prompt. It does not aim for analytical rigor, native charts, or brand templates. The README explicitly defers custom branding to paid "enterprise" work.

## B. Architecture

```
agents/mckinsey-slide-agent.md  --(LLM reads)-->  mckinsey_pptx/agent/CATALOG.md
        | writes output/agent_<slug>.py
        v
PresentationBuilder (builder.py:206)
   .add(type, **kw)  -> _REGISTRY[type](prs, **kw)   (builder.py:26-102, 52 keys -> 40 functions)
   .add_spec(dict)   -> infer_slide_type(dict)        (builder.py:105-203, key-shape heuristics)
   .save(path)
        |
slides/<family>.py  add_xxx(prs, *, title, <payload>, page_number, section_marker, source, footnote, theme)
        |  blank_slide(prs) -> layout[6] of python-pptx default template (base.py:274)
        |  add_chrome(): section marker + title + underline + footer (base.py:279)
        |  geometry in inches, hard-coded per template
        v
base.py primitives: add_textbox / write_paragraph / add_rect / add_oval / add_line / enable_text_shrink
theme.py: frozen dataclasses Palette / Typography / Layout / Theme (DEFAULT_THEME)
```

Modules and key functions (file:line):
- `theme.py:7` `rgb()`. `:12` `Palette` (18 colors). `:34` `Typography`. `:46` `Layout`. `:63` `Theme` (plus `copyright_text`). `:70` `DEFAULT_THEME`. Customize with `dataclasses.replace` (README and agent prompt).
- `base.py`
  - `:15 enable_text_shrink` sets `MSO_AUTO_SIZE.TEXT_TO_SHAPE_FIT`. It writes the flag only, with no fontScale computed.
  - `:40 add_textbox` zeroes the insets, word_wrap=True, no fill or line.
  - `:61 write_paragraph` handles the first-paragraph reuse trick, runs, space_before/after, and bullets.
  - `:84 _set_bullet` injects raw `a:buChar "•"` with marL/indent=228600 EMU. `:95 _clear_bullet` adds `a:buNone`.
  - `:107 add_rect` / `:131 add_oval` set `shadow.inherit=False` (writes an empty `a:effectLst`) and zero the text insets.
  - `:151 add_line` is a straight connector. It does **not** strip the shadow (see E).
  - `:165 add_title` (24pt bold, box top 0.45", height 0.7", rule at 1.15"). `:184 add_subtitle_placeholder` (dashed box if the text starts with "["). `:208 add_section_marker` (top-right outlined tag). `:225 add_footer` (rule at 7.05", footnote + "Source:" left, copyright + page right). `:266 init_presentation` (default python-pptx template resized to 13.333x7.5). `:279 add_chrome`.
- `builder.py`: `:26 _REGISTRY`. `:105 infer_slide_type` (about 40 if-rules on dict keys). `:206 PresentationBuilder` (auto page numbers, default section marker, theme injection at `:219-231`). `:247 build_from_spec`.
- `cli.py:11` `--list-types`, `--demo`, a JSON spec list goes to a pptx.
- `slides/column_chart.py`: `:28 _y_ticks` (nice 1/2/2.5/5x10^k steps, 5 to 12 ticks). `:52 _draw_takeaway` (right "so-what" pane with divider and header rule). `:90 _draw_description_header`. `:122 _draw_axis_and_bars` (bars as rectangles, gridlines as connectors, value labels as textboxes). `:223 _draw_growth_arrow` (connector + XML `a:tailEnd triangle` + oval CAGR bubble). `:271/297/333/381` are the four column variants.
- `slides/extra_charts.py`: `:23 _palette_series`, `:31 _draw_axis_frame`, `:87` stacked, `:179` grouped, `:260` line. The line chart is made of one connector per segment plus oval markers.
- `slides/bubble_chart.py`: `:36 _draw_xy_axis` (linear ticks `i*max/(n-1)`, not nice numbers), `:90 _draw_bubble` (linear diameter scaling 0.25 to 0.95", `label_pos` left/right/top/bottom), `:140 _draw_legend_groups`, `:172` bubble, `:227` bubble+takeaways, `:267` BCG 2x2, `:370` 3x3 prioritization. `:23 _round_up_nice` is dead code.
- `slides/comparison_slides.py`: `:22 _harvey_ball` (0 to 4 fill faked by a navy oval with a white rectangle mask on top and the outline re-stroked), `:71 _parse_score` (int, semantic words, or ●◐○ glyphs), `:98` comparison table, `:209` pros/cons, `:278` two-column compare.
- `slides/org_charts.py`: `:23 _box` (rect + overlay textbox), `:35 _elbow` (3 separate connectors), `:46` issue tree (leaf-count-driven vertical allocation), `:160` org chart, `:258` team circles, `:346` team chart.
- `slides/timeline_slides.py`: `:27 _chevron`, `:48` 3 chevrons, `:156` 4-phase table, `:244` 4 waves, `:347` gantt, `:461` overview areas A-G, `:546` process activities.
- `slides/process_extras.py`: `:22` process flow (overlapping chevrons), `:99` funnel (rectangles, not trapezoids), `:189` KPI tiles.
- `slides/structure_slides.py`: `:23` cover, `:90` section divider, `:145` agenda, `:207` stat hero, `:274` quote.
- `slides/summary_slide.py:14` dark-navy statement slide (bolds a `[Label]:` prefix).
- `slides/executive_summary.py:13` paragraph summary and `:46` takeaways + bullets.
- `slides/assessment_table.py:25` KPI table with traffic-light dots (rect grid, not a native table).

Data flow: brief, then LLM reasoning (no code), then a Python script of `b.add("<type>", **kwargs)` calls, then imperative drawing into absolute inch coordinates, then `.pptx`, then optional soffice/pdftoppm PNGs, then the LLM looks at 2 or 3 images. No intermediate representation exists: no storyline object, no slide-intent object, no layout model, no measurement.

## C. Operating flow (how the agent uses it)

From `agents/mckinsey-slide-agent.md:66-160`:
1. Understand the brief: audience, purpose, known data vs placeholders, language (Korean triggers the Apple SD Gothic Neo theme).
2. Read CATALOG.md, "the source of truth"; never invent templates.
3. Plan the arc. The suggested sequence is dark_navy_summary, exec summary takeaways, 1-3 analyses, 1-2 implications, roadmap, recommendation, at 5-10 slides.
4. For each slide, write a one-line rationale naming the template and why it beats nearby templates (with examples).
5. Fill content. Use real numbers or "plausible, illustrative placeholders" (it explicitly allows invented numbers). Follow hard "overflow discipline" rules as prose: titles ≤50 Korean / ≤70 English chars, bullets ≤15 words, ≤6 Korean / 10 English words in dense templates, Korean about 1.3x wider, always pass `description=` and `takeaway_header=` or placeholders render.
6. Write `output/agent_<slug>.py`, then run it and fix errors.
7. Render with soffice then pdftoppm at 80 dpi, read 2-3 PNGs, check 4 listed defect types, shorten content, rebuild ("MANDATORY when tools are available").
8. Report the path, slide list with template + rationale, caveats (invented data), and an offer to iterate.
It also forbids hand-drawing shapes and modifying the package ("requires a plugin update from AX Labs").

`commands/mckinsey-deck.md` only delegates `$ARGUMENTS` to the subagent.

## D. Strengths

1. **Catalog-as-decision-tree** (CATALOG.md). Each template has Use when / Don't use when / inputs / example, plus a consolidated "Choosing between similar templates" section (CATALOG.md:815-851). It routes by item count (3/5/7), axis type (continuous vs categorical vs banded), time vs category, and history vs forecast. This is the most reusable intellectual asset.
2. **Mandatory rationale per slide** ("not X because Y") forces explicit visual reasoning and gives a reviewable audit trail.
3. **Consistent chrome**: every slide shares the title, rule, section marker, footnote/source, copyright, and page number. That gives strong visual consistency with little code.
4. **Consulting idioms captured**: so-what pane to the right of charts, CAGR arrow with oval label, actuals vs forecast coloring, focus-bar highlight, Harvey balls, traffic lights, BCG quadrants, 3x3 prioritization, issue tree, gantt with milestones, dark "bottom line" slide, stat hero.
5. **Placeholder semantics**: bracketed `[...]` or default strings render gray (and dashed for subtitles), so unfilled slots are visually flagged (`base.py:193`, `column_chart.py:64-72,105-113`). That is a cheap "unfinished content" signal.
6. **Theme as frozen dataclasses**, overridable with `replace()`. Clean token access (`pal, typo, layout = theme.palette, ...`).
7. **Nice-number tick algorithm** `_y_ticks` (column_chart.py:28) is decent.
8. **Issue-tree layout allocates vertical space by leaf count** (org_charts.py:93-154). That is a real, if simple, tree layout.
9. **Z-order awareness**: BCG quadrant labels are drawn last so they sit above bubbles (bubble_chart.py:291-366).
10. **Renders cleanly for "happy path" content**. The Korean demo looks professional at first glance.
11. Zero heavy dependencies. Everything is 100% python-pptx.

## E. Weaknesses (concrete, with evidence)

**Charts and data**
- **No native charts at all.** Every chart is rectangles, ovals, connectors and textboxes (column_chart.py:4 says so explicitly). In test_real.pptx the result was 0 charts and 0 tables across 16 slides, with 450 shapes + 91 connectors, and up to 77 shapes on one slide. Nothing is data-editable in PowerPoint and there is no "Edit data" option. Changing one value means moving rectangles by hand.
- **No negative-value support.** `_draw_axis_and_bars` documents it (column_chart.py:127). In the line chart the negative branch computes ticks and then ignores the negative range (extra_charts.py:307-311). Rendered test: the NA series with -2/-4 plots **below the slide footer and off the canvas** (test_real slide 11).
- **Decimals destroyed**: all axis/value labels use `f"{int(round(v))}"` (column_chart.py:180,207; extra_charts.py:79,152,162,243; bubble_chart.py:59,65). With values 0.45/0.32/1.25/0.8 the axis reads 0,0,0,1,1,1,1 and the labels read 0,0,1,1 (test_real slide 15). There are no number formats, units, thousands separators or % formatting.
- Bubble axis ticks are `i*max/(n-1)`, not nice numbers (bubble_chart.py:43-44). This yields 58/117/175/233/292 ticks (demo_korean slide 7). Axis max is caller-supplied (`x_max=900, y_max=3000` defaults) with no auto-scaling from the data.
- Bubble size is linear in *diameter*, not area (bubble_chart.py:111-114, 348-351), so size perception is exaggerated.
- There is no label collision avoidance except manual `label_pos` / `ox,oy` hints. Rendered: CATL/CA../SK On labels overlap (demo_korean 7), and the "Question mark" quadrant label overlaps a bubble (demo_korean 8).
- **Missing chart types**: waterfall/bridge, bar (horizontal), combo (bar+line), 100% stacked, mekko/marimekko, pie/donut, scatter without size, area, sensitivity/tornado, slope, heatmap, map. There is no dual axis and no data table.
- The funnel is plain centered rectangles, not trapezoids (process_extras.py:151-156 admits it).
- Harvey balls are faked with **white rectangle masks** (comparison_slides.py:359-392) while the table alternates `soft_gray` rows (:486-489). The masks show as white squares on gray rows (test_real slide 6). They are also not editable as a single shape.
- The line chart is N separate connectors. It cannot be smoothed and it is not a series.

**Hard-coding / leftover template text**
- Every template has geometry as literal inches (e.g. `DEFAULT_CHART_BOX=(0.45,1.95,8.5,4.85)` column_chart.py:22; `plot_box=(1.05,2.05,11.7,4.6)` bubble_chart.py:196; `cat_w=1.6, kpi_w=4.4` assessment_table.py:47-50). No grid system is used, and changing Layout margins does not move most content.
- Hard-coded English strings that cannot be overridden:
  - BCG: "Growth rate 20xx-20xx (%)", "Market share (%)", "Size = [insert description]", quadrant names (bubble_chart.py:298-337). The split is fixed at the midpoint (x=50%, y=y_max/2) and ticks step 5/10 (:318-326).
  - Prioritization: "[Description]", 3x "Insert status/group" legend, "TIME TO IMPACT", "LEVEL OF IMPACT", "Short/Medium/Long", "Low/Medium/High" (bubble_chart.py:383-459). Rendered in demo_korean slide 9 with the placeholders visible even in the "finished" Korean deck.
  - phases_table_4 always prints "[TIMELINE]" (timeline_slides.py:185). team_chart always prints two "[Type of role, if relevant]" legends (org_charts.py:383-392). Bubble legends are always bracketed `f"[{label}]"` (bubble_chart.py:156) and axis titles are always bracketed (:72-85), even with real content. phases_chevron_3 has fixed "Deliverables"/"People" legend and fixed chevron color order (timeline_slides.py:71-101).
  - Defaults `source="xx"`, `footnote="1. xx"` on most templates, so "1. xx / Source: xx" appears on real slides unless overridden (visible on nearly every rendered slide). The default subtitle `"[Insert subtitle]"` renders a dashed placeholder unless `subtitle=None` is passed (demo_korean 17).
  - Brand strings: `corner_text="McKinsey & Company"` default on the dark slide (summary_slide.py:18) and `copyright_text="Copyright of mckinsey-AX"` (theme.py:67). **This is trademark / impersonation risk. Do not port.**
- Docstring promises `phases_chevron_4`, which doesn't exist (timeline_slides.py:4). `_round_up_nice` is dead (bubble_chart.py:23). A stray comment is left at summary_slide.py:66. The `status_overview`, `executive_summary` aliases etc. inflate "52 types" to 40 functions.

**Text fitting / overflow / collisions**
- **No text measurement anywhere.** Box sizes are fixed. Row heights are divided evenly (`block_h = avail/n`) whatever the content length. The only "fitting" is `enable_text_shrink` on the title, cover and stat hero (base.py:15,175; structure_slides.py:60,240), which sets the `normAutofit` flag without `fontScale`. LibreOffice ignores it, and PowerPoint only recomputes on edit. Rendered: a 2-line title **overlaps the underline rule** (test_real 15).
- Overflow falls through to the prompt ("≤ 70 chars", "≤ 15 words") and to post-hoc visual inspection of 2 or 3 PNGs.
- Pros/cons: `item_h = max(0.45, ...)`, so 14 items run **past the footer and over the Source line** (test_real 16). A few items get spread out with huge gaps (test_real 7).
- KPI value is fixed at 36pt (`title_size+12`). "123,456,789 days" wraps to 2 lines inside the tile (test_real 14).
- Bubble chart x-axis title collides with the footer/copyright (demo_full 4, demo_korean 7). The overview_areas call-out covers the bottom of cards A/B (demo_korean 20). The growth arrows can rise into the legend band for top-heavy series (column_chart.py:326-327 place the arrow 0.55" above the last bar).
- BCG bubble labels are always white (bubble_chart.py:358), so they are **invisible in the light-gray "Dog" quadrant** (demo_full 6: [BU 2]/[BU 3]).
- The issue tree and org chart have no vertical-capacity check. Many leaves or reports compress to the 0.30" minimum, then overflow (`org_charts.py:101-103,224-225`). team_chart roles run past the footer if there are many (`:420-446`, no bound).

**Editability / PPTX hygiene**
- Text on shapes is a **separate overlay textbox** stacked on a rect/oval/chevron (e.g. `_box` org_charts.py:26-32, `_chevron` timeline_slides.py:35-42, all KPI tiles, all bubbles). Moving the shape leaves the text behind. Nothing is grouped.
- Connectors come from `add_connector` with the default `<p:style>` `effectRef idx="1"`. The python-pptx default theme maps that to an `outerShdw`, so **every rule/gridline/connector carries a drop shadow** (verified in the XML dump). That is why all rules render as blurry gray bars. `add_line` never clears it (base.py:151-160).
- Rects and ovals keep `<p:style>` refs (fillRef idx=3 means gradient-capable, fontRef lt1). They override with an explicit fill and an empty effectLst, but new text typed into them inherits white `lt1` font. The LibreOffice render still shows shadows on cards.
- The default python-pptx template is used: an Office theme (Calibri, blue accent1), 4:3 master stretched to 16:9, layout[6] "Blank". Theme colors/fonts are **not** written into the theme XML, so PowerPoint's color picker and new shapes don't follow the palette. There is no real master/layouts and no placeholders, so titles are plain textboxes (the outline view and accessibility get no titles).
- The font is set per run (`run.font.name`) with no East-Asian font slot (`a:ea`). Korean relies on "Apple SD Gothic Neo" (macOS only), which fell back to DejaVu on Linux. No font embedding.
- Emoji icons as text glyphs (🤖, 📣, 👥) render inconsistently across platforms. The code even works around a missing ♟ glyph (org_charts.py:433-436).

**Process / QA**
- **No automated QA**: no bounds checks, no overlap detection, no text-fit estimation, no placeholder-leak detection (the "[...]" convention exists but is never scanned), no min font size check, no contrast check. There are no tests.
- The render step checks "2–3 PNGs" only, at 80 dpi, depends on soffice + poppler, and there is no loop limit or scoring.
- "Plausible, illustrative placeholders" invites fabricated numbers (agent.md:102-106). The only guard is a request to disclose them.
- There is no storyline object and no pyramid/SCR structure beyond a suggested slide order. Action titles are recommended but not enforced (template defaults are topic titles like "[Bubble chart / Insert action title]").
- `infer_slide_type` is brittle key sniffing (e.g. any dict with `body` and ≤4 keys becomes the dark slide, builder.py:147). It is order-dependent and has no scoring.
- Content ingestion (xlsx/docx/pdf) is only README promises. There is no code; the LLM reads files with generic tools.

## F. Reusable elements (worth porting, reinterpreted)

1. **CATALOG.md structure** (Use when / Don't use when / Required / Optional / Example) and the "Choosing between similar templates" rules (CATALOG.md:815-851). Port as machine-readable metadata per layout (`intent`, `n_items range`, `axis_type`, `time_axis`, `forecast`, `anti-patterns`) and make the "not X because Y" rationale a required field in the slide plan.
2. **Theme token dataclasses** (theme.py). Use the frozen `Palette/Typography/Layout/Theme` + `replace()` pattern, then extend with a spacing scale, grid columns, number formats, an `ea` font, and chart palettes.
3. **Chrome builder** `add_chrome` (base.py:279): a single function applying title, rule, tracker/section marker, source, footnote and page number. Reuse the concept, implemented on real slide-master placeholders.
4. **`_y_ticks` nice-number axis** (column_chart.py:28-49). Good for any custom-drawn scale; extend to negatives and a non-zero min.
5. **Growth/CAGR arrow with oval label** (column_chart.py:223-254). The XML arrowhead injection is a handy trick:
   ```python
   ln = line.line._get_or_add_ln(); tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type","triangle")
   ```
   Use it as an overlay on top of a native chart (compute bar tops from the axis scale).
6. **Actuals vs forecast coloring + legend**, **focus-bar highlight**, and the **right-side so-what pane** (`_draw_takeaway`, column_chart.py:52-87) as layout patterns.
7. **Bullet XML helpers** `_set_bullet/_clear_bullet` (base.py:84-102). Explicit `buChar`/`buNone` with marL/indent means consistent bullets independent of the master. Also the `first=True` paragraph reuse in `write_paragraph` (base.py:64-67).
8. **Zero-inset textboxes** (base.py:45-49) for pixel-accurate alignment against drawn geometry.
9. **Placeholder convention**: gray/dashed rendering for `[...]` (base.py:184-205). Keep it, and add a QA scan that fails the build if any `[` placeholder or "xx" survives.
10. **Issue-tree leaf-count vertical allocation** (org_charts.py:93-154) as a starting point for a real tree layout. The same goes for the **org-chart spine/tee connector pattern** (:201-241).
11. **Harvey-ball score parser** `_parse_score` (comparison_slides.py:71-93), which accepts ints, semantic words and glyphs. Keep the parser but draw the balls with `MSO_SHAPE.PIE`/`BLOCK_ARC` adjustments or a native pie, not masks.
12. **Deferred z-order drawing** (labels last) (bubble_chart.py:291-366).
13. **KPI tile anatomy** (label, big value, ▲▼▬ delta colored by direction, context) (process_extras.py:189-291), with a data-driven `columns` grid.
14. **Agent workflow skeleton**: understand, read catalog, plan, per-slide rationale, script, build, render, inspect, fix, report with caveats about invented data. Also its explicit visual defect checklist (text past box, labels hidden, title into rule, stacked chart labels). Promote that checklist to automated checks.
15. **Korean text-width heuristic** (about 1.3x Latin, keep content 25% shorter) and the per-template word budgets (agent.md:108-126). Seed values for a text-fit estimator.

## G. Elements to discard

- Shape-drawn charts (columns, stacked, grouped, line, bubble, scatter axes). Replace them with native `chart_data` charts (`CategoryChartData`, `XyChartData`, `BubbleChartData`) styled via the XML, and keep shape overlays only for annotations (CAGR arrows, callouts, brackets).
- Overlay-textbox-on-shape pattern. Put text in the shape's own `text_frame` (or group shape+label).
- `add_line` connectors with inherited theme shadow. Always strip `p:style` or set an explicit `a:effectLst`.
- The default python-pptx template + blank layout with textbox titles. Build a real master with title/body placeholders, theme colors and fonts written into theme1.xml.
- `int(round(v))` label formatting. Use locale-aware number formats.
- White-mask Harvey balls and rectangle funnels.
- `infer_slide_type` key sniffing. Replace it with an explicit intent-to-layout selection that has scoring.
- Hard-coded demo strings (BCG axis text, "TIME TO IMPACT", "[TIMELINE]", "[Type of role…]", "xx" sources, "[Insert subtitle]" defaults).
- Any "McKinsey & Company" / "mckinsey-AX" branding strings. Also the upsell and "don't modify the package" constraints.
- "Plausible illustrative placeholder" numbers. In the new engine, invented data must be explicitly flagged in the data model and visibly marked (e.g. "ILLUSTRATIVE" sticker).
- Emoji glyph icons. Use a vector icon set (SVG, then native shapes) or omit them.
- Fixed-count templates (`three_trends_*`, `five_key_areas`, `phases_chevron_3`, `waves_timeline_4`) as separate functions. Collapse them into parametric N-item layouts.

## H. Ideas to reinterpret

1. **Catalog, then a layout knowledge base**: turn CATALOG.md into YAML metadata consumed by a selector *and* rendered into the agent prompt. Add capacity limits per layout (max items, max chars per slot at a given font size) so selection considers content volume.
2. **Rationale field, then a "visual reasoning" record** in the slide spec: `{message, evidence_type, comparison_type (time/rank/part-to-whole/correlation/flow/hierarchy), chosen_visual, rejected_alternatives[]}`. That makes the auto-review checkable.
3. **Prose overflow rules, then an enforced text-fit engine**: measure with PIL/fonttools against real font metrics, compute line breaks per box, and shrink within a floor (e.g. 10pt body / 18pt title). Otherwise split/condense and send back to the LLM with a concrete "slot X over by N chars" error.
4. **Visual inspection of 2-3 PNGs, then a deterministic QA pass on the PPTX geometry**: bounds inside safe area, pairwise bbox overlap (with an allow-list for intentional overlays), min font, placeholder/"xx" leak, contrast of text vs fill (would have caught the white-on-gray BCG labels), empty-slot detection, and title length/lines. Keep the image review as a second, scored layer over *all* slides with an iteration cap.
5. **Chrome defaults, then master/layout placeholders** so the output is truly editable and themeable. Keep `Layout` tokens but derive a 12-column grid (margins 0.45", gutter about 0.2") and snap every region to it.
6. **"Dark navy bottom line" + exec-summary takeaways, then an explicit storyline layer**: governing thought, then SCR or pyramid key-line (3-5 arguments), then supporting slides, with action titles generated from and checked against the pyramid (the title-reads-as-storyline test).
7. **Growth arrow / focus bar / forecast shading**: generalize into a chart **annotation layer** on native charts (CAGR arrow, delta bracket, highlight series point, reference line, callout box), positioned from the chart's computed plot geometry.
8. **Placeholder gray convention, then an "unfinished content" state machine**: allow drafts with placeholders, but final validation must fail if any remain.
9. **Theme via `replace()`, then a brand-pack loader** (colors/fonts/logo/master from a .potx), since the reference's biggest product gap is brand templates.

---

## Slide types / layouts offered (40 functions, 52 registry keys)

| # | Key (aliases) | File:line | One-line description |
|---|---|---|---|
| 1 | executive_summary_paragraph (executive_summary) | executive_summary.py:13 | Title + optional dashed subtitle + 2-4 prose paragraphs |
| 2 | executive_summary_takeaways | executive_summary.py:46 | Bold takeaways each with indented bullets + bold final conclusion |
| 3 | dark_navy_summary | summary_slide.py:14 | Full-bleed deep-navy slide, one big white statement, `[Label]:` prefix |
| 4 | assessment_table (status_overview) | assessment_table.py:25 | Category-grouped KPI rows: target / actual / status label + traffic-light dot |
| 5 | bubble_chart | bubble_chart.py:172 | Full-width bubble scatter with group legend, diagonal ref line, state captions |
| 6 | bubble_chart_takeaways | bubble_chart.py:227 | Bubble scatter left + so-what pane right |
| 7 | growth_share (bcg_matrix) | bubble_chart.py:267 | BCG 2x2 with colored quadrants, bubbles = BUs |
| 8 | prioritization_matrix (assessment_matrix) | bubble_chart.py:370 | 3x3 impact x time-to-impact grid with status-colored circles |
| 9 | column_comparison | column_chart.py:271 | Sorted category bars, one focus bar highlighted, so-what pane |
| 10 | column_simple_growth | column_chart.py:297 | Time-series bars with one CAGR arrow |
| 11 | column_split_growth | column_chart.py:333 | Time-series bars with two CAGR arrows at a split index |
| 12 | column_historic_forecast | column_chart.py:381 | Actuals (navy) vs forecast (blue) bars with two CAGR arrows |
| 13 | three_trends_icons | trends_slides.py:40 | 3 rows: circle glyph icon + label + bullets |
| 14 | three_trends_table | trends_slides.py:92 | 3 rows: name pill / description bullets / examples |
| 15 | three_trends_numbered | trends_slides.py:166 | 3 rows: number circle + blue label pill + bullets |
| 16 | five_key_areas | trends_slides.py:218 | 5 numbered rows: area name then arrow then one-line description |
| 17 | overview_areas | timeline_slides.py:461 | 5-7 vertical cards with A-G badge, navy header, bullets, optional call-out |
| 18 | issue_tree | org_charts.py:46 | Root, then main, secondary and underlying drivers with elbow connectors |
| 19 | org_chart | org_charts.py:160 | CEO, then N heads, then stacked reports per head |
| 20 | project_team_circles | org_charts.py:258 | Leader circle + N member circles with icon, name, description |
| 21 | team_chart | org_charts.py:346 | Project bubble + function columns with filled/outline role dots |
| 22 | phases_chevron_3 | timeline_slides.py:48 | 3 chevrons with timeframe, deliverables and people lists |
| 23 | phases_table_4 | timeline_slides.py:156 | 4 phase columns: description / key activities / outcomes |
| 24 | waves_timeline_4 | timeline_slides.py:244 | 4 waves on a horizontal arrow with markers, activities, deliverables |
| 25 | gantt_timeline | timeline_slides.py:347 | Workstream rows x week columns bars + milestone dots |
| 26 | process_activities | timeline_slides.py:546 | 3-4 time-block columns x rows Activities / Mgmt interaction / Deliverables (diamonds) |
| 27 | cover_slide (cover) | structure_slides.py:23 | Title, subtitle, client, date, right navy stripe, CONFIDENTIAL tag |
| 28 | section_divider | structure_slides.py:90 | Left navy panel with huge number + section title/subtitle |
| 29 | agenda | structure_slides.py:145 | Numbered chapter list with optional active highlight |
| 30 | stat_hero (big_number) | structure_slides.py:207 | One huge number + label + context |
| 31 | quote_slide (quote) | structure_slides.py:274 | Big quote mark, quote text, attribution |
| 32 | comparison_table (option_compare) | comparison_slides.py:98 | Options x criteria with Harvey balls, notes, recommended column |
| 33 | pros_cons | comparison_slides.py:209 | Green check / red X two-column cards |
| 34 | two_column_compare (before_after) | comparison_slides.py:278 | As-is / to-be cards with connecting arrow |
| 35 | stacked_column_chart (stacked_column) | extra_charts.py:87 | Stacked bars with in-segment labels + totals + so-what pane |
| 36 | grouped_column_chart (grouped_column) | extra_charts.py:179 | Clustered bars per category + so-what pane |
| 37 | line_chart | extra_charts.py:260 | 1-4 lines of connector segments + markers + optional value labels |
| 38 | process_flow_horizontal (process_flow) | process_extras.py:22 | 4-6 overlapping numbered chevrons + description below |
| 39 | funnel | process_extras.py:99 | Narrowing stacked bands (rectangles) + descriptions right |
| 40 | kpi_dashboard | process_extras.py:189 | Grid of KPI tiles: label / big value / ▲▼ delta / context |

## Theme tokens (verbatim, theme.py)

Palette (hex):
```
dark_navy 0F2A4A   deep_navy 0A1F3D   bright_blue 2E9BD6   mid_blue 1F6FA8
light_blue 4FB2E5  royal_blue 2A2AE5  black 000000        white FFFFFF
text_dark 1A1A1A   rule_gray 999999   light_gray E8E8E8   soft_gray F2F2F2
grid_gray D0D0D0   footer_gray 888888 placeholder_gray BFBFBF
status_green 4CAF50 status_amber F4C57A status_red E04E5E
```
Typography: `family="Arial"`, `title_size=24`, `section_title_size=14`, `body_size=12`, `small_size=10`, `footer_size=9`, `chart_label_size=10`, `chart_axis_size=10` (pt). Korean override: `family="Apple SD Gothic Neo"`.
Derived sizes used in code: exec-takeaway 13, cover title 40, section number 80, section title 32, stat hero 104, quote mark 84, KPI value 36, dark-slide statement 26, trend icon glyph 18.
Layout (inches):
```
slide_width_in 13.333   slide_height_in 7.5  (16:9)
margin_left_in 0.45     margin_right_in 0.45   margin_top_in 0.35   margin_bottom_in 0.3
title_top_in 0.45       title_height_in 0.7    title_underline_top_in 1.15
body_top_in 1.40        footer_top_in 7.05
section_marker_w_in 1.4 section_marker_h_in 0.3  (marker top hard-coded 0.18, base.py:215)
```
Other: `copyright_text="Copyright of mckinsey-AX"`. Rules are 0.75pt (title) and 0.5pt (footer, chart headers). Gridlines are 0.5pt grid_gray. Bullet indent is 228600 EMU (0.25"). Chart box is (0.45, 1.95, 8.5, 4.85), the takeaway box is (9.45, 1.95, 3.45, 4.85) and the divider x is 9.30. Bar width is 60% of the slot (55% stacked, 75% group in grouped).

## Capability scoring (0 = absent, 1 = rudimentary, 2 = solid, 3 = strong)

| Capability | Score | Justification |
|---|---|---|
| Content ingestion | 1 | README promises xlsx/docx/pdf reading, but no code exists; it relies on the LLM's generic file tools. |
| Storyline | 1 | A suggested slide-order arc in the prompt (agent.md:81-89); no storyline model. |
| Pyramid principle | 0 | Not mentioned; no governing thought, SCR or key-line structure. |
| Slide planning | 2 | Explicit per-slide plan with template + "not X because Y" rationale; prompt-only. |
| Headline generation | 1 | "Action title" appears only in placeholder defaults; there are no rules and no check that titles are sentences/insights. |
| Executive communication | 2 | Exec-summary takeaways, dark bottom-line slide, so-what panes and a 5-10 slide guidance. |
| Visual choice | 2 | Good Use / Don't-use catalog and decision rules (CATALOG.md:815-851); LLM-judged, no scoring. |
| Layout selection | 2 | 40 templates with clear routing by item count and axis type; `infer_slide_type` fallback is brittle. |
| Layout library | 2 | 40 layouts covering most consulting archetypes, but fixed-count and hard-coded geometry. |
| Charts | 1 | Column/stacked/grouped/line/bubble drawn as shapes; no native charts, no negatives, decimals broken. |
| Tables | 1 | Assessment and comparison "tables" are rect grids; no native pptx table, no generic table template. |
| Waterfalls | 0 | None. |
| Bridges | 0 | None (no bridge/walk chart). |
| Timelines | 2 | Gantt, waves, chevrons, 4-phase table and process activities work for happy paths. |
| Matrices | 2 | BCG 2x2 and 3x3 prioritization look good, but axes/labels are hard-coded. |
| Trees | 2 | Issue tree with leaf-count allocation and elbow connectors; no overflow guard. |
| Processes | 2 | Chevron process flow, process activities, funnel (rectangles). |
| Maps | 0 | None. |
| Org charts | 2 | Org chart (2 levels + reports), team circles, function x role chart. |
| Bubble charts | 1 | Shape-drawn; linear-diameter sizing, non-nice ticks, manual label placement, overlaps in render. |
| Combo charts | 0 | None (no bar+line, no dual axis). |
| Conceptual diagrams | 1 | Chevrons, arrows, cards, Harvey balls; no generic framework/diagram engine. |
| SVG | 0 | No SVG handling or icon pipeline (emoji glyphs instead). |
| PPTX generation | 2 | Reliable python-pptx output, 16:9, runs without errors; default template, no master. |
| Editability | 1 | Text is editable, but charts are not data-editable, text is overlaid on shapes, nothing is grouped, and there are no title placeholders. |
| Visual consistency | 2 | Shared chrome and palette give a coherent look across all templates. |
| Fonts | 1 | Single family token set per run; no East-Asian slot and no embedding; the Korean font is macOS-only. |
| Colors | 2 | Clean navy/blue palette tokens + status colors; not written to theme XML. |
| Spacing | 1 | Margins are tokens, but internal spacing is ad-hoc literal inches per template; no spacing scale/grid. |
| Alignment | 2 | Zero-inset textboxes and shared margins align well in practice; no grid snapping. |
| Density | 1 | Word budgets exist only in the prompt; layouts don't adapt (huge gaps or overflow). |
| Overflow | 0 | No measurement; title shrink flag ineffective; overflow reproduced (titles, pros/cons, KPI). |
| Collisions | 0 | No detection or avoidance beyond manual label_pos/ox/oy; overlaps reproduced. |
| Rendering | 1 | Prompt instructs soffice + pdftoppm at 80 dpi; no code wrapper. |
| QA | 0 | No automated checks or tests of any kind. |
| Auto review | 1 | The LLM eyeballs 2-3 PNGs against a 4-item defect checklist. |
| Iteration | 1 | "Shorten and rebuild" instruction plus conversational edits; no loop control or scoring. |
| Final validation | 0 | No validation (placeholders, "xx" sources and brackets ship in outputs, e.g. demo_korean). |
