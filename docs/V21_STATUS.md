# v2.1 status (2.1.0)

> **Closed as 2.1.0 on 2026-10-02 (owner decision).**
> - Items 2–5 are done.
> - Item 1 (blind validation on real material: unseen templates, new cases with the owner's key)
>   moves to v2.2.

Goal: less review work for a person, and the blind validation on real material that v2.0 left open.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: 3–5 unseen corporate templates; 2–3 new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | Less noise in conflicts: priority, dismiss with a reason, decisions kept across runs | **done** |
| 3 | A review sheet instead of editing JSON | **done** |
| 4 | More headline claims checked: comparisons, sign, order | **done**: superlative, sign, order, payback year |
| 5 | Cumulative series (cash curve): recompute from flows, or flag as not recomputable | **done** |

## Item 2: which conflicts to read first

On the development cases, magnitude did not separate real conflicts from noise: "high" by size was 36%
right, against 40% for "medium". Two features did separate:
- a tangle of 3–5 versions from different sources: 7 of 9 right;
- a conflict involving the analyst's own analysis outputs: 4 of 29 right. The analysis is the
  correction, so its difference from a source is expected.

| priority (all 7 cases with keys) | flags that are real conflicts |
|---|---|
| high | **8 / 10** |
| medium | 19 / 50 |
| low | 5 / 30 |

The rule was built on the 3 development cases and the v1.8 project. The sealed holdout of v2.0 had
already been run once and is used, so its share of these numbers (high 2/3, medium 4/16, low 1/1) is a
consistency check, not a blind test.

**Commands:**
- `cpe reason conflicts WORK` lists conflicts by priority, each with its state: open, resolved or
  dismissed.
- `--dismiss X004 --why "…"` dismisses one. The reason is required and is kept.
- `--resolve X001 --use F0123 --why "…"` records the fact used.

Re-running `reason facts` (new sources) re-detects and keeps every decision:
- a group that gained a version keeps its review;
- a reviewed conflict that is no longer detected stays, marked `stale`.

## Item 3: the review sheet

`cpe update old.pptx sources -o work` writes `work/review.xlsx` beside `edits.md`. The columns to fill
are in colour, with drop-downs:

| sheet | one row per | the reviewer fills |
|---|---|---|
| Changes (Cambios) | proposed edit, and every number left for review | approve yes/no, corrected value, comment |
| Headlines (Titulares) | slide whose message changed | approve the proposal, or your own headline |
| Conflicts (Conflictos) | conflict, by priority | use / dismiss, the fact to use, the reason |
| Slides (Diapositivas) | slide | keep / delete / rebuild |

- `cpe update --read-sheet work` reads it back. `--apply` does it on its own when the sheet is newer than
  `edits.json`.
- Rows are matched by a hidden key, so sorting or filtering is safe.
- Problems are reported and not applied: a value that is not a number, an approval without a value,
  a dismissal without a reason, a fact that is not one of the conflict's.

**On the v1.8 project:**
- **Sheet:** 105 change rows, 4 headlines, 47 conflicts, 11 slides.
- **Review:** filled with the owner's key values, then read back:
  - 21 approved, 9 corrected, 1 added;
  - 29 low-priority conflicts dismissed with a reason;
  - slide 7 deleted, slide 6 marked for rebuild.
- **Apply:** 37 edits, 0 failed.

## Item 4: more claims a headline makes

Besides thresholds ("se pagan en menos de 5 años"), `messages.md` now reads four more kinds of claim.
Each is checked against the slide's own numbers, and only when it was true of the old values; else it
is not a claim about them.

| claim | example | checked against | proposal when it no longer holds |
|---|---|---|---|
| superlative | "la fase 2 es la más rentable" | the row of the measure (rentable → payback lowest, IRR or net savings highest; barato / caro → cost; productivo → productivity), across the entities of the slide's table, total column excluded | the actual winner substituted ("la Fase 1 es la más rentable") |
| sign | "ahorra 0,89 M€", "genera…", "crece…" | the new value of that figure | none: the argument flipped |
| order | "el ahorro de 1,2 M€ supera el coste de 0,9 M€" | the new values of both figures | none |
| payback year | "la inversión se recupera en 2030" | the first year the slide's cumulative curve is ≥ 0 | the new year |

**On the v1.8 project:**
- **Slide 6:** "la fase 2 es la más rentable" still holds (payback 5,8 against 9,2). "Menos de 5 años"
  no longer holds.
- **Slide 7:** "se recupera en 2030" cannot be checked: its curve cannot be recomputed (item 5).

## Item 5: cumulative series

A cumulative series is recognised by its name ("caja acumulada", "cumulative").
- **When the slide also shows its flows** (a series whose values are the year-on-year differences),
  each point becomes "previous point + this year's flow". Approving the new flows recomputes the curve,
  and with it the payback year.
- **When it does not**, every point is marked "not recomputable from the deck", with the reason, in the
  plan and in `update_report.md`. A new curve then needs the analysis, or values approved point by
  point. Before, these points were a silent "untraced".

On the v1.8 project, the 10 points of the cumulative cash curve (slide 7) are flagged so.
