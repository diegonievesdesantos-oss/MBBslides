---
name: consulting-presentation-engine
description: >
  Turn structured or unstructured input (notes, documents, PDFs, Excel/CSV, research, financials,
  business cases) into a top-tier consulting PowerPoint, or update an existing deck with new figures.
  Storyline-first (pyramid principle, SCR and 6 other frameworks); every number traced to a cited
  source; one evidence-backed proposition per slide, stated by a conclusion headline the engine
  verifies (no topic titles, unsupported numbers or causal claims); sibling messages in parallel
  wording; visuals chosen by the message; 45 grid layouts in 16 families; native editable
  charts/tables/shapes; corporate templates; and an automatic render → QA → patch loop with
  machine-derived pass/fail verdicts. Use for strategy decks, board and steering committee
  presentations, business reviews, investment memos, CDD, market analysis, transformation /
  operating-model / roadmap decks, financial analysis and executive updates, in English or Spanish.
---

# Consulting Presentation Engine — operating manual

You are the **thinking** layer. The engine is the **rendering + checking** layer.
Never start by drawing. You write a *deck spec* (JSON) in which every slide carries a
complete **slide intent**; the engine turns it into a native `.pptx`, renders it,
inspects it and tells you exactly what to fix.

```
INPUT → UNDERSTAND → STORYLINE → SLIDE INTENT → SO-WHAT → EVIDENCE → VISUAL → LAYOUT CANDIDATES
      → COMPOSITION CANDIDATES → RENDER → COMPOSITION SCORING → BEST → PPTX → RENDER
      → QA (content · geometry · render · composition) → PATCH → … → FINAL PPTX
```

All commands: `scripts/cpe <command>` from the skill folder (or `python -m cpe` with `src/` on the path).
Requirements: Python ≥3.10, `pip install -r requirements.txt`, LibreOffice **with Impress**
(`libreoffice-impress`) for rendering, Liberation Sans fonts (Arial metrics).

### Raw material → deck (reasoning protocol 1.5)

When the input is raw business material rather than a ready storyline, follow
`docs/REASONING_PROTOCOL.md` **before** writing a deck spec: `cpe reason facts sources/ -o work/`
builds a traceable fact model; you write `project.json` (business question), `hypotheses.json`,
`insights.json`, `storyline.json` (≥ 2 governing-thought candidates, plus a `decision` frame: levers
that add up to the stated total and gap to target, the current plan tested, options costed on the same basis, approvable
asks, gates and KPIs, problem before solution) and `deck_plan.json` (why each
slide exists); `cpe reason check work/ --enrich` blocks the deck on any invented number, wrong source,
arithmetic error or claim resting on a rejected hypothesis. Row-level data (orders, CRM, ledgers) is aggregated by your own scripts run through
`cpe reason analyze` (recorded, hashed, re-run), whose outputs become citable facts. You may create hypotheses, insights and
wording — never facts. Computations go in `computed_facts.json` (formulas over fact ids, recomputed);
assumptions in `assumptions.json` (flagged wherever they reach a headline). `cpe reason trace work/
"<sentence>"` explains any sentence down to source cells.

Protocol 1.5 adds five rules (`docs/REASONING_PROTOCOL.md`):
1. **Contingency.** Investments carry a contingency when a comparable phase overran.
2. **Options, not the supplier's calendar.** Whenever an option carries an investment, compare
   renegotiating (`kind: renegotiate`) and deferring (`kind: defer`) with approving. A
   counterparty's deadline is a negotiation fact, not a criterion.
3. **Gates with margin.** Gates state `threshold`, `break_even` and `period_weeks`, clear the
   break-even by 5% or more, and run 8 weeks or more.
4. **Discarded evidence stays discarded.** Mark it with `insights[].discards`; when a slide shows it
   only to set it aside, mark the evidence item `"as_discarded": true`.
5. **Coherent figures.** One base per quantity; assumptions stay out of the summary and headlines
   (declare `rests_on_assumptions` on computed facts that need one); no rejected hypothesis comes back
   as a risk.

