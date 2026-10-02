# Reasoning protocol 1.4 — from raw sources to a deck plan

*The thinking layer of MBBslides is part of the product, so it is versioned like code.*
`reasoning_protocol: 1.4` is recorded in every artifact `cpe reason` writes and in every
source-to-deck evaluation, together with the agent/model and skill version that produced the work.
Engine performance (deterministic code) and agent + engine system performance are reported apart.

## Contract

The agent writes structured JSON artifacts into `work/`; deterministic tools build the fact model,
check everything, and render. The agent may create hypotheses, insights and wording. **It never
creates a fact**: every number above `facts.json` must be grounded in cited facts (one bounded
operation at most), or `cpe reason check` blocks the deck. Persist structured decisions, evidence,
short rationales and critic findings — never hidden reasoning traces.

| artifact | written by | content |
|---|---|---|
| `project.json` | agent from the brief (fields not given are marked `inferred`) | audience, decision, question, horizon, scope, constraints, assumptions, max_slides |
| `source_manifest.json`, `facts.json` | `cpe reason facts` | sources with hashes; atomic facts with values, unit, period, basis and exact location; derived changes with lineage |
| `hypotheses.json` | agent | `{id, statement, status: supported|rejected|unresolved, supporting_facts, contradicting_facts, confidence, implication}` |
| `insights.json` | agent | `{id, statement, facts, hypotheses, materiality: high|medium|low, decision_relevance, caveat?, contradicting_facts?}` |
| `storyline.json` | agent | `{framework, framework_rationale, candidates: [{text, scores, insights}], governing_thought, key_line: [{id, message, insights, role}], decision}` |
| `deck_plan.json` | agent | `{slides: [{id, priority: core|support|appendix, role?, key_line, purpose, decision_role, headline, insights, facts, message_type, archetype, reason_to_exist, why_not_merge?}]}` |
| `ghost_deck.md` | `cpe reason ghost` | the argument from headlines alone |
| `deck.json` | agent (render spec) | slides cite facts: `evidence: [{"fact": "F0012", "claim": …}]` |
| `reasoning_report.json/.md`, `evidence_graph.json` | `cpe reason check` | every check, hard gates, stopping criteria, lineage |

### Exact formats (learned from the first independent agent runs)

- `hypotheses.json`: `confidence` is a number in 0–1; a supported hypothesis with contradicting
  facts carries a `rationale` saying why it still holds.
- `insights.json`: `hypotheses` lists the hypotheses an insight SUPPORTS; a rejected hypothesis an
  insight argues against goes in `refutes` (citing a rejected hypothesis under `hypotheses` is a
  hard failure: the insight would rest on it).
- `computed_facts.json`: `{"facts": [{"id": "C0001", "claim": …, "formula": "F0029 / F0041 * 100",
  "values": [{"value": 19.9, "unit": "PCT"}]}]}` — the formula uses fact ids (`F…`, `C…`, `A…`),
  numbers, `+ − × ÷`, `sum()` and `abs()`; it is recomputed and must match the stated value.
  A bare id is the fact's first value; `F0062[1]` is its second value (0-based), for sentences that
  state several numbers ("of 9 and 14 days, costing 1.6 and 2.4 EUR M").
- `assumptions.json`: `{"assumptions": [{"id": "A001", "statement": …, "values": [{"value": 3,
  "unit": "PP"}], "rationale": …, "owner": …}]}`.
- `deck_plan.json`: each slide's `key_line` is ONE key-line id; the executive summary is
  `"role": "exec_summary"` (no key line); `title`, `divider`, `next_steps` are the other roles.
- Units: `EUR_M`, `USD_BN`, `PCT`, `PP`, `DAYS`, `HOURS`, … (as `facts.json` writes them). In prose, money
  may be written `€7.8M`, `7.8 EUR M` or `EUR 7.8M`; `€2.868M` is a decimal; `23–24%` is two percentages.
- `fact_conflicts.json`: `{"conflicts": [{"facts": [{"fact": "F0012"}, {"fact": "F0040"}], "type": …, "resolution": "…"}]}`
  (plain ids in `facts` are accepted).
- **Every number a reader sees on a slide is grounded (v1.8):**
  - This covers the headline, body text, KPIs, table cells, chart data, commentary and takeaways.
  - Each number must be a value of a fact the slide cites in `evidence`, or one operation on two of
    them. Table cells and chart values are compared unit-free.
  - An uncited number is a hard UNSUPPORTED_NUMBER. Years, ranks and counts up to 10 are exempt;
    "23–25%" reads as 23% and 25%.
  - A computed fact's source is the files of the raw facts it derives from (WRONG_SOURCE follows lineage).
