# External holdout and unseen corporate template — intake protocol (v1.5)

v1.5 has **no independent evidence of its own yet**. Everything the developer (human or agent) can
see or write is development data: the regression suite, the archetype battery, the example decks,
round r2 after `mark-used`, the holdout v2 findings, and the JET template. Two kinds of evidence can
only come from someone else; this document is how to hand them over.

```
EXTERNAL HOLDOUT: AWAITING INPUT
UNSEEN CORPORATE TEMPLATE: AWAITING USER-SUPPLIED TEMPLATE
```

`scripts/cpe holdout intake` prints the current status of both. It never runs anything.

## 1. External deck holdout

**What qualifies.** Deck specs (`*.json`, the public spec format, docs/SPEC_REFERENCE.md) written
by a person who

- is not the developer of the engine and did not ask the developer (or its agent) to draft them;
- has not seen renders of the v1.5 engine while writing;
- writes realistic consulting content: real headlines with a claim, the evidence they would put on
  a slide, any archetype mix. Bad decks are fine — they are evidence too.

10–30 decks, 6–15 slides each, is enough to report per-archetype numbers with coverage labels.
Anonymize anything confidential before handing it over (names, figures may be scaled).

**Where it goes** (gitignored, never pushed):

```
.private/holdouts/v15_external/
    decks/*.json
    PROVENANCE.json
```

```json
{
  "author_role": "e.g. strategy consultant, 6 years",
  "authored_by_developer": false,
  "engine_renders_seen_by_author": false,
  "received": "YYYY-MM-DD",
  "notes": "how the decks were written (from real projects, anonymized / from scratch)"
}
```

The runner refuses to run without a `PROVENANCE.json` attesting both `false` values: a deck the
developer wrote is never presented as external, whatever it is called.

**How it runs** (on the frozen release candidate only; never in CI):

```bash
scripts/cpe holdout intake                       # → EXTERNAL HOLDOUT: READY
scripts/cpe holdout v15-external --record        # private_results/v15_external/ + sanitized aggregate in latest.json
```

**Rules.**

- Run once per release candidate, on a clean, frozen commit. The engine is not tuned on the
  results in the same cycle; findings become development items for the next version.
- Only sanitized aggregates are recorded (counts, scores, archetype n/mean/min). Deck names,
  headlines, text, numbers and renders stay in `private_results/` and are never committed.
- After the run the decks are **development-known** for the next cycle and must be described so.

## 2. Unseen corporate template

**What qualifies.** A real corporate PowerPoint template (`.pptx` / `.potx` saved as `.pptx`) that
has never been used in this project's development. JET is development data since v1.3 and is
refused automatically (its hash is in `.private/holdouts/KNOWN_DEVELOPMENT.sha256`, hashes only).
Optionally a human-written brand guide and `expectations.json` (claims transcribed from it:
fonts, colours, layouts), as in `.private/holdouts/jet/`.

**Where it goes** (gitignored, never pushed):

```
.private/holdouts/v15_corporate/
    template.pptx
    brand_spec.*          (optional)
    expectations.json     (optional)
```

**How it runs:**

```bash
scripts/cpe holdout intake                       # → UNSEEN CORPORATE TEMPLATE: READY
scripts/cpe holdout v15-corporate --record
```

Outputs go to `private_results/v15_corporate/`. Nothing from the template — PPTX, logos, assets,
XML, renders, screenshots, text, brand guide — is ever committed; only the sanitized summary
(counts and rates: masters, layouts, classification confidence, font conflict yes/no, test-deck QA
verdict and composition, agreement with the brand guide) is recorded.

## What CI does

Nothing of this. GitHub Actions never sees `.private/`, has no secrets for it, and does not run
`holdout v15-*`, `holdout private`, `holdout external`, the sealed holdout v2 or any human report
(`tests/test_v15.py::test_ci_never_runs_private_or_human_validation`).
