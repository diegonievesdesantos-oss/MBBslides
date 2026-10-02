# Cerrar v1.8: qué tiene que aportar el responsable

v1.8 tiene construido y probado todo lo que no depende de material real (ver
[V18_STATUS.md](../V18_STATUS.md)). Para cerrarla faltan tres entregas del responsable. Las plantillas
vacías para prepararlas están en [v18_intake/](v18_intake/).

| entrega | qué es | plantilla | coste |
|---|---|---|---|
| 1 | 3–5 plantillas corporativas nunca vistas | `v18_intake/plantillas_v18/` | sin agentes |
| 2 | 1–2 proyectos reales desordenados, con su deck anterior | `v18_intake/proyecto_v18_1/` | una ejecución de agente por proyecto |
| 3 | El criterio del responsable sobre layouts, marca y el deck actualizado | `v18_intake/revision/` | 10–15 min por plantilla, ~30 min por proyecto |

Orden recomendado:
1. Las plantillas: son lo más rápido y no gastan créditos.
2. El proyecto.
3. La revisión, cuando se entreguen los resultados de las dos anteriores.

**Privacidad.**
- Todo lo entregado va a `.private/`, que nunca se sube al repositorio.
- En público solo se registran totales y porcentajes anónimos (Plantilla A, B, C…).
- Nunca se publican nombres, colores, textos, logos, XML, renders ni capturas.
- GitHub Actions no ejecuta nada de esto.

---

## Entrega 1 — Plantillas corporativas (3–5)

### Qué plantillas valen
- **Plantillas reales** que alguna empresa use para sus presentaciones, en `.pptx` o `.potx`.
- **Que el motor no haya visto nunca.** La plantilla corporativa privada usada en desarrollo es material de desarrollo para siempre, y el motor la
  rechaza sola porque reconoce su huella (`.private/holdouts/KNOWN_DEVELOPMENT.sha256`).
- **De empresas distintas**, y si puede ser de sectores distintos. Cinco plantillas de un mismo
  grupo cuentan como una.
- **Mejor variadas que fáciles.** Lo ideal es que al menos una o dos tengan alguna de estas dificultades:

| dificultad | qué prueba |
|---|---|
| varios patrones de diapositiva (masters) | que el motor use todos, no solo el primero |
| formato 4:3 | el reescalado |
| fondos oscuros o de color en contenido | si elige bien dónde dibujar gráficos |
| mucho grafismo (bandas, formas, logo grande) | la protección del grafismo y del logo |
| tipografía corporativa no estándar | la detección de la fuente y el aviso de sustitución |
| layouts con nombres poco claros | la clasificación por geometría, no por nombre |

### Qué debe llevar cada plantilla
- **Imprescindible:** el archivo de la plantilla, con todos sus masters y layouts, sin tocar.
- **Muy recomendable:**
  - **5–20 diapositivas de ejemplo de uso real** en el mismo archivo: portada, agenda,
    separador, gráfico, tabla, mensaje y cierre. Es la señal más fuerte de cómo se usa la plantilla.
  - **Si los ejemplos son confidenciales**, cambia textos y cifras, pero conserva el layout, la
    posición, la tipografía y los colores.
- **Opcional:**
  - La guía de marca en PDF.
  - O `marca.md`: tipografía, colores, logo, qué layout para qué y reglas de estilo.

  El desarrollador lo convierte en afirmaciones comparables (`expectations.json`) **antes** de
  ejecutar nada, solo para medir si el motor entendió la marca.

### Qué no hacer
- No arreglar ni limpiar la plantilla antes de entregarla.
- No decir de antemano qué layout es para qué, salvo en `marca.md`.
- No entregar archivos de fuentes, salvo los de licencia libre. Basta con el nombre.
- No entregarlas por partes: la prueba se ejecuta **una sola vez** por versión del motor.

### Qué se hace con ellas
1. Se fija el motor en una versión candidata (1.8.0-rc) antes de abrir nada.
2. Se copia cada plantilla a `.private/holdouts/corporate_unseen/<nombre>/` y se comprueba su
   huella para descartar la plantilla de desarrollo o plantillas ya vistas.
3. `cpe holdout corporate-run --record` se ejecuta una vez y, por cada plantilla:
   - lee y clasifica masters y layouts;
   - deduce tipografía, paleta, rejilla, logos y grafismo protegido, con sus conflictos;
   - renderiza la plantilla original (sustitución de fuentes);
   - genera un deck de prueba de unas 12 diapositivas con contenido sintético.
4. Se sacan dos informes por plantilla:
   - **uso:** cuántas diapositivas usan el layout propio, cuántas se adaptan y cuántas recurren
     al layout del motor, con el motivo de cada una;
   - **fidelidad:** tipografía, colores, márgenes, logo, portada y separadores, y colores de gráficos.
5. Solo se registran los agregados anónimos. Los fallos pasan a la deuda de v1.9: **el motor no se
   corrige con estas plantillas dentro de v1.8.**

---

## Entrega 2 — Proyecto real desordenado (1–2)

