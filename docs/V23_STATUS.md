# v2.3 status (2.3.0.dev0)

Goal: find the numbers a deck must change on material the tool has not seen. In v2.2's blind check,
it found about 1 outdated number in 4 on unseen cases, against 4 in 5 on the project it was built on.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: unseen corporate templates; new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | Matching a deck number to its new source on unseen material | **done** (first round) |
| 3 | A fresh sealed synthetic set, written before item 2's work is measured on new cases, run once at the end | **sealed**; runs at the end of 2.3 |
| 4 | Group heads: a weak match must not spread to every restatement | open |
| 5 | Fewer false "current": a restatement of the old plan or a figure with the same digits is no confirmation | open |

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
- "Current" is right only about half the time (13/24). That is item 5.
- A verb that names a known measure can mislabel a count ("crece hasta 30.000 socios" is read as
  growth).
