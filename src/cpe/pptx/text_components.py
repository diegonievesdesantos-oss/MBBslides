"""Text-based components: chrome, commentary, statements, KPIs, columns, statement,
agenda, takeaway, exhibit header.

Design intent: structure comes from typography, alignment and hairlines — not
from boxes. There are no rounded cards; a filled panel is used only for the
takeaway bar and for emphasis on a single element.
"""
from __future__ import annotations

from ..design.tokens import GRID, LINES, SLIDE_H, SLIDE_W, SPACING
from ..layout.engine import EXHIBIT_HEADER_H, Box
from .adaptive import body_cap, optical_top, pick_scale, size
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
    head_w = min(g.content_w, (g.headline_right_limit or SLIDE_W) - g.margin_l)
    hb = Box(g.margin_l, g.headline_y, balanced_width(pc, slide.get("headline", ""), head_w), g.headline_h)
    pc.text(hb, slide.get("headline", ""), role="headline", max_lines=p.profile.get("headline_max_lines", 2), record="headline", kind="text")
    used["headline"] = hb.to_dict()
    if slide.get("subheadline"):
        sb = Box(g.margin_l, g.body_y - 0.06, g.content_w, g.subheadline_h)
        pc.text(sb, slide["subheadline"], role="subheadline", max_lines=1, record="subheadline")
        used["subheadline"] = sb.to_dict()
    footer(pc, slide, page_no, meta)
    return used


def balanced_width(p: Painter, text: str, full_w: float, role: str = "headline") -> float:
    """Headlines run to the right margin (full width). The only exception is a widow
    (a single word on the last line): then the box narrows by the minimum needed to
    carry one more word down (never below 85% of the width). Words never change.

    Renderers wrap within about ±1% of our metrics, so a width is accepted only if it
    is widow-free for every width in that tolerance band."""
    from ..design import text_metrics as tm

    st = p.style(role)
    fam = tm.family_for(p.theme.font_for(role))
    tol = 0.012

    def widow_or_extra(w, max_lines):
        for f in (1 - tol, 1.0, 1 + tol):
            ls = tm.wrap_lines(plain(text), w * f, st["size"], st["bold"], fam)
            if len(ls) >= 2 and len(ls[-1].split()) == 1:
                return True
            if max_lines and len(ls) > max_lines:
                return True
        return False

    base_lines = len(tm.wrap_lines(plain(text), full_w, st["size"], st["bold"], fam))
    if base_lines < 2 or not widow_or_extra(full_w, None):
        return full_w
    w = full_w
    while w > full_w * 0.85:
        w -= 0.03
        if not widow_or_extra(w, max(2, base_lines)):
            return w
    return full_w


def footer(pc: Painter, slide: dict, page_no: int, meta: dict) -> None:
    g = GRID
    lines: list[Para] = []
    for i, fn in enumerate(slide.get("footnotes") or []):
        mark = fn if fn[:2].strip().rstrip(".").isdigit() else f"{i + 1}. {fn}"
        lines.append(Para(mark, space_after=0))
    if slide.get("source"):
        src = slide["source"]
        if not src.lower().startswith(("source", "sources", "note", "fuente", "fuentes", "nota")):
            src = ("Fuente: " if str(meta.get("language") or "").lower().startswith("es") else "Source: ") + src
        lines.append(Para(src, space_after=0))
    right = min(SLIDE_W - g.margin_r, g.footer_right_limit or SLIDE_W)
    if lines:
        fb = Box(g.margin_l, g.footer_y, right - g.margin_l - 1.2 - (0.0 if not meta.get("confidentiality") else 1.4), g.footer_h)
        pc.text(fb, lines, role="source", anchor="bottom", spacing=1.0, space_after=0, record="footer")
    label = str(page_no)
    nb = Box(right - 1.0, g.footer_y, 1.0, g.footer_h)
    if meta.get("confidentiality"):
        label = f"{meta['confidentiality']}   {page_no}"
        nb = Box(right - 2.4, g.footer_y, 2.4, g.footer_h)
    pc.text(nb, label, role="page_number", align="right", anchor="bottom", fit=False)


