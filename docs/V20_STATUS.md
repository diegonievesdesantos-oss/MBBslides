# v2.0 status (2.0.0.dev0)

The goal of 2.0 is a tool that works on cases it has never seen. The release cannot close without the
owner's blind validation.

| # | item | status |
|---|---|---|
| 1 | Blind validation: 3–5 unseen corporate templates (run once, aggregates only); 2–3 new cases with the owner's key sealed beforehand, judged only against it | **needs the owner** |
| 2 | One update command: `cpe update` | **done** |
| 3 | Derived figures in `deck stale`: totals, net rows, ratios, repeated figures | **done** |
| 4 | Conflicts by definition (same quantity, different scope: management report vs ledger vs full cost) | not started |
| 5 | Rewrite slides whose message no longer holds (new headline and exhibit, keeping the layout) | not started; `update_report.md` already lists the headlines whose own figures changed |

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