- **Fact ids are stable (v1.8):**
  - Re-running `cpe reason facts` on a work folder keeps the id of every fact found at the same source
    location: the same cell, or the same sentence and values.
  - New facts get new ids; facts no longer extracted are listed in `facts_refresh.json`.
  - FACT_FABRICATED is checked against the raw content of each file, under every reading of its
    separators, not against a re-extraction. An extractor upgrade never turns an old true fact into a
    fabrication.
- Grounding is per sentence: a number must come from the facts the sentence (insight, key-line
  insights for the governing thought, slide facts and insights for a headline) cites.

## Passes

Each pass reads the artifacts before it and writes or amends one artifact. A pass may send the
work back (e.g. a critic finding reopens the storyline).

1. **Extract facts** — `cpe reason facts sources/ -o work/`. Read `facts.json`; note conflicts
   (same KPI, different values or periods), forecast vs actual, units.
1b. **Analyse row-level data** (1.3):
   - A table longer than 150 rows (orders, CRM, ledger) is listed under `facts.json` → `stats.datasets`, not read cell by cell.
   - Write a script that reads `$CPE_SOURCES` and writes CSV tables to `$CPE_OUT`. Keep them small and labelled, one measure per column.
   - Run `cpe reason analyze work/ script.py --sources sources/`. It runs the script twice, records hashes in `work/analysis.json` and fails if the two runs differ.
   - Then re-run `cpe reason facts`: the output tables become facts (`analysis/<script>/<file>`), citable like any other.
   - Check the data before trusting it: duplicates, double-loaded batches, test rows, time zones, units.
   - Record what you cleaned and why in the script.
   - The check blocks a deck whose analysis outputs no longer match their script or inputs (ANALYSIS_STALE, ANALYSIS_NOT_REPRODUCIBLE).
2. **Business question** — write `project.json`. If the brief is ambiguous, infer a working
   question and list it under `inferred`; do not continue without a question.
3. **Hypotheses** — 3–6 competing explanations / answers, including the one management believes.
4. **Test hypotheses** — mark each supported / rejected / unresolved with the facts for and
   against. A hypothesis with no evidence stays unresolved; rejecting one is progress.
