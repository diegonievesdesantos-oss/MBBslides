# s2 — expert feedback (storyline A/B, blind, case set 02)

One expert evaluator (owner; expert single-rater standard). Four cases written after protocol 1.1 was frozen.
Result: **agent with protocol 1.1 wins 3–1** against the agent without the protocol (Wilson 95% CI 0.30–0.95).
Self-consistency was 2/2 after one correction. The owner corrected repeat r002 as a mis-click, and the
correction is recorded in the vote file with a `correction` field.

The owner confirmed the round is valid: vote times were 2–58 s because the storylines had been read
before voting.

| pair | case | preferred |
|---|---|---|
| p001 | almacén Valencia | protocol 1.1 ("almost a tie") |
| p002 | packaging, single supplier | **baseline** |
| p003 | SaaS, 30 AEs | protocol 1.1 |
| p004 | tiendas de proximidad | protocol 1.1 |

## Why (the evaluator's words, translated; mapped to systems after unblinding)

- **SaaS: protocol.** It turns the diagnosis into an approvable decision:
  - it rejects the 30 AEs with a figure (at most €4.5M in 2026, not €9M);
  - it proposes a sized, costed alternative;
  - it sets dated gates with thresholds before releasing more investment.

  The baseline gets the diagnosis right and adds NRR and a 2025-cohort rescue, but leaves the decision
  open ("a smaller first tranche").
- **Packaging: baseline.** The protocol storyline treats risk inconsistently. It charges all the stoppage
  cost (€4.0M) to the 100% option and none to 70/30. Yet with the split Supplier B still carries 70% of
  the volume on one plant, and the incumbent's cover only starts after two weeks. With the same risk
  applied to both options, the split's advantage disappears. The baseline compares the three options on
  the same basis, states its assumption, and protects continuity with signing conditions. The protocol
  run had better governance but recommends the wrong option because of a logic error.
- **Tiendas: protocol.** Both reach the same plan with the same numbers. The protocol run is more ready to
  execute:
  - confirm the break windows with legal;
  - a renegotiation gate in Q1, with closure at expiry as the fallback;
  - a restated EBITDA target.

  The baseline has the stronger message (94% of the benefit for a fifth of the cost), but leaves the
  renegotiation open with no plan B.
- **Almacén: protocol, almost a tie.** The protocol run leaves the decision ready to sign, with owners, the
  landlord's offer confirmed in writing and a 24-hour service KPI. The baseline has a more rigorous
  capacity analysis (it sees the whole network above 85%), but weaker governance.

## Reading

- **The 1.1 decision frame did what s1 asked for.** In three of four cases the expert preferred the run
  that closes with an approvable, governed decision: owners, gates with dates and thresholds, a fallback.
- **The loss is a reasoning error, not a missing section.** Options were compared on different bases
  (risk charged to one option only). The deterministic checks passed: every number was grounded and
  every option was costed, but not on the same cost components.
- **The case author made the same error.** The reference answer (C3, "70/30 is better") built in the same
  asymmetry. The expert is right; C3 is marked contested in `reference.json`.
- **Protocol 1.2 adds a same-basis check.** Each option lists its `cost_components`; options whose
  component sets differ are flagged (OPTIONS_DIFFERENT_BASIS). The RED TEAM critic asks whether each risk
  is applied to every option it touches.
- **Analysis depth is still uneven.** In almacén the baseline saw that the whole network passes 85%
  utilisation; the protocol run did not.

**Status: development data** from protocol 1.2 on.
