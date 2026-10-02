# v2.3 status (2.3.0)

> **Closed as 2.3.0 on 2026-10-02 (owner decision).**
> - Items 2–5 are done.
> - Item 1 (blind validation on real material: unseen templates, new cases with the owner's key)
>   moves to v2.4.

Goal: find the numbers a deck must change on material the tool has not seen. In v2.2's blind check,
it found about 1 outdated number in 4 on unseen cases, against 4 in 5 on the project it was built on.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: unseen corporate templates; new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | Matching a deck number to its new source on unseen material | **done** (first round) |
| 3 | A fresh sealed synthetic set, written before item 2's work is measured on new cases, run once at the end | **done**: run once |
| 4 | Group heads: a weak match must not spread to every restatement | **done** |
| 5 | Fewer false "current": a restatement of the old plan or a figure with the same digits is no confirmation | **done** |

## The sets

| set | written by | cases | keyed numbers | use |
|---|---|---|---|---|
| v2.2 sealed set | an agent, sealed 2026-10-02 | 3 (ES) | 185 | used by v2.2: development now |
| v2.3 development set | another agent | 6 (4 ES, 2 EN) | 347 | development |
| v2.3 sealed set | a third agent, sealed 2026-10-02 | 4 (3 ES, 1 EN) | 308 | runs once, at the end of 2.3 |

- The agents did not read the tool's code. Every case is fictional and stays private (`.private/`,
  not in the repository).
- Sectors differ from the cases the tool was built on: airline maintenance, food manufacturing OEE,
  bank branches, e-commerce fulfilment, university admissions, hotels.
- Sources come in varied formats: prose reports, emails, minutes, long and wide CSVs, monthly tables,
  XLSX and markdown tables.

## Item 2: matching on unseen material

**Why the tool missed.** On the v2.2 set, 29 of the 84 missed outdated numbers had their new value in
the sources, but the matcher never paired them. It matched only on a closed list of about 25 measures
built on the logistics project of v1.8. A number about "socios", "expedientes" or "applications" had
no measure, so it stayed untraced. The other misses are figures no source gives, which only the deck's
own arithmetic can recompute.

**What changed.**

| rule | example |
|---|---|
| open measures: with no known measure, the words the number counts, else an acronym | "30.000 socios" ↔ "31.500 socios activos"; "OEE 72,5" ↔ "oee_pct 74,6" |
| a table cell's column says what it counts, its row which one | "Engineering · Offers" ↔ "Engineering, offers, 2900", not "applications" |
| a short caption above a table names its cells' measure and unit | "Capex por fase (k€)" over "Total · Fase 1: 2.800" |
| proper names must agree; in a sentence, the name nearest before the number | "Lugo … 72,5%, mientras Mérida … 61,2%" |
| a source figure for one named part ranks below one for the whole | the network's figure over Getafe's for an unnamed total |
| a benchmark is not the company's figure | "competitive set", "mediana del sector", "cuartil" |
| more forms of the known measures | "crecerán", "facturación", "growth", "headcount" |

**Measured.**

| | v2.2.0 | v2.3 item 2 |
|---|---|---|
| **v2.3 development set** (6 cases), outdated found | 30 / 255 | **123 / 255** |
| "outdated" right | 30 / 32 | 123 / 133 |
| proposed value right | 21 / 30 | **93 / 123** |
| "current" right | 4 / 5 | 13 / 24 |
| **v2.2 set** (3 cases, now development), outdated found | 26 / 110 | 32 / 110 |
| proposed value right | 17 / 26 | 24 / 32 |
| **v1.8 project**, outdated found | 54 / 68 | 54 / 68 |

How much of this is in-sample:
- The first rules (open measures, captions, more measure forms) were written on the v2.2 set before
  the development set existed. For them, the development set's figure is out of sample.
- The later rules (names, columns, benchmarks) were tuned on the development set.
- The honest figure for 2.3 will be the sealed set, run once at the end.

**What did not work.** Each was measured on the development set and dropped:
- Refusing a value when only the old plan restates it (an offer, a budget, a target). In these cases a
  budget approved this year often is the new value.
- Taking the measure only from the words next to the number in a sentence. It lost 5 finds on the v1.8
  project.