5. **Insights** — reasoning ACROSS facts ("acquisition efficiency fell 42% with stable conversion
   → media inflation, not funnel leakage"), each with materiality and decision relevance. A
   restated fact is not an insight; a causal claim needs a tested hypothesis.
6. **Governing-thought candidates** — at least two, scored 0–2 on: answers the question,
   supported by evidence, specific, decision-oriented, non-trivial, covers the storyline.
7. **Critique the storyline** — red team (what contradicts it?), partner review (is this the
   answer a senior client needs?).
8. **Choose** the governing thought; build the key line (2–5 MECE points, each backed by
   insights); choose the framework that fits the question (SCR, CII, PDS, DRI, MPO, CGT, HEC) and
   say why. The argument comes first; the framework is a tool.
8b. **Decision frame** (1.1) — write `storyline.json["decision"]` (see below): target, levers with
   their impact, identified total and gap, the current plan tested, options with their cost, asks,
   gates, KPIs. Key-line roles put the problem or risk before the solution.
9. **Ghost deck** — write `deck_plan.json`: what deserves a slide, what merges, what goes to the
   appendix, what is omitted. Every slide states its reason to exist; two core slides on one
   key-line point state why they are not one. Then `cpe reason ghost`.
10. **Challenge the ghost deck** — editor (can any slide be deleted?), fact checker (is every
    headline number grounded?). Read the headlines alone: do they make the argument?
11. **Slide intents** — message type per slide, then the evidence it needs.
13. **Write for the reader** (1.4) — storyline.md and slide text keep deadlines, owners, mechanisms
    and every concrete fact. Uncertainty is stated once, where it matters. Compare your storyline with
    what a senior consultant would hand over without any protocol: nothing they would include may be missing.
12. **Visuals** — only now choose the exhibit, from the message type and the data shape
    (change → waterfall, ranking → bar/table, structure → architecture, recommendation →
    statement …); write `deck.json` citing fact ids.

Then: `cpe reason check work/` → render (`cpe run work/deck.json`) → visual QA → review.

## Decision frame (1.1)

Added after the first expert storyline round (`evals/human_reference/rounds/s1/FEEDBACK.md`). That round
was 2–2. The evaluator praised the protocol run for **numeric discipline**: figures reconcile, the gap
to the target is admitted, every lever is quantified, there is governance, and it does not overclaim.
They praised the no-protocol run for **thinking about the decision**: it challenges the current plan,
costs the options, marks upper bounds and what to validate, closes with approvable proposals, and puts
the problem first. A storyline needs both.

```json
"decision": {
  "target":       {"value": 1.5, "unit": "PP", "facts": ["F0003"]},
  "levers":       [{"id": "L1", "statement": "…", "impact": {"value": 0.9, "unit": "PP"}, "facts": ["C0002"],
                    "bound": "point|upper|lower|range", "validate": "price test on the top 200 references, Q1 2027"}],
  "identified":   {"value": 1.4, "unit": "PP"},
  "gap":          {"value": 0.1, "unit": "PP", "how_closed": "…"},
  "current_plan": {"statement": "budgeted +25% electronics growth", "verdict": "holds|partly|does_not_hold",
                   "facts": ["…"], "cost_if_kept": {"value": 0.7, "unit": "PP"}},
  "options":      [{"id": "O1", "statement": "…", "cost": {"value": …, "unit": "…"}, "facts": ["…"], "chosen": true,
                    "cost_components": {"price": …, "switching": …, "risk": …}}],
  "asks":         [{"statement": "…", "type": "approve|reject|reallocate|stop|commission", "owner": "…"}],
  "gates":        [{"statement": "…", "criterion": "…", "when": "…"}],
  "kpis":         [{"name": "…", "target": "…", "cadence": "monthly"}]
}
```

| check | level | asks for |
|---|---|---|
| levers ≠ `identified`, `gap` ≠ target − identified (to one unit of the last digit shown) | **hard** ARITHMETIC_ERROR | figures that reconcile |
| lever impact not grounded in the facts it cites | **hard** UNSUPPORTED_NUMBER | a defensible lever |
| GAP_NOT_STATED | warning | say what is missing to reach the target |
| LEVER_UNQUANTIFIED | warning | every lever quantified separately |
| OVERCLAIM_BOUND | warning | an upper bound is not stated as certain in the governing thought |
| UNCERTAINTY_UNMARKED | warning | upper bounds and assumptions carry what to validate before committing |
| CURRENT_PLAN_NOT_TESTED / _UNSUPPORTED | warning | does the plan / budget in force hold, and what does keeping it cost? |
| OPTIONS_NOT_COMPARED / OPTION_UNCOSTED | warning | at least two options (keeping the current plan counts), each costed |
| OPTIONS_DIFFERENT_BASIS (1.2) | warning | every option carries the same `cost_components`: a risk or cost charged to one option is charged to every option it touches (0 only if it truly does not apply) |
| ASK_MISSING / ASK_DEFERRED | warning | an approvable close — `commission` alone is an assignment for later |
| GATES_MISSING / KPIS_MISSING | warning | governance: validation gate, approval criterion, tracking KPI |
| SOLUTION_BEFORE_PROBLEM | warning | problem or risk first (key-line `role`) |
| KEYLINE_WITHOUT_NUMBERS | info | the storyline stands alone with data |

The benchmark reports a `decision` dimension (elements present, no score). `cpe reason eval-text` reports
`decision_signals` for any storyline.md. These are lexical cues for comparing systems that write no
JSON, and they are not verdicts. The frame is a checklist for the PARTNER REVIEW critic: a warning is
a question to answer ("no option was costed: is there really only one?"), not something to fill in mechanically.

### 1.2 — options on the same basis

From round s2 (`evals/human_reference/rounds/s2/FEEDBACK.md`), where the protocol won 3–1. Its one loss
was a logic error the checks could not see. The single-plant stoppage risk was charged to the 100%
option only, although the 70/30 option still put 70% of the volume on that plant. Options now declare
their cost components, and options compared on different components are flagged.

## 1.4 — traceability never costs the reader content

In round s4 (five external raw-data cases) the agent without the protocol was preferred 4–1. Both
reached the same answers, but the protocol storylines were about 30% shorter. They dropped deadlines,
mechanisms and the bridge from numbers to action, partly to get past checks. From 1.4 on:

- **The checks block invented quantities, and nothing else.**
  - Checked: amounts, percentages, points, ratios and counts above 30.
  - Never checked: dates, deadlines and periods ("antes del 31/12/2026", "Q1 2027", "2025-26"),
    durations ("6-8 semanas", "12 mensualidades") and small whole counts (people, stores, waves).
- **Never remove or blur a true statement to pass a check.** If a true number fails, cite the fact
  that holds it, add an analysis output, or record an assumption. Do not reword it into vagueness
  ("antes de que acabe 2026" for a contractual date). Write a tool problem in `critique.json`.
- **Put the brief in `sources/brief.md`.** Its figures (targets, budgets, constraints) are then
  citable facts, not assumptions.
- **Write for the reader** (pass 13). The storyline.md is a client document:
  - each key-line point says what happened, why (the mechanism) and what follows from it;
  - the recommendation names action, owner, amount and date;
  - every fact that makes the case concrete stays in;
  - state uncertainty once, where it matters (an upper bound, a gate); headlines and the governing
    thought state the decision plainly.
  - A protocol storyline should be at least as complete as one written without the protocol. The
    protocol adds verification; it never subtracts content.

## v1.8 tooling — messy inputs (protocol text unchanged at 1.4)

These checks run inside `cpe reason facts` / `cpe reason check`. They add no step for the agent and
need no new human round. Each is a warning unless stated.

- **Periods and bases.** Every value carries a period and a basis:
  - periods: FY2025, CY2025, 2025-Q3, H1, 2025-07, LTM, YTD, run-rate;
  - bases: actual, budget, forecast, target, plan, estimate, audited, management.

  Scenario columns (Real / Presupuesto / Forecast) and two-level headers ("2024 · Real") set them.
  `PERIOD_MISMATCH` (warning) flags a computed fact that mixes incompatible values:
  - budget with actual;
  - run-rate with reported;
  - YTD with a full year;
  - a quarter with a year;
  - FY with CY.

  When the comparison is deliberate, add `"periods_ok": true` to the computed fact and say it in the
  text ("vs presupuesto").
- **Conflict types.** `conflicts.json` names the kind of disagreement:
  - `management_vs_audited`;
  - `forecast_vs_actual`;
  - `definition_mismatch` (group vs local scope);
  - `value_mismatch`;
  - `prose_mismatch` (two documents, no period).

  The storyline must resolve each conflict whose facts it uses, as in 1.0.
- **Tables as found.** These are read correctly:
  - two-level headers;
  - total and subtotal rows, which become `row_kind` and are never summed again;
  - decimal-comma documents;
  - units per cell.

  Charts embedded in docx / xlsx / pptx are read from their data caches, or from the referenced
  cells, and become facts like any table.
- **Cell-to-fact binding.**
  - A table cell or chart point must be a cited fact value (since 1.7.1).
  - Since 1.8 it can be bound to its fact with `"at"`, which makes a swapped value a hard error.
  - Unbound cells are checked by their labels: a warning when the value belongs to a fact about another row.
  - On the real private deck: 11 of 15 injected same-column swaps were flagged, with 0 false positives on
    the clean deck.
- **Updating an existing deck.**
  1. Run `cpe deck ingest old.pptx -o work` before the new pass.
  2. Run `cpe deck stale work` after `cpe reason facts`.
  3. An old number is reused only when the new fact model confirms it. An outdated number is replaced
     from its new fact. An untraced number is removed, or its source is added.

  The old deck's storyline (`old_ghost.md`) is a hypothesis, not a fact.

## Critic roles

Each critic writes structured findings into `work/critique.json`:
`{critic, finding, artifact, ref, severity: high|medium|low, action, resolved: bool}`.

| critic | question |
|---|---|
| FACT CHECKER | Is every important claim grounded? (the deterministic check runs first) |
| PARTNER REVIEW | Is this the answer a senior client needs? Does it test the current plan, cost the options, and close with something approvable today? Is it as concrete and readable as a document written without any protocol (deadlines, owners, mechanisms kept)? |
| RED TEAM | What contradicts this storyline? Which rejected or unresolved hypothesis could be true? Is each risk and cost applied to every option it touches (1.2)? |
| EDITOR | Can any slide be deleted, merged or moved to the appendix? |
| DATA-VIZ REVIEW | Is each visual encoding appropriate for its message and data? |

## Stopping criteria

Stop iterating when: no hard factual error (decision-frame arithmetic included) · storyline checks pass · ghost-deck checks pass · no
unsupported headline · visual QA passes · composition passes · no unresolved high-severity critic
finding. `cpe reason check` reports the first four; render QA the next two. Avoid endless
self-review: two critique rounds without new high-severity findings end the loop.

## Model dependency

The deterministic engine is model-agnostic. The protocol needs a model that can: read tables and
prose, follow a JSON contract, cite ids, and revise artifacts from structured findings. Record the
model family, skill version and any exposed sampling configuration in the evaluation's `run`
metadata (`cpe reason eval … --model … --skill …`).
