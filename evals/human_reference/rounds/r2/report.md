# Human A/B preference — round r2

Evaluators: 1 · comparisons: 38

| scope | n | challenger wins | baseline wins | ties | challenger preference | 95% CI (Wilson) | ties as ½ |
|---|---|---|---|---|---|---|---|
| all | 38 | 35 | 1 | 2 | 0.972 | 0.858–0.995 | 0.947 |
| comparison `engine-v1.3.3-vs-v1.4` | 38 | 35 | 1 | 2 | 0.972 | 0.858–0.995 | 0.947 |
| archetype comparison | 7 | 7 | 0 | 0 | 1.0 | 0.646–1.0 | 1.0 |
| archetype hierarchy | 2 | 1 | 0 | 1 | 1.0 | 0.207–1.0 | 0.75 |
| archetype kpi_dashboard | 3 | 2 | 1 | 0 | 0.667 | 0.208–0.939 | 0.667 |
| archetype kpi_hero | 6 | 5 | 0 | 1 | 1.0 | 0.566–1.0 | 0.917 |
| archetype process | 8 | 8 | 0 | 0 | 1.0 | 0.676–1.0 | 1.0 |
| archetype roadmap | 6 | 6 | 0 | 0 | 1.0 | 0.61–1.0 | 1.0 |
| archetype text_exhibit | 6 | 6 | 0 | 0 | 1.0 | 0.61–1.0 | 1.0 |

**Does the automatic score agree with people?** 33/34 decisive votes (rate 0.971, 95% CI 0.851–0.995)
**Left-side bias:** left chosen in 0.5 of decisive votes (95% CI 0.345–0.655)
**Inter-rater:** {"note": "one evaluator: agreement needs \u22652"}
**Self-consistency on repeated pairs:** 1/2

**When the scorer prefers one slide, do people agree?** 33/34 decisive pairs (rate 0.971, 95% CI 0.851–0.995); 4 ties or no meaningful score gap

| score gap | pairs | agree | rate | 95% CI |
|---|---|---|---|---|
| |Δ| < 5 | 2 | 2 | 1.0 | 0.342–1.0 |
| 5 ≤ |Δ| < 15 | 1 | 1 | 1.0 | 0.207–1.0 |
| |Δ| ≥ 15 | 31 | 30 | 0.968 | 0.838–0.994 |

**Score gap vs human preference:** Kendall τ-b 0.143 (95% CI -0.236–0.428, n=38 pairs). With n this small, read the interval, not the point estimate.

**Round status:** BLIND — independent validation

_Method:_ Preference = challenger wins / decisive votes, Wilson 95% interval (ties excluded; ties-as-half also shown). Agreement: percent agreement and Fleiss' kappa over {baseline, challenger, tie} on pairs rated by ≥2 evaluators. Human preference is an independent signal and is never part of the automatic composition score.