# ---------------------------------------------------------------------------
# Structural slides
# ---------------------------------------------------------------------------
def cover(p: Painter, slide: dict, meta: dict) -> None:
    """Title block measured and set on the optical centre of the upper field; client, date and
    confidentiality sit in a primary-colour band across the foot. (Fixed positions left a one-line
    title floating above a large gap and the lower half of the page empty.)"""
    g = GRID
    pc = p.for_zone("text")
    x = g.margin_l
    title = slide.get("title") or meta.get("title", "")
    sub = slide.get("subtitle") or meta.get("subtitle")
    tw, sw = g.span_w(1, 10), g.span_w(1, 9)
    th = min(p.measure(title, "cover_title", tw)[0], 3 * p.measure("X", "cover_title", tw)[0]) + 0.1  # same width as the box (no insets)
    sh = (p.measure(sub, "cover_subtitle", sw)[0] + 0.1) if sub else 0.0
    band_y = SLIDE_H * 0.8
    bar, gap_t, gap_s = 0.07, 0.25, 0.22
    group = bar + gap_t + th + (gap_s + sh if sub else 0.0)
    field_top = 0.4
    top = field_top + max(0.0, (band_y - field_top - group) * 0.55)  # a touch below centre: the band is visually heavy
    pc.rect(Box(x, top, 0.9, bar), fill="highlight", kind="fill")
    y = top + bar + gap_t
    pc.text(Box(x, y, tw, th), title, role="cover_title", anchor="top", max_lines=3, record="cover_title")
    if sub:
        pc.text(Box(x, y + th + gap_s, sw, sh), sub, role="cover_subtitle", anchor="top", record="cover_subtitle")
    pc.rect(Box(0, band_y, SLIDE_W, SLIDE_H - band_y), fill="primary", kind="bleed")
    bits = [b for b in (meta.get("client"), meta.get("date"), meta.get("confidentiality")) if b]
    if bits:
        pc.text(Box(x, band_y + (SLIDE_H - band_y - 0.35) / 2, sw, 0.35), "   |   ".join(bits), role="source", size=11,
                color="background", fit=False, anchor="middle")


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
    """A compact index, centred on the slide's optical centre: an agenda is navigation, it is not
    stretched over the full height (stretched rows read as a sparse list) nor stuck at the top."""
    n = len(items)
    row_h = min(0.95, box.h / max(n, 1))
    block = n * row_h
    top = box.y + max(0.0, (box.h - block) * 0.42)  # slightly above the geometric centre
    for i, it in enumerate(items):
        title = it if isinstance(it, str) else it.get("title", "")
        desc = None if isinstance(it, str) else it.get("description")
        y = top + i * row_h
        active = current is None or current == i
        col = "primary" if active else "neutral"
        if i == 0:
            p.line(box.x, y - 0.04, box.r, y - 0.04, color="rule", width=LINES["rule"])
        p.text(Box(box.x, y + 0.08, 0.9, row_h - 0.16), f"{i + 1:02d}", role="section", size=24, color="highlight" if (current == i or current is None) else col,
               fit=False, anchor="middle")
        paras = [Para(title, bold=True, color=col, size=18)]
        if desc:
            paras.append(Para(desc, size=13, color="text_muted" if active else "muted"))
        p.text(Box(box.x + 1.0, y + 0.06, box.w - 1.0, row_h - 0.12), paras, role="body", space_after=2, anchor="middle", record=f"agenda {i + 1}")
        p.line(box.x, y + row_h - 0.04, box.r, y + row_h - 0.04, color="gridline", width=LINES["hairline"])


