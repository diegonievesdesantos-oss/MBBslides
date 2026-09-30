# Audit: kgraph57/mckinsey-style-visualization-skill

Repo: `/tmp/claude-0/ref/mckinsey-style-visualization-skill` (HEAD `49d1370`, "Document mobile presentation trial and iOS verification"). The skill is named `strategy-consulting-visualization`.
Audited for: a unified Python + python-pptx "consulting presentation engine" that produces native, editable PPTX (storyline, slide intent, visual reasoning, layout, generation, render, QA, iterate).

**Evidence base.** I read the references, the scripts and the templates, and ran the tests. I rendered five example specs to PNG with cairosvg and inspected them.
- Test suite: `python3 -m pytest tests` gave **335 passed, 13 subtests passed in 1.57s**.
- Package validator: `validate_skill.py` returned `OK`.
- Review script: `review_slide_spec.py` scored the flagship example 20/20 and the v1 draft 14/20.
- Coverage gap: I only saw the first ~40 lines of `SKILL.md` (frontmatter, Purpose and Fast Path). A tool-permission block stopped me reading the rest. The output contract is reconstructed below from `references/prompt-templates.md` and the `REQUIRED_SECTIONS` list in `scripts/review_slide_spec.py`, which enforce the same headings.

---

## A. Problem it solves

It is an agent skill (SKILL.md package for Claude Code, Cursor, Codex and similar) that turns messy business input into consulting-style "insight-led" visuals. The input can be notes, metrics or prose. The flow is:
1. **Reasoning layer (Markdown references).** Triage the input. Name the reader's decision. Write a single-proposition headline. Pick a pattern through a comparison-type gate. Apply a strict style system. Score against a rubric with review lenses.
2. **Rendering layer (stdlib Python).** A JSON *slide spec* is rendered to a **16:9 SVG** (1280×720) for 22 patterns. The SVGs are then wrapped into an animated HTML deck, an HTML report (A4 print), a speaker script or an "article". PDF export goes through headless Chrome, and an optional Node script writes a Word briefing.

It is **not** a PPTX generator. PPTX is explicitly out of scope (`docs/superpowers/specs/2026-08-02-full-presentation-system-design.md:28`, "no PPTX export"). It is only a roadmap item (`ROADMAP.md:11`), and even that plan embeds SVGs via `svgBlip` rather than native shapes.

## B. Architecture (file refs)

| Layer | Files | Notes |
|---|---|---|
| Skill entrypoint | `SKILL.md` (142 lines) | Frontmatter says "Use when turning any content into clear, professional visualizations…". The Fast Path is scaffold, then edit JSON, then build the HTML deck, or Markdown to an HTML report. |
| Method references | `references/input-triage.md`, `visualization-patterns.md`, `document-type-profiles.md`, `persona-playbook.md`, `style-system.md`, `quality-rubric.md`, `iterative-review-loop.md`, `expert-review-loop.md`, `prompt-templates.md` | These hold most of the value. They are dense and well-reasoned. |
| Reference-fidelity study | `references/consulting-design-study.md`, `reference-reproduction.md`, `public-reference-corpus.md`, `consulting-reference-evidence.json` | A page-level study of 9 public docs from 6 firms, plus a reproduction workflow and a 0–2 × 8 fidelity rubric. |
| Renderer | `scripts/render_slide_spec.py` (1,999 lines, stdlib only) | Design tokens are module constants (l.36–120). There are 22 `render_*` functions, `RENDERERS` (l.1670), `CHROMELESS` (l.1698), per-pattern `VALIDATORS` (l.1868), `validate_spec` (l.1886), `render` (l.1936) and `render_exhibit` (l.1962, a compact chart body for documents). It has CJK-aware `wrap()` with kinsoku (l.157–293) and palette swap by string replace (l.337–347). |
| Heuristic reviewer | `scripts/review_slide_spec.py` (194 lines) | Scores the *Markdown spec text* by keyword and regex, out of 20. |
| Deck scaffolding | `scripts/scaffold_deck.py`, `templates/decks/{board-update, board-update-ja, market-entry, project-status, sales-proposal, strategy-recommendation}/deck.json + specs/*.json` | A manifest is `{title, description, slides:[paths]}`. Archetypes have 9–11 slides. |
| Output builders | `build_html_deck.py` (281), `build_html_report.py` (918, own Markdown subset), `build_html_article.py` (600), `build_speaker_script.py` (334, reads `notes` field), `export_pdf.py` (Playwright/Chrome), `build_briefing_docx.cjs` (Node `docx` + `sharp`) | All share the style tokens. |
| Site/marketing | `build_site.py`, `render_landing_decks.py`, `docs/site/**`, `site/*.json`, `assets/**` | Landing page, gallery, i18n. |
| Examples | `examples/render-specs/*.json` (25), `examples/board-update-*.md`, `examples/review-loop/*` (4 scenarios × draft/review v1/v2), `examples/evaluation-report.md` | |
| Tests | `tests/test_*.py` (13 files, 335 tests) | Heavy regression coverage on renderer geometry and text. |

