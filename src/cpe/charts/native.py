"""Native, data-editable PowerPoint charts styled for executive communication.

Principles implemented here (not left to the user):
  * no chart junk: no gridlines, no value axis when bars carry labels, no tick
    marks, no legend when series can be labelled directly;
  * one focus: highlighted categories / the focus series use the primary
    colour, context uses muted greys;
  * explicit, rounded scales (so overlays can be placed exactly);
  * deterministic plot area (manualLayout, layoutTarget=inner) so annotation
    overlays (CAGR arrows, totals, end-of-line labels, reference lines,
    forecast shading, waterfall connectors) land on the data;
  * the data lives in the embedded workbook — the chart stays editable.
"""
from __future__ import annotations

import math

from lxml import etree
from pptx.chart.data import BubbleChartData, CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.oxml.ns import qn
from pptx.util import Pt

from ..design import text_metrics as tm
from ..design.tokens import LINES, best_text_on
from ..layout.engine import Box
from ..pptx.painter import E, Painter, rgb
from ..pptx.text_components import exhibit_header, legend
from .numfmt import cagr, excel_code, fmt, fmt_spec, nice_scale

C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------
def _c(tag: str) -> str:
    return qn(f"c:{tag}")


def set_plot_layout(chart, fx: float, fy: float, fw: float, fh: float) -> None:
    plot_area = chart._chartSpace.find(_c("chart")).find(_c("plotArea"))
    old = plot_area.find(_c("layout"))
    if old is not None:
        plot_area.remove(old)
    layout = etree.Element(_c("layout"))
    ml = etree.SubElement(layout, _c("manualLayout"))
    for tag, val in (("layoutTarget", "inner"), ("xMode", "edge"), ("yMode", "edge"), ("x", fx), ("y", fy), ("w", fw), ("h", fh)):
        etree.SubElement(ml, _c(tag), {"val": str(round(val, 5)) if isinstance(val, float) else val})
    plot_area.insert(0, layout)


def _no_fill_chart_bg(chart) -> None:
    """Transparent chart/plot area, square corners, and no automatic title
    (PowerPoint and LibreOffice auto-title single-series charts)."""
    chart.has_title = False
    ch = chart._chartSpace.find(_c("chart"))
    atd = ch.find(_c("autoTitleDeleted"))
    if atd is None:
        atd = etree.Element(_c("autoTitleDeleted"))
        title = ch.find(_c("title"))
        (title.addnext(atd) if title is not None else ch.insert(0, atd))
    atd.set("val", "1")
    cs = chart._chartSpace
    # chart space + plot area without borders/fills
    for parent in (cs, cs.find(_c("chart")).find(_c("plotArea"))):
        sp = parent.find(_c("spPr"))
        if sp is None:
            sp = etree.SubElement(parent, _c("spPr"))
            if parent is cs:  # spPr must come before txPr in chartSpace
                tx = cs.find(_c("txPr"))
                if tx is not None:
                    cs.remove(sp)
                    tx.addprevious(sp)
        for ch in list(sp):
            sp.remove(ch)
        etree.SubElement(sp, qn("a:noFill"))
        ln = etree.SubElement(sp, qn("a:ln"))
        etree.SubElement(ln, qn("a:noFill"))
    rc = cs.find(_c("roundedCorners"))
    if rc is None:
        rc = etree.Element(_c("roundedCorners"))
        cs.insert(0, rc)
    rc.set("val", "0")


def _style_axis_line(axis, color: str | None, width: float = LINES["rule"]) -> None:
    if color is None:
        axis.format.line.fill.background()
    else:
        axis.format.line.color.rgb = rgb(color)
        axis.format.line.width = Pt(width)


def _font(obj, p: Painter, role: str, color: str | None = None, bold: bool | None = None, size: float | None = None):
    st = p.style(role)
    f = obj.font
    f.name = p.theme.font_latin
    f.size = Pt(size or st["size"])
    f.bold = st["bold"] if bold is None else bold
    f.color.rgb = rgb(p.color(color or st["color"]))


def _series_labels(series, p: Painter, code: str, pos, color: str | None = None, bold: bool = False, size: float | None = None) -> None:
    dl = series.data_labels
    dl.show_value = True
    dl.number_format = code
    dl.number_format_is_linked = False
    if pos is not None:
        dl.position = pos
    _font(dl, p, "chart", color=color, bold=bold, size=size)


def _hide_series_labels(series) -> None:
    ser = series._element
    dl = ser.find(_c("dLbls"))
    if dl is not None:
        ser.remove(dl)


def _fill(target, color_hex: str | None) -> None:
    if color_hex is None:
        target.format.fill.background()
    else:
        target.format.fill.solid()
        target.format.fill.fore_color.rgb = rgb(color_hex)


def _gap_overlap(plot, gap: int, overlap: int | None = None) -> None:
    plot.gap_width = gap
    if overlap is not None:
        plot.overlap = overlap


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
class PlotGeom:
    """Maps data space to slide inches for overlays."""

    def __init__(self, frame: Box, fx, fy, fw, fh, lo, hi, n, horizontal=False, gap=0.6, nseries=1, overlap=False):
        self.frame = frame
        self.inner = Box(frame.x + fx * frame.w, frame.y + fy * frame.h, fw * frame.w, fh * frame.h)
        self.lo, self.hi, self.n = lo, hi, n
        self.horizontal = horizontal
        self.gap = gap
        self.nseries = nseries
        self.overlap = overlap

    def v(self, value: float) -> float:
        t = (value - self.lo) / (self.hi - self.lo) if self.hi != self.lo else 0
        if self.horizontal:
            return self.inner.x + t * self.inner.w
        return self.inner.b - t * self.inner.h

    def slot(self) -> float:
        return (self.inner.h if self.horizontal else self.inner.w) / max(1, self.n)

    def c(self, i: int) -> float:
        base = self.inner.y if self.horizontal else self.inner.x
        return base + (i + 0.5) * self.slot()

    def bar_w(self) -> float:
        k = 1 if self.overlap else self.nseries
        return self.slot() / (k + self.gap)

    def series_c(self, i: int, s: int) -> float:
        if self.overlap or self.nseries == 1:
            return self.c(i)
        bw = self.bar_w()
        start = self.c(i) - bw * self.nseries / 2
        return start + (s + 0.5) * bw


def _cat_label_height(p: Painter, cats: list[str], slot_w: float) -> tuple[float, int]:
    st = p.style("chart_axis")
    lines = max((len(tm.wrap_lines(str(c), max(0.2, slot_w - 0.06), st["size"])) for c in cats), default=1)
    return lines * tm.line_height_in(st["size"]) + 0.12, lines


