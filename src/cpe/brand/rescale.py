"""Rescale a template's masters and layouts to the engine canvas (same aspect ratio only).

Many corporate templates use the older 16:9 page of 10 × 5.625 in; the engine lays out on
13.333 × 7.5 in. When the aspect ratio matches (±1%), every geometric quantity of the
masters and layouts is multiplied by one factor — positions and sizes (a:off, a:ext,
a:chOff, a:chExt), font sizes (sz), spacing in points, text insets and line widths — so the
masters are used as-is at the engine size instead of being discarded. The ingest report
states the factor; PowerPoint's "Slide Size" dialog can scale the output back without
distortion.

Example slides are removed from the rescaled copy (they are analysed by the ingest, not
reused by the builder), which also drops media only they referenced.
"""
from __future__ import annotations

from pptx import Presentation
from pptx.util import Emu

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"

EMU_ATTRS = {("off", "x"), ("off", "y"), ("ext", "cx"), ("ext", "cy"), ("chOff", "x"), ("chOff", "y"), ("chExt", "cx"), ("chExt", "cy")}
INSETS = ("lIns", "tIns", "rIns", "bIns")


def _scale_tree(root, k: float) -> int:
    n = 0
    for el in root.iter():
        tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
        for attr in ("x", "y", "cx", "cy"):
            if (tag, attr) in EMU_ATTRS and el.get(attr) is not None:
                el.set(attr, str(int(round(int(el.get(attr)) * k))))
                n += 1
        if tag in ("rPr", "defRPr", "endParaRPr") and el.get("sz"):
            el.set("sz", str(max(100, int(round(int(el.get("sz")) * k / 50)) * 50)))  # half-point steps
            n += 1
        if tag == "spcPts" and el.get("val"):
            el.set("val", str(int(round(int(el.get("val")) * k))))
        if tag == "bodyPr":
            for a in INSETS:
                if el.get(a):
                    el.set(a, str(int(round(int(el.get(a)) * k))))
        if tag == "ln" and el.get("w"):
            el.set("w", str(int(round(int(el.get("w")) * k))))
        if tag in ("lvl1pPr", "lvl2pPr", "lvl3pPr", "lvl4pPr", "lvl5pPr", "lvl6pPr", "lvl7pPr", "lvl8pPr", "lvl9pPr"):
            for a in ("marL", "indent"):
                if el.get(a):
                    el.set(a, str(int(round(int(el.get(a)) * k))))
    return n


def rescale(src: str, dst: str, target_w_in: float = 13.333, drop_slides: bool = True) -> dict:
    prs = Presentation(src)
    w, h = prs.slide_width, prs.slide_height
    k = target_w_in * 914400 / w
    if drop_slides:
        lst = prs.slides._sldIdLst
        for sid in list(lst):
            prs.part.drop_rel(sid.rId)
            lst.remove(sid)
    n = 0
    for m in prs.slide_masters:
        n += _scale_tree(m._element, k)
        for lay in m.slide_layouts:
            n += _scale_tree(lay._element, k)
    prs.slide_width = Emu(int(round(w * k)))
    prs.slide_height = Emu(int(round(h * k)))
    prs.save(dst)
    return {"factor": round(k, 4), "from_in": [round(w / 914400, 3), round(h / 914400, 3)], "to_in": [round(w * k / 914400, 3), round(h * k / 914400, 3)], "values_scaled": n}
