"""Render the same spec twice with the same engine in the same environment and compare.

    cpe repro examples/alvora/deck.json -o out/repro

Checked, with explicit tolerances (docs/REPRODUCIBILITY.md):
  slide count            equal
  PNG dimensions         equal
  PNG content hash       equal (the renderer is expected to be deterministic)
  pixel difference       share of differing pixels ≤ PIXEL_TOLERANCE (0: exact)
  PDF text layout        every span's text, font size and position equal (±0.01 in)
  composition metrics    every slide score / metric equal (±METRIC_TOLERANCE)
  QA result              same verdict, same issue codes per slide

The PDF bytes themselves are NOT compared: LibreOffice stamps a creation date and a
document id into every PDF. Everything the engine reads from the PDF is compared instead.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

PIXEL_TOLERANCE = 0.0  # share of pixels allowed to differ; 0 = pixel-identical
METRIC_TOLERANCE = 0.0  # composition metric difference allowed
POSITION_TOLERANCE = 0.01  # inches, PDF span positions


def _sha(p: str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _pixel_diff(a: str, b: str) -> tuple[float, int]:
    from PIL import Image, ImageChops

    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 1.0, 255
    d = ImageChops.difference(ia, ib)
    bbox = d.getbbox()
    if not bbox:
        return 0.0, 0
    px = d.load()
    n = mx = 0
    for y in range(d.height):
        for x in range(d.width):
            v = max(px[x, y])
            if v:
                n += 1
                mx = max(mx, v)
    return n / (d.width * d.height), mx


def _spans(pdf: str) -> list[list[tuple]]:
    import pymupdf

    out = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            sp = []
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    for s in line.get("spans", []):
                        if s["text"].strip():
                            sp.append((s["text"], round(s["size"], 2), *(round(v / 72, 3) for v in s["bbox"])))
            out.append(sp)
    return out


def _one_run(spec: dict, out: Path, dpi: int) -> dict:
    from .pipeline import run

    rep = run(spec, out, max_iter=1, dpi=dpi, verbose=False, compose=False)
    return {"report": rep, "pngs": rep["artifacts"]["pngs"], "pdf": rep["artifacts"]["pdf"]}


def check(spec: dict, out_dir: str | Path | None = None, dpi: int = 80) -> dict:
    from PIL import Image

    from . import environment

    base = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="cpe_repro_"))
    runs = [_one_run(spec, base / f"run{i}", dpi) for i in (1, 2)]
    a, b = runs
    res: dict = {"environment_fingerprint": environment.fingerprint(environment.manifest()), "checks": {}, "slides": []}
    c = res["checks"]
    c["slide_count"] = len(a["pngs"]) == len(b["pngs"])
    dims = [(Image.open(x).size, Image.open(y).size) for x, y in zip(a["pngs"], b["pngs"])]
    c["dimensions"] = all(p == q for p, q in dims)
    worst = 0.0
    hashes_equal = True
    for i, (x, y) in enumerate(zip(a["pngs"], b["pngs"]), 1):
        same = _sha(x) == _sha(y)
        hashes_equal &= same
        share, mx = (0.0, 0) if same else _pixel_diff(x, y)
        worst = max(worst, share)
        res["slides"].append({"slide": i, "png_hash_equal": same, "pixel_diff_share": round(share, 6), "max_channel_diff": mx})
    c["png_hashes"] = hashes_equal
    c["pixel_diff"] = worst <= PIXEL_TOLERANCE
    res["worst_pixel_diff_share"] = worst
    sa, sb = _spans(a["pdf"]), _spans(b["pdf"])
    c["pdf_text_layout"] = len(sa) == len(sb) and all(
        len(p) == len(q) and all(u[0] == v[0] and u[1] == v[1] and all(abs(m - n) <= POSITION_TOLERANCE for m, n in zip(u[2:], v[2:])) for u, v in zip(p, q))
        for p, q in zip(sa, sb))
    ca = {s["slide_id"]: s for s in (a["report"].get("composition") or {}).get("slides", [])}
    cb = {s["slide_id"]: s for s in (b["report"].get("composition") or {}).get("slides", [])}
    metric_ok = set(ca) == set(cb)
    for sid in ca:
        if sid in cb:
            metric_ok &= abs(ca[sid]["score"] - cb[sid]["score"]) <= METRIC_TOLERANCE
            metric_ok &= all(abs(v - cb[sid]["metrics"].get(k, -9)) <= METRIC_TOLERANCE for k, v in ca[sid]["metrics"].items())
    c["composition_metrics"] = metric_ok

    def codes(rep):
        return sorted((i.get("slide") or "", i["code"], i["level"]) for i in rep["issues"])

    c["qa_result"] = a["report"]["passed"] == b["report"]["passed"] and codes(a["report"]) == codes(b["report"])
    res["passed"] = all(c.values())
    res["tolerances"] = {"pixel_diff_share": PIXEL_TOLERANCE, "composition_metric": METRIC_TOLERANCE, "pdf_span_position_in": POSITION_TOLERANCE}
    (base / "repro_report.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res
