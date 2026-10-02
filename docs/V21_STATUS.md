# v2.1 status (2.1.0.dev0)

Goal: less review work for a person, and the blind validation on real material that v2.0 left open.

| # | item | status |
|---|---|---|
| 1 | Blind validation on real material: 3–5 unseen corporate templates; 2–3 new cases with the owner's key sealed beforehand | **needs the owner** |
| 2 | Less noise in conflicts: priority, dismiss with a reason, decisions kept across runs | **done** |
| 3 | A review sheet instead of editing JSON | **done** |
| 4 | More headline claims checked: comparisons, sign, order | not started |
| 5 | Cumulative series (cash curve): recompute from flows, or flag as not recomputable | not started |

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
