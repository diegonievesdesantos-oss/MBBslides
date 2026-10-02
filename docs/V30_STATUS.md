# v3.0 status (3.0.0): the last version

> **Closed as 3.0.0 on 2026-10-02 (owner decision): the last version of the tool.**
> - Validated blind on the owner's real material.
> - Two clear bugs found there are fixed. No matching rule was tuned on that material.

The owner closed v2.5 and asked for one last version. Its only criterion is the owner's real material.
No new matching rule is written for it, and only clear bugs found on that material are fixed.

| # | step | who | status |
|---|---|---|---|
| 1 | Real material: 2–3 update cases (old deck + this year's sources) and 3–5 unseen corporate templates | owner | **done**: 3 cases, 3 templates |
| 2 | A key sheet per case, from its old deck (`scripts/validation_kit.py template`) | tool | **ready** |
| 3 | The owner keys each sheet without seeing the tool's output; sha256 recorded before the run (`seal`) | owner, then tool | **done** |
| 4 | One blind run per case (`score`); a sample deck built on each template, QA'd and rated by the owner | tool, owner | **done** (the owner's template ratings were not returned) |
| 5 | Fix only clear bugs; final guide, measured limits; 3.0.0 | tool | **done** |

## Privacy

- **Where the material lives.** All of it stays in `.private/`, which is excluded from the repository:
  - decks, sources, keys and templates;
  - per-case results;
  - sample decks built on the owner's templates.
- **What is published.** Only aggregate figures, worded and shown to the owner first.

## The key

One row per number the tool reads in the old deck. The owner fills three columns:

| column | value |
|---|---|
| estado | desactualizada / vigente / sin fuente / ignorar |
| valor nuevo | the new value in the deck's own units and scale (only when desactualizada) |
| de dónde | optional: the file that gives it, or "calculado" |

The kit was checked end to end on a used synthetic case:
- the template;
- a key filled from that case's known answers;
- the seal;
- the score, which matched the scorer used since v2.2 exactly.

Numbers the tool does not read cannot be keyed: in a picture, or a chart that is an image. On that case
the template listed 107 of the 111 numbers the case's author had keyed.

## Blind result on the owner's real material

- **The material.** 3 real update cases from the owner: an old deck, this year's sources (reports,
  spreadsheets, PDFs, emails, minutes, a large ERP export) and a short brief each.
- **The key.** The owner keyed each number of each old deck. The key file's sha256 was recorded before
  the tool ran on any case.
- **The run.** Once, with the published version (93ff9e7).

Everything specific to the cases stays private: material, key and per-case results. Only the aggregate
is published.

| real material, 3 cases (322 keyed numbers, 309 matched to the plan) | blind run |
|---|---|
| outdated numbers found | **59 / 216 (27%)** |
| "outdated" right | 59 / 79 (75%) |
| proposed value right | **16 / 59 (27%)** |
| "current" right | 11 / 25 (44%) |

**This is much worse than on synthetic cases.** On v2.5's sealed synthetic set the same tool found 68% of
the outdated numbers, with values right 76% of the time. What holds is that an "outdated" flag is
usually right.

**Why** (read after the run):
- **The new values are mostly model outputs, not stated figures.** Updating a business case means
  recombining several sources: a phase's actual cost, the next phase's offer, a subsidy, then the
  payback. The tool recomputes the arithmetic already in the deck; it does not build a model.
- **One case rests on aggregating a row-level ERP export** (tens of thousands of orders) by channel,
  region and customer. By design the tool does not aggregate row-level data without an analysis step
  (`cpe reason analyze`), and none was run here. It saw only the other sources.
- **One case took monthly rows as yearly figures,** for example a January row for an annual total. That
  is a bug (fixed below).
- **"Current" is right less than half the time:** it often confirms figures the owner's key changes.

## The two bugs fixed

1. **A monthly row is never the new value of a figure that is not monthly.**
   - A month's row is one written "2025-01". "2025-12-31" is a point in time, and "Sep 2026" is a date
     in a label. Both forms were tried as month rows first; both removed right values on the synthetic
     sets, and were narrowed.
   - On every synthetic set and the v1.8 project, the final rule loses no right value. It removes 4
     wrong ones on v2.5's sealed set.
2. **A corporate template the engine cannot use is said, not silent.** A 4:3 template is applied only as
   colours and fonts. That was documented in the brand's compatibility report, but a run still ended
   "PASSED" with no word of it. It is now:
   - a deck-level warning, `BRAND_TEMPLATE_NOT_USED`, in the QA report;
   - a line on screen at the end of the run.

**Measured again on the real cases.** This is **in-sample**: the bugs were found there.

| real material, 3 cases | blind run | after the two fixes |
|---|---|---|
| outdated numbers found | 59 / 216 | 55 / 216 |
| "outdated" right | 59 / 79 (75%) | 55 / 70 (79%) |
| proposed value right | 16 / 59 | 17 / 55 |
| "current" right | 11 / 25 | 11 / 25 |

## Templates

3 corporate templates the tool had not seen, each with an example deck. The same 12-slide test deck was
built on each.

| template | QA | template use |
|---|---|---|
| A (4:3) | passed, 99,8 | **not used**: 4:3 is not supported, so only its colours and fonts were applied. Now a visible warning |
| B (16:9) | failed, 83,2 | native cover, 11 adaptive slides; palette 97%, grid 100%. 12 overlaps with a decorative shape of the template, 1 label collision |
| C (16:9) | failed by one error, 98,2 | native cover, 11 adaptive slides; palette 98%, grid 100%; 1 label collision, no template artwork covered |

In all three, a waterfall chart cuts its axis labels. The owner's own ratings of the three decks were not
returned, so the judgement of brand fidelity is the tool's metrics only.

## What 3.0 leaves as limits

These were not fixed: they are new features, not bugs.
- Building a business-case model from several sources.
- Aggregating row-level exports without an analysis step.
- 4:3 corporate templates.
- Template artwork that content may cover (template B).

The guide [GUIA_ACTUALIZAR_DECK.md](GUIA_ACTUALIZAR_DECK.md) states how to work around each of these.
