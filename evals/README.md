# Visual-quality evals

`cases/` holds reproducible decks designed to break the engine. `cpe eval` generates, renders and
QA-checks each one, scores every slide with the composition metrics (`src/cpe/qa/composition.py`)
and compares with `baseline.json`.

| case | stresses |
|---|---|
| `01_sparse_content` | tiny tables, a lone KPI, a one-sentence slide (dead space) |
| `02_text_overload` | commentary / bullets / executive summary far over budget |
| `03_tables` | an 18-row table (split) and a wide heatmap |
| `04_charts_stress` | 7 series, 10-digit numbers, very long labels, a pie with 8 slices |
| `05_spanish` | Spanish content, decimal commas, accents |
| `06_diagrams_dense` | 6-layer operating model, 10-row roadmap, 14-item matrix, wide org chart |
| `07_waterfalls` | 12 drivers, subtotals, truncated axis |
| `08_headlines_structure` | long two-line headlines, comparison columns, statements |

```bash
scripts/cpe eval                         # FAILED (exit 1) on: crash, render failure, more QA errors,
                                         # composition drop > 2 pts (deck) / 4 pts (slide), new flags
scripts/cpe eval --update-baseline       # accept an intended change (commit baseline.json with it)
```

`results/` keeps the reports per version and [`v1.0_vs_v1.1.md`](results/v1.0_vs_v1.1.md), where
both engines' renders are scored with the same metrics. To add a case, drop a deck spec in
`cases/` with an `"eval": {"purpose": "…"}` block and update the baseline.
