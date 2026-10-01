# Source-to-deck evaluation — x2_saas_retention

_protocol 1.1_ · run: {"engine": "1.7.0.dev0", "reasoning_protocol": "1.1", "model": "Claude subagent", "skill": "protocol 1.1", "author": "developing agent"}

**Factuality (hard gate): PASS** — 0 hard failures 

## fact grounding

- critical_fact_recall: 1.0
- critical_facts: 4/4
- facts: 86
- fabricated_facts: 0
- fact_precision: 1.0
- traceable: 1.0
- arithmetic_errors: 0

## insight quality

- insights: 8
- supported: 8
- unsupported: 0
- material_conclusion_coverage: 3/3
- conclusions: {"C1": true, "C2": true, "C3": true}
- restating_facts: 0
- causal_overclaims: 0
- with_decision_relevance: 8

## storyline

- governing_thought: Growth slowed because we lost customers, not deals: higher churn explains 80.4% of the €5.6M fall in net new ARR, concentrated in first-year customers after the onboarding cut. Fund retention first (restore onboarding, €0.8M) with a gated first wave of 10 AEs, for €2.0M a year instead of €3.6M, rather than 30 AEs whose 2026 yield is at most an estimated €4.5M, not the €9M promised.
- candidates_compared: 3
- framework: SCR
- framework_acceptable: True
- answer_first: True
- key_line_points: 4
- unsupported_key_line_points: 0
- mece_overlaps: 0
- traps_triggered: []
- errors: 0

## decision

- frame: True
- levers: 3
- levers_quantified: 3
- gap_stated: True
- current_plan_tested: True
- options_costed: 3
- approvable_asks: 4
- deferred_asks: 0
- bounds_marked: 3
- gates: 2
- kpis: 4
- problem_first: True
- warnings: []

## slide architecture

- slides: 9
- core: 9
- appendix: 0
- max_slides: 9
- within_length: True
- required_messages_on_core_slides: 3/3
- orphan_slides: 0
- duplicates: 0
- unjustified_extra_slides: 0
- information_economy: {"facts_available": 97, "facts_used": 50, "facts_appendix": 0, "facts_omitted": 47, "slides": 9, "core": 9, "support": 0, "appendix": 0, "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}

## headlines

- headlines: 8
- conclusion_rate: 1.0
- numbers_proven_rate: 1.0
- mean_words: 24.1

## visual intent

- slides_with_intent: 9
- mismatches: 0
- accuracy: 1.0

_dimensions are separate on purpose; there is no total score_
