# Editorial fixtures (v3.1)

Fixtures for the Editorial Logic Layer (Action Title Engine + Parallel Wording Guarantee,
`docs/V31_SPEC.md`). They were written by authors who **did not read the engine's code**: only
the specification and the schema below. Two sets:

| set | path | use |
|---|---|---|
| dev | `evals/editorial/dev/*.json` | visible; used while building the engine |
| holdout | `evals/editorial/holdout/*.json` + `SEAL.json` | sealed (sha256) before the engine was run on it; run once at release, never used to tune |

Run: `cpe editorial eval --set dev` (or `--set holdout`, which verifies the seal first).

## Schema

Each file is a JSON list of cases. Three case types.

### `headline` — one slide, one headline against its proposition

```json
{
  "id": "EN-NUM-004",
  "type": "headline",
  "lang": "en",
  "tags": ["numeric", "invalid"],
  "slide": {
    "id": "s05", "kind": "content", "message_type": "trend",
    "purpose": "Show how revenue moved in 2026",
    "proposition": {"statement": "...", "role": "observation", "claim_type": "trend",
                    "subject": "revenue", "direction": "up", "magnitude": "12%", "timeframe": "2026",
                    "evidence_ids": ["F1"], "confidence": "high"},
    "headline": "...",
    "headline_candidates": ["optional", "alternatives"],
    "evidence": [{"id": "F1", "claim": "Revenue 2025 €100m, 2026 €112m", "values": [100, 112]}],
    "visual": {"type": "column", "data": {"categories": ["2025", "2026"], "series": [{"name": "Revenue (€m)", "values": [100, 112]}]}},
    "source": "Company accounts"
  },
  "deck": {"language": "en", "editorial_mode": "mbb_strict"},
  "expect": {"status": "failed", "codes": ["HEADLINE_NUMBER_UNSUPPORTED"], "selected": null}
}
```

- `expect.status`: `passed` (no hard editorial error on the slide) or `failed` (at least one hard error).
- `expect.codes` (when failed): the acceptable hard codes — the case is right if **any** of them is raised.
- `expect.selected` (optional): when `headline_candidates` are given, the exact text the engine must pick.
- `kind` may be `cover`, `divider`, `agenda`, `closing` for exemption cases (expect `passed` with a topic title).

### `parallel` — one sibling group

```json
{
  "id": "ES-PAR-003", "type": "parallel", "lang": "es", "tags": ["parallel"],
  "group": {"context": "recommendations", "explicit": true, "members": ["Consolidar proveedores para reducir complejidad", "..."]},
  "expect": {"status": "passed", "codes": []}
}
```

- `context`: `recommendations`, `process_steps`, `options`, `design_principles`, `exec_summary`, `key_line`, `roadmap_workstreams`, `cards`.
- `expect.status`: `passed` (no PARALLEL_* warning or error), `failed` (a PARALLEL_* error), `flagged` (a PARALLEL_* warning or error: the spec allows either).

### `sequence` — consecutive slides that must NOT be forced into one form

```json
{
  "id": "EN-SEQ-002", "type": "sequence", "lang": "en", "tags": ["non_parallel"],
  "deck": {"language": "en", "editorial_mode": "mbb_strict"},
  "slides": [ {"id": "s03", "kind": "content", "section": "K1", "story_role": "diagnosis", "proposition": {}, "headline": "..."} ],
  "expect": {"parallel_flags": 0, "headlines_unchanged": true}
}
```

## Hard codes (spec §14)

`HEADLINE_MISSING`, `HEADLINE_PLACEHOLDER`, `HEADLINE_TOPIC`, `HEADLINE_PROPOSITION_MISMATCH`,
`HEADLINE_NUMBER_UNSUPPORTED`, `HEADLINE_CAUSALITY_UNSUPPORTED`, `HEADLINE_COMPARISON_UNSUPPORTED`,
`HEADLINE_DIRECTION_MISMATCH`, `HEADLINE_TIMEFRAME_MISMATCH`, `HEADLINE_TWO_GOVERNING_MESSAGES`,
`HEADLINE_UNRESOLVED`, and `PROPOSITION_MISSING` (strict content slide with no proposition).

## Parallel codes (spec §28)

`PARALLEL_SIGNATURE_MISMATCH`, `PARALLEL_ROLE_MISMATCH`, `PARALLEL_TENSE_MISMATCH`, `PARALLEL_VOICE_MISMATCH`,
`PARALLEL_GRANULARITY_MISMATCH`, `PARALLEL_LENGTH_OUTLIER`, `PARALLEL_PUNCTUATION_MISMATCH`, `PARALLEL_NUMBERING_MISMATCH`.
