# Visual guide — every exhibit type, its data shape and its rules

All exhibits accept: `title`, `unit` (shown as "**Title**, unit"), `format`
(`{decimals, prefix, suffix, percent, thousands, plus}`), `highlight` (categories, series,
items or labels to emphasise — everything else is greyed), `annotations`.
Charts are **native PowerPoint charts** (data editable in PowerPoint); tables are native
tables; diagrams are native shapes. Working examples of every type: `examples/gallery/deck.json`.

## Charts (native)

| type | data | notes |
|---|---|---|
| `column`, `bar` | `{categories: [...], series: [{name, values, role?, color?}]}` | single series → labels on bars, value axis hidden; `sort: desc` for rankings; negatives coloured `negative`; `bar` = horizontal (first category on top) |
| `stacked_column`, `stacked_bar` | same, ≥2 series | segment labels inside, totals on top, series named at the right end (no legend); `totals: false` to hide |
| `stacked_100` | same | mix view; values are shares |
| `line`, `slope` | same | first series (or `role: focus`) thick primary, others grey; end-of-line labels; `labels: ends|all|none`; `zero_baseline` |
| `area` | same | stacked area for long series |
| `histogram` | same (buckets as categories) | gap 8% |
| `combo` | same, series with `"axis": "secondary"` become lines | rendered as **two aligned native panels** (lines on top, columns below) — no dual axis |
| `waterfall` | `{steps: [{label, value, type: total|subtotal|delta}]}` | a `total` without value = running total; `highlight` steps in accent; `delta_colors: neutral`; axis auto-truncated (with break marks) when deltas would be slivers; `truncate_axis: false` to disable |
| `bridge` | same with `subtotal` steps | multi-period bridges |
| `scatter` | `{points: [{label?, x, y, group?}]}` + `x_title`, `y_title`, `x_split`, `y_split`, `x_format`, `y_format` | labels placed with collision avoidance; unlabelled points allowed |
| `bubble` | points with `size` | size ∝ **area**; `bubble_scale` |
| `pie`, `donut` | one series, ≤5 parts | label list on the right with shares; warn >5 slices |

Annotations (category charts): `{"type": "cagr", "from": "2021", "to": "2025", "label"?}`,
`{"type": "reference", "value": 100, "label": "Median"}`, `{"type": "callout", "at": "2024", "text": "…"}`,
`{"type": "forecast", "from": "2026", "label": "Forecast"}`.

## Tables (native)

| type | data | notes |
|---|---|---|
| `table` | `columns: [{label, kind: text|number|delta|harvey|rag, format?, width?, align?, good?: up|down}]`, `rows: [[…] | {cells, style: subtotal|total|highlight, indent}]` | numbers right-aligned and formatted; header rule; hairline rows; total rows bold with rule; `highlight_columns` |
| `heatmap` | same + `heatmap: {columns: [1,2], mode: sequential|diverging, domain: [lo, hi]}` | fills auto-darkened to keep text contrast ≥4.5 |
| `harvey_table` | numeric criteria 0–4 become Harvey balls | legend added automatically |
| `scorecard` | `rag` columns with `R/A/G` | status dots |

## Diagrams (native shapes)

| type | data |
|---|---|
| `process`, `value_chain` | `{steps: [{title, text|points, owner?, duration?, callout?}]}`, `highlight: [i]`, `orientation: vertical`, `numbered` |
| `timeline` | `{events: [{date, text}]}`, `highlight: [i]` |
| `gantt`, `roadmap` | `{periods: [...], phases?: [{label, start, end}], today?: 2.5, rows: [{label, bars: [{start, end, label, status?, highlight?}], milestones?: [{at, label}]}]}` (period indices, end exclusive) |
| `matrix_2x2`, `portfolio` | `{x_label, y_label, quadrants: [TL, TR, BL, BR], focus: "TR", items: [{label, x, y, size?}]}` (x, y in 0–1) |
| `tree`, `driver_tree` | `{root: {label, value?, highlight?, operator?, children: [...]}}` left→right |
| `org_chart` | `{root: {label, sub?, children: [...]}}` top→down |
| `funnel` | `{stages: [{label, value, highlight?}]}` — widths ∝ values, conversion % and the largest drop flagged |
| `pyramid` | `{levels: [{label, text?}]}` (top → base) |
| `tile_map` | `{preset: europe|spain, values: {code: v}}` or `{tiles: [{code, row, col, value}]}` |
| `flow` | `{nodes: [{id, label, col, row, emphasis?}], edges: [{from, to, label?}]}` |
| `journey` | `{stages: [...], lanes: [{label, cells: [...], pain_lane?}], pain: [i]}` |
| `layers`, `operating_model`, `architecture` | `{layers: [{label, emphasis?, items: ["…" | {label, change: new|changed, emphasis?}]}], pillars?: [{label}]}` |
| `mekko`, `segmentation` | `{columns: [{label, total, parts: {player: share}}], order: [...]}` — width ∝ total; `highlight: ["Player"]` |

## Text exhibits

| type | data |
|---|---|
| `statements` | `{items: [{title, text | points, label?}], style: numbered|scr}` — executive summaries |
| `kpi` | `{items: [{value, label, delta?, trend?: up|down|flat, good?: up|down, note?}], style?: grid}` |
| `text_columns` / slide `columns` | `[{title, subtitle?, metric?, metric_label?, points, emphasis?}]` |
| `bullets` / slide `commentary` | `{title?, points: ["**Lead-in** text", {text, sub: [...]}]}` |
| `statement`, `quote` | slide kind `statement`: `text`, `support`, `style: quote`, `attribution` |

## Choosing — the reasoning the engine applies

1. **Message first** (`message_type`, see SKILL.md §5). 2. **Data shape**: time axis → left-to-right
(never time on a vertical axis); long or many labels → horizontal bars; <4 periods → no line;
negative values → no pie/stack-100/mekko; >5 parts → no pie; >4 series → highlight one, grey the
rest, or small multiples (`exhibit_trio`). 3. **Feasibility**: the data must feed the visual.
Every automatic choice records *why* and *why not the runners-up* in `resolved.json`.
