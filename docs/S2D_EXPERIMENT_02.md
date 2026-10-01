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

## End to end: SaaS case, raw sources → rendered deck

`runs/protocol_agent_02_deck/` takes the protocol-1.1 reasoning run of x2_saas_retention through passes
11–12 and the render loop:
- **Spec:** `deck.json`; every slide cites fact ids in `evidence`.
- **Checks:** `cpe reason check --enrich`, then `cpe run`.
- **Agent review:** the agent read the renders and fixed what a partner would reject. S3: the wrong bar
  drew the eye. S7: the autofix hid the €4.5M shortfall. S8–S9: wrapped headers, a pointless highlight.

**Result:** reasoning check PASS (0 errors, 0 hard failures). Render QA: 0 errors, 11 warnings (7 long
headlines, 3 two-message headlines, a dense executive summary). Deck score 95.0, composition 99.7. All 9
deck-plan headlines were kept word for word.

### Product gaps found (the v1.8 backlog for source → deck)

| # | gap | consequence |
|---|---|---|
| 1 | The fact checker compares against a fresh re-extraction, and fact ids are not stable across extractor versions | An extractor fix makes an older fact model fail as FACT_FABRICATED. Two unused year facts had to be removed here. |
| 2 | WRONG_SOURCE does not follow computed-fact lineage | A slide citing only C-facts cannot name the raw file. |
| 3 | The deck check grounds headline numbers only | Body text, KPIs, table cells, chart data and takeaways are not checked against cited facts. |
| 4 | Render QA reads numbers only after `--enrich`, which overwrites the claim text | Regenerating deck.json without re-enriching silently disables the headline proof. |
| 5 | The reasoning check and the board profile disagree on headline length | The plan's 22–29-word headlines pass one layer and warn in the other. |
| 6 | No way to mark an estimate or upper bound on a cell, bar or waterfall step; no footnote on a number | Estimates are written as text ("≤4.5", "est."), so the number formatting is lost. |
| 7 | Waterfall: no "grey all but the highlight"; the "neutral" palette is close to the totals | The default red and green deltas compete with the highlighted step. |
| 8 | No target or reference marker on a bridge | "Needed €5.6M" had to be faked as a final total. |
| 9 | Table + chart has no commentary slot | The empty space was filled by a full-width takeaway. |
| 10 | Table column widths are relative and undocumented | Setting one width causes wraps in the others. |
| 11 | No cause → effect exhibit | A process chart reads as steps, not causality. |
| 12 | No explicit n/a cell in grouped categories with missing values | |
| 13 | No decisions-table + timeline combination | The gate date cannot sit next to the decision. |
| 14 | Automatic waterfall labels ("−5.6 vs …") cannot be styled or turned off | It adds a second accent colour. |

**Fixed (v1.8):**
- **Gap 1:** ids are preserved on re-extraction, and fabrication is checked against the raw files.
- **Gap 2:** WRONG_SOURCE follows computed-fact lineage.
- **Gap 3:** every number on a slide is grounded.

On the SaaS deck, re-extraction kept all 55 cited ids and dropped 10 label cells ("Q1 2024", year
columns) that the old extractor read as numbers. The new check found one real uncited number (S9:
€10.4M, now cited). On the v1.7 development run (margin_recovery) it found two: freight €9M on s08 and
the totals row of the appendix table on s10.

Gaps 1–4 are factuality gaps, and 1 and 3 mattered most. A deck can pass every check with an unchecked
number in a table cell, and an extractor upgrade breaks old runs. They are the first items for v1.8.

## Protocol 1.2 rerun (development check, same cases)

Four new independent agents, protocol 1.2, frozen engine copy (`runs/protocol_agent_03_p12/`). These
cases were already used in s2, so this is a development check, not evidence.

| case | conclusions | traps | untraced | options on the same basis |
|---|---|---|---|---|
| almacén | 3/3 | 0 | 2 / 51 | yes (2 options, 8 components) |
| SaaS | 3/3 | 0 | 2 / 77 | yes (3 options, 4 components) |
| tiendas | 3/3 | 0 | 15 / 66 | yes (4 options, 4 components) |
| packaging | 3/3 | 0 | 3 / 35 | yes (3 options, risk scaled by volume share) |

- **The s2 packaging error does not recur.** Stoppage risk is charged to every option by its share of
  volume on Supplier B (100%: €4.0M, 70/30: €2.8M, status quo: €1.2M over three years). With that
  basis, full consolidation with a continuity safeguard comes out ahead. This is the same answer as
  the run the expert preferred, and the break-even risk (2.4× history) is made a gate.
- **The agents reported these tool problems, now fixed with tests:**
  - "0,048" and "€2.868M" were read as thousands;
  - "7.8 EUR M" and "EUR 7.8M" were not read as money;
  - "23–24%" did not ground;
  - a bare "10.4" did not match €10.4M;
  - formulas could not pick a fact's second value (now `F0062[1]`);
  - "/año" in a header became a YEARS unit;
  - "plantilla" and "plantearía" set a "plan" basis, while "propose" did not;
  - a malformed conflicts file crashed the check;
  - SLIDE_MERGE grouped the title and summary slides.
- **Still open:**
  - prose-vs-prose conflicts without a period are not detected (closure cost 1.5 vs 3.2 M€);
  - no unit conversion in formulas;
  - numbers written in words ("two stoppages") are not extracted.

## Second end to end: tiendas, in Spanish (protocol 1.2)

`x2_tiendas_proximidad_es/runs/protocol_agent_03_deck/`: the reasoning run is from the 1.2 rerun.
- **Checks:** reasoning check PASS, with every number on every slide grounded. Render QA: 0 errors.
- **Scores:** deck 98.4, composition 99.6.
- **The v1.8 markers worked:** `~1500`, `≤840`, a muted bridge with a highlight, `proof_label: false`.

**Found and fixed afterwards:**
- **A regression from the 1.2-rerun fixes:** "1.596 k€" was read as 1.596. Spanish thousands before `k€`/`M€`
  are thousands again, and "€2.868M" stays a decimal.
- **The footer:** it printed "Source:" in a Spanish deck; it now says "Fuente:" when `meta.language` is `es`.
- **The headline lint's Spanish verbs:** it was missing cuesta, costaría, cierra, rompen, aprobar and others.

**Still open:**
- No locale number formatting: Spanish decks need `thousands: false` or show "1,596".
- KPIs + commentary and KPIs + process have no layout.
- Table cells are compared unit-free, so "10 M€" against a k€ column needs a computed fact.
- **Editorial note from the agent:** per store, the 2024 group-B openings contribute more than the 2023
  ones, which weakens a ramp-by-age reading. The ramp claim rests on sales per m² growing 11% a year.
