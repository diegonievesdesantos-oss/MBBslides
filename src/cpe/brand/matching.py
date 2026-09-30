"""Corporate layout matching: which of the template's own layouts should carry this slide?

    SLIDE INTENT → ARCHETYPE → CORPORATE LAYOUT CANDIDATES → CAPACITY / GEOMETRY MATCH
                 → (compose, render, QA + archetype score) → BEST CORPORATE LAYOUT

Three modes, tried in order, and recorded per slide in `_plan.corporate`:

  native     the corporate layout's own placeholders carry the content (cover, section
             divider, closing, statement): the text inherits the template's typography,
             colours and positions — the slide IS a corporate slide.
  adaptive   a corporate content layout supplies background, artwork, logo, footer and
             title position; the engine composes the body inside the layout's free area.
  cpe        no corporate layout can represent the slide correctly: engine layout on the
             template's base layout with the corporate theme (colours, fonts).

A layout is only a candidate when it is technically able to carry the slide: the right
class (from the layout classifier, with its confidence), a light background for engine-drawn
bodies, no artwork inside the body area, a title where the engine's headline goes, and
enough capacity. Every rejection is recorded with its reason.
"""
from __future__ import annotations

NATIVE_KINDS = {
    "cover": ["cover"],
    "divider": ["section"],
    "appendix_divider": ["section"],
    "closing": ["closing", "section"],
    "statement": ["statement", "section"],
}
ARCHETYPE_CLASSES = {
    "table": ["table", "content", "one_column"],
    "chart": ["chart", "chart_commentary", "content", "one_column"],
    "waterfall": ["chart", "content", "one_column"],
    "segmentation": ["chart", "content", "one_column"],
    "matrix": ["matrix", "content", "one_column"],
    "comparison": ["two_column", "three_column", "comparison", "content", "one_column"],
    "process": ["process", "content", "one_column"],
    "roadmap": ["roadmap", "timeline", "content", "one_column"],
    "timeline": ["timeline", "roadmap", "content", "one_column"],
    "kpi_hero": ["statement", "content", "one_column"],
    "kpi_dashboard": ["content", "one_column"],
    "executive_summary": ["one_column", "content", "conclusion"],
    "text_exhibit": ["one_column", "content"],
    "operating_model": ["content", "one_column"],
    "architecture": ["content", "one_column"],
    "hierarchy": ["content", "one_column"],
    "statement": ["statement", "content"],
}
MIN_CONF = 0.35


def _conf(layout: dict, cls: str) -> float:
    return max((c["confidence"] for c in layout["classification"] if c["type"] == cls), default=0.0)


def native_candidates(kind: str, layouts: list[dict]) -> list[tuple[float, dict, str]]:
    out = []
    for pref, cls in enumerate(NATIVE_KINDS.get(kind, [])):
        for lay in layouts:
            c = _conf(lay, cls)
            if c < MIN_CONF:
                continue
            if not any(p["type"] in ("TITLE", "CENTER_TITLE") for p in lay["placeholders"]):
                continue
            out.append((c - 0.15 * pref + 0.05 * min(3, lay.get("usage_n", 0)), lay, f"{cls} layout (confidence {c:.2f})"))
    return sorted(out, key=lambda t: -t[0])


def adaptive_candidates(archetype: str, layouts: list[dict], grid) -> tuple[list[tuple[float, dict, str]], list[str]]:
    """Content layouts able to host an engine-composed body; returns (ranked, rejections)."""
    out, rejected = [], []
    classes = ARCHETYPE_CLASSES.get(archetype, ["content", "one_column"])
    for lay in layouts:
        best = max(((1 - 0.08 * i) * _conf(lay, cls), cls) for i, cls in enumerate(classes))
        score, cls = best
        if score < MIN_CONF * 0.8:
            continue
        why = None
        title = next((p for p in lay["placeholders"] if p["type"] == "TITLE"), None)
        if title is None:
            why = "no title placeholder"
        elif lay["dark_bg"] or lay["picture_bg"]:
            why = "dark or picture background (engine bodies are drawn for light backgrounds)"
        elif lay["artwork_in_body"]:
            why = "artwork inside the body area"
        elif title["y"] > grid.body_y - 0.4:
            why = f"title placeholder too low ({title['y']:.2f} in)"
        elif abs(title["y"] - grid.headline_y) > 0.6:
            why = f"title placeholder at {title['y']:.2f} in, far from the headline band ({grid.headline_y:.2f} in)"
        else:
            why = band_conflict(lay, grid)
        if why:
            rejected.append(f"{lay['name']} ({cls}): {why}")
            continue
        # prefer layouts whose title geometry agrees with the engine's headline band and that keep a full body free
        geom = 1 - min(1.0, abs(title["y"] - grid.headline_y) / 0.6) * 0.3
        free = 0.1 if not [p for p in lay["placeholders"] if p["type"] not in ("TITLE", "DATE", "FOOTER", "SLIDE_NUMBER")] else 0.0
        out.append((score * geom + free + 0.03 * min(3, lay.get("usage_n", 0)), lay, f"{cls} layout (confidence {_conf(lay, cls):.2f})"))
    return sorted(out, key=lambda t: -t[0]), rejected