def statement(p: Painter, box: Box, data: dict) -> None:
    text = data.get("text", "")
    kind = data.get("type", "statement")
    if kind == "quote":
        p.text(Box(box.x, box.y, box.w, box.h * 0.72), f"“{text}”", role="headline", size=26, anchor="bottom", bold=False, color="primary", record="quote")
        if data.get("attribution"):
            p.text(Box(box.x, box.y + box.h * 0.76, box.w, 0.5), "— " + data["attribution"], role="body", color="text_muted")
        return
    # the bar, the statement and its support form ONE block, set on the optical centre of the zone.
    # Fallback ladder: measure (with a margin for renderer metrics) → narrower/wider measure →
    # optical placement → smaller type down to a readability floor → no longer a statement: set as
    # body text with a warning (never clipped).
    sup = data.get("support")
    sup_w = box.w * 0.85
    gap = 0.35 if sup else 0.0
    bar = 0.27
    chosen = None
    for sz in STATEMENT_SIZES:
        th, lines = p.measure(text, "headline", box.w * STATEMENT_MEASURE, size=sz)
        sh = p.measure(sup, "body", sup_w * STATEMENT_MEASURE, size=14)[0] if sup else 0.0
        group = bar + th * STATEMENT_LEADING + gap + sh * STATEMENT_LEADING
        if lines <= STATEMENT_MAX_LINES and group <= box.h * 0.9:
            chosen = (sz, th * STATEMENT_LEADING, sh * STATEMENT_LEADING, group)
            break
    if chosen is None:
        p.warn("STATEMENT_TOO_LONG", f"Statement of {len(text.split())} words does not read as a statement at ≥ {STATEMENT_SIZES[-1]} pt; set as body text. Shorten it or move the reasoning to the support line.")
        paras = [Para(text, bold=True, color="primary")] + ([Para(sup, color="text_muted")] if sup else [])
        p.text(box, paras, role="body", size=18, floor=12, anchor="middle", record="statement")
        return
    sz, th, sh, group = chosen
    top = box.y + max(0.0, (box.h - group) * 0.42)
    p.rect(Box(box.x, top, 0.9, 0.07), fill="highlight")
    p.text(Box(box.x, top + bar, box.w, min(box.b - top - bar, th + 0.1)), text, role="headline", size=sz, floor=STATEMENT_SIZES[-1], record="statement")
    if sup:
        y = top + bar + th + gap
        p.text(Box(box.x, y, sup_w, min(box.b - y, sh + 0.1)), sup, role="body", size=14, color="text_muted")


STATEMENT_SIZES = (30, 28, 26, 24, 22)  # 22 pt: still clearly display type over 14 pt support
STATEMENT_MEASURE = 0.92  # wrap against 92% of the width: renderer metrics differ from ours
STATEMENT_LEADING = 1.1
STATEMENT_MAX_LINES = 4


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
    if style in (None, "plain") and len(points) == 1 and body.h > 2.5:
        from ..core.headline import words

        txt = points[0] if isinstance(points[0], str) else points[0].get("text", "")
        if len(words(txt)) <= 35:  # one argument on a full slide: set it as a statement, not a lonely bullet
            p.rect(Box(body.x, body.y + body.h * 0.12, 0.9, 0.07), fill="highlight")
            p.text(Box(body.x, body.y + body.h * 0.12 + 0.25, body.w * 0.9, body.h * 0.6), txt, role="headline", size=28, bold=False, color="primary", record="statement point")
            return
    bullet = data.get("bullet", "•")
    p.text(body, _points_to_paras(points, bullet), role="body", space_after=data.get("space_after", 8), record="commentary")


def commentary_columns(p: Painter, box: Box, data: dict) -> None:
    points = data.get("points") or []
    n = max(1, len(points))
    if data.get("title"):
        th, _ = p.measure(data["title"], "exhibit_title", box.w)
        p.text(Box(box.x, box.y, box.w, th + 0.02), data["title"], role="exhibit_title", color="primary", max_lines=1, record="takeaways title")
        box = Box(box.x, box.y + th + SPACING["XS"], box.w, box.h - th - SPACING["XS"])
    cols = box.columns(n, GRID.gutter)
    p.line(box.x, box.y, box.r, box.y, color="rule", width=LINES["rule"])
    for c, pt in zip(cols, points):
        txt = pt if isinstance(pt, str) else pt.get("text", "")
        p.text(c.inset(t=SPACING["S"]), [Para(txt)], role="body", record="takeaway column")


