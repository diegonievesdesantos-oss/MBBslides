"""Text-based components: chrome, commentary, statements, KPIs, columns, statement,
agenda, takeaway, exhibit header.

Design intent: structure comes from typography, alignment and hairlines — not
from boxes. There are no rounded cards; a filled panel is used only for the
takeaway bar and for emphasis on a single element.
"""
from __future__ import annotations

from ..design.tokens import GRID, LINES, SLIDE_H, SLIDE_W, SPACING
from ..layout.engine import EXHIBIT_HEADER_H, Box
from .painter import Painter, Para, plain


# ---------------------------------------------------------------------------
# Chrome
# ---------------------------------------------------------------------------
def chrome(p: Painter, slide: dict, page_no: int, meta: dict) -> dict:
    """Tracker, headline, subheadline, footer. Returns boxes used (for manifest)."""
    used = {}
    g = GRID
    pc = p.for_zone("chrome")
    if slide.get("tracker") and p.profile.get("show_tracker", True):
        b = Box(g.margin_l, g.tracker_y, g.content_w * 0.7, g.tracker_h)
        pc.text(b, slide["tracker"], role="tracker", fit=False, kind="text")
        used["tracker"] = b.to_dict()
    hb = Box(g.margin_l, g.headline_y, balanced_width(pc, slide.get("headline", ""), g.content_w), g.headline_h)
    pc.text(hb, slide.get("headline", ""), role="headline", max_lines=p.profile.get("headline_max_lines", 2), record="headline", kind="text")
    used["headline"] = hb.to_dict()
    if slide.get("subheadline"):
        sb = Box(g.margin_l, g.body_y - 0.06, g.content_w, g.subheadline_h)
        pc.text(sb, slide["subheadline"], role="subheadline", max_lines=1, record="subheadline")
        used["subheadline"] = sb.to_dict()
    footer(pc, slide, page_no, meta)
    return used


def balanced_width(p: Painter, text: str, full_w: float, role: str = "headline") -> float:
    """Narrowest width that keeps the same line count → balanced lines, no widows.
    (Typographic fix only: the words never change.)"""
    from ..design import text_metrics as tm

    st = p.style(role)
    lines = tm.wrap_lines(plain(text), full_w, st["size"], st["bold"])
    if len(lines) < 2:
        return full_w
    n = len(lines)
    lo, hi = full_w * 0.55, full_w
    for _ in range(18):
        mid = (lo + hi) / 2
        if len(tm.wrap_lines(plain(text), mid, st["size"], st["bold"])) > n:
            lo = mid
        else:
            hi = mid
    return min(full_w, hi * 1.03 + 0.05)  # safety margin for renderer differences


def footer(pc: Painter, slide: dict, page_no: int, meta: dict) -> None:
    g = GRID
    lines: list[Para] = []
    for i, fn in enumerate(slide.get("footnotes") or []):
        mark = fn if fn[:2].strip().rstrip(".").isdigit() else f"{i + 1}. {fn}"
        lines.append(Para(mark, space_after=0))
    if slide.get("source"):
        src = slide["source"]
        if not src.lower().startswith(("source", "sources", "note")):
            src = "Source: " + src
        lines.append(Para(src, space_after=0))
    if lines:
        fb = Box(g.margin_l, g.footer_y, g.content_w - 1.2, g.footer_h)
        pc.text(fb, lines, role="source", anchor="bottom", spacing=1.0, space_after=0, record="footer")
    nb = Box(SLIDE_W - g.margin_r - 1.0, g.footer_y, 1.0, g.footer_h)
    right = str(page_no)
    if meta.get("confidentiality"):
        right = f"{meta['confidentiality']}   {page_no}"
        nb = Box(SLIDE_W - g.margin_r - 2.4, g.footer_y, 2.4, g.footer_h)
    pc.text(nb, right, role="page_number", align="right", anchor="bottom", fit=False)


# ---------------------------------------------------------------------------
# Structural slides
# ---------------------------------------------------------------------------
def cover(p: Painter, slide: dict, meta: dict) -> None:
    g = GRID
    pc = p.for_zone("text")
    x = g.margin_l
    pc.rect(Box(x, 2.35, 0.9, 0.07), fill="highlight", kind="fill")
    title = slide.get("title") or meta.get("title", "")
    pc.text(Box(x, 2.6, g.span_w(1, 10), 1.9), title, role="cover_title", anchor="top", max_lines=3, record="cover_title")
    sub = slide.get("subtitle") or meta.get("subtitle")
    if sub:
        pc.text(Box(x, 4.55, g.span_w(1, 9), 0.9), sub, role="cover_subtitle", record="cover_subtitle")
    bits = [b for b in (meta.get("client"), meta.get("date"), meta.get("confidentiality")) if b]
    if bits:
        pc.text(Box(x, 6.55, g.span_w(1, 9), 0.35), "   |   ".join(bits), role="source", size=10, fit=False)