def _hits(a: dict, y0: float, y1: float, x0: float, x1: float) -> float:
    """Width share of [x0, x1] covered by artwork a inside the vertical band [y0, y1]."""
    if a["y"] >= y1 or a["y"] + a["h"] <= y0:
        return 0.0
    return max(0.0, min(x1, a["x"] + a["w"]) - max(x0, a["x"])) / max(0.01, x1 - x0)


def band_conflict(lay: dict, grid) -> str | None:
    """Artwork that would collide with the engine's headline, body or footer (source, page number)."""
    x0, x1 = grid.margin_l, grid.margin_l + grid.content_w
    for a in lay["reserved"]:
        if _hits(a, grid.footer_y, grid.footer_y + grid.footer_h, x0, x1) > 0.35:
            return f"artwork '{a['name']}' runs through the footer band (source line, page number)"
        if _hits(a, grid.headline_y, grid.headline_y + grid.headline_h, x0, x1) > 0 and a["x"] < x0 + 0.6 * (x1 - x0):
            return f"artwork '{a['name']}' sits in the headline band"
    return None


def limits(lay: dict, grid) -> dict:
    """Per-slide headline / footer right limits so the engine keeps clear of this layout's corner artwork."""
    out = {}
    for a in lay["reserved"]:
        if a["y"] < grid.body_y and a["y"] + a["h"] > grid.tracker_y and a["x"] > grid.margin_l + grid.content_w / 2:
            out["headline_right_limit"] = round(min(out.get("headline_right_limit", 99), a["x"] - 0.15), 3)
        if a["y"] + a["h"] > grid.footer_y and a["x"] > grid.margin_l + grid.content_w / 2:
            out["footer_right_limit"] = round(min(out.get("footer_right_limit", 99), a["x"] - 0.15), 3)
    return out


def choose(slide: dict, archetype: str | None, corporate: dict, grid) -> dict:
    """The corporate decision for one slide: {mode, layout, master, why, alternatives, rejected}."""
    layouts = corporate.get("layouts") or []
    kind = slide.get("kind", "content")
    if kind in NATIVE_KINDS and not slide.get("visual") and not slide.get("exhibits"):
        nat = native_candidates(kind, layouts)
        if nat:
            s, lay, why = nat[0]
            return {"mode": "native", "layout": lay["name"], "layout_id": lay["id"], "master": lay["master"], "why": why,
                    "alternatives": [f"{l['name']} ({round(x, 2)})" for x, l, _ in nat[1:3]]}
    if kind in ("cover", "divider", "appendix_divider", "closing"):
        return {"mode": "cpe", "why": f"no corporate {'/'.join(NATIVE_KINDS.get(kind, [kind]))} layout recognised with confidence ≥ {MIN_CONF}"}
    ranked, rejected = adaptive_candidates(archetype or "chart", layouts, grid)
    if ranked:
        s, lay, why = ranked[0]
        return {"mode": "adaptive", "layout": lay["name"], "layout_id": lay["id"], "master": lay["master"], "why": why, "limits": limits(lay, grid),
                "alternatives": [f"{l['name']} ({round(x, 2)})" for x, l, _ in ranked[1:3]], "rejected": rejected[:6]}
    return {"mode": "cpe", "why": "no corporate content layout can host this slide", "rejected": rejected[:6]}
