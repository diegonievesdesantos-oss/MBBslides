"""Diagrams built from native, editable shapes.

Every diagram sizes itself from its zone and its content (no hard-coded
coordinates), uses square corners, one emphasis colour, and hairline
connectors. Text inside filled shapes is a separate text box with
auto-contrast colour so it stays editable and measurable.
"""
from __future__ import annotations

import math

from pptx.enum.shapes import MSO_SHAPE

from ..charts.numfmt import fmt, fmt_spec
from ..design.tokens import GRID, LINES, SPACING, best_text_on, legible_fill, sequential_color
from ..layout.engine import Box
from ..pptx.painter import Painter, Para
from ..pptx.text_components import exhibit_header

G = GRID.gutter


def _label_in(p: Painter, box: Box, text: str, fill_token: str | None, role: str = "body", bold: bool = False, align: str = "center", size: float | None = None, max_lines=None, record=None):
    color = None
    if fill_token:
        color_hex = best_text_on(p.color(fill_token), p.theme)
        color = color_hex
    p.text(box, text, role=role, bold=bold, align=align, anchor="middle", color=color, size=size, max_lines=max_lines, record=record)


# ---------------------------------------------------------------------------
# Process / value chain
# ---------------------------------------------------------------------------
def process(p: Painter, box: Box, ex: dict) -> dict:
    """Steps: [{"title", "text"|"points", "owner", "duration"}]; highlight: [index]."""
    box = exhibit_header(p, box, ex)
    steps = ex["data"]["steps"]
    n = len(steps)
    hl = set(ex.get("highlight") or [])
    vertical = ex.get("orientation") == "vertical" or (box.w < 6.5 and n > 3)
    if vertical:
        return _process_vertical(p, box, steps, hl)
    chevron = ex["type"] == "value_chain" or ex.get("style") == "chevron"
    head_h = 0.72
    cols = box.columns(n, 0.08 if chevron else G)
    for i, (c, st) in enumerate(zip(cols, steps)):
        fill = "primary" if i in hl else ("secondary" if chevron else "surface")
        hb = Box(c.x, c.y, c.w + (0.18 if chevron and i < n - 1 else 0), head_h)
        if chevron:
            p.shape(MSO_SHAPE.CHEVRON if i > 0 else MSO_SHAPE.PENTAGON, hb, fill=fill)
            inner = hb.inset(l=0.3 if i > 0 else 0.12, r=0.3)
        else:
            p.rect(hb, fill=fill)
            inner = hb.inset(l=SPACING["S"], r=SPACING["S"])
        num = f"{i + 1}  " if ex.get("numbered", True) and not chevron else ""
        _label_in(p, inner, f"{num}{st['title']}", fill, role="body_strong", align="left" if not chevron else "center", max_lines=2, record=f"step {i + 1}")
        if not chevron and i < n - 1:
            # small arrow in the gutter between steps
            ax = c.r + 0.02
            p.line(ax, c.y + head_h / 2, ax + G - 0.04, c.y + head_h / 2, color="neutral", width=LINES["strong"], arrow_end=True, kind="connector")
        y = c.y + head_h + SPACING["M"]
        bottom = c.b
        if any(s_.get("metric") for s_ in steps):
            # impact row aligned with the steps: what each step changes, as a number
            mh = 1.0
            bottom = c.b - mh - SPACING["S"]
            p.line(c.x, c.b - mh, c.r, c.b - mh, color="rule", width=LINES["rule"])
            if st.get("metric"):
                p.text(Box(c.x, c.b - mh + 0.1, c.w, 0.5), str(st["metric"]), role="kpi_value", size=22, max_lines=1,
                       color="primary" if i in hl else "text", record=f"step {i + 1} metric")
                if st.get("metric_label"):
                    p.text(Box(c.x, c.b - mh + 0.6, c.w, 0.38), st["metric_label"], role="kpi_label", max_lines=2, record=f"step {i + 1} metric label")
        meta = " · ".join(x for x in (st.get("owner"), st.get("duration")) if x)
        if meta:
            p.text(Box(c.x, y, c.w, 0.28), meta, role="annotation", color="text_muted", max_lines=1, record="step meta")
            y += 0.34
        body = st.get("points") or ([st["text"]] if st.get("text") else [])
        if body:
            paras = [Para(t, bullet="•" if len(body) > 1 else None) for t in body]
            p.text(Box(c.x, y, c.w, bottom - y), paras, role="body", size=p.style("body")["size"] - (1 if n >= 5 else 0), record=f"step {i + 1} body")
        if i in hl and st.get("callout"):
            p.text(Box(c.x, c.b - 0.55, c.w, 0.55), st["callout"], role="annotation", bold=True, color="highlight", record="step callout")
    return {"type": "process", "steps": n}


