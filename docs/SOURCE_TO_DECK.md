# Source-to-deck evaluation

v1.7 asks: **given raw material and a decision question, does MBBslides build the right deck —
not only render a good one?** The evaluation keeps every dimension separate; there is no total
score, because a beautiful deck with an invented number is a failure whatever else it does well.

| dimension | measures | source |
|---|---|---|
| **factuality (hard gate)** | fabricated facts (checked against the raw files), unsupported numbers in insights / governing thought / every number on every slide (v1.8), wrong source attribution, arithmetic errors, claims resting on rejected hypotheses | `cpe reason check` |
| fact grounding | critical-fact recall, fact precision (1 − fabricated), traceability, arithmetic errors | `facts.json` vs sources and `reference.json` |
| insight quality | supported vs unsupported, required conclusions reached, restated facts, causal overclaims, decision relevance stated | `insights.json` |
| storyline | governing thought, candidates compared, framework fits, answer first, key-line support, MECE overlaps, **traps triggered** | `storyline.json`, `deck_plan.json` |
| slide architecture | required messages on core slides, length vs brief, orphans, duplicates, unjustified extra slides, information economy | `deck_plan.json` |
| headlines | conclusion rate, numbers proven, length | `deck_plan.json` |
| visual intent | message type ↔ archetype mismatches | `deck_plan.json` |
| final deck | visual QA, composition, human preference | existing render pipeline and human rounds |

Required conclusions and traps are matched by **term groups and numbers**, never by wording: a
case lists several acceptable phrasings, and a human reviewer reads `reference_governing_thought`
only as orientation. Several decks can be good.

## Sets and contamination

| set | status |
|---|---|
| `evals/source_to_deck/development/` | development — written by the developing agent, visible, tunable |
| `evals/source_to_deck/sealed/` | written before a cycle and not used in it; run once at the freeze |
| `evals/source_to_deck/external/` | written outside the development loop — **AWAITING EXTERNAL INPUT** |

Any case used to change the engine, the checks, the protocol or the skill becomes development data
for later versions. A run records `reasoning_protocol`, the engine version, the agent/model and the
skill version (`--model`, `--skill`), so a reasoning result is reproducible.

## Human evaluation of reasoning

The blind A/B tool is reused for **storylines** and **deck outlines** before rendering: reviewers
see the business question and a short source summary, then two storylines (or two outlines), and
answer "which would you take to the client?" — separating reasoning quality from visual quality.

```bash
scripts/cpe human build-text -o evals/human_reference/rounds/s1 --kind storyline \
  --pair "agentA->agentB=runs_A/storylines,runs_B/storylines" --context cases/context
scripts/cpe human package evals/human_reference/rounds/s1 -o s1_voting.zip
```

Same blinding, private key, voting package, per-rater and pooled statistics as slide rounds. Round
`s1` (expert, protocol 1.0 vs no protocol, development cases) was 2–2 and produced the decision
frame of protocol 1.1 (`rounds/s1/FEEDBACK.md`); it is now development data. The next storyline
round needs cases that 1.1 has not seen.

## Conflicts and critics

`cpe reason facts` writes `fact_conflicts.json` (same measure and period stated differently,
forecast vs actual, value mismatch); the agent records a resolution for each. An unresolved
conflict touching a fact the deck uses is an error. Critic findings go to `critique.json`; an
unresolved high-severity finding stops the loop.