# ---------------------------------------------------------------------------
# Category charts
# ---------------------------------------------------------------------------
CATEGORY_TYPES = {
    ("column", False): XL_CHART_TYPE.COLUMN_CLUSTERED,
    ("bar", False): XL_CHART_TYPE.BAR_CLUSTERED,
    ("stacked_column", False): XL_CHART_TYPE.COLUMN_STACKED,
    ("stacked_bar", False): XL_CHART_TYPE.BAR_STACKED,
    ("stacked_100", False): XL_CHART_TYPE.COLUMN_STACKED_100,
    ("stacked_100", True): XL_CHART_TYPE.BAR_STACKED_100,
    ("line", False): XL_CHART_TYPE.LINE,
    ("slope", False): XL_CHART_TYPE.LINE,
    ("area", False): XL_CHART_TYPE.AREA_STACKED,
    ("histogram", False): XL_CHART_TYPE.COLUMN_CLUSTERED,
}


def _prepare_categories(ex: dict) -> tuple[list[str], list[dict]]:
    data = ex["data"]
    cats = [str(c) for c in data["categories"]]
    series = [dict(s) for s in data["series"]]
    for s in series:
        s["values"] = [None if v is None else float(v) for v in s["values"]]
        if len(s["values"]) != len(cats):
            raise ValueError(f"Series '{s.get('name')}' has {len(s['values'])} values for {len(cats)} categories")
    sort = ex.get("sort")
    if sort in ("asc", "desc") and len(series) >= 1:
        key_vals = [sum((s["values"][i] or 0) for s in series) for i in range(len(cats))]
        order = sorted(range(len(cats)), key=lambda i: key_vals[i], reverse=(sort == "desc"))
        cats = [cats[i] for i in order]
        for s in series:
            s["values"] = [s["values"][i] for i in order]
    return cats, series


def _highlight_idx(ex: dict, cats: list[str]) -> set[int]:
    out = set()
    for h in ex.get("highlight") or []:
        if isinstance(h, int) and 0 <= h < len(cats):
            out.add(h)
        elif str(h) in cats:
            out.add(cats.index(str(h)))
    return out