def statements(p: Painter, box: Box, data: dict) -> None:
    """Executive summary rows: number | bold claim | supporting evidence.

    Dense summaries share the full height evenly. When the rows are short (they would need well
    under the available height), the rows keep their natural height plus a fixed breathing space
    and are set as ONE block on the optical centre, instead of being spread into thin lines
    separated by empty bands."""
    items = data.get("items") or []
    style = data.get("style", "numbered")  # numbered | scr
    n = max(1, len(items))
    gap = SPACING["S"]
    label_w = 1.55 if style == "scr" else 0.55
    claim_w = (box.w - label_w) * 0.42
    support_w = box.w - label_w - claim_w

    def need(it):
        sup = it.get("text") or it.get("points") or ""
        sup = " ".join(sup) if isinstance(sup, list) else sup
        h_claim = p.measure(it.get("title", ""), "body_strong", claim_w - SPACING["M"], size=14)[0]
        h_sup = p.measure(sup, "body", support_w)[0] if sup else 0.0
        return max(h_claim, h_sup, 0.3)

    pad = 0.55  # breathing space inside a compact row (above + below the text)
    needs = [need(it) for it in items]
    compact_total = sum(h + pad for h in needs) + gap * (n - 1)
    if compact_total <= box.h * 0.72:
        heights = [h + pad for h in needs]
        top = box.y + (box.h - compact_total) * 0.42
    else:
        heights = [(box.h - gap * (n - 1)) / n] * n
        top = box.y
    y = top
    for i, (it, row_h) in enumerate(zip(items, heights)):
        if i > 0:
            p.line(box.x, y - gap / 2, box.r, y - gap / 2, color="gridline", width=LINES["hairline"])
        label = it.get("label") if style == "scr" else f"{i + 1}"
        # content sits on the row's centre line
        p.text(Box(box.x, y + 0.04, label_w - 0.1, row_h - 0.08), label or "", role="section", color="highlight" if style == "numbered" else "primary",
               size=18 if style == "numbered" else 12, fit=False, anchor="middle")
        cx = box.x + label_w
        p.text(Box(cx, y + 0.04, claim_w - SPACING["M"], row_h - 0.08), it.get("title", ""), role="body_strong", size=14, color="primary", record=f"statement {i + 1} claim", anchor="middle")
        support = it.get("text") or it.get("points") or ""
        paras = [Para(s, bullet="•") for s in support] if isinstance(support, list) else [Para(support)]
        p.text(Box(cx + claim_w, y + 0.04, support_w, row_h - 0.08), paras, role="body", anchor="middle", record=f"statement {i + 1} support")
        y += row_h + gap
    if heights and heights[0] != (box.h - gap * (n - 1)) / n:  # frame the compact block
        p.line(box.x, top - gap / 2, box.r, top - gap / 2, color="rule", width=LINES["rule"])
        p.line(box.x, y - gap * 1.5, box.r, y - gap * 1.5, color="gridline", width=LINES["hairline"])


def _trend(it: dict) -> tuple[str, str]:
    d = str(it["delta"])
    trend = it.get("trend") or ("up" if d.strip().startswith("+") else "down" if d.strip().startswith(("-", "−")) else "flat")
    col = "neutral" if trend == "flat" else ("positive" if trend == it.get("good", "up") else "negative")
    return {"up": "▲ ", "down": "▼ ", "flat": ""}[trend] + d, col


def _kpi_geom(p: Painter, w: float, it: dict, k: float, big: bool = False) -> dict:
    vs = size(34 if big else p.style("kpi_value")["size"], k, 54)
    ds, ls, ns = size(p.style("kpi_label")["size"], k, 16), size(p.style("kpi_label")["size"], k, 15), size(11, k, 14)
    vh = vs / 72 * 1.35
    dh = ds / 72 * 1.5 if it.get("delta") else 0.0
    lh = p.measure(it.get("label", ""), "kpi_label", w, size=ls)[0]
    nh = p.measure(it["note"], "body", w, size=ns)[0] + 0.08 if it.get("note") else 0.0
    return {"vs": vs, "ds": ds, "ls": ls, "ns": ns, "vh": vh, "dh": dh, "lh": lh, "nh": nh, "h": vh + dh + lh + 0.08 + nh}