The partner review covers capacity, sunk costs, contingency, external deadlines and unsourced history.

---

## 0. When to use / not use

Content can be English or Spanish: the lints recognise verbs, topic nouns, vague words and
number formats in both languages. Write the whole deck in the user's language.

Use when the user wants a presentation, deck, slides, board pack, SteerCo pack, memo-as-slides,
or wants to "turn this into slides", in any language. Also to review/QA an existing deck spec.

Do not use for: decorative / inspirational slides with no argument, pure design work on a
corporate template you must reproduce pixel-exact, or when the user wants a Word/HTML report.

Priorities when they conflict: **clarity > visual sophistication · a sharper message > more
information · communicate > decorate.** Never sacrifice legibility to fit content.

---

## 1. Understand the input (Step 1)

1. If there are files: `scripts/cpe ingest <files…> -o work/inventory.json`
   → `inventory.md` lists headings, tables and **facts** (numbers with their sentence and location).
   Every number you later put in a headline must be traceable to a fact or table.
2. Answer in writing (keep it in the spec `storyline` fields):
   - **Audience** and **decision sought** (what should they do/approve after the deck?).
   - **Governing thought**: the one-sentence answer. If you cannot write it, you are not ready.
3. Triage the material into message units (3–7 per section). For each: what type of claim is it?
   (see §5 message types). Prose without numbers → argument structures, **never invent numbers**.
   Fewer than 3 data points → KPI/statement, and flag the gap. Missing data → say so in the deck
   (footnote "assumption") rather than fabricate.

## 2. Build the storyline (Step 2)

Pick the framework that fits the audience's question:

| Framework | Key line | Use for |
|---|---|---|
| `SCR` | Situation → Complication → Resolution | recommendations, board, updates (default) |
| `CII` | Context → Insight → Implication | research read-outs, market analysis |
| `PDS` | Problem → Drivers → Solution | performance problems, financial analysis, sales |
| `DRI` | Diagnosis → Recommendation → Impact | transformation, operating model |
| `MPO` | Market → Position → Opportunity | strategy, growth, product strategy |
| `CGT` | Current state → Gap → Target state | capability, roadmap, operating model |
| `HEC` | Hypothesis → Evidence → Conclusion | investment memos, due diligence |

`scripts/cpe scaffold --deck-type <type> --title "…" -o deck.json` creates a skeleton with the
default framework and slide archetypes for the 14 deck types (`strategy_deck`, `business_review`,
`investment_memo`, `board_presentation`, `market_analysis`, `commercial_due_diligence`,
`transformation_program`, `operating_model`, `product_strategy`, `financial_analysis`,
`sales_strategy`, `implementation_roadmap`, `executive_update`, `project_steering_committee`).
The skeleton is a **hypothesis**: delete, merge and reorder archetypes to serve the argument.

Rules (checked by `lint`):
- Answer first: executive summary is slide 2–3 and covers every key-line point.
- 2–5 key-line points, same logical type, MECE. Every point has ≥1 supporting slide; every
  content slide has a `section` pointing to its key-line point; sections are not interleaved.
- **Horizontal logic:** `scripts/cpe outline deck.json` prints the ghost deck (headlines only).
  Read it aloud. It must tell the whole story without the charts. Fix the storyline here,
  before any visual work.
- Decision decks end on the ask (recommendation / decisions / next steps).

## 3. Write the slide intents (Step 3)

No slide is rendered without its intent. Content slide fields:

```json
{
  "id": "s06", "section": "K2", "tracker": "Profitability",
  "purpose": "Explain what drove the EBITDA decline",
  "proposition": {"statement": "Margin erosion in grocery and convenience (€119M) pushed EBITDA down from €924M to €857M",
                  "role": "driver", "claim_type": "driver", "subject": "EBITDA", "direction": "down",
                  "magnitude": "€119M", "timeframe": "2025", "evidence_ids": ["E06-1"], "confidence": "high"},
  "headline": "Margin erosion in grocery and convenience (€119M) pushed EBITDA down to €857M",
  "headline_candidates": ["optional alternative wordings: the engine picks the strongest faithful one"],
  "supporting_message": "Volume and price gains were not enough to offset cost inflation",
  "message_type": "change_bridge",
  "evidence": [{"id": "E06-1", "claim": "EBITDA 2024 €924M to 2025 €857M", "values": [924, 857], "source": "mgmt accounts"}],
  "visual": {"type": "waterfall", "title": "EBITDA bridge 2024 to 2025", "unit": "€M", "data": {…}},
  "commentary": {"title": "Two categories explain the decline", "points": ["**Grocery (−€78M):** …"]},
  "takeaway": "optional so-what bar at the bottom",
  "layout": "auto",
  "source": "Alvora management accounts",
  "footnotes": ["optional"],
  "notes": "optional speaker notes"
}
```

Other slide kinds: `cover`, `agenda` (`items`), `divider` (`number`, `title`), `exec_summary`
(`visual: {type: statements, data: {items: [{title, text}], style: numbered|scr}}`), `statement`
(`text`, `support`), `closing`. Slide-level `kpis`, `columns` (comparison columns) and `commentary`
are roles the layout engine places for you. Full reference: `docs/SPEC_REFERENCE.md`.

**v3.1 — purpose, proposition, headline are three different things.** Write the `proposition` (what the
slide asserts, its role and claim type, the evidence ids that prove it, how sure you are) before the
headline; the headline is its compressed wording. New decks are `meta.editorial_mode: "mbb_strict"`:
a content slide without a proposition, a topic title, an unsupported number or causal word, or a broken
sibling group FAILS the deck (docs/EDITORIAL_LAYER.md). `scripts/cpe editorial check deck.json` before
rendering; `scripts/cpe editorial explain deck.json` shows why a title was rejected and what was expected.

## 4. Headlines (Step 4)

The headline is the conclusion an executive keeps after 5 seconds. Pattern:
**subject + verb + quantified so-what** (≤ ~18 words, ≤ 2 lines, sentence case, no full stop).

| ✗ Topic (rejected) | ✓ Conclusion |
|---|---|
| Revenue evolution | Revenue growth slowed to 3% as acquisition weakened in H2 |
| Customer segmentation | Three customer segments generate 72% of contribution margin |
| Market analysis | Spain represents the largest untapped expansion opportunity |

The lint rejects topic labels, flags two claims joined by "and", vague intensifiers without
numbers, and **any number in the headline that the slide's evidence/exhibit cannot produce**
(values, sums, shares, deltas, growth rates, CAGRs are derived automatically; the executive
summary may quote any number proven elsewhere in the deck). If the number is right, add the
evidence; if it is not, fix the number.

v3.1: the Action Title Engine then checks the headline against the proposition (docs/HEADLINE_STYLE.md):
no change of direction, magnitude, entity, scope, period, confidence or causal strength; a finding is
not a recommendation and a recommendation is not a decision; numbers at the precision of the evidence;
causal words only on causal/driver claims. If it rejects every candidate the slide fails closed
(`HEADLINE_UNRESOLVED`, with the expected proposition): write a new candidate, do not weaken the claim's
evidence. Siblings — recommendations, process steps, options, workstreams, executive-summary statements,
key-line points — must share one grammatical family (docs/PARALLEL_WORDING.md).

## 5. Choose the visual by the message (Step 5)

First name the message type, then the visual. `visual.type: "auto"` lets the engine decide
(with the rationale recorded in `resolved.json`); `scripts/cpe recommend <message_type>` shows
the ranking. Explicit choices are critiqued and, when safe, auto-corrected.