def category_chart(p: Painter, box: Box, ex: dict) -> dict:
    vt = ex["type"]
    horizontal = vt in ("bar", "stacked_bar") or (vt == "stacked_100" and ex.get("orientation") == "horizontal")
    plot_box = exhibit_header(p, box, ex)
    cats, series = _prepare_categories(ex)
    f = fmt_spec(ex)
    n = len(cats)
    stacked = vt in ("stacked_column", "stacked_bar", "stacked_100", "area")
    is_line = vt in ("line", "slope")
    pct100 = vt == "stacked_100"
    theme = p.theme
    ex = {**ex, "annotations": list(ex.get("annotations") or []) + _auto_proof(ex, cats, series, stacked, is_line, pct100)}

    # --- scale ---------------------------------------------------------
    if pct100:
        lo, hi, step = 0.0, 1.0, 0.25
    else:
        if stacked:
            tops = [sum(max(0, s["values"][i] or 0) for s in series) for i in range(n)]
            bots = [sum(min(0, s["values"][i] or 0) for s in series) for i in range(n)]
            vmin, vmax = min(bots), max(tops)
        else:
            allv = [v for s in series for v in s["values"] if v is not None]
            vmin, vmax = min(allv), max(allv)
        for a in ex.get("annotations") or []:
            if a.get("type") == "reference" and isinstance(a.get("value"), (int, float)):
                vmax, vmin = max(vmax, a["value"]), min(vmin, a["value"])
        include_zero = not is_line or ex.get("zero_baseline", vmin >= 0 and vmin < 0.5 * vmax)
        lo, hi, step = nice_scale(vmin, vmax, 5, include_zero=include_zero or not is_line)
        if is_line and not include_zero:
            lo, hi, step = nice_scale(vmin, vmax, 5, include_zero=False)
        # headroom for labels / annotations
        if not is_line and not horizontal:
            # headroom in real inches: value/total labels (+ CAGR arrow) above the tallest bar
            need = 0.3 + (0.4 if any(a.get("type") == "cagr" for a in ex.get("annotations") or []) else 0.0)
            inner_h = max(1.0, plot_box.h - 0.45 - (0.34 if len(series) > 1 and not stacked else 0))
            top = vmax + (vmax - lo) * need / max(0.3, inner_h - need)
            hi = lo + math.ceil((top - lo) / step * 4) / 4 * step
        elif horizontal:
            hi = hi + step * 0.6
        elif is_line and any(a.get("type") == "cagr" for a in ex.get("annotations") or []):
            hi = hi + step * 1.0
        if is_line:  # room for value labels above/below the points
            hi = hi + step * 0.5
            if lo < vmin - 1e-9 or lo != 0:
                lo = lo - step * 0.5 if lo - step * 0.5 >= 0 or vmin < 0 else lo
    # --- geometry (fractions of the frame) --------------------------------
    right_pad = ex.get("_right_pad", 0.02)
    end_labels = (is_line and len(series) > 1 and ex.get("direct_labels", True)) or (stacked and not horizontal and ex.get("direct_labels", True) and len(series) > 1)
    if end_labels:
        maxw = max(p.text_w(s["name"], "chart", bold=True) for s in series) + 0.25
        if is_line:
            maxw += p.text_w(fmt(max(v for s in series for v in s["values"] if v is not None), f), "chart") + 0.1
        right_pad = max(right_pad, min(0.35, maxw / plot_box.w)) if "_right_pad" not in ex else right_pad
    legend_h = 0.0
    if len(series) > 1 and not end_labels and not horizontal:
        legend_h = 0.34
    elif len(series) > 1 and horizontal:
        legend_h = 0.34
    fy_top = (legend_h + 0.05) / plot_box.h
    if horizontal:
        cat_w = min(plot_box.w * 0.38, max(p.text_w(c, "chart_axis") for c in cats) + 0.2)
        fx = cat_w / plot_box.w
        fw = 1 - fx - right_pad - 0.04
        fh = 1 - fy_top - 0.02
        geom = PlotGeom(plot_box, fx, fy_top, fw, fh, lo, hi, n, horizontal=True, gap=ex.get("gap", 55) / 100, nseries=len(series), overlap=stacked)
    else:
        slot_w = plot_box.w * (1 - right_pad - 0.02) / n
        cat_h, _ = _cat_label_height(p, cats, slot_w)
        if ex.get("_hide_cat_axis"):
            cat_h = 0.08
        fh = 1 - fy_top - cat_h / plot_box.h
        fx = 0.01 if not ex.get("show_value_axis") else 0.08
        fw = 1 - fx - right_pad
        gap = ex.get("gap", 8 if vt == "histogram" else 60)
        geom = PlotGeom(plot_box, fx, fy_top, fw, fh, lo, hi, n, horizontal=False, gap=gap / 100, nseries=len(series), overlap=stacked)

    # --- background overlays (drawn before the chart = behind it) -------
    pb = p.for_zone(p.zone)
    for a in ex.get("annotations") or []:
        if a.get("type") == "forecast" and not horizontal:
            idx = cats.index(str(a["from"])) if str(a.get("from")) in cats else int(a.get("from", n - 1))
            x0 = geom.c(idx) - geom.slot() / 2
            pb.rect(Box(x0, geom.inner.y - 0.05, geom.inner.r - x0, geom.inner.h + 0.05), fill="faint", kind="fill")
            pb.text(Box(x0 + 0.05, geom.inner.y - 0.02, geom.inner.r - x0 - 0.1, 0.26), a.get("label", "Forecast"), role="chart_axis", align="left", fit=False, kind="label")

    # --- the native chart ------------------------------------------------
    cd = CategoryChartData()
    cd.categories = cats
    for s in series:
        vals = s["values"]
        if pct100:
            pass
        cd.add_series(s["name"], vals)
    ctype = CATEGORY_TYPES.get((vt, horizontal)) or CATEGORY_TYPES[(vt, False)]
    gf = p.slide.shapes.add_chart(ctype, E(plot_box.x), E(plot_box.y), E(plot_box.w), E(plot_box.h), cd)
    gf.name = p._name("chart")
    chart = gf.chart
    chart.has_legend = False
    chart.font.name = theme.font_latin
    chart.font.size = Pt(p.style("chart")["size"])
    _no_fill_chart_bg(chart)
    set_plot_layout(chart, geom.inner.x and (geom.inner.x - plot_box.x) / plot_box.w, (geom.inner.y - plot_box.y) / plot_box.h, geom.inner.w / plot_box.w, geom.inner.h / plot_box.h)
    plot = chart.plots[0]
    if not is_line and vt != "area":
        _gap_overlap(plot, int(geom.gap * 100), 100 if stacked else (-10 if len(series) > 1 else 0))
    va, ca = chart.value_axis, chart.category_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = lo, hi, step
    va.has_major_gridlines = False
    va.has_minor_gridlines = False
    va.major_tick_mark = XL_TICK_MARK.NONE
    va.minor_tick_mark = XL_TICK_MARK.NONE
    show_va = bool(ex.get("show_value_axis")) or (is_line and ex.get("labels", "ends") == "none")
    va.visible = show_va
    if show_va:
        _font(va.tick_labels, p, "chart_axis")
        va.tick_labels.number_format = excel_code(f) if not pct100 else "0%"
        va.tick_labels.number_format_is_linked = False
        _style_axis_line(va, None)
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = rgb(theme.c("gridline"))
        va.major_gridlines.format.line.width = Pt(LINES["hairline"])
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.minor_tick_mark = XL_TICK_MARK.NONE
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    _font(ca.tick_labels, p, "chart_axis", color="text")
    _style_axis_line(ca, theme.c("rule"))
    if ex.get("_hide_cat_axis"):
        ca.visible = False
    if horizontal:
        ca.reverse_order = True  # first category on top
    hl = _highlight_idx(ex, cats)
    hl_series = {str(h) for h in ex.get("highlight") or []} & {s["name"] for s in series}
    if hl_series:  # series-level focus: everything else goes to context grey
        for s_ in series:
            if s_["name"] not in hl_series and not s_.get("color"):
                s_["role"] = "context"
            elif s_["name"] in hl_series and len(series) > 1 and not s_.get("role"):
                s_["role"] = "focus" if is_line else None
    palette = theme.series
    label_mode = ex.get("labels", "all" if not is_line else "ends")
    code = excel_code({**f, "suffix": f.get("suffix") or ("%" if pct100 and not f.get("percent") else "")})

    for si, (s, ser) in enumerate(zip(series, plot.series)):
        role = s.get("role")
        if is_line:
            focus = role == "focus" or (role is None and si == 0)
            col = theme.c(s.get("color") or ("primary" if focus else ("muted" if role == "context" else palette[min(si, len(palette) - 1)] if len(series) <= 3 else "neutral")))
            ser.format.line.color.rgb = rgb(col)
            ser.format.line.width = Pt(2.5 if focus else 1.75)
            ser.smooth = False
            ser.marker.style = 8 if vt == "slope" else None  # circle for slope
            if vt != "slope":
                from pptx.enum.chart import XL_MARKER_STYLE

                ser.marker.style = XL_MARKER_STYLE.NONE
            else:
                ser.marker.size = 7
                ser.marker.format.fill.solid()
                ser.marker.format.fill.fore_color.rgb = rgb(col)
                ser.marker.format.line.color.rgb = rgb(col)
            s["_color"] = col
            continue
        if stacked:
            col = theme.c(s.get("color") or palette[si % len(palette)])
            if role == "context":
                ctx = [c for c in ("muted", "gridline", "rule", "faint")]
                k = sum(1 for x in series[:si] if x.get("role") == "context")
                col = theme.c(ctx[k % len(ctx)])
            _fill(ser, col)
            ser.format.line.color.rgb = rgb("FFFFFF")
            ser.format.line.width = Pt(0.75)
            s["_color"] = col
            if label_mode != "none":
                _series_labels(ser, p, code, XL_LABEL_POSITION.CENTER, color=best_text_on(col, theme), size=p.style("chart")["size"] - 0.5)
            continue
        # clustered bar / column
        if len(series) == 1:
            if not hl and ex.get("focus", "auto") != "none" and not s.get("color") and n > 2:
                # one focus by default: the latest period on a time axis, the leader in a ranking
                from ..core.visual_reasoning import data_shape

                time_axis = data_shape({"data": {"categories": cats, "series": series}}).get("time_axis")
                vals = [v if v is not None else float("-inf") for v in s["values"]]
                hl = {n - 1} if time_axis else {max(range(n), key=lambda i: vals[i])}
                s["_context"] = theme.series[2] if time_axis else theme.c("muted")
            base = theme.c(s.get("color") or (s.get("_context") or "muted" if hl else "primary"))
            _fill(ser, base)
            ser.invert_if_negative = False
            for i in range(n):
                if i in hl:
                    _fill(ser.points[i], theme.c(ex.get("highlight_color", "primary")))
                elif (s["values"][i] or 0) < 0 and ex.get("color_negative", True):
                    _fill(ser.points[i], theme.c("negative"))
            s["_color"] = base
        else:
            col = theme.c(s.get("color") or ("muted" if role == "context" else palette[si % len(palette)]))
            _fill(ser, col)
            ser.invert_if_negative = False
            s["_color"] = col
        if label_mode != "none":
            _series_labels(ser, p, code, XL_LABEL_POSITION.OUTSIDE_END, color="text", size=p.style("chart")["size"])

    # --- foreground overlays --------------------------------------------
    po = p
    # stacked totals
    if stacked and not pct100 and ex.get("totals", True) and not horizontal and vt != "area":
        for i in range(n):
            tot = sum(s["values"][i] or 0 for s in series)
            y = geom.v(tot)
            po.text(Box(geom.c(i) - geom.slot() / 2, y - 0.3, geom.slot(), 0.26), fmt(tot, f), role="chart", bold=True, align="center", anchor="bottom", fit=False, kind="label")
    elif stacked and not pct100 and ex.get("totals", True) and horizontal:
        for i in range(n):
            tot = sum(s["values"][i] or 0 for s in series)
            x = geom.v(tot)
            po.text(Box(x + 0.06, geom.c(i) - 0.13, 0.9, 0.26), fmt(tot, f), role="chart", bold=True, anchor="middle", fit=False, kind="label")
    # direct series labels at the right end
    if end_labels:
        placed = []
        last = n - 1
        for s in series:
            if is_line:
                v = s["values"][last]
                if v is None:
                    continue
                yc = geom.v(v)
                label = f"**{s['name']}** {fmt(v, f)}" if label_mode in ("ends", "last") else f"**{s['name']}**"
            else:
                idx = series.index(s)
                below = sum(series[k]["values"][last] or 0 for k in range(idx))
                v = s["values"][last] or 0
                if pct100:
                    tot = sum(x["values"][last] or 0 for x in series) or 1
                    yc = geom.v((below + v / 2) / tot)
                else:
                    yc = geom.v(below + v / 2)
                label = s["name"]
            placed.append([yc, label, s.get("_color", theme.c("text"))])
        placed.sort(key=lambda t: t[0])
        min_gap = 0.24
        for k in range(1, len(placed)):  # de-collide vertically
            if placed[k][0] - placed[k - 1][0] < min_gap:
                placed[k][0] = placed[k - 1][0] + min_gap
        x0 = geom.c(last) + (geom.bar_w() / 2 if not is_line else 0) + 0.1
        w = plot_box.r - x0
        for yc, label, colr in placed:
            po.text(Box(x0, yc - 0.13, max(0.3, w), 0.26), label, role="chart", color=_readable(colr, theme) if is_line else "text", anchor="middle", fit=False, kind="label", max_lines=1)
    # line value labels (start / all) with vertical de-collision per category
    if is_line and label_mode in ("ends", "all"):
        labelled = [s for s in series if s.get("role") == "focus" or series.index(s) == 0 or label_mode == "all"]
        idxs = list(range(n)) if label_mode == "all" else [0] + ([n - 1] if not end_labels else [])
        for i in idxs:
            pts = sorted(((geom.v(s["values"][i]), s) for s in labelled if s["values"][i] is not None), key=lambda t: t[0])
            for k, (y, s) in enumerate(pts):
                v = s["values"][i]
                crowded_below = k + 1 < len(pts) and pts[k + 1][0] - y < 0.3
                crowded_above = k > 0 and y - pts[k - 1][0] < 0.3
                below = crowded_above and not crowded_below or (k == len(pts) - 1 and crowded_above)
                yb = y + 0.07 if below else y - 0.33
                po.text(Box(geom.c(i) - 0.5, yb, 1.0, 0.26), fmt(v, f), role="chart", align="center", anchor="top" if below else "bottom", fit=False, kind="label", color=_readable(s.get("_color"), theme), bold=s is labelled[0])
    # legend when needed
    if legend_h:
        legend(po, Box(plot_box.x + (geom.inner.x - plot_box.x), plot_box.y, plot_box.w, legend_h), [(s["name"], s.get("_color", theme.c("primary"))) for s in series])
    _annotations(po, geom, ex, cats, series, f, is_line, stacked)
    return {"type": vt, "categories": n, "series": len(series), "scale": [lo, hi, step]}