def divider(p: Painter, slide: dict, meta: dict) -> None:
    g = GRID
    pc = p.for_zone("text")
    pc.rect(Box(0, 0, SLIDE_W, SLIDE_H), fill="primary", kind="bleed")
    if slide.get("number") is not None:
        pc.text(Box(g.margin_l, 2.45, 3, 0.7), f"{slide['number']:02d}" if isinstance(slide["number"], int) else str(slide["number"]), role="divider_title", color="highlight", fit=False)
    pc.text(Box(g.margin_l, 3.15, g.span_w(1, 10), 1.6), slide.get("title", ""), role="divider_title", color="background", max_lines=2, record="divider_title")
    if slide.get("subtitle"):
        pc.text(Box(g.margin_l, 4.8, g.span_w(1, 9), 0.9), slide["subtitle"], role="cover_subtitle", color="muted")


def agenda(p: Painter, box: Box, items: list, current: int | None = None) -> None:
    n = len(items)
    row_h = min(0.78, box.h / max(n, 1))
    for i, it in enumerate(items):
        title = it if isinstance(it, str) else it.get("title", "")
        desc = None if isinstance(it, str) else it.get("description")
        y = box.y + i * row_h
        active = current is None or current == i
        col = "primary" if active else "neutral"
        p.text(Box(box.x, y, 0.8, row_h - 0.1), f"{i + 1:02d}", role="section", size=20, color="highlight" if (current == i) else col, fit=False)
        paras = [Para(title, bold=True, color=col, size=16)]
        if desc:
            paras.append(Para(desc, size=12, color="text_muted" if active else "muted"))
        p.text(Box(box.x + 0.9, y + 0.02, box.w - 0.9, row_h - 0.12), paras, role="body", space_after=2, record=f"agenda {i + 1}")
        p.line(box.x, y + row_h - 0.04, box.r, y + row_h - 0.04, color="gridline", width=LINES["hairline"])


def statement(p: Painter, box: Box, data: dict) -> None:
    text = data.get("text", "")
    kind = data.get("type", "statement")
    if kind == "quote":
        p.text(Box(box.x, box.y, box.w, box.h * 0.72), f"“{text}”", role="headline", size=26, anchor="bottom", bold=False, color="primary", record="quote")
        if data.get("attribution"):
            p.text(Box(box.x, box.y + box.h * 0.76, box.w, 0.5), "— " + data["attribution"], role="body", color="text_muted")
        return
    p.rect(Box(box.x, box.y + box.h * 0.18 - 0.2, 0.9, 0.07), fill="highlight")
    p.text(Box(box.x, box.y + box.h * 0.18, box.w, box.h * 0.5), text, role="headline", size=30, record="statement")
    if data.get("support"):
        p.text(Box(box.x, box.y + box.h * 0.7, box.w * 0.85, box.h * 0.3), data["support"], role="body", size=14, color="text_muted")


# ---------------------------------------------------------------------------
# Body text components
# ---------------------------------------------------------------------------
def _points_to_paras(points: list, bullet: str = "•") -> list[Para]:
    paras: list[Para] = []
    for pt in points:
        if isinstance(pt, str):
            paras.append(Para(pt, bullet=bullet))
        else:
            paras.append(Para(pt.get("text", ""), bullet=bullet))
            for sub in pt.get("sub", []) or []:
                paras.append(Para(sub, bullet="–", level=1, color="text_muted"))
    return paras


