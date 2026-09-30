"""Design tokens: the single source of truth for every visual decision.

Nothing in the renderers may hard-code a colour, a font size or a distance.
Everything is looked up here (or in a theme JSON that overrides these defaults),
so a deck is consistent by construction and a theme swap is one argument.

Units: distances are inches (float), font sizes are points, colours are
6-char hex strings without '#'.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

THEMES_DIR = Path(__file__).parent / "themes"

# ---------------------------------------------------------------------------
# Canvas & grid
# ---------------------------------------------------------------------------
SLIDE_W = 13.333  # 16:9 widescreen
SLIDE_H = 7.5

SPACING = {  # spacing scale — the only distances layouts may use
    "XXS": 0.04,
    "XS": 0.08,
    "S": 0.15,
    "M": 0.25,
    "L": 0.40,
    "XL": 0.60,
    "XXL": 0.90,
}


@dataclass
class Grid:
    """12-column grid with fixed vertical bands.

    Vertical bands (top→bottom):
      tracker   small section label above the headline
      headline  action title, max 2 lines
      body      the exhibit area — layouts only place zones here
      footer    source / footnotes / page number
    """

    margin_l: float = 0.55
    margin_r: float = 0.55
    columns: int = 12
    gutter: float = 0.22
    tracker_y: float = 0.30
    tracker_h: float = 0.22
    headline_y: float = 0.52
    headline_h: float = 0.86  # two lines of 22 pt with 1.0 spacing + slack
    subheadline_h: float = 0.30
    body_y: float = 1.62
    body_bottom: float = 6.78
    footer_y: float = 6.86
    footer_h: float = 0.44

    @property
    def content_w(self) -> float:
        return SLIDE_W - self.margin_l - self.margin_r

    @property
    def col_w(self) -> float:
        return (self.content_w - self.gutter * (self.columns - 1)) / self.columns

    @property
    def body_h(self) -> float:
        return self.body_bottom - self.body_y

    def col_x(self, col: int) -> float:
        """Left edge of 1-based column `col`."""
        return self.margin_l + (col - 1) * (self.col_w + self.gutter)

    def span_w(self, first: int, last: int) -> float:
        n = last - first + 1
        return n * self.col_w + (n - 1) * self.gutter

    def safe_box(self) -> tuple[float, float, float, float]:
        return (self.margin_l, self.tracker_y, self.content_w, self.footer_y + self.footer_h - self.tracker_y)


GRID = Grid()
_GRID_DEFAULTS = dict(GRID.__dict__)
GRID_EXTRA_DEFAULTS = {"headline_right_limit": None, "footer_right_limit": None}
for _k, _v in GRID_EXTRA_DEFAULTS.items():
    setattr(GRID, _k, _v)


def apply_grid(overrides: dict | None) -> None:
    """Reset the shared grid to defaults, then apply brand overrides (margins, limits)."""
    for k, v in {**_GRID_DEFAULTS, **GRID_EXTRA_DEFAULTS}.items():
        setattr(GRID, k, v)
    for k, v in (overrides or {}).items():
        if k in _GRID_DEFAULTS or k in GRID_EXTRA_DEFAULTS:
            setattr(GRID, k, v)

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
# role -> (size_pt, bold, colour_token)
TYPE_SCALE: dict[str, dict] = {
    "cover_title": {"size": 36, "bold": True, "color": "primary"},
    "cover_subtitle": {"size": 16, "bold": False, "color": "text_muted"},
    "divider_title": {"size": 32, "bold": True, "color": "primary"},
    "headline": {"size": 22, "bold": True, "color": "primary"},
    "subheadline": {"size": 14, "bold": False, "color": "text_muted"},
    "tracker": {"size": 10, "bold": True, "color": "text_muted", "caps": True},
    "section": {"size": 14, "bold": True, "color": "primary"},
    "exhibit_title": {"size": 12, "bold": True, "color": "text"},
    "exhibit_unit": {"size": 11, "bold": False, "color": "text_muted"},
    "body": {"size": 12, "bold": False, "color": "text"},
    "body_strong": {"size": 12, "bold": True, "color": "text"},
    "kpi_value": {"size": 30, "bold": True, "color": "primary"},
    "kpi_label": {"size": 11, "bold": False, "color": "text_muted"},
    "chart": {"size": 11, "bold": False, "color": "text"},
    "chart_axis": {"size": 10, "bold": False, "color": "text_muted"},
    "annotation": {"size": 10, "bold": False, "color": "text"},
    "table_header": {"size": 11, "bold": True, "color": "text"},
    "table_body": {"size": 11, "bold": False, "color": "text"},
    "source": {"size": 8, "bold": False, "color": "text_muted"},
    "footnote": {"size": 8, "bold": False, "color": "text_muted"},
    "page_number": {"size": 9, "bold": False, "color": "text_muted"},
}

# Hard legibility floors. The density engine may shrink text towards these,
# never below. QA fails any run under the floor for its role.
FONT_FLOOR = {
    "headline": 20,
    "body": 11,
    "chart": 10,
    "chart_axis": 9,
    "annotation": 9,
    "table_body": 10,
    "table_header": 10,
    "kpi_value": 22,
    "source": 8,
    "footnote": 8,
    "default": 9,
}

LINE_SPACING = 1.08  # multiple applied to body paragraphs
PARA_SPACE_AFTER = 5  # points between bullets

# ---------------------------------------------------------------------------
# Shape language
# ---------------------------------------------------------------------------
LINES = {
    "hairline": 0.5,  # gridlines (rarely), table inner rules
    "rule": 0.75,  # separators, table header rule, axis
    "strong": 1.5,  # emphasis rules, connectors in trees
    "accent": 2.25,  # left accent bar on callouts, highlight outlines
}
CORNER_RADIUS = 0.0  # square corners: no rounded "AI cards"
ARROW_HEAD = "triangle"


# ---------------------------------------------------------------------------
# Theme (colours + fonts) — loaded from JSON so decks can be re-skinned
# ---------------------------------------------------------------------------
HEADING_ROLES = {"headline", "cover_title", "divider_title"}


@dataclass
class Theme:
    name: str
    font_latin: str
    font_fallback_file: str
    colors: dict[str, str]
    series: list[str]
    sequential: list[str]
    diverging: list[str]
    extras: dict = field(default_factory=dict)
    font_heading: str | None = None
    source_dir: str | None = None

    def font_for(self, role: str) -> str:
        return self.font_heading if (self.font_heading and role in HEADING_ROLES) else self.font_latin

    def fonts(self) -> set[str]:
        return {self.font_latin} | ({self.font_heading} if self.font_heading else set())

    def c(self, token: str) -> str:
        """Resolve a colour token (or pass through a literal hex)."""
        if token in self.colors:
            return self.colors[token]
        t = token.lstrip("#")
        if len(t) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in t):
            return t.upper()
        raise KeyError(f"Unknown colour token '{token}' in theme '{self.name}'")

    def palette(self) -> set[str]:
        vals = set(v.upper() for v in self.colors.values())
        vals |= set(v.upper() for v in self.series + self.sequential + self.diverging)
        return vals


def load_theme(name: str = "meridian") -> Theme:
    """A built-in theme name, a theme JSON file, or a brand directory (from `cpe brand ingest`)."""
    p = Path(name)
    if p.is_dir() and (p / "theme.json").exists():
        path = p / "theme.json"
    elif p.suffix == ".json" and p.exists():
        path = p
    else:
        path = THEMES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Theme '{name}' not found (built-ins: {', '.join(available_themes())})")
    data = json.loads(path.read_text())
    return Theme(
        name=data["name"],
        font_latin=data["font_latin"],
        font_fallback_file=data.get("font_fallback_file", "LiberationSans"),
        colors={k: v.upper() for k, v in data["colors"].items()},
        series=[s.upper() for s in data["series"]],
        sequential=[s.upper() for s in data["sequential"]],
        diverging=[s.upper() for s in data["diverging"]],
        extras=data.get("extras", {}),
        font_heading=data.get("font_heading"),
        source_dir=str(path.parent),
    )


def theme_for(meta: dict) -> Theme:
    """Theme of a deck: `meta.brand` (a brand directory) wins over `meta.theme`."""
    return load_theme(meta.get("brand") or meta.get("theme") or "meridian")


def activate(theme: Theme) -> None:
    """Point the shared measurement and grid state at this theme (fonts, brand margins)."""
    from . import text_metrics as tm

    for font, fam in (theme.extras.get("measure_fonts") or {}).items():
        tm.register_font(font, fam)
    tm.set_default_family(tm.family_for(theme.font_latin))
    apply_grid(theme.extras.get("grid"))


def available_themes() -> list[str]:
    return sorted(p.stem for p in THEMES_DIR.glob("*.json"))


# ---------------------------------------------------------------------------
# Deck-type density profiles
# ---------------------------------------------------------------------------
PROFILES_PATH = Path(__file__).parent / "profiles.json"


def load_profile(name: str) -> dict:
    data = json.loads(PROFILES_PATH.read_text())
    base = copy.deepcopy(data["_default"])
    if name and name in data:
        base.update(data[name])
    elif name:
        # deck types map to a density profile
        mapped = data.get("_deck_type_map", {}).get(name)
        if mapped and mapped in data:
            base.update(data[mapped])
    base["deck_type"] = name
    return base


# roles the composition engine may enlarge on sparse slides (never chrome / sources)
SCALABLE_ROLES = {"body", "body_strong", "section", "kpi_value", "kpi_label", "table_header", "table_body"}  # charts keep their geometry
SCALE_CAP = {"body": 17, "body_strong": 18, "table_body": 15, "table_header": 15, "chart": 13, "chart_axis": 12, "annotation": 12, "kpi_value": 44}


def type_style(role: str, profile: dict | None = None) -> dict:
    s = dict(TYPE_SCALE[role])
    if profile:
        s["size"] = round(s["size"] * profile.get("font_scale", 1.0) * 2) / 2
        bs = profile.get("body_scale", 1.0)
        if bs != 1.0 and role in SCALABLE_ROLES:
            s["size"] = min(round(s["size"] * bs * 2) / 2, max(s["size"], SCALE_CAP.get(role, s["size"] * bs)))
        s["size"] = max(s["size"], FONT_FLOOR.get(role, FONT_FLOOR["default"]))
    return s


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(h: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def best_text_on(fill: str, theme: Theme) -> str:
    """Pick white or ink text for a filled shape, maximising contrast."""
    white, ink = "FFFFFF", theme.c("text")
    return white if contrast_ratio(fill, white) >= contrast_ratio(fill, ink) else ink


def legible_fill(fill: str, theme: "Theme", target: float = 4.5) -> str:
    """Mid-tone fills are illegible for both white and ink text: darken them just
    enough for white text to reach the target contrast."""
    if max(contrast_ratio(fill, "FFFFFF"), contrast_ratio(fill, theme.c("text"))) >= target:
        return fill
    f = fill
    for k in range(1, 11):
        f = interpolate(fill, theme.c("primary"), k / 10)
        if contrast_ratio(f, "FFFFFF") >= target:
            return f
    return f


def interpolate(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"{r:02X}{g:02X}{b:02X}"


def sequential_color(theme: Theme, t: float) -> str:
    """Continuous sequential scale sampled at t∈[0,1] along theme.sequential."""
    t = max(0.0, min(1.0, t))
    stops = theme.sequential
    if t >= 1:
        return stops[-1]
    pos = t * (len(stops) - 1)
    i = int(pos)
    return interpolate(stops[i], stops[i + 1], pos - i)
