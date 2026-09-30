"""PPTX builder: resolved slide specifications → native .pptx + build manifest."""
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

from ..charts import native as charts
from ..design.tokens import GRID, SLIDE_H, SLIDE_W, activate, theme_for
from ..diagrams import diagrams
from ..layout.engine import Box, get_layout, resolve_zones
from ..spec import VISUAL_TYPES, slide_exhibits
from ..tables import table as tables
from . import text_components as tc
from .painter import Manifest, Painter

TABLE_TYPES = {"table", "heatmap", "harvey_table", "scorecard"}


def render_exhibit(p: Painter, box: Box, ex: dict) -> dict:
    vt = ex["type"]
    if vt in TABLE_TYPES:
        return tables.render(p, box, ex)
    if vt in diagrams.RENDERERS:
        return diagrams.render(p, box, ex)
    if VISUAL_TYPES.get(vt) == "chart":
        return charts.render(p, box, ex)
    if vt == "kpi":
        tc.kpis(p, box, ex.get("data") or ex)
        return {"type": "kpi"}
    if vt == "bullets":
        tc.commentary(p, box, {"points": (ex.get("data") or {}).get("points") or ex.get("points"), "title": ex.get("title")}, style="plain")
        return {"type": "bullets"}
    if vt == "statements":
        tc.statements(p, box, ex.get("data") or {})
        return {"type": "statements"}
    raise ValueError(f"No renderer for visual type '{vt}'")


def _content_slide(p: Painter, s: dict, meta: dict) -> None:
    from ..core.layout_selector import content_roles

    lay = get_layout(s["_plan"]["layout"]["id"])
    zones = resolve_zones(lay, with_takeaway=bool(s.get("takeaway")), has_subheadline=bool(s.get("subheadline")))
    roles = content_roles(s)
    _adapt_columns_zone(p, zones, roles)
    p.manifest.zones = {n: {"role": z.role, **z.box.to_dict()} for n, z in zones.items()}
    tc.chrome(p, s, s.get("_page", 0), meta)
    ex_iter = iter(roles.get("exhibit") or [])
    col_iter = iter(roles.get("column") or [])
    for name in lay.hierarchy + [n for n in zones if n not in lay.hierarchy]:
        z = zones.get(name)
        if z is None:
            continue
        pz = p.for_zone(name)
        if z.role == "exhibit":
            ex = next(ex_iter, None)
            if ex is not None:
                info = render_exhibit(pz, z.box, ex)
                p.manifest.exhibits.append({"zone": name, **info})
        elif z.role == "commentary" and roles.get("commentary"):
            tc.commentary(pz, z.box, roles["commentary"], style=z.style)
        elif z.role == "kpis" and roles.get("kpis"):
            tc.kpis(pz, z.box, (roles["kpis"].get("data") or roles["kpis"]) if isinstance(roles["kpis"], dict) else roles["kpis"])
        elif z.role == "column":
            col = next(col_iter, None)
            if col is not None:
                tc.column(pz, z.box, col)
        elif z.role == "statements" and roles.get("statements"):
            data = dict(roles["statements"].get("data") or {})
            if lay.id == "exec_summary_scr":
                data.setdefault("style", "scr")
            tc.statements(pz, z.box, data)
        elif z.role == "statement" and roles.get("statement"):
            st = roles["statement"]
            tc.statement(pz, z.box, {"type": st.get("type"), **(st.get("data") or {})})
        elif z.role == "takeaway" and s.get("takeaway"):
            tc.takeaway(pz, z.box, s["takeaway"])


def _adapt_columns_zone(p: Painter, zones: dict, roles: dict) -> None:
    """Takeaway columns under a full-width exhibit only take the height they need;
    the exhibit gets the rest (no dead band at the bottom of the slide)."""
    from ..design.tokens import SPACING

    cz = next((z for z in zones.values() if z.role == "commentary" and z.style == "columns"), None)
    ez = next((z for z in zones.values() if z.role == "exhibit" and abs(z.box.b - (cz.box.y if cz else 0)) < 0.5), None) if cz else None
    if not cz or not ez or not roles.get("commentary"):
        return
    pts = roles["commentary"].get("points") or []
    n = max(1, len(pts))
    cw = (cz.box.w - GRID.gutter * (n - 1)) / n
    need = max((p.measure(pt if isinstance(pt, str) else pt.get("text", ""), "body", cw)[0] for pt in pts), default=0) + SPACING["S"] + 0.1
    if roles["commentary"].get("title"):
        need += p.measure(roles["commentary"]["title"], "exhibit_title", cz.box.w)[0] + SPACING["XS"]
    spare = cz.box.h - need
    if spare > 0.2:
        shift = spare - 0.05
        cz.box = Box(cz.box.x, cz.box.y + shift, cz.box.w, cz.box.h - shift)
        ez.box = Box(ez.box.x, ez.box.y, ez.box.w, ez.box.h + shift)