def commentary(p: Painter, box: Box, data: dict, style: str | None = None) -> None:
    """So-what commentary: optional title + bullets. Styles: rule_left, rule_right, plain, columns."""
    if isinstance(data, list):
        data = {"points": data}
    points = data.get("points") or []
    if style == "columns":
        return commentary_columns(p, box, data)
    inner = box
    if style == "rule_left":
        p.line(box.x, box.y, box.x, box.b, color="rule", width=LINES["rule"])
        inner = box.inset(l=SPACING["M"])
    elif style == "rule_right":
        p.line(box.r, box.y, box.r, box.b, color="rule", width=LINES["rule"])
        inner = box.inset(r=SPACING["M"])
    y = inner.y
    if data.get("title"):
        th, _ = p.measure(data["title"], "exhibit_title", inner.w)
        p.text(Box(inner.x, y, inner.w, th + 0.02), data["title"], role="exhibit_title", color="primary", record="commentary title")
        y += th + SPACING["S"]
    body = Box(inner.x, y, inner.w, inner.b - y)
    bullet = data.get("bullet", "•")
    p.text(body, _points_to_paras(points, bullet), role="body", space_after=data.get("space_after", 8), record="commentary")


def commentary_columns(p: Painter, box: Box, data: dict) -> None:
    points = data.get("points") or []
    n = max(1, len(points))
    cols = box.columns(n, GRID.gutter)
    p.line(box.x, box.y, box.r, box.y, color="rule", width=LINES["rule"])
    for c, pt in zip(cols, points):
        txt = pt if isinstance(pt, str) else pt.get("text", "")
        p.text(c.inset(t=SPACING["S"]), [Para(txt)], role="body", record="takeaway column")


def statements(p: Painter, box: Box, data: dict) -> None:
    """Executive summary rows: number | bold claim | supporting evidence."""
    items = data.get("items") or []
    style = data.get("style", "numbered")  # numbered | scr
    n = max(1, len(items))
    gap = SPACING["S"]
    row_h = (box.h - gap * (n - 1)) / n
    label_w = 1.55 if style == "scr" else 0.55
    claim_w = (box.w - label_w) * 0.42
    for i, it in enumerate(items):
        y = box.y + i * (row_h + gap)
        if i > 0:
            p.line(box.x, y - gap / 2, box.r, y - gap / 2, color="gridline", width=LINES["hairline"])
        label = it.get("label") if style == "scr" else f"{i + 1}"
        p.text(Box(box.x, y + 0.04, label_w - 0.1, 0.45), label or "", role="section", color="highlight" if style == "numbered" else "primary", size=18 if style == "numbered" else 12, fit=False)
        cx = box.x + label_w
        p.text(Box(cx, y + 0.04, claim_w - SPACING["M"], row_h - 0.08), it.get("title", ""), role="body_strong", size=14, color="primary", record=f"statement {i + 1} claim", anchor="top")
        support = it.get("text") or it.get("points") or ""
        paras = [Para(s, bullet="•") for s in support] if isinstance(support, list) else [Para(support)]
        p.text(Box(cx + claim_w, y + 0.04, box.r - cx - claim_w, row_h - 0.08), paras, role="body", record=f"statement {i + 1} support")


