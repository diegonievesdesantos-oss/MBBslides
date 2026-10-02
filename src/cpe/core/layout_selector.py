"""Layout selection: content roles × visual compatibility × capacity × variety.

A slide's content is normalised into roles (exhibit, commentary, kpis, column,
statements, statement). A layout is eligible when it accepts exactly those
roles in the right counts and all exhibits are compatible with it. Among the
eligible layouts the selector scores family fit, "needs width" signals,
commentary capacity and variety (no identical layout on consecutive slides).
"""
from __future__ import annotations

from ..layout.engine import Layout, load_library
from ..spec import slide_exhibits
from .headline import words

FAMILY_FOR_VISUAL = {
    "waterfall": "09_waterfall", "bridge": "09_waterfall",
    "matrix_2x2": "06_matrix", "portfolio": "06_matrix",
    "process": "07_process", "value_chain": "07_process", "flow": "07_process", "journey": "07_process", "funnel": "07_process",
    "cause_effect": "07_process", "causal_chain": "07_process",
    "timeline": "08_timeline",
    "gantt": "15_roadmap", "roadmap": "15_roadmap",
    "table": "10_table", "heatmap": "10_table", "scorecard": "10_table", "harvey_table": "05_comparison",
    "tile_map": "11_market_map",
    "mekko": "12_segmentation", "segmentation": "12_segmentation",
    "tree": "13_framework", "driver_tree": "13_framework", "pyramid": "13_framework",
    "org_chart": "14_architecture", "layers": "14_architecture", "operating_model": "14_architecture", "architecture": "14_architecture",
}

WIDE_VISUALS = {"gantt", "roadmap", "timeline", "journey", "value_chain", "operating_model", "architecture", "layers", "mekko"}


def content_roles(slide: dict) -> dict:
    roles: dict = {}
    exhibits = []
    text_ex = None
    for ex in slide_exhibits(slide):
        t = ex.get("type")
        if t == "statements":
            roles["statements"] = ex
        elif t == "kpi":
            roles["kpis"] = ex
        elif t == "text_columns" or t == "comparison":
            roles["column"] = (ex.get("data") or {}).get("columns") or ex.get("columns") or []
        elif t in ("statement", "quote"):
            roles["statement"] = ex
        elif t == "bullets":
            text_ex = {"points": (ex.get("data") or {}).get("points") or ex.get("points") or [], "title": ex.get("title")}
        else:
            exhibits.append(ex)
    if exhibits:
        roles["exhibit"] = exhibits
    if slide.get("kpis"):
        roles["kpis"] = slide["kpis"] if isinstance(slide["kpis"], dict) else {"items": slide["kpis"]}
    if slide.get("columns"):
        roles["column"] = slide["columns"]
    if slide.get("statements"):
        roles["statements"] = {"data": {"items": slide["statements"]}}
    if text_ex is not None and not any(roles.get(k) for k in ("exhibit", "kpis", "column", "statements", "statement")):
        # (v1.4) body text that IS the slide gets its own role and component (tc.text_exhibit),
        # instead of being drawn as side commentary; the slide's own commentary becomes its so-what
        roles["text"] = text_ex
        if slide.get("commentary"):
            roles["commentary"] = slide["commentary"]
    elif text_ex is not None:
        # beside another exhibit, bullets are commentary: MERGED with the slide's commentary
        # (v1.3.3 silently replaced the bullets with it and lost content)
        c = slide.get("commentary") or {}
        roles["commentary"] = {"title": text_ex.get("title") or (c.get("title") if isinstance(c, dict) else None),
                               "points": list(text_ex["points"]) + list((c.get("points") if isinstance(c, dict) else c) or [])}
    elif slide.get("commentary"):
        roles["commentary"] = slide["commentary"]
    return roles


def _count(roles: dict, role: str) -> int:
    v = roles.get(role)
    if v is None:
        return 0
    if role in ("exhibit", "column"):
        return len(v)
    return 1


def commentary_words(c) -> tuple[int, int]:
    if not c:
        return 0, 0
    pts = c.get("points") if isinstance(c, dict) else c
    pts = pts or []
    n = 0
    for p in pts:
        t = p if isinstance(p, str) else p.get("text", "") + " " + " ".join(p.get("sub", []) or [])
        n += len(words(t))
    return n, len(pts)