## C. Operating flow

1. **Triage** (`input-triage.md`): identify the input type and the reader job ("decide, understand, follow, compare, remember, act"). Pick the pattern family and the document profile. Split mixed input into one visual per message.
2. **Comparison gate** (`visualization-patterns.md` Step 0): name the Zelazny comparison type (component, item, time series, frequency distribution, correlation) before picking a chart.
3. **Write the spec** in the output contract (Markdown). The sections are Strategic question, Insight headline, Recommended visualization (render-supported vs spec-only), Slide spec (canvas, layout, primary visual, data labels, annotations, source note), Data and assumptions, Quality check, and optionally Expert review notes.
4. **Encode as JSON** for renderer-supported patterns, or scaffold a deck archetype (`scaffold_deck.py`).
5. **Render** SVG with `render_slide_spec.py`, which validates first and raises `RenderSpecError` on density or overflow violations. Then build HTML, PDF or DOCX.
6. **Review**: `review_slide_spec.py` (heuristic, pass ≥18/20). Then run the iterative loop with 5 lenses (`iterative-review-loop.md`) and, for public or high-stakes work, 9 expert lenses plus 5 bias-breakers (`expert-review-loop.md`). Finish with the deck-level headline-only storyline check (`quality-rubric.md`).
7. **Iterate** until the stopping criteria are met (score ≥18, no blocking lens issue, assumptions visible, renderable, implication explainable in one sentence). The worked v1 and v2 examples are in `examples/review-loop/`.

## D. Strengths

1. **Design discipline written down as testable tokens.** The type scale is a ratio system (headline 40 : body 22 : chrome 13, with ratio checks asserted in tests). There is an 18px reading floor, a single navy, and an emphasis ladder (fill > line > text) with caps. Ink rules are explicit (no decorative bars, no border+fill, no vertical column rules). The renderer and the doc share the same constants.
2. **"Fewer words, not smaller type" enforced in code.** Validators *reject* over-dense content instead of shrinking it:
   - `bullet_list` >6 bullets, sub >3, or more than one emphasized bullet
   - `agenda` >8 items
   - executive `benchmark_table` >5 rows or 6 criteria
   - executive `process_flow` >5 steps, `two_by_two` >6 points
   - `commentary` rail too dense, `summary_strip` metric too wide, or focused block too dense
   - analytical headline >2 lines

   This is exactly the right philosophy for an overflow-free engine.
3. **Message-first method.** Triage, then comparison type, then pattern. Headlines are single propositions (no "and"), target ≤40 half-width units. There is a deck-level pyramid check (read the headlines only).
4. **Honest-charting rules.** Explicit 0 tick, diverging ramp for signed heatmaps, sign prefix plus colour in waterfalls (greyscale-safe), shared scale in small multiples, ellipsis plus `<title>` for any truncation, and waterfall scaling that is floored at zero so it can never draw off-canvas.
5. **CJK typography.** Width counting (fullwidth = 2), katakana run protection, line-start and line-end kinsoku, and bunsetsu-ish break preference. This is reusable in any text-fitting engine that has to handle Japanese.
6. **Useful catalogues.** Triage table, document profiles (including Japanese 稟議書/週報 etc.), persona playbook, and a reader-question per pattern.
7. **Well tested and deterministic.** There are 335 tests, a CI freshness check that committed SVGs stay byte-identical, and a regression history documented inline (e.g. band_start anchoring, rounds 2–3).
8. **Reference-fidelity study** with a measurable 16-point reproduction rubric and a "measure before reproducing" discipline (normalized geometry, colour mapped to meaning).
9. **Rendered visual quality** is clean, restrained and board-plausible (see §E for the flaws).

## E. Weaknesses (concrete)

1. **No PPTX at all.** The output is SVG, then HTML, PDF or DOCX. A slide is one SVG with absolutely positioned `<text>`, so it is **not editable** in PowerPoint beyond "convert to shapes". The charts are not native charts and hold no data. The roadmap PPTX plan embeds SVG blips, which is still not editable. The design doc says so itself: "Native editable Office charts are not implemented."
2. **Text fitting is char-count heuristics, not font metrics.** `wrap(text, width_units)` uses hard-coded unit budgets (`wrap(headline, 48)`, `wrap(annotation, 81)`, `T_BODY*0.62` per char). A mismatch shows up in rendering: the gantt headline "Sequence six workstreams around two decision gates" wraps to two lines, and the subline then crowds the month header row (y≈169 vs ≈202). There is no measured bounding box and no real font loading. SVG viewers substitute fonts, which changes widths.
3. **No collision or overlap detection.** The tests assert specific y coordinates and regressions (e.g. `test_waterfall_with_negative_cumulative_stays_inside_canvas`, `test_summary_metric_rejects_text_that_would_overflow`). There is no generic bbox-intersection QA pass. Collision safety depends on hand-tuned offsets (see the long comment in `header()` l.380–395 about 4px clearance).
4. **Limited chart grammar.**
   - `time_series` renders **only `series[0]`**, with no multi-series, combo or dual axis.
   - There are no stacked or 100% bars, clustered bars, bubble, Marimekko, Sankey, map, tree/org chart, pyramid, cycle, decision tree or timeline (non-gantt). All of these are "spec-only", meaning the skill writes text or an image prompt.
   - There are no per-chart axes with gridlines or ticks, and no axis scale control.
   - Heatmap and table cells are plain SVG text.