def _annotations(p: Painter, geom: PlotGeom, ex: dict, cats, series, f, is_line, stacked) -> None:
    for a in ex.get("annotations") or []:
        t = a.get("type")
        if t == "cagr":
            i0 = _idx(a.get("from", 0), cats)
            i1 = _idx(a.get("to", len(cats) - 1), cats)
            if stacked:
                v0 = sum(s["values"][i0] or 0 for s in series)
                v1 = sum(s["values"][i1] or 0 for s in series)
            else:
                s = series[a.get("series", 0)]
                v0, v1 = s["values"][i0], s["values"][i1]
            label = a.get("label")
            if not label:
                g = cagr(v0, v1, i1 - i0)
                label = f"CAGR {'+' if g >= 0 else '−'}{abs(g) * 100:.0f}%"
            if geom.horizontal:
                continue
            ytop = min(geom.v(max(v0, v1)), geom.v(v0), geom.v(v1)) - (0.42 if not is_line else 0.55)
            ytop = max(geom.inner.y + 0.12, ytop)
            x0, x1 = geom.c(i0), geom.c(i1)
            p.line(x0, ytop, x1, ytop, color="text", width=LINES["rule"], arrow_end=True, kind="connector")
            p.line(x0, ytop, x0, ytop + 0.1, color="text", width=LINES["rule"], kind="connector")
            lw = p.text_w(label, "annotation", bold=True) + 0.24
            xm = (x0 + x1) / 2
            p.text(Box(xm - lw / 2, ytop - 0.15, lw, 0.3), label, role="annotation", bold=True, align="center", anchor="middle", fill="background", fit=False, kind="label")
        elif t == "reference":
            v = a["value"]
            if geom.horizontal:
                x = geom.v(v)
                p.line(x, geom.inner.y, x, geom.inner.b, color="text_muted", width=LINES["rule"], dash=True, kind="connector")
                p.text(Box(x + 0.05, geom.inner.y - 0.3, 2.2, 0.26), a.get("label", fmt(v, f)), role="annotation", fit=False, kind="label", color="text_muted")
            else:
                y = geom.v(v)
                p.line(geom.inner.x, y, geom.inner.r, y, color="text_muted", width=LINES["rule"], dash=True, kind="connector")
                lab = a.get("label", fmt(v, f))
                lw = p.text_w(lab, "annotation") + 0.1
                p.text(Box(geom.inner.r - lw, y - 0.28, lw, 0.24), lab, role="annotation", align="right", fit=False, kind="label", color="text_muted")
        elif t == "callout":
            i = _idx(a.get("at", 0), cats)
            s = series[a.get("series", 0)]
            v = s["values"][i] or 0
            text = a["text"]
            w = min(2.4, max(1.2, p.text_w(text, "annotation") / 2 + 0.3))
            h, _ = p.measure(text, "annotation", w)
            if geom.horizontal:
                x = geom.v(v) + 0.7
                y = geom.c(i) - h / 2
            else:
                x = geom.c(i) - w / 2
                y = geom.v(v) - h - 0.45
                y = max(geom.inner.y, y)
                x = min(max(x, geom.frame.x), geom.frame.r - w)
            p.text(Box(x, y, w, h + 0.06), text, role="annotation", fill="background", fit=True, kind="label", record="callout")


