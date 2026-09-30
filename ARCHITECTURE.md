# ARCHITECTURE.md — Consulting Presentation Engine

## 1. Principio: THINKING separado de RENDERING

El sistema tiene una frontera explícita: la **deck spec** (JSON). A un lado razona el agente
(qué comunicar, storyline, intención de cada slide, evidencia); al otro, el motor dibuja, renderiza
y comprueba. Nada se dibuja sin *slide intent* completa (`validate_structure` lo bloquea), y todo
cambio posterior se expresa como **parche sobre la spec**, nunca como edición del PPTX. Así el
resultado es reproducible, diffable y auditable.

```
                THINKING (agente + core/)                                RENDERING (motor)
┌──────────────────────────────────────────────────────┐   ┌──────────────────────────────────────────────┐
│ INPUT ──ingest──► inventory (bloques, tablas, cifras)│   │ SLIDE SPECIFICATION (resolved.json)          │
│   │                                                  │   │   │                                          │
│   ▼  CONTENT UNDERSTANDING (triage, SKILL §1)        │   │   ▼ pptx/builder ─► painter ─► componentes   │
│ STORYLINE  core/storyline  (framework, key line,     │   │      text · charts(nativos) · tables · diag. │
│            ghost deck, lint horizontal)              │   │   ▼ deck.pptx + build_manifest.json          │
│   ▼                                                  │   │ RENDER  render/renderer (LibreOffice→PDF→PNG)│
│ SLIDE INTENT (purpose, headline, message_type,       │   │   ▼                                          │
│               evidence)  core/headline (lint)        │   │ QA  qa/geometry · qa/render_checks ·         │
│   ▼                                                  │   │     contenido (planner)  → qa/report (gate)  │
│ VISUAL ENCODING  core/visual_reasoning               │   │   ▼                                          │
│   ▼                                                  │   │ ITERATION qa/autofix → parches de forma ─────┼──┐
│ LAYOUT SELECTION core/layout_selector + layouts/*.json│  │         + review packet → parches del agente │  │
│   ▼                                                  │   └──────────────────────────────────────────────┘  │
│ DENSITY core/density  →  PLANNER core/planner ───────┼──► (resolved.json)                                  │
└──────────────────────────────────────────────────────┘◄──────────────── spec parcheada ───────────────────┘
```

## 2. Módulos

```
consulting-presentation-engine/
├── SKILL.md                 manual operativo del agente
├── layouts/01_…/…16_…/      43 layouts declarativos (JSON) en 16 familias
├── src/cpe/
│   ├── spec.py              vocabulario (kinds, 45 visual types, 20 message types, 14 deck types),
│   │                        validación estructural, parches
│   ├── ingest/readers.py    txt/md/csv/xlsx/json/pdf/docx/pptx → inventario con cifras trazables
│   ├── core/
│   │   ├── storyline.py     7 frameworks, 14 blueprints de deck, arquetipos, scaffold, ghost deck, lint
│   │   ├── headline.py      lint de headlines + verificación de cifras contra la evidencia
│   │   ├── visual_reasoning.py  mensaje × forma de datos → visual (con motivos); crítica de elecciones
│   │   ├── layout_selector.py   roles × compatibilidad × capacidad × variedad
│   │   ├── density.py       capacidad por zona con métricas reales; cambio de layout; división
│   │   └── planner.py       spec → resolved spec (visual, layout, ajuste, trazas `_plan`)
│   ├── design/
│   │   ├── tokens.py        rejilla 12 col, bandas, spacing XS–XXL, escala tipográfica, suelos,
│   │   │                    líneas, contraste WCAG, escalas de color
│   │   ├── themes/*.json    meridian · graphite · harbor
│   │   ├── profiles.json    densidad por perfil (board/standard/analytical/status) y tipo de deck
│   │   └── text_metrics.py  medición de texto con glifos reales (Liberation Sans ≡ Arial)
│   ├── layout/engine.py     carga de la librería y resolución de zonas a cajas en pulgadas
│   ├── pptx/
│   │   ├── painter.py       única capa que toca python-pptx: tokens, sin p:style, nombres
│   │   │                    `cpe|zona|tipo|n`, ajuste de texto hacia el suelo, manifest
│   │   ├── text_components.py  chrome, headline equilibrado, KPIs, statements, columnas, takeaway
│   │   └── builder.py       orquesta slides → .pptx + manifest
│   ├── charts/              native.py (charts nativos con plot area determinista + overlays),
│   │                        numfmt.py (formatos Excel ⇄ Python, escalas redondas, CAGR)
│   ├── tables/table.py      tablas nativas: heatmap, deltas, subtotales, Harvey, RAG
│   ├── diagrams/diagrams.py proceso, timeline, gantt, 2x2, árboles, org chart, funnel, pirámide,
│   │                        tile map, flow, journey, capas/modelo operativo, mekko
│   ├── render/renderer.py   LibreOffice headless → PDF → PNG (PyMuPDF) → contact sheet
│   ├── qa/
│   │   ├── geometry.py      ~20 comprobaciones sobre el PPTX
│   │   ├── render_checks.py comprobaciones sobre lo que LibreOffice dibujó (spans del PDF + tinta)
│   │   ├── autofix.py       issues → parches de forma / acciones para el autor
│   │   └── report.py        score, gate `passed`, excepciones acotadas, informe, review packet
│   ├── pipeline.py          bucle generate → render → inspect → patch → render
│   └── cli.py               `cpe` (ingest, scaffold, outline, lint, recommend, plan, build,
│                            render, qa, run, patch, review, catalog, themes)
├── examples/alvora/         deck de demostración (borrador → QA → parches → final), PPTX y renders
├── examples/gallery/        todos los tipos de exhibit (26 slides), PPTX y renders
├── tests/                   44 tests (unitarios, estrés de QA, render, bucle)
└── docs/                    auditoría detallada, catálogo de layouts, guía visual, spec, códigos QA
```