5. **Fixed single canvas and layout.** It is 1280×720 only, with a fixed header/chart-band/footer (208–560). There is no layout library (two-column chart + text, chart + table, multi-panel), except for the distribution-only `commentary` rail. White space is often unbalanced: the waterfall has a large empty band above the bars, and summary_strip leaves the bottom third empty.
6. **The review script is a keyword matcher and trivially gameable.** A 16-line junk Markdown file containing the section headings plus words like "waterfall annotation", "canvas layout source note", "5 assumption", "recommend original board contrast" scores **20/20** (tested). It never looks at the JSON or SVG and cannot check arithmetic, headline length, number consistency or density.
7. **Rubric inconsistency.** `quality-rubric.md` is out of **24** (it adds Data-Ink 0–4), but `iterative-review-loop.md` and `review_slide_spec.py` use **/20** with a ≥18 threshold. The rubric bands (20–24 marketplace) and the loop threshold (18) are not reconciled.
8. **Qualitative review is prompt-only.** The CEO/CFO/visual-editor lenses are text for the LLM. Nothing renders the SVG to pixels and inspects it (there is no vision QA and no render-then-check loop in code).
9. **Palette swap by string replacement** of `fill="#15296B"` works but is brittle. Themes are only `classic` and `executive`, and there is no brand/template ingestion (no .potx/master).
10. **Repo sprawl.** Much of the repo is marketing and growth material (LAUNCH, BUYER_BRIEF, COMMERCIALIZATION, GROWTH, TRACTION, MARKETPLACE*, SUBMISSION, landing site, i18n). There is a lot of duplicated rendered output (assets/rendered, docs/site/artifacts/rendered, en/ja copies).
11. **Storyline is prescriptive only.** There is no storyline object, no SCR/pyramid data structure, and no slide-planning step in code. The deck manifest is just an ordered list of spec paths.

## F. Reusable elements

### F1. Slide-spec JSON schema (as implemented in `render_slide_spec.py`)

**Common (content slides):**
```
pattern            (required) one of the 22 below
headline           insight headline; standard: wrap 48 units -> 40px, ≤2 lines, else 32px ≤3 lines
subline            scope / unit / period line (20px grey)
annotation         footer takeaway (22px navy 600, ≤2 lines, y=630)
source             source line (13px, y=692)
footnotes          [≤2 strings], rendered ¹ ²
page_number        int/str (bottom right)
classification     top-right marker (upper-cased)
theme              "classic" | "executive"
layout             "standard" | "analytical"  (analytical: exhibit_label at y=40, 32px sans headline ≤2 lines @64 units, subline ≤1 line @96 units at y=163)
exhibit_label      analytical only
palette            "navy" | "red" | "green" | "mono"   (primary/secondary: #15296B/#2563EB, #B4232D/#D96A72, #176B50/#439F7A, #202124/#686B70)
notes              string | [paragraphs] — ignored by renderer, used by speaker script / article
lang               used by kpi_scorecard / closing
```
**Per pattern:**
```
waterfall        unit, start{label,value}, drivers[{label,value(±)}], end_label   (end = start+Σdrivers, computed)
gap              unit, items[{label,value,emphasis?}], gap_label
before_after     unit, before_label, after_label, pairs[{label,before,after,unit?}]
time_series      unit, x_labels[], series[{label,values[]}]   (only series[0] drawn; len(x_labels)==len(values))
benchmark_table  columns[], rows[{label,values[] (len==columns)}], leaders[[row,col],...]   (executive: ≤5 rows, ≤6 cols)
summary_strip    blocks[{metric?,claim,proof,implication}], focus_block (0-based)
process_flow     steps[{label,detail,owner?,duration?}], highlight (index)   (executive ≤5)
funnel           unit, stages[{label,value numeric}]
heatmap          rows[], columns[], values[[num]] (rectangular), unit, diverging? (auto when data spans 0)
gantt            periods[], bars[{label,start,end,highlight?,note?}], gates[{label,period}]
kpi_scorecard    columns (default 3), metrics[{label,value,target,trend,status}]
two_by_two       x_axis{label,low,high}, y_axis{…}, quadrants[4], points[{label,x 0-100,y 0-100,emphasis?}], focus_quadrant 0-3, legend_title   (executive ≤6 points, numbered markers + key)
scatter          x_axis{label,unit?}, y_axis{label,unit?}, points[{label,x,y,emphasis?}], x_zero, y_zero
distribution     unit, bins[{label,value}], highlight, commentary{title, points[1-3]} (≤6 bins with rail)
small_multiples  unit, columns, charts[{label,values[],emphasis?}]  (shared scale)
cover            title (req), subtitle, classification, theme
section_divider  title (req), section_number int≥1 (req), subtitle, sections[]
end_cover        title (default "Thank you"), subtitle, contact[≤4], classification
agenda           items[{title,detail?}] (1-8; >6 → 2 columns), current (1-based)
bullet_list      bullets[{text, sub[≤3], emphasis?}] (1-6, ≤1 emphasized), columns 1|2
closing          takeaways[1-4]?, next_steps[{action (req), owner, timing}], call_to_action
quote            text (req), attribution, context
```
**Deck manifest:** `{"title", "description", "slides": ["specs/01-cover.json", ...]}`.
**Output contract (Markdown, per slide):** Strategic question, Insight headline, Recommended visualization, Slide spec (Canvas / Layout / Primary visual / Data labels / Annotations / Source note), Data and assumptions, Quality check, Expert review notes (Assumption challenged / Reader fit / Accessibility-localization / Counterpoint).

