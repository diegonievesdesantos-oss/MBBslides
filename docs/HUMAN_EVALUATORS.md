# Adding human evaluators to a round (r3 and later)

> **Owner decision (2026-10-01):** one expert rater (the owner, an experienced strategy consultant)
> is the human-evidence standard. r3 is closed and development data since v1.7. Additional raters
> are optional: the tools below remain for future rounds, and their results are reported per rater
> and pooled.

Human evidence so far comes from **one** evaluator. Round r3 (v1.4.0 vs v1.5.0rc1, 38 pairs + 4
repeats) is reopened so that **2–4 more people** vote on exactly the same pairs. The pairs are not
changed. Its key has been in the repository since `0b1556b`, so additional evaluators must **not**
receive the repository: they receive a self-contained **voting package** (images, page and a
small server; no key, no scores, no versions).

## For the project owner

1. Build the package (already built for r3: `r3_voting_package.zip`):

   ```bash
   scripts/cpe human package evals/human_reference/rounds/r3 -o r3_voting_package.zip
   ```

2. Send the zip to each evaluator, separately. Good evaluators: people who read or make business
   presentations (consultants, managers, analysts). Do not tell them which version is which, what
   changed, or how you voted; ask them not to discuss votes with each other until all have voted.
3. Each evaluator returns one file, `votes/<their-id>.jsonl`. Put the files anywhere and import:

   ```bash
   scripts/cpe human import evals/human_reference/rounds/r3 path/to/<their-id>.jsonl
   ```

   (Windows: `py -m cpe human import ...` with `$env:PYTHONPATH="src"`.) Importing twice is safe.
4. Commit the votes (`evals/human_reference/rounds/r3/votes/*.jsonl`) and push; the report is
   regenerated with `scripts/cpe human report evals/human_reference/rounds/r3 --record`.

## What the report then shows

| statistic | meaning |
|---|---|
| per rater (`by_rater`) | each person's preference, ties, left share, self-consistency |
| pooled | all decisive votes of all raters, Wilson 95% interval |
| **within-rater** self-consistency | the same person on side-swapped repeats (noise of ONE person) |
| **between-rater** agreement | percent agreement and Fleiss' κ on pairs rated by ≥ 2 people |
| scorer ↔ human | per-pair agreement and Kendall τ between score gap and preference (directional only) |
| identical controls (new rounds only) | tie rate on pairs of two identical images: evaluator noise; reported, never used to discard a rater |

Several votes by the same person count as **one** rater (the last vote per pair).

## After all evaluators have voted

Only then may r3 be marked development data (`cpe human mark-used`) and used for calibration —
the KPI-dashboard profile decision and the waterfall scorer study wait for this.

## Next rounds

`cpe human build ... --identical-controls 4` adds identical-image control pairs. New rounds keep the
key private (`.private/human_reference/keys/<round>/`) and are distributed as voting packages from
the start.
