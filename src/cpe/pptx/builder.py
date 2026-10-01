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
    """Default: python-pptx blank template. Brand theme: the corporate template's masters (all of them)."""
    tpl = theme.extras.get("template")
    if tpl:
        path = Path(theme.source_dir or ".") / tpl
        prs = Presentation(str(path))
        sldIdLst = prs.slides._sldIdLst
        for sldId in list(sldIdLst):  # drop the template's sample slides
            prs.part.drop_rel(sldId.rId)
            sldIdLst.remove(sldId)
        name, lid = theme.extras.get("base_layout"), theme.extras.get("base_layout_id")
        layouts = [l for m in prs.slide_masters for l in m.slide_layouts]
        by_id = _layouts_by_id(prs)
        blank = by_id.get(lid) or next((l for l in layouts if l.name == name), layouts[-1] if layouts else None)
        return prs, blank
    prs = Presentation()
    prs.slide_width = Emu(int(SLIDE_W * 914400))
    prs.slide_height = Emu(int(SLIDE_H * 914400))
    return prs, prs.slide_layouts[6]


def _layouts_by_id(prs) -> dict:
    return {f"m{mi + 1}.l{li + 1}": lay for mi, m in enumerate(prs.slide_masters) for li, lay in enumerate(m.slide_layouts)}


def _inherited_size(ph, default: float) -> float:
    """Font size the placeholder inherits (layout placeholder → master text style)."""
    from lxml import etree  # noqa: F401

    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    try:
        lp = ph._base_placeholder
        for el in (lp._element if lp is not None else None,):
            if el is not None:
                d = el.find(f".//{A}lstStyle/{A}lvl1pPr/{A}defRPr")
                if d is not None and d.get("sz"):
                    return int(d.get("sz")) / 100
        master = ph.part.slide_layout.slide_master
        tag = "titleStyle" if ph.placeholder_format.type in (1, 3) else "bodyStyle"  # TITLE, CENTER_TITLE
        d = master._element.find(f"{P}txStyles/{P}{tag}/{A}lvl1pPr/{A}defRPr")
        if d is not None and d.get("sz"):
            return int(d.get("sz")) / 100
    except Exception:
        pass
    return default


def _effective_colors(ph, slide) -> tuple[str | None, str | None]:
    """(inherited text colour of a placeholder, background colour behind it) through layout → master."""
    from ..brand.model import _color_of, background, theme_of_master

    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
    lay = slide.slide_layout
    master = lay.slide_master
    th = theme_of_master(master)
    bg = None
    for el in (lay._element, master._element):
        b = background(el, th)
        if b and b.get("color"):
            bg = b["color"]
            break
    text = None
    chain = []
    try:
        base = ph._base_placeholder
        chain.append(base._element if base is not None else None)
        mb = base._base_placeholder if base is not None else None
        chain.append(mb._element if mb is not None else None)
    except Exception:
        pass
    for el in [e for e in chain if e is not None]:
        d = el.find(f".//{A}lstStyle/{A}lvl1pPr/{A}defRPr")
        if d is not None and d.find(f"{A}solidFill") is not None:
            text = _color_of(d.find(f"{A}solidFill"), th)
            break
    if text is None:
        tag = "titleStyle" if ph.placeholder_format.type in (1, 3) else "bodyStyle"
        d = master._element.find(f"{P}txStyles/{P}{tag}/{A}lvl1pPr/{A}defRPr")
        if d is not None and d.find(f"{A}solidFill") is not None:
            text = _color_of(d.find(f"{A}solidFill"), th)
    return text or th["colors"].get("dk1"), bg