def _process_vertical(p: Painter, box: Box, steps: list, hl: set) -> dict:
    n = len(steps)
    rows = box.rows(n, SPACING["S"])
    lab_w = min(2.6, box.w * 0.36)
    for i, (r, st) in enumerate(zip(rows, steps)):
        fill = "primary" if i in hl else "surface"
        lb = Box(r.x, r.y, lab_w, r.h)
        p.rect(lb, fill=fill)
        _label_in(p, lb.inset(l=SPACING["S"], r=SPACING["S"]), f"{i + 1}  {st['title']}", fill, role="body_strong", align="left", max_lines=3)
        body = st.get("points") or ([st["text"]] if st.get("text") else [])
        paras = [Para(t, bullet="•" if len(body) > 1 else None) for t in body]
        if paras:
            p.text(Box(r.x + lab_w + SPACING["M"], r.y, r.w - lab_w - SPACING["M"], r.h), paras, role="body", anchor="middle", record=f"vstep {i + 1}")
        if i < n - 1:
            xm = r.x + lab_w / 2
            p.line(xm, r.b, xm, rows[i + 1].y, color="neutral", width=LINES["strong"], arrow_end=True, kind="connector")
    return {"type": "process", "steps": n, "orientation": "vertical"}


# ---------------------------------------------------------------------------
# Timeline (milestones)
# ---------------------------------------------------------------------------
def timeline(p: Painter, box: Box, ex: dict) -> dict:
    box = exhibit_header(p, box, ex)
    evs = ex["data"]["events"]
    n = len(evs)
    hl = set(ex.get("highlight") or [])
    axis_y = box.y + box.h * 0.46
    p.line(box.x, axis_y, box.r, axis_y, color="rule", width=LINES["strong"])
    slot = box.w / n
    for i, ev in enumerate(evs):
        cx = box.x + (i + 0.5) * slot
        d = 0.2 if i in hl else 0.15
        p.oval(Box(cx - d / 2, axis_y - d / 2, d, d), fill="highlight" if i in hl else "primary")
        up = i % 2 == 0
        w = slot * 1.7 if n > 5 else slot - 0.1
        w = min(w, 2.6)
        x = min(max(cx - w / 2, box.x), box.r - w)
        date_h = 0.3
        text_h = box.h * 0.46 - date_h - 0.25
        paras = [Para(ev.get("text", ""), bold=i in hl)]
        if ev.get("detail"):  # what the milestone unlocks / who owns it
            paras.append(Para(ev["detail"], color="text_muted", size=p.style("body")["size"] - 2))
        if up:
            p.line(cx, axis_y - d / 2, cx, axis_y - 0.22, color="rule", width=LINES["hairline"])
            p.text(Box(x, axis_y - 0.25 - date_h, w, date_h), ev.get("date", ""), role="body_strong", color="primary", align="center", anchor="bottom", max_lines=1)
            p.text(Box(x, box.y, w, text_h), paras, role="body", size=p.style("body")["size"] - 1, align="center", anchor="bottom", space_after=3, record=f"event {i + 1}")
        else:
            p.line(cx, axis_y + d / 2, cx, axis_y + 0.22, color="rule", width=LINES["hairline"])
            p.text(Box(x, axis_y + 0.25, w, date_h), ev.get("date", ""), role="body_strong", color="primary", align="center", max_lines=1)
            p.text(Box(x, axis_y + 0.25 + date_h, w, text_h), paras, role="body", size=p.style("body")["size"] - 1, align="center", space_after=3, record=f"event {i + 1}")
    return {"type": "timeline", "events": n}


