# v1.9 status (1.9.0, 2026-10-02)

> **Closed as 1.9.0 on 2026-10-02 (owner decision).**
> - Blocks B (unseen templates) and C (blind cases against the owner's key) move to v2.0.
> - A, D1 and D2 are done.
> - Every measured figure is in-sample on the v1.8 project.

The owner's instruction: "empieza con A, D las dos, solo contra mi clave".
- **A:** the tool debts.
- **D:** both features.
- **Measurement:** only against the owner's answer key, with no comparison to the previous protocol.

| block | what | status |
|---|---|---|
| A | Tool debts U1–U9 from the v1.8 real project | done: U1–U6, U8, U9 fixed; U3 partly (1 of 5 conflict groups); see [DEBT_V18.md](DEBT_V18.md#status-in-190dev0-2026-10-02) |
| D1 | Update the original pptx in place, changing only what needs changing | done: `cpe deck edits` → review → `cpe deck patch` |
| D2 | Learn corporate layouts from a hand-made deck's slide geometry (U7) | done: `brand ingest` learns them when no layout has a title placeholder |
| B | 3–5 unseen corporate templates | **needs the owner** (templates) |
| C | 2–3 new blind cases for protocol 1.5, judged only against the owner's key | **needs the owner** (cases and keys) |

## What the numbers mean

Every figure in this cycle comes from the v1.8 project (Albor). Since v1.8 that case is
development data, and the fixes were developed against its key. These figures show the fixes work on
the case they came from. They do **not** show the fixes generalise. Block C is the test that can.

| measure (Albor, owner's key) | v1.8 | v1.9 |
|---|---|---|
| `deck stale`: old numbers called current that are still valid | 7/56 | 11/11 |
| `deck stale`: old numbers called outdated that are outdated | 19/36 | 33/36 |
| `deck stale`: proposed new value right (where the key gives one) | 1/7 | 15/23 |
| `deck stale`: outdated numbers found (recall) | 19/66 | 33/66 |
| conflicts between sources: real / false | 0 of 5 groups / 1 | 1 of 5 groups / 0 |
| corporate layouts used in the updated deck | 0/12 | 12/12 |
| render errors in that deck | 16 | 0 |
| in-place patch of the old deck (reviewed edits) | — | 23 applied, 0 failed |

`deck stale` is still a review list, not a change plan.
- About half of the outdated numbers stay `untraced`, mostly derived figures that no new source
  restates.
- 8 of 23 proposed values would be wrong if applied unreviewed.

That is why `deck patch` applies only approved edits.

## Updating a deck (1.9)

```
cpe deck ingest old.pptx -o work           # what the old deck says, every number with its location
cpe reason facts sources -o work           # the new fact model
cpe deck stale work                        # current / outdated / untraced / ignored, per number
cpe deck edits work                        # work/edits.json: proposed edits, approved: false
#   review edits.json: approve, correct "replace", add replace_text / set_chart / delete_slide / note
cpe deck patch old.pptx work/edits.json -o new.pptx --mark
```

For a rebuild in the old deck's style, run `cpe brand ingest old.pptx -o brand`. If the deck uses free
text boxes, it now learns the layouts too.

## What needs the owner

- **B:** 3–5 corporate templates the engine has never seen.
  - They stay in `.private/`.
  - Only sanitized aggregates are published.
- **C:** 2–3 new real or realistic cases, each with an old deck if possible, and the owner's answer key
  sealed before the run.
  - They will be judged only against the key.
