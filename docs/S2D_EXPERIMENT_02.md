# Source-to-deck experiment 02: harder cases, protocol 1.1

**Date** 2026-10-01 · **Status** development. The cases were written by the developing agent after
protocol 1.1 was frozen and were not used to tune it. **Human verdict: protocol 1.1 wins 3–1** (round s2,
one expert, blind).

## Design

Four cases in `evals/source_to_deck/development/x2_*` (generator: `scripts/make_s2d_cases_02.py`):

| case | lang | sources | what makes it hard |
|---|---|---|---|
| almacén Valencia | ES | xlsx (3 sheets incl. notes), PDF, memo | The "€4.1M saving" is gross cost. Madrid lacks capacity. Transport, the extra shift and the overtime rate sit in a notes sheet. The closure cost is stated two ways (1.5 vs 3.2). |
| SaaS retention | EN | PDF board pack, CSV bridge, xlsx CRM, notes | The CRO blames a competitor, but the data says churn after an onboarding cut. The "€9M new ARR" ignores the 9-month ramp. |
| tiendas proximidad | ES | 40-row xlsx, PDF, memo | 3.6 M€ of allocated central cost stays after closing. The young stores contribute before allocation. Rent is stated on two bases (16% vs 14.5%). |
| packaging supplier | EN | DOCX, PDF, CSV invoices, note | The 12% applies to €23.9M, not €25M (rush freight). There is single-plant stoppage risk. Several options must be costed. |

The two systems were independent agents with fresh contexts, given only their copy of the brief and sources
(isolation instructed). **A** wrote the storyline template directly. **B** followed protocol 1.1:
`cpe reason facts/check/ghost`, iterating to a passing check, with the decision frame.

## Results

| case | conclusions A / B | traps A / B | untraced numbers A / B | B reasoning check | expert |
|---|---|---|---|---|---|
| almacén | 3/3 · 3/3 | 0 · 0 | 3 · 2 | PASS | B (almost a tie) |
| SaaS | 3/3 · 3/3 | 0 · 0 | 21 · 6 | PASS | B |
| tiendas | 3/3 · 3/3 | 0 · 0 | 3 · 4 | PASS | B |
| packaging | 3/3 · 3/3 | 0 · 0 | 19 · 7 | PASS | **A** |

The tiendas trap T2 initially fired for both systems. Its terms matched storylines that refute "cerrar las
40", so they were corrected.

## Reading

- **Automatic substance is still a tie.** Strong agents find the buried drivers in these cases too. The
  difference the expert saw is in the **decision**. The protocol runs close with approvable asks, owners,
  dated gates and fallbacks; that is the 1.1 decision frame, built from s1's feedback.
- **The loss is a reasoning error that passes every deterministic check.** In packaging, risk was charged to
  one option only. Protocol 1.2 makes option bases comparable (OPTIONS_DIFFERENT_BASIS).
- **The case author made the same error.** The reference conclusion C3 is marked contested: references
  written by the developing agent are not ground truth.
- **The protocol run did not always find everything the baseline found.** In almacén the baseline saw the
  whole network passing 85% utilisation.
- **The agents found five fact-model bugs**, all fixed with tests:
  - dot decimals in CSV and typed xlsx cells;
  - notes sheets not read as text;
  - snake_case unit headers;
  - year columns read as values;
  - false conflicts, 161 of them on tiendas.

## Limits

One rater, four cases, one run per system. The cases were written by the developing agent, so the 95%
interval (0.30–0.95) is wide. A 3–1 result is a direction, not a validation. The next evidence needs
external cases, more of them, and ideally a second rater.
