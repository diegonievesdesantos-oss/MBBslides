# Changelog

## Unreleased — 2.2.0.dev0

Fewer numbers left for a person to trace by hand. Status: [docs/V22_STATUS.md](docs/V22_STATUS.md).

- **One figure, one value across the deck (item 2).** The same figure restated on several slides (the
  plan table's 3.200 k€, the summary's "3,2 M€", the recommendation's "fase 1 por 3,2 M€") is now one
  group that follows one value.
  - A number joins a group when it has the same value at some scale, the same kind (level, share or
    multiple), the same phase / zone / option and the same measure. A number with no measure of its own
    joins only as a distinctive figure (2+ significant digits) next to one that has a measure.
  - The group's head is, in order: a figure the deck's own arithmetic derives; one an analysis output
    gives; a table cell; any direct match.
  - Approving one member moves the others. A member whose own match said something else keeps it as an
    alternative, shown in `review.xlsx`, `edits.md` and the update report.
  - In-sample on the v1.8 project: outdated numbers found 41/68 → 51/68, proposed values right 17/25 →
    24/31, no loss on current (11/11) or outdated precision (51/54).
- **Projections and curves from their drivers (item 3).** Three new derivations:
  - **Growth.** A chart series whose last 3+ points grow at a rate the slide states ("Demanda
    prevista (+6%/año)", "crecimiento del 6% anual") is a projection: each point = the previous one ×
    (1 + rate). It follows a new rate or base, and a point with its own new value (an actual, a new
    forecast) keeps it.
  - **Payback curve.** A cumulative cash curve whose 3+ last points are exactly −investment + n ×
    annual savings, both figures of the deck, follows them.
  - **Flows in the sources.** A cumulative curve the deck cannot recompute is the running sum of
    the yearly flows a source gives, when one source covers every year of the curve. The analysis
    comes first, then any source that is not the old plan; two different equally ranked sources give
    no proposal.
  - A point of a cumulative series is no longer matched to a single year's flow.
  - In-sample on the v1.8 project: outdated numbers found 51/68 → 54/68 (its demand projection). Its
    cash curve still cannot be recomputed: no source gives yearly flows, and the old curve does not
    follow the simple payback model exactly.
- Two edits of the same figure in one paragraph no longer collide: later occurrences are patched first.

## 2.1.0 — Less review work: ranked conflicts, a review sheet, more headline claims

**Closed 2026-10-02 by the owner, without the blind validation on real material, which moves to v2.2:**
- unseen corporate templates;
- new cases with the owner's key.

There is no new blind figure in this release. The Albor figures are in-sample, and the sealed
holdout of v2.0 was already used.

Less review work for a person. Status: [docs/V21_STATUS.md](docs/V21_STATUS.md).

- **Conflicts ranked by what separates real ones from noise (item 2).** Each conflict gets a priority:
  - **high:** the deck uses one of the figures, or 3–5 sources give the quantity 3–5 ways;
  - **low:** one side is the analyst's own analysis output, or a long chain;
  - **medium:** the rest.

  Over the 7 cases with keys, 8/10 high flags are real conflicts, against 19/50 medium and 5/30 low.
  - The rule comes from the development cases. Ranking by magnitude did not separate.
  - `cpe reason conflicts WORK [--dismiss ID --why … | --resolve ID --use FACT]` lists and records
    decisions.
  - `reason facts` now re-detects with the current sources and keeps every resolution and dismissal.
    A group that gained a version keeps its review, and a reviewed conflict no longer detected stays,
    marked `stale`.
- **More headline claims (item 4):**
  - superlatives ("la fase 2 es la más rentable", checked on the measure row of the slide's table);
  - signs ("ahorra" with a value now negative);
  - orders ("A supera B");
  - the payback year against the slide's cumulative curve.

  Each is read only if it held with the old values, and a superlative or payback year gets a
  substituted proposal.
- **Cumulative series (item 5).** A curve whose flows the slide shows is recomputed point by point from
  approved flows. One whose flows are not shown is marked "not recomputable from the deck", with the
  reason, instead of a silent "untraced".
- **The review as a spreadsheet (item 3).** `cpe update` also writes `work/review.xlsx` with four
  sheets:
  - **Changes:** approve or correct each number, or give a value to one left for review.
  - **Headlines:** approve the proposal or write your own.
  - **Conflicts:** use a fact or dismiss, with a reason.
  - **Slides:** keep, delete or rebuild.

  `--read-sheet` reads it back, and `--apply` reads it on its own when it is newer than `edits.json`.
  Typos, approvals without a value and dismissals without a reason are reported, never applied.
  Labels are in the deck's language (Spanish or English).

## 2.0.0 — Update an existing deck end to end; versions of a quantity across sources

**Closed 2026-10-02 by the owner, without the blind validation on real material, which moves to v2.1:**
- unseen corporate templates;
- new cases with the owner's key.

The only blind figure of this release is on a synthetic holdout written by an agent (item 4). The
v1.8 project figures are in-sample.

The aim of 2.0 is a tool that works on cases it has not seen. The release needs the owner's blind
validation (unseen templates and new cases, judged only against the owner's key). Status:
[docs/V20_STATUS.md](docs/V20_STATUS.md).

- **`cpe update`: one command to update an existing deck.**
  - `cpe update old.pptx sources/ -o work` ingests the deck, builds the facts (with any recorded
    analyses), writes the plan and proposes edits.
  - Re-running keeps the review.
  - `cpe update --apply work -o new.pptx [--mark] [--accept-derived]` patches the original file.
  - `update_report.md` lists:
    - headlines whose own figures changed (check the message still holds);
    - every number left unchanged for review.
- **Derived figures.** Totals, net rows, ratios such as payback, sums stated in a sentence and the same
  figure repeated elsewhere are found in the old deck's own arithmetic (`derive.py`). They are
  recomputed from the new values of their parts:
  - first in the plan;
  - then, more importantly, from the reviewer's approved values (`cpe deck edits --derive`).

  A derived proposal whose parts are not all approved is marked provisional, and `--accept-derived`
  never applies it.
- **Versions of one quantity across sources (item 4).** A quantity given with different values in
  different files (scope, basis, cut-off, restatement, competing estimates) is reported as one conflict
  with all its versions.
  - Facts now carry their paragraph and section heading, so an implicit subject is read.
  - `scripts/score_conflicts.py` scores the conflicts against a key.
  - **Sealed synthetic holdout** (3 cases by an agent, keys never read, run once):
    - 7/14 groups found (previous engine: 0/14);
    - 7/20 flags are planted conflicts;
    - 0 decoys flagged.
- **Slides whose message no longer holds (item 5):**
  - `work/messages.md` gives each slide a verdict: holds, figures updated, no longer holds, or check.
  - A threshold claim in a headline must hold with the old values and is re-read with the new ones.
  - A headline that no longer holds gets a mechanical `set_headline` proposal, unapproved.
  - `cpe update --rebuild` builds the flagged slides in the old deck's own style. On `--apply`, a
    `replace_slide` edit transplants each one into the original, on the old slide's layout.
  - On the v1.8 project:
    - slide 6 "se pagan en menos de 5 años" is caught (payback now 9,2 / 5,8);
    - the rebuilt slide passed QA (92, 0 errors) and sits in the original deck.
- **`deck stale`:**
  - durations ("se recupera en 3,7 años") are read as figures;
  - horizons and criteria ("TIR a 10 años", "en menos de 5 años") are ignored;
  - a KPI label may contain numbers.
- **Measured on the v1.8 project (owner's key, in-sample):**
  - outdated numbers found: 41/68 (1.9.0: 33/66);
  - outdated status correct: 41/44;
  - proposed value right: 17/25.
  - After the reviewer approves the parts, totals, KPIs and payback follow: 6.646 k€ capex,
    payback 9,2 / 5,8 years by phase.

## 1.9.0 — Tool debts, in-place deck update, layouts learned from slides

**Closed 2026-10-02 by the owner, without blocks B and C, which move to v2.0:**
- **B:** unseen corporate templates;
- **C:** blind cases for protocol 1.5, judged only against the owner's key.

All figures below are in-sample, on the v1.8 project.

Status and what needs the owner: [docs/V19_STATUS.md](docs/V19_STATUS.md).

The figures are measured on the v1.8 real project against the owner's key. That case is development
data, so the figures are in-sample.

- **Block A: tool debts U1–U9 from v1.8** ([docs/DEBT_V18.md](docs/DEBT_V18.md)):
  - **`deck stale` (U1)** matches each old number on its own words (measure, phase, zone, year) and unit,
    never on its value alone.
    - Page numbers, document codes, phase indices and specifications are `ignored`.
    - Restatements of the old plan never confirm a number.
    - Analysis outputs and the latest aggregate come first.
    - On the owner's key: asserted statuses 61/64 correct; proposed new value 15/23 (v1.8: 1/7).
  - **Conflicts (U3):** prose numbers are read with their own words and compared with period-less tables;
    tables are compared with each other; ratios are compared. Different phases, years, zones and
    opposite qualifiers are never paired. On the case: 3 conflicts, all real, 0 false.
  - **Messy tables (U2):** a banner line above a header, a repeated two-level group label, and `n/d` cells.
  - **Periods and dates (U4, U5):** week references are periods, and render QA masks dates in headlines.
  - **Units (U6):** units come from the label's unit text, not from figures quoted in it.
  - **Factuality gate (U8):** statement texts are fact-checked.
  - **Scaled numbers (U9):** they ground against unscaled facts.
- **D2: layouts learned from slide geometry.** A deck built with free text boxes now yields real
  corporate layouts (cover, statement, content), and its slides count as usage evidence.
  - Footer artwork on a layout moves the engine's source line up instead of rejecting the layout.
  - Dated fixed text on a layout is flagged.
  - On the case: corporate share 0/12 → 12/12, render errors 16 → 0.
- **D1: update the original pptx in place.**
  - `cpe deck edits` proposes edits in the old number's notation, all unapproved.
  - `cpe deck patch` applies the approved ones to the original file. Run formatting, table cells and
    chart data are kept, and the change is noted on the slide.
  - `--mark` highlights the new text. An edit that cannot be found is reported, never moved.

## 1.8.0 — Real-world inputs, corporate use, any OS

**Closed 2026-10-02 by the owner, without the unseen-template validation, which moves to v1.9.**
- **Acceptance test:** one real messy project with its previous deck, updated end to end.
  - Owner's blind review: 14 of 14 numbers right, 9 of 11 traps found, "would present with changes".
  - The review led to protocol 1.5.
- **Tool findings U1-U9:** listed in docs/DEBT_V18.md for v1.9.

Status and what needs the owner: [docs/V18_STATUS.md](docs/V18_STATUS.md).
- **Messy inputs:**
  - period and basis semantics, with a `PERIOD_MISMATCH` warning;
  - typed conflicts (management vs audited, forecast vs actual, definition, value, prose);
  - two-level headers, scenario columns, total rows;
  - chart data read from docx / xlsx / pptx.
- **Existing decks:** `cpe deck ingest` and `cpe deck stale`. An old deck is read, rebuilt natively,
  and each of its numbers is checked against the new facts.
- **Cell-to-fact binding:** `"at"` on evidence items (hard), plus a label check on unbound cells
  (warning). This closes the DEBT F1 residual.
- **Visuals:**
  - `cause_effect` exhibit (message type `causality`);
  - `timeline_decisions` layout;
  - explicit n/a cells and chart points (`n/d` in Spanish).
- **Corporate:**
  - `corporate_usage.md` (native / adaptive / engine fallback per slide, with reasons);
  - `brand_fidelity.md` (separate metrics, never blended into the deck score);
  - `cpe brand fidelity`.
- **Portability:**
  - UTF-8 for every file read or written;
  - LibreOffice and font discovery on Windows and macOS;
  - Windows wrappers;
  - `docs/INSTALL.md`;
  - a `Portability` CI workflow (Windows, macOS, Linux × Python 3.10 / 3.12).
- Fix: a chart series with a gap (`None`) no longer crashes visual reasoning.
- **Reasoning protocol 1.5**, adopted by the owner after their blind review of the real-project update.
  It adds five rules, each checked as a warning or info:
  - contingency (`CONTINGENCY_MISSING`);
  - renegotiate and defer options, with gates that have margin and a sustained test (`OPTION_RENEGOTIATE_MISSING`, `OPTION_DEFER_MISSING`, `GATE_NO_MARGIN`, `GATE_SHORT_TEST`);
  - discarded evidence stays discarded (`DISCARDED_EVIDENCE_REUSED`);
  - coherent figures (`ASSUMPTION_IN_SUMMARY`, `REJECTED_HYPOTHESIS_REVIVED`);
  - partner-review checklist (`PARTNER_CHECKLIST`).

  Computed facts may declare `rests_on_assumptions`.

## 1.7.1 — Fine-tuning of the v1.7 debt

Fine-tuning of docs/DEBT_V17.md, with no new agent runs. The stored decks are the regression set: all
pass, and the real Brasa deck re-renders at 98.1.
- **Factuality:**
  - table and chart values must be cited fact values, in any scale (F1, F7);
  - prose-vs-prose money conflicts are detected (F2);
  - numbers in table text cells are extracted (F3);
  - `_k` / `_m` header units (F4);
  - `to()` converts units in formulas (F5).
- **Locale and render:**
  - Spanish and other decimal-comma number formats everywhere, including native chart labels (L1);
  - a highlighted loss uses the negative colour (L2);
  - header alignment (L3);
  - the governing-thought word count (L4);
  - a KPI + commentary layout, KPI strip + process, and process steps accept `label` (L5);
  - km and m² units (L7).
- **Moved to v1.8:** new exhibits (cause → effect, decisions + timeline) and cell-to-fact binding.

## 1.7.0 — Consulting intelligence: from raw material to a decision deck

**Closed 2026-10-02.**
- **Reasoning protocol frozen at 1.4.** Traceability never costs the reader content; row-level data goes
  through recorded analysis scripts.
- **Acceptance test:** one real external case (private) taken from raw ERP data and documents to an
  8-slide Spanish board deck.
  - Reasoning check: 0 errors, 0 hard failures. Render QA: 0 errors; deck score 98.1.
  - The owner judged it "perfect".
- **Remaining findings:** in docs/DEBT_V17.md as the backlog for a last fine-tuning pass. The weak
  grounding on dense slides and locale number formatting come first.
- **Human rounds this cycle (expert, blind):**
  - s1 2–2;
  - s2 3–1 for protocol 1.1;
  - s3 1–0 for protocol 1.2 (external);
  - s4 1–4 against protocol 1.3 (5 external raw-data cases), which led to 1.4.

- **s4 (five external raw-data cases, private): the baseline was preferred 4–1.** Answers converged, but
  the protocol storylines lost concrete content, partly to get past checks.
- **Protocol 1.4: traceability never costs the reader content.**
  - Checks block invented quantities only. Dates, deadlines, periods, durations and small counts are
    never checked.
  - A rule forbids blurring a true statement to pass a check.
  - The brief goes into the sources.
  - A "write for the reader" pass.
  - The partner critic compares the storyline with a no-protocol document.

- **Five external cases from the owner (round s4, private, voting pending).**
  - Agents ran without the protocol and with protocol 1.3; all five protocol runs pass the reasoning check.
  - The tool problems they reported are fixed with tests:
    - the CSV sniffer gave up on wide files;
    - dates, periods and times were read as numbers ("22 de septiembre", "2/12/2025", "2025-26", file date ranges, "10:30");
    - "35-39" was read as a negative number;
    - "más" was read as a million;
    - "1.428.000" in prose;
    - "9,55x" ratios did not ground;
    - units written in cells ("1,6%", "140.000 €");
    - `_pct` and "porcentaje" headers;
    - "(inicio mes)" was taken for a unit;
    - negative lever impacts did not ground;
    - one arithmetic error cascaded into UNKNOWN_FACT;
    - Spanish estimate verbs and more Spanish verbs.

- **Protocol 1.3, row-level data:**
  - `cpe reason analyze work/ script.py --sources …` runs the agent's analysis script twice and records
    script, input and output hashes in `analysis.json`;
  - the output tables become citable facts with lineage;
  - tables longer than 150 rows are listed as datasets, not read cell by cell;
  - hard gates ANALYSIS_STALE and ANALYSIS_NOT_REPRODUCIBLE.

- **First external case (round s3, private).**
  - The owner supplied a corporate business case, kept under `.private/`; no content is in the repository.
  - Blind storyline A/B: protocol 1.2 preferred, 1/1, consistent on the side-swapped repeat.
  - The case is a single document → storyline, so this is a signal, not validation.
- **Extraction fixes it exposed (tested on synthetic text only):**
  - decimal-comma documents ("1,829" is 1.829, "75.846" is 75846);
  - markdown tables with bold, "≈", empty or label cells now keep their numeric columns;
  - "a → b" cells are split into two columns;
  - rate units ("Pedidos/semana") and period labels ("Año ant.", "Mes") are no longer units;
  - table locations point at the table's first line;
  - more hedging words clear ASSUMPTION_IN_HEADLINE.

- **Second end-to-end deck, in Spanish** (tiendas, protocol 1.2): reasoning PASS, QA 0 errors, deck 98.4.
- **Fixes:**
  - Spanish thousands before k€/M€ (a regression in the previous commit);
  - a localised source label ("Fuente:");
  - more Spanish verbs in the headline lint.

- **Protocol 1.2 rerun on case set 02 (development check):** every option is compared on the same cost
  components, and the s2 packaging error does not recur.
- **The agents reported these, now fixed:**
  - decimals read as thousands ("0,048", "€2.868M");
  - "7.8 EUR M" and "EUR 7.8M" now read as money;
  - "23–24%" ranges;
  - a bare number now matches a fact in its own unit;
  - `F0062[1]` selects a fact's second value in formulas;
  - rate units ("/año");
  - plan/proposal basis words, matched as whole words;
  - the conflicts file is validated instead of crashing;
  - SLIDE_MERGE ignores non-argument slides.

- **Decision-deck visuals (from the end-to-end deck's gaps):**
  - estimate and bound markers on waterfall steps (hollow, dashed, `~`/`≤`) and on table cells, which
    stay numbers;
  - a waterfall target line;
  - `delta_colors: "muted"` (grey but the highlight);
  - `proof_label: false`;
  - table widths documented (inches, fixed).
- `cpe reason check --enrich` keeps the agent's evidence wording (`fact_claim` holds the source text).
  Deck-plan headlines are linted with the deck type's word budget, as the render lint does.

- **Factuality gaps closed (from the end-to-end deck):**
  - Every number a reader sees on a slide must be grounded in the slide's cited facts: body, KPIs,
    table cells, chart data, takeaways. Before, only the headline was checked.
  - Fact ids are stable when facts are re-extracted (matched by source location; `facts_refresh.json`).
  - FACT_FABRICATED is checked against the raw source content, not a re-extraction.
  - WRONG_SOURCE follows computed-fact lineage.
  - Label cells such as "Q1 2024" are no longer read as numbers.
  - The new check found three real uncited numbers in stored decks; they are now cited.

- **s2 voted (expert, blind): protocol 1.1 wins 3–1** (almacén, SaaS, tiendas). The baseline won
  packaging; the owner corrected one repeat as a mis-click.
  - The expert praised decision-ready closes: approvable asks, owners, dated gates, fallbacks.
  - The one loss was options compared on different bases (risk charged to one option only). The case
    author's reference made the same error and is marked contested.
  - **Protocol 1.2 adds OPTIONS_DIFFERENT_BASIS** (`cost_components` per option).
  - The voting page now swaps the sides of a repeat relative to its original. Before, the swap was random.
- **Experiment 02 / round s2:** four harder development cases (set 02, written after
  protocol 1.1 was frozen); baseline agent vs agent with protocol 1.1.
  - Automatic yardstick: 3/3 conclusions for both systems in every case.
  - Untraced numbers: protocol 19, baseline 46.
  - The protocol agent passed the reasoning check in all four cases.
- **Fact-model fixes reported by the experiment 02 agents:**
  - a dot decimal in CSV and typed xlsx cells ("1.444" is 1.444, not 1,444);
  - prose in spreadsheet cells (a "Notes" sheet) is read as text facts;
  - snake_case unit headers ("opening_arr_eur_m");
  - year columns label rows and set their period;
  - units written after the number ("25 EUR M", "3,2 millones de euros", "250.000 euros").
- **Conflict detector:** no longer flags two rows or two columns of one table, a prose total of a
  row's parts, or the same figure with a different sign or rounding. On case x2_tiendas this
  removes 161 false positives; the real forecast-vs-actual conflict in margin_recovery is still found.

- **s1 voted (expert, blind storyline A/B): 2–2.** The protocol run won churn and margin; the run without
  the protocol won plant and promo. Written feedback mapped after unblinding
  (`evals/human_reference/rounds/s1/FEEDBACK.md`): the protocol run has numeric discipline and
  governance; the run without it thinks about the decision. s1 is now development data.
- **Reasoning protocol 1.1, decision frame** (`storyline.json["decision"]`, `cpe.reasoning.decision`):
  - target, quantified levers, identified total and gap, the current plan tested, costed options,
    approvable asks, gates and KPIs;
  - hard: lever arithmetic and lever-impact grounding;
  - warnings: gap not stated, unquantified lever, upper bound stated as certain, uncertainty without
    what to validate, current plan untested, options not compared, deferred close, no gates or KPIs,
    solution before problem;
  - the benchmark gains a `decision` dimension, and `eval-text` gains `decision_signals`.

- **Experiment 01 (docs/S2D_EXPERIMENT_01.md):** 4 development cases, independent agents without
  (A) and with (B) the reasoning protocol. Substance tie (3/3 conclusions, 0 traps each); B
  verifiable (every number a fact or a recomputed formula), fewer untraced numbers. Blind
  storyline round `s1` built for the expert rater. Two new cases with PDF and DOCX sources.
- Fact model: period per number ("38% in FY2025, up from 29% in FY2024"), comparison bases ("15%
  more than in 2025" is a 2026 figure), forecast words (prevista, expected, target), units in prose
  and headers (días, horas, minutos, meses), "12 M€"; Spanish thousands in headline numbers; "100
  EUR" is money. `cpe reason eval-text` scores any system's storyline.md (negation- and
  reported-speech-aware trap detection).

- **Evidence standard (owner decision):** one expert rater. r3 closed (blind v1.5 result preserved
  in `VALIDATION_v1.5.json`) and marked development data.
- **Waterfall scorer blind spot fixed:** new critical `integrity` metric — a broken slide (content
  off-slide, colliding or overflowing; a chart that cannot encode its data) cannot score well. On r3
  scorer–expert agreement 5/10 → 9/10 (waterfalls 7/7), no false positive on tied pairs; `cpe
  measure` uses the current checks. docs/WATERFALL_SCORER_STUDY.md. KPI-dashboard profile stays
  provisional (4–2 expert votes, 5 ties).

- `src/cpe/reasoning/` + `cpe reason facts | check | ghost | trace | eval`: structured fact model
  (cell ranges, periods with basis — actual / estimate / budget / forecast —, units, derived
  changes with lineage), business-question object, hypotheses, insights, storyline candidates,
  deck plan (slide architecture), computed facts (formulas recomputed) and explicit assumptions.
- Hard factuality gates: fabricated fact, unsupported number (insight, governing thought, plan or
  deck headline), wrong source attribution, arithmetic error, claim resting on a rejected hypothesis.
- Evidence graph and `trace`: any sentence → insight → facts → source cells.
- Source-to-deck benchmark (`evals/source_to_deck/{development,sealed,external}`), dimensions
  reported separately; one development case (margin recovery) with traps; one development run by
  the developing agent (not evidence). docs/REASONING_PROTOCOL.md (protocol 1.0: 12 passes, 5
  critic roles, stopping criteria), docs/SOURCE_TO_DECK.md.
- Conflicting sources: `fact_conflicts.json` (forecast vs actual, value mismatch for one measure
  and period); an unresolved conflict touching a used fact is an error. Critic findings
  (`critique.json`, five roles); an unresolved high-severity finding stops the loop. Both are
  stopping criteria. Hedged headline numbers ("about 1.1 pp") that rest on assumptions are info,
  unhedged ones a warning.
- Blind A/B of reasoning before rendering: `cpe human build-text` (storylines or deck outlines,
  with business-question context), same private key and voting packages.
- Second development case (`churn_es`: Spanish, multi-sheet Excel, M€, decimal commas) — no run
  yet; it found two fact-model bugs, fixed: a unit in one column spread to the whole table;
  "30.000" was read as 30.
- The margin-recovery development run went through a real critic loop: RED TEAM found that the
  governing thought claimed the full 1.5 pp target from two levers that size to about 1.1 pp; the
  storyline was revised (RUN.json records the iterations). Still the developing agent's own run.
- Ingest: numbers in prose are read whole ("2026" was split into "202" + "6"); Spanish thousands.
  Headline lint verb lexicon: recover, sell, combine, serve, handle.

## 1.6.0rc1 — External validation infrastructure (awaiting external input)

v1.6 answers *does the existing engine generalise?* It adds almost no rendering functionality on
purpose. **No v1.6 validation claim exists yet**: the three inputs that would make one (raters 2–4
on r3, an externally authored holdout, an unseen corporate template) must come from outside.
The engine is frozen on the `release/v1.6.0rc1` branch for those runs; v1.7 development continues on `main`.

- **Human, multi-rater.** `cpe human package` builds a self-contained voting package (bundle +
  stdlib-only server + Windows launcher + instructions, never a key) — r3's key is in the
  repository, so new raters vote from the package, not the repo. `cpe human import` takes the
  returned `votes/<id>.jsonl` (idempotent). Reports separate WITHIN-rater self-consistency from
  BETWEEN-rater agreement. New rounds: `--identical-controls K` (same image twice; tie rate =
  evaluator noise, reported per rater, never used to drop anyone). r3 reopened for raters 2–4,
  pairs unchanged (docs/HUMAN_EVALUATORS.md).
- **External holdout.** `.private/holdouts/external/` with attested provenance;
  `cpe holdout external-seal` (hashes, never rewritten) and `external-run` (refuses unsealed or
  edited decks, a dirty engine, and a second run per engine version). Author brief for the
  external author (docs/EXTERNAL_AUTHOR_BRIEF.md).
- **Unseen corporate templates.** `.private/holdouts/corporate_unseen/<name>/template.pptx`, any
  number; known development templates refused by hash; run once per engine version.
- **Derived proof across exhibits** (development): a headline figure may combine two explicit
  single quantities of two different exhibits (KPI value, table total row, waterfall start/end,
  one-value series) with one operation (sum, difference, share, ratio); never more than 10
  candidates, ambiguity → unproven; lineage recorded.
- **Not done, by rule:** KPI-dashboard profile and the waterfall scorer blind spot wait for r3's
  additional raters (r3 is not development data yet); absolute gates stay provisional until the
  external-holdout distribution exists (docs/EVALS.md, "v1.6 status").

## 1.5.0rc1 — Human alignment, real failure modes, independent evidence pending

A deliberately small release. It ends as a **release candidate awaiting external validation**: the
independent evidence that could confirm it (an externally authored holdout, an unseen corporate
template, human round r3) can only come from someone else. Nothing below is independent evidence
for v1.5 (docs/EVALS.md, first table).

### Governance
- Round r2's blind result is preserved as the **single-rater blind validation of v1.4.0**
  (`rounds/r2/VALIDATION_v1.4.json`: 35/1/2, 97.2% [85.8–99.5], scorer agreement 33/34; a test
  recomputes it from the hashed votes). r2 was then marked **development data** (`mark-used`).
- Profiles: process and comparison `utilization`/`empty` → `human_supported_single_rater` (8/8 and
  7/7 decisive votes, one rater). kpi_dashboard stays `provisional`, range unchanged. Absolute
  gates (mean ≥ 70, ≤ 25% below floor) stay provisional. `evals/profile_changes.md`.

### KPI dashboards (docs/KPI_DASHBOARD_DIAGNOSIS.md)
- r2's largest disagreement (p034, −26.2) was the **metric**: separators extended the "used" area;
  light card panels were invisible. New occupancy measurement (`qa/composition.py:_occupancy`):
  panels count as occupied, isolated thin lines do not. r2 re-measured (development data): 35/35.
- Engine: cards arranged by measured width (one row up to 4, 5 when legible, else rows of 3,
  centred short last row), height from content, every text colour made legible against the card
  fill (the holdout's 2.8:1 delta). Development KPI dashboards 77.5 → 98.6.

### Derived-number proof (qa/proof.py)
- Deterministic, unit-aware arithmetic lineage: sum, sum of the 2/3 largest, difference, ratio,
  percent change, percentage-point change, part ÷ total, waterfall increases / decreases / net
  change. €/$/£, k/M/bn, %, pp, bps, ×; never across currencies or kinds. Tolerance = the headline's
  written precision + 0.5%. No subset search; plain integers < 10 never derived; different kinds of
  derivation matching one figure → "ambiguous", not proven. Machine-readable provenance per figure.
  The direct match now honours the headline's rounding.

### Render fixes (minimised repros in `evals/regression/cases/11_render_edges.json`)
- **Waterfall**: running totals and totals below zero / crossing zero (were drawn off-slide, labels
  at y = 18–66 in). Every bar is a span; positive and negative parts stack from zero; labels above
  positive bars and under negative totals, clamped inside the plot frame; zero line on the axis.
  `WATERFALL_NEGATIVE` is no longer emitted.
- **Statement**: fallback ladder — measure with a renderer margin → 30/28/26/24/22 pt (22 = floor)
  → optical placement → if it still does not read as a statement, set as body text with a
  `STATEMENT_TOO_LONG` warning. Never clipped.
- **QA measurement**: rendered spans are measured on visible glyphs; a trailing space's advance at
  a line break was reported as `RENDER_TEXT_SPILL`.

### QA semantics, reporting, provenance
- `visual_qa_passed`, `authoring_qa_passed`, `benchmark_passed` reported separately; lint-stress
  cases declare `eval.lint_stress`. Slides authored / resolved / measured reported apart.
- Benchmark specs made editorially valid: the archetype battery is a declared slide
  **collection** (no executive-summary rule; every other storyline rule applies), its 11 real topic
  headlines were rewritten as claims, and the headline lint's verb lexicon gained common verbs it
  missed ("rate", "beat", "bajó", "tiene", "cubre", …). Lint coverage is unchanged
  ("Lessons from the pilot" is still a topic).
- Provenance names `evaluated_source_commit`/`evaluated_source_dirty` and
  `working_tree_commit`/`working_tree_dirty`; result files never make the evaluated source "dirty".

### Human evaluation
- Private-key architecture for new rounds: key in `.private/human_reference/keys/<round>/`,
  SHA-256 commitment in the bundle, `cpe human report --key`, `cpe human close`; test that the
  bundle reveals no version, role, layout, score or mapping. r1/r2 history untouched.
- Per-rater and pooled statistics; a rater voting twice counts once. Windows: UTF-8 everywhere,
  `votes/` created on demand (the "Vote not saved" bug of the first r2 session).

### Robustness
- Median / P90 / P95 / max drop, meaningful (≥ 5) and large (≥ 10) drop rates, new-visual-error,
  font-drop, layout-change and layout-change-with-drop, new-flag rates — global, per perturbation,
  per archetype. Enforced: no new visual QA error, no catastrophic variant, no coverage loss.
  Provisional relative gates for P90, large drops, font drops, layout instability.

### Human round r3 (voted after the freeze; single rater)
- 38 blind pairs + 4 repeats, v1.4.0 vs v1.5.0rc1, one evaluator: v1.5 preferred 9, v1.4 1,
  **28 ties** (decisive preference 0.90, 95% CI 0.60–0.98; ties-as-half 0.61); 4/4 repeats
  consistent; left share 0.50. Waterfalls 7–0 (5 ties); KPI dashboards 2–1 (4 ties); long
  statements 19 ties — the statement change is not visible to this rater. Fresh content 8–0;
  holdout-v2 content (development-known) 1–1. Scorer agrees on 5 of 6 decisive pairs; Kendall
  τ-b 0.37 [−0.22, 0.83] (directional only). Not used for calibration.

### Intake (awaiting input)
- `cpe holdout intake | v15-external | v15-corporate` and docs/EXTERNAL_HOLDOUT_PROTOCOL.md.
  External decks need attested outside authorship; a known development template (JET) is refused.

## 1.4.0 — Generalisation and visual intelligence

Engine frozen at `430176d`; every number below was evaluated on that clean commit
(`evals/results/latest.json`, `provenance.evaluated_commit`).

### Evaluation
- **Quality profile** in every eval (`quality.py`): macro-archetype score, weakest archetype,
  P10/P25/median/P75/P90, shares ≥ 90/80/70, per-archetype n/mean/median/min/P10/flags, coverage
  (insufficient < 5, provisional < 8, gate-eligible ≥ 8), health, and `archetype_diagnostics.md` +
  contact sheets per weak archetype. The overall mean is kept for continuity, no longer the headline.
- **Absolute archetype gates** (`evals/archetype_gates.json`) on top of the relative baseline:
  catastrophic minimum 35 enforced; mean floor 70 and ≤ 25% of slides below it provisional
  (reported until human evidence exists); coverage regression fails CI. v1.3.3 would have failed
  the enforced gate (text slide at 20.5) while passing its relative baseline.
- **Penalty attribution**: every score explains itself per metric (expected, observed, fitness,
  weight, points lost); penalties sum to 100 − score.
- **Archetype battery**: 17 decks / 154 slides (`scripts/make_archetype_battery.py`), every archetype
  gate-eligible. Regression: 27 decks, 194 slides.
- **Robustness** (`cpe robustness`, CI job): 8 metamorphic perturbations × 22 development seeds;
  median / P90 drop, catastrophic rate, own baseline.
- **Holdout v2**: 26 decks / 157 slides sealed in `40a0589` before any v1.4 change, run once on the
  frozen engine; guarded runner (release candidate, seal, clean tree, once per version). H01–H05
  retired as blind evidence. External deck holdouts: `cpe holdout external` (sanitized, never
  baselined). The private corporate template is recorded as development data, never as a holdout.
- **Human**: round r1 preserved (awaiting votes); round r2 (40 pairs: v1.3.3 vs v1.4 engine on the
  sealed holdout decks, both scored by the v1.4 scorer, quotas on comparison / process / KPI /
  text / roadmap + controls) awaiting votes; per-pair scorer/human agreement, Kendall τ-b with
  bootstrap CI, `human_score_disagreements.md`, round status (development data once used).
- **Provenance**: evaluated commit, tree, dirty flag, container digest, fingerprint, timestamp on
  every release signal; dirty runs cannot be recorded as release truth; `cpe results verify` in CI.
- Profiles moved to `qa/archetype_profiles.json` with rationale and evidence; `evals/profile_changes.md`.

### Engine (fixed on development data only; docs/ARCHETYPE_DIAGNOSIS.md)
- Adaptive vertical composition (`pptx/adaptive.py`): largest readable scale that fits, block on
  the optical centre, body type capped below the headline. Process (numerals for sparse flows,
  metric row under the steps), comparison (one scale and top edge for all columns), KPI strip →
  cards, KPI hero centred, gantt rows sized by count, small org charts centred.
- Text slides: own `text` role and component (argument / list / narrative / quote) instead of side
  commentary. **Bug fixed**: bullets were silently dropped when the slide also had commentary.
- **Bug fixed**: combo chart without a secondary axis crashed (found by the battery).
- Classification: one short argument and short quotations are statements; a one-row flow is a process.
- Metric fixes: figures with short units ("4.5 days") no longer count against hierarchy; the proof
  check accepts the same number at another scale ("€1.2bn" ↔ "1,210" in €M; "€61,000,000" ↔ "61").
- Provisional profile changes (process, comparison, kpi_dashboard), evidence and reasons in
  `evals/profile_changes.md`; human round r2 tests them.

### Results (v1.4 scorer unless stated)
- Regression: overall 92.8, **macro 92.4, P10 75.4, weakest kpi_dashboard 79.8**; 17/17 archetypes
  gate-eligible; QA visual errors 0. Battery before (v1.3.3): macro 80.4, P10 37.8, text 30.8,
  process 42.1, comparison 48.2.
- Robustness: 78 variants, median drop 0.0, P90 drop 0.0, catastrophic 0 (2 before the scaled-proof
  fix, both "€61M" → "€61,000,000").
- **Holdout v2** (run once): 26/26 decks built, overall 91.4, **macro 91.8, P10 74.5, weakest
  kpi_dashboard 71.6 (n=5)**; 4 visual QA errors.
- Engine vs scorer on the holdout (slide mean / macro / P10): v1.3.3 engine 77.3 / 78.9 / 36.5 with
  the v1.3.3 scorer; v1.4 engine **87.1 / 87.7 / 53.6 with the same v1.3.3 scorer**; 91.4 / 91.8 /
  73.7 with the v1.4 scorer. The engine alone explains ~10 points of mean and 17 of P10; the rest
  depends on the provisional profile changes.
- Examples (fixtures, not benchmark): Alvora 99.8, Gallery 99.1, Kestrel 99.5, QA passed.
- Human: no votes yet (r1, r2 awaiting votes).

### Holdout v2 findings (recorded, NOT tuned in this cycle → v1.5)
- KPI dashboards weakest (71.6); one dashboard slide has a hard LOW_CONTRAST error (likely a
  coloured delta on the new KPI card fill).
- PROOF_NOT_VISIBLE causes 7 of the 8 slides below 62: derived numbers (sums, differences).
- OUTSIDE_ZONE ×2 on a Spanish waterfall; RENDER_TEXT_SPILL on a long statement.

## 1.3.3 — Balanced cover

- Built-in cover: the title block (accent bar, title, subtitle) is measured and set on the optical
  centre of the upper field, so a one-line title no longer floats above a fixed gap; client, date
  and confidentiality sit in a primary-colour band across the foot of the slide (the lower half
  used to be empty). Corporate templates keep their native cover.
- Executive summary numbering (Alvora slide 2) checked at full resolution: the numbers are already
  centred on their claims; the misalignment seen on the contact sheet was a thumbnail artefact.
  No change.
- Regression unchanged (87.5); examples regenerated (Alvora final 99.8, gallery 99.8).

## 1.3.2 — Compact executive summaries

- Short executive summaries are set as ONE compact block on the optical centre (rows at their
  natural height plus breathing space, framed by rules) instead of being spread over the full
  height; dense summaries still share the height evenly.
- Archetype profile change, driven by explicit human feedback on gallery slide 3 (development
  set): `executive_summary` accepts a compact, balanced block (utilization from 0.50, empty space
  up to 0.32, balance weighted higher). A summary using under half the canvas is still flagged.
- Regression 87.3 → 87.5 (no regressions; the two-line summary case 41.8 → 75.1, still flagged as
  thin); gallery slide 3 scores 100.

## 1.3.1 — Agenda, executive summary and statement layout

- Agenda: a compact index set on the optical centre of the body (not stacked from the top),
  aligned with the headline's left margin, with larger numbers and titles.
- Executive summary rows: content sits on each row's centre line, so short rows read as an even
  table instead of text stuck to the top of tall empty bands.
- Statement slides: bar, statement and support are placed as one block on the optical centre of
  the zone (the text used to fall into the lower half).
- Gallery slides 2, 3 and 26 regenerated; regression unchanged (87.3, no new flags).

## 1.3.0 — Corporate templates read through their inheritance chain

Fixes for the structural findings of the v1.2 private corporate holdout. Because those findings
drove the changes, that template is **development data from now on**, not a holdout; the fixes are
generic and are tested on a synthetic template built to reproduce the same patterns
(`brand/fixtures.py::make_inherited_styles`). The public holdout cases were reviewed during v1.2
and are no longer blind either: v1.4 needs new sealed cases.

### Typography
- Text is attributed to the font it is really drawn in, following PowerPoint's inheritance:
  run → shape list style → layout placeholder → master placeholder → master text styles →
  presentation default → theme (`brand/model.py::effective_style`). The report says where the
  inherited text gets its font from.
- Weight-named families are one family ("Inter Black", "Inter ExtraBold" → Inter); a different
  family such as "Inter Tight" stays separate.
- Any INSTALLED font is now measured with its own file (fontconfig, exact family match), not only
  the built-in metric twins.
- The visual environment ships widely used open-licence corporate typefaces (Inter, Roboto,
  Open Sans, Lato, Montserrat; pinned) so brands set in them render and measure exactly.
  Regression renders are unchanged (87.3 before and after the image change).

### Colour roles
- Page and text colours come from what the template draws (the background of its content
  layouts, the colour its text resolves to) instead of theme slot names, which some templates use
  unconventionally (dk1 = accent, lt1 = text). All derived greys come from that real pair, the
  secondary data colour is darkened until white labels reach 4.5:1, and the dark data colour is a
  template colour (the text colour when the brand has no other dark).
- Supporting colours include brand-colour slide backgrounds and coloured text; pale brand tints
  are no longer mistaken for greys.

### Grid, layouts, brand rules
- Margins from the titles of the content layouts (symmetric when the content reaches the mirrored
  margin); finer column systems must earn their extra columns; pictures and full-bleed artwork no
  longer vote.
- A layout used for the last example slide keeps a `closing` label, even when it looks like a divider.
- Deck-level brand advice (editorial, never QA): `BRAND_BOOKEND` (the brand opens and closes on its
  colour) and `BRAND_COLOUR_SHARE` (share of brand-colour slides vs the template's examples).
- Render QA no longer judges text that belongs to the template's own artwork (e.g. a "Confidential"
  mark on a corporate cover layout).
- Bounded a contrast loop that could hang on templates with unconventional colour slots.

### Results on the (former) private holdout — development data, not a holdout result
- Agreement with the human-written brand spec: 13/22 → 21/22 claims (the remaining one: the
  closing layout is a divider-class layout used last, counted under "section").
- Test deck generated on it: QA failed with 112 errors → passed, 0 errors; with dividers and a
  closing slide, 0 errors, 0 warnings, no brand advice.
- Regression unchanged (87.3); public holdout 81.0 → 81.2 (the Spanish "todo" false error fixed
  after v1.2), now reported as no longer blind.

## 1.2.0 — Reproducible, archetype-aware, independently evaluated, corporate-template aware

**Goal:** make visual quality reproducible, archetype-aware, independently evaluable, and capable
of understanding real corporate PowerPoint systems. Not a higher score for its own sake: a higher
score should correspond more closely to a genuinely better composition on unseen slides.

### Reproducibility
- `docker/Dockerfile`: the visual environment pinned end to end (base image digest, Ubuntu archive
  snapshot, exact LibreOffice / fontconfig / FreeType / HarfBuzz / FriBiDi / font versions,
  `requirements.lock`). `scripts/cpe-docker` runs it locally; CI uses the same image (built once
  per commit and published to GHCR).
- Silent drift found and fixed: without FriBiDi, Pillow falls back from RAQM to BASIC text layout
  (no kerning) and every text measurement shifts ~0.2%.
- `environment.py`: manifest + render fingerprint recorded with every eval; `scripts/check_environment.py`.
- `cpe repro`: render twice, compare slide count, dimensions, PNG hashes, pixels, PDF spans,
  composition metrics and QA. Observed and required: pixel-identical.
- CI on `ubuntu-24.04`; actions on Node 24 pinned to SHAs; jobs lint · package · image · tests ·
  regression · reproducibility.
- `evals/results/latest.json` is the single source of truth; the README table is generated from
  it (`cpe results readme`, checked in CI).

### Composition
- `qa/archetypes.py`: 17 archetypes from content; expected visual profiles; score = fitness to the
  archetype (weighted mean + worst critical metric). v1.1 universal score kept as `score_v1`.
- Measurement fixes: hairline table rules, accent-only regions, one-sided emphasis, continuation
  markers, structural counts in the proof check.
- Composition is editorial advice (`editorial_advice`), never part of the hard-QA verdict or score.
- Candidate selection: hard-QA filter → archetype fitness; explicit "technically compatible but
  inappropriate for this content volume / archetype" verdicts; corporate layouts as candidates.
- Engine fixes from the development set: exhibit data given at the top level is normalised
  (`SPEC_DATA_SHAPE`) instead of crashing the build; table decimals follow the data; table splits
  are balanced; layouts are packaged so an installed wheel works.

### Evaluation
- `evals/regression/` (10 decks, +currencies/negatives/multi-source, +one slide per archetype),
  `evals/holdout/public/` (5 decks, sealed before the metric work), `evals/human_reference/`.
- `cpe eval --suite regression|holdout|examples [--docker] [--record]`; the holdout can never be
  baselined; `cpe holdout private` for corporate templates in `.private/` (git-ignored).
- `cpe human build|serve|import|report`: blind A/B page (random sides and order, no version /
  layout / score, keyboard, anonymous evaluators, resumable), Wilson intervals, Fleiss' κ, left
  bias, self-consistency, agreement between the automatic score and people. Round r1: 40 pairs.

### Corporate templates
- Every master analysed (no `slide_masters[0]` assumption); layout features → 20 classes with
  confidences, refined by observed usage; typography from theme + masters + layouts + usage +
  style-guide slides with conflicts; palette, grid, assets and brand rules with confidence.
- 16:9 templates on the 10 in page are rescaled and their masters used.
- Layout matching: native (placeholders filled) → adaptive (corporate layout + engine body) →
  CPE layout + theme; rejections recorded; per-slide reserved areas and headline/footer limits.
- New brand report (FONT WARNING with declared / observed / installed / renderable / fallback / risk).
- Synthetic three-master fixture for tests (`brand/fixtures.py`).

### Results (frozen for this release; current numbers live in `evals/results/latest.json`)
- Regression (archetype fitness): 87.3 over 10 decks / 39 slides, 0 QA errors. Not comparable to
  v1.1's 84.0 (a different metric); the v1.1 universal score of the v1.1.1 engine in the pinned
  environment reproduced 84.0 exactly (`evals/results/history/v1.1.1_pinned_env_*.json`).
- Holdout, public (rules frozen at e3b63e1): 81.0 over 5 decks / 27 slides, 1 QA error —
  a generalisation gap of 6.3 points.
- Holdout, private corporate template (sanitized): 1 master, 54 layouts, 32% of layouts classified
  with confidence ≥ 0.5; 13/22 claims of the human-written brand spec confirmed; the test deck
  generated on it failed QA (contrast).
- Human preference: tool and round r1 ready; no votes yet.

### Holdout findings (reported, not tuned on in this release)
- Typography inheritance stops at the master text styles: a template whose master placeholders
  are styled in another font (and whose weight variants are named as families, e.g. "Inter Black")
  is read as the theme font. Detected on the private holdout.
- Colour roles can put dark template accents under dark text (110 contrast errors on the private
  holdout test deck; the QA caught all of them).
- Grid inference over-fits finer column systems; closing layouts on brand colour are read as
  section dividers.
- `PROOF_NOT_VISIBLE` fires on derived headline numbers (sums, ratios) that the exhibit supports
  (≈ 4 of 7 flags on the public holdout).
- Fixed as correctness bugs, holdout results not re-recorded: layout classifier crash when all
  evidence is weak (private holdout); `TODO` placeholder check matched the Spanish word "todo"
  (public holdout).

## 1.1.1 — Full-width headlines and sparse-slide fixes

### Changed
- **Headlines run to the right margin.** The old "balanced" headline narrowed two-line titles to as
  little as 55% of the width, which pushed them to the left. Headlines now use the full width (or
  stop before a template logo). A single-word last line is fixed by the smallest possible
  narrowing (at most 15%), which is validated against a ±1.2% renderer tolerance so LibreOffice
  and PowerPoint cannot reintroduce it.
- Harvey balls use the secondary colour; the primary colour is kept for the highlighted column.
- The hierarchy metric ignores big figures ("€13M", "85%"): they are deliberate emphasis, not text
  competing with the headline.

### Added
- Process diagrams: an optional per-step `metric` / `metric_label` impact row, aligned with the steps.
- Timelines: an optional per-event `detail` line (owner / what the milestone unlocks).
- Takeaway columns under an exhibit show the commentary `title`.
- Composition variants (content scale) for text-bearing diagrams.
- Automatic proof ignores forecast periods: the claim is proven on actuals.

### Gallery
- g07, g13, g14, g18 and g19 no longer carry composition warnings: 0 warnings, composition
  87.0 → 92.1. g14, g18 and g19 got richer content (the impact per step, the goal of each
  phase, the critical-path read-out) rather than padding.

## 1.1.0 — Visual intelligence, corporate templates, quality evals

**Goal:** make visual quality testable rather than subjective, adapt composition to content, and
inherit the visual identity of an existing corporate PowerPoint.

### Added
- `qa/composition.py`: eight composition metrics measured on the real render (dead space, canvas
  utilization, balance, density, focal-point strength, visible headline proof, hierarchy,
  alignment rhythm) → 0–100 score + named flags; unfixable flags become `COMPOSITION_*` author actions.
- `compose.py`: composition engine (layout candidates × composition variants → one render pass →
  scoring → best candidate; rejects QA-failing and "compatible but editorially weak" candidates;
  consistency margin and repetition penalty). On by default in `cpe run` (`--no-compose` to skip).
- `evals/`: 8 stress decks, `cpe eval` with baseline comparison (crash / QA errors / composition
  drop / new flags → exit 1), `cpe measure` for any existing run, v1.0 vs v1.1 comparison.
- `brand/ingest.py` + `cpe brand ingest`: theme colours, heading/body fonts, masters, layouts,
  placeholders, logos → brand theme + compatibility report (fonts detected/installed/missing, the
  substitute used for measurement and rendering, unsupported elements); generation on the
  template's masters; `BRAND_RESERVED_OVERLAP` check.
- Font-aware text measurement (Carlito ≡ Calibri, Caladea ≡ Cambria, render-substitute measurement
  for missing fonts), heading vs body fonts.
- Automatic proof annotations (first→last change, CAGR, last-period change, waterfall total delta,
  pie top-k share); default single focus on one-series charts; KPI hero and single-statement
  treatments for sparse slides; content scale and table stretch knobs.
- QA: `RENDER_LABEL_TRUNCATED`, `RENDER_LABEL_ROTATED`; legible accent text (WCAG) for light brand colours.
- Apache-2.0 `LICENSE` + `NOTICE`; GitHub Actions CI (lint, tests, regression decks, evals).

### Changed
- README leads with the rendered demo; Spanish decimal commas understood by the number checks.

### Results (same metrics for both versions)
- Eval suite composition 77.6 → 83.8; flagged slides 30 → 20. Demo deck 91.3 → 94.4; gallery 84.1 → 87.0.

## 1.0.0 — Consulting presentation engine
Storyline-first engine: deck spec contract, storyline frameworks, headline lint, visual reasoning,
43 layouts in 16 families, native charts/tables/diagrams, LibreOffice rendering, three-layer QA
with a self-correction loop, CLI, docs, demo and gallery decks, 44 tests.
