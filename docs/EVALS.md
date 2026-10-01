# Evaluation — independent signals that are never merged

```
DEVELOPMENT (regression + battery + examples + robustness)  ≠  SEALED HOLDOUT  ≠  HUMAN EVALUATION
```

v1.4 asks one question: **does MBBslides make good editorial decisions on slides it has never been
tuned on?** A single mean cannot answer it: in v1.3.3, an overall 87.5 coexisted with process and
comparison slides at 39 and text slides at 20–30. Every signal is therefore reported as a
**distribution across slide archetypes**, and the signals stay separate.

| | regression | robustness | holdout v2 | human reference |
|---|---|---|---|---|
| where | `evals/regression/cases/` (10 stress decks + 17-deck archetype battery) | `evals/robustness/seeds.json` | `evals/holdout/v2/` (sealed) | `evals/human_reference/rounds/` |
| role | development set: visible, drives changes | does a small content change collapse quality? | generalisation on unseen decks | do people prefer what the scorer prefers? |
| may drive changes? | yes | yes | **no** — findings go to the next cycle | evidence for patterns, never per-slide exceptions |
| gates CI? | relative baseline + absolute archetype gates | against its own baseline | **never runs in CI** | no |
| baselined? | yes | yes (catastrophic count) | **never** (the code refuses) | no |
| command | `cpe eval --suite regression` · `cpe quality` | `cpe robustness` | `cpe eval --suite holdout_v2 --release-candidate` | `cpe human …` |

There is deliberately **no** combined "quality = 93.7": signals of different nature and
reliability would be false precision. Example decks (Alvora, Gallery, Kestrel) are development
material and QA fixtures (`--suite examples`), **not** evidence of generalisation.

## Quality profile (every eval run)

`src/cpe/quality.py`, in `eval_report.md`, `latest.json` and the README:

| measure | why |
|---|---|
| `overall_score` | mean of deck scores — kept for continuity with v1.1–v1.3, no longer the headline |
| `macro_archetype_score` | mean of per-archetype means: many excellent tables cannot hide bad processes |
| `weakest_archetype` (+ score, n) | the family that needs work, named |
| P10 / P25 / median / P75 / P90 of slide fitness | P10 especially: ten bad slides cannot hide behind thirty excellent ones |
| share of slides ≥ 90 / 80 / 70 | |
| per archetype: n, mean, median, min, P10, flags, coverage, health | |
| `absolute_floor_breaches`, `not_healthy` | absolute expectations not met (below) |

**Coverage** decides how much a number may claim (`evals/archetype_gates.json`):
n < 5 → `INSUFFICIENT COVERAGE` (reported, never gated, never "healthy"); 5 ≤ n < 8 → provisional;
n ≥ 8 → gate-eligible. The 17-deck **archetype battery** (`scripts/make_archetype_battery.py`, 8–12
slides per archetype: counts, label length, density, English/Spanish, number formats, sources,
footnotes) exists so that every archetype is gate-eligible.

**Diagnostics.** Every run writes `archetype_diagnostics.md` (mean penalty per metric from the
score attribution, dominant flags, worst slides) and `archetype_sheets/sheet_<archetype>.png`
(worst slide first) for weak archetypes. A low score is a question — *is the slide bad, or is the
metric wrong?* — answered with the sheet and the attribution before anything changes
(docs/ARCHETYPE_DIAGNOSIS.md records the v1.4 answers).

## Absolute gates

A relative baseline protects against getting worse; it cannot see "bad then, equally bad now"
(process 39 → 40 is green). `evals/archetype_gates.json` adds absolute expectations per archetype:

| rule | value | status | rationale (abridged) |
|---|---|---|---|
| `min_floor` | 35 | **enforced** (gate-eligible archetypes) | below 35 a slide is broken in every archetype seen so far |
| `mean_floor` | 70 | provisional | engineering target; the editorial floor already used by candidate selection |
| `max_share_below_floor` | 25% | provisional | a quarter of slides below the floor is systematic |

Provisional rules are reported (`NOT HEALTHY`) but do not fail CI until human evidence says where
"acceptable" starts. CI also fails on **coverage regression** (an archetype losing slides against the
baseline). The CI job `quality_profile` renders the battery and runs `cpe quality … --check`.

## Robustness (metamorphic)

`src/cpe/robustness.py`: seeds are development slides; perturbations are small and deterministic —
headline +20%, body text +25% (translation length), process +2 steps, table ×1.5 rows, chart +2
series, "€1.2M" → "€1,200,000", one source → three, +1 list/KPI/column item. Measured per variant:
score delta, layout change, ≥ 2 pt font drop, new visual QA errors, new flags. **Catastrophic** = a
drop ≥ 25 points or a new visual QA error. Reported: median and P90 drop, catastrophic rate —
separate from the composition score. CI job `robustness` fails if catastrophic variants exceed
`evals/robustness/baseline.json`.

