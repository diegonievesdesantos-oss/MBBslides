# v2.0 status (2.0.0)

> **Closed as 2.0.0 on 2026-10-02 (owner decision).**
> - Items 2–5 are done.
> - Item 1 (blind validation on real material: unseen templates, new cases with the owner's key)
>   moves to v2.1.

The goal of 2.0 is a tool that works on cases it has never seen. The release cannot close without the
owner's blind validation.

| # | item | status |
|---|---|---|
| 1 | Blind validation: 3–5 unseen corporate templates (run once, aggregates only); 2–3 new cases with the owner's key sealed beforehand, judged only against it | **needs the owner** |
| 2 | One update command: `cpe update` | **done** |
| 3 | Derived figures in `deck stale`: totals, net rows, ratios, repeated figures | **done** |
| 4 | Conflicts by definition (same quantity, different scope: management report vs ledger vs full cost) | **done**: versions of one quantity across sources; blind result below |
| 5 | Rewrite slides whose message no longer holds (new headline and exhibit, keeping the layout) | **done**: `messages.md`, `set_headline`, `cpe update --rebuild` with `replace_slide` |

## Updating a deck

```
cpe update old.pptx sources/ -o work      # facts, plan, proposed edits (work/edits.md)
#   review work/edits.json: approve ("approved": true), correct "replace", add edits for untraced numbers
cpe deck edits work --derive              # optional: see totals / ratios recomputed from what you approved
cpe update --apply work -o new.pptx --mark --accept-derived
```

- Analyses recorded with `cpe reason analyze work script.py` before `cpe update` are part of the facts.
- Re-running `cpe update` keeps every approval and correction.
- `--accept-derived` applies only figures computed from approved values. A figure with a part not yet
  approved stays a provisional proposal.

## Versions of one quantity across sources (item 4)

`reason facts` now also finds a quantity given with different values in different files. One project
cost can appear as 3,52 M€ in the management report, 3,74 M€ in the ledger and 4,03 M€ in the full
cost. The causes are scope, basis (plan vs actual), cut-off, restatement or a competing estimate.
Each group is one conflict listing all its versions (`fact_conflicts.json`, types `plan_vs_actual`,
`definition_mismatch`, `value_mismatch`). A deck that uses one of them must record which value it
uses and why.

**How it was measured.** Two agents wrote synthetic but realistic cases. Each case has messy memos,
emails, controller notes, CSV exports and ledgers in Spanish and English, with planted conflict groups
and decoys.
- **Development:** 3 cases with visible keys, used to build the rules. Their contents and keys are in
  `.private/defconf/`.
- **Sealed:** 3 cases in other industries (retail, hospitals, software). Their keys were never read.
  They were run once on the committed engine (`1d368a5`), with no change after the run. Only the
  aggregates are reported here, and the holdout is now used.

| | previous engine (0b5b558) | 2.0.0.dev0 |
|---|---|---|
| sealed: conflict groups found | 0 / 14 | **7 / 14** |
| sealed: flagged groups that are planted conflicts | 0 / 3 | **7 / 20** |
| sealed: decoys flagged | 0 | **0** |
| development: groups found | 3 / 14 | 11 / 14 |
| development: flagged groups correct | 5 / 16 | 15 / 23 |
| v1.8 project (in-sample): groups found | 1 / 5 | 3 / 5 |

**Read it as follows:**
- Half of the planted conflicts are found on unseen material, where none were before.
- About one flag in three is a planted conflict.
- The other flags are not decoys (0 decoy hits). They are pairs the keys do not list. In the
  development cases many of them are defensible (the same savings restated in an email; an old offer
  vs a new one). They still cost review time.

The list is a review aid, not a verdict.

**Not paired, by design:**
- a part and its row total, a month and a year, a per-unit figure and a total;
- a change and a level, a threshold, a value cited "from" or "frente a";
- two rows of two data exports, two outputs of the analyst's own model.

## Slides whose message no longer holds (item 5)

`cpe update` reads every headline against the new values: approved edits, figures derived from them,
and the numbers found current. Each slide gets a verdict in `work/messages.md`:

| verdict | meaning | what is proposed |
|---|---|---|
| holds | no headline figure changed, no claim contradicted | nothing |
| figures updated | the headline's own figures changed; its claims still hold | the headline with the new figures (the number edits apply them) |
| no longer holds | a threshold claim ("menos de 5 años", "más del 20%", "supera …") held with the old values and fails with the new | a mechanical rewrite as a `set_headline` edit, unapproved |
| check | a headline figure is outdated or untraced, with no approved value | nothing: a person decides |

To rebuild a slide whose argument changed, run `cpe update --rebuild work [--slides 4,6]`:
- It writes `work/rewrite/deck.json` with those slides, taken from the old deck's native rebuild with
  every approved value and the proposed headline.
- You edit the headline and the exhibit there and run it again.
- It builds the slides with the brand learned from the old deck itself and proposes `replace_slide`
  edits.

On `--apply`, the rebuilt slide takes the old one's place in the original file:
- It sits on the old slide's own layout, with the old slide's page-number placeholder.
- Placeholders become plain shapes with their geometry and style written out.
- Learned repeated shapes, charts and pictures are copied.
- The rest of the file is untouched.

**On the v1.8 project:**
- **Slide 6** ("Las dos fases se pagan en menos de 5 años") is found to no longer hold: payback
  4,4 / 3,1 → 9,2 / 5,8. The total column is not one of "las dos fases".
- **Proposed headline:** "Las dos fases se pagan en 9,2 y 5,8 años; la fase 2 es la más rentable".
- **The rebuilt slide 6:**
  - passed QA (92, 0 errors);
  - sits in the original deck with its footer, logo and page number;
  - carries its source line and the business case with every approved and derived figure.
- **Slide 2:** its figures were updated (6,65 M€ · 0,89 M€ · 7,5 años).
- **Slides 3, 4 and 7:** marked "check" (14%, 6% and 7,8 M€ have no approved value).

The mechanical rewrite is a lead, not a message. "La fase 2 es la más rentable" is not checked
(superlatives are not read).

## Measured (v1.8 project, owner's key; in-sample: the case is development data)

| | 1.9.0 | 2.0.0.dev0 |
|---|---|---|
| outdated numbers found | 33/66 | 41/68 |
| status "outdated" correct | 33/36 | 41/44 |
| status "current" correct | 11/11 | 11/11 |
| proposed new value right | 15/23 | 17/25 |

The denominators grew because durations ("3,7 años") are now read as figures.

The larger effect comes after the review. Once the components are approved (capex 4.030 / 2.616, FTE
12 / 14,6, net savings 440 / 450, maintenance -210 / -203), these follow, with no hand edits:
- the table totals (6.646, 26,6, -413, 890);
- the payback by phase (9,2 / 5,8);
- the summary KPIs (6,65 M€, 0,89 M€, 7,5 años);
- the sentence "reduce 26,6 FTE".

The headline of the summary slide is listed for rewriting.

## Limits

- A relation is used only when it holds exactly in the old deck. A total is recomputed only when all its
  parts have a new value: nothing is guessed.
- Cumulative series (a cash curve) need flows the deck does not show. They stay for review.
- About 40% of the outdated numbers still have no proposal before review. They are figures no new
  source restates and no arithmetic in the deck derives (unsourced history, the growth narrative).
