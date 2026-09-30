# Consulting Presentation Engine

Motor de presentaciones de nivel consultoría: convierte información (notas, documentos, PDF, Excel,
CSV, análisis, business cases) en un **PowerPoint nativo y editable** con lógica de consultoría —
storyline explícito (pyramid principle), una idea por slide con headlines-conclusión, visual elegido
por el mensaje, layouts sobre rejilla — y un **bucle automático de render → QA → corrección** con
veredicto calculado por código.

Es la síntesis de la auditoría de cuatro skills de referencia ([AUDIT.md](AUDIT.md)); la
arquitectura está en [ARCHITECTURE.md](ARCHITECTURE.md) y el manual operativo del agente en
[SKILL.md](SKILL.md).

| | |
|---|---|
| ![demo](examples/alvora/output/2_final/contact_sheet.png) | Deck de demostración (12 slides, datos ficticios coherentes): resumen ejecutivo, mercado (apilado + CAGR), KPIs + combo, mekko, waterfall, heatmap, 2×2 de posicionamiento, modelo operativo, roadmap, impacto financiero y decisiones. **QA: PASSED, 99,8/100, 0 errores, 0 avisos; revisión visual 12/12 slides aprobadas.** |

## Qué lo hace diferente

- **Thinking antes que rendering.** Nada se dibuja sin *slide intent* (propósito, headline,
  tipo de mensaje, evidencia). El storyline es un objeto (governing thought + key line + framework)
  y se verifica leyendo sólo los titulares (*ghost deck*).
- **Headlines verificados.** Se rechazan títulos-tema y dobles mensajes, y cada cifra del titular
  debe poder derivarse de la evidencia o de los datos del exhibit (valores, sumas, cuotas, deltas,
  crecimientos, CAGR).
- **Razonamiento visual explicable.** 20 tipos de mensaje × forma de los datos → visual, con el
  porqué y el porqué-no registrados.
- **Nativo y editable.** Charts nativos (datos editables), tablas nativas, diagramas con shapes;
  cero imágenes de slides. Sin sombras de tema, sin esquinas redondeadas, un solo color de acento.
- **QA real.** Geometría con métricas de fuente reales + comparación con lo que LibreOffice
  *realmente* dibuja (texto desbordado, colisiones, líneas del titular) + revisión semántica guiada.
- **Autocorrección acotada.** El motor corrige la forma (visual, layout, división); lo que exige
  reescribir se devuelve como acción concreta. Nunca trunca frases.

## Instalación

```bash
cd consulting-presentation-engine
pip install -r requirements.txt            # python-pptx, Pillow, lxml, PyMuPDF, openpyxl
# render: LibreOffice con Impress + fuentes Liberation (métricas de Arial)
sudo apt-get install -y libreoffice-impress fonts-liberation    # Debian/Ubuntu
# macOS: brew install --cask libreoffice   (Arial ya está instalada)
pip install pytest && python -m pytest -q  # 44 tests
```

Opcional: `pip install -e .` instala el comando `cpe`. Sin instalar: `scripts/cpe <comando>`.

## Uso rápido

```bash
scripts/cpe ingest notas.md datos.xlsx informe.pdf -o work/inventory.json   # 1. entender el input
scripts/cpe scaffold --deck-type board_presentation --title "…" -o deck.json  # 2. esqueleto de storyline
#   … el agente escribe governing thought, key line e intents de cada slide (SKILL.md §2–§5)
scripts/cpe outline deck.json               # 3. ghost deck: ¿se entiende la historia sólo con titulares?
scripts/cpe lint deck.json                  # 4. intents, headlines, cifras, visuales, densidad
scripts/cpe run deck.json -o out/           # 5. plan → pptx → render → QA → autofix (≤3 vueltas)
#   revisar out/contact_sheet.png y out/review.md; escribir out/review.json y patches.json
scripts/cpe review out/review.json          # 6. revisión visual semántica
scripts/cpe patch deck.json patches.json && scripts/cpe run deck.json -o out/   # 7. iterar
```

Otros comandos: `plan`, `build`, `render`, `qa`, `recommend <message_type>`, `catalog`, `themes`.

## Ejemplos

