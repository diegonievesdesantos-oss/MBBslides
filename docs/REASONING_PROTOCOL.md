# Reasoning protocol 1.0 — from raw sources to a deck plan

*The thinking layer of MBBslides is part of the product, so it is versioned like code.*
`reasoning_protocol: 1.0` is recorded in every artifact `cpe reason` writes and in every
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
| `storyline.json` | agent | `{framework, framework_rationale, candidates: [{text, scores, insights}], governing_thought, key_line: [{id, message, insights, role}]}` |
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
- `assumptions.json`: `{"assumptions": [{"id": "A001", "statement": …, "values": [{"value": 3,
  "unit": "PP"}], "rationale": …, "owner": …}]}`.
- `deck_plan.json`: each slide's `key_line` is ONE key-line id; the executive summary is
  `"role": "exec_summary"` (no key line); `title`, `divider`, `next_steps` are the other roles.
- Units: `EUR_M`, `USD_BN`, `PCT`, `PP`, `DAYS`, `HOURS`, … (as `facts.json` writes them).
- Grounding is per sentence: a number must come from the facts the sentence (insight, key-line
  insights for the governing thought, slide facts and insights for a headline) cites.

## Passes

Each pass reads the artifacts before it and writes or amends one artifact. A pass may send the
work back (e.g. a critic finding reopens the storyline).

1. **Extract facts** — `cpe reason facts sources/ -o work/`. Read `facts.json`; note conflicts
   (same KPI, different values or periods), forecast vs actual, units.
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
9. **Ghost deck** — write `deck_plan.json`: what deserves a slide, what merges, what goes to the
   appendix, what is omitted. Every slide states its reason to exist; two core slides on one
   key-line point state why they are not one. Then `cpe reason ghost`.
10. **Challenge the ghost deck** — editor (can any slide be deleted?), fact checker (is every
    headline number grounded?). Read the headlines alone: do they make the argument?
11. **Slide intents** — message type per slide, then the evidence it needs.
12. **Visuals** — only now choose the exhibit, from the message type and the data shape
    (change → waterfall, ranking → bar/table, structure → architecture, recommendation →
    statement …); write `deck.json` citing fact ids.

Then: `cpe reason check work/` → render (`cpe run work/deck.json`) → visual QA → review.

## Critic roles

Each critic writes structured findings into `work/critique.json`:
`{critic, finding, artifact, ref, severity: high|medium|low, action, resolved: bool}`.

| critic | question |
|---|---|
| FACT CHECKER | Is every important claim grounded? (the deterministic check runs first) |
| PARTNER REVIEW | Is this the answer a senior client needs, and is the ask clear? |
| RED TEAM | What contradicts this storyline? Which rejected or unresolved hypothesis could be true? |
| EDITOR | Can any slide be deleted, merged or moved to the appendix? |
| DATA-VIZ REVIEW | Is each visual encoding appropriate for its message and data? |

## Stopping criteria

Stop iterating when: no hard factual error · storyline checks pass · ghost-deck checks pass · no
unsupported headline · visual QA passes · composition passes · no unresolved high-severity critic
finding. `cpe reason check` reports the first four; render QA the next two. Avoid endless
self-review: two critique rounds without new high-severity findings end the loop.

## Model dependency

The deterministic engine is model-agnostic. The protocol needs a model that can: read tables and
prose, follow a JSON contract, cite ids, and revise artifacts from structured findings. Record the
model family, skill version and any exposed sampling configuration in the evaluation's `run`
metadata (`cpe reason eval … --model … --skill …`).
