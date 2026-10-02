# Headline style (v3.1)

What the Action Title Engine accepts, for the person or agent writing the headline. The rules are in
`docs/ACTION_TITLE_ENGINE.md`; this is the short form.

1. **State what the slide means.** An action title is a takeaway, not necessarily an instruction:
   observation, diagnosis, causal conclusion, implication, recommendation and decision are all action
   titles.
2. **Write the proposition first, the headline second.** The proposition is what you assert (with its
   evidence ids); the headline is how you say it. Compress; never strengthen.
3. **One governing message.** A second claim goes to the body or to its own slide.
4. **Numbers only from the evidence, at the precision of the evidence.** "~1.4 pp" stays hedged; a
   derived figure (a difference, a share, a CAGR) is fine when the exhibit can produce it.
5. **Causal words need a causal claim.** On a correlation, say *is associated with*, *coincides with*,
   *is concentrated in* — *se concentra en*, *coincide con*.
6. **Superlatives need the comparison on the slide** (and must be true of its numbers).
7. **A finding is not a recommendation; a recommendation is not a decision.** "Option A has the highest
   NPV" ≠ "Choose Option A" ≠ "The board approved Option A".
8. **Keep scope, period and confidence.** Iberia ≠ all regions; 2026 ≠ 2025; a low-confidence finding
   says *may*, *suggests*, *podría*.
9. **Sentence case, no full stop, the deck's language.** Never a hybrid.
10. **Quantify when it strengthens the claim, not by reflex** (spec §112): "A fragmented ownership model
    prevents end-to-end accountability" can beat an irrelevant number.
11. **No consulting parody.** "Unlocking sustainable value through strategic transformation" says
    nothing; a precise plain sentence does.

| ✗ | ✓ |
|---|---|
| Revenue evolution | Revenue grew 12% in 2026, driven primarily by enterprise customers *(driver claim)* |
| 2026 EBITDA | EBITDA is €8m below plan despite revenue remaining on target |
| Implementation roadmap | Three waves can deliver the target model by Q4 2027 |
| Pricing opportunity | Pricing can recover ~1.4 pp of margin without reducing volume |
| Evolución de ventas | Las ventas crecieron un 12% en 2026 |
| Explain the causes of the margin decline | Electronics mix explains most of the 1.9 pp margin decline |

**Siblings are written as siblings** (docs/PARALLEL_WORDING.md): recommendations as *verb + object + to +
outcome* (*verbo en infinitivo + objeto + para + resultado*), process steps as instructions in one form,
executive-summary statements as declarative conclusions of similar weight.

Offer alternatives in `headline_candidates`; the engine picks the strongest faithful one.