def _base_presentation(theme):
    """Default: python-pptx blank template. Brand theme: the corporate template's masters."""
    tpl = theme.extras.get("template")
    if tpl:
        path = Path(theme.source_dir or ".") / tpl
        prs = Presentation(str(path))
        sldIdLst = prs.slides._sldIdLst
        for sldId in list(sldIdLst):  # drop the template's sample slides
            prs.part.drop_rel(sldId.rId)
            sldIdLst.remove(sldId)
        name = theme.extras.get("base_layout")
        layouts = [l for m in prs.slide_masters for l in m.slide_layouts]
        blank = next((l for l in layouts if l.name == name), layouts[-1] if layouts else None)
        return prs, blank
    prs = Presentation()
    prs.slide_width = Emu(int(SLIDE_W * 914400))
    prs.slide_height = Emu(int(SLIDE_H * 914400))
    return prs, prs.slide_layouts[6]


def build(resolved: dict, out_path: str | Path) -> list[dict]:
    meta = resolved.get("meta", {})
    theme = theme_for(meta)
    activate(theme)
    profile = resolved.get("_profile") or {}
    prs, blank = _base_presentation(theme)
    manifests: list[dict] = []
    for s in resolved["slides"]:
        slide = prs.slides.add_slide(blank)
        for ph in list(slide.placeholders):  # the engine draws its own content; no empty "Click to add…" boxes
            ph._element.getparent().remove(ph._element)
        kind = s.get("kind", "content")
        lay_id = (s.get("_plan") or {}).get("layout", {}).get("id", kind) if s.get("_plan") and s["_plan"].get("layout") else kind
        m = Manifest(slide_id=s.get("id", ""), layout=lay_id)
        comp = s.get("_compose") or {}
        prof = {**profile, **({"body_scale": comp["scale"]} if comp.get("scale") else {}), **({"table_stretch": comp["table_stretch"]} if comp.get("table_stretch") else {})}
        p = Painter(slide, theme, prof, m)
        if kind == "cover":
            tc.cover(p, s, meta)
        elif kind in ("divider", "appendix_divider"):
            tc.divider(p, s, meta)
        elif kind == "agenda":
            s.setdefault("headline", s.get("title", "Agenda"))
            tc.chrome(p, {**s, "tracker": s.get("tracker")}, s.get("_page", 0), meta)
            box = Box(GRID.col_x(2), GRID.body_y, GRID.span_w(2, 10), GRID.body_h)
            m.zones = {"text": {"role": "agenda", **box.to_dict()}}
            tc.agenda(p.for_zone("text"), box, s.get("items") or [], s.get("current"))
        elif kind in ("statement", "closing") and not slide_exhibits(s):
            lay = get_layout("statement")
            zones = resolve_zones(lay)
            m.zones = {n: {"role": z.role, **z.box.to_dict()} for n, z in zones.items()}
            if s.get("headline"):
                tc.chrome(p, s, s.get("_page", 0), meta)
            tc.statement(p.for_zone("text"), zones["text"].box, {"text": s.get("text") or s.get("title", ""), "support": s.get("support"), "type": s.get("style", "statement"), "attribution": s.get("attribution")})
        else:
            _content_slide(p, s, meta)
        notes = s.get("notes") or " ".join(x for x in (s.get("purpose"), s.get("supporting_message")) if x)
        if notes:
            slide.notes_slide.notes_text_frame.text = notes
        manifests.append(m.to_dict())
    cp = prs.core_properties
    cp.title = meta.get("title", "")
    cp.subject = resolved.get("storyline", {}).get("governing_thought", "")[:250]
    cp.author = meta.get("author", "Consulting Presentation Engine")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return manifests


def save_manifest(manifests: list[dict], path: str | Path) -> None:
    Path(path).write_text(json.dumps(manifests, indent=2, ensure_ascii=False))