def _auto_proof(ex: dict, cats: list, series: list, stacked: bool, is_line: bool, pct100: bool) -> list[dict]:
    """If the headline quotes the first→last change (or CAGR) of the exhibit, draw it:
    the proof of the headline must be visible on the slide, not only in the title."""
    from ..core.headline import numbers_in

    head = ex.get("_headline") or ""
    if pct100 or ex.get("auto_proof") is False or not head or len(cats) < 2 or any(a.get("type") == "cagr" for a in ex.get("annotations") or []):
        return []
    pcts = [v for v, u in numbers_in(head) if u == "%"]
    if not pcts:
        return []
    if stacked:
        vals = [sum(s_["values"][i] or 0 for s_ in series) for i in range(len(cats))]
    else:
        focus = next((s_ for s_ in series if s_.get("role") == "focus"), series[0])
        vals = focus["values"]
    v0, v1 = vals[0], vals[-1]
    if not v0 or v0 <= 0 or v1 is None or v1 <= 0:
        return []
    change = (v1 / v0 - 1) * 100
    g = cagr(v0, v1, len(cats) - 1) * 100

    def label(v, prefix=""):
        txt = f"{v:g}"
        if txt.replace(".", ",") in head and "." in txt:
            txt = txt.replace(".", ",")
        return f"{prefix}{'+' if change >= 0 else '−'}{txt}%"

    last = (vals[-1] / vals[-2] - 1) * 100 if len(vals) > 2 and vals[-2] and vals[-2] > 0 else None
    for v in pcts:
        if last is not None and abs(abs(last) - v) <= 0.06 and abs(abs(change) - v) > 0.6:
            return [{"type": "cagr", "from": len(cats) - 2, "to": len(cats) - 1, "label": label(v).replace("+" if change >= 0 else "−", "+" if last >= 0 else "−", 1), "series": series.index(focus) if not stacked else 0}]
        if abs(abs(change) - v) <= 0.6:
            return [{"type": "cagr", "from": 0, "to": len(cats) - 1, "label": label(v), "series": series.index(focus) if not stacked else 0}]
        if len(cats) > 2 and abs(abs(g) - v) <= 0.3:
            return [{"type": "cagr", "from": 0, "to": len(cats) - 1, "label": label(v, "CAGR "), "series": series.index(focus) if not stacked else 0}]
    return []


def _readable(color: str | None, theme, bg: str = "FFFFFF") -> str:
    """Series colour for a text label only if it is legible on white; else muted text."""
    from ..design.tokens import contrast_ratio

    if not color:
        return theme.c("text")
    return color if contrast_ratio(color, bg) >= 4.5 else theme.c("text_muted")


def _idx(v, cats) -> int:
    if isinstance(v, int):
        return v
    return cats.index(str(v))


