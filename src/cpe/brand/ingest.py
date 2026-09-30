"""Brand ingestion: corporate .pptx template → engine theme + compatibility report.

    cpe brand ingest template.pptx -o brands/acme

produces
    brands/acme/theme.json          engine theme (colours, fonts, grid, reserved areas, template)
    brands/acme/template.pptx       copy of the template (decks are generated on its masters)
    brands/acme/compatibility.md    human report   (+ compatibility.json)

The report makes every approximation explicit so the engine never silently
produces a different deck: fonts detected / available / missing and the
fallback used for measurement and rendering, theme colours and how they were
mapped to roles, slide size, master layouts and recognised placeholders, logos
and other master artwork (turned into reserved areas the QA protects), and
elements the engine does not use.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Emu

from ..design import text_metrics as tm
from ..design.tokens import SLIDE_H, SLIDE_W, contrast_ratio, hex_to_rgb, interpolate, load_theme

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
SCHEME_SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"]
IN = 914400


def _in(v) -> float:
    return round(Emu(v).inches, 3)


def _theme_xml(prs):
    master = prs.slide_masters[0]
    part = master.part.part_related_by(RT.THEME)
    return etree.fromstring(part.blob)


def read_theme(prs) -> dict:
    root = _theme_xml(prs)
    colors = {}
    cs = root.find(f".//{A}clrScheme")
    for slot in SCHEME_SLOTS:
        el = cs.find(f"{A}{slot}") if cs is not None else None
        if el is None:
            continue
        c = el.find(f"{A}srgbClr")
        if c is not None:
            colors[slot] = c.get("val").upper()
        else:
            s = el.find(f"{A}sysClr")
            if s is not None:
                colors[slot] = (s.get("lastClr") or ("000000" if s.get("val") == "windowText" else "FFFFFF")).upper()
    fs = root.find(f".//{A}fontScheme")
    fonts = {}
    if fs is not None:
        for kind in ("majorFont", "minorFont"):
            lat = fs.find(f"{A}{kind}/{A}latin")
            ea = fs.find(f"{A}{kind}/{A}ea")
            fonts[kind] = {"latin": lat.get("typeface") if lat is not None else None, "ea": (ea.get("typeface") or None) if ea is not None else None}
    return {"colors": colors, "fonts": fonts, "scheme_name": cs.get("name") if cs is not None else None}


def installed_font_families() -> set[str]:
    try:
        out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=20).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    fams = set()
    for line in out.splitlines():
        for f in line.split(","):
            fams.add(f.strip().lower())
    return fams


def fc_match(name: str) -> str:
    try:
        r = subprocess.run(["fc-match", "-f", "%{family}", name], capture_output=True, text=True, timeout=10)
        return r.stdout.split(",")[0].strip() or "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown (fontconfig not available)"


def font_report(name: str | None, installed: set[str]) -> dict:
    if not name:
        return {"font": None}
    low = name.lower()
    fam = tm.FONT_ALIASES.get(low)
    installed_ok = low in installed
    metric = low in tm.METRIC_COMPATIBLE
    measure = fam if fam and tm.family_available(fam) else "LiberationSans"
    if not installed_ok and not metric:
        # the deck will be RENDERED here with the fontconfig substitute: measure with it when we can
        sub = tm.FONT_ALIASES.get(fc_match(name).lower())
        if sub and tm.family_available(sub):
            measure = sub
    exact_measure = bool(fam) and tm.family_available(fam) and (metric or installed_ok)
    # what the renderer will actually draw with when the font itself is missing
    render_fallback = None if installed_ok else fc_match(name)
    status = "available" if installed_ok else ("metric-compatible substitute" if metric and fam and tm.family_available(fam) else "missing")
    return {
        "font": name,
        "installed": installed_ok,
        "status": status,
        "measure_family": measure,
        "measurement": "exact" if exact_measure else "approximate",
        "render_fallback": render_fallback,
    }


def _saturation(h: str) -> float:
    r, g, b = [c / 255 for c in hex_to_rgb(h)]
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def _lum(h: str) -> float:
    r, g, b = hex_to_rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _hue(h: str) -> float:
    import colorsys

    r, g, b = [c / 255 for c in hex_to_rgb(h)]
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def map_colors(scheme: dict, base) -> tuple[dict, dict, list[str]]:
    """Theme scheme → engine roles. Returns (colors, series, notes)."""
    notes = []
    text = scheme.get("dk1", base.c("text"))
    bg = scheme.get("lt1", "FFFFFF")
    accents = [scheme[k] for k in ("accent1", "accent2", "accent3", "accent4", "accent5", "accent6") if k in scheme]
    dark_candidates = [c for c in [scheme.get("dk2")] + accents if c and _lum(c) < 0.45 and contrast_ratio(c, bg) >= 4.5]
    primary = dark_candidates[0] if dark_candidates else base.c("primary")
    if not dark_candidates:
        notes.append("No dark brand colour with ≥4.5:1 contrast on the background: primary kept from the default theme.")
    def signal(c):  # reds and greens are reserved for negative / positive
        h = _hue(c)
        return (h <= 15 or h >= 340) or (90 <= h <= 170)

    vivid = sorted([c for c in accents if c != primary and _saturation(c) > 0.35], key=lambda c: (signal(c), -_saturation(c)))
    highlight = vivid[0] if vivid else base.c("highlight")
    secondary = next((c for c in accents if c not in (primary, highlight) and 0.2 < _lum(c) < 0.65), interpolate(primary, "FFFFFF", 0.35))
    greens = [c for c in accents if 90 <= _hue(c) <= 170 and _saturation(c) > 0.3]
    reds = [c for c in accents if (_hue(c) <= 15 or _hue(c) >= 340) and _saturation(c) > 0.35]
    colors = dict(base.colors)
    colors.update({
        "primary": primary, "secondary": secondary, "highlight": highlight,
        "text": text if contrast_ratio(text, bg) >= 7 else base.c("text"),
        "background": bg,
        "positive": greens[0] if greens else base.c("positive"),
        "negative": reds[0] if reds else base.c("negative"),
        "muted": interpolate(text, bg, 0.78), "faint": interpolate(text, bg, 0.93), "surface": interpolate(text, bg, 0.95),
        "rule": interpolate(text, bg, 0.68), "gridline": interpolate(text, bg, 0.88), "neutral": interpolate(text, bg, 0.5),
    })
    tm_ = interpolate(text, bg, 0.35)
    while contrast_ratio(tm_, bg) < 4.6:
        tm_ = interpolate(tm_, text, 0.2)
    colors["text_muted"] = tm_
    if contrast_ratio(highlight, bg) < 3:
        notes.append(f"Highlight #{highlight} has contrast {contrast_ratio(highlight, bg):.1f}:1 — used for fills only; text in it may be flagged by QA.")
    series = [primary, secondary, interpolate(primary, bg, 0.55), colors["muted"], highlight, colors["neutral"]]
    return colors, series, notes


def _shape_kind(sh) -> str:
    if sh.is_placeholder:
        return "placeholder"
    if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
        return "picture"
    if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
        return "group"
    if getattr(sh, "has_chart", False) and sh.has_chart:
        return "chart"
    if sh.shape_type in (MSO_SHAPE_TYPE.TABLE, MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT, MSO_SHAPE_TYPE.MEDIA) or sh._element.tag.endswith("graphicFrame"):
        return "graphic_frame"
    if sh.has_text_frame and sh.text_frame.text.strip():
        return "text"
    return "shape"


def _box(sh) -> dict:
    return {"x": _in(sh.left or 0), "y": _in(sh.top or 0), "w": _in(sh.width or 0), "h": _in(sh.height or 0)}


def _bg_kind(el) -> str | None:
    bg = el.find(f"{P}cSld/{P}bg")
    if bg is None:
        return None
    if bg.find(f".//{A}blipFill") is not None:
        return "picture background"
    if bg.find(f".//{A}gradFill") is not None:
        return "gradient background"
    return "solid background"


def read_structure(prs) -> dict:
    master = prs.slide_masters[0]
    out = {"master": {"artwork": [], "background": _bg_kind(master._element), "placeholders": []}, "layouts": [], "unsupported": []}
    for sh in master.shapes:
        k = _shape_kind(sh)
        if k == "placeholder":
            out["master"]["placeholders"].append({"type": str(sh.placeholder_format.type).split(".")[-1].split(" ")[0], "name": sh.name, **_box(sh)})
        else:
            out["master"]["artwork"].append({"kind": k, "name": sh.name, **_box(sh)})
    if out["master"]["background"] in ("picture background", "gradient background"):
        out["unsupported"].append(f"Master has a {out['master']['background']}: kept from the template, but contrast QA assumes a plain background.")
    for lay in master.slide_layouts:
        phs, art = [], []
        for sh in lay.shapes:
            if sh.is_placeholder:
                phs.append({"type": str(sh.placeholder_format.type).split(".")[-1].split(" ")[0], "idx": sh.placeholder_format.idx, "name": sh.name, **_box(sh)})
            else:
                art.append({"kind": _shape_kind(sh), "name": sh.name, **_box(sh)})
        bgk = _bg_kind(lay._element)
        out["layouts"].append({"name": lay.name, "placeholders": phs, "artwork": art, "background": bgk,
                               "shows_master_artwork": lay._element.get("showMasterSp", "1") != "0"})
        if bgk in ("picture background", "gradient background"):
            out["unsupported"].append(f"Layout '{lay.name}' has a {bgk} (not used as the base layout).")
        for a in art:
            if a["kind"] in ("chart", "graphic_frame", "group"):
                out["unsupported"].append(f"Layout '{lay.name}' contains a {a['kind']} ('{a['name']}'): treated as artwork, not content.")
    return out


RECOGNISED = {"TITLE": "headline", "CENTER_TITLE": "cover title", "SUBTITLE": "cover subtitle", "BODY": "body text", "OBJECT": "content",
              "DATE": "date", "FOOTER": "footer", "SLIDE_NUMBER": "slide number", "PICTURE": "picture", "CHART": "chart", "TABLE": "table"}


def choose_base_layout(struct: dict) -> dict:
    """The emptiest layout that still shows the master artwork (logo, rules)."""
    def content_phs(lay):
        return [p for p in lay["placeholders"] if p["type"] not in ("DATE", "FOOTER", "SLIDE_NUMBER")]

    cands = sorted(struct["layouts"], key=lambda l: (len(content_phs(l)), 0 if "blank" in l["name"].lower() else 1, 0 if l["shows_master_artwork"] else 1, 0 if not l["background"] else 1))
    return cands[0] if cands else {"name": None}


def derive_grid(struct: dict, sw: float, sh: float) -> tuple[dict, list[str]]:
    notes = []
    grid = {}
    title = None
    for lay in struct["layouts"]:
        t = next((p for p in lay["placeholders"] if p["type"] == "TITLE"), None)
        if t:
            title = t
            break
    if title is None:
        title = next((p for p in struct["master"]["placeholders"] if p["type"] == "TITLE"), None)
    if title and abs(sw - SLIDE_W) < 0.05:
        ml = min(1.2, max(0.3, title["x"]))
        mr = min(1.2, max(0.3, sw - title["x"] - title["w"]))
        grid.update(margin_l=round(ml, 3), margin_r=round(mr, 3))
        notes.append(f"Margins taken from the title placeholder: left {ml:.2f} in, right {mr:.2f} in.")
    return grid, notes


def reserved_areas(struct: dict, base: dict, sw: float, sh: float) -> list[dict]:
    """Master/base-layout artwork the content must not cover (logos, bars, marks)."""
    out = []
    items = (struct["master"]["artwork"] if base.get("shows_master_artwork", True) else []) + base.get("artwork", [])
    for a in items:
        full_width = a["w"] > sw * 0.8
        full_height = a["h"] > sh * 0.8
        if full_width and full_height:
            continue  # a full-slide backdrop, not a reserved area
        out.append({"name": a["name"], "kind": a["kind"], "x": a["x"], "y": a["y"], "w": a["w"], "h": a["h"]})
    return out


def ingest(template: str | Path, out_dir: str | Path, name: str | None = None, base_theme: str = "meridian") -> dict:
    template = Path(template)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prs = Presentation(str(template))
    sw, sh = _in(prs.slide_width), _in(prs.slide_height)
    base = load_theme(base_theme)
    th = read_theme(prs)
    struct = read_structure(prs)
    installed = installed_font_families()
    heading = (th["fonts"].get("majorFont") or {}).get("latin") or base.font_latin
    body = (th["fonts"].get("minorFont") or {}).get("latin") or base.font_latin
    fonts = {"heading": font_report(heading, installed), "body": font_report(body, installed)}
    colors, series, color_notes = map_colors(th["colors"], base)
    base_layout = choose_base_layout(struct)
    grid, grid_notes = derive_grid(struct, sw, sh)
    reserved = reserved_areas(struct, base_layout, sw, sh)
    size_ok = abs(sw - SLIDE_W) < 0.05 and abs(sh - SLIDE_H) < 0.05
    notes = color_notes + grid_notes
    unsupported = list(struct["unsupported"])
    use_template = size_ok
    if not size_ok:
        ratio = sw / sh if sh else 0
        unsupported.append(f"Slide size {sw}×{sh} in (ratio {ratio:.2f}) is not the engine canvas 13.333×7.5 in: colours and fonts are applied, masters are NOT used.")
    # limits so the headline / footer never run into reserved artwork
    from ..design.tokens import GRID

    ml = grid.get("margin_l", GRID.margin_l)
    for r in reserved:
        if r["y"] < GRID.body_y and r["y"] + r["h"] > GRID.tracker_y and r["x"] > sw / 2:
            grid["headline_right_limit"] = round(min(grid.get("headline_right_limit") or sw, r["x"] - 0.15), 3)
        if r["y"] + r["h"] > GRID.footer_y and r["x"] > sw / 2:
            grid["footer_right_limit"] = round(min(grid.get("footer_right_limit") or sw, r["x"] - 0.15), 3)
    if grid.get("headline_right_limit"):
        notes.append(f"Headline width limited to end at {grid['headline_right_limit']} in to keep clear of master artwork.")
    for r in reserved:
        inside_body = r["y"] < 6.78 and r["y"] + r["h"] > 1.62 and r["x"] < sw - 0.4 and r["x"] + r["w"] > ml + 0.4
        if inside_body:
            unsupported.append(f"Master artwork '{r['name']}' sits inside the content area: QA will flag any content that overlaps it.")
    brand_name = name or template.stem
    shutil.copy(template, out / "template.pptx")
    theme = {
        "name": brand_name,
        "description": f"Brand theme ingested from {template.name}",
        "font_latin": body,
        "font_heading": heading if heading != body else None,
        "font_fallback_file": fonts["body"]["measure_family"],
        "colors": colors,
        "series": series,
        "sequential": [interpolate(colors["primary"], "FFFFFF", t) for t in (0.92, 0.7, 0.45, 0.2)] + [colors["primary"]],
        "diverging": [colors["negative"], interpolate(colors["negative"], "FFFFFF", 0.55), colors["surface"], interpolate(colors["positive"], "FFFFFF", 0.55), colors["positive"]],
        "extras": {
            "template": "template.pptx" if use_template else None,
            "base_layout": base_layout.get("name") if use_template else None,
            "grid": grid,
            "reserved": reserved if use_template else [],
            "measure_fonts": {f["font"]: f["measure_family"] for f in fonts.values() if f.get("font")},
        },
    }
    report = {
        "brand": brand_name,
        "template": template.name,
        "slide_size": {"width_in": sw, "height_in": sh, "supported": size_ok},
        "fonts": fonts,
        "theme_colors": th["colors"],
        "color_mapping": {k: colors[k] for k in ("primary", "secondary", "highlight", "text", "text_muted", "background", "positive", "negative")},
        "master": {"placeholders": struct["master"]["placeholders"], "artwork": struct["master"]["artwork"], "background": struct["master"]["background"]},
        "layouts": [{"name": l["name"], "placeholders": [f"{RECOGNISED.get(p['type'], p['type'].lower())}" for p in l["placeholders"]], "artwork": len(l["artwork"]), "background": l["background"]} for l in struct["layouts"]],
        "base_layout": base_layout.get("name"),
        "reserved_areas": reserved,
        "grid_overrides": grid,
        "unsupported": unsupported,
        "notes": notes,
        "masters_used": use_template,
    }
    (out / "theme.json").write_text(json.dumps(theme, indent=2, ensure_ascii=False))
    (out / "compatibility.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / "compatibility.md").write_text(to_markdown(report))
    return report


def to_markdown(r: dict) -> str:
    L = [f"# Brand compatibility report — {r['brand']}", "", f"Template: `{r['template']}`", ""]
    ok = r["masters_used"] and all(f.get("measurement") == "exact" for f in r["fonts"].values() if f.get("font"))
    L.append(f"**Verdict:** {'✅ fully compatible' if ok else '⚠️ compatible with approximations (see below)'}")
    L += ["", "## Slide size", "", f"{r['slide_size']['width_in']} × {r['slide_size']['height_in']} in — {'supported (masters used)' if r['slide_size']['supported'] else 'NOT the engine canvas: masters not used'}", ""]
    L += ["## Fonts", "", "| role | font | installed | status | measured with | measurement | rendered with if missing |", "|---|---|---|---|---|---|---|"]
    for role, f in r["fonts"].items():
        if f.get("font"):
            L.append(f"| {role} | {f['font']} | {'yes' if f['installed'] else 'no'} | {f['status']} | {f['measure_family']} | {f['measurement']} | {f['render_fallback'] or '—'} |")
    L += ["", "## Theme colours → engine roles", "", "| slot | colour |", "|---|---|"]
    L += [f"| {k} | `#{v}` |" for k, v in r["theme_colors"].items()]
    L += ["", "| role | colour |", "|---|---|"] + [f"| {k} | `#{v}` |" for k, v in r["color_mapping"].items()]
    L += ["", "## Masters and layouts", "", f"Base layout for generated slides: **{r['base_layout']}**", "", "| layout | recognised placeholders | artwork | background |", "|---|---|---|---|"]
    for l in r["layouts"]:
        L.append(f"| {l['name']} | {', '.join(l['placeholders']) or '—'} | {l['artwork']} | {l['background'] or '—'} |")
    L += ["", "## Reserved areas (master artwork protected by QA)", ""]
    L += [f"- {a['kind']} `{a['name']}` at ({a['x']}, {a['y']}) {a['w']}×{a['h']} in" for a in r["reserved_areas"]] or ["- none"]
    L += ["", "## Grid overrides", "", f"`{json.dumps(r['grid_overrides'])}`", ""]
    L += ["## Unsupported / not used", ""] + ([f"- {u}" for u in r["unsupported"]] or ["- none"])
    L += ["", "## Notes", ""] + ([f"- {n}" for n in r["notes"]] or ["- none"])
    return "\n".join(L) + "\n"