# ---------------------------------------------------------------------------
# Gantt / roadmap
# ---------------------------------------------------------------------------
def gantt(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"periods": ["Q1 26", ...], "phases": [{"label","start","end"}],
    "rows": [{"label", "bars": [{"start","end","label","status"}], "milestones": [{"at","label"}]}],
    "today": 2.5}. start/end are period indices (end exclusive; floats allowed)."""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    periods = d["periods"]
    rows = d["rows"]
    npd = len(periods)
    lab_w = min(2.9, box.w * 0.24)
    grid_x = box.x + lab_w + SPACING["S"]
    grid_w = box.r - grid_x
    colw = grid_w / npd
    y = box.y
    if d.get("phases"):
        for ph in d["phases"]:
            x0 = grid_x + ph["start"] * colw
            x1 = grid_x + ph["end"] * colw
            p.rect(Box(x0 + 0.02, y, x1 - x0 - 0.04, 0.3), fill="primary")
            _label_in(p, Box(x0 + 0.06, y, x1 - x0 - 0.12, 0.3), ph["label"], "primary", role="annotation", bold=True, max_lines=1)
        y += 0.38
    for j, per in enumerate(periods):
        p.text(Box(grid_x + j * colw, y, colw, 0.28), per, role="chart_axis", align="center", max_lines=1, fit=True)
    y += 0.32
    p.line(box.x, y, box.r, y, color="primary", width=LINES["rule"])
    body_h = box.b - y - (0.26 if d.get("today") is not None else 0)
    rh = min(0.62, body_h / max(1, len(rows)))
    for j in range(1, npd):
        xg = grid_x + j * colw
        p.line(xg, y, xg, y + rh * len(rows), color="gridline", width=LINES["hairline"])
    if d.get("today") is not None:  # drawn first: bars sit on top of it
        tx = grid_x + float(d["today"]) * colw
        p.line(tx, y - 0.05, tx, y + rh * len(rows), color="highlight", width=LINES["rule"], dash=True, kind="connector")
        p.text(Box(tx - 0.5, y + rh * len(rows) + 0.02, 1.0, 0.22), "Today", role="annotation", size=9, bold=True, color="text_muted", align="center", fit=False, kind="label")
    status_fill = {"done": "neutral", "on_track": "secondary", "at_risk": "warning", "late": "negative", "planned": "muted", None: "secondary"}
    for i, r in enumerate(rows):
        ry = y + i * rh
        p.text(Box(box.x, ry, lab_w, rh), r["label"], role="body", size=p.style("body")["size"] - 0.5, anchor="middle", max_lines=2, record=f"row {r['label']}")
        for b in r.get("bars", []):
            x0 = grid_x + b["start"] * colw + 0.03
            x1 = grid_x + b["end"] * colw - 0.03
            bh = rh * 0.52
            fill = "highlight" if b.get("highlight") else status_fill.get(b.get("status"), "secondary")
            by = ry + (rh - bh) / 2 + (rh * 0.14 if r.get("milestones") else 0)
            bb = Box(x0, by, max(0.05, x1 - x0), bh)
            ms_at = [m["at"] for m in r.get("milestones", [])]
            lab_l = 0.2 if any(abs(grid_x + a * colw - x0) < 0.2 for a in ms_at) else 0.06  # clear a diamond at the bar start
            p.rect(bb, fill=fill)
            if b.get("label"):
                tw = p.text_w(b["label"], "annotation")
                if tw + lab_l + 0.08 <= bb.w:
                    _label_in(p, bb.inset(l=lab_l, r=0.06), b["label"], fill, role="annotation", align="left", max_lines=1)
                elif x1 + tw + 0.1 < box.r:
                    p.text(Box(x1 + 0.06, bb.y, tw + 0.1, bb.h), b["label"], role="annotation", anchor="middle", fit=False, kind="label")
        for m in r.get("milestones", []):
            mx = grid_x + m["at"] * colw
            s = 0.2
            bh = rh * 0.52
            by = ry + (rh - bh) / 2 + (rh * 0.14 if r.get("milestones") else 0)
            p.shape(MSO_SHAPE.DIAMOND, Box(mx - s / 2, by + bh / 2 - s / 2, s, s), fill="highlight", line="background", line_w=0.75, kind="marker")
            if m.get("label"):
                tw = p.text_w(m["label"], "annotation", size=9) + 0.1
                lx = min(max(mx - tw / 2, grid_x), box.r - tw)
                p.text(Box(lx, by - 0.22, tw, 0.2), m["label"], role="annotation", size=9, bold=True, align="center", anchor="bottom", fit=False, kind="label")
        p.line(box.x, ry + rh, box.r, ry + rh, color="gridline", width=LINES["hairline"])
    return {"type": "gantt", "rows": len(rows), "periods": npd}


# ---------------------------------------------------------------------------
# 2x2 matrix / portfolio
# ---------------------------------------------------------------------------
def matrix_2x2(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"x_label","y_label","quadrants":[TL,TR,BL,BR] titles, "items":[{"label","x","y","size"}],
    "focus": "TR"} with x,y in [0,1]."""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    ax_w = 0.15
    ax_h = 0.42
    top_pad = 0.4
    box = Box(box.x, box.y + top_pad, box.w, box.h - top_pad)
    side = min(box.w - ax_w, box.h - ax_h)
    square = ex.get("square", False)
    gx = box.x + ax_w + (box.w - ax_w - side) / 2 if square else box.x + ax_w
    gw = side if square else box.w - ax_w - 0.1
    gy, gh = box.y, box.h - ax_h
    q = Box(gx, gy, gw, gh)
    half_w, half_h = q.w / 2, q.h / 2
    focus = d.get("focus")
    names = ["TL", "TR", "BL", "BR"]
    boxes = [Box(q.x, q.y, half_w, half_h), Box(q.x + half_w, q.y, half_w, half_h), Box(q.x, q.y + half_h, half_w, half_h), Box(q.x + half_w, q.y + half_h, half_w, half_h)]
    for nm, b in zip(names, boxes):
        p.rect(b, fill="faint" if nm == focus else None, line="rule", line_w=LINES["hairline"])
    placed: list[Box] = []
    for k, (nm, b) in enumerate(zip(names, boxes)):
        titles = d.get("quadrants") or []
        if k < len(titles) and titles[k]:
            align = "left" if nm in ("TL", "BL") else "right"
            ty = b.y + 0.08 if nm in ("TL", "TR") else b.b - 0.34  # outer corners, away from the data
            tb = Box(b.x + 0.1, ty, b.w - 0.2, 0.26)
            p.text(tb, titles[k], role="annotation", bold=True, color="primary" if nm == focus else "text_muted", align=align, max_lines=1, record="quadrant title")
            tw = p.text_w(titles[k], "annotation", bold=True)
            placed.append(Box(tb.x if align == "left" else tb.r - tw, tb.y, tw, tb.h))
    p.line(q.x, q.b, q.r + 0.05, q.b, color="text", width=LINES["rule"], arrow_end=True)
    p.line(q.x, q.b, q.x, q.y - 0.05, color="text", width=LINES["rule"], arrow_end=True)
    p.text(Box(q.x, q.b + 0.06, q.w, 0.3), d.get("x_label", ""), role="chart_axis", align="center", max_lines=1)
    # y-axis label: horizontal, above the arrow head (rotated text reads badly and measures unreliably)
    yl = d.get("y_label", "")
    if yl:
        p.text(Box(q.x - 0.05, q.y - 0.36, min(q.w, p.text_w(yl, "chart_axis") + 0.3), 0.26), "↑ " + yl, role="chart_axis", max_lines=1, fit=False, kind="label")
    items = d.get("items") or []
    smax = max([float(it.get("size", 1)) for it in items] or [1])
    hl = set(ex.get("highlight") or [])
    bubbles: list[Box] = []
    for it in sorted(items, key=lambda it: -float(it.get("size", 1))):
        cx = q.x + float(it["x"]) * q.w
        cy = q.b - float(it["y"]) * q.h
        dmax = min(q.w, q.h) * 0.16
        dia = max(0.16, dmax * math.sqrt(float(it.get("size", 1)) / smax)) if any("size" in i for i in items) else 0.2
        fill = "highlight" if it.get("label") in hl or it.get("highlight") else "primary"
        p.oval(Box(cx - dia / 2, cy - dia / 2, dia, dia), fill=fill, line="background", line_w=0.75)
        bubbles.append(Box(cx - dia / 2, cy - dia / 2, dia, dia))
        w = p.text_w(it["label"], "annotation") + 0.08
        h = 0.24
        cands = [Box(cx + dia / 2 + 0.04, cy - h / 2, w, h), Box(cx - dia / 2 - 0.04 - w, cy - h / 2, w, h), Box(cx - w / 2, cy - dia / 2 - h, w, h), Box(cx - w / 2, cy + dia / 2, w, h)]
        choice = next((c for c in cands if q.contains(c, 0.0) and all(c.intersection(o) < 1e-4 for o in placed + bubbles[:-1])), None)
        if choice is None:
            choice = cands[0]
            p.warn("LABEL_COLLISION", f"Matrix label '{it['label']}' overlaps")
        placed.append(choice)
        p.text(choice, it["label"], role="annotation", bold=fill == "highlight", anchor="middle", fit=False, kind="label")
    return {"type": "matrix_2x2", "items": len(items)}


