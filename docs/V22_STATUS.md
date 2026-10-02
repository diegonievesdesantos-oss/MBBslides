# v2.2 status (2.2.0.dev0)

Goal: fewer numbers a person must trace by hand when updating a deck, and the blind validation on real
material still open since v1.9.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: 3–5 unseen corporate templates; 2–3 new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | One figure, one value across the deck: restatements of a figure on several slides follow one value | **done** |
| 3 | Projections and curves from their drivers: a growth series from its base and rate; a cumulative curve from flows in the sources | **done** |
| 4 | Precision of medium-priority conflicts (19/50 real in v2.1) | **done**: 18/38 |
| 5 | Headline proposals for sign and order claims; a larger superlative lexicon | **done** |

Most figures below are in-sample: they come from the v1.8 project (the "Albor" case), which the rules
were developed on. The one blind figure is in "Blind check on a sealed synthetic set" at the end.

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

## Blind check on a sealed synthetic set (items 2 and 3)

**The set.** An agent wrote 3 synthetic update cases in Spanish:
- a packaging line;
- a claims-automation programme;
- a gym-chain expansion.

Each has an old deck (9 slides, with tables and charts), 6 new sources, and a key for each of the 185
numbers of the old decks. The agent did not read the tool's code. The key was sealed (sha256) before
the tool ran. The set is fictional and stays private, like every case.

**The run.** It ran once, with 2.1.0 and with items 2–3 on the same inputs. The scorer was then fixed
twice, and both fixes were to the scorer only:
- it compared "21,0" with "21" as text;
- it read chart values with the wrong decimal mark.

The same outputs were then re-scored, without running the tool again. 161 of the 185 keyed numbers are
matched to a number of the plan. Most of the other 24 are phase indices ("fase 1"), which the tool
does not treat as figures.

| blind, 3 cases | 2.1.0 | items 2–3 |
|---|---|---|
| outdated numbers found | 20 / 110 | **26 / 110** |
| "outdated" right | 20 / 21 | 26 / 27 |
| proposed value right | 8 / 20 | **17 / 26** |
| "current" right | 6 / 8 | **6 / 13** |

**What this says:**
- **On unseen material the tool finds about 1 outdated number in 4,** against 54 of 68 on the
  project it was developed on. The gap is mostly in matching a deck number to its new source in the
  first place, before any of items 2–3 apply. That gap is the main open problem of the tool.
- **Items 2–3 help where they apply.** They bring 6 more outdated numbers found and nearly double the
  right proposed values (8 → 17). The growth series and the curve from source flows were recomputed
  right.
- **Items 2–3 also cost.** 5 more numbers are called "current" wrongly:
  - two decoys grouped with a figure of the same digits ("45 FTE" and "45 días");
  - points of a cumulative curve that already had their flows on the slide;
  - a projection's base.

  And one wrong direct match (a headline's "4,6 M€" investment matched to a 1,8 M€ saving) was
  propagated to its restatements: a group is only as right as its head.

**After the run** (so in-sample on this set too):
- A rule from the failures: two numbers written with different count units ("FTE", "días") are not
  one figure. "current" right went from 6/13 to 6/12.
- The set is now used. It is not run again as a blind test.

## Item 4: fewer false medium-priority conflicts

In v2.1, 19 of the 50 "medium" conflicts on the 7 keyed cases were real. Reading the false ones on the
development cases and the v1.8 project (not on the used holdout) gave two patterns:
- **A presentation on one side.** The deck being updated, or another earlier deck, sits among the
  sources. Its figures are what the update changes, not a source that disagrees. Now low.
- **Values 40% or more apart.** Every one of them was another quantity under the same words: a quarter
  against the year, a share against a level, a phase against the total. Every real conflict of the
  development cases rated medium was within 30%. Now low.

| "medium" flags that are real conflicts | v2.1 | v2.2 |
|---|---|---|
| development cases and v1.8 project | 15 / 34 | **15 / 25** |
| sealed holdout of v2.0 (used: a consistency check) | 4 / 16 | 3 / 13 |
| all 7 keyed cases | 19 / 50 | **18 / 38** |

- **Low** goes from 5/30 to 6/43 real, so a real conflict is now low more often. On the holdout, one
  real conflict moved from medium to low.
- **High** is 8/9.
- Detection, and so the groups found on each case, is unchanged: only the order a person reads them in
  changes.

**Limit.** A real budget overrun of 40% or more between a plan and an actual is now low. It still
appears in the list and in `review.xlsx`, only further down.

## Item 5: headline proposals for signs and orders, more superlatives

v2.1 flagged a flipped sign or order without proposing a headline. Now:

| claim | old headline | approved values | proposal |
|---|---|---|---|
| sign | "El proyecto ahorra 0,89 M€ al año" | −0,12 | "El proyecto cuesta 0,12 M€ al año" |
| order | "El ahorro de 1,2 M€ supera el coste de 0,9 M€" | 0,8 and 0,9 | "El ahorro de 0,8 M€ no alcanza el coste de 0,9 M€" |
| superlative by noun | "La fase 2 tiene el mayor ahorro neto" | 451 and 436 | "La Fase 1 tiene el mayor ahorro neto" |
| superlative by adjective | "La zona norte es la más económica" | 4,9 / 4,4 / 5,2 | "La Zona sur es la más económica" |

- **Sign.** The opposite verb comes from a fixed table (ahorra/cuesta, genera/consume, gana/pierde,
  crece/cae, sube/baja, aumenta/disminuye, mejora/empeora, aporta/resta, and the English forms), in
  the same person and tense. A verb form not in the table gets no proposal.
- **Order.** The opposite comparison: supera/no alcanza, por encima/por debajo, más que/menos que,
  superior/inferior, and the English forms. A tie gets no proposal.
- **Superlative by noun.** "Tiene / aporta / ofrece el mayor / menor X" needs no lexicon: the noun
  names the table row.
- **Superlative by adjective.** The lexicon now covers atractiva, valiosa, económica, costosa,
  rápida, lenta, grande, pequeña, plurals and English forms.

These are proposals for the reviewer, like every headline proposal. A rewrite that keeps the numbers
right can still argue something the author would not; the update report lists them.

**Limit.** An adjective with no measure behind it ("la más estratégica") is still not checked.