def _native_slide(slide, s: dict, meta: dict, m: Manifest, theme) -> None:
    """Fill the corporate layout's own placeholders: the slide inherits the template's typography and look."""
    from ..design import text_metrics as tm

    kind = s.get("kind")
    if kind == "cover":
        main, sub = s.get("title") or meta.get("title", ""), " · ".join(x for x in (s.get("subtitle") or meta.get("subtitle"), meta.get("client"), meta.get("date")) if x)
    elif kind in ("divider", "appendix_divider"):
        main, sub = s.get("title") or s.get("headline", ""), s.get("subtitle") or ""
    elif kind == "closing":
        main, sub = s.get("title") or s.get("headline") or s.get("text") or "", s.get("subtitle") or s.get("support") or ""
    else:  # statement
        main, sub = s.get("text") or s.get("headline", ""), s.get("support") or s.get("attribution") or ""
    phs = list(slide.placeholders)
    title = next((p for p in phs if p.placeholder_format.type in (1, 3)), None)
    subp = next((p for p in phs if p.placeholder_format.type == 4), None) or next((p for p in phs if p.placeholder_format.type in (2, 7) and p is not title), None)
    for n, (ph, text, role, default) in enumerate(((title, main, "title", 32.0), (subp, sub, "subtitle", 16.0))):
        if ph is None or not text:
            continue
        ph.text_frame.text = text
        size = _inherited_size(ph, default)
        w, h = Emu(ph.width).inches, Emu(ph.height).inches
        fit = tm.largest_fitting_size([text], max(0.5, w - 0.2), max(0.3, h - 0.1), size, max(10.0, size * 0.6), bold=role == "title") or max(10.0, size * 0.6)
        from pptx.dml.color import RGBColor

        from ..design.tokens import contrast_ratio

        txt_c, bg_c = _effective_colors(ph, slide)
        override = None
        if txt_c and bg_c and contrast_ratio(txt_c, bg_c) < 4.5:  # the template's own pairing is unreadable here
            override = max(("FFFFFF", theme.c("text")), key=lambda c: contrast_ratio(c, bg_c))
            m.warnings.append({"level": "info", "code": "NATIVE_TEXT_COLOR", "message": f"{role}: inherited #{txt_c} on #{bg_c} ({contrast_ratio(txt_c, bg_c):.1f}:1) → #{override}"})
        for p_ in ph.text_frame.paragraphs:
            for r in p_.runs:
                r.font.size = Emu(int(fit * 12700))
                if override:
                    r.font.color.rgb = RGBColor.from_string(override)
        ph.name = f"cpe|{role}|text|{n + 1}"
        m.zones[role] = {"role": "statement" if role == "title" else "subtitle", "x": round(Emu(ph.left).inches, 3), "y": round(Emu(ph.top).inches, 3), "w": round(w, 3), "h": round(Emu(ph.height).inches, 3)}
    for ph in list(slide.placeholders):  # nothing empty is left behind
        if not ph.name.startswith("cpe|"):
            ph._element.getparent().remove(ph._element)


def build(resolved: dict, out_path: str | Path) -> list[dict]:
    meta = resolved.get("meta", {})
    theme = theme_for(meta)
    activate(theme)
    profile = resolved.get("_profile") or {}
    prs, blank = _base_presentation(theme)
    corp = (theme.extras.get("corporate") or {}) if theme.extras.get("template") else {}
    by_id = _layouts_by_id(prs) if corp.get("layouts") else {}
    corp_layouts = {c["id"]: c for c in corp.get("layouts") or []}
    manifests: list[dict] = []
    for s in resolved["slides"]:
        kind = s.get("kind", "content")
        decision = None
        base = blank
        if corp_layouts and not s.get("corporate_layout") == "off":
            from ..brand.matching import choose
            from ..qa.archetypes import classify

            decision = choose(s, classify(s)[0] if kind in ("content", "exec_summary") else None, corp, GRID)
            forced = (s.get("_compose") or {}).get("corporate")
            if forced and forced in corp_layouts and decision.get("mode") == "adaptive":  # chosen by the composition engine after rendering
                from ..brand.matching import limits

                lay = corp_layouts[forced]
                decision = {**decision, "layout": lay["name"], "layout_id": forced, "master": lay["master"], "limits": limits(lay, GRID),
                            "why": "chosen by the composition engine among corporate layouts (render + QA + archetype fitness)"}
            if decision.get("layout_id") in by_id:
                base = by_id[decision["layout_id"]]
        slide = prs.slides.add_slide(base)
        lay_id = (s.get("_plan") or {}).get("layout", {}).get("id", kind) if s.get("_plan") and s["_plan"].get("layout") else kind
        m = Manifest(slide_id=s.get("id", ""), layout=lay_id)
        if decision:
            m.corporate = decision
            if decision["mode"] == "adaptive":
                m.reserved = corp_layouts[decision["layout_id"]]["reserved"]
        if decision and decision["mode"] == "native":
            m.layout = f"corporate:{decision['layout']}"
            m.reserved = []
            _native_slide(slide, s, meta, m, theme)
            notes = s.get("notes") or " ".join(x for x in (s.get("purpose"), s.get("supporting_message")) if x)
            if notes:
                slide.notes_slide.notes_text_frame.text = notes
            manifests.append(m.to_dict())
            continue
        for ph in list(slide.placeholders):  # the engine draws its own content; no empty "Click to add…" boxes
            ph._element.getparent().remove(ph._element)
        saved = {k: getattr(GRID, k, None) for k in ("headline_right_limit", "footer_right_limit")}
        if decision and decision.get("limits"):  # keep clear of THIS layout's corner artwork
            for k, v in decision["limits"].items():
                cur = getattr(GRID, k, None)
                setattr(GRID, k, min(v, cur) if cur else v)
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
            box = Box(GRID.col_x(1), GRID.body_y, GRID.span_w(1, 9), GRID.body_h)  # aligned with the headline
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
        for k, v in saved.items():
            setattr(GRID, k, v)
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