# ---------------------------------------------------------------------------
# Trees: issue / driver tree (left→right), org chart (top→down)
# ---------------------------------------------------------------------------
def _leaves(node) -> int:
    ch = node.get("children") or []
    return 1 if not ch else sum(_leaves(c) for c in ch)


def _depth(node) -> int:
    ch = node.get("children") or []
    return 1 + (max(_depth(c) for c in ch) if ch else 0)


def tree(p: Painter, box: Box, ex: dict) -> dict:
    box = exhibit_header(p, box, ex)
    root = ex["data"]["root"]
    if ex["type"] == "org_chart" or ex.get("orientation") == "vertical":
        return _tree_vertical(p, box, root, ex)
    depth = _depth(root)
    leaves = _leaves(root)
    gap_x = 0.45
    col_w = (box.w - gap_x * (depth - 1)) / depth
    unit = box.h / leaves
    node_h = min(0.8, unit * 0.78)
    f = fmt_spec(ex)

    def draw(node, level, y0):
        span = _leaves(node) * unit
        cy = y0 + span / 2
        x = box.x + level * (col_w + gap_x)
        nb = Box(x, cy - node_h / 2, col_w, node_h)
        emph = node.get("highlight")
        fill = "primary" if level == 0 else ("highlight" if emph else "surface")
        p.rect(nb, fill=fill)
        label = node["label"]
        if node.get("value") is not None:
            label = f"{label}\n**{fmt(float(node['value']), f) if isinstance(node['value'], (int, float)) else node['value']}**"
        _label_in(p, nb.inset(l=0.08, r=0.08, t=0.02, b=0.02), label, fill, role="body", size=p.style("body")["size"] - (1 if depth >= 4 else 0), align="left", record=f"node {node['label'][:20]}")
        ch = node.get("children") or []
        yc = y0
        for c in ch:
            cspan = _leaves(c) * unit
            ccy = yc + cspan / 2
            p.elbow(nb.r, cy, nb.r + gap_x, ccy, color="neutral", width=LINES["rule"], mid="h")
            draw(c, level + 1, yc)
            yc += cspan
        if node.get("operator") and ch:
            p.text(Box(nb.r + 0.02, cy - 0.28, gap_x / 2, 0.26), node["operator"], role="annotation", bold=True, color="text_muted", align="center", fit=False, kind="label")

    draw(root, 0, box.y)
    return {"type": ex["type"], "depth": depth, "leaves": leaves}


