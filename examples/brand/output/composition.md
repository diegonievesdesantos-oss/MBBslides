# Composition decisions

Scores are archetype fitness (qa/archetypes.py). Candidates with QA errors are rejected before scoring.

| slide | archetype | chosen | variant | score | vs default | rejected / inappropriate alternatives |
|---|---|---|---|---|---|---|
| s03 | chart | `exhibit_commentary_right` | — | 98.9 | +0.0 | — |
| s04 | chart | `kpi_strip_exhibit` | — | 97.2 | +0.0 | — |
| s05 | segmentation | `exhibit_takeaways_below` | — | 99.8 | +0.0 | — |
| s06 | waterfall | `waterfall_drivers` | — | 99.6 | +0.0 | — |
| s07 | table | `table_full` | — | 100.0 | +0.0 | — |
| s08 | matrix | `matrix_commentary` | — | 100.0 | +0.0 | — |
| s09 | operating_model | `exhibit_takeaways_below` | — | 100.0 | +0.0 | — |
| s10 | roadmap | `roadmap_full` | — | 100.0 | +0.0 | — |
| s11 | waterfall | `waterfall_full` | — | 100.0 | +0.0 | — |
| s12 | table | `exhibit_takeaways_below` | {'scale': 1.2, 'table_stretch': 0.6} | 100.0 | +27.6 | `exhibit_takeaways_below`  58.8 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.404 vs 0.0–0.2) |