| message_type | Say… | Default visual (alternatives) |
|---|---|---|
| `single_number` | "X is €13.6bn" | `kpi` (statement) |
| `ranking` | "A is bigger than B" | sorted `bar` (column ≤7 short labels, table) |
| `composition` | "X is n% of the whole" | `bar` / `stacked_bar` (donut ≤5 parts, pie 2–4) |
| `composition_change` | "the mix shifts" | `stacked_column`, `stacked_100`, area |
| `trend` | "X rises/falls" | `column` (few periods) / `line` (many, several series), `combo` (level + rate), `slope` |
| `change_bridge` | "what explains the change" | `waterfall`, `bridge` (with subtotals) |
| `distribution` | "most cases fall in…" | `histogram` |
| `correlation` | "X moves with Y" | `scatter`, `bubble` |
| `positioning` | "where items sit on two dimensions" | `matrix_2x2`, `portfolio` (sized) |
| `comparison` | options × criteria | `harvey_table`, `table`, `heatmap`, `text_columns` |
| `segmentation` | segment size × share | `mekko`, `stacked_100`, `heatmap` |
| `sequence` | steps in order | `process`, `value_chain`, `flow` |
| `plan` | what happens when | `gantt`/`roadmap`, `timeline` |
| `hierarchy` | decomposition / drivers / org | `driver_tree`, `tree`, `org_chart`, `pyramid` |
| `geography` | varies by place | `tile_map` (only if geography is the message; else ranked `bar`) |
| `flow` | where volume is lost / journey | `funnel`, `journey`, `flow` |
| `structure` | how the system is built | `operating_model`, `layers`, `architecture` |
| `status` | where things stand | `scorecard` (RAG), table, gantt |
| `argument` / `recommendation` | reasons / what to do | `statements`, `text_columns`, `bullets`, decision `table` |

Exhibit rules the engine applies for you: no gridlines, no legend when direct labels are
possible, one focus colour (`highlight: [...]`), rounded scales, category sorting for rankings,
compact number formats (`format: {decimals, prefix, suffix, percent, plus}`), units in the
exhibit title (`title` + `unit`), truncated waterfall axes marked with breaks.
Use `annotations`: `cagr` {from, to}, `reference` {value, label}, `callout` {at, text},
`forecast` {from}. Data shapes per visual: `docs/VISUAL_GUIDE.md`.

## 6. Layout and composition (Step 6)

Composition (v1.2): `cpe run` does not just take the first compatible layout. For each content
slide it renders the compatible layouts × composition variants (content scale on sparse slides,
table rows stretched to the zone, alternative corporate layouts), drops candidates with QA errors,
and scores the rest by **fitness to the slide's archetype** — what the slide is (statement, KPI
hero, table, roadmap…), derived from its content. A statement may breathe; a table must not float
in half an empty slide. A different layout must win clearly, for deck consistency.
`out/composition.md` lists every choice and every "technically compatible but inappropriate for
this content volume / archetype" alternative, with the deviations. Composition findings are
**editorial advice** in `qa_report.md` — they never fail the gate. When even the best composition
is weak (`COMPOSITION_DEAD_SPACE`, `COMPOSITION_UNDERUSED_CANVAS`), the fix is content, not
layout: add the proof, merge the slide, or turn it into the archetype it really is (a statement,
a KPI hero).

Leave `layout: "auto"`. The selector matches the slide's content roles (exhibit, commentary,
kpis, columns, statements, statement, takeaway) and visual family against 45 layouts in 16
families (`scripts/cpe catalog`, `docs/LAYOUT_CATALOG.md`), checks capacity with real text
metrics, and avoids repeating the previous slide's layout. Fix a layout only for a reason
(e.g. `exhibit_commentary_left` when the argument must be read before the chart,
`roadmap_phases` for phase columns). A fixed layout that does not fit becomes an author action.

### Corporate identity

If the user supplies a corporate template, run `scripts/cpe brand ingest template.pptx -o brands/<name>`
**before** building and read `brands/<name>/compatibility.md`. Tell the user, in one line each:
- masters and layouts found, and the layout families recognised (with low-confidence ones);
- the typography actually used vs the theme's declared fonts (any **conflict**), and every
  **FONT WARNING** (font not installed here → substitute and approximate line breaks);