def _tree_vertical(p: Painter, box: Box, root: dict, ex: dict) -> dict:
    depth = _depth(root)
    leaves = _leaves(root)
    gap_y = 0.42
    row_h = min(0.95, (box.h - gap_y * (depth - 1)) / depth)
    unit = box.w / leaves
    node_w = min(2.4, unit * 0.9)

    def draw(node, level, x0):
        span = _leaves(node) * unit
        cx = x0 + span / 2
        y = box.y + level * (row_h + gap_y)
        nb = Box(cx - node_w / 2, y, node_w, row_h)
        fill = "primary" if level == 0 else ("highlight" if node.get("highlight") else "surface")
        p.rect(nb, fill=fill)
        paras = [Para(node["label"], bold=True)]
        if node.get("sub"):
            paras.append(Para(node["sub"], size=p.style("body")["size"] - 1))
        color = best_text_on(p.color(fill), p.theme)
        p.text(nb.inset(l=0.06, r=0.06), paras, role="body", size=p.style("body")["size"] - (1 if leaves > 5 else 0), align="center", anchor="middle", color=color, space_after=1, record=f"org {node['label'][:20]}")
        xc = x0
        for c in node.get("children") or []:
            cspan = _leaves(c) * unit
            p.elbow(cx, nb.b, xc + cspan / 2, nb.b + gap_y, color="neutral", width=LINES["rule"], mid="v")
            draw(c, level + 1, xc)
            xc += cspan

    draw(root, 0, box.x)
    return {"type": ex["type"], "depth": depth, "leaves": leaves}


# ---------------------------------------------------------------------------
# Funnel & pyramid
# ---------------------------------------------------------------------------
def funnel(p: Painter, box: Box, ex: dict) -> dict:
    """Honest funnel: bar widths proportional to values, conversion % between stages,
    the largest drop annotated."""
    box = exhibit_header(p, box, ex)
    stages = ex["data"]["stages"]
    f = fmt_spec({**ex, "data": {"series": [{"values": [s["value"] for s in stages]}]}})
    n = len(stages)
    lab_w = min(2.6, box.w * 0.28)
    conv_w = 1.3
    bar_area = Box(box.x + lab_w, box.y, box.w - lab_w - conv_w, box.h)
    rows = bar_area.rows(n, SPACING["S"])
    vmax = max(s["value"] for s in stages)
    drops = [(stages[i + 1]["value"] / stages[i]["value"] if stages[i]["value"] else 0) for i in range(n - 1)]
    worst = min(range(n - 1), key=lambda i: drops[i]) if n > 1 else None
    for i, (r, s) in enumerate(zip(rows, stages)):
        w = max(0.25, r.w * s["value"] / vmax)
        bb = Box(r.x + (r.w - w) / 2, r.y, w, r.h)
        fill = "primary" if i == 0 or s.get("highlight") else "secondary"
        p.rect(bb, fill=fill)
        val = fmt(float(s["value"]), f)
        if p.text_w(val, "chart", bold=True) + 0.1 < w:
            _label_in(p, bb, val, fill, role="chart", bold=True)
        else:
            p.text(Box(bb.r + 0.05, r.y, 1.0, r.h), val, role="chart", bold=True, anchor="middle", fit=False, kind="label")
        p.text(Box(box.x, r.y, lab_w - 0.15, r.h), s["label"], role="body", anchor="middle", max_lines=2, record=f"stage {i + 1}")
        if i < n - 1:
            conv = drops[i] * 100
            txt = f"{conv:.0f}%"
            p.text(Box(bar_area.r + 0.1, r.b - 0.12, conv_w - 0.1, SPACING["S"] + 0.24), ("▼ " + txt), role="annotation", bold=i == worst, color="negative" if i == worst else "text_muted", anchor="middle", fit=False, kind="label")
    return {"type": "funnel", "stages": n}


def pyramid(p: Painter, box: Box, ex: dict) -> dict:
    """levels top→bottom: [{"label", "text"}]. Narrow top, wide base; descriptions right."""
    box = exhibit_header(p, box, ex)
    levels = ex["data"]["levels"]
    n = len(levels)
    pw = min(box.w * 0.45, 5.5)
    rows = Box(box.x, box.y, pw, box.h).rows(n, 0.06)
    for i, (r, lv) in enumerate(zip(rows, levels)):
        frac = 0.35 + 0.65 * (i + 1) / n
        w = pw * frac
        bb = Box(r.x + (pw - w) / 2, r.y, w, r.h)
        fill = "primary" if i == 0 or lv.get("highlight") else ("secondary" if i < n / 2 else "muted")
        p.shape(MSO_SHAPE.TRAPEZOID if i > 0 else MSO_SHAPE.ISOSCELES_TRIANGLE, bb, fill=fill) if ex.get("shape") == "true" else p.rect(bb, fill=fill)
        _label_in(p, bb.inset(l=0.08, r=0.08), lv["label"], fill, role="body_strong", max_lines=2)
        if lv.get("text"):
            tx = box.x + pw + SPACING["L"]
            p.line(bb.r + 0.05, r.y + r.h / 2, tx - 0.08, r.y + r.h / 2, color="gridline", width=LINES["hairline"])
            p.text(Box(tx, r.y, box.r - tx, r.h), lv["text"], role="body", anchor="middle", record=f"level {i + 1}")
    return {"type": "pyramid", "levels": n}


