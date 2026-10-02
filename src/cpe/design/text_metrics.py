"""Text measurement with real font metrics.

PowerPoint does not tell python-pptx how much space text needs, so every
"does it fit?" decision (density engine before generation, overflow QA after
generation) is made here by wrapping text with the actual glyph advances of a
metric-compatible font (Liberation Sans == Arial metrics).

The wrap algorithm mirrors PowerPoint's: greedy word wrap on spaces, words
longer than the line are broken by character.
"""
from __future__ import annotations

import functools
import math
import os
from pathlib import Path

from PIL import ImageFont

FONT_DIRS = [
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/crosextra",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation2",
    "/usr/share/fonts/liberation",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/Library/Fonts"),
    "C:/Windows/Fonts",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
    str(Path(__file__).parent / "fonts"),
]

# measurement family -> (regular, bold) candidate file names
FONT_FILES = {
    "LiberationSans": (["LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf"], ["LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]),
    "LiberationSerif": (["LiberationSerif-Regular.ttf", "Times New Roman.ttf", "times.ttf"], ["LiberationSerif-Bold.ttf", "Times New Roman Bold.ttf", "timesbd.ttf"]),
    "LiberationMono": (["LiberationMono-Regular.ttf", "cour.ttf"], ["LiberationMono-Bold.ttf", "courbd.ttf"]),
    "Carlito": (["Carlito-Regular.ttf", "calibri.ttf", "Calibri.ttf"], ["Carlito-Bold.ttf", "calibrib.ttf", "Calibri Bold.ttf"]),
    "Caladea": (["Caladea-Regular.ttf", "cambria.ttc", "Cambria.ttf"], ["Caladea-Bold.ttf", "cambriab.ttf", "Cambria Bold.ttf"]),
    "DejaVuSans": (["DejaVuSans.ttf", "Verdana.ttf"], ["DejaVuSans-Bold.ttf", "Verdana Bold.ttf"]),
    "DejaVuSerif": (["DejaVuSerif.ttf"], ["DejaVuSerif-Bold.ttf"]),
}

# Font names used in decks -> measurement family (metric-compatible where one exists).
FONT_ALIASES = {
    "arial": "LiberationSans", "helvetica": "LiberationSans", "helvetica neue": "LiberationSans", "liberation sans": "LiberationSans", "arimo": "LiberationSans",
    "times new roman": "LiberationSerif", "times": "LiberationSerif", "liberation serif": "LiberationSerif", "tinos": "LiberationSerif",
    "courier new": "LiberationMono", "cousine": "LiberationMono",
    "calibri": "Carlito", "carlito": "Carlito",
    "cambria": "Caladea", "caladea": "Caladea",
    "verdana": "DejaVuSans", "dejavu sans": "DejaVuSans", "dejavu serif": "DejaVuSerif",
    # no metric twin: closest shape, measurement flagged as approximate
    "georgia": "DejaVuSerif", "garamond": "LiberationSerif", "palatino": "LiberationSerif", "book antiqua": "LiberationSerif",
    "segoe ui": "LiberationSans", "roboto": "LiberationSans", "open sans": "DejaVuSans", "lato": "LiberationSans", "montserrat": "DejaVuSans",
    "frutiger": "LiberationSans", "gill sans": "LiberationSans", "futura": "DejaVuSans", "univers": "LiberationSans",
}
METRIC_COMPATIBLE = {"arial", "helvetica", "liberation sans", "arimo", "times new roman", "times", "liberation serif", "tinos",
                     "courier new", "cousine", "calibri", "carlito", "cambria", "caladea"}

DEFAULT_FAMILY = "LiberationSans"
_REGISTERED: dict[str, str] = {}


def register_font(font_name: str, family: str) -> None:
    """Map a deck font name to a measurement family (used by brand themes)."""
    _REGISTERED[font_name.lower()] = family


def set_default_family(family: str) -> None:
    global DEFAULT_FAMILY
    DEFAULT_FAMILY = family


@functools.lru_cache(maxsize=None)
def installed_file(font_name: str, bold: bool = False) -> str | None:
    """File of an INSTALLED font family (exact family match through fontconfig), else None.
    Lets the engine measure with any real installed font (Inter, Roboto, a corporate face…),
    not only the built-in metric twins."""
    import subprocess

    try:
        r = subprocess.run(["fc-match", "-f", "%{family}|%{file}", f"{font_name}:weight={200 if bold else 80}"], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    fams, _, path = r.stdout.partition("|")
    names = {f.strip().lower() for f in fams.split(",")}
    if font_name.lower() not in names or not path or not os.path.exists(path) or not path.lower().endswith((".ttf", ".otf", ".ttc")):
        return None
    return path


def family_for(font_name: str | None) -> str:
    if not font_name:
        return DEFAULT_FAMILY
    key = font_name.lower()
    if key in _REGISTERED:
        return _REGISTERED[key]
    if key not in METRIC_COMPATIBLE and installed_file(font_name):
        return "fc:" + font_name  # measure with the real font
    return FONT_ALIASES.get(key) or DEFAULT_FAMILY


def family_available(family: str) -> bool:
    return _font_path(family, False) is not None

LINE_HEIGHT_FACTOR = 1.17  # Arial ascent+descent ≈ 1.149 em; renderers add a little


@functools.lru_cache(maxsize=None)
def _font_path(family: str, bold: bool) -> str | None:
    if family.startswith("fc:"):
        return installed_file(family[3:], bold)
    regular, boldf = FONT_FILES.get(family, FONT_FILES["LiberationSans"])
    if family not in FONT_FILES:
        return None
    for name in boldf if bold else regular:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def _font(size_pt: float, bold: bool, family: str | None = None):
    fam = family or DEFAULT_FAMILY
    if _font_path(fam, bold) is None:
        fam = "LiberationSans"
    return _font_cached(size_pt, bold, fam)


@functools.lru_cache(maxsize=512)
def _font_cached(size_pt: float, bold: bool, family: str):
    path = _font_path(family, bold)
    # Measure at 10x resolution for sub-point precision: 1pt == 10 units.
    px = max(1, int(round(size_pt * 10)))
    if path is None:  # pragma: no cover - degraded mode
        return None
    return ImageFont.truetype(path, px)


def text_width_in(text: str, size_pt: float, bold: bool = False, family: str | None = None) -> float:
    """Advance width of a single line, in inches."""
    if not text:
        return 0.0
    f = _font(size_pt, bold, family)
    if f is None:  # heuristic fallback: 0.52 em average
        return len(text) * size_pt * 0.52 / 72
    units = f.getlength(text)  # in 1/10 pt
    return units / 10 / 72


def wrap_lines(text: str, width_in: float, size_pt: float, bold: bool = False, family: str | None = None) -> list[str]:
    """Greedy word wrap. Honours explicit newlines."""
    out: list[str] = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            cand = w if not line else f"{line} {w}"
            if text_width_in(cand, size_pt, bold, family) <= width_in:
                line = cand
                continue
            if line:
                out.append(line)
            # word alone longer than the line → hard break
            if text_width_in(w, size_pt, bold, family) > width_in:
                chunk = ""
                for ch in w:
                    if text_width_in(chunk + ch, size_pt, bold, family) > width_in and chunk:
                        out.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                line = chunk
            else:
                line = w
        out.append(line)
    return out


def line_height_in(size_pt: float, spacing: float = 1.0) -> float:
    return size_pt * LINE_HEIGHT_FACTOR * spacing / 72


def text_block_height(
    paragraphs: list[str] | str,
    width_in: float,
    size_pt: float,
    bold: bool = False,
    spacing: float = 1.0,
    space_after_pt: float = 0.0,
    bullet_indent_in: float = 0.0,
) -> tuple[float, int]:
    """Height (inches) and total line count of a list of paragraphs."""
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    total_lines = 0
    h = 0.0
    for i, p in enumerate(paragraphs):
        n = len(wrap_lines(p, max(0.05, width_in - bullet_indent_in), size_pt, bold))
        total_lines += n
        h += n * line_height_in(size_pt, spacing)
        if i < len(paragraphs) - 1:
            h += space_after_pt / 72
    return h, total_lines


def fits(paragraphs, width_in, height_in, size_pt, bold=False, spacing=1.0, space_after_pt=0.0, bullet_indent_in=0.0) -> bool:
    h, _ = text_block_height(paragraphs, width_in, size_pt, bold, spacing, space_after_pt, bullet_indent_in)
    return h <= height_in + 1e-6


def largest_fitting_size(paragraphs, width_in, height_in, start_pt, floor_pt, bold=False, spacing=1.0, space_after_pt=0.0, bullet_indent_in=0.0, step=0.5):
    """Largest size in [floor, start] that fits, or None if even the floor overflows."""
    s = start_pt
    while s >= floor_pt - 1e-9:
        if fits(paragraphs, width_in, height_in, s, bold, spacing, space_after_pt, bullet_indent_in):
            return s
        s -= step
    return None


def max_chars_per_line(width_in: float, size_pt: float) -> int:
    """Rough capacity estimate used by planners (average glyph ≈ 0.5 em)."""
    return max(1, math.floor(width_in * 72 / (size_pt * 0.5)))
