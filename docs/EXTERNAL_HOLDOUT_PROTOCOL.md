# External validation intake — protocol (v1.6)

v1.6 asks one question: **does the existing engine generalise outside data authored, inspected
or calibrated by its own development loop?** Everything the developer (human or agent) has seen or
written is development data (docs/EVALS.md, first table). Three kinds of evidence can only come
from someone else:

| evidence | status | where |
|---|---|---|
| additional human raters on r3 | **AWAITING EXTERNAL INPUT** | docs/HUMAN_EVALUATORS.md |
| external deck holdout | **EXTERNAL HOLDOUT: AWAITING INPUT** | `.private/holdouts/external/` |
| unseen corporate template(s) | **UNSEEN CORPORATE TEMPLATE: AWAITING USER-SUPPLIED TEMPLATE** | `.private/holdouts/corporate_unseen/<name>/` |

`scripts/cpe holdout intake` prints the current status. It never runs anything.

## The frozen engine

External evidence is collected on the **v1.6 release candidate**: branch `release/v1.6.0rc1`
(commit `0c20ce7`; engine commit `f7e96d3`). Development of v1.7 continues on `main` and never
touches that branch. To run intake on the frozen engine:

```bash
git fetch origin release/v1.6.0rc1
git worktree add ../mbbslides-v16 origin/release/v1.6.0rc1
cp -r .private ../mbbslides-v16/          # intake folders are gitignored: copy them across
cd ../mbbslides-v16 && scripts/cpe holdout intake
```

## 1. External deck holdout

**Who may author it.** A human consultant, another team member, or another AI agent with **no
access to MBBslides internals** (not the agent developing it), or an external benchmark. Give the
author docs/EXTERNAL_AUTHOR_BRIEF.md and docs/SPEC_REFERENCE.md — nothing else: no regression
slides, no holdout-v2 failures, no profile details.

**Strict order.**

```
AUTHOR CASES → RECEIVE FILES → PLACE IN .private/holdouts/external/ → SEAL (hashes)
→ DO NOT RENDER OR OPEN IN THE ENGINE → RUN ONCE ON THE FROZEN TAG → REPORT
→ NO SAME-VERSION TUNING; failures become development items of the next version
```

```
.private/holdouts/external/
    decks/*.json
    PROVENANCE.json        authored_by_developer: false, engine_renders_seen_by_author: false
    SEAL.json              written by external-seal (never rewritten)
```

```bash
scripts/cpe holdout external-seal               # immediately on arrival
scripts/cpe holdout external-run --record       # on the frozen tag; refuses a second run per engine version
```

The runner refuses: missing or non-independent provenance, an unsealed or broken seal, a dirty
engine, a second run for the same engine version. Only sanitized aggregates are recorded; deck
names, text, numbers and renders stay in `private_results/` and are never committed. After the run
the decks are development-known for the next cycle.

## 2. Unseen corporate template(s)

**What qualifies.** A real corporate PowerPoint template never used in this project's
development. JET is development data permanently and is refused automatically (hash list in
`.private/holdouts/KNOWN_DEVELOPMENT.sha256`). One template is the v1.6 minimum; 3–5 different
ones are the v1.8 target. Optionally a human-written brand guide and `expectations.json`.

```
.private/holdouts/corporate_unseen/<name>/
    template.pptx
    brand_spec.*          (optional)
    expectations.json     (optional)
```

```bash
scripts/cpe holdout corporate-run --record      # on the frozen tag, once per engine version
```

No manual brand correction before the first run. Measured: masters, layouts, layout-family
confidence, font inference and theme-vs-observed conflicts, palette, reserved artwork, placeholder
semantics, native / adaptive / fallback layout rate of a representative deck, visual QA, font
warnings, render failures. Nothing from the template — PPTX, logos, assets, XML, renders,
screenshots, text, brand guide — is ever committed; only the sanitized summary.

## What CI does

Nothing of this. GitHub Actions never sees `.private/`, has no secrets for it, and does not run
`holdout external-*`, `corporate-run`, `holdout private`, the sealed holdout v2 or any human report
(`tests/test_v15.py::test_ci_never_runs_private_or_human_validation`).
