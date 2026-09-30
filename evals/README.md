# Evaluation data

Three layers with different roles — see [docs/EVALS.md](../docs/EVALS.md) before adding anything.

| folder | role | command |
|---|---|---|
| `regression/cases/` + `regression/baseline.json` | development set; gates CI | `scripts/cpe-docker eval --suite regression` |
| `holdout/public/` + `SEAL.json` | sealed unseen cases; reported, never tuned on or baselined | `scripts/cpe-docker eval --suite holdout` |
| `human_reference/rounds/` | blind A/B rounds and votes | `scripts/cpe human serve …` / `report …` |
| `results/latest.json` | the single source of truth for current numbers (README is generated from it) | `--record`, `cpe results readme` |
| `results/history/` | frozen reports of past versions (v1.0, v1.1, v1.1.1 in the pinned environment) | — |

Regression cases:

| case | stresses |
|---|---|
| `01_sparse_content` | tiny tables, a lone KPI, a one-sentence slide |
| `02_text_overload` | commentary / bullets / executive summary far over budget |
| `03_tables` | an 18-row table (split) and a wide heatmap |
| `04_charts_stress` | 7 series, 10-digit numbers, very long labels, a pie with 8 slices |
| `05_spanish` | Spanish content, decimal commas, accents |
| `06_diagrams_dense` | 6-layer operating model, 10-row roadmap, 14-item matrix, wide org chart |
| `07_waterfalls` | 12 drivers, subtotals, truncated axis |
| `08_headlines_structure` | long two-line headlines, comparison columns, statements |
| `09_numbers_currencies` | $, €, £, ¥, negative values, long numbers, several sources per slide |
| `10_archetypes` | one slide per archetype at its natural density (statement, KPI hero, dense table, matrix, roadmap, sparse process, timeline, KPI dashboard) |

Holdout cases (H01–H05: hospital operations, energy transition, Spanish retail, SaaS board pack,
public-sector programme) were written and sealed before the v1.2 metric work.
