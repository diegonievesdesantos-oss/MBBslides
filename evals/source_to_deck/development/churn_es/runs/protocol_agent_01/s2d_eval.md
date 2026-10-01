# Source-to-deck evaluation — churn_es

_protocol 1.0_ · run: {"engine": "1.7.0.dev0", "reasoning_protocol": "1.0", "model": "Claude subagent (fresh context)", "skill": "REASONING_PROTOCOL 1.0", "author": "independent subagent B"}

**Factuality (hard gate): PASS** — 0 hard failures 

## fact grounding

- critical_fact_recall: 1.0
- critical_facts: 4/4
- facts: 38
- fabricated_facts: 0
- fact_precision: 1.0
- traceable: 1.0
- arithmetic_errors: 0

## insight quality

- insights: 5
- supported: 5
- unsupported: 0
- material_conclusion_coverage: 3/3
- conclusions: {"C1": true, "C2": true, "C3": true}
- restating_facts: 0
- causal_overclaims: 0
- with_decision_relevance: 5

## storyline

- governing_thought: La fuga de particulares (-50.000 clientes, -22 M€) nace del deterioro de la atención al cliente tras el cambio de proveedor del centro de llamadas, no de la subida de precios: restaurar el tiempo de resolución es la primera palanca y la condición para recuperar los 30.000 clientes del presupuesto 2026.
- candidates_compared: 3
- framework: SCR
- framework_acceptable: True
- answer_first: True
- key_line_points: 3
- unsupported_key_line_points: 0
- mece_overlaps: 0
- traps_triggered: []
- errors: 0

## slide architecture

- slides: 8
- core: 6
- appendix: 0
- max_slides: 8
- within_length: True
- required_messages_on_core_slides: 3/3
- orphan_slides: 0
- duplicates: 0
- unjustified_extra_slides: 0
- information_economy: {"facts_available": 38, "facts_used": 20, "facts_appendix": 0, "facts_omitted": 18, "slides": 8, "core": 6, "support": 2, "appendix": 0, "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}

## headlines

- headlines: 8
- conclusion_rate: 1.0
- numbers_proven_rate: 1.0
- mean_words: 18.8

## visual intent

- slides_with_intent: 8
- mismatches: 0
- accuracy: 1.0

_dimensions are separate on purpose; there is no total score_
