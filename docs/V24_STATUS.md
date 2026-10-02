# v2.4 status (2.4.0)

> **Closed as 2.4.0 on 2026-10-02 (owner decision).**
> - Items 2–5 are done; blind, items 3–5 did not generalise.
> - Item 1 (blind validation on real material) moves to v2.5.

Goal: pick the right new value. In v2.3's blind check the tool found 2,5 times more of the numbers a deck
must change, but the new value it proposed was right only 46% of the time, against 89% on the
development set.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: unseen corporate templates; new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | A fresh sealed set, stressing how a new value is chosen; run once at the end of 2.4 | **done**: run once |
| 3 | One source value is the new value of one figure, not of five | **done** |
| 4 | The year of each figure: a projection's future points do not take a past actual; FY2023 does not replace FY2025 | **done** |
| 5 | Group heads: a weak match does not lead a group; members that disagree are flagged, not overwritten | **done** |

## The sets

| set | cases | keyed numbers | use |
|---|---|---|---|
| v2.2 sealed set | 3 | 185 | used: development |
| v2.3 development set | 6 | 347 | development |
| v2.3 sealed set | 4 | 308 | used once by v2.3: development now |
| **v2.4 sealed set** | 4 (1 EN) | 366 | sealed; runs once at the end of 2.4 |

Item 3 was written before the v2.4 sealed set existed, so the set is blind to it.

## Item 3: one source value, at most two figures

**The failure.** In v2.3's blind check, "El comité valida un ahorro anual en régimen de 3,5 M€" became
the new value of five different numbers of a deck. Each number was matched on its own, so nothing
stopped one source value from feeding several quantities.

**The rule.**
- All numbers are matched first; values are then assigned across the deck.
- The best-matched numbers (table cells first on a tie) take their source value.
- A source value may be the new value of at most two different figures. Restatements of one figure
  (3,2 M€ in the summary, 3.200 k€ in the table) count once and share it freely.
- A number that loses its first candidate takes the next one only if it matched nearly as well.
  Otherwise it stays untraced.

| | wrong values before | removed | right values lost |
|---|---|---|---|
| v2.3 sealed set (now development) | 44 | 10 | 0 |
| v2.3 development set | 13 | 3 | 0 |
| v2.2 set | 5 | 1 | 0 |
| v1.8 project | | | 0 (54/68 unchanged) |

**What did not work.** One source value per figure, strictly. It lost right values on every set (5 on the
v2.2 set, 6 on v2.3's sealed set) and 2 outdated finds on the v1.8 project. Allowing two figures kept
every right value.

## Item 4: the year of each figure

**The failure.** In v2.3's blind check, a projection's 2025–2027 points took the 2024 actual. Their
categories read "2025e", "2026e", "2027e", and the year reader needed a bare 2025.

**The rule.** Years are read in every written form, and a year on each side that differs is a clash:
- an estimate or forecast: 2025e, 2025F;
- a fiscal year: FY2025, FY25, and FY2024/25, 2024/25 or 2024-2025 (the year it ends);
- a price such as "2.025 €" is not a year.

**Measured.** On v2.3's sealed set (now development), 7 wrong proposed values removed and no right one
lost; no change on the other development sets or the v1.8 project.

**What did not work.** Preferring the latest year when the deck's number names none changed nothing
on any set, and was dropped.

## Item 5: weak heads, disagreeing restatements

**The failure.** A restatement with a plain (non-analysis) match led its group, and every other
restatement copied it. In v2.3's blind check, a headline's "4,5 M€" matched to 1,7 M€ was copied to
the table and the next steps.

**The rules.** For a group whose best member is a plain match (not derived by the deck's arithmetic,
not from an analysis):
- **Members that disagree are flagged, not overwritten.** When restatements found different values, no
  value is copied. Each keeps its own, and `review.xlsx`, `edits.md` and the review list show
  "restatements disagree" with every slide's value. The older pairwise "same figure" rule now respects
  this too.
- **A large jump does not spread.** A match that moves the figure by more than half does not speak for
  every restatement.

**Measured.** On v2.3's sealed set (now development), 6 wrong proposed values removed and no right one
lost. No change on the other development sets or the v1.8 project. On the v1.8 project the rule first
lost 4 finds, because it also stopped an analysis output from leading. It now applies only to plain
matches.

## Development sets after items 3–5

| | 2.3.0 | 2.4 items 3–5 |
|---|---|---|
| v2.3 sealed set (now development): found / value right | 82 / 38 (46%) | 59 / 38 (64%) |
| v2.3 development set: found / value right | 116 / 103 | 113 / 103 |
| v2.2 set: found / value right | 33 / 28 | 32 / 28 |
| v1.8 project: outdated found / value right | 54 / 24 | 54 / 24 |

Every proposal items 3–5 removed on these sets was a wrong value: a reviewer now gets "untraced" (work
to do) instead of a wrong number. Not one right value was lost. The v2.4 sealed set will say whether
this holds blind.

## Blind result on the v2.4 sealed set

- **The run.** Once, after items 3–5: 2.3.0 (9356cf6) against 2.4 (52caab0), on 4 sealed cases (366
  keyed numbers, 149 of them outdated). The seal was checked first. The scorer is unchanged.
- **Item 3 is blind here:** it was written before the set existed.

| blind, 4 cases | 2.3.0 | 2.4 |
|---|---|---|
| outdated numbers found | 88 / 149 | 84 / 149 |
| "outdated" right | 88 / 133 (66%) | 84 / 123 (68%) |
| proposed value right | 47 / 88 (53%) | 45 / 84 (54%) |
| "current" right | 47 / 49 | 46 / 49 |

**What this says.**
- **Blind, items 3–5 barely move anything.** They remove 6 false "outdated" flags and 2 wrong values,
  but also lose 2 right values and 4 finds.
- **They did not generalise.** On the development sets they removed only wrong values; blind, they
  remove right ones too. Proposed values stay right about half the time, as in v2.3.
- **The v2.3 tool does better on this set.** It finds 88 of 149 outdated numbers (59%), against 40% on
  v2.3's sealed set. Recall varies a lot from one set of cases to another, so a single set is a rough
  figure.

**Why it still fails** (read after the run, so this is diagnosis, not tuning):
- **Past actuals called outdated.** 34 numbers the key keeps valid were called "outdated". Most are past
  years' actuals in a chart ("ANR real 2022", "inversión real 2023").
- **The year check counts every year in the source sentence.** A source sentence that lists several
  years ("1,4 M€ en 2023, 1,8 M€ en 2024 y 2,3 M€ en 2025") counts as about all of them. The 2023 point
  can then take 2024's value. The year check needs the year next to the value, as v2.3 does for names.
- **A total takes a cumulative or another part.** "La inversión acumulada alcanza 5,5 M€" became the new
  value of a single year's investment.

This set is now used and is not run again as a blind test.
