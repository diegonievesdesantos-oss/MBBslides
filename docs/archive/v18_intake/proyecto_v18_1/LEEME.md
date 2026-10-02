# Proyecto real para v1.8 — cómo montar el zip

```
proyecto_v18_1.zip
  brief.md              ← OBLIGATORIO (rellena la plantilla)
  deck_anterior.pptx    ← OBLIGATORIO: el deck que se presentó de verdad
  fuentes_nuevas/       ← OBLIGATORIO: lo que ha llegado desde entonces (5-30 archivos)
  fuentes_anteriores/   ← recomendable: en qué se basaba el deck antiguo
```

`respuesta.md` **no va en el zip**: escríbelo antes y guárdalo hasta que te entregue el resultado.

## Qué sirve en fuentes_nuevas/
- Exportaciones de ERP o CRM (Excel, CSV); pueden ser grandes, se analizan con scripts.
- PDFs (informes, cuentas, presupuestos).
- Actas, correos y notas, pasados a `.md` o `.txt`.
- Excel o Word con gráficos dentro.

## El desorden que quiero ver (no lo limpies)
- [ ] Periodos mezclados: fiscal y natural, últimos 12 meses, acumulado, trimestres, run-rate.
- [ ] Bases mezcladas: real, presupuesto, previsión, gestión frente a auditado.
- [ ] Fuentes que se contradicen.
- [ ] Tablas con cabeceras de dos niveles, totales, subtotales y celdas "n/d".
- [ ] Unidades mezcladas (k€ / M€, % / puntos) y coma decimal.
- [ ] Gráficos metidos en Word, Excel o PowerPoint.
- [ ] Cifras en texto corrido.
- [ ] Números del deck antiguo que ya no valen, y alguno que nunca tuvo fuente.

## Confidencialidad
- Puedes cambiar nombres de empresa, personas y marcas.
- Si cambias cifras, hazlo igual en todos los archivos (p. ej. todo × 0,8) y dilo en `brief.md`.
- No elimines las contradicciones reales: son la prueba.
- Todo se queda en `.private/`; en público solo salen totales.

Coste: una ejecución de agente por proyecto, como Brasa. Detalle completo: `docs/V18_OWNER_BRIEF.md`.
