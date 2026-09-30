# AUDIT.md — Audit of the four reference implementations

> Mandatory intermediate deliverable (Phases 1–3). It was written **before** the engine was
> implemented. The detailed per-repository reports (with `file:line` references, verbatim tokens
> and justified scores) are in [`docs/audit/`](docs/audit/). This document synthesises them.

Method: the four repositories were cloned; all code and documentation was read (not just the
README); the available examples and tests were run; the PPTX outputs were rendered with
LibreOffice → PDF → PNG and inspected visually. Three audits ran in parallel as sub-agents with the
same brief (A–H + 38 capabilities); the fourth (PR #813) was done directly. Every defect cited
below was reproduced in a render, not inferred.

| # | Repository | What it really is | Size |
|---|---|---|---|
| 1 | `seulee26/mckinsey-pptx` | Claude Code plugin + python-pptx library of 40 templates + catalogue | 30 files, ~5.3k lines of Python |
| 2 | `vercel-labs/skills` PR #813 (`elite-ppt-pro`) | **Prompt-only** skill (pptxgenjs) with 38 layout snippets and 8 palettes | 3 Markdown files, 3.1k lines |
| 3 | `likaku/Mck-ppt-design-skill` | python-pptx engine `MckEngine` (67 methods) + geometric QA + JSON gate | 53 files, `engine.py` 3.2k lines |
| 4 | `kgraph57/mckinsey-style-visualization-skill` | Visualisation method + SVG/HTML renderer (22 patterns), no PPTX | 389 files, 335 tests |

---

## 1. Per-repository analysis

### 1.1 seulee26/mckinsey-pptx

**A. Problem.** Generate "McKinsey-style" decks in python-pptx from a prompt: the agent picks one template per slide, writes a build script, runs it and looks at 2–3 PNGs.

**B. Architecture.** `theme.py` (tokens in frozen dataclasses) → `base.py` (primitives + `add_chrome`) → `builder.py` (`_REGISTRY` with 52 keys, `infer_slide_type` by key sniffing, `PresentationBuilder`) → `slides/*.py` (40 template functions). Agent (`agents/mckinsey-slide-agent.md`), `/mckinsey-deck` command and `agent/CATALOG.md` (885 lines, *Use when / Don't use when / inputs / example* format).

**C. Flow.** Prompt → the LLM plans slide by slide with a "template X, not Y because…" rationale → writes `build.py` → runs it → optional render at 80 dpi → eyeball review.

**D. Strengths.** An excellent catalogue as a knowledge format (when to use / when not / tie-break rules between similar templates, CATALOG.md:816+). Explicit rationale per slide. Coherent chrome and a restrained navy/blue palette. Recognisable consulting patterns: "so-what" pane, CAGR arrow, forecast shading, KPI tiles, issue tree with space allocated by leaf count, BCG/3×3 matrices, Harvey balls.

**E. Weaknesses (verified in renders).**
- **No native charts**: everything is drawn with rectangles (0 charts and 0 tables in a 16-slide deck; up to 77 shapes per slide) → data is not editable.
- Chart bugs: negative values drawn off the slide; `int(round())` labels (0.45 → "0"); non-round bubble ticks; bubbles scaled by diameter (not area).
- Overflow and collisions: a two-line title collides with the rule below it; long lists run through the footer; a long KPI wraps; bubble labels overlap; white text on a light-grey quadrant (invisible).
- Connectors inherit the theme shadow (`p:style effectRef`) → blurry rules.
- Placeholders leak into deliverables ("[TIMELINE]", "Source: xx"); "McKinsey & Company" branding by default (trademark risk).
- **Zero automated QA**, zero tests, no text measurement.

**F. Reusable.** Catalogue format + tie-break rules; "not X because Y" rationale; round tick scale (`_y_ticks`, column_chart.py:28); arrowhead XML trick; bullet XML helpers; Harvey-score parser; issue-tree space allocation by leaves.

**G. Discard.** Shape-drawn charts, text overlaid on ungrouped shapes, shadowed connectors, `infer_slide_type`, fixed-count variants (3 trends, 5 areas…), emoji as icons, invented data, third-party branding.

**H. Reinterpret.** Catalogue → machine-readable layout metadata with capacity; rationale → a visual-reasoning object recorded per slide; CAGR arrows → an annotation layer over native charts; suggested slide order → an explicit storyline layer.

### 1.2 vercel-labs/skills PR #813 — `elite-ppt-pro`

**A. Problem.** A prompt skill that merges a multi-style layout library with a McKinsey-like "data-first" workflow, generating with pptxgenjs.

**B. Architecture.** No executable code. `SKILL.md` (7 steps: research ≥15 data points / ≥5 sources → plan → style → layout → pptxgenjs code → optional HTML → checklist), `slide-types.md` (38 JS functions: SWOT, Ansoff, Pareto, Chasm, KANO, STP, RFM, Gantt, journey, BMC, Porter, 2×2, KPI dashboard…), `qa-checklist.md`.

**C. Flow.** The agent researches, copies and adapts JS snippets, runs node and ticks the checklist by eye. No render.

**D. Strengths.** A quantified research gate and source hierarchy (Tier 1–5); mandatory `Source:` on every data slide; "title = conclusion" rule with ✅/❌ examples; at most 2 accent colours per slide; data-type → layout table; a standard 10-page structure; a wide catalogue of frameworks.

**E. Weaknesses.** No engine: each deck is rewritten from snippets → inconsistency. "≥4 content zones per page" contradicts "one idea per slide" and pushes towards overload. Headline at 10 pt in a 0.55" band. Gradients, "smart icons", 7 colour themes, page badges and an "Elite PPT Pro" watermark → *AI slide look*. Charts as rectangles. Internal contradiction (says pptxgenjs does not support gradients, then uses officegen syntax). Manual QA, no overflow measurement.

**F. Reusable.** Evidence gate and source convention; accent limit; data → visual table; the framework catalogue as **diagram types**; common-error table (→ automatic lint).

**G. Discard.** Multiple loud colour themes, gradients, icons, badges, watermark, the ≥4-zones rule, pptxgenjs snippets, dual HTML output.

**H. Reinterpret.** "Research first" → an evidence register in the *slide intent*; checklist → automatic checks + semantic rubric; framework library → diagram primitives parameterised by data.

### 1.3 likaku/Mck-ppt-design-skill

**A. Problem.** A python-pptx engine with fixed tokens and a 5-stage process (brief → outline.json → content.json → render → delivery) with geometric QA and a machine gate.

**B. Architecture.** `mck_ppt/engine.py` (`MckEngine`, 67 slide methods), `core.py` (primitives, EA/CJK font), `constants.py` (navy `#051C2C`, Georgia/Arial/KaiTi, 0.8" margins), `qa.py` (10 checks with severity and score), `review.py` (density, long titles, language mix, autofix), `references/scripts/gate_check*.py` (JSON `passed` + exit code), `references/layout-matrix.yaml` (per-layout capacities), planning guides and *guard rails*, `experiences/` (Problem/Cause/Fix/Rule lessons).

**C. Flow.** The LLM drafts brief and outline, picks layouts from a table, fills `content.json`, runs the engine, runs `qa.py` + gate; on failure, autofix (regex truncation + 1 pt shrink).

**D. Strengths.** **The code-derived gate** ("passed is decided by code, not by the LLM") — the best idea of the four. A QA inventory with explicit thresholds (slide overflow, text overflow, text–rule collision, dead whitespace on a 20×20 grid, text–text overlap >15%, font <8 pt, font consistency within a row, legends outside, connectors, `p:style`). Character budgets and max items per layout. Dynamic sizing formulas (`item_w=(CW−gap(n−1))/n`). "Adjacent slides do not share a layout" rule. CJK handling (`a:ea` font, 1.35 line spacing). Stress harness: one slide per layout with normal/stress fixtures.

**E. Weaknesses (verified).** No native charts or tables (line = stacked rectangles; "stacked area" = columns). Hand-coded geometry in almost every method; no solver. **No render step in the pipeline.** Its own test deck: 82/100 with 41 errors (its gate says FAIL); the 33-slide sample deck has 28 errors but `DeckBuilder` prints "QA passed". Character-count text estimation (0.55 em). Autofix that truncates sentences by regex (changes the meaning). Documentation out of sync (8 non-existent methods; `layout-matrix.yaml` is Markdown). Global exemption whitelist.

**F. Reusable.** JSON gate with exit code and exemptions **scoped by layout and with a reason**; the check inventory (improved with real metrics and rendering); per-layout capacities; sizing formulas; `**bold**` → runs parser; peer consistency; text–rule collision; stress harness; lessons-learned template.

**G. Discard.** Hand-placed geometry, shape-drawn charts, regex autofix, the Tencent cover-image module, Chinese text hard-coded in layouts, global whitelist.

**H. Reinterpret.** `content.json` → a typed specification the renderer consumes directly; capacity → validated **before** (budget) and **after** (measurement); capacity-based layout *fallback* (7 steps → vertical, or split the slide).

### 1.4 kgraph57/mckinsey-style-visualization-skill

**A. Problem.** Turn notes and metrics into consulting-style visuals with a rigorous method (triage, comparison gate, rubric, review loops) and a deterministic SVG renderer.

**B. Architecture.** A Markdown method layer (`references/*.md`: input-triage, document-type-profiles, persona-playbook, visualization-patterns, style-system, quality-rubric, iterative/expert-review-loop, reference-reproduction) + `scripts/render_slide_spec.py` (2k lines, stdlib) JSON → 1280×720 SVG for 22 patterns → HTML/PDF/Word. 6 deck archetypes in `templates/decks/`. 335 tests.

**C. Flow.** Strategic question → triage → document profile → headline (a single proposition, no "and") → pattern (Zelazny comparison gate) → style → spec → SVG render → rubric → review loops.

**D. Strengths.** **Visual-selection reasoning (the best)**: comparison gate (component, item, time series, distribution, correlation), a 16-row input-triage table, the reader's question per pattern, and the shortcut "what should the reader be able to do after 10 seconds?". Clear headline rules. **Density limits enforced by validators** with a "split, don't shrink" policy. A style system with single-source tokens, WCAG, diverging ramps. A /24 rubric with blocking gates and a **deck-level headline check (do they form a pyramid?)**. Review loops with 5 lenses (CEO, CFO, partner, visual editor, safety) and stopping criteria. Document-type profiles.

**E. Weaknesses.** **Does not generate PPTX** (explicitly out of scope) → editability 0. Character-count text fitting (headline/subline crowding observed in the Gantt). No general collision detection. Time series draw only the first series. No combo, bubble, stacked, trees, org charts, maps. The `review_slide_spec.py` reviewer scores keywords: a 16-line junk file scored 20/20. Inconsistent rubric (/24 vs /20). A lot of commercial material (LAUNCH, BUYER_BRIEF, MARKETPLACE…).

**F. Reusable.** Per-pattern spec schemas; triage; comparison gate and pattern → question table; document profiles; rubric and blocking gates; review lenses and stopping criteria; density limits; colour/type tokens; the "subtract before adding" rule.

**G. Discard.** Commercial documents, landing-site tooling, SVG/HTML/Word outputs, the keyword reviewer, "marketplace safety" as a score criterion.

**H. Reinterpret.** Schema → *slide intent* + storyline object; px tokens → pt/inches; patterns → native python-pptx charts, native tables and shapes; density limits → measured with real fonts; review → deterministic checks on structured data + the agent's visual review on real PNGs.

---

## 2. Capability comparison matrix

Scale 0 = absent · 1 = weak / documentation only · 2 = solid · 3 = strong and reusable.
S = seulee26 · E = elite-ppt-pro (PR #813) · L = likaku · K = kgraph57. **Best** = whose idea we take.

| Capability | S | E | L | K | Best | Why / what we take |
|---|---|---|---|---|---|---|
| Content ingestion | 1 | 1 | 1 | 1 | K | Nobody parses files; K has the best triage method → implemented with real readers |
| Storyline | 1 | 1 | 1 | 1 | K | Arc + headline check in prose; nobody has a storyline model → we built one |
| Pyramid principle | 0 | 0 | 0 | 1 | K | Only K mentions it (deck headline check) |
| Slide planning | 2 | 1 | 2 | 1 | L/S | Per-slide outline + "not X because Y" rationale |
| Headline generation | 1 | 2 | 1 | 2 | K/E | "One proposition" rules, ✅/❌ examples |
| Executive communication | 2 | 1 | 2 | 2 | K | CEO/CFO lenses, closing with owners, takeaway bar (L) |
| Visual choice | 2 | 2 | 1 | **3** | K | Comparison gate + triage + reader's question |
| Layout selection | 2 | 1 | 1 | 1 | S | Catalogue tie-break rules |
| Layout library | 2 | 2 | 2 | 1 | S/L | Breadth of patterns (without their hand-placed geometry) |
| Charts | 1 | 1 | 1 | 2 | K | Integrity rules; nobody uses native charts |
| Tables | 1 | 1 | 1 | 2 | K | Benchmark table with leader highlight |
| Waterfalls | 0 | 0 | 2 | 2 | K/L | Correct bridge maths (K), connectors (L) |
| Bridges (subtotals) | 0 | 0 | 1 | 2 | K | Nobody supports subtotals → added |
| Timelines | 2 | 2 | 1 | 1 | S | Gantt, waves, chevrons |
| Matrices | 2 | 2 | 2 | 2 | S/K | BCG / 2×2 with focus quadrant |
| Trees | 2 | 0 | 1 | 0 | S | Space allocation by leaves |
| Processes | 2 | 2 | 2 | 2 | K | Owner / duration / bottleneck |
| Maps | 0 | 0 | 0 | 0 | — | Nobody → editable *tile map* |
| Org charts | 2 | 1 | 0 | 0 | S | 2 levels + reports |
| Bubble charts | 1 | 0 | 1 | 0 | S | The idea yes, the implementation no (diameter scaling) |
| Combo charts | 0 | 0 | 0 | 0 | — | Nobody → native combo (two aligned panels, no dual axis) |
| Conceptual diagrams | 1 | 2 | 2 | 1 | L/E | Framework catalogue |
| SVG | 0 | 1 | 0 | **3** | K | Excellent, but not the target medium (editable PPTX) |
| PPTX generation | 2 | 1 | 2 | 0 | S/L | Reliable python-pptx |
| Editability | 1 | 1 | 2 | 0 | L | Native shapes; nobody has editable chart data |
| Visual consistency | 2 | 1 | 2 | **3** | K | A single token source |
| Fonts | 1 | 1 | 2 | 2 | L/K | EA/CJK font, font stacks |
| Colours | 2 | 2 | 2 | **3** | K | Semantic roles + WCAG |
| Spacing | 1 | 0 | 2 | 2 | L/K | Grid and gap rules |
| Alignment | 2 | 0 | 2 | 2 | L | Consistent LM/CW grid |
| Density | 1 | 0 | 2 | **3** | K | Hard limits + "split, don't shrink" |
| Overflow | 0 | 1 | 1 | 2 | K | Rejects dense specs (but by character count) |
| Collisions | 0 | 0 | 1 | 1 | L | Text–text and text–rule |
| Rendering | 1 | 0 | 0 | 2 | K | Nobody renders the PPTX inside the loop |
| QA | 0 | 1 | 2 | 1 | L | Check inventory + score |
| Automatic review | 1 | 0 | 1 | 1 | K | Lenses (as prompts) |
| Iteration | 1 | 0 | 1 | 1 | K | Well-defined stopping criteria |
| Final validation | 0 | 1 | 2 | 1 | L | **Code-derived JSON gate** |

**Reading the matrix.** No implementation scores above "2" across the whole chain. The shared
gaps are exactly the ones that define professional quality: (1) there is no structured *thinking*
layer (storyline / intent) before drawing; (2) nobody produces charts with editable data;
(3) nobody measures text with real metrics; (4) nobody renders the PPTX inside the QA loop;
(5) nobody closes the *generate → render → inspect → patch → re-render* loop.

---

## 3. Best practices found (to keep)

1. **Machine gate** (L): the `passed` verdict is computed by code and written to JSON with an exit code.
2. **Comparison gate + triage** (K): message type first, then the visual.
3. **"Split, don't shrink"** (K) with legibility floors; density limits enforced by validators.
4. **Headline = one proposition** with a conclusion (K, E), no "and" joining two claims.
5. **Deck headline check** (K): reading only the titles must tell the story (*ghost deck*).
6. **Mandatory source** on data slides (E, L).
7. **Catalogue with "use when / don't use when" + tie-break rules** (S).
8. **Per-layout capacity** (max items, budget per field) (L).
9. **Adjacent slides with different layouts** (L) — avoids monotony.
10. **A single token source**, semantic colour roles, WCAG contrast (K).
11. **Review lenses** CEO/CFO/partner/visual editor with stopping criteria (K).
12. **Stress harness**, one slide per layout (L).
13. **At most 2 accents per slide** (E); a single focus per exhibit.

## 4. Problems found (not to repeat)

| Problem | Where | Consequence | Answer in the new engine |
|---|---|---|---|
| Charts drawn with rectangles | S, E, L | Non-editable data, scale bugs | Native python-pptx charts + computed overlays |
| Hand-coded geometry | S, E, L | Overflow with real content | Declarative layouts on a 12-column grid |
| Text estimated by character count | L, K | Undetected overflow / false positives | Real font metrics (Liberation Sans ≡ Arial) |
| No render in the loop | S, E, L | Defects only visible when opening the PPTX | LibreOffice → PDF → PNG + QA on the rendered PDF |
| False "QA passed" | L (DeckBuilder) | Deliverables with errors | Single code-derived verdict, exit code |
| Autofix that truncates sentences | L | Changes the meaning | Autofix only touches form parameters; the agent rewrites text |
| Keyword reviewer | K | Gameable score | Checks on structured data + visual review on PNGs |
| Theme shadows on shapes/connectors | S | Blurry rules | `p:style` removed from every shape |
| Placeholders in the deliverable | S | "[TIMELINE]", "Source: xx" | Blocking `PLACEHOLDER_TEXT` check |
| Decoration (gradients, icons, loud themes, badges) | E | *AI slide look* | Restricted shape language, square corners, 1 accent |
| "≥4 zones per slide" | E | Overload | One idea per slide, capacity per zone |
| Third-party branding | S, L | Trademark risk | Consulting aesthetics without imitating brands |

## 5. Design decisions

| # | Decision | Reason |
|---|---|---|
| D1 | **Python + python-pptx** as the only runtime; LibreOffice only for rendering | Two of the four repos already use it; the most reliable path to native PPTX |
| D2 | **THINKING / RENDERING separated by a JSON `deck spec`** | Nothing is drawn without a complete *slide intent*; the spec is diffable and patchable |
| D3 | **Explicit storyline**: `governing_thought` + `key_line` + framework (SCR, CII, PDS, DRI, MPO, CGT, HEC) | Verifiable horizontal logic (*ghost deck*) |
| D4 | **Visual reasoning by message type** (Zelazny extended to 20 types) + data shape | The choice depends on the message, not on preference |
| D5 | **Declarative JSON layouts** on a 12-column grid with fixed vertical bands | Consistency by construction; declared capacity |
| D6 | **Native charts** with a deterministic *plot area* (`manualLayout inner`) + explicit round scales | Editable, with precise annotations (CAGR, totals, direct labels, waterfall connectors) |
| D7 | **Native tables** with their own styling (no Office table style) | Editable; heatmap, subtotals, deltas, Harvey balls |
| D8 | **Diagrams from named native shapes** | Editable; QA knows which zone each shape belongs to |
| D9 | **Real text metrics** (PIL + Liberation Sans) for planning and for QA | The same calculation before and after |
| D10 | **Three-layer QA**: structure/content (spec), geometry (PPTX), render (LibreOffice PDF: real text positions) | Detects *real* overflow and collisions, not estimated ones |
| D11 | **Bounded autofix** (layout, size within floors, table/list splitting, chart variant) + **agent patches** for text | Code never rewrites the message |
| D12 | **Final gate** `qa_report.json` with `passed`, blocking errors and exit code | Inherited from L, without a global whitelist |
| D13 | **Density by deck profile** (board, standard, analytical, status) | The style adapts to the deck type |
| D14 | **Restrained aesthetics**: square corners, no shadows, no gradients, no icons, 1 accent colour, typographic hierarchy | Avoid the *AI slide look* |

## 6. Proposed architecture

```
INPUT (txt, md, csv, xlsx, pdf, docx, pptx, json)
  │  cpe ingest            → inventory.json (text blocks, tables, numbers with context)
  ▼
CONTENT UNDERSTANDING      (agent, guided by SKILL.md §1 + triage)
  ▼
STORYLINE                  cpe scaffold  → deck.json with governing thought, key line, sections
  ▼                        cpe outline   → ghost deck (headlines only)  ← horizontal-logic review
SLIDE INTENT               purpose · headline · supporting_message · message_type · evidence
  ▼                        cpe lint      → structure + headlines + storyline + evidence
VISUAL ENCODING            core/visual_reasoning  (message_type × data shape → visual, with reason)
  ▼
LAYOUT SELECTION           core/layout_selector   (roles present × compatibility × capacity × variety)
  ▼
SLIDE SPECIFICATION        core/planner + density → resolved.json (visual, layout, fitting, splits)
  ▼
PPTX GENERATION            pptx/builder → painter → text_components · charts · tables · diagrams
  ▼                        + build_manifest.json (zones, boxes, fitting decisions)
RENDER                     render/renderer → PDF → PNG + contact sheet
  ▼
VISUAL QA                  qa/geometry (PPTX) · qa/render_checks (real PDF) · content (spec)
  ▼                        → qa_report.json / .md  (+ review packet for the agent's semantic review)
ITERATION                  qa/autofix → spec patches → rebuild (max N) ; agent → patches.json
  ▼
FINAL PPTX                 gate: passed ⇔ 0 blocking errors
```

Modules (`src/cpe/`): `spec.py` (contract), `ingest/`, `core/` (storyline, headline, visual_reasoning,
layout_selector, density, planner), `design/` (tokens, themes, profiles, text metrics),
`layout/` (layout engine), `pptx/` (painter, text components, builder), `charts/`, `tables/`,
`diagrams/`, `render/`, `qa/` (geometry, render, autofix, report), `cli.py`.
`layouts/` holds the declarative library by family (01–16). See `ARCHITECTURE.md`.

## 7. What to reuse / what to rewrite

| Component | Origin | Action |
|---|---|---|
| JSON gate with exit code | L | **Reuse the idea**, rewrite without a global whitelist |
| QA check inventory | L | **Rewrite** with real metrics + rendering; add zone, contrast, palette, placeholders, headline |
| Per-layout capacities | L | **Reinterpret** as `capacity` in layout JSON + measurement |
| Comparison gate, triage, reader's question | K | **Reuse** as a rule table in `visual_reasoning.py` |
| Density limits / "split, don't shrink" | K | **Reuse** with legibility floors per role |
| Rubric, blocking gates, lenses, stopping criteria | K | **Reuse** in the semantic review (review packet) |
| Headline rules | K, E | **Rewrite** as a deterministic, scored lint |
| "Use / don't use" catalogue + tie-breaks | S | **Reinterpret** in `when_to_use` + selector rules |
| Round tick scale, XML arrowhead | S | **Rewrite** (`nice_scale`, connectors) |
| Tree space allocation by leaves | S | **Rewrite** in `diagrams/tree` |
| `**bold**` → runs parser | L | **Reuse** the idea |
| Tier 1–5 data sources, mandatory `Source:` | E | **Reuse** in the evidence lint |
| Chart renderers (S, L, E) | — | **Discard**: native charts |
| SVG/HTML renderer (K) | — | **Discard** as output; the verification render is LibreOffice |

## 8. Technical risks

| Risk | Impact | Mitigation |
|---|---|---|
| LibreOffice does not render exactly like PowerPoint (metrics, charts) | Render QA false positives/negatives | Arial font (≡ Liberation Sans, same metrics); tolerances; geometric QA independent of the render |
| LibreOffice interprets the plot-area `manualLayout` differently | Misaligned overlays | Visual check in the loop; overlays only where they add value (totals, CAGR, direct labels) |
| Injected XML (combo, table borders, bullets) invalid for PowerPoint | "Repair file" prompt | Schema order respected; tests reopen every PPTX with python-pptx |
| The LibreOffice Impress component missing in the environment | No rendering | Detection and clear message; geometric QA still runs (`--no-render`) |
| CJK languages | Different metrics | Em-width fallback; documented as a limitation |
| Storyline quality depends on the agent | Correct but irrelevant deck | Storyline lint, ghost deck, rubric and lenses in SKILL.md |
| Autofix degrading the message | "Clean" but worse deck | Autofix does not touch text; anything needing rewording is reported as a pending patch |