### F2. Input triage method (`references/input-triage.md`)

Steps: name the input type, then the reader job (decide/understand/follow/compare/remember/act), then the pattern family, then the document profile. Mixed input is split into one visual per message.

| Input type | Reader job | Pattern family |
|---|---|---|
| Quantity over time | Spot momentum/inflection | Time-series, before-after |
| Comparison across items | Pick or rank | Benchmark table, gap, ranked bars |
| Part-to-whole | See composition | Market share, stacked composition |
| Change decomposition | What drove the change | Waterfall |
| Process/workflow | Follow/improve sequence | Process flow, funnel, cycle |
| Plan over time | Know what happens when | Timeline, Gantt/roadmap |
| Hierarchy/structure | Navigate levels | Tree, pyramid |
| Relationships/systems | See interactions | Concept/system map, Sankey |
| Position across two drivers | Choose a position | 2x2, scatter |
| Many-by-many intensity | Find hot spots | Heatmap |
| Distribution | Spread/outliers | Distribution |
| Status snapshot | Scan state | KPI scorecard, maturity grid |
| Decision logic | Branch correctly | Decision tree |
| Qualitative argument | Grasp claim + support | Summary strip, pyramid, contrast |
| Instructional | Learn/retain | Process, concept map, before-after, cycle |
| Geographic | Spatial concentration | Annotated map, ranked bars by region |

Difficult-input rules:
- **Prose with no numbers:** visualize the argument structure and never invent numbers.
- **Long documents:** reduce to 3–7 message units, with one pattern per unit plus an overview.
- **Vague requests:** state the assumed reader, job and pattern.
- **Mixed input:** the qualitative claim becomes the headline and the numbers become the proof.
- **Fewer than 3 data points:** use a scorecard, contrast or annotated statement, and flag the gap.
- **Regulated domains:** mark conclusions as user-provided.

One-question shortcut: "What should the reader be able to do after ten seconds?" Decide → comparison; why changed → waterfall/before-after; follow steps → process/decision tree; where they stand → gap/scorecard/maturity; remember → summary strip/pyramid.

### F3. Document-type profiles (`references/document-type-profiles.md`)

| Profile | Canvas | Density | Tone | Preferred patterns |
|---|---|---|---|---|
| Board/executive deck | 16:9 | High | Decisive, analytical | Waterfall, benchmark, 2x2, summary strip |
| Internal report/memo | A4 portrait, inline figs | Medium | Neutral, factual | Time-series, gap, scorecard, tables |
| Research/whitepaper | A4, numbered figs | High | Cautious, sourced | Distribution, scatter, heatmap, methodology flow |
| Sales proposal/pitch | 16:9 | Medium | Confident, customer-framed | Before-after, contrast, timeline, funnel |
| Project status/steering | 16:9 or A4 | High | Direct, risk-aware | Gantt, scorecard, heatmap, decision tree |
| Training/education | 16:9 or 4:3 | Low-med | Patient, sequential | Process, cycle, concept map, before-after |
| Technical docs | Inline, flexible | Medium | Precise | System map, process, decision tree, hierarchy |
| One-pager/fact sheet | A4 single page | Very high | Compressed | Summary strip, scorecard, mini-charts |
| Infographic | 4:5 / 9:16 | Low | Plain-language | Pyramid, cycle, annotated map, big numbers |
| Policy brief | A4 | Medium | Balanced | Timeline, contrast, gap, distribution |
| Academic/clinical | A4/poster | High | Conservative | Distribution, before-after, methodology flow, tables |
| Personal notes | Flexible | Low | Informal | Concept map, hierarchy, checklist, timeline |