# ---------------------------------------------------------------------------
# Waterfall / bridge (stacked column with invisible base — fully native)
# ---------------------------------------------------------------------------
def waterfall(p: Painter, box: Box, ex: dict) -> dict:
    plot_box = exhibit_header(p, box, ex)
    steps = ex["data"]["steps"]
    f = fmt_spec(ex)
    theme = p.theme
    labels, base, up, down, tot, kinds, running = [], [], [], [], [], [], 0.0
    ends = []
    for st in steps:
        k = st.get("type", "delta")
        labels.append(str(st["label"]))
        if k in ("total", "subtotal"):
            v = float(st["value"]) if st.get("value") is not None else running
            running = v
            base.append(0.0)
            up.append(0.0)
            down.append(0.0)
            tot.append(v)
            kinds.append("total")
            ends.append(v)
        else:
            v = float(st["value"])
            start = running
            running = start + v
            lo_ = min(start, running)
            base.append(lo_)
            up.append(v if v > 0 else 0.0)
            down.append(-v if v < 0 else 0.0)
            tot.append(0.0)
            kinds.append("up" if v >= 0 else "down")
            ends.append(running)
    if min(base) < 0 or min(ends) < 0:
        p.warn("WATERFALL_NEGATIVE", "Running total crosses zero; waterfall base rendering assumes positive totals.")
    n = len(labels)
    vmax = max(max(b + u + d + t for b, u, d, t in zip(base, up, down, tot)), 0)
    lo = 0.0
    totals = [t for t in tot if t]
    deltas = [u + d for u, d, k in zip(up, down, kinds) if k != "total"]
    trunc = ex.get("truncate_axis")
    if trunc is None:  # auto: deltas would be slivers next to the totals
        trunc = bool(totals) and min(totals) > 0 and bool(deltas) and max(deltas) < 0.12 * max(totals)
    if trunc:
        lows = [b for b, k in zip(base, kinds) if k != "total"]
        rng = vmax - min(lows)
        _, _, st = nice_scale(0, rng, 4)
        lo = max(0.0, (min(lows) - 0.6 * rng) // st * st)
    _, hi, step = nice_scale(lo, vmax, 5, include_zero=True)
    if lo:
        step = nice_scale(0, vmax - lo, 5)[2]
        hi = lo + math.ceil((vmax - lo) / step) * step
    # proof: the headline quotes the total change → print it above the end total
    from ..core.headline import numbers_in

    first_total = next((t for t, k in zip(tot, kinds) if k == "total"), None)
    wf_delta = (ends[-1] - first_total) if first_total is not None and kinds[-1] == "total" else None
    proof = wf_delta is not None and any(abs(abs(wf_delta) - v) <= max(0.51, 0.01 * v) and abs(v - abs(ends[-1])) > 0.5 for v, _ in numbers_in(ex.get("_headline") or ""))
    hi += step * (0.4 if not proof else 1.0)
    slot_w = plot_box.w / n
    cat_h, _ = _cat_label_height(p, labels, slot_w)
    fy = 0.02
    fh = 1 - fy - cat_h / plot_box.h
    geom = PlotGeom(plot_box, 0.0, fy, 1.0, fh, lo, hi, n, gap=ex.get("gap", 45) / 100)

    cd = CategoryChartData()
    cd.categories = labels
    b_adj = [max(0.0, b - lo) if lo else b for b in base]
    t_adj = [t - lo if (t and lo) else t for t in tot]
    cd.add_series("Base", b_adj)
    cd.add_series("Total", t_adj)
    cd.add_series("Increase", up)
    cd.add_series("Decrease", down)
    gf = p.slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, E(plot_box.x), E(plot_box.y), E(plot_box.w), E(plot_box.h), cd)
    gf.name = p._name("chart")
    chart = gf.chart
    chart.has_legend = False
    chart.font.name = theme.font_latin
    chart.font.size = Pt(p.style("chart")["size"])
    _no_fill_chart_bg(chart)
    set_plot_layout(chart, 0.0, fy, 1.0, fh)
    plot = chart.plots[0]
    _gap_overlap(plot, int(geom.gap * 100), 100)
    va, ca = chart.value_axis, chart.category_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 0, hi - lo, step
    va.visible = False
    va.has_major_gridlines = False
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    _font(ca.tick_labels, p, "chart_axis", color="text")
    _style_axis_line(ca, theme.c("rule"))
    s_base, s_tot, s_up, s_down = plot.series
    _fill(s_base, None)
    s_base.format.line.fill.background()
    col_total = theme.c(ex.get("total_color", "primary"))
    neutral_deltas = ex.get("delta_colors") == "neutral"
    _fill(s_tot, col_total)
    _fill(s_up, theme.c("secondary" if neutral_deltas else "positive"))
    _fill(s_down, theme.c("secondary" if neutral_deltas else "negative"))
    hl = _highlight_idx(ex, labels)
    for i in hl:
        for s in (s_up, s_down):
            _fill(s.points[i], theme.c("highlight"))
    # overlays: value labels + connectors
    run = []
    for i in range(n):
        top = (base[i] + up[i] + down[i]) if kinds[i] != "total" else tot[i]
        run.append(top)
        if kinds[i] == "total":
            val, plus = tot[i], False
        else:
            val = up[i] if kinds[i] == "up" else -down[i]
            plus = True
        label = fmt(val, f, plus=plus)
        y = geom.v(top)
        p.text(Box(geom.c(i) - geom.slot() / 2, y - 0.29, geom.slot(), 0.26), label, role="chart", bold=kinds[i] == "total", align="center", anchor="bottom", fit=False, kind="label")
    if proof:
        i = n - 1
        y = geom.v(tot[i])
        txt = f"{fmt(wf_delta, f, plus=True)} vs {labels[0]}"
        w = p.text_w(txt, "annotation", bold=True) + 0.1
        x = min(max(geom.c(i) - w / 2, plot_box.x), plot_box.r - w)  # stay inside the zone
        # sit above every value label the text spans horizontally
        covered = [k for k in range(n) if geom.c(k) + geom.slot() / 2 > x and geom.c(k) - geom.slot() / 2 < x + w]
        y = min(geom.v(run[k]) for k in covered) - 0.29
        y = max(plot_box.y + 0.26, y)
        p.text(Box(x, y - 0.27, w, 0.26), txt, role="annotation", bold=True, color="negative" if wf_delta < 0 else "positive",
               align="right" if x + w >= plot_box.r - 0.01 else "center", anchor="bottom", fit=False, kind="label")
    bw = geom.bar_w()
    for i in range(n - 1):
        level = ends[i]
        y = geom.v(level)
        p.line(geom.c(i) + bw / 2, y, geom.c(i + 1) - bw / 2, y, color="neutral", width=LINES["hairline"], kind="connector")
    if lo:  # truncated axis: draw a break on every total bar so the eye is not misled
        from pptx.enum.shapes import MSO_SHAPE

        yb = geom.inner.b - min(0.35, geom.inner.h * 0.08)
        for i in range(n):
            if kinds[i] == "total":
                p.shape(MSO_SHAPE.PARALLELOGRAM, Box(geom.c(i) - bw / 2 - 0.06, yb - 0.045, bw + 0.12, 0.09), fill="background", kind="marker")
    return {"type": "waterfall", "steps": n, "end": ends[-1], "axis_truncated": bool(lo)}


