# AUDIT.md — Auditoría de las cuatro implementaciones de referencia

> Entregable intermedio obligatorio (Fases 1–3). Se escribió **antes** de implementar el motor.
> Los informes detallados por repositorio (con referencias `archivo:línea`, tokens literales y
> puntuaciones justificadas) están en [`docs/audit/`](docs/audit/). Este documento los sintetiza.

Metodología: se clonaron los cuatro repositorios, se leyó todo el código y la documentación
(no solo el README), se ejecutaron los ejemplos y tests disponibles, se renderizaron los PPTX con
LibreOffice → PDF → PNG y se inspeccionaron visualmente los resultados. Tres auditorías se hicieron en
paralelo con subagentes con el mismo guion (A–H + 38 capacidades); la cuarta (PR #813) se hizo
directamente. Todos los defectos citados abajo se reprodujeron en render, no se infirieron.

| # | Repositorio | Qué es realmente | Tamaño |
|---|---|---|---|
| 1 | `seulee26/mckinsey-pptx` | Plugin Claude Code + librería python-pptx de 40 plantillas + catálogo | 30 ficheros, ~5,3k líneas Py |
| 2 | `vercel-labs/skills` PR #813 (`elite-ppt-pro`) | Skill **solo de prompt** (pptxgenjs) con 38 fragmentos de layout y 8 paletas | 3 ficheros Markdown, 3,1k líneas |
| 3 | `likaku/Mck-ppt-design-skill` | Motor python-pptx `MckEngine` (67 métodos) + QA geométrico + gate JSON | 53 ficheros, `engine.py` 3,2k líneas |
| 4 | `kgraph57/mckinsey-style-visualization-skill` | Método de visualización + renderer SVG/HTML (22 patrones), sin PPTX | 389 ficheros, 335 tests |

---

## 1. Análisis por repositorio

### 1.1 seulee26/mckinsey-pptx

**A. Problema.** Generar decks "estilo McKinsey" en python-pptx a partir de un prompt: el agente elige una plantilla por slide, escribe un script de build, lo ejecuta y mira 2–3 PNG.

**B. Arquitectura.** `theme.py` (tokens en dataclasses congeladas) → `base.py` (primitivas + `add_chrome`) → `builder.py` (`_REGISTRY` de 52 claves, `infer_slide_type` por *sniffing* de claves, `PresentationBuilder`) → `slides/*.py` (40 funciones de plantilla). Agente (`agents/mckinsey-slide-agent.md`), comando `/mckinsey-deck` y `agent/CATALOG.md` (885 líneas, formato *Use when / Don't use when / inputs / example*).

**C. Flujo.** Prompt → el LLM planifica slide a slide con justificación "plantilla X, no Y porque…" → escribe `build.py` → ejecuta → render opcional a 80 dpi → revisión ocular.

**D. Fortalezas.** Catálogo excelente como formato de conocimiento (cuándo usar / cuándo no / reglas de desempate entre plantillas similares, CATALOG.md:816+). Justificación explícita por slide. Chrome coherente y paleta navy/azul sobria. Patrones de consultoría reconocibles: panel "so-what", flecha CAGR, sombreado de forecast, KPI tiles, issue tree con reparto de espacio por nº de hojas, matrices BCG/3×3, Harvey balls.

**E. Debilidades (verificadas en render).**
- **Ningún gráfico nativo**: todo se dibuja con rectángulos (0 charts y 0 tablas en un deck de 16 slides; hasta 77 shapes por slide) → datos no editables.
- Bugs de gráficos: valores negativos dibujados fuera de la slide; etiquetas `int(round())` (0,45 → "0"); ticks del bubble no redondos; burbujas escaladas por diámetro (no por área).
- Overflow y colisiones: título de 2 líneas choca con la línea inferior; listas largas atraviesan el footer; KPI largo se parte; etiquetas del bubble se solapan; texto blanco sobre cuadrante gris claro (invisible).
- Conectores heredan la sombra del tema (`p:style effectRef`) → reglas borrosas.
- Placeholders que se cuelan al entregable ("[TIMELINE]", "Source: xx"); marca "McKinsey & Company" por defecto (riesgo de marca).
- **Cero QA automatizado**, cero tests, sin medición de texto.

**F. Reutilizable.** Formato de catálogo + reglas de desempate; justificación "no X porque Y"; escala de ticks redondos (`_y_ticks`, column_chart.py:28); truco XML de punta de flecha; helpers XML de viñetas; parser de puntuaciones Harvey; reparto de espacio del issue tree por hojas.

**G. Descartar.** Gráficos dibujados con shapes, texto superpuesto a shapes sin agrupar, conectores con sombra, `infer_slide_type`, variantes de cuenta fija (3 tendencias, 5 áreas…), emojis como iconos, datos inventados, branding de terceros.

**H. Reinterpretar.** Catálogo → metadatos de layout legibles por máquina con capacidad; justificación → objeto de razonamiento visual registrado por slide; flechas CAGR → capa de anotaciones sobre gráficos nativos; orden sugerido de slides → capa explícita de storyline.

### 1.2 vercel-labs/skills PR #813 — `elite-ppt-pro`

**A. Problema.** Skill de prompt que fusiona una librería multi-estilo de layouts con un flujo "data-first" tipo McKinsey, generando con pptxgenjs.

**B. Arquitectura.** Sin código ejecutable. `SKILL.md` (7 pasos: investigación ≥15 datos/≥5 fuentes → plan → estilo → layout → código pptxgenjs → HTML opcional → checklist), `slide-types.md` (38 funciones JS: SWOT, Ansoff, Pareto, Chasm, KANO, STP, RFM, Gantt, journey, BMC, Porter, 2×2, KPI dashboard…), `qa-checklist.md`.

**C. Flujo.** El agente investiga, copia y adapta fragmentos JS, ejecuta node y marca la checklist a ojo. No hay render.

**D. Fortalezas.** *Gate* de investigación cuantificado y jerarquía de fuentes (Tier 1–5); `Source:` obligatorio en cada slide con datos; regla "título = conclusión" con ejemplos ✅/❌; máximo 2 colores de acento por slide; tabla tipo-de-dato → layout; estructura estándar de 10 páginas; amplio catálogo de frameworks.

**E. Debilidades.** Sin motor: cada deck se reescribe desde fragmentos → inconsistencia. "≥4 zonas de contenido por página" contradice "una idea por slide" y empuja a la sobrecarga. Headline a 10 pt en una banda de 0,55". Degradados, "iconos inteligentes", 7 temas de color, badges de página y marca de agua "Elite PPT Pro" → *AI slide look*. Gráficos como rectángulos. Contradicción interna (dice que pptxgenjs no soporta degradados y usa sintaxis de officegen). QA manual, sin medición de overflow.

**F. Reutilizable.** Gate de evidencia y convención de fuentes; límite de acentos; tabla dato→visual; catálogo de frameworks como **tipos de diagrama**; tabla de errores comunes (→ lint automático).

**G. Descartar.** Temas de color múltiples y chillones, degradados, iconos, badges, marca de agua, regla ≥4 zonas, fragmentos pptxgenjs, doble salida HTML.

**H. Reinterpretar.** "Investigar primero" → registro de evidencia en la *slide intent*; checklist → comprobaciones automáticas + rúbrica semántica; librería de frameworks → primitivas de diagrama parametrizadas por datos.

### 1.3 likaku/Mck-ppt-design-skill

**A. Problema.** Motor python-pptx con tokens fijos y un proceso de 5 etapas (brief → outline.json → content.json → render → entrega) con QA geométrico y un *gate* de máquina.

**B. Arquitectura.** `mck_ppt/engine.py` (`MckEngine`, 67 métodos de slide), `core.py` (primitivas, fuente EA/CJK), `constants.py` (navy `#051C2C`, Georgia/Arial/KaiTi, márgenes 0,8"), `qa.py` (10 checks con severidad y score), `review.py` (densidad, títulos largos, mezcla de idiomas, autofix), `references/scripts/gate_check*.py` (JSON `passed` + exit code), `references/layout-matrix.yaml` (capacidades por layout), guías de planificación y *guard rails*, `experiences/` (lecciones Problema/Causa/Fix/Regla).

**C. Flujo.** El LLM redacta brief y outline, elige layouts con una tabla, rellena `content.json`, ejecuta el motor, corre `qa.py` + gate; si falla, autofix (recorte regex + reducción de 1 pt).

**D. Fortalezas.** **El gate derivado por código** ("passed lo decide el código, no el LLM") — la mejor idea de las cuatro. Inventario de QA con umbrales explícitos (overflow de slide, overflow de texto, colisión texto-regla, whitespace muerto en rejilla 20×20, solape texto-texto >15 %, fuente <8 pt, consistencia de fuentes en fila, leyendas fuera, conectores, `p:style`). Presupuestos de caracteres y máximo de ítems por layout. Fórmulas de dimensionado dinámico (`item_w=(CW−gap(n−1))/n`). Regla "slides adyacentes no comparten layout". Manejo CJK (fuente `a:ea`, interlineado 1,35). Arnés de estrés: un slide por layout con fixtures normal/estrés.

**E. Debilidades (verificadas).** Sin gráficos ni tablas nativas (línea = rectángulos apilados; "área apilada" = columnas). Geometría codificada a mano en casi todos los métodos; sin *solver*. **Sin render en el pipeline.** Su propio deck de test: 82/100 con 41 errores (su gate dice FAIL); el deck de ejemplo de 33 slides tiene 28 errores pero `DeckBuilder` imprime "QA passed". Estimación de texto por caracteres (0,55 em). Autofix que trunca frases por regex (cambia el significado). Documentación desalineada (8 métodos inexistentes; `layout-matrix.yaml` es Markdown). Whitelist de excepciones global.

**F. Reutilizable.** Gate JSON con exit code y excepciones **acotadas por layout y con motivo**; inventario de checks (mejorado con métricas reales y render); capacidades por layout; fórmulas de dimensionado; parser `**negrita**` → runs; consistencia de pares; colisión texto-regla; arnés de estrés; plantilla de lecciones aprendidas.

**G. Descartar.** Geometría a mano, gráficos con shapes, autofix por regex, módulo de portada con imágenes Tencent, textos chinos codificados en el layout, whitelist global.

**H. Reinterpretar.** `content.json` → especificación tipada que el render consume directamente; capacidad → validada **antes** (presupuesto) y **después** (medición); *fallback* de layout por capacidad (7 pasos → vertical o dividir slide).

### 1.4 kgraph57/mckinsey-style-visualization-skill

**A. Problema.** Convertir notas y métricas en visuales de estilo consultoría con un método riguroso (triage, gate de comparación, rúbrica, loops de revisión) y un renderer SVG determinista.

**B. Arquitectura.** Capa de método en Markdown (`references/*.md`: input-triage, document-type-profiles, persona-playbook, visualization-patterns, style-system, quality-rubric, iterative/expert-review-loop, reference-reproduction) + `scripts/render_slide_spec.py` (2k líneas, stdlib) JSON → SVG 1280×720 para 22 patrones → HTML/PDF/Word. 6 arquetipos de deck en `templates/decks/`. 335 tests.

**C. Flujo.** Pregunta estratégica → triage → perfil de documento → headline (una sola proposición, sin "y") → patrón (gate de comparación de Zelazny) → estilo → spec → render SVG → rúbrica → loops de revisión.

**D. Fortalezas.** **Razonamiento de selección visual (el mejor)**: gate de comparación (componente, ítem, serie temporal, distribución, correlación), tabla de triage de 16 tipos de input, pregunta del lector por patrón, atajo "¿qué debe poder hacer el lector tras 10 segundos?". Reglas de headline claras. **Límites de densidad aplicados por validadores** con la política "dividir, no encoger". Sistema de estilo con tokens únicos, WCAG, rampas divergentes. Rúbrica /24 con *gates* bloqueantes y **comprobación de headlines del deck (¿forman una pirámide?)**. Loops de revisión con 5 lentes (CEO, CFO, partner, editor visual, seguridad) y criterios de parada. Perfiles por tipo de documento.

**E. Debilidades.** **No genera PPTX** (explícitamente fuera de alcance) → editabilidad 0. Ajuste de texto estimado por caracteres (se observó apelotonamiento headline/subtítulo en el Gantt). Sin detección general de colisiones. Series temporales: solo dibuja la primera serie. Sin combo, bubble, apilados, árboles, org charts, mapas. El revisor `review_slide_spec.py` puntúa palabras clave: un fichero basura de 16 líneas obtuvo 20/20. Rúbrica inconsistente (/24 vs /20). Mucho material comercial (LAUNCH, BUYER_BRIEF, MARKETPLACE…).

**F. Reutilizable.** Esquemas de spec por patrón; triage; gate de comparación y tabla patrón→pregunta; perfiles de documento; rúbrica y gates bloqueantes; lentes de revisión y criterios de parada; límites de densidad; tokens de color/tipografía; regla "restar antes de añadir".

**G. Descartar.** Documentos comerciales, tooling del *landing site*, salidas SVG/HTML/Word, revisor por palabras clave, criterio de "marketplace safety" como puntuación.

**H. Reinterpretar.** Schema → *slide intent* + objeto storyline; tokens px → pt/pulgadas; patrones → gráficos nativos python-pptx, tablas nativas y shapes; límites de densidad → medidos con fuentes reales; revisión → checks deterministas sobre datos estructurados + revisión visual del agente sobre PNG reales.

---

## 2. Matriz comparativa de capacidades

Escala 0 = ausente · 1 = débil / solo documentación · 2 = sólido · 3 = fuerte y reutilizable.
S = seulee26 · E = elite-ppt-pro (PR #813) · L = likaku · K = kgraph57. **Mejor** = de quién tomamos la idea.

| Capacidad | S | E | L | K | Mejor | Por qué / qué tomamos |
|---|---|---|---|---|---|---|
| Ingestión de contenido | 1 | 1 | 1 | 1 | K | Nadie parsea ficheros; K tiene el mejor método de triage → lo implementamos con lectores reales |
| Storyline | 1 | 1 | 1 | 1 | K | Arco + check de headlines en prosa; nadie tiene modelo de storyline → lo creamos |
| Pyramid principle | 0 | 0 | 0 | 1 | K | Solo K lo nombra (check de headlines del deck) |
| Slide planning | 2 | 1 | 2 | 1 | L/S | outline por slide + justificación "no X porque Y" |
| Generación de headlines | 1 | 2 | 1 | 2 | K/E | Reglas "una proposición", ejemplos ✅/❌ |
| Comunicación ejecutiva | 2 | 1 | 2 | 2 | K | Lentes CEO/CFO, closing con owners, takeaway bar (L) |
| Elección de visualización | 2 | 2 | 1 | **3** | K | Gate de comparación + triage + pregunta del lector |
| Selección de layout | 2 | 1 | 1 | 1 | S | Reglas de desempate del catálogo |
| Librería de layouts | 2 | 2 | 2 | 1 | S/L | Amplitud de patrones (sin su geometría a mano) |
| Gráficos | 1 | 1 | 1 | 2 | K | Reglas de integridad; nadie usa charts nativos |
| Tablas | 1 | 1 | 1 | 2 | K | benchmark table con líder resaltado |
| Waterfalls | 0 | 0 | 2 | 2 | K/L | Matemática correcta del puente (K), conectores (L) |
| Bridges (subtotales) | 0 | 0 | 1 | 2 | K | Nadie soporta subtotales → lo añadimos |
| Timelines | 2 | 2 | 1 | 1 | S | Gantt, waves, chevrons |
| Matrices | 2 | 2 | 2 | 2 | S/K | BCG / 2×2 con cuadrante foco |
| Árboles | 2 | 0 | 1 | 0 | S | Reparto de espacio por hojas |
| Procesos | 2 | 2 | 2 | 2 | K | Owner/duración/cuello de botella |
| Mapas | 0 | 0 | 0 | 0 | — | Nadie → *tile map* editable |
| Org charts | 2 | 1 | 0 | 0 | S | 2 niveles + reportes |
| Bubble charts | 1 | 0 | 1 | 0 | S | Idea sí, implementación no (diámetro) |
| Charts combinados | 0 | 0 | 0 | 0 | — | Nadie → combo nativo barra + línea eje secundario |
| Diagramas conceptuales | 1 | 2 | 2 | 1 | L/E | Catálogo de frameworks |
| SVG | 0 | 1 | 0 | **3** | K | Excelente, pero no es el medio final (PPTX editable) |
| Generación PPTX | 2 | 1 | 2 | 0 | S/L | python-pptx fiable |
| Editabilidad | 1 | 1 | 2 | 0 | L | Shapes nativas; nadie tiene datos editables |
| Consistencia visual | 2 | 1 | 2 | **3** | K | Una sola fuente de tokens |
| Fuentes | 1 | 1 | 2 | 2 | L/K | Fuente EA/CJK, pilas de fuentes |
| Colores | 2 | 2 | 2 | **3** | K | Roles semánticos + WCAG |
| Spacing | 1 | 0 | 2 | 2 | L/K | Rejilla y reglas de gap |
| Alineación | 2 | 0 | 2 | 2 | L | Rejilla LM/CW consistente |
| Densidad | 1 | 0 | 2 | **3** | K | Límites duros + "dividir, no encoger" |
| Overflow | 0 | 1 | 1 | 2 | K | Rechazo de specs densas (pero por caracteres) |
| Colisiones | 0 | 0 | 1 | 1 | L | Texto-texto y texto-regla |
| Rendering | 1 | 0 | 0 | 2 | K | Nadie renderiza PPTX dentro del loop |
| QA | 0 | 1 | 2 | 1 | L | Inventario de checks + score |
| Revisión automática | 1 | 0 | 1 | 1 | K | Lentes (como prompts) |
| Iteración | 1 | 0 | 1 | 1 | K | Criterios de parada bien definidos |
| Validación final | 0 | 1 | 2 | 1 | L | **Gate JSON derivado por código** |

**Lectura de la matriz.** Ninguna implementación supera "2" en la cadena completa. Los huecos comunes
son exactamente los que definen la calidad profesional: (1) no existe una capa de *thinking*
estructurada (storyline / intent) antes de dibujar; (2) nadie produce gráficos con datos editables;
(3) nadie mide el texto con métricas reales; (4) nadie renderiza el PPTX dentro del bucle de QA;
(5) nadie cierra el bucle *generar → renderizar → inspeccionar → parchear → re-renderizar*.

---

## 3. Mejores prácticas encontradas (a conservar)

1. **Gate de máquina** (L): el veredicto `passed` lo calcula el código y se escribe en JSON con exit code.
2. **Gate de comparación + triage** (K): primero el tipo de mensaje, luego el visual.
3. **"Dividir, no encoger"** (K) con suelos de legibilidad; límites de densidad aplicados por validadores.
4. **Headline = una proposición** con conclusión (K, E), sin "y" que una dos afirmaciones.
5. **Check de headlines del deck** (K): leer solo los títulos debe contar la historia (*ghost deck*).
6. **Fuente obligatoria** en slides con datos (E, L).
7. **Catálogo con "úsalo cuando / no lo uses cuando" + reglas de desempate** (S).
8. **Capacidad por layout** (máx. ítems, presupuesto por campo) (L).
9. **Slides adyacentes con layouts distintos** (L) — evita monotonía.
10. **Una sola fuente de tokens**, roles de color semánticos, contraste WCAG (K).
11. **Lentes de revisión** CEO/CFO/partner/editor visual con criterios de parada (K).
12. **Arnés de estrés** un slide por layout (L).
13. **Máx. 2 acentos por slide** (E); un único foco por exhibit.

## 4. Problemas encontrados (a no repetir)

| Problema | Dónde | Consecuencia | Respuesta en el nuevo motor |
|---|---|---|---|
| Gráficos dibujados con rectángulos | S, E, L | Datos no editables, bugs de escala | Charts nativos python-pptx + overlays calculados |
| Geometría codificada a mano | S, E, L | Overflow con contenido real | Layouts declarativos sobre rejilla de 12 columnas |
| Texto estimado por nº de caracteres | L, K | Overflow no detectado / falsos positivos | Métricas reales de fuente (Liberation Sans ≡ Arial) |
| Sin render en el bucle | S, E, L | Defectos solo visibles al abrir el PPTX | LibreOffice → PDF → PNG + QA sobre el PDF renderizado |
| QA "aprobado" falso | L (DeckBuilder) | Entregables con errores | Veredicto único derivado de checks, exit code |
| Autofix que trunca frases | L | Cambia el significado | Autofix solo toca parámetros de forma; el texto lo reescribe el agente |
| Revisor por palabras clave | K | Puntuación trucable | Checks sobre datos estructurados + revisión visual sobre PNG |
| Sombras de tema en shapes/conectores | S | Reglas borrosas | Se elimina `p:style` de cada shape |
| Placeholders en el entregable | S | "[TIMELINE]", "Source: xx" | Check `PLACEHOLDER_TEXT` bloqueante |
| Decoración (degradados, iconos, temas chillones, badges) | E | *AI slide look* | Lenguaje de formas restringido, esquinas rectas, 1 acento |
| "≥4 zonas por slide" | E | Sobrecarga | Una idea por slide, capacidad por zona |
| Branding de terceros | S, L | Riesgo de marca | Estética de consultoría sin imitar marcas |

## 5. Decisiones de diseño

| # | Decisión | Motivo |
|---|---|---|
| D1 | **Python + python-pptx** como único runtime; LibreOffice solo para render | Dos de cuatro repos ya lo usan; es el camino más fiable a PPTX nativo |
| D2 | **Separación THINKING / RENDERING mediante un `deck spec` JSON** | Nada se dibuja sin *slide intent* completa; la spec es diffable y parcheable |
| D3 | **Storyline explícito**: `governing_thought` + `key_line` + framework (SCR, CII, PDS, DRI, MPO, CGT, HEC) | Lógica horizontal verificable (*ghost deck*) |
| D4 | **Razonamiento visual por tipo de mensaje** (Zelazny ampliado a 20 tipos) + forma de los datos | La elección depende del mensaje, no de la preferencia |
| D5 | **Layouts declarativos en JSON** sobre rejilla de 12 columnas y bandas verticales fijas | Consistencia por construcción; capacidad declarada |
| D6 | **Charts nativos** con *plot area* determinista (`manualLayout inner`) + escalas redondas explícitas | Editables y con anotaciones precisas (CAGR, totales, etiquetas directas, conectores de waterfall) |
| D7 | **Tablas nativas** con estilo propio (sin estilo de tabla de Office) | Editables; heatmap, subtotales, deltas, Harvey balls |
| D8 | **Diagramas con shapes nativas nombradas** | Editables; QA sabe a qué zona pertenece cada shape |
| D9 | **Métrica de texto real** (PIL + Liberation Sans) para planificar y para QA | Mismo cálculo antes y después |
| D10 | **QA en tres capas**: estructura/contenido (spec), geometría (PPTX), render (PDF de LibreOffice: posiciones reales de texto) | Detecta overflow y colisiones *reales*, no estimadas |
| D11 | **Autofix acotado** (layout, tamaño dentro de suelos, división de tablas/listas, variante de chart) + **parches del agente** para el texto | El código nunca reescribe el mensaje |
| D12 | **Gate final** `qa_report.json` con `passed`, errores bloqueantes y exit code | Heredado de L, sin whitelist global |
| D13 | **Densidad por perfil de deck** (board, standard, analytical, status) | El estilo se adapta al tipo de deck |
| D14 | **Estética sobria**: esquinas rectas, sin sombras, sin degradados, sin iconos, 1 color de acento, jerarquía tipográfica | Evitar el *AI slide look* |

## 6. Arquitectura propuesta

```
INPUT (txt, md, csv, xlsx, pdf, docx, pptx, json)
  │  cpe ingest            → inventory.json (bloques de texto, tablas, cifras con contexto)
  ▼
CONTENT UNDERSTANDING      (agente, guiado por SKILL.md §2 + triage)
  ▼
STORYLINE                  cpe scaffold  → deck.json con governing thought, key line, secciones
  ▼                        cpe outline   → ghost deck (solo headlines)  ← revisión de lógica horizontal
SLIDE INTENT               purpose · headline · supporting_message · message_type · evidence
  ▼                        cpe lint      → estructura + headlines + storyline + evidencia
VISUAL ENCODING            core/visual_reasoning  (message_type × forma de datos → visual, con motivo)
  ▼
LAYOUT SELECTION           core/layout_selector   (roles presentes × compatibilidad × capacidad × variedad)
  ▼
SLIDE SPECIFICATION        core/planner + density → resolved.json (visual, layout, ajustes, divisiones)
  ▼
PPTX GENERATION            pptx/builder → painter → text_components · charts · tables · diagrams
  ▼                        + build_manifest.json (zonas, cajas, decisiones de ajuste)
RENDER                     render/soffice → PDF → PNG + contact sheet
  ▼
VISUAL QA                  qa/geometry (PPTX) · qa/render (PDF real) · qa/content (spec)
  ▼                        → qa_report.json / .md  (+ review packet para revisión semántica del agente)
ITERATION                  qa/autofix → parches de spec → rebuild (máx. N) ; agente → patches.json
  ▼
FINAL PPTX                 gate: passed ⇔ 0 errores bloqueantes
```

Módulos (`src/cpe/`): `spec.py` (contrato), `ingest/`, `core/` (storyline, headline, visual_reasoning,
layout_selector, density, planner), `design/` (tokens, temas, perfiles, métricas de texto),
`layout/` (motor de layouts), `pptx/` (painter, componentes de texto, builder), `charts/`, `tables/`,
`diagrams/`, `render/`, `qa/` (geometry, render, content, autofix, report), `cli.py`.
`layouts/` contiene la librería declarativa por familias (01–16). Ver `ARCHITECTURE.md`.

## 7. Qué reutilizar / qué reescribir

| Componente | Origen | Acción |
|---|---|---|
| Gate JSON con exit code | L | **Reutilizar la idea**, reescribir sin whitelist global |
| Inventario de checks QA | L | **Reescribir** con métricas reales + render; añadir zona, contraste, paleta, placeholders, headline |
| Capacidades por layout | L | **Reinterpretar** como `capacity` en JSON de layout + medición |
| Gate de comparación, triage, pregunta del lector | K | **Reutilizar** como tabla de reglas en `visual_reasoning.py` |
| Límites de densidad / "dividir, no encoger" | K | **Reutilizar** con suelos de legibilidad por rol |
| Rúbrica, gates bloqueantes, lentes, criterios de parada | K | **Reutilizar** en la revisión semántica (review packet) |
| Reglas de headline | K, E | **Reescribir** como lint determinista con puntuación |
| Catálogo "úsalo/no lo uses" + desempates | S | **Reinterpretar** en `when_to_use` + reglas del selector |
| Escala de ticks redondos, punta de flecha XML | S | **Reescribir** (`nice_scale`, conectores) |
| Reparto de espacio del árbol por hojas | S | **Reescribir** en `diagrams/tree` |
| Parser `**negrita**` → runs | L | **Reutilizar** la idea |
| Fuentes de datos Tier 1–5, `Source:` obligatorio | E | **Reutilizar** en lint de evidencia |
| Renderers de gráficos (S, L, E) | — | **Descartar**: charts nativos |
| Renderer SVG/HTML (K) | — | **Descartar** como salida; el render de verificación es LibreOffice |

## 8. Riesgos técnicos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| LibreOffice no renderiza exactamente igual que PowerPoint (métricas, charts) | QA de render con falsos +/− | Fuente Arial (≡ Liberation Sans, mismas métricas); tolerancias; QA geométrico independiente del render |
| `manualLayout` del plot area interpretado distinto por LibreOffice | Overlays desalineados | Verificación visual en el loop; overlays solo donde aportan (totales, CAGR, etiquetas directas) |
| XML inyectado (combo, bordes de tabla, viñetas) inválido para PowerPoint | "Reparar archivo" | Orden de esquema respetado; test que reabre el PPTX con python-pptx y valida el XML de cada parte |
| Falta el componente Impress de LibreOffice en el entorno | Sin render | Detección y mensaje claro; QA geométrico sigue funcionando (`--no-render`) |
| Idiomas CJK | Métricas distintas | Fallback por ancho de em; documentado como limitación |
| La calidad del storyline depende del agente | Deck correcto pero irrelevante | Lint de storyline, ghost deck, rúbrica y lentes en SKILL.md |
| Autofix que degrade el mensaje | Deck "limpio" pero peor | El autofix no toca texto; lo que requiere reescritura se reporta como parche pendiente |