Profile notes:
- **Status decks** must show plan vs actual and the ask.
- **Proposals** frame headlines around customer outcomes.
- **One-pager:** 2–4 visuals and one dominant number, readable in 60 seconds.
- **Japanese overlays:** 稟議書, 週報/月報, 役員会資料 (結論ファースト), 学会抄録, 社内勉強会, 提案書. Each has specific ordering rules.

### F4. Persona playbook (`references/persona-playbook.md`)

| Persona | Go-to patterns |
|---|---|
| Sales | Funnel, before-after, benchmark |
| Marketing | Heatmap, funnel, time-series |
| Product manager | 2x2, gantt, KPI scorecard |
| PMO | Gantt, KPI scorecard, heatmap |
| HR | KPI scorecard, heatmap, maturity grid |
| Engineer | Process flow, decision tree, benchmark |
| Researcher/clinician | Before-after, distribution, methodology flow |
| Finance/FP&A | Waterfall, gap, time-series |
| Founder/exec | Waterfall, summary strip, 2x2 |

Each persona has a copy-paste prompt template that states the audience and the decision. Personas change the framing, not the rules.

### F5. Visualization selection logic

**Step 0, comparison gate (Zelazny):**

| Comparison type | You are saying | Pattern families |
|---|---|---|
| Component | "X is n% of the total" | Market share, stacked composition |
| Item (ranking) | "A is bigger/better than B" | Gap, benchmark table, investment/scale |
| Time series | "X is rising/falling/flat" | Time-series, before-after, waterfall, small multiples, gantt |
| Frequency distribution | "Most cases fall in this range" | Distribution, heatmap |
| Correlation | "X moves with Y" | Scatter, 2x2 |

Qualitative structures (process, hierarchy, cycle, decision logic) skip the gate and go to the structural patterns.

**Pattern → strategic/reader question (✓ = renders to SVG):**

| Pattern | Render | Question |
|---|---|---|
| Time-series | ✓ | Is momentum accelerating or stalling? |
| Gap | ✓ | How large is the gap and why does it matter? |
| Before-after | ✓ | What changed and is it enough to justify action? |
| Market share | spec | Where is the center of gravity? |
| Investment/scale | spec | Who has the scale advantage? |
| Timeline | spec | What must happen, and when? |
| Contrast diagram | spec | Where are the structural differences? |
| 2x2 | ✓ | Which position is attractive or exposed? |
| Benchmark table | ✓ | Who leads on the dimensions that matter? |
| Waterfall | ✓ | What drives the delta? |
| Summary strip | ✓ | What should the executive remember? |
| Process flow | ✓ | What happens, in what order, who owns each step? |
| Funnel | ✓ | Where do we lose the most? |
| Cycle | spec | What sustains or breaks this loop? |
| Hierarchy/tree | spec | How is this organized? |
| Pyramid | spec | What is the foundation? |
| Concept/system map | spec | How do the parts interact? |
| Gantt/roadmap | ✓ | Are we on track, what blocks what? |
| Heatmap | ✓ | Where are the hot spots? |
| Scatter | ✓ | Do these move together, outliers? |
| Distribution | ✓ | What is typical, what is extreme? |
| Small multiples | ✓ | Does the pattern hold everywhere? |
| Stacked composition | spec | What is the mix and how is it changing? |
| KPI scorecard | ✓ | What is healthy, what needs attention? |
| Decision tree | spec | Given my situation, what do I do? |
| Sankey | spec | Where does the volume go? |
| Maturity grid | spec | What is done, what is next level? |
| Annotated map | spec | Where is this happening? |
| Structural slides (✓) | | Section divider, agenda, bullet_list (action title), closing, quote, end cover, cover |

**Pattern-level rules worth keeping:**
- Donut only for few segments; otherwise ranked bars.
- Timeline: even spacing for phases, proportional spacing for dates.
- Funnel shows counts and stage conversion, and annotates the single largest drop.
- Tree: ≤3 levels shown.
- Concept map: ≤12 nodes.
- Stacked: ≤5–6 segments, then "Other".
- Map only when geography *is* the message.
- Gantt: one row per workstream in executive views, with plan vs actual.
- Decision tree leaves must be actions.

### F6. Quality rubric (`references/quality-rubric.md`, /24)

| Criterion | Max | Top anchor |
|---|---|---|
| Strategy | 5 | Headline answers a decision-critical question; implication clear (3 = partly descriptive; 1 = chart request; 0 = no decision) |
| Data integrity | 5 | Values, labels, units, assumptions, sources explicit and consistent (0 = invents data) |
| Visual hierarchy | 4 | Eye goes headline → key number → implication; ≤1–2 strong-emphasis elements |
| Data-ink & graphical integrity | 4 | Lie factor ≈1.0 (±5%), zero baselines marked, floating bars labelled, no silent truncation |
| Portability | 3 | Renders without extra explanation; spec-only is disclosed |
| Marketplace safety | 3 | No affiliation or fabricated evidence |