## 3. Decisiones clave de implementación

**Rejilla y bandas fijas.** Slide 13,333″×7,5″; márgenes 0,55″; 12 columnas con gutter 0,22″;
bandas: tracker 0,30″ · headline 0,52″ (2 líneas) · body 1,62–6,78″ · footer 6,86″. Los layouts
sólo declaran columnas y fracciones verticales del body; el motor añade exactamente un gutter entre
zonas adyacentes. Resultado: todas las slides comparten alineaciones sin coordenadas manuales.

**Métricas reales en ambos sentidos.** `text_metrics` envuelve el texto con los avances de glifo de
Liberation Sans (métricas idénticas a Arial). El mismo cálculo decide *antes* (densidad, ajuste a
suelo, headline equilibrado) y verifica *después* (QA geométrico), y el render de LibreOffice lo
contrasta con la realidad.

**Charts nativos con geometría determinista.** Cada chart fija escala (redonda) y *plot area*
(`c:manualLayout`, `layoutTarget=inner`). Con eso el motor conoce el mapeo dato→pulgada y coloca
overlays exactos: totales de apilados, etiquetas directas al final de series (sin leyenda),
flechas CAGR, líneas de referencia, sombreado de forecast, conectores y marcas de corte de eje en
waterfalls. Los datos quedan en el workbook embebido (editables). El combo se resuelve con dos
paneles nativos alineados en lugar de un eje dual.

**Waterfall 100 % nativo.** Barra apilada con serie base invisible; totales/subtotales; deltas
coloreados o neutros; eje truncado automáticamente cuando los deltas serían astillas, con marcas
de corte visibles para no engañar.

**Nombres de shape como contrato con el QA.** `cpe|<zona>|<tipo>|<n>` permite al QA saber a qué
zona pertenece cada shape (escape de zona), qué solapes son intencionados (texto sobre relleno,
etiqueta sobre su línea guía) y cuáles no (tinta de texto sobre tinta de texto).

**QA en tres capas + revisión semántica.** (1a) contenido sobre la spec; (1b) geometría sobre el
PPTX; (1c) render: los spans de texto del PDF de LibreOffice se comparan con las cajas del PPTX
(texto desbordado, colisiones reales, líneas reales del headline) y el PNG da la cobertura de
tinta. (2) El agente revisa los PNG con 8 preguntas y 4 lentes. El veredicto `passed` lo calcula
el código; las excepciones exigen slide + código + motivo.

**Autocorrección acotada.** El bucle aplica sólo cambios de forma (tipo de visual con fix concreto,
alternativa de layout, división de tablas), registra cada parche y se detiene cuando no hay
parches nuevos o se agota el presupuesto. Lo que requiere reescribir se devuelve como acción
precisa para el autor (p. ej. "recorta ≈90 palabras").

## 4. Flujo de datos y artefactos

| Paso | Entrada | Salida |
|---|---|---|
| ingest | ficheros | `inventory.json/.md` |
| scaffold / edición | tipo de deck | `deck.json` |
| outline / lint | `deck.json` | ghost deck, issues |
| plan | `deck.json` | `resolved.json` (visual, layout, ajuste, motivos) |
| build | `resolved.json` | `deck.pptx`, `build_manifest.json` |
| render | `deck.pptx` | `deck.pdf`, `renders/*.png`, `contact_sheet.png` |
| qa | pptx + manifest + pdf/png | `qa_report.json/.md` |
| run | `deck.json` | todo lo anterior + iteraciones + `review.md` + `deck.autofixed.json` |
| patch / review | parches / `review.json` | spec corregida / veredicto semántico |

## 5. Extender el motor

- **Nuevo layout:** añade un JSON en `layouts/<familia>/` (zonas por columnas y fracciones,
  `accepts`, `compatible_visuals`, `capacity`, `when_to_use`). El test de librería comprueba que
  ninguna zona se solape ni salga de los márgenes.
- **Nuevo visual:** implementa `render(p, box, ex)` usando sólo `Painter`, regístralo en
  `spec.VISUAL_TYPES` y en `diagrams.RENDERERS` / `charts.native.render`, añade reglas en
  `visual_reasoning.BASE` y un ejemplo en la galería.
- **Nuevo tema:** copia `design/themes/meridian.json`; los tests exigen contraste ≥7:1 (texto) y
  ≥4,5:1 (texto secundario).
- **Nuevo check:** devuelve `issue(level, CODE, message, slide)` desde `qa/`; documenta el código
  (el generador de `docs/QA_CODES.md` lo recoge) y, si puede corregirse sin tocar el mensaje,
  añade la regla en `qa/autofix.py`.