## Holdout v2 protocol

```
DEFINE schema → CREATE / FREEZE cases → SEAL hashes → DO NOT LOOK AT RENDERS
→ DEVELOP ON REGRESSION ONLY → FREEZE ENGINE → RUN HOLDOUT ONCE → REPORT
```

- 26 decks / 157 slides (board, financial, operations, transformation, market, product, sales,
  public sector, NGO; 10 Spanish, 16 English) were written and sealed (`SEAL.json`, SHA-256 per file)
  in commit `40a0589`, **before** any v1.4 engine, metric or profile change; validated with `plan` /
  `lint` only.
- **Limitation, stated plainly:** they were written by the same agent that develops the engine,
  after it had seen the v1.3.3 weak slides. This is *sealed evaluation data*, not a truly
  externally authored blind benchmark.
- The runner refuses unless `--release-candidate`, the seal verifies, the tree is clean (frozen
  engine) and the run is whole (no `--match`, no baseline). A second run for the same version on a
  different engine commit is refused (`--rerun-reason` only for a non-engine cause).
- If an archetype scores badly: record it, open a v1.5 development item, **do not** change
  thresholds or profiles and re-run. Correctness bugs found there are documented, fixed in the next
  cycle, and the recorded result is not re-run.
- Case files are never moved into the regression suite while they are the current holdout; after a
  release they may be retired like v1.

**Holdout v1 (H01–H05)** is retired as blind evidence (`evals/holdout/public/RETIRED.md`): the last
blind result is 81.0 at v1.2; later runs are development evidence (`--suite holdout_v1`).

### External and private holdouts

```
.private/holdouts/decks/*.json     deck specs kept outside GitHub (anonymized corporate examples …)
cpe holdout external [--record]    → private_results/external/; sanitized aggregates only; never baselined
.private/holdouts/<name>/…         corporate templates: cpe holdout private
```

The private corporate template used in v1.2 (JET) is **development data** since v1.3 (its findings
drove the v1.3 fixes); its sanitized summary is recorded as `development_private`, never as a
holdout. Nothing specific to it is published.

## Human reference (blind A/B)

```bash
scripts/cpe human serve evals/human_reference/rounds/r1          # http://localhost:8765
scripts/cpe human report evals/human_reference/rounds/r1 [--record]
scripts/cpe human import evals/human_reference/rounds/r1 votes.jsonl
scripts/cpe human build -o evals/human_reference/rounds/r2 --n 40 --quota process=6 … \
  --pair "name=BASELINE_RUNS_ROOT,CHALLENGER_RUNS_ROOT"
scripts/cpe human mark-used evals/human_reference/rounds/r1 --change "…"
```

- Blinding: random image names, left/right and pair order randomised per evaluator, no version,
  layout or score on the page; `key.json` is never served.
- **Statistics** (`report`): preference with a Wilson 95% interval, ties, per comparison and
  archetype, left/right bias, self-consistency on side-swapped repeats, inter-rater agreement
  (Fleiss' κ); v1.4 adds per-pair **scorer/human agreement** (agree / disagree / tie, overall and by
  score gap), **Kendall τ-b** between score gap and human preference with a percentile-bootstrap
  95% CI (small n: read the interval), controls, and `human_score_disagreements.md` — the pairs
  where the scorer strongly prefers one slide and people the other.
- Rounds carry `STATUS.json`. Once a round's votes drive an engine or profile change
  (`mark-used`), it is **development data** and every report says so. **r1** (40 pairs, v1.1.1 vs
  v1.2 configurations) is preserved unchanged and awaits votes. **r2** is built after the v1.4
  freeze from the sealed holdout decks rendered by v1.3.3 and v1.4 (content the engine was never
  tuned on), both re-scored by the v1.4 scorer, balanced over comparison, process, KPI hero, text
  exhibit, architecture and roadmap with control pairs. No vote is ever generated by the system.

### Calibration without Goodhart

Votes are used to find **patterns** ("people consistently prefer more whitespace on process slides
than the scorer allows") that justify a documented profile or metric change — never to make one
slide win. Profile changes follow `evals/profile_changes.md`.

## Single source of truth and provenance

`evals/results/latest.json` holds the current numbers: `regression` (overall, distribution,
archetypes, absolute gates), `examples`, `robustness`, `holdout.v2` / `holdout.v1_historical`,
`human_reference.rounds.{r1,r2}`, `development_private`, `environment`. Each release signal carries
`provenance` (`evaluated_commit`, `git_tree`, `dirty`, engine version, container digest,
environment fingerprint, UTC timestamp of the run). The README block is generated from it
(`cpe results readme`, checked in CI) and `cpe results verify` (CI) fails unless every release
signal was evaluated on a clean commit whose engine inputs equal HEAD's — see
docs/REPRODUCIBILITY.md#release-workflow.