def kpis(p: Painter, box: Box, data: dict) -> None:
    items = data.get("items") if isinstance(data, dict) else data
    items = items or []
    grid_mode = isinstance(data, dict) and data.get("style") == "grid"
    if grid_mode:
        n = len(items)
        ncols = 3 if n > 4 else 2
        nrows = -(-n // ncols)
        cells = []
        for r_box in box.rows(nrows, SPACING["L"]):
            cells.extend(r_box.columns(ncols, GRID.gutter * 2))
        for cell, it in zip(cells, items):
            p.line(cell.x, cell.y, cell.r, cell.y, color="rule", width=LINES["rule"])
            _kpi(p, cell.inset(t=SPACING["S"]), it, big=True)
        return
    n = max(1, len(items))
    cols = box.columns(n, GRID.gutter * 2)
    for i, (c, it) in enumerate(zip(cols, items)):
        if i > 0:
            xl = c.x - GRID.gutter
            p.line(xl, c.y + 0.05, xl, c.b - 0.05, color="gridline", width=LINES["rule"])
        _kpi(p, c, it)


def _kpi(p: Painter, c: Box, it: dict, big: bool = False) -> None:
    val = str(it.get("value", ""))
    vh = 0.62 if not big else 0.75
    p.text(Box(c.x, c.y, c.w, vh), val, role="kpi_value", size=None if not big else 34, max_lines=1, color=it.get("color", "primary"), record=f"kpi {val}")
    y = c.y + vh
    if it.get("delta"):
        d = str(it["delta"])
        trend = it.get("trend") or ("up" if d.strip().startswith("+") else "down" if d.strip().startswith(("-", "−")) else "flat")
        good = it.get("good", "up")
        col = "neutral" if trend == "flat" else ("positive" if trend == good else "negative")
        arrow = {"up": "▲ ", "down": "▼ ", "flat": ""}[trend]
        p.text(Box(c.x, y, c.w, 0.26), arrow + d, role="kpi_label", bold=True, color=col, max_lines=1)
        y += 0.28
    lh, _ = p.measure(it.get("label", ""), "kpi_label", c.w)
    p.text(Box(c.x, y, c.w, min(c.b - y, lh + 0.05)), it.get("label", ""), role="kpi_label", record="kpi label")
    y += lh + 0.08
    if it.get("note") and c.b - y > 0.25:
        p.text(Box(c.x, y, c.w, c.b - y), it["note"], role="body", size=11, record="kpi note")


def column(p: Painter, box: Box, data: dict, index: int = 0) -> None:
    """One comparison column: header (optionally emphasised) + bullets / key facts."""
    head = data.get("title", "")
    emphasis = data.get("emphasis", False)
    hh = 0.62
    if emphasis:
        p.rect(Box(box.x, box.y, box.w, hh), fill="primary")
        p.text(Box(box.x, box.y, box.w, hh).inset(l=SPACING["S"], r=SPACING["S"]), head, role="section", color="background", anchor="middle", max_lines=2, record="column header")
    else:
        p.text(Box(box.x, box.y, box.w, hh - 0.08), head, role="section", color="primary", anchor="bottom", max_lines=2, record="column header")
        p.line(box.x, box.y + hh, box.r, box.y + hh, color="primary", width=LINES["strong"])
    y = box.y + hh + SPACING["M"]
    if data.get("metric"):
        p.text(Box(box.x, y, box.w, 0.55), str(data["metric"]), role="kpi_value", size=24, max_lines=1)
        y += 0.55
        if data.get("metric_label"):
            p.text(Box(box.x, y, box.w, 0.3), data["metric_label"], role="kpi_label", max_lines=1)
            y += 0.4
    if data.get("subtitle"):
        sh, _ = p.measure(data["subtitle"], "body_strong", box.w)
        p.text(Box(box.x, y, box.w, sh + 0.04), data["subtitle"], role="body_strong", record="column subtitle")
        y += sh + SPACING["S"]
    pts = data.get("points") or []
    if pts:
        p.text(Box(box.x, y, box.w, box.b - y), _points_to_paras(pts), role="body", space_after=6, record="column points")


def takeaway(p: Painter, box: Box, text: str) -> None:
    p.rect(box, fill="faint")
    p.rect(Box(box.x, box.y, 0.07, box.h), fill="highlight")
    p.text(box.inset(l=SPACING["M"] + 0.07, r=SPACING["M"]), text, role="body_strong", size=13, color="primary", anchor="middle", max_lines=2, record="takeaway")


def exhibit_header(p: Painter, box: Box, ex: dict) -> Box:
    """Draw exhibit title/unit and return the remaining plot box."""
    title = ex.get("title")
    if not title:
        return box
    unit = ex.get("unit")
    txt = f"**{title}**" + (f", {unit}" if unit else "")
    p.text(Box(box.x, box.y, box.w, 0.3), [Para(txt)], role="exhibit_unit", color="text", max_lines=1, record="exhibit title")
    return Box(box.x, box.y + EXHIBIT_HEADER_H, box.w, box.h - EXHIBIT_HEADER_H)


def legend(p: Painter, box: Box, entries: list[tuple[str, str]], y: float | None = None) -> float:
    """Inline legend (swatch + label) — only used when direct labelling is impossible."""
    x = box.x
    y = box.y if y is None else y
    for label, color in entries:
        p.rect(Box(x, y + 0.07, 0.14, 0.14), fill=color, kind="marker")
        w = p.text_w(label, "chart_axis") + 0.05
        p.text(Box(x + 0.2, y, w + 0.1, 0.28), label, role="chart_axis", fit=False, kind="label")
        x += 0.2 + w + 0.3
    return 0.3


def bullets_block(p: Painter, box: Box, points: list, title: str | None = None) -> None:
    commentary(p, box, {"title": title, "points": points}, style="plain")


__all__ = [
    "chrome",
    "cover",
    "divider",
    "agenda",
    "statement",
    "commentary",
    "statements",
    "kpis",
    "column",
    "takeaway",
    "exhibit_header",
    "legend",
    "plain",
]