# ---------------------------------------------------------------------------
# Tile map (grid cartogram) — honest, editable, no shapefiles needed
# ---------------------------------------------------------------------------
TILE_PRESETS = {
    "europe": {
        "IS": (0, 0), "NO": (0, 4), "SE": (0, 5), "FI": (0, 6),
        "IE": (1, 0), "GB": (1, 1), "DK": (1, 4), "EE": (1, 6),
        "NL": (2, 2), "BE": (3, 2), "DE": (2, 3), "PL": (2, 5), "LV": (2, 6), "LT": (2, 7),
        "FR": (3, 1), "LU": (3, 3), "CZ": (3, 4), "SK": (3, 5), "UA": (3, 6),
        "PT": (4, 0), "ES": (4, 1), "CH": (4, 2), "AT": (4, 4), "HU": (4, 5), "RO": (4, 6),
        "IT": (5, 3), "SI": (5, 4), "HR": (5, 5), "RS": (5, 6), "BG": (5, 7),
        "MT": (6, 3), "GR": (6, 6), "CY": (6, 8),
    },
    "spain": {
        "GA": (0, 0), "AS": (0, 1), "CB": (0, 2), "PV": (0, 3), "NA": (0, 4),
        "CL": (1, 1), "RI": (1, 3), "AR": (1, 4), "CT": (1, 5),
        "MD": (2, 2), "EX": (2, 0), "CM": (2, 3), "VC": (2, 4), "IB": (2, 6),
        "AN": (3, 1), "MC": (3, 3), "CN": (4, 0), "CE": (4, 2), "ML": (4, 3),
    },
}


def tile_map(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"preset": "europe"|"spain", "values": {"ES": 12.3, ...}} or {"tiles": [{"code","row","col","value"}]}"""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    f = fmt_spec({**ex, "data": {"series": [{"values": list((d.get("values") or {}).values()) or [t.get("value") for t in d.get("tiles", [])]}]}})
    if d.get("tiles"):
        tiles = [(t["code"], t["row"], t["col"], t.get("value")) for t in d["tiles"]]
    else:
        pos = TILE_PRESETS[d.get("preset", "europe")]
        vals = d.get("values") or {}
        show_all = d.get("show_all", True)
        tiles = [(c, r, k, vals.get(c)) for c, (r, k) in pos.items() if show_all or c in vals]
    nrow = max(t[1] for t in tiles) + 1
    ncol = max(t[2] for t in tiles) + 1
    legend_h = 0.4
    s = min((box.w) / ncol, (box.h - legend_h) / nrow)
    ox = box.x + (box.w - s * ncol) / 2
    oy = box.y
    vals = [t[3] for t in tiles if isinstance(t[3], (int, float))]
    lo, hi = (min(vals), max(vals)) if vals else (0, 1)
    hl = set(ex.get("highlight") or [])
    for code, r, k, v in tiles:
        b = Box(ox + k * s + 0.03, oy + r * s + 0.03, s - 0.06, s - 0.06)
        if isinstance(v, (int, float)):
            t = 0 if hi == lo else (v - lo) / (hi - lo)
            fill = legible_fill(sequential_color(p.theme, 0.12 + 0.83 * t), p.theme)
        else:
            fill = p.theme.c("faint")
        p.rect(b, fill=fill, line="highlight" if code in hl else None, line_w=LINES["accent"])
        txt_col = best_text_on(fill, p.theme)
        paras = [Para(code, bold=True, size=10)]
        if isinstance(v, (int, float)) and s > 0.55:
            paras.append(Para(fmt(float(v), f), size=9))
        p.text(b, paras, role="annotation", align="center", anchor="middle", color=txt_col, spacing=0.95, space_after=0, fit=False)
    # legend: low → high
    lx = ox
    ly = oy + nrow * s + 0.1
    for j in range(5):
        p.rect(Box(lx + j * 0.42, ly + 0.05, 0.42, 0.16), fill=sequential_color(p.theme, 0.12 + 0.83 * j / 4), kind="marker")
    p.text(Box(lx + 2.2, ly, 3.5, 0.26), f"{fmt(lo, f)} → {fmt(hi, f)}" + (f"  ({ex['legend']})" if ex.get("legend") else ""), role="chart_axis", fit=False, kind="label", anchor="middle")
    return {"type": "tile_map", "tiles": len(tiles)}


# ---------------------------------------------------------------------------
# Flow (nodes in columns with arrows)
# ---------------------------------------------------------------------------
def flow(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"nodes": [{"id","label","col","row","emphasis"}], "edges": [{"from","to","label"}]}"""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    nodes = {n["id"]: n for n in d["nodes"]}
    ncol = max(n["col"] for n in nodes.values()) + 1
    nrow = max(n.get("row", 0) for n in nodes.values()) + 1
    gap_x, gap_y = 0.6, 0.35
    cw = (box.w - gap_x * (ncol - 1)) / ncol
    rh = min(1.1, (box.h - gap_y * (nrow - 1)) / nrow)
    total_h = nrow * rh + (nrow - 1) * gap_y
    oy = box.y + (box.h - total_h) / 2
    geo = {}
    for nid, n in nodes.items():
        b = Box(box.x + n["col"] * (cw + gap_x), oy + n.get("row", 0) * (rh + gap_y), cw, rh)
        geo[nid] = b
        fill = "primary" if n.get("emphasis") else "surface"
        p.rect(b, fill=fill)
        _label_in(p, b.inset(l=0.08, r=0.08), n["label"], fill, role="body", record=f"flow {nid}")
    for e in d.get("edges", []):
        a, b = geo[e["from"]], geo[e["to"]]
        if abs(a.y - b.y) < 1e-3:
            p.line(a.r, a.y + a.h / 2, b.x, b.y + b.h / 2, color="neutral", width=LINES["strong"], arrow_end=True, kind="connector")
        elif b.x > a.r:
            p.elbow(a.r, a.y + a.h / 2, b.x - 0.02, b.y + b.h / 2, color="neutral", width=LINES["strong"], mid="h")
        else:
            p.line(a.x + a.w / 2, a.b if b.y > a.y else a.y, b.x + b.w / 2, b.y if b.y > a.y else b.b, color="neutral", width=LINES["strong"], arrow_end=True, kind="connector")
        if e.get("label"):
            mx = (a.r + b.x) / 2
            p.text(Box(mx - gap_x / 2 - 0.2, (a.y + b.y) / 2 + a.h / 2 - 0.32, gap_x + 0.4, 0.26), e["label"], role="annotation", align="center", fit=False, kind="label", color="text_muted")
    return {"type": "flow", "nodes": len(nodes)}