- the colours inferred as brand colour and text colour, and their source (theme vs observed usage);
- canvas rescaling, unsupported elements.
Then set `"meta": {"brand": "brands/<name>"}`. Structural slides (cover, dividers, closing,
statements) are generated **natively** on the template's own layouts; content slides use a
corporate content layout with an engine-composed body (**adaptive**); otherwise the engine layout
with the corporate theme. `build_manifest.json` → `corporate` records the mode and the reason per
slide. QA protects the template's artwork (`BRAND_RESERVED_OVERLAP`) and checks contrast against
the layout's real background. Never claim the deck is "on brand" when the report shows conflicts
or missing fonts: say what was approximated.

## 7. Density (Step 7)

Budgets come from the deck type's profile (`board` < `standard` < `analytical`; `status` for
SteerCos): words per slide, bullets per zone, words per bullet, table rows/cols, chart
categories/series, shapes. The engine never truncates your words. Order of remedies:
1. cut words (keep only what proves the headline); 2. move detail to notes/backup;
3. change layout / visual; 4. split into two slides, **each with its own headline**.
Tables over capacity are split mechanically as a fallback (flagged `AUTO_SPLIT`: replace with a
summary table — top rows + "Other" — whenever possible). Text shrinks towards role floors
(body 11 pt, tables 10 pt, charts 9–10 pt, sources 8 pt) and never below.

## 8. Build, render, inspect, patch (Steps 8–9) — the loop

```bash
scripts/cpe lint deck.json            # fix every error before building
scripts/cpe run deck.json -o out/     # compose → build → render → QA → autofix (≤3 iterations)
```

`out/` contains `deck.pptx`, `renders/slide-NN.png`, `contact_sheet.png`, `qa_report.md|json`,
`review.md` + `review_template.json`, `ghost_deck.md`, `resolved.json`, `build_manifest.json`,
and `deck.autofixed.json` if the engine patched the spec.

**Layer 1 — automatic (deterministic).** Content (intent, storyline, headline, evidence, visual,
density), geometry (off-slide, margins, zone escape, text overflow by real metrics, text
collisions, connectors through text, font floors, font family, palette, WCAG contrast,
placeholders, headline lines/widows, near-miss alignment, shape count) and render (what
LibreOffice actually drew: text spilling out of boxes, rendered collisions, text in margins,
headline line count, tiny rendered text, empty/unbalanced slides). Codes: `docs/QA_CODES.md`.
The autofix only changes **form** (visual encoding with a concrete fix, layout alternatives,
table splits). Everything that needs rewording is listed under *Actions for the author*.

**Layer 1d — composition.** Every slide gets a composition score in
`qa_report.json → composition`; flags the engine could not fix become `COMPOSITION_*` warnings
with a remedy. The exhibit shows the headline's proof automatically when it can (change, CAGR,
last period, waterfall total, top-k share); `PROOF_NOT_VISIBLE` means you must label or
highlight it yourself.

**Layer 2 — your visual review (mandatory before delivery).** Open `contact_sheet.png` and every
`renders/slide-NN.png`. For each slide answer the 8 questions in `review.md` (0/1/2):
one idea? · understood in 5 seconds? · evident hierarchy? · no decoration without function? ·
does the exhibit prove the headline? · one focus only? · right layout? · would a partner send it?
Then the deck lenses: CEO (decision or description?), CFO (numbers reconcile across slides?),
partner (weakest claim?), visual editor (what does the eye see first?).
Write `out/review.json` (copy `review_template.json`), then `scripts/cpe review out/review.json`
(pass = every slide ≥13/16 and no 0).

