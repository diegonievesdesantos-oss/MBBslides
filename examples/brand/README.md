# Brand example — the demo deck on a corporate template

`kestrel_template.pptx` is a **fictitious** corporate template produced by
`scripts/make_sample_template.py`. Like real ones, it has custom theme colours, a heading font that is
usually not installed (Georgia) with a Calibri body, a logo and a bar on the master, custom title
positions and a gradient background on one layout.

```bash
scripts/cpe brand ingest examples/brand/kestrel_template.pptx -o examples/brand/kestrel --name "Kestrel Capital"
scripts/cpe run examples/brand/alvora_on_kestrel.json -o examples/brand/output
```

- [`kestrel/compatibility.md`](kestrel/compatibility.md): what was detected and what is approximated.
  Calibri is measured exactly (Carlito). Georgia is missing, so it is measured with the font the
  renderer will substitute (DejaVu Serif) and flagged as approximate.
- `kestrel/theme.json`: the brand theme. `alvora_on_kestrel.json` is the Alvora deck spec with
  `"meta": {"brand": "kestrel"}`.
- `kestrel/brand_model.json`, `kestrel/layout_catalog.json`: the full brand model (layout features,
  classification, typography / palette / grid inference, assets, rules).
- `output/`: the generated deck and its QA report. The cover is **native** (the template's own
  "Title Slide" layout and placeholders, with the text colour corrected because the template's own
  pairing is unreadable on its gradient); content slides are **adaptive** on the template's
  "Title Only" layout; `build_manifest.json` → `corporate` gives the reason per slide.

A synthetic **three-master** template for tests and experiments: `src/cpe/brand/fixtures.py`
(`make_multimaster(path)`), see [docs/BRAND_INGESTION.md](../../docs/BRAND_INGESTION.md).