# ---------------------------------------------------------------------------
# Layers / operating model / architecture / journey (grids of labelled cells)
# ---------------------------------------------------------------------------
def layers(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"layers": [{"label", "items": ["..."], "emphasis": bool, "note": "..."}],
              "pillars": [{"label"}]}  (pillars = vertical bars spanning all layers, right side)"""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    lyr = d["layers"]
    pillars = d.get("pillars") or []
    lab_w = min(2.3, box.w * 0.2)
    pil_w = 0.62 if pillars else 0
    pil_total = len(pillars) * (pil_w + 0.08)
    rows = box.rows(len(lyr), 0.1)
    item_x = box.x + lab_w + 0.1
    item_r = box.r - pil_total
    for i, (r, L) in enumerate(zip(rows, lyr)):
        lf = "primary" if L.get("emphasis") else "secondary"
        lb = Box(r.x, r.y, lab_w, r.h)
        p.rect(lb, fill=lf)
        _label_in(p, lb.inset(l=0.1, r=0.1), L["label"], lf, role="body_strong", align="left", max_lines=3, record=f"layer {i + 1}")
        items = L.get("items") or []
        if items:
            cells = Box(item_x, r.y, item_r - item_x, r.h).columns(len(items), 0.08)
            for c, it in zip(cells, items):
                txt = it if isinstance(it, str) else it.get("label", "")
                emph = isinstance(it, dict) and it.get("emphasis")
                change = isinstance(it, dict) and it.get("change")  # "new" | "changed"
                fill = "faint" if not emph else "highlight"
                p.rect(c, fill=fill, line="highlight" if change else None, line_w=LINES["strong"], dash=change == "changed")
                _label_in(p, c.inset(l=0.06, r=0.06), txt, fill, role="body", size=p.style("body")["size"] - (1 if len(items) > 4 else 0), record=f"cell {txt[:18]}")
    for k, pl in enumerate(pillars):
        x = item_r + 0.08 + k * (pil_w + 0.08)
        pb = Box(x, box.y, pil_w, box.h)
        p.rect(pb, fill="surface", line="rule", line_w=LINES["hairline"])
        p.text(pb.inset(t=0.1, b=0.1), pl["label"], role="body_strong", align="center", anchor="middle", vertical=True, record=f"pillar {k}")
    return {"type": ex["type"], "layers": len(lyr)}


def journey(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"stages": ["Discover", ...], "lanes": [{"label", "cells": ["..", ...]}], "pain": [idx...]}"""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    stages = d["stages"]
    lanes = d["lanes"]
    lab_w = min(1.9, box.w * 0.16)
    head_h = 0.5
    area = Box(box.x + lab_w + 0.1, box.y, box.w - lab_w - 0.1, box.h)
    cols = area.columns(len(stages), 0.08)
    pain = set(d.get("pain") or [])
    for j, (c, st) in enumerate(zip(cols, stages)):
        hb = Box(c.x, c.y, c.w + (0.12 if j < len(stages) - 1 else 0), head_h)
        fill = "primary" if j in pain else "secondary"
        p.shape(MSO_SHAPE.CHEVRON if j else MSO_SHAPE.PENTAGON, hb, fill=fill)
        _label_in(p, hb.inset(l=0.25, r=0.25), st, fill, role="body_strong", max_lines=1)
    lane_area = Box(box.x, box.y + head_h + 0.12, box.w, box.h - head_h - 0.12)
    rows = lane_area.rows(len(lanes), 0.08)
    for r, ln in zip(rows, lanes):
        p.text(Box(r.x, r.y, lab_w, r.h), ln["label"], role="body_strong", anchor="middle", max_lines=3)
        p.line(r.x, r.b + 0.04, r.r, r.b + 0.04, color="gridline", width=LINES["hairline"])
        for j, (c, cell) in enumerate(zip(cols, ln.get("cells", []))):
            cb = Box(c.x, r.y, c.w, r.h)
            if j in pain and ln.get("pain_lane"):
                p.rect(cb, fill="faint")
            p.text(cb.inset(l=0.05, r=0.05, t=0.04), cell, role="body", size=p.style("body")["size"] - 1, record=f"journey {j}")
    return {"type": "journey", "stages": len(stages)}


