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
- `output/`: the generated deck (on the template's masters, with the logo and bar kept) and its QA
  report, including the protected logo area (`BRAND_RESERVED_OVERLAP`).
