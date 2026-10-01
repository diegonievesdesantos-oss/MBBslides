# Composition decisions

Scores are archetype fitness (qa/archetypes.py). Candidates with QA errors are rejected before scoring.

| slide | archetype | chosen | variant | score | vs default | rejected / inappropriate alternatives |
|---|---|---|---|---|---|---|
| S2 | waterfall | `waterfall_drivers` | — | 98.2 | +0.0 | — |
| S3 | table | `table_full` | — | 100.0 | +0.0 | — |
| S4 | table | `table_commentary` | {'scale': 1.2, 'table_stretch': 0.6} | 100.0 | +56.4 | `table_commentary`  43.6 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.442 vs 0.0–0.2); content uses too little of the canvas (utilization 0.553 vs 0.75–1.0); `exhibit_commentary_right`  43.6 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.442 vs 0.0–0.2); content uses too little of the canvas (utilization 0.553 vs 0.75–1.0) |
| S5 | waterfall | `kpi_strip_exhibit` | — | 100.0 | +0.0 | — |
| S6 | table | `table_full` | {'scale': 1.2, 'table_stretch': 0.6} | 100.0 | +2.2 | — |
| S7 | process | `process_commentary` | — | 98.6 | +0.0 | — |
| S8 | table | `table_full` | {'scale': 1.2, 'table_stretch': 0.6} | 100.0 | +42.1 | `table_full`  57.9 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.385 vs 0.0–0.2); content uses too little of the canvas (utilization 0.615 vs 0.75–1.0); `exhibit_full`  57.9 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.385 vs 0.0–0.2); content uses too little of the canvas (utilization 0.615 vs 0.75–1.0); `comparison_table`  57.9 — technically compatible with the content, but the composition is inappropriate for this content volume / table archetype: a large area is left empty (empty 0.385 vs 0.0–0.2); content uses too little of the canvas (utilization 0.615 vs 0.75–1.0) |
