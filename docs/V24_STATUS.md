# v2.4 status (2.4.0.dev0)

Goal: pick the right new value. In v2.3's blind check the tool found 2,5 times more of the numbers a deck
must change, but the new value it proposed was right only 46% of the time, against 89% on the
development set.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: unseen corporate templates; new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | A fresh sealed set, stressing how a new value is chosen; run once at the end of 2.4 | **sealed** |
| 3 | One source value is the new value of one figure, not of five | **done** |
| 4 | The year of each figure: a projection's future points do not take a past actual; FY2023 does not replace FY2025 | open |
| 5 | Group heads: a weak match does not lead a group; members that disagree are flagged, not overwritten | open |

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