**Patch.** Express every fix as a patch (never hand-edit the PPTX):
```json
[{"op": "set", "slide": "s07", "path": "headline", "value": "The erosion concentrates in fresh…"},
 {"op": "set", "slide": "s03", "path": "visual.highlight", "value": ["Discount", "Online"]},
 {"op": "delete", "slide": "s05", "path": "subheadline"},
 {"op": "insert_slide_after", "slide": "s06", "value": {…}}, {"op": "remove_slide", "slide": "s09"}]
```
`scripts/cpe patch deck.json patches.json` then `scripts/cpe run` again. Iterate until
**stop criteria**: `qa_report.json.passed == true`, review passed, no pending author action you
can resolve, ghost deck reads as one argument. If the same blocking issue survives two rounds,
go back to the storyline (the slide is probably trying to say two things).

## 9. Deliver (Step 10)

Deliver `deck.pptx` (native: text is text, charts are data-editable, tables are tables, diagrams
are shapes; speaker notes carry purpose/supporting message) plus the contact sheet and a 3-line
summary: governing thought, number of slides, QA verdict/score and anything the user must verify
(assumptions, illustrative data). Never claim QA passed unless `qa_report.json` says so.

---

## Anti-patterns (the "AI slide look") — never do this

- Topic titles; headlines that are questions; two messages in one headline.
- Cards everywhere, rounded boxes, shadows, gradients, decorative icons, emoji, stock imagery.
- More than one accent colour on a slide; colour without meaning; rainbow series.
- Walls of text; >5 bullets; bullets that restate the chart; tiny fonts to make it fit.
- Symmetric grids of identical boxes when the content is not parallel.
- The same layout on every slide; decorative "infographics" (circles, hexagons, puzzles).
- Charts without units/sources; 3D; dual axes (use `combo`, which stacks two aligned panels);
  pies with >5 slices; unsorted rankings; legends when direct labels fit.
- Invented numbers, invented sources, placeholder text left in the deck.

## Deck-type adaptation

| Deck type | Profile | Notes |
|---|---|---|
| board_presentation, executive_update | `board` | fewer words, larger type, one exhibit per slide, end on the decision |
| investment_memo, commercial_due_diligence, financial_analysis, market_analysis | `analytical` | denser exhibits allowed (tables ≤14 rows), footnote assumptions, HEC/CII storylines |
| project_steering_committee, implementation_roadmap, transformation_program | `status` | scorecards (RAG), gantt with today line, decisions required slide |
| strategy_deck, business_review, operating_model, product_strategy, sales_strategy | `standard` | balanced |

Themes: `meridian` (navy + teal, default), `graphite` (charcoal + green, finance/PE),
`harbor` (blue + amber, programmes). Set `meta.theme`. Override profile with `meta.profile`.

## Changing the engine itself

Use the pinned environment: `scripts/cpe-docker eval --suite regression` before and after any
change to renderers, layouts, tokens, QA or composition. It fails on crashes, new QA errors,
composition drops or new flags against `evals/regression/baseline.json`. Improve the engine, not the
baseline; update it (`--update-baseline --record`) only for an intended change, and say so in the
commit. Three rules keep the evaluation honest (docs/EVALS.md):
- the **regression** suite is the development set — tune on it;
- the **holdout** (`evals/holdout/public`, `.private/holdouts`) is run only with the rules frozen,
  reported, never tuned on in the same cycle, never baselined;
- **human preference** (`cpe human`) is an independent signal, never part of the score.
Never hand-edit numbers in the README: `cpe results readme` generates them from
`evals/results/latest.json`.

## Troubleshooting

- `RENDER_UNAVAILABLE` / "source file could not be loaded" → install `libreoffice-impress`;
  QA still runs geometry checks without rendering (`--no-render`).
- `HEADLINE_NUMBER_UNSUPPORTED` → add `evidence[].value(s)` or correct the headline.
- `CONTENT_OVER_CAPACITY` with `excess_words` → cut that many words; or split the slide.
- `LAYOUT_NONE` → the combination of roles is not supported by any layout: move commentary
  into `takeaway`, or split into two slides (see `scripts/cpe catalog`).
- More in `README.md#troubleshooting`.
