# Action Title Engine (v3.1)

`src/cpe/editorial/action_titles.py`. It accepts, rejects and selects wording for a proposition; it
does not write prose. `core/headline.py` (`lint_headline`) is its first layer and stays the planner's
independent check.

## The proposition (`proposition.py`)

```json
"proposition": {
  "statement": "Electronics mix explains 1.3 pp of the 1.9 pp gross-margin decline",
  "role": "diagnosis",            "claim_type": "driver",
  "subject": "gross margin",      "direction": "down",      "magnitude": "1.9 pp",
  "driver": "electronics mix",    "comparison": null,       "implication": "electronics is the first lever",
  "recommended_action": null,     "decision": null,         "timeframe": "2026",
  "scope": null,                  "qualifiers": [],
  "evidence_ids": ["F18"],        "analysis_ids": [],       "confidence": "high"
}
```

`role`: context · observation · diagnosis · driver · comparison · insight · implication · recommendation ·
decision · risk · status · impact · implementation. `claim_type`: fact · trend · comparison · composition ·
driver · causal · constraint · risk · opportunity · recommendation · decision · impact · status.

Validation: `PROPOSITION_MISSING` / `PROPOSITION_PLACEHOLDER` / `PROPOSITION_NO_LINEAGE` (no evidence or
analysis ids) / `PROPOSITION_EVIDENCE_UNRESOLVED` (ids not in the deck's evidence, facts, analyses,
key line or `meta.fact_model`) / `PROPOSITION_NUMBER_UNSUPPORTED` (the magnitude is not in the slide's
evidence) are hard; unknown role / claim type / confidence and `PROPOSITION_CAUSAL_TYPE` (the
statement itself uses causal wording on a non-causal claim) are soft.

## Headline types (spec §12)

From the proposition: factual · comparative · driver · causal · implication · recommendation · decision ·
risk · status. The observed type of a candidate is read from its form; an incompatible pair is
`HEADLINE_TYPE_MISMATCH` (soft, and a ranking criterion).

## Checks

Hard (errors in `mbb_strict`):

| code | when |
|---|---|
| `HEADLINE_MISSING`, `HEADLINE_PLACEHOLDER` | empty, TODO, `[…]` |
| `HEADLINE_TOPIC` | a label ("Revenue evolution", "2026 EBITDA"), the slide's purpose ("Explain…", "Mostrar…") |
| `HEADLINE_TWO_GOVERNING_MESSAGES` | two claims joined ("… and the board should …"; "…; separately, …") |
| `HEADLINE_NUMBER_UNSUPPORTED` | a number not in / derivable from the evidence: values, sums, differences, ratios, growth, CAGR, shares of a total, any 2–3 values together, a bridge's running total; tolerance = the precision written (½ unit of the last digit, ≥ 0.5%), 5% when hedged ("~1.4", "about") |
| `HEADLINE_DIRECTION_MISMATCH` | opposite direction, or the change stated without its direction ("changed by 1.9 pp") |
| `HEADLINE_TIMEFRAME_MISMATCH` | a period not in the proposition (a comparison base year from the evidence is allowed) |
| `HEADLINE_CAUSALITY_UNSUPPORTED` | causal wording (drives, causes, due to, because, provoca, se debe a, impulsa…) on a claim that is not `causal`/`driver`; attribution ("explains", "accounts for") also allowed for `composition`/`impact` |
| `HEADLINE_COMPARISON_UNSUPPORTED` | a superlative / comparative with no comparison claim, fewer than two items on the slide, or contradicted by the slide's numbers |
| `HEADLINE_PROPOSITION_MISMATCH` | magnitude changed; approximation made exact; scope widened ("all regions", a scope qualifier dropped); confidence overclaimed; entity substituted (a sibling entity of the evidence, an invented proper noun); comparison sides swapped; a finding worded as a recommendation; a recommendation worded as a decision (or as a decision already taken); nothing in common with the proposition |
| `HEADLINE_LANGUAGE_MISMATCH` | not the deck's language, or a hybrid ("Repricing electrónica unlocks…") |
| `HEADLINE_UNRESOLVED` | no candidate passes: fail closed, with the expected proposition in the message |

Soft: `HEADLINE_LONG`, `HEADLINE_WEAK_VERB` ("the chart shows"), `HEADLINE_VAGUE`, `HEADLINE_REDUNDANT`,
`HEADLINE_QUESTION`, `HEADLINE_TITLE_CASE` (unless `meta.editorial.capitalization: "title"`),
`HEADLINE_LOW_INFORMATION` (consulting-sounding phrases without a supported claim), `HEADLINE_SO_WHAT_WEAK`,
`HEADLINE_SUBJECT_IMPLICIT`, `HEADLINE_TYPE_MISMATCH`; deck level `HEADLINE_REPEATED_OPENING`.

## Diagnostic score (never overrides a hard failure)

proposition fidelity 25 · evidence support 25 · answer-first 15 · specificity 10 · so-what 10 ·
sentence structure 5 · concision 5 · wording hygiene 5. A 90/100 headline with unsupported causality
fails.

## Selection (spec §73)

Candidates: `headline` + `headline_candidates`. Ranked lexicographically by: hard validity → fidelity →
evidence support → correct type → one message → answer-first → specificity → so-what → concision →
hygiene; ties keep the current headline (so compiling twice changes nothing).

**Safe rewrite.** When no candidate passes for reasons of FORM (a label, a placeholder) and the
proposition is a `fact`/`trend` with subject, up/down direction, an exact magnitude and a past period,
the engine states it ("Revenue declined 8% in 2026"; Spanish only with an article-led subject: "Las
ventas cayeron un 8% en 2026"). The result goes through every check. It never adds a cause, driver or
implication, never words a projection (its tense is not determined), and never replaces a headline that
contradicts its proposition or evidence.

## The update workflow

`messages.review` decides; the ATE words. See `docs/EDITORIAL_LAYER.md`. `set_headline` edits carry
`proposition`, `editorial` (status, candidates, hard codes) and stay unapproved.
