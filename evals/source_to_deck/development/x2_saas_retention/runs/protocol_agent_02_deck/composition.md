# Composition decisions

Scores are archetype fitness (qa/archetypes.py). Candidates with QA errors are rejected before scoring.

| slide | archetype | chosen | variant | score | vs default | rejected / inappropriate alternatives |
|---|---|---|---|---|---|---|
| S3 | waterfall | `waterfall_drivers` | — | 99.7 | +0.0 | — |
| S4 | chart | `kpi_strip_exhibit` | — | 99.9 | +0.0 | — |
| S5 | chart | `exhibit_pair` | — | 100.0 | +0.0 | — |
| S6 | process | `process_full` | — | 100.0 | +0.0 | — |
| S7 | waterfall | `waterfall_drivers` | — | 98.8 | +0.0 | — |
| S8 | table | `exhibit_pair` | — | 100.0 | +0.0 | — |
| S9 | table | `table_commentary` | {'scale': 1.2, 'table_stretch': 0.6} | 100.0 | +51.5 | `table_commentary`  48.5 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.423 vs 0.0–0.2); content uses too little of the canvas (utilization 0.577 vs 0.75–1.0); `exhibit_commentary_right`  48.5 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.423 vs 0.0–0.2); content uses too little of the canvas (utilization 0.577 vs 0.75–1.0) |