**Limits.**
- About 90 of the 132 outdated numbers still missed on the development set are figures no source
  gives. They need the deck's own arithmetic (totals, ratios, projections) to reach them, and that only
  works once their parts are found.
- A verb that names a known measure can mislabel a count ("crece hasta 30.000 socios" is read as
  growth).

## Items 4 and 5: safer groups, fewer false "current"

**Item 5: "current" only when the source really confirms the figure.**
- **The deck's precision.** A source within 1,5% used to confirm a number: 94,1% "confirmed" 93,2%,
  and 880 confirmed 870. Now the source must round to what the deck shows. A chart point is read at
  its series' precision: "−3" in a series of "−2,8" is −3,0.
- **Restatements.** A supplier's proposal or quote restates the old figure, like an offer or a budget.
- **Reminders.** "Os recuerdo", "como recordatorio", "reaffirmed", "the original offer" repeat what was
  agreed. When only such a text speaks to a number, it gets no new value.

**Item 4: a group follows a head only when the head is sound.**
- **A sentence's match leads only about its own measure.** A match in a sentence leads its group only
  when the source's measure is the one named right next to the number. In "ahorra 1,8 M€ … una
  inversión de 4,6 M€", the 4,6 had been matched to the saving.
- **A match on open words alone must be close.** With no known measure behind it, the value must be
  within 60% of the old one.
- **Labelled cells.** Two table cells or chart points whose labels name different things ("Horas de
  vuelo" and "Eventos AOG") are never one figure, whatever their digits.

| | after item 2 | after items 4–5 |
|---|---|---|
| **v2.3 development set**, outdated found | 123 / 255 | 116 / 255 |
| "outdated" right | 123 / 133 | 116 / 124 |
| proposed value right | 93 / 123 (76%) | **103 / 116 (89%)** |
| "current" right | 13 / 24 | **13 / 15** |
| **v2.2 set**, outdated found | 32 / 110 | 33 / 110 |
| proposed value right | 24 / 32 | 28 / 33 |
| "current" right | 10 / 15 | **9 / 9** |
| **v1.8 project**, outdated found | 54 / 68 | 54 / 68 (outdated right 54/57, current 11/12) |

Items 4 and 5 trade a few finds for right ones. Every proposal they removed on the development set was
wrong: a wrong proposal became "untraced", which a reviewer sees as work, not as an answer.

**What did not work.** "A total is not one phase's figure" lost right finds on the v1.8 project and
the v2.2 set, and was dropped.

## Blind result on the sealed set (items 2–5)

- **The run.** Once, after items 2–5 were done: 2.2.0 (a9c85bf) against 2.3 (a001616), on the 4
  sealed cases (308 keyed numbers). The seal was checked first: every key's sha256 matched the one
  recorded when it was written.
- **The scorer.** The same as for the development sets, fixed before this run.

| blind, 4 cases | 2.2.0 | 2.3 |
|---|---|---|
| outdated numbers found | 32 / 206 (16%) | **82 / 206 (40%)** |
| "outdated" right | 32 / 41 | 82 / 95 |
| proposed value right | 15 / 32 (47%) | 38 / 82 (46%) |
| "current" right | 7 / 14 | 14 / 21 |

**What this says:**
- **Finds.** The tool now finds 2,5 times more of the numbers a deck must change on unseen material,
  and its "outdated" flags are right more often (86% against 78%).
- **Proposed values are the overfit part.** On the development sets they were right 89% of the time.
  Blind, they are right less than half the time, no better than before. Finding which number changed
  generalises; picking its new value does not yet.
- **"Current."** It improves (14 of 21 right, against 7 of 14) but is still wrong a third of the time.

**Why the blind values are wrong** (read after the run, so this is diagnosis, not tuning):
- **One source sentence feeds many numbers.** A committee's "ahorro anual de 3,5 M€" became the new
  value of 5 different numbers of the deck. Nothing stops one source value from being assigned to
  several quantities.
- **Projections against another year's actual.** The 2025–2027 points of a spend projection took the
  2024 actual.
- **Weak heads still spread.** A headline's "4,5 M€" matched to 1,7 M€ led its group.

These are the starting points for v2.4. The set is now used and is not run again as a blind test.