def eligible(slide: dict, roles: dict, lib: dict[str, Layout]) -> list[Layout]:
    kind = slide.get("kind", "content")
    out = []
    for lay in lib.values():
        if lay.body_band == "full" or lay.id in ("agenda",):
            continue
        ok = True
        for role in set(list(lay.accepts) + list(roles)):
            lo, hi = lay.accepts.get(role, [0, 0])
            c = _count(roles, role)
            if not lo <= c <= hi:
                ok = False
                break
        if not ok:
            continue
        exs = roles.get("exhibit") or []
        if exs and lay.compatible_visuals and not all(e.get("type") in lay.compatible_visuals for e in exs):
            continue
        if kind == "exec_summary" and lay.family != "01_executive_summary" and "statements" in roles:
            continue
        out.append(lay)
    return out


def score_layout(lay: Layout, slide: dict, roles: dict, prev_layout: str | None, profile: dict) -> tuple[float, list[str]]:
    s = 50.0
    why = []
    exs = roles.get("exhibit") or []
    types = [e.get("type") for e in exs]
    fams = {FAMILY_FOR_VISUAL.get(t) for t in types if FAMILY_FOR_VISUAL.get(t)}
    if lay.family in fams:
        s += 20
        why.append(f"family {lay.family} matches {', '.join(types)}")
    wide = any(t in WIDE_VISUALS for t in types) or any(
        len((e.get("data") or {}).get("categories") or []) > 10 or len(e.get("columns") or []) > 6 for e in exs
    )
    if wide:
        if any(z["cols"] == [1, 12] for z in lay.zones if z["role"] == "exhibit"):
            s += 15
            why.append("exhibit needs the full width")
        else:
            s -= 10
    wc, nb = commentary_words(roles.get("commentary"))
    cap = lay.capacity.get("commentary") or {}
    if wc and cap:
        if wc > cap.get("words", 999) or nb > cap.get("bullets", 99):
            s -= 25
            why.append(f"commentary ({wc} words/{nb} bullets) exceeds capacity {cap}")
        else:
            s += 5
    if slide.get("takeaway") and lay.takeaway == "none":
        s -= 30
        why.append("layout has no takeaway band")
    if lay.id == prev_layout:
        s -= 15
        why.append("same layout as previous slide")
    style = (slide.get("statements_style") or ((roles.get("statements") or {}).get("data") or {}).get("style"))
    if lay.id == "exec_summary_scr" and style == "scr":
        s += 20
    if lay.id == "exec_summary_scr" and style != "scr":
        s -= 20
    if lay.id == "exec_summary_kpi" and roles.get("kpis"):
        s += 10
    if lay.id == "exhibit_commentary_left" and slide.get("reading_first"):
        s += 15
    if lay.id == "exhibit_commentary_left" and not slide.get("reading_first"):
        s -= 3  # default: exhibit first
    if lay.id == "kpi_strip_exhibit_commentary" and not roles.get("commentary"):
        s -= 50
    n_cols = len(roles.get("column") or [])
    if n_cols and lay.family == "15_roadmap" and slide.get("message_type") != "plan":
        s -= 10
    return s, why


def select(slide: dict, prev_layout: str | None = None, profile: dict | None = None) -> tuple[str, dict]:
    profile = profile or {}
    lib = load_library()
    kind = slide.get("kind", "content")
    if kind in ("cover", "divider", "agenda", "appendix_divider"):
        return {"appendix_divider": "divider"}.get(kind, kind), {"why": "structural slide"}
    if kind in ("statement", "closing") and not slide_exhibits(slide):
        return "statement", {"why": "statement slide"}
    explicit = slide.get("layout")
    if explicit and explicit != "auto":
        if explicit not in lib:
            raise KeyError(f"Slide {slide.get('id')}: unknown layout '{explicit}'")
        return explicit, {"why": "explicit in spec"}
    roles = content_roles(slide)
    cands = eligible(slide, roles, lib)
    if not cands:
        raise ValueError(
            f"Slide {slide.get('id')}: no layout accepts roles {{{', '.join(f'{k}:{_count(roles, k)}' for k in roles)}}} "
            f"with visuals {[e.get('type') for e in roles.get('exhibit') or []]}"
        )
    scored = sorted(((score_layout(l, slide, roles, prev_layout, profile), l) for l in cands), key=lambda t: -t[0][0])
    (best_s, why), best = scored[0]
    return best.id, {"why": "; ".join(why) or "best available fit", "score": best_s, "alternatives": [l.id for _, l in scored[1:4]]}