# ---------------------------------------------------------------------------
# Scatter / bubble (native XY charts + label overlays with de-collision)
# ---------------------------------------------------------------------------
def xy_chart(p: Painter, box: Box, ex: dict) -> dict:
    vt = ex["type"]
    plot_box = exhibit_header(p, box, ex)
    pts = ex["data"]["points"]
    theme = p.theme
    xs = [float(q["x"]) for q in pts]
    ys = [float(q["y"]) for q in pts]
    xlo, xhi, xstep = nice_scale(min(xs), max(xs), 5, include_zero=ex.get("x_zero", False))
    ylo, yhi, ystep = nice_scale(min(ys), max(ys), 5, include_zero=ex.get("y_zero", False))
    # pad so bubbles are not cut
    xpad, ypad = xstep * 0.3, ystep * 0.3
    xlo, xhi, ylo, yhi = xlo - (xpad if min(xs) - xlo < xpad else 0), xhi + (xpad if xhi - max(xs) < xpad else 0), ylo - (ypad if min(ys) - ylo < ypad else 0), yhi + (ypad if yhi - max(ys) < ypad else 0)
    ax_lab_h = 0.34
    fx, fy = 0.07, 0.04
    fw = 1 - fx - 0.02
    fh = 1 - fy - (0.3 + ax_lab_h) / plot_box.h
    inner = Box(plot_box.x + fx * plot_box.w, plot_box.y + fy * plot_box.h, fw * plot_box.w, fh * plot_box.h)

    if vt == "bubble":
        cd = BubbleChartData()
    else:
        cd = XyChartData()
    groups: dict[str, list] = {}
    for q in pts:
        groups.setdefault(q.get("group", "Items"), []).append(q)
    for gname, gpts in groups.items():
        s = cd.add_series(gname)
        for q in gpts:
            if vt == "bubble":
                s.add_data_point(float(q["x"]), float(q["y"]), float(q.get("size", 1)))
            else:
                s.add_data_point(float(q["x"]), float(q["y"]))
    ctype = XL_CHART_TYPE.BUBBLE if vt == "bubble" else XL_CHART_TYPE.XY_SCATTER
    gf = p.slide.shapes.add_chart(ctype, E(plot_box.x), E(plot_box.y), E(plot_box.w), E(plot_box.h), cd)
    gf.name = p._name("chart")
    chart = gf.chart
    chart.has_legend = False
    chart.font.name = theme.font_latin
    chart.font.size = Pt(p.style("chart_axis")["size"])
    _no_fill_chart_bg(chart)
    set_plot_layout(chart, fx, fy, fw, fh)
    va, ca = chart.value_axis, chart.category_axis
    for ax, lo, hi, step in ((ca, xlo, xhi, xstep), (va, ylo, yhi, ystep)):
        ax.minimum_scale, ax.maximum_scale, ax.major_unit = lo, hi, step
        ax.has_major_gridlines = False
        ax.major_tick_mark = XL_TICK_MARK.OUTSIDE
        ax.tick_label_position = XL_TICK_LABEL_POSITION.LOW
        _font(ax.tick_labels, p, "chart_axis")
        _style_axis_line(ax, theme.c("rule"))
        xf = ex.get("x_format") if ax is ca else ex.get("y_format")
        if xf:
            ax.tick_labels.number_format = excel_code({**{"decimals": 0}, **xf})
            ax.tick_labels.number_format_is_linked = False
    if vt == "bubble":
        bscale = ex.get("bubble_scale", 60)
        bc = chart._chartSpace.find(".//" + _c("bubbleChart"))
        el = bc.find(_c("bubbleScale"))
        if el is None:
            el = etree.SubElement(bc, _c("bubbleScale"))
            # schema order: bubbleScale must precede showNegBubbles/sizeRepresents/axId
            axid = bc.find(_c("axId"))
            bc.remove(el)
            axid.addprevious(el)
        el.set("val", str(bscale))
        sr = bc.find(_c("sizeRepresents"))
        if sr is None:
            sr = etree.Element(_c("sizeRepresents"))
            bc.find(_c("axId")).addprevious(sr)
        sr.set("val", "area")
    hl = set(ex.get("highlight") or [])
    for gi, (gname, ser) in enumerate(zip(groups, chart.plots[0].series)):
        gcol = theme.c(ex.get("group_colors", {}).get(gname) or (theme.series[gi % len(theme.series)] if len(groups) > 1 else "secondary"))
        if vt == "scatter":
            from pptx.enum.chart import XL_MARKER_STYLE

            ser.format.line.fill.background()
            ser.marker.style = XL_MARKER_STYLE.CIRCLE
            ser.marker.size = 9
            ser.marker.format.fill.solid()
            ser.marker.format.fill.fore_color.rgb = rgb(gcol)
            ser.marker.format.line.color.rgb = rgb("FFFFFF")
        else:
            _fill(ser, gcol)
            ser.format.line.color.rgb = rgb("FFFFFF")
        for k, q in enumerate(groups[gname]):
            if q.get("label") in hl:
                pt = ser.points[k]
                if vt == "scatter":
                    pt.marker.format.fill.solid()
                    pt.marker.format.fill.fore_color.rgb = rgb(theme.c("highlight"))
                else:
                    _fill(pt, theme.c("highlight"))
    # axis titles
    if ex.get("x_title"):
        p.text(Box(inner.x, plot_box.b - ax_lab_h, inner.w, ax_lab_h), ex["x_title"] + "  →", role="chart_axis", align="center", anchor="bottom", fit=False, kind="label")
    if ex.get("y_title"):
        p.text(Box(plot_box.x, plot_box.y - 0.02, 3.5, 0.26), "↑  " + ex["y_title"], role="chart_axis", fit=False, kind="label")

    def X(v):
        return inner.x + (v - xlo) / (xhi - xlo) * inner.w

    def Y(v):
        return inner.b - (v - ylo) / (yhi - ylo) * inner.h

    # reference lines (quadrant split)
    for q in ex.get("quadrants", {}).get("lines", []) if isinstance(ex.get("quadrants"), dict) else []:
        pass
    if ex.get("x_split") is not None:
        xv = X(float(ex["x_split"]))
        p.line(xv, inner.y, xv, inner.b, color="rule", width=LINES["hairline"], dash=True, kind="connector")
    if ex.get("y_split") is not None:
        yv = Y(float(ex["y_split"]))
        p.line(inner.x, yv, inner.r, yv, color="rule", width=LINES["hairline"], dash=True, kind="connector")
    # labels with greedy de-collision
    placed: list[Box] = []
    sizes = [float(q.get("size", 1)) for q in pts]
    smax = max(sizes) if sizes else 1
    for q in sorted(pts, key=lambda q: -float(q.get("size", 1))):
        if not q.get("label"):
            continue
        cx, cy = X(float(q["x"])), Y(float(q["y"]))
        r = 0.08
        if vt == "bubble":
            # bubble diameter in LibreOffice/PowerPoint ≈ bubbleScale% of 25% plot min-dim at max size (area)
            dmax = min(inner.w, inner.h) * 0.25 * (ex.get("bubble_scale", 60) / 100)
            r = dmax / 2 * math.sqrt(float(q.get("size", 1)) / smax)
        w = p.text_w(q["label"], "chart_axis", bold=q.get("label") in hl) + 0.08
        h = 0.24
        cands = [Box(cx + r + 0.03, cy - h / 2, w, h), Box(cx - r - 0.03 - w, cy - h / 2, w, h), Box(cx - w / 2, cy - r - h, w, h), Box(cx - w / 2, cy + r, w, h),
                 Box(cx + r * 0.7, cy - r * 0.7 - h, w, h), Box(cx + r * 0.7, cy + r * 0.7, w, h), Box(cx - r * 0.7 - w, cy - r * 0.7 - h, w, h), Box(cx - r * 0.7 - w, cy + r * 0.7, w, h)]
        choice = None
        for c in cands:
            if c.x < plot_box.x or c.r > plot_box.r or c.y < plot_box.y or c.b > inner.b:
                continue
            if all(c.intersection(o) < 1e-4 for o in placed):
                choice = c
                break
        if choice is None:
            choice = cands[0]
            p.warn("LABEL_COLLISION", f"Could not place label '{q['label']}' without overlap")
        placed.append(choice)
        p.text(choice, q["label"], role="chart_axis", color="text", bold=q.get("label") in hl, fit=False, kind="label", anchor="middle")
    if len(groups) > 1:
        legend(p, Box(inner.x + 0.1, plot_box.y, inner.w, 0.3), [(g, theme.c(ex.get("group_colors", {}).get(g) or theme.series[i % len(theme.series)])) for i, g in enumerate(groups)])
    return {"type": vt, "points": len(pts)}