Bands: 20–24 marketplace quality, 17–19 usable draft, 12–16 internal only, 0–11 restart.

**Deck-level check (yes/no):**
- Do the headlines alone form one pyramid argument?
- Is each headline one proposition (no "and")?
- Is any headline repeated or contradicted?

**Blocking gates:**
- Language more universal or certain than the evidence
- Reader or decision not named
- Recommendation would flip under a plausible missing-data scenario that is not disclosed
- Meaning depends on colour alone, tiny labels or jargon
- Output implies professional verification or affiliation
- Output implies a rendered file for a spec-only pattern

### F7. Review loop steps

- **Iterative loop** (`iterative-review-loop.md`): reference scan → draft → executive review → revision → rubric score → repeat.
  - 5 lenses: CEO/board (decision vs description), CFO (numbers, units, deltas), strategy partner (sharp answer), visual editor (hierarchy in 5 seconds), safety.
  - Stop when score ≥18 **and** no blocking lens issue **and** assumptions visible **and** the spec renders without interpretation **and** the implication fits in one sentence.
  - If a blocking issue repeats twice, return to the strategic question.
  - Revision rules: fix the highest severity first; keep the data accurate even if the visual gets less dramatic; one implication beats many; make assumptions more visible.
  - Review template: Score / Blocking Issues / Revision Instructions / Decision.
- **Expert loop** (`expert-review-loop.md`):
  - 9 lenses: methods professor, behavioral scientist, executive operator, CFO, UX, dataviz, accessibility, cross-cultural, legal.
  - 5 bias-breakers: most-likely-wrong assumption, who rejects the framing, missing data that flips the recommendation, overcertain wording, works without colour or jargon.
  - "Subtract before adding" rules: remove adjectives before adding caveats, remove precision before adding footnotes, split before annotating.
- **Reproduction rubric** (`reference-reproduction.md`): 8 dimensions × 0–2 (narrative hierarchy, frame geometry, type hierarchy, chart encoding, annotation/labels, source/notes, page flow, editability). Target ≥14/16 with no zero on encoding, labels or source.

### F8. `review_slide_spec.py` checks and thresholds (Markdown text heuristics)

| Dimension | Points | Rule |
|---|---|---|
| Required sections | issue only | Strategic question, Insight headline, Recommended visualization, Slide spec, Data and assumptions, Quality check (as `## X` or `**X:**`) |
| Strategy | +3 | Strategic question and headline sections present |
| | +2 | Text contains recommend / approve / sequence / "should be" / "decision:" |
| Data integrity | +2 | Any number regex (`$?\d+(\.\d+)?\s?(%\|M\|B\|T\|x\|pts\|points)?`) |
| | +3 | Contains assumption / source / provided / missing / "not provided" |
| Visual hierarchy | +2 | Contains a pattern word (waterfall, timeline, gap, benchmark, 2x2, matrix, contrast, market, before, after, executive summary, cover) |
| | +2 | Contains annotation / primary number / direct label / implication box |
| Portability | 3 | Slide spec present and canvas + layout + source note all present |
| | 2 | Slide spec present only |
| Safety | +2 | No affiliation phrases ("official mckinsey", "bcg-approved", …) |
| | +1 | Contains not affiliated / original / no copied / source-aware / user-provided |
| Warnings (no score) | | Overconfident words (always, guaranteed, best option, all users, everyone, no risk, will definitely); no reader term (reader, audience, stakeholder, leader, executive, board, operator); no accessibility term |

Total /20, `--min-score` default **18**, exit 1 if below. It is gameable (see E6), so reuse the *check list* only, re-implemented on structured data.

### F9. Style-system tokens

- **Canvas:** 1280×720 px. 8px grid. Margins L/R 80. Headline baseline y=96. Chart band y=208–560. Annotation y=630. Source/page y=692. Classification y=40.
- **Colours:**

| Role | Hex |
|---|---|
| Background | `#FFFFFF` |
| Primary text | `#000000` |
| Primary accent navy (also cover background) | `#15296B` |
| Secondary accent | `#2563EB` |
| Dark grey | `#374151` |
| Medium grey | `#6B7280` |
| Border grey | `#D1D5DB` |
| Light fill | `#F3F4F6` |
| Accent tint | `#EFF3FB` |
| Risk red | `#B91C1C` |
| Red tint | `#FBEAEA` |
| Strong rule | `#9CA3AF` |
| Cover secondary text | `#E5E7EB` |

  Alternative palettes: red `#B4232D`/`#D96A72`, green `#176B50`/`#439F7A`, mono `#202124`/`#686B70`.
- **Type (px on 1280 canvas):**

