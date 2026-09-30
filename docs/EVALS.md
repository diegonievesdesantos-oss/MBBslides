# Evaluation — three signals that are never merged

```
DEVELOPMENT DATA (regression)   ≠   HOLDOUT DATA   ≠   HUMAN EVALUATION
```

v1.1 adjusted two metrics after looking at the renders of its own benchmark (`emphasis` became
focal regions; `hierarchy` stopped penalising big figures). Those changes may have been right,
but they show the benchmark was starting to act as a training set. v1.2 separates the roles.

| | regression | holdout | human reference |
|---|---|---|---|
| where | `evals/regression/cases/` | `evals/holdout/public/` (+ private corporate holdouts in `.private/holdouts/`, never in git) | `evals/human_reference/rounds/` |
| role | development set: visible, used while building | unseen cases: measures generalisation | independent ground truth: do people prefer what the score prefers? |
| may drive changes? | yes | **no** (see protocol) | no — it is evidence, not a loss function |
| gates CI? | yes, against `evals/regression/baseline.json` | no | no |
| baselined? | yes (`--update-baseline`) | **never** (the code refuses) | no |
| command | `cpe eval --suite regression` | `cpe eval --suite holdout` · `cpe holdout private` | `cpe human build / serve / import / report` |

The README reports the three separately. There is deliberately **no** "overall score": combining
signals of different nature and reliability would be false precision.

## Regression suite

Ten decks designed to break the engine: sparse content, text overload, small/large tables, many
series and long numbers, Spanish, dense diagrams, waterfalls, long headlines, currencies and
negative numbers with several sources, and one slide per archetype at its natural density.
A run fails (exit 1) on a crash, a render failure, more QA errors than the baseline, a composition
drop > 2 points (deck) or > 4 points (slide), or a new composition flag.

## Holdout protocol

1. Holdout cases are written **before** the metric work of a cycle and sealed
   (`evals/holdout/public/SEAL.json` holds their SHA-256; a test fails if a case changes).
2. They are not run while weights, thresholds or archetype profiles are being set.
3. They run at the end of a milestone / release candidate, with the rules frozen.
4. **If a holdout case performs poorly, report it. Do not tune weights, thresholds or archetype
   profiles to make it pass in the same cycle.** A structural problem becomes an input to the
   next iteration (CHANGELOG "Holdout findings").
5. Correctness bugs (a crash, a false hard-QA error) may be fixed, are documented as holdout
   findings, and the recorded holdout result is **not** re-run to benefit from the fix.
6. New holdout cases replace consumed ones between cycles; once a case has influenced a decision,
   it moves to the regression suite.

### Private corporate holdouts

```
.private/holdouts/<name>/template.pptx       real corporate template (git-ignored)
.private/holdouts/<name>/brand_spec.*        human-authored brand specification (optional)
.private/holdouts/<name>/expectations.json   claims transcribed from that spec (optional)
cpe holdout private [--record]               → private_results/<name>/ (git-ignored)
```

Measures theme detection, font inference, palette inference, layout classification and geometry,
asset detection, placeholder detection, brand-rule inference, slide-layout matching and render
fidelity; compares **what the PPTX contains → what CPE infers → what the human-written spec says**.
Only a sanitized summary (counts and rates; no names, colours, text or assets) may be recorded in
`evals/results/latest.json`. Public CI never runs it (the folder does not exist there) and the
runner skips cleanly.

## Human reference (blind A/B)

```bash
scripts/cpe human build -o evals/human_reference/rounds/r2 --n 40 \
  --pair "name=BASELINE_RUNS_ROOT,CHALLENGER_RUNS_ROOT" [--pair …]
scripts/cpe human serve evals/human_reference/rounds/r1      # http://localhost:8765
scripts/cpe human report evals/human_reference/rounds/r1 [--record]
scripts/cpe human import evals/human_reference/rounds/r1 votes.jsonl
```

- Pairs are the same slide rendered by two configurations (matched by deck + slide id; identical
  renders are skipped). The page shows two slides side by side, **left/right randomised** per
  evaluator and pair, **pair order randomised** (seeded by the evaluator id so a resumed session
  keeps its order), no version, layout name, composition or QA score. Choices: A, B, Tie
  (keys ←/1/A, →/2/B, T/↓/0).
- Each evaluator gets an anonymous id (kept in the browser; type it again to resume on another
  machine). Every vote is written immediately to `votes/<id>.jsonl`; the page resumes where it
  stopped. `key.json` (which image is baseline / challenger) is never served by the page.
- Round `r1`: 40 pairs (38 + 2 side-swapped repeats for self-consistency) over three comparisons:
  `engine-v1.1.1-vs-v1.2`, `default-layout-vs-composed` and
  `universal-score-vs-archetype-selection`. Designed for 1–3 evaluators and ~15 minutes.

**Statistics** (`report`): challenger wins, baseline wins, ties; challenger preference among
decisive votes with a **Wilson 95% interval** (good coverage at small n and near 0/1; ties
excluded, ties-as-half also shown); per comparison and per archetype; number of comparisons and
evaluators; left-side bias with its interval; self-consistency on repeated pairs; inter-rater
agreement on shared pairs (percent agreement and **Fleiss' κ** over {baseline, challenger, tie});
and the question this signal exists for — **how often the automatic score agrees with people**
on decisive votes where the scores differ by ≥ 1 point.

Human preference is recorded under `human_reference` in `evals/results/latest.json` and is never
used in the automatic score (a test enforces it). Note: `key.json` is committed so the report is
reproducible; evaluators should not open it before voting.

## Single source of truth

`evals/results/latest.json` holds the current numbers (regression, examples, holdout public and
private summary, human reference, environment). The README block between the metrics markers is
generated from it (`cpe results readme`) and CI fails if they disagree. Frozen numbers of past
releases stay in CHANGELOG.md and `evals/results/history/`.
