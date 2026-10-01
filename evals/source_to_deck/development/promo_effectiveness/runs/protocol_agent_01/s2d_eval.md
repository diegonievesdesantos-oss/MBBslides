# Source-to-deck evaluation — promo_effectiveness

_protocol 1.0_ · run: {"engine": "1.7.0.dev0", "reasoning_protocol": "1.0", "model": "Claude subagent (fresh context)", "skill": "REASONING_PROTOCOL 1.0", "author": "independent subagent B"}

**Factuality (hard gate): PASS** — 0 hard failures 

## fact grounding

- critical_fact_recall: 1.0
- critical_facts: 4/4
- facts: 28
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

- governing_thought: Our promotions are destroying value — they shift existing demand rather than create it while gross margin fell from 27.4% to 25.1% — so the board should reject the 20% budget increase and refocus the 2026 plan on Fresh and Beverages, cutting deep discounts in Household and Snacks
- candidates_compared: 3
- framework: SCR
- framework_acceptable: True
- answer_first: True
- key_line_points: 4
- unsupported_key_line_points: 0
- mece_overlaps: 0
- traps_triggered: []
- errors: 0

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
- information_economy: {"facts_available": 28, "facts_used": 17, "facts_appendix": 0, "facts_omitted": 11, "slides": 8, "core": 8, "support": 0, "appendix": 0, "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}

## headlines

- headlines: 8
- conclusion_rate: 1.0
- numbers_proven_rate: 1.0
- mean_words: 19.5

## visual intent

- slides_with_intent: 8
- mismatches: 0
- accuracy: 1.0

_dimensions are separate on purpose; there is no total score_
