# Source-to-deck evaluation

v1.7 asks: **given raw material and a decision question, does MBBslides build the right deck —
not only render a good one?** The evaluation keeps every dimension separate; there is no total
score, because a beautiful deck with an invented number is a failure whatever else it does well.

| dimension | measures | source |
|---|---|---|
| **factuality (hard gate)** | fabricated facts, unsupported numbers in insights / governing thought / headlines, wrong source attribution, arithmetic errors, claims resting on rejected hypotheses | `cpe reason check` |
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

## Human evaluation of reasoning (planned)

The blind A/B tool is reused for **storylines** and **deck plans** before rendering: reviewers see
the business question, a short source summary and two storylines (or two outlines) and answer
"which would you take to the client?" — separating reasoning quality from visual quality.
