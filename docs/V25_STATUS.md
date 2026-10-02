# v2.5 status (2.5.0.dev0)

Goal: the failures v2.4's blind check found: years, past actuals and cumulative figures. This is the
last round built on synthetic cases. After it, the open question is real material.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: unseen corporate templates; new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | A fresh sealed set stressing years, quarters and cumulative figures; run once at the end of 2.5 | **done**: run once |
| 3 | The year next to each source value; a chart point's own year | **done** |
| 4 | A past actual is not "outdated" | **done** |
| 5 | Cumulative against yearly figures | **done** |

## Item 3: each value its own year

**The failure.** v2.4's year check counted every year of a source sentence. In "La inversión ejecutada
fue de 1,4 M€ en 2023, 1,8 M€ en 2024 y 2,3 M€ en 2025", each value was "about" 2023, 2024 and 2025, so
the 2023 point of a chart could take 2025's 2,3.

**The deck side had the same failure.** A chart titled "real 2023–2024, previsión 2025–2028" made every
point about all those years.

**The rules.**
- **A source value's year** is the one named right after it ("1,4 M€ en 2023"), before the next figure
  and within the clause. Else it is the last one named before it since the previous figure ("en 2024,
  1,8 M€"). Else the period the fact extractor recorded.
- **A chart point's year** is its category's year.

## Item 4: a past actual is not "outdated"

**The failure.** On v2.4's sealed set, 34 numbers the key keeps valid were called "outdated". Most were
past years' figures. Their sources were long tables, "indicador, año, valor", where the year sits in a
column of its own. The tool read the year cell as one more value, and the other values of the row had
no year. A deck figure "at the close of 2024" could then take 2023's or 2025's row.

**The rule.** In a table, a column named año / anio / year / ejercicio / periodo / FY dates the values
of its row. The year cell itself is no longer a candidate quantity.

**What did not work.** "A target is updated only by a target" (an objective for 2030 is not changed by
this year's actual). It removed 2 false flags but lost 4 right values (3 on v2.4's set, 1 on v2.2's),
and was dropped.

## Item 5: cumulative against yearly

**The rule.** A figure the words next to it call cumulative ("acumulada", "a origen", "to date", "since
launch", "YTD") is matched only to cumulative source figures, and a period figure only to period ones.
This holds for any number, both ways. v2.2 applied it only to a cumulative chart's points against
yearly flows.

## Development sets after items 3–5

| | 2.4.0 | 2.5 items 3–5 |
|---|---|---|
| **v2.4 sealed set (now development)**, false "outdated" flags | 39 | **19** |
| "current" right | 46 / 49 | **62 / 64** |
| outdated found / value right | 84 / 45 | 79 / 48 |
| **v2.3 sealed set (development)**, found / value right | 59 / 38 | 55 / 37 |
| **v2.3 development set**, found / value right | 113 / 103 | 113 / 103 |
| **v2.2 set**, found / value right | 32 / 28 | 31 / 28 |
| **v1.8 project**, outdated found / value right | 54 / 24 | 54 / 24 |

- Most of the gain is on v2.4's set, whose failures these items were written from. It is in-sample.
- One right value was lost, on v2.3's set. The two half-year points "Ene–Jun 2026" and "Jul–Dic 2026"
  are now untraced: one had a right value, the other a wrong one.
- The v2.5 sealed set gives the blind figure (below).

## Blind result on the v2.5 sealed set

- **The set.** Written by an agent that did not read the code: 4 cases, 392 keyed numbers (airport
  ground handling, B2B software in English, a chemicals plant, outpatient care).
- **Items 3–5 are blind here.** They were committed before the set existed.
- **The run.** Once: 2.4.0 (b7ab79d) against 2.5 (d2abc9f). The seal was checked first.

| blind, 4 cases | 2.4.0 | 2.5 |
|---|---|---|
| outdated numbers found | 109 / 161 | 110 / 161 |
| "outdated" right | 109 / 135 (81%) | 110 / 132 (83%) |
| proposed value right | 78 / 109 (72%) | **84 / 110 (76%)** |
| "current" right | 67 / 70 | 70 / 72 |

**What this says.**
- **The first blind gain in three rounds,** and on every measure at once:
  - 6 more right values;
  - 3 fewer false "outdated" flags;
  - 3 more right "current".

  It is small: the items fix specific failures, and this set has fewer of them than v2.4's.
- **2.4.0 already did well on this set.** It found 68% of the outdated numbers, with values right 72%
  of the time. As noted in v2.4, the figures vary a lot from one set of cases to another.
- **The set is now used.** It is not run again as a blind test.
