"""Painter: the only place that talks to python-pptx shape APIs.

Every visual component draws through a Painter bound to (slide, zone). The
painter
  * applies the design tokens (fonts, colours, line weights, zero corner radius),
  * strips python-pptx's default shape style (no theme shadows / outlines),
  * names every shape `cpe|<zone>|<kind>|<n>` so geometric QA knows which zone a
    shape belongs to and which overlaps are intentional,
  * fits text with real font metrics (shrinks towards the role floor, never
    below) and records every fitting decision in the build manifest.

Shape kinds: text, fill, line, connector, chart, table, marker, label.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from ..design import text_metrics as tm
from ..design.tokens import FONT_FLOOR, LINE_SPACING, LINES, PARA_SPACE_AFTER, Theme, type_style
from ..layout.engine import Box

ALIGN = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
ANCHOR = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
BOLD_RE = re.compile(r"(\*\*[^*]+\*\*)")


def E(inches: float) -> Emu:
    return Emu(int(round(inches * 914400)))


def rgb(hex6: str) -> RGBColor:
    return RGBColor.from_string(hex6.lstrip("#").upper())


def _strip_style(shape) -> None:
    """Remove <p:style> so no theme shadow/outline/fill leaks into shapes."""
    el = shape._element
    st = el.find(qn("p:style"))
    if st is not None:
        el.remove(st)


def plain(text: str) -> str:
    return BOLD_RE.sub(lambda m: m.group(0)[2:-2], text)


@dataclass
class Para:
    """A paragraph to paint. `text` may contain **bold** spans."""

    text: str
    bullet: str | None = None  # None | "•" | "–" | "1." ...
    level: int = 0
    bold: bool | None = None
    color: str | None = None
    size: float | None = None
    align: str | None = None
    space_after: float | None = None


@dataclass
class Manifest:
    """Per-slide record of zones, shapes and fitting decisions (for QA)."""

    slide_id: str
    layout: str
    zones: dict = field(default_factory=dict)
    fits: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    exhibits: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slide_id": self.slide_id,
            "layout": self.layout,
            "zones": self.zones,
            "fits": self.fits,
            "warnings": self.warnings,
            "exhibits": self.exhibits,
        }


class Painter:
    def __init__(self, slide, theme: Theme, profile: dict, manifest: Manifest, zone: str = "chrome"):
        self.slide = slide
        self.theme = theme
        self.profile = profile
        self.manifest = manifest
        self.zone = zone
        self._n = {"_": 0}

    # -- context -----------------------------------------------------------
    def for_zone(self, zone: str) -> "Painter":
        p = Painter(self.slide, self.theme, self.profile, self.manifest, zone)
        p._n = self._n  # shared counter so names stay unique on the slide
        return p

    def _name(self, kind: str) -> str:
        self._n["_"] += 1
        return f"cpe|{self.zone}|{kind}|{self._n['_']}"

    def style(self, role: str) -> dict:
        return type_style(role, self.profile)

    def color(self, token: str) -> str:
        return self.theme.c(token)

    # -- primitives --------------------------------------------------------
    def rect(self, box: Box, fill: str | None = None, line: str | None = None, line_w: float = LINES["rule"], kind: str = "fill", shape=MSO_SHAPE.RECTANGLE, dash: bool = False):
        sp = self.slide.shapes.add_shape(shape, E(box.x), E(box.y), E(box.w), E(box.h))
        _strip_style(sp)
        sp.name = self._name(kind)
        if fill:
            sp.fill.solid()
            sp.fill.fore_color.rgb = rgb(self.color(fill))
        else:
            sp.fill.background()
        if line:
            sp.line.color.rgb = rgb(self.color(line))
            sp.line.width = Pt(line_w)
            if dash:
                sp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            sp.line.fill.background()
        # autoshape text frame must not add padding if later used
        tf = sp.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        return sp

    def oval(self, box: Box, fill: str | None = None, line: str | None = None, line_w: float = LINES["rule"], kind: str = "marker"):
        return self.rect(box, fill, line, line_w, kind, shape=MSO_SHAPE.OVAL)

    def shape(self, mso_shape, box: Box, fill: str | None = None, line: str | None = None, line_w: float = LINES["rule"], kind: str = "fill"):
        return self.rect(box, fill, line, line_w, kind, shape=mso_shape)

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = "rule", width: float = LINES["rule"], arrow_end: bool = False, arrow_start: bool = False, dash: bool = False, kind: str = "line"):
        cx = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
        _strip_style(cx)
        cx.name = self._name(kind)
        cx.line.color.rgb = rgb(self.color(color))
        cx.line.width = Pt(width)
        if dash:
            cx.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        ln = cx.line._get_or_add_ln()
        # schema order inside a:ln: fill, prstDash, join, headEnd, tailEnd
        if arrow_start:
            etree.SubElement(ln, qn("a:headEnd"), {"type": "triangle", "w": "med", "len": "med"})
        if arrow_end:
            etree.SubElement(ln, qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
        return cx

    def elbow(self, x1: float, y1: float, x2: float, y2: float, color: str = "rule", width: float = LINES["rule"], mid: str = "v"):
        """Orthogonal connector drawn as straight segments (renders identically everywhere)."""
        if mid == "v":  # down, across, down
            ym = (y1 + y2) / 2
            self.line(x1, y1, x1, ym, color, width, kind="connector")
            if abs(x2 - x1) > 1e-3:
                self.line(min(x1, x2), ym, max(x1, x2), ym, color, width, kind="connector")
            self.line(x2, ym, x2, y2, color, width, kind="connector")
        else:  # across, down, across
            xm = (x1 + x2) / 2
            self.line(x1, y1, xm, y1, color, width, kind="connector")
            if abs(y2 - y1) > 1e-3:
                self.line(xm, min(y1, y2), xm, max(y1, y2), color, width, kind="connector")
            self.line(xm, y2, x2, y2, color, width, kind="connector")

    # -- text --------------------------------------------------------------
    def text(
        self,
        box: Box,
        paras: list[Para] | list[str] | str,
        role: str = "body",
        align: str = "left",
        anchor: str = "top",
        color: str | None = None,
        bold: bool | None = None,
        size: float | None = None,
        fit: bool = True,
        floor: float | None = None,
        spacing: float | None = None,
        space_after: float | None = None,
        kind: str = "text",
        fill: str | None = None,
        inset: float = 0.0,
        max_lines: int | None = None,
        record: str | None = None,
        vertical: bool = False,
    ):
        """Paint text into `box`, shrinking towards the role floor if needed.
        `vertical=True` rotates the text 270° (reads bottom→top); it is measured
        against the rotated box."""
        if isinstance(paras, str):
            paras = [Para(paras)]
        paras = [p if isinstance(p, Para) else Para(str(p)) for p in paras]
        st = self.style(role)
        base = size or st["size"]
        is_bold = st["bold"] if bold is None else bold
        spacing = spacing if spacing is not None else (LINE_SPACING if len(paras) > 1 else 1.0)
        sa = PARA_SPACE_AFTER if space_after is None else space_after
        floor = floor or FONT_FLOOR.get(role, FONT_FLOOR["default"])
        floor = min(floor, base)
        inner_w = box.w - 2 * inset
        inner_h = box.h - 2 * inset
        if vertical:
            inner_w, inner_h = inner_h, inner_w
            kind = "vtext"
        indent = 0.17 if any(p.bullet for p in paras) else 0.0

        def measure(sz: float) -> tuple[float, int]:
            h = 0.0
            lines = 0
            for i, p in enumerate(paras):
                psz = p.size * sz / base if p.size else sz
                b = is_bold if p.bold is None else p.bold
                ind = indent * (1 + p.level) if p.bullet else 0.0
                n = len(tm.wrap_lines(plain(p.text), max(0.05, inner_w - ind), psz, b))
                lines += n
                h += n * tm.line_height_in(psz, spacing)
                if i < len(paras) - 1:
                    h += (p.space_after if p.space_after is not None else sa) / 72
            return h, lines

        chosen = base
        need, nlines = measure(base)
        overflow = need > inner_h + 1e-3 or (max_lines is not None and nlines > max_lines)
        if overflow and fit:
            s = base - 0.5
            while s >= floor - 1e-9:
                need, nlines = measure(s)
                if need <= inner_h + 1e-3 and (max_lines is None or nlines <= max_lines):
                    chosen = s
                    overflow = False
                    break
                s -= 0.5
            if overflow:
                chosen = floor
                need, nlines = measure(floor)
        if record or overflow or chosen != base:
            self.manifest.fits.append(
                {
                    "zone": self.zone,
                    "role": role,
                    "what": record or plain(paras[0].text)[:60],
                    "base_pt": base,
                    "chosen_pt": chosen,
                    "need_h": round(need, 3),
                    "box_h": round(inner_h, 3),
                    "lines": nlines,
                    "overflow": bool(overflow),
                }
            )

        tb = self.slide.shapes.add_textbox(E(box.x), E(box.y), E(box.w), E(box.h))
        tb.name = self._name(kind)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.margin_left = tf.margin_right = E(inset)
        tf.margin_top = tf.margin_bottom = E(inset)
        tf.vertical_anchor = ANCHOR[anchor]
        if vertical:
            tf._txBody.bodyPr.set("vert", "vert270")
        if fill:
            tb.fill.solid()
            tb.fill.fore_color.rgb = rgb(self.color(fill))
        col = self.color(color or st["color"])
        for i, p in enumerate(paras):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = ALIGN[p.align or align]
            para.line_spacing = spacing
            if i < len(paras) - 1:
                para.space_after = Pt(p.space_after if p.space_after is not None else sa)
            psz = p.size * chosen / base if p.size else chosen
            if p.bullet:
                self._bullet(para, p.bullet, p.level, indent, psz, self.color(p.color) if p.color else col)
            txt = p.text.upper() if st.get("caps") else p.text
            for seg in BOLD_RE.split(txt):
                if not seg:
                    continue
                strong = seg.startswith("**") and seg.endswith("**")
                run = para.add_run()
                run.text = seg[2:-2] if strong else seg
                f = run.font
                f.name = self.theme.font_latin
                f.size = Pt(psz)
                f.bold = True if strong else (is_bold if p.bold is None else p.bold)
                f.color.rgb = rgb(self.color(p.color) if p.color else col)
        return tb

    def _bullet(self, para, char: str, level: int, indent: float, size: float, color: str):
        pPr = para._p.get_or_add_pPr()
        mar = int((indent * (1 + level)) * 914400)
        pPr.set("marL", str(mar))
        pPr.set("indent", str(-int(indent * 914400)))
        for tag in ("a:buNone", "a:buChar", "a:buAutoNum", "a:buClr", "a:buSzPct", "a:buFont"):
            for el in pPr.findall(qn(tag)):
                pPr.remove(el)
        buClr = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(buClr, qn("a:srgbClr"), {"val": color})
        etree.SubElement(pPr, qn("a:buSzPct"), {"val": "100000"})
        etree.SubElement(pPr, qn("a:buFont"), {"typeface": "Arial"})
        etree.SubElement(pPr, qn("a:buChar"), {"char": char})

    def measure(self, text: str, role: str, width: float, size: float | None = None, bold: bool | None = None) -> tuple[float, int]:
        st = self.style(role)
        sz = size or st["size"]
        b = st["bold"] if bold is None else bold
        lines = tm.wrap_lines(plain(text), width, sz, b)
        return len(lines) * tm.line_height_in(sz), len(lines)

    def text_w(self, text: str, role: str, size: float | None = None, bold: bool | None = None) -> float:
        st = self.style(role)
        return tm.text_width_in(plain(text), size or st["size"], st["bold"] if bold is None else bold)

    def warn(self, code: str, msg: str):
        self.manifest.warnings.append({"zone": self.zone, "code": code, "message": msg})