| Token | Size |
|---|---|
| Cover title | 54 serif |
| Divider title | 48 |
| Headline | 40 bold serif (≤2 lines) |
| Dense headline | 32 (3 lines) |
| Statement | 32 |
| KPI number | 44 |
| Subline | 20 |
| Body | 22 |
| Label (reading floor) | 18 |
| Agenda numbers | 28 |
| Closing numbers | 26 |
| Tick | 14 |
| Kicker | 15 letter-spaced |
| Annotation | 22 semibold navy |
| Chrome | 13 |

  Line heights: body 30, label 24. Ratio rules: Headline/Body ≥1.7 (actual 1.8), Body/Chrome ≥1.6 (1.7), Cover/Chrome ≈4.2.
- **Fonts:** Georgia (headline serif) plus Helvetica Neue/Helvetica/Arial (sans). CJK: Hiragino/Yu, with system faces listed before Noto Sans JP. The executive theme uses sans headlines.
- **Emphasis ladder:**
  1. Solid navy fill with white text
  2. Tint fill with navy text
  3. Navy outline
  4. Blue text
  5. Bold text
  6. Body

  Use at most 1 (rarely 2) strong rungs per slide, never stack rungs, and keep red orthogonal to the ladder.
- **Word budget:** headline ≤40 half-width units (≈20 JP characters), one proposition; bullets 1 line (max 2); sub-bullets 1 line; summary proof/implication ≤2 lines.
- **Geometry caps:** executive bars and columns ≤88px; gap and funnel bands ≤28px.

## G. Discard

- Marketing and commercial docs: `LAUNCH.md`, `BUYER_BRIEF.md`, `COMMERCIALIZATION.md`, `GROWTH.md`, `TRACTION.md`, `MARKETPLACE*.md`, `SUBMISSION.md`, `DISTRIBUTION.md`, `marketplace/`, the README "Why This Gets Starred / Roasted by Five Design Legends" sections, and `docs/superpowers/plans|specs` (landing-site and marketplace plans).
- Site tooling: `build_site.py`, `render_landing_decks.py`, `docs/site/**`, `site/*.json`, and duplicated `assets/rendered/**`.
- The SVG renderer as an output path (string-built `<text>` elements), the palette string-replace, the HTML deck/article/speaker-script builders, `export_pdf.py`, `build_briefing_docx.cjs` and the custom Markdown parser.
- The "marketplace safety" rubric dimension and the affiliation-phrase lists. For a private engine, keep only a generic "no fabricated sources/claims" gate.
- `review_slide_spec.py` as written (keyword scoring of prose).

## H. Reinterpret (for a python-pptx engine)

1. **Spec schema → slide-intent model.** Keep the per-pattern field shapes (F1) almost verbatim as a pydantic schema. Add `intent` (reader job and comparison type), `message` (headline), `evidence`, and `layout_id`. The deck manifest becomes a storyline object (governing thought → sections → slides) instead of a list of paths.
2. **Tokens → theme module.** Port the colours, type scale and grid to EMU/pt. On a 13.333×7.5in slide, 1px@1280 ≈ 0.75pt: headline 40px → 30pt, body 22 → 16.5pt, label 18 → 13.5pt, chrome 13 → ~10pt. Keep the ratio assertions as unit tests.
3. **Validators → pre-render density gates.** Keep all caps (≤6 bullets, ≤3 subs, ≤8 agenda, ≤5×6 exec table, ≤5 process steps, ≤6 matrix points, ≤2-line headline, ≤3 commentary points). Replace char-unit `wrap()` with **real font-metric measurement** (PIL `ImageFont.getbbox` on the actual TTF) so the "reject, don't shrink" policy is exact.
4. **Renderers → native builders.**
   - Waterfall, gap, funnel, time series, before-after, distribution, small multiples, scatter: native `XL_CHART_TYPE` charts with data, or native rectangles when a chart type does not exist (a waterfall as a stacked bar with an invisible base series).
   - Tables: native `add_table`.
   - Process, 2x2, gantt, summary strip, KPI: grouped autoshapes.
   - Port the geometry math (waterfall cumulative scaling floored at 0, gantt period mapping, 2x2 0–100 coordinates with numbered markers and a key) directly.
5. **Add the missing families** with the pattern notes as the design spec: stacked/100%, clustered, combo/dual-axis, bubble, Marimekko, timeline, tree/org, pyramid, cycle, decision tree, Sankey-ish, map.
6. **QA.** Replace the keyword reviewer with structured checks on the spec and the generated PPTX:
   - bbox overflow and collision from shape frames plus measured text
   - font and size whitelist
   - colour whitelist
   - headline length and the no-"and" rule
   - arithmetic reconciliation (waterfall end = start + Σ, % sums)
   - emphasis-rung count
   - zero baseline present
   - source present

   Then render (LibreOffice → PNG) and run a vision review using the 5 and 9 lenses as prompts. Unify the rubric at /24 with explicit thresholds and blocking gates.