### El caso ideal
Un proyecto real, o uno real anonimizado, en el que ya hubo un deck y ahora hay datos nuevos y hay
que actualizarlo. Por ejemplo:
- el comité del trimestre pasado, que toca rehacer con el nuevo cierre;
- un business case que hay que revisar con el presupuesto aprobado.

### Qué incluye

| pieza | | detalle |
|---|---|---|
| `deck_anterior.pptx` | obligatorio | el deck que se presentó de verdad, hecho por personas |
| `fuentes_nuevas/` | obligatorio | lo llegado desde entonces: ERP / CRM (Excel, CSV), PDFs, actas, correos y notas (`.md` / `.txt`), presupuestos; 5–30 archivos, que pueden ser grandes |
| `fuentes_anteriores/` | recomendable | en qué se basaba el deck antiguo; distingue "cambió" de "nunca tuvo fuente" |
| `brief.md` | obligatorio | audiencia, decisión, qué ha cambiado, restricciones, formato y plazo |
| `respuesta.md` | obligatorio, **entregado después** | la clave de respuesta ciega |

### El desorden que se quiere ver (no limpiarlo)
- **Periodos mezclados:** fiscal y natural, últimos 12 meses, acumulado del año, trimestres, run-rate.
- **Bases mezcladas:** real, presupuesto, previsión, gestión frente a auditado.
- **Fuentes que se contradicen.**
- **Tablas reales:** cabeceras de dos niveles, totales, subtotales y celdas "n/d".
- **Unidades mezcladas** (k€ / M€, % / puntos) y coma decimal.
- **Gráficos metidos** en Word, Excel o PowerPoint.
- **Cifras en texto corrido.**
- **Números del deck antiguo** que ya no valen, y alguno que nunca tuvo fuente.

### Confidencialidad
- Se pueden cambiar nombres de empresa, personas y marcas.
- **Si se cambian cifras, igual en todos los archivos** (p. ej. todo × 0,8), y se dice en `brief.md`.
  Cambiar una cifra en un archivo y no en los demás crea una contradicción falsa.
- **No eliminar las contradicciones reales:** son la prueba.

### La clave de respuesta
`respuesta.md` debe contener:
1. qué ha cambiado de verdad;
2. qué números del deck antiguo siguen valiendo;
3. las trampas conocidas;
4. la recomendación correcta;
5. qué hacer con cada diapositiva.

Se escribe **antes** de empezar y se entrega **después** de recibir el deck, para que la
evaluación sea ciega.

### Qué se hace con él
1. `cpe deck ingest deck_anterior.pptx`: estructura, titulares, gráficos y tablas con datos, y
   cada número.
2. `cpe reason facts fuentes_nuevas/`: el modelo de datos, con periodos, bases y conflictos tipados.
3. `cpe deck stale`: el plan de actualización.
   - Cada número queda como vigente, desactualizado o sin fuente.
   - Cada diapositiva queda como mantener, actualizar o revisar.
4. Una ejecución completa con el protocolo 1.4:
   - el deck nuevo, con cada cifra atada a su dato;
   - la comprobación de razonamiento, con 0 errores graves;
   - el render con QA visual.
5. Se entregan:
   - el deck actualizado (.pptx y PDF);
   - el plan de cambios;
   - los conflictos encontrados y cómo se resolvieron.
6. El responsable entrega `respuesta.md` y se comparan.

---

## Entrega 3 — Criterio del responsable

Con los resultados se entregan los archivos de revisión, ya prellenados con lo que hizo el motor:

- **`revision_plantilla.md`, uno por plantilla.** Por diapositiva:
  - veredicto: ✅ el layout de un diseñador de la marca, 🟡 aceptable, ❌ incorrecto;
  - si es ❌, qué layout habría elegido.

  Además:
  - una nota de 1 a 5 a "¿parece un deck de la propia empresa?", con el porqué;
  - si alguna métrica de fidelidad no cuadra con lo que se ve.
- **`revision_proyecto.md`.** Número a número:
  - si el plan de cambios acertó frente a la clave;
  - qué no vio y qué cambió sin motivo.

  Además:
  - ¿se presentaría tal cual?
  - ¿respeta lo bueno del deck anterior?
  - ¿llega a la recomendación correcta?

Se registra como el juicio de un único evaluador experto, sin inventar votos. En público solo
van los agregados: % de diapositivas con layout correcto, nota media de parecido con la marca y
acierto del plan de cambios.

---

## Cuándo se cierra v1.8
1. Las 3–5 plantillas se han ejecutado una vez sobre el motor fijado, sin fallos de render, con los
   agregados de uso y fidelidad registrados.
2. Al menos un proyecto real ha pasado la actualización completa con 0 errores graves, y está
   revisado contra su clave.
3. El criterio del responsable sobre layouts y marca está registrado.
4. Los hallazgos van a `docs/DEBT_V18.md`. Lo grave se arregla en una 1.8.1, sin volver a ejecutar
   las plantillas.
5. Se publica la versión 1.8.0.
