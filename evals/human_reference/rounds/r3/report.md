# Human A/B preference — round r3

Evaluators: 1 · comparisons: 38

| scope | n | challenger wins | baseline wins | ties | challenger preference | 95% CI (Wilson) | ties as ½ |
|---|---|---|---|---|---|---|---|
| all | 38 | 9 | 1 | 28 | 0.9 | 0.596–0.982 | 0.605 |
| comparison `v1.4.0->v1.5.0rc1 fresh content` | 25 | 8 | 0 | 17 | 1.0 | 0.676–1.0 | 0.66 |
| comparison `v1.4.0->v1.5.0rc1 holdout-v2 content (development-known)` | 13 | 1 | 1 | 11 | 0.5 | 0.095–0.905 | 0.5 |
| archetype kpi_dashboard | 7 | 2 | 1 | 4 | 0.667 | 0.208–0.939 | 0.571 |
| archetype statement | 19 | 0 | 0 | 19 | None | None–None | 0.5 |
| archetype waterfall | 12 | 7 | 0 | 5 | 1.0 | 0.646–1.0 | 0.792 |

**Does the automatic score agree with people?** 5/6 decisive votes (rate 0.833, 95% CI 0.436–0.97)
**Left-side bias:** left chosen in 0.5 of decisive votes (95% CI 0.237–0.763)
**Inter-rater:** {"note": "one evaluator: agreement needs \u22652"}
**Self-consistency on repeated pairs:** 4/4

**When the scorer prefers one slide, do people agree?** 5/6 decisive pairs (rate 0.833, 95% CI 0.436–0.97); 32 ties or no meaningful score gap

| score gap | pairs | agree | rate | 95% CI |
|---|---|---|---|---|
| |Δ| < 5 | 3 | 2 | 0.667 | 0.208–0.939 |
| 5 ≤ |Δ| < 15 | 1 | 1 | 1.0 | 0.207–1.0 |
| |Δ| ≥ 15 | 2 | 2 | 1.0 | 0.342–1.0 |

**Score gap vs human preference:** Kendall τ-b 0.372 (95% CI -0.219–0.825, n=38 pairs). With n this small, read the interval, not the point estimate.

**Round status:** DEVELOPMENT DATA — used for calibration, not unbiased validation

_Method:_ Preference = challenger wins / decisive votes, Wilson 95% interval (ties excluded; ties-as-half also shown). Agreement: percent agreement and Fleiss' kappa over {baseline, challenger, tie} on pairs rated by ≥2 evaluators. Human preference is an independent signal and is never part of the automatic composition score.