# ---------------------------------------------------------------------------
# Pie / donut (only for ≤5 parts of a whole)
# ---------------------------------------------------------------------------
def pie_chart(p: Painter, box: Box, ex: dict) -> dict:
    plot_box = exhibit_header(p, box, ex)
    cats = [str(c) for c in ex["data"]["categories"]]
    vals = [float(v) for v in ex["data"]["series"][0]["values"]]
    if len(cats) > 6:
        p.warn("PIE_TOO_MANY", "Pie/donut with more than 6 slices is unreadable; use a bar chart")
    theme = p.theme
    d = min(plot_box.w * 0.55, plot_box.h)
    frame = Box(plot_box.x, plot_box.y + (plot_box.h - d) / 2, d, d)
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series(ex["data"]["series"][0].get("name", "Share"), vals)
    ct = XL_CHART_TYPE.DOUGHNUT if ex["type"] == "donut" else XL_CHART_TYPE.PIE
    gf = p.slide.shapes.add_chart(ct, E(frame.x), E(frame.y), E(frame.w), E(frame.h), cd)
    gf.name = p._name("chart")
    chart = gf.chart
    chart.has_legend = False
    _no_fill_chart_bg(chart)
    set_plot_layout(chart, 0.04, 0.04, 0.92, 0.92)
    ser = chart.plots[0].series[0]
    hl = _highlight_idx(ex, cats)
    cols = []
    hl_order = sorted(hl)
    ctx_cols = ["muted", "rule", "gridline", "faint"]
    for i in range(len(cats)):
        if not hl:
            col = theme.c(theme.series[i % len(theme.series)])
        elif i in hl:
            col = theme.c(["primary", "secondary", "highlight"][min(hl_order.index(i), 2)])
        else:
            col = theme.c(ctx_cols[(i - len([h for h in hl if h < i])) % len(ctx_cols)])
        _fill(ser.points[i], col)
        ser.points[i].format.line.color.rgb = rgb("FFFFFF")
        cols.append(col)
    if ex["type"] == "donut":
        dn = chart._chartSpace.find(".//" + _c("doughnutChart"))
        hs = dn.find(_c("holeSize"))
        if hs is None:
            hs = etree.SubElement(dn, _c("holeSize"))
        hs.set("val", "62")
    # legend-as-labels to the right, aligned list (no leader-line spaghetti)
    tot = sum(vals) or 1
    lx = frame.r + 0.35
    lw = plot_box.r - lx
    rowh = min(0.42, plot_box.h / max(1, len(cats)))
    y0 = plot_box.y + (plot_box.h - rowh * len(cats)) / 2
    f = fmt_spec(ex)
    for i, (c, v) in enumerate(zip(cats, vals)):
        y = y0 + i * rowh
        p.rect(Box(lx, y + rowh / 2 - 0.07, 0.14, 0.14), fill=cols[i], kind="marker")
        share = f"{v / tot * 100:.0f}%"
        p.text(Box(lx + 0.25, y, 0.7, rowh), share, role="chart", bold=True, anchor="middle", fit=False, kind="label")
        p.text(Box(lx + 0.95, y, lw - 0.95, rowh), c + (f"  ({fmt(v, f)})" if ex.get("show_values") else ""), role="chart", anchor="middle", max_lines=1, kind="label", record="pie label")
    from ..core.headline import numbers_in

    order = sorted(range(len(vals)), key=lambda i: -vals[i])
    acc = 0.0
    for k, i in enumerate(order[:-1], start=1):
        acc += vals[i] / tot * 100
        if k >= 2 and any(abs(acc - v) <= 0.6 for v, u in numbers_in(ex.get("_headline") or "") if u == "%"):
            yk = y0 + len(cats) * rowh + 0.05
            if yk + 0.3 <= plot_box.b:
                p.line(lx, yk, plot_box.r, yk, color="rule", width=LINES["hairline"])
                p.text(Box(lx + 0.25, yk + 0.02, lw - 0.25, 0.3), f"**Top {k}: {acc:.0f}%**", role="chart", anchor="middle", fit=False, kind="label")
            break
    return {"type": ex["type"], "slices": len(cats)}


# ---------------------------------------------------------------------------
# Combo: level (columns) + rates (lines) as two aligned native panels
# ---------------------------------------------------------------------------
def combo_chart(p: Painter, box: Box, ex: dict) -> dict:
    """Columns for the level (bottom panel) and lines for the rate series
    (`"axis": "secondary"`, top panel). Two native charts that share the
    category geometry: no dual axis to misread, both fully editable."""
    plot_box = exhibit_header(p, box, ex)
    cats, series = _prepare_categories({**ex, "sort": None})
    bars = [s for s in series if s.get("axis") != "secondary"]
    lines = [s for s in series if s.get("axis") == "secondary"]
    n = len(cats)
    fmt_spec({"format": ex.get("line_format"), "data": {"series": lines}})
    # shared horizontal geometry: right padding for the line end labels
    lab_w = max(p.text_w(s["name"], "chart", bold=True) for s in lines) + 0.2 if lines else 0.1
    right = min(0.3, lab_w / plot_box.w)
    ratio = ex.get("line_panel", 0.36)
    gap = 0.12
    top = Box(plot_box.x, plot_box.y, plot_box.w, plot_box.h * ratio)
    bottom = Box(plot_box.x, top.b + gap, plot_box.w, plot_box.h - top.h - gap)
    # bottom: columns (reuse the category chart with the same right padding)
    col_ex = {**ex, "type": "column", "title": None, "annotations": ex.get("annotations"), "data": {"categories": cats, "series": bars}, "_right_pad": right, "direct_labels": False}
    category_chart(p, bottom, col_ex)
    # top: lines
    line_ex = {**ex, "type": "line", "title": None, "format": ex.get("line_format"), "annotations": [], "labels": "all",
               "data": {"categories": cats, "series": lines}, "_right_pad": right, "_hide_cat_axis": True, "zero_baseline": False}
    category_chart(p, top, line_ex)
    # panel labels on the left edge (units)
    if ex.get("panel_labels"):
        lt, lb = ex["panel_labels"]
        p.text(Box(plot_box.x, top.y, 2.5, 0.24), lt, role="chart_axis", fit=False, kind="label")
        p.text(Box(plot_box.x, bottom.y, 2.5, 0.24), lb, role="chart_axis", fit=False, kind="label")
    return {"type": "combo", "categories": n}


def render(p: Painter, box: Box, ex: dict) -> dict:
    vt = ex["type"]
    if vt in ("waterfall", "bridge"):
        return waterfall(p, box, ex)
    if vt in ("scatter", "bubble"):
        return xy_chart(p, box, ex)
    if vt in ("pie", "donut"):
        return pie_chart(p, box, ex)
    if vt == "combo":
        return combo_chart(p, box, ex)
    return category_chart(p, box, ex)
