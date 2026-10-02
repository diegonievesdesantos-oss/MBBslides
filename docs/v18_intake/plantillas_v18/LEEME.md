# Plantillas corporativas para v1.8 — cómo montar el zip

Copia la carpeta `plantilla_A/` una vez por plantilla (`plantilla_B/`, `plantilla_C/`…),
de 3 a 5 plantillas, cada una de una empresa distinta.

```
plantillas_v18.zip
  plantilla_A/
    template.pptx      ← OBLIGATORIO: la plantilla tal cual (si es .potx, renómbrala a template.potx)
    marca.md           ← opcional: lo que sepas de la marca (ver el archivo)
    guia_marca.pdf     ← opcional: la guía de marca oficial, si existe
  plantilla_B/
    …
```

## Lista de comprobación por plantilla
- [ ] Es una plantilla real que usa una empresa (no JET, no una de Office genérica).
- [ ] El motor no la ha visto nunca en este proyecto.
- [ ] Contiene todos sus masters y layouts, sin tocar ni limpiar.
- [ ] Lleva entre 5 y 20 diapositivas de ejemplo de uso real (portada, agenda, separador,
      gráfico, tabla, mensaje, cierre). Si son confidenciales, has cambiado los textos y las
      cifras pero has mantenido el layout, la posición, la tipografía y los colores.
- [ ] La carpeta tiene un nombre anónimo (plantilla_A…), sin el nombre de la empresa.
- [ ] No incluye archivos de fuentes, salvo que sean de licencia libre.

## No hagas
- No arregles la plantilla antes de dármela.
- No me digas qué layout es para qué fuera de `marca.md`.
- No me la des por partes: la prueba se ejecuta una sola vez por versión del motor.

Súbelo al chat como un solo zip. Todo se queda en `.private/` y solo se publican totales anónimos.
Detalle completo: `docs/V18_OWNER_BRIEF.md`.
