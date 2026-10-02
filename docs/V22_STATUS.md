# v2.2 status (2.2.0.dev0)

Goal: fewer numbers a person must trace by hand when updating a deck, and the blind validation on real
material still open since v1.9.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: 3–5 unseen corporate templates; 2–3 new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | One figure, one value across the deck: restatements of a figure on several slides follow one value | **done** |
| 3 | Projections and curves from their drivers: a growth series from its base and rate; a cumulative curve from flows in the sources | **done** |
| 4 | Precision of medium-priority conflicts (19/50 real in v2.1) | open |
| 5 | Headline proposals for sign and order claims; a larger superlative lexicon | open |

All figures below are in-sample: they come from the v1.8 project (the "Albor" case), which the rules
were developed on. There is no new blind figure yet.

## Item 2: one figure, one value

Before, the fase-1 investment "3,2 M€" of the v1.8 project was handled four ways on four slides:
- 4.034 k€ on slide 2 (the analysis output);
- 3,52 M€ on slide 5 (a management report);
- untraced in the plan table of slide 6 and the recommendation of slide 10.

A reviewer had to find and fix each restatement by hand.

**How a group is built.** Numbers join one group when, pairwise:
- they have the same value at some scale (3,2 M€ = 3.200 k€), to the precision each is written with;
- they are the same kind (a level, a share, a multiple) and the same sign;
- they are about the same phase, zone or option, when both say. In a sentence this is the one named
  right after the number ("2,4 M€ en la fase 2"), else the nearest one before it ("fase 1 (3,2 M€)");
- they are about the same measure, when both say. The words right around the number decide ("39 FTE"
  is headcount even after "productividad").

A number that does not say what it is (a recommendation's "por 3,2 M€") joins only as a figure with
2 or more significant digits, next to a member that says. Two cells of one table, or two points of one
chart, are never one figure.

**Which value the group follows**, in order:
1. a figure the deck's own arithmetic derives (a total, a ratio);
2. a figure an analysis output gives;
3. a table cell;
4. any direct match.

At review, the member the reviewer approved leads instead. Approving the plan table's fase-1 cell moves
slides 2, 5 and 10, and the row total, at once. A member whose own match said something else (slide 5's
3,52 M€) keeps that value as an alternative: in `review.xlsx`, in `edits.md`, and in the update report
under "One figure, one value".

**Measured on the v1.8 project** (in-sample, owner's key):

| | v2.1 | v2.2 item 2 |
|---|---|---|
| outdated numbers found | 41 / 68 | **51 / 68** |
| "outdated" right | 41 / 44 | 51 / 54 |
| proposed value right | 17 / 25 | **24 / 31** |
| "current" right | 11 / 11 | 11 / 11 |

Approving every firm proposal and applying: 56 edits applied, 0 failed. The fase-1 investment reads
4,03 M€ on slides 2, 5 and 10, and 4.034 in the table.

**Limits.**
- A group follows its head: when the head is wrong, so is every member. The direct match a member had
  is shown as an alternative so the reviewer sees the disagreement.
- When the head is a total the deck cannot recompute (one of its parts has no value), the group keeps
  each member's own match.

## Item 3: projections and curves from their drivers

In v2.1, a projection and a cash curve stayed for review unless the slide showed their flows. Three
derivations now recompute them from what drives them. Each is accepted only when it holds in the old
deck, to the precision its numbers are written with.

| derivation | when | each point |
|---|---|---|
| growth | a chart series whose last 3+ points grow at a rate the slide states (its headline's percentage, or the one in the series name) | the previous point × (1 + rate) |
| payback curve | a cumulative cash curve whose last 3+ points are exactly −investment + n × annual savings, with an investment figure and a savings figure of the deck | −investment + n × savings |
| flows in a source | a cumulative curve the deck cannot recompute, and one source that gives the yearly flows for every year of it | the running sum of those flows |

Some details:
- **Growth.** A point with its own new value (this year's actual, a new forecast) keeps it. The points
  after it grow from it at the new rate.
- **Flows in a source.** The analysis comes first, then any source that is not a restatement of the
  old plan. Two equally ranked sources with different flows give no proposal: that is a conflict for
  a person.
- A point of a cumulative curve is no longer matched to one year's flow: a year's flow is not the
  running total to that year.

**Measured on the v1.8 project** (in-sample):

| | after item 2 | after item 3 |
|---|---|---|
| outdated numbers found | 51 / 68 | **54 / 68** |
| "outdated" right | 51 / 54 | 54 / 57 |
| proposed value right | 24 / 31 | 24 / 31 |
| "current" right | 11 / 11 | 11 / 11 |

The 3 new finds are the demand projection of slide 4 (2028–2030). They now grow from 2027's new
forecast at the new rate (3%), and the chart reads 4,51 / 4,65 / 4,80 M lines instead of
5,34 / 5,66 / 6,00. Approving every firm proposal and applying: 59 edits applied, 0 failed.

The project's cash curve (slide 7) still cannot be recomputed, and stays flagged:
- no source gives yearly flows;
- its tail rises 1,486 M€ a year, which is no figure of the deck. The table's net savings are
  1,495 M€, so the curve does not follow the simple payback model exactly.

The tool does not guess a curve that the deck's own figures do not reproduce.

**Limits.**
- The rate quoted in a series name ("+6%/año") is not rewritten when the rate changes. The headline
  is, and the update report lists the slide's headline for checking.
- A growth base or a curve's investment that no source updates must be approved by the reviewer
  before the projection moves.