7. **Method docs → planner prompts.** The triage table, comparison gate, profile table, persona table and the "one-question shortcut" become the slide-planning and visual-reasoning stage. The deck-level headline check becomes an automated storyline pass.
8. **CJK wrapping** (kinsoku, katakana runs, bunsetsu breaks) is worth porting as a text utility if JP decks are in scope. python-pptx wraps natively, but pre-measurement for overflow gates needs the same break logic.

---

## Capability scores (0 = absent, 1 = weak/doc-only, 2 = solid, 3 = strong and reusable)

| Capability | Score | Justification |
|---|---|---|
| Content ingestion | 1 | Triage method is good, but there is no parser. The LLM reads raw notes, and the only structured input is hand-written JSON or Markdown. |
| Storyline | 1 | Deck arc and headline-only pyramid check are prose rules. The manifest is a flat list, and there is no storyline data model. |
| Pyramid principle | 1 | Named in the deck-level check and summary_strip (claim/proof/implication). The pyramid pattern is spec-only, and nothing enforces it. |
| Slide planning | 1 | "3–7 message units, one pattern each" plus 6 fixed archetypes. There is no planner. |
| Headline generation | 2 | Clear rules: single proposition, no "and", ≤40 units, decision-linked, 2-line/3-line fitting. Generation itself is left to the LLM. |
| Executive communication | 2 | Strong guidance (decision, owner, timing, ask; closing with owners; 5 and 9 lenses). |
| Visual choice | 3 | Comparison-type gate, triage table, reader-question per pattern and one-question shortcut. Directly reusable. |
| Layout selection | 1 | One fixed band layout plus the analytical header variant. There is no selection logic across layouts. |
| Layout library | 1 | Effectively one template (header/chart band/footer) plus the distribution commentary rail. |
| Charts | 2 | 10 data charts render cleanly with honest-scale rules, but only as SVG and time series is single-series. |
| Tables | 2 | benchmark_table with leader highlighting, zebra rows and exec caps. SVG text only. |
| Waterfalls | 2 | Correct bridge math, zero floor, signed labels, exec grey/navy styling. No subtotals and no horizontal variant. |
| Bridges | 2 | Same as waterfall. No multi-step subtotal bridges. |
| Timelines | 1 | Gantt with gates and a critical path renders. A true milestone timeline is spec-only. |
| Matrices | 2 | 2x2 (numbered markers, focus quadrant) and heatmap (auto-diverging, WCAG cell text) render. |
| Trees | 0 | Spec-only (hierarchy/tree, decision tree). |
| Processes | 2 | process_flow with owner, duration and highlighted bottleneck, ≤5 steps. No swimlanes or cycles. |
| Maps | 0 | Spec-only, with advice to prefer ranked bars. |
| Org charts | 0 | Not implemented. |
| Bubble charts | 0 | Scatter has no size encoding. |
| Combo charts | 0 | No combo or dual axis. Time series draws series[0] only. |
| Conceptual diagrams | 1 | summary_strip, quote and closing only. Cycle, pyramid and system map are spec-only. |
| SVG | 3 | Deterministic, well-tested SVG with a11y `role=img`, aria-label and `<title>` on truncations. |
| PPTX generation | 0 | None. Explicitly out of scope; the roadmap only plans SVG embedding. |
| Editability | 0 | Positioned SVG text, image charts in DOCX, no native shapes or charts. |
| Visual consistency | 3 | Single token source shared by doc and code, ratio tests, byte-identical CI check, 6 consistent archetypes. |
| Fonts | 2 | Named stacks with CJK ordering rationale. No font embedding or metric measurement; viewer substitution changes widths. |
| Colors | 3 | Restrained palette, semantic roles, greyscale-separation and WCAG tests, diverging ramps. |
| Spacing | 2 | 8px grid, fixed bands, documented row-anchoring rules. Whitespace is sometimes unbalanced (empty bands). |
| Alignment | 2 | Consistent ML anchor and shared baselines. Hand-tuned offsets, no alignment engine. |
| Density | 3 | Hard caps enforced by validators, word budget, "split, don't shrink" policy. |
| Overflow | 2 | Ellipsis+`<title>`, rejection of too-dense specs, CJK hard-breaks. Based on char-count estimates, not real metrics (gantt headline/subline crowding observed). |
| Collisions | 1 | Specific regression tests for known collisions. No general bbox intersection check. |
| Rendering | 2 | SVG, HTML, PDF (Chrome) and DOCX paths all work. No raster preview in the loop. |
| QA | 1 | 335 unit/regression tests on code, but content QA is a gameable keyword scorer (junk file scored 20/20). |
| Auto review | 1 | `review_slide_spec.py` is text-heuristic only. The lenses are prompt text. |
| Iteration | 1 | The loop is well specified (stop criteria, repeat-twice rule, worked v1→v2 examples) but is not automated. |
| Final validation | 1 | `validate_skill.py` checks packaging only. There is no final artifact validation beyond successful render and the ≥18 heuristic. |