# ---------------------------------------------------------------------------
# Mekko (market map by segment size × share) — editable rectangles
# ---------------------------------------------------------------------------
def mekko(p: Painter, box: Box, ex: dict) -> dict:
    """data: {"columns": [{"label","total", "parts": {"Player A": 30, ...}}], "order": ["Player A", ...]}
    Column width ∝ total; segment height ∝ share within the column."""
    box = exhibit_header(p, box, ex)
    d = ex["data"]
    cols = d["columns"]
    order = d.get("order") or list(dict.fromkeys(k for c in cols for k in c["parts"]))
    f = fmt_spec({**ex, "data": {"series": [{"values": [c["total"] for c in cols]}]}})
    grand = sum(c["total"] for c in cols)
    lab_h = 0.62
    legend_w = min(2.0, box.w * 0.18)
    plot = Box(box.x, box.y + 0.3, box.w - legend_w - 0.15, box.h - lab_h - 0.3)
    palette = [p.theme.c(x) for x in (["primary", "secondary"] + p.theme.series[2:4] + ["neutral", "faint"])]
    colors = {k: palette[i % len(palette)] for i, k in enumerate(order)}
    hl = set(ex.get("highlight") or [])
    x = plot.x
    gap = 0.04
    usable = plot.w - gap * (len(cols) - 1)
    labels: list = []  # drawn after all segments so no segment covers a label
    for c in cols:
        w = usable * c["total"] / grand
        tot = sum(c["parts"].values()) or 1
        y = plot.b
        for k in order:
            v = c["parts"].get(k, 0)
            if v <= 0:
                continue
            h = plot.h * v / tot
            y -= h
            col = colors[k]
            if hl and k not in hl:
                col = p.theme.c("muted")
            b = Box(x, y, w, h)
            p.rect(b, fill=col, line="background", line_w=0.75)
            share = f"{v / tot * 100:.0f}%"
            if hl and k not in hl:
                continue  # focus: only the highlighted player's shares are labelled
            fits_w = w > p.text_w(share, "annotation", bold=bool(hl)) + 0.1
            if h > 0.26 and fits_w:
                labels.append((b, share, best_text_on(col, p.theme), "middle"))
            elif hl and fits_w:  # too thin: label just above the segment
                labels.append((Box(x, y - 0.27, w, 0.25), share, p.theme.c("primary"), "bottom"))
        p.text(Box(x, box.y, w, 0.28), fmt(float(c["total"]), f), role="chart", bold=True, align="center", fit=False, kind="label")
        p.text(Box(x, plot.b + 0.06, w, lab_h - 0.06), c["label"], role="chart_axis", align="center", max_lines=3, record=f"mekko {c['label']}")
        x += w + gap
    for b, txt, colr, anchor in labels:
        p.text(b, txt, role="annotation", bold=bool(hl), align="center", anchor=anchor, color=colr, fit=False, kind="label")
    # legend (right): with a highlight only the highlighted players + "Other players"
    ly = plot.y
    entries = order if not hl else [k for k in order if k in hl] + ["Other players"]
    for k in entries:
        col = colors.get(k, p.theme.c("muted")) if not hl or k in hl else p.theme.c("muted")
        p.rect(Box(plot.r + 0.2, ly + 0.07, 0.14, 0.14), fill=col, kind="marker")
        p.text(Box(plot.r + 0.42, ly, legend_w - 0.3, 0.3), k, role="chart_axis", anchor="middle", max_lines=1, kind="label")
        ly += 0.32
    return {"type": "mekko", "columns": len(cols)}


RENDERERS = {
    "process": process,
    "value_chain": process,
    "timeline": timeline,
    "gantt": gantt,
    "roadmap": gantt,
    "matrix_2x2": matrix_2x2,
    "portfolio": matrix_2x2,
    "tree": tree,
    "driver_tree": tree,
    "org_chart": tree,
    "funnel": funnel,
    "pyramid": pyramid,
    "tile_map": tile_map,
    "flow": flow,
    "layers": layers,
    "operating_model": layers,
    "architecture": layers,
    "journey": journey,
    "mekko": mekko,
    "segmentation": mekko,
}


def render(p: Painter, box: Box, ex: dict) -> dict:
    return RENDERERS[ex["type"]](p, box, ex)