- **`examples/alvora/`** — test final del encargo. `deck_draft.json` es un primer borrador con
  problemas reales (barras con el tiempo en vertical, comentario demasiado largo, título-tema,
  titular de 3 líneas, fuente ausente). `output/1_draft/` muestra el bucle: el motor corrige la forma
  por sí solo (`VIS_TIME_VERTICAL`: barras apiladas → columnas apiladas, iteración 2) y devuelve 6
  acciones de autor que exigen reescribir (recortar palabras, título-tema, titular largo/doble
  mensaje/3 líneas, fuente ausente). `agent_patches.json` son las correcciones del agente; aplicadas sobre
  `deck.autofixed.json` producen exactamente `deck.json`, cuyo resultado final está en
  `output/2_final/` (PPTX, PDF, PNG por slide, contact sheet, informe QA, revisión visual).
- **`examples/gallery/`** — 26 slides que ejercitan todos los tipos de exhibit, estructura (agenda,
  divisores, statement) y el tema `harbor`. QA: PASSED 99,7.

## Tipos de deck

strategy deck · business review · investment memo · board presentation · market analysis ·
commercial due diligence · transformation program · operating model · product strategy ·
financial analysis · sales strategy · implementation roadmap · executive update ·
project steering committee. Cada uno tiene framework de storyline, arquetipos de slide y perfil de
densidad por defecto (board / standard / analytical / status). Temas: `meridian`, `graphite`, `harbor`.

## Documentación

| | |
|---|---|
| [SKILL.md](SKILL.md) | manual operativo del agente (cuándo usar, análisis, storyline, headlines, visuales, layouts, densidad, bucle, revisión, errores a evitar) |
| [AUDIT.md](AUDIT.md) · [docs/audit/](docs/audit/) | auditoría de las 4 skills, matriz de capacidades, decisiones |
| [ARCHITECTURE.md](ARCHITECTURE.md) | arquitectura, módulos, decisiones de implementación, cómo extender |
| [docs/VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md) | cada tipo de exhibit, su forma de datos y reglas |
| [docs/SPEC_REFERENCE.md](docs/SPEC_REFERENCE.md) | referencia de la deck spec y de los parches |
| [docs/LAYOUT_CATALOG.md](docs/LAYOUT_CATALOG.md) | 43 layouts en 16 familias |
| [docs/QA_CODES.md](docs/QA_CODES.md) | todos los códigos de QA, severidad y remedio |

## Troubleshooting

| Síntoma | Causa / solución |
|---|---|
| `RENDER_UNAVAILABLE`, "source file could not be loaded" | Falta el componente Impress: `apt-get install libreoffice-impress`. Mientras tanto `cpe run --no-render` ejecuta el QA geométrico. |
| El render tarda o se cuelga | Otra instancia de LibreOffice abierta: el motor usa un perfil temporal por conversión; cierra instancias zombis (`pkill soffice`). |
| Anchos de texto distintos a PowerPoint | Instala Liberation Sans (o Arial). Sin ellas el motor cae a un estimador y el QA es menos preciso. |
| `HEADLINE_NUMBER_UNSUPPORTED` | La cifra del titular no sale de los datos: añade `evidence[].value(s)` o corrige la cifra. |
| `CONTENT_OVER_CAPACITY` | El texto no cabe ni al tamaño mínimo: recorta las palabras indicadas o divide la slide. |
| `LAYOUT_NONE` | Ningún layout acepta esa combinación de roles: pasa el comentario a `takeaway` o divide la slide. |
| `AUTO_SPLIT` | Tabla dividida mecánicamente: mejor resumirla (top N + "Otros"). |
| El PPTX muestra "reparar" en PowerPoint | Guarda el `deck.json` y reprodúcelo: los tests reabren cada PPTX con python-pptx, pero PowerPoint es más estricto que LibreOffice con el orden del XML. |

## Limitaciones conocidas

- El render de verificación es LibreOffice; PowerPoint puede diferir ligeramente en saltos de línea
  (el motor deja un margen de seguridad del 3 % en headlines y usa fuentes con métricas idénticas).
- Mapas: *tile maps* (cartogramas) editables con presets Europa/España o casillas propias; no
  mapas coropléticos con fronteras reales.
- Texto CJK: la medición usa Liberation Sans; para decks CJK conviene revisar el render con más
  cuidado.
- La calidad del storyline depende del agente; el motor la estructura y la verifica, no la inventa.
