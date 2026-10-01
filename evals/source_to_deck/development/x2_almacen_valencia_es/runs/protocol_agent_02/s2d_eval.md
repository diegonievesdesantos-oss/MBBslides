# Source-to-deck evaluation — x2_almacen_valencia_es

_protocol 1.1_ · run: {"engine": "1.7.0.dev0", "reasoning_protocol": "1.1", "model": "Claude subagent", "skill": "protocol 1.1", "author": "developing agent"}

**Factuality (hard gate): PASS** — 0 hard failures 

## fact grounding

- critical_fact_recall: 0.75
- critical_facts: 3/4
- facts: 55
- fabricated_facts: 0
- fact_precision: 1.0
- traceable: 1.0
- arithmetic_errors: 0

## insight quality

- insights: 6
- supported: 6
- unsupported: 0
- material_conclusion_coverage: 3/3
- conclusions: {"C1": true, "C2": true, "C3": true}
- restating_facts: 0
- causal_overclaims: 0
- with_decision_relevance: 6

## storyline

- governing_thought: Rechazar el cierre de Valencia: los 4,1 M€ de ahorro prometidos son el coste bruto del almacén y, neto de transporte, turno adicional y coste variable trasladado a Madrid, el cierre ahorra como máximo 0,1 M€ al año, cuesta 3,2 M€ y arriesga hasta 2,2 M€ de margen anual; en su lugar, renovar el alquiler con un 25% de descuento antes de diciembre de 2026, que ahorra 0,3 M€ al año.
- candidates_compared: 3
- framework: SCR
- framework_acceptable: True
- answer_first: True
- key_line_points: 3
- unsupported_key_line_points: 0
- mece_overlaps: 0
- traps_triggered: []
- errors: 0

## decision

- frame: True
- levers: 1
- levers_quantified: 1
- gap_stated: True
- current_plan_tested: True
- options_costed: 3
- approvable_asks: 2
- deferred_asks: 1
- bounds_marked: 0
- gates: 2
- kpis: 3
- problem_first: True
- warnings: []

## slide architecture

- slides: 8
- core: 8
- appendix: 0
- max_slides: 9
- within_length: True
- required_messages_on_core_slides: 3/3
- orphan_slides: 0
- duplicates: 0
- unjustified_extra_slides: 0
- information_economy: {"facts_available": 71, "facts_used": 35, "facts_appendix": 0, "facts_omitted": 36, "slides": 8, "core": 8, "support": 0, "appendix": 0, "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}

## headlines

- headlines: 7
- conclusion_rate: 1.0
- numbers_proven_rate: 1.0
- mean_words: 28.1

## visual intent

- slides_with_intent: 8
- mismatches: 0
- accuracy: 1.0

_dimensions are separate on purpose; there is no total score_
