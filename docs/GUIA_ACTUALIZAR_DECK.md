# Guía: actualizar un deck existente con material nuevo (v3.0)

Esta guía cubre el uso principal de la herramienta: coger el deck del año pasado y las fuentes de este
año, y obtener un deck actualizado revisado por una persona. Lo que la herramienta hace bien y lo que no
está medido al final, con material real.

## 1. Preparar

```
mi_caso/
  deck_anterior.pptx        el deck a actualizar (tablas y gráficos nativos, no imágenes)
  fuentes/                  el material nuevo: .xlsx .csv .docx .pdf (con texto) .pptx .md .txt
```

- **Correos:** guárdalos como `.txt` o `.pdf`.
- **Formatos antiguos:** un `.xls` debe convertirse a `.xlsx`.
- **PDF escaneados:** no se leen; no hay reconocimiento de texto.

## 2. Proponer

```
cpe update mi_caso/deck_anterior.pptx mi_caso/fuentes -o trabajo
```

Escribe en `trabajo/`:

| archivo | contenido |
|---|---|
| `review.xlsx` | **la revisión, en una hoja de cálculo** (cuatro hojas: Cambios, Titulares, Conflictos, Diapositivas) |
| `update_plan.md` | cada cifra del deck: vigente, desactualizada (con el valor propuesto y su fuente), sin rastrear o ignorada |
| `messages.md` | titulares cuyo mensaje ya no se sostiene (umbrales, superlativos, signo, orden, año de recuperación) |
| `fact_conflicts.json` | fuentes que se contradicen, ordenadas por prioridad |

## 3. Revisar (siempre una persona)

En `review.xlsx`:
- **Cambios:**
  - aprueba o corrige cada cifra;
  - da valor a las que quedaron "sin propuesta";
  - mira las que dicen "restatements disagree": la misma cifra encontró valores distintos en sitios distintos.
- **Titulares:** acepta la propuesta o escribe la tuya.
- **Conflictos:** elige qué fuente usar o descarta el conflicto, con un motivo.
- **Diapositivas:** mantener, eliminar o reconstruir.

Los errores de la hoja (un valor que no es número, una aprobación sin valor) se avisan y no se aplican.

## 4. Aplicar

```
cpe update --apply trabajo -o deck_nuevo.pptx --mark --accept-derived
```

Cambia **solo** las cifras aprobadas en el archivo original: todo lo demás queda igual.
- `--mark` resalta lo cambiado para revisarlo.
- `--accept-derived` aplica también los totales y ratios recalculados a partir de valores aprobados.
- `update_report.md` lista lo aplicado, lo que no se pudo aplicar y lo que quedó sin tocar.

## 5. Reconstruir diapositivas (opcional)

```
cpe update --rebuild trabajo --slides 6
```

Construye en el estilo del deck las diapositivas cuyo mensaje ya no se sostiene. Se revisan igual que lo
demás.

## 6. Lo que la herramienta no hace, medido con material real

Sobre tres casos reales del propietario (322 cifras con clave sellada, una ejecución ciega):
- **Detección:** encontró el 27% de las cifras desactualizadas, y sus avisos "desactualizada" acertaron
  el 75% de las veces.
- **Valor nuevo:** acertó el 27% de las veces.

La revisión humana no es opcional. Por qué no llega más lejos:
- **No modeliza.** Si el valor nuevo sale de rehacer un business case combinando fuentes (coste real de
  la fase 1 más la oferta de la fase 2, menos la subvención, entre el ahorro), la herramienta no lo
  calcula. Solo rehace la aritmética que ya está en el deck (totales, ratios, payback, proyecciones).
- **No agrega datos fila a fila.** Un export de ERP con miles de pedidos no se suma solo: las tablas
  de más filas que un umbral se tratan como datos a resumir, no se leen celda a celda. Hay que escribir
  un script que calcule los agregados que necesita el deck (por canal, región, año) y registrarlo con
  `cpe reason analyze trabajo script.py --sources fuentes` antes de volver a ejecutar `cpe update`. Sus
  salidas pasan a ser fuentes citables.
- **"Vigente" acierta menos de la mitad** sobre material real: compruébalo antes de dar una cifra por
  buena.
- **Plantillas:** solo se usan plantillas 16:9. Con una 4:3 se aplican sus colores y tipografías, sin
  su patrón ni sus diseños, y la ejecución lo avisa (`BRAND_TEMPLATE_NOT_USED`).

## 7. Validar con tus propios casos

`scripts/validation_kit.py` repite la validación de la v3.0 con cualquier caso nuevo:

```
python scripts/validation_kit.py template deck_anterior.pptx -o clave.xlsx   # una fila por cifra
#   … una persona rellena estado / valor nuevo SIN mirar la salida de la herramienta …
python scripts/validation_kit.py seal clave.xlsx -o SEALED                   # huella antes de ejecutar
cpe update deck_anterior.pptx fuentes -o trabajo                             # una sola ejecución
python scripts/validation_kit.py score clave.xlsx trabajo -v
```


## v3.1 — titulares que dicen la conclusión

Desde la 3.1 la herramienta también revisa la **redacción** de los titulares:

- Si un titular deja de ser cierto con las cifras nuevas, la propuesta de nuevo titular pasa por el
  *Action Title Engine*: no puede cambiar el sentido, el periodo ni el alcance, ni afirmar una causa o una
  decisión que los datos no sostienen. La propuesta llega **sin aprobar** (`set_headline`, columna de
  titulares en `review.xlsx`): la aprueba una persona.
- Un titular que sigue siendo cierto **no se toca**.
- Con `cpe update OLD.pptx FUENTES -o WORK --normalize-editorial` la herramienta señala además los
  títulos que son etiquetas ("Plan de inversión") aunque sus cifras sigan valiendo. No inventa la nueva
  redacción: escribe la alternativa en `candidates` de esa edición en `edits.json` y vuelve a ejecutar;
  si la acepta, queda propuesta (sin aprobar). Una edición sin texto nunca se aplica.
- Las diapositivas reconstruidas (`--rebuild`) se comprueban con las mismas reglas que un deck nuevo.

Detalle: `docs/EDITORIAL_LAYER.md`.
