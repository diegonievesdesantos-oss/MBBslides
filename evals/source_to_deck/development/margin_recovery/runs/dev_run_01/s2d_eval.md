# Source-to-deck evaluation — margin_recovery

_protocol 1.0_ · run: {"engine": "1.7.0.dev0", "reasoning_protocol": "1.0", "model": "Claude (developing session)", "skill": "SKILL.md v1.6 + REASONING_PROTOCOL 1.0", "author": "developing agent"}

**Factuality (hard gate): PASS** — 0 hard failures 

## fact grounding

- critical_fact_recall: 1.0
- critical_facts: 6/6
- facts: 57
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

- governing_thought: Gross margin fell 1.9 pp mainly because sales shifted to low-margin electronics; repricing and mix steering recover about 1.1 pp, and regaining within-category margins closes the 1.5 pp target by 2027 without touching store labour
- candidates_compared: 4
- framework: PDS
- framework_acceptable: True
- answer_first: True
- key_line_points: 3
- unsupported_key_line_points: 0
- mece_overlaps: 0
- traps_triggered: []
- errors: 0

## slide architecture

- slides: 9
- core: 7
- appendix: 1
- max_slides: 10
- within_length: True
- required_messages_on_core_slides: 3/3
- orphan_slides: 0
- duplicates: 0
- unjustified_extra_slides: 0
- information_economy: {"facts_available": 63, "facts_used": 25, "facts_appendix": 15, "facts_omitted": 23, "slides": 9, "core": 7, "support": 1, "appendix": 1, "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}

## headlines

- headlines: 8
- conclusion_rate: 1.0
- numbers_proven_rate: 1.0
- mean_words: 13.9

## visual intent

- slides_with_intent: 8
- mismatches: 0
- accuracy: 1.0

_dimensions are separate on purpose; there is no total score_