def kpis(p: Painter, box: Box, data: dict) -> None:
    """KPI strip or grid (v1.4): the tiles take the largest readable scale that leaves the band
    breathing, and the set sits on the optical centre — not a strip of small figures under the
    headline with the slide empty below."""
    items = data.get("items") if isinstance(data, dict) else data
    items = items or []
    if len(items) == 1 and box.h > 2.5:
        return kpi_hero(p, box, items[0])
    grid_mode = isinstance(data, dict) and data.get("style") == "grid"
    n = max(1, len(items))
    if grid_mode:
        ncols = 3 if n > 4 else 2
        nrows = -(-n // ncols)
        gap_x, gap_y = GRID.gutter * 2, SPACING["L"]
        cw = (box.w - gap_x * (ncols - 1)) / ncols

        def block(k):
            rows_h = [max(_kpi_geom(p, cw, it, k, big=True)["h"] for it in items[r * ncols:(r + 1) * ncols]) + SPACING["S"] for r in range(nrows)]
            return sum(rows_h) + gap_y * (nrows - 1)

        k, h = pick_scale(block, box.h, fill=0.8, cap=1.35)
        rh = (h - gap_y * (nrows - 1)) / nrows
        y = optical_top(box, h)
        for r in range(nrows):
            for c in range(ncols):
                i = r * ncols + c
                if i >= n:
                    break
                cell = Box(box.x + c * (cw + gap_x), y + r * (rh + gap_y), cw, rh)
                p.line(cell.x, cell.y, cell.r, cell.y, color="rule", width=LINES["rule"])
                _kpi(p, cell.inset(t=SPACING["S"]), items[i], big=True, k=k)
        return
    cw = (box.w - GRID.gutter * 2 * (n - 1)) / n
    if box.h < 2.5:  # a KPI strip above an exhibit: its band is already sized to it
        for i, it in enumerate(items):
            c = Box(box.x + i * (cw + GRID.gutter * 2), box.y, cw, box.h)
            if i > 0:
                xl = c.x - GRID.gutter
                p.line(xl, c.y + 0.05, xl, c.b - 0.05, color="gridline", width=LINES["rule"])
            _kpi(p, c, it)
        return
    # a KPI set that IS the slide: one card per figure (v1.4) — the dashboard pattern. v1.5: the
    # arrangement follows the content (one row while the figures stay large enough, 3+2 / rows of 3
    # when they would not), card height follows what the cards hold, text contrast is computed
    # against the card fill
    rows = _kpi_rows(p, box, items)
    gap_x, gap_y = GRID.gutter * 2, SPACING["L"]
    per_row = max(len(r) for r in rows)
    cw = (box.w - gap_x * (per_row - 1)) / per_row
    inner = cw - 2 * SPACING["M"]
    fill_share = 0.5 if len(rows) == 1 else 0.78
    k, need = pick_scale(lambda k: max(_kpi_geom(p, inner, it, k)["h"] for it in items), box.h / len(rows), fill=fill_share, cap=1.5)
    ch = max(need + 2 * SPACING["L"], min(2.6, box.h * 0.55) if len(rows) == 1 else 0)
    ch = min(ch, (box.h - gap_y * (len(rows) - 1)) / len(rows))
    total = ch * len(rows) + gap_y * (len(rows) - 1)
    y = optical_top(box, total)
    for r, row in enumerate(rows):
        x0 = box.x + (box.w - (len(row) * cw + (len(row) - 1) * gap_x)) / 2  # a short last row is centred
        for i, it in enumerate(row):
            c = Box(x0 + i * (cw + gap_x), y + r * (ch + gap_y), cw, ch)
            p.rect(c, fill="surface")
            g = _kpi_geom(p, inner, it, k)
            _kpi(p, Box(c.x + SPACING["M"], c.y + (ch - g["h"]) / 2, inner, g["h"] + 0.05), it, k=k, on="surface")


def _kpi_rows(p: Painter, box: Box, items: list) -> list[list]:
    """One row of cards while every figure stays legible at full size; otherwise 3 per row
    (5 → 3 + 2, 6 → 3 + 3, …). Driven by measured widths, not by the count alone."""
    n = len(items)
    if n <= 3:
        return [items]
    cw = (box.w - GRID.gutter * 2 * (n - 1)) / n - 2 * SPACING["M"]
    vs = p.style("kpi_value")["size"]
    widest = max(p.text_w(str(it.get("value", "")), "kpi_value", size=vs) for it in items)
    longest_label = max(p.measure(it.get("label", ""), "kpi_label", cw)[1] for it in items)
    if n <= 4 or (n == 5 and widest <= cw and longest_label <= 2):
        return [items]
    return [items[i:i + 3] for i in range(0, n, 3)]


def kpi_hero(p: Painter, box: Box, it: dict) -> None:
    """One number IS the message: a hero figure, not a small tile floating in white.
    (v1.4) The figure group sits on the optical centre; with a note, figure and note form two
    balanced columns; without one, the figure is centred on the slide (intentional whitespace,
    not a figure stuck in the top-left corner of an empty slide)."""
    val = str(it.get("value", ""))
    note = it.get("note")
    vs = 88 if len(val) <= 6 else 72 if len(val) <= 10 else 60
    vh = vs / 72 * 1.3
    dh = 0.6 if it.get("delta") else 0.0
    w = box.w * 0.55 if note else box.w
    lh = p.measure(it.get("label", ""), "body", w, size=20)[0] + 0.05
    group = 0.27 + vh + dh + lh
    top = optical_top(box, group)
    align = "left" if note else "center"
    if note:
        p.rect(Box(box.x, top, 0.9, 0.07), fill="highlight")
    else:
        p.rect(Box(box.x + box.w / 2 - 0.45, top, 0.9, 0.07), fill="highlight")
    y = top + 0.27
    p.text(Box(box.x, y, w, vh), val, role="kpi_value", size=vs, max_lines=1, align=align, color=it.get("color", "primary"), record="kpi hero")
    y += vh
    if it.get("delta"):
        txt, col = _trend(it)
        p.text(Box(box.x, y, w, 0.5), txt, role="kpi_label", size=22, bold=True, color=col, align=align, max_lines=1)
        y += dh
    p.text(Box(box.x, y, w, lh + 0.1), it.get("label", ""), role="body", size=20, color="text_muted", align=align, record="kpi hero label")
    if note:
        nx = box.x + box.w * 0.6
        nh = p.measure(note, "body", box.r - nx, size=18)[0] + 0.1
        p.line(nx - 0.3, top, nx - 0.3, top + group, color="rule")
        p.text(Box(nx, top + max(0.0, (group - nh) / 2), box.r - nx, nh + 0.1), note, role="body", size=18, record="kpi hero note")


def _kpi(p: Painter, c: Box, it: dict, big: bool = False, k: float = 1.0, on: str | None = None) -> None:
    """One KPI. `on`: the fill token it sits on — every text colour is then made legible against
    that fill (deltas, muted labels), not against the page."""
    g = _kpi_geom(p, c.w, it, k, big=big)
    bg = p.color(on) if on else None

    def col(token, size, bold=False):
        return p.legible(token, size, bold, bg=bg) if bg else token

    val = str(it.get("value", ""))
    p.text(Box(c.x, c.y, c.w, g["vh"]), val, role="kpi_value", size=g["vs"], max_lines=1, color=col(it.get("color", "primary"), g["vs"], True), record=f"kpi {val}")
    y = c.y + g["vh"]
    if it.get("delta"):
        txt, dcol = _trend(it)
        p.text(Box(c.x, y, c.w, g["dh"]), txt, role="kpi_label", size=g["ds"], bold=True, color=col(dcol, g["ds"], True), max_lines=1)
        y += g["dh"]
    p.text(Box(c.x, y, c.w, min(c.b - y, g["lh"] + 0.05)), it.get("label", ""), role="kpi_label", size=g["ls"],
           color=col("text_muted", g["ls"]) if bg else None, record="kpi label")
    y += g["lh"] + 0.08
    if it.get("note") and c.b - y > 0.25:
        p.text(Box(c.x, y, c.w, c.b - y), it["note"], role="body", size=g["ns"], color=col("text", g["ns"]) if bg else None, record="kpi note")


def _column_geom(p: Painter, w: float, data: dict, k: float) -> dict:
    hs, bs = size(p.style("section")["size"], k, body_cap(p, 20)), size(p.style("body")["size"], k, body_cap(p, 18))
    hh = max(0.62, p.measure(data.get("title", ""), "section", w - 2 * SPACING["S"], size=hs)[1] * hs / 72 * 1.25 + 0.22)
    h = hh + SPACING["M"]
    if data.get("metric"):
        h += 0.55 * max(1.0, k) + (0.4 if data.get("metric_label") else 0)
    if data.get("subtitle"):
        h += p.measure(data["subtitle"], "body_strong", w, size=bs)[0] + SPACING["S"]
    pts = data.get("points") or []
    h += sum(p.measure(pt if isinstance(pt, str) else pt.get("text", ""), "body", w - 0.18, size=bs)[0] + 6 * k / 72 + 0.02 for pt in pts)
    return {"hs": hs, "bs": bs, "hh": hh, "h": h}


def columns(painters: list[Painter], boxes: list[Box], cols: list[dict]) -> None:
    """All comparison columns at ONE scale and ONE top edge (v1.4): short columns get readable type
    and sit on the optical centre as a group, instead of a band of small text under the headline
    with the lower half of the slide empty. Unequal content keeps aligned headers; the group is
    balanced by its tallest column."""
    if not boxes:
        return
    p = painters[0]
    avail = min(b.h for b in boxes)
    k, block = pick_scale(lambda k: max(_column_geom(p, b.w, c, k)["h"] for b, c in zip(boxes, cols)), avail, fill=0.86, cap=1.5)
    hh = max(_column_geom(p, b.w, c, k)["hh"] for b, c in zip(boxes, cols))
    top = optical_top(boxes[0], block) if block < avail else boxes[0].y
    for i, (pz, b, c) in enumerate(zip(painters, boxes, cols)):
        column(pz, Box(b.x, top, b.w, b.b - top), c, index=i, k=k, hh=hh)


def column(p: Painter, box: Box, data: dict, index: int = 0, k: float = 1.0, hh: float | None = None) -> None:
    """One comparison column: header (optionally emphasised) + bullets / key facts."""
    head = data.get("title", "")
    emphasis = data.get("emphasis", False)
    g = _column_geom(p, box.w, data, k)
    hh = hh or g["hh"]
    if emphasis:
        p.rect(Box(box.x, box.y, box.w, hh), fill="primary")
        p.text(Box(box.x, box.y, box.w, hh).inset(l=SPACING["S"], r=SPACING["S"]), head, role="section", size=g["hs"], color="background", anchor="middle", max_lines=2, record="column header")
    else:
        p.text(Box(box.x, box.y, box.w, hh - 0.08), head, role="section", size=g["hs"], color="primary", anchor="bottom", max_lines=2, record="column header")
        p.line(box.x, box.y + hh, box.r, box.y + hh, color="primary", width=LINES["strong"])
    y = box.y + hh + SPACING["M"]
    if data.get("metric"):
        mh = 0.55 * max(1.0, k)
        p.text(Box(box.x, y, box.w, mh), str(data["metric"]), role="kpi_value", size=size(24, k, 32), max_lines=1)
        y += mh
        if data.get("metric_label"):
            p.text(Box(box.x, y, box.w, 0.3), data["metric_label"], role="kpi_label", size=size(p.style("kpi_label")["size"], k, 14), max_lines=1)
            y += 0.4
    if data.get("subtitle"):
        sh, _ = p.measure(data["subtitle"], "body_strong", box.w, size=g["bs"])
        p.text(Box(box.x, y, box.w, sh + 0.04), data["subtitle"], role="body_strong", size=g["bs"], record="column subtitle")
        y += sh + SPACING["S"]
    pts = data.get("points") or []
    if pts:
        p.text(Box(box.x, y, box.w, box.b - y), _points_to_paras(pts), role="body", size=g["bs"], space_after=6 * k, record="column points")


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


QUOTE_MARKS = ('"', "\u201c", "\u00ab", "'")


def _plain_points(points: list) -> list[str]:
    return [pt if isinstance(pt, str) else pt.get("text", "") for pt in points or []]


def text_form(points: list) -> str:
    """What kind of text slide this is: one ARGUMENT, a LIST of points, a NARRATIVE paragraph,
    or QUOTES. Each is composed differently (text_exhibit)."""
    from ..core.headline import words

    pts = [t.strip() for t in _plain_points(points) if t.strip()]
    if pts and all(t.startswith(QUOTE_MARKS) for t in pts):
        return "quote"
    if len(pts) == 1:
        return "narrative" if len(words(pts[0])) > 40 else "argument"
    return "list"


def _lead_in(t: str) -> str:
    """'Risk: mitigation' → '**Risk:** mitigation' (a bold lead-in when the point has one)."""
    i = t.find(":")
    if 0 < i <= 60 and "**" not in t:
        return f"**{t[: i + 1]}**{t[i + 1:]}"
    return t


def text_exhibit(p: Painter, box: Box, data: dict, so_what: dict | None = None) -> str:
    """A text slide composed for what it is (v1.4). Text used to be drawn as a side-commentary
    box: small type stuck under the headline on an empty slide. Now
      argument   one claim: large type with an accent bar, on the optical centre
      list       2–7 points: numbered rows at a readable size, separated by hairlines, one block
      narrative  one paragraph: comfortable reading size and measure
      quote      quotations: large type with a rule, stacked
    The slide-level so-what (commentary) follows the block as a bold conclusion line."""
    pts = [t for t in _plain_points(data.get("points")) if t.strip()]
    form = text_form(pts)
    sw = " ".join(_plain_points((so_what or {}).get("points"))) if so_what else ""
    meas = min(box.w, 10.5 if form == "list" else 9.6)
    sw_size = min(16, body_cap(p, 99))

    def sw_h(w):
        return (p.measure(sw, "body_strong", w - 0.25, size=sw_size)[0] + 0.45) if sw else 0.0

    if form in ("argument", "narrative"):
        cap = body_cap(p, 99)
        sizes = (28, 26, 24, 22, 20) if form == "argument" else tuple(x for x in (20, 18, 17, 16, 15, 14, 13, 12) if x <= cap)
        role = "headline" if form == "argument" else "body"
        txt = pts[0] if pts else ""
        for ts in sizes:
            th, lines = p.measure(txt, role, meas, size=ts, bold=False)
            block = 0.27 + th + sw_h(meas)
            if block <= box.h * 0.8 and (form == "narrative" or lines <= 3):
                break
        top = optical_top(box, block)
        p.rect(Box(box.x, top, 0.9, 0.07), fill="highlight")
        p.text(Box(box.x, top + 0.27, meas, th + 0.15), txt, role=role, size=ts, bold=False, color="primary" if form == "argument" else "text", record="text argument")
        y = top + 0.27 + th + 0.15
    elif form == "quote":
        # short quotations carry the slide like a statement (classified as one): large type
        for ts in (24, 22, 20, 18, 16, 14, 12):
            hs = [p.measure(t, "body", meas - 0.35, size=ts)[0] for t in pts]
            block = sum(hs) + 0.4 * (len(pts) - 1) + sw_h(meas)
            if block <= box.h * 0.8:
                break
        y = optical_top(box, block)
        for t, h in zip(pts, hs):
            p.rect(Box(box.x, y + 0.04, 0.06, h - 0.04), fill="highlight")
            p.text(Box(box.x + 0.35, y, meas - 0.35, h + 0.1), t, role="body", size=ts, color="primary", record="text quote")
            y += h + 0.4
        y -= 0.4
    else:
        lab_w = 0.6
        avail = box.h * 0.86 - sw_h(meas)
        for ts in tuple(x for x in (22, 20, 18, 17, 16, 15, 14, 13, 12, 11) if x <= body_cap(p, 99)):
            hs = [p.measure(_lead_in(t), "body", meas - lab_w, size=ts)[0] for t in pts]
            if sum(hs) + 2 * 0.08 * len(pts) <= avail:
                break
        # the rows breathe with what is left, within bounds: type size wins over padding
        pad = max(0.08, min(0.18 + 0.012 * ts, (avail - sum(hs)) / (2 * len(pts))))
        block = sum(h + 2 * pad for h in hs) + sw_h(meas)
        y = optical_top(box, block)
        p.line(box.x, y, box.x + meas, y, color="rule", width=LINES["rule"])
        for i, (t, h) in enumerate(zip(pts, hs)):
            row = Box(box.x, y, meas, h + 2 * pad)
            p.text(Box(row.x, row.y + pad, lab_w - 0.1, h), f"{i + 1}", role="section", size=ts, color="highlight", record="text number")
            p.text(Box(row.x + lab_w, row.y + pad, meas - lab_w, h + 0.05), _lead_in(t), role="body", size=ts, record=f"text point {i + 1}")
            y = row.b
            p.line(box.x, y, box.x + meas, y, color="gridline", width=LINES["hairline"])
    if sw:
        y += 0.3
        h = p.measure(sw, "body_strong", meas - 0.25, size=sw_size)[0]
        p.rect(Box(box.x, y, 0.06, h + 0.04), fill="highlight")
        p.text(Box(box.x + 0.25, y, meas - 0.25, h + 0.1), sw, role="body_strong", size=sw_size, color="primary", record="text so-what")
    return form


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
