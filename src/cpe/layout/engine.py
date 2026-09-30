"""Layout engine: loads the layout library and resolves zones to inch boxes.

A layout is pure geometry + semantics, declared in JSON under /layouts/<family>/.
Zones are placed on the 12-column grid horizontally and on fractions of the body
band vertically, so every layout snaps to the same grid (consistency by
construction). Adjacent zones are separated by exactly one gutter.

Layout JSON:
{
  "id": "exhibit_commentary_right",
  "family": "04_chart_commentary",
  "name": "...", "description": "...", "when_to_use": "...",
  "zones": [
     {"name": "exhibit", "role": "exhibit", "cols": [1, 8], "top": 0, "bottom": 1},
     {"name": "commentary", "role": "commentary", "cols": [9, 12], "top": 0, "bottom": 1,
      "style": "rule_left"}
  ],
  "accepts": {"exhibit": [1, 1], "commentary": [0, 1], "kpis": [0, 0]},
  "takeaway": "optional" | "none" | "required",
  "compatible_visuals": ["bar", ...],
  "capacity": {"commentary": {"bullets": 5, "words": 80}},
  "hierarchy": ["exhibit", "commentary"]
}
"""
from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..design.tokens import GRID, SPACING, Grid

LAYOUTS_DIR = Path(__file__).resolve().parents[3] / "layouts"

TAKEAWAY_H = 0.62  # "so-what" bar at the bottom of the body band
EXHIBIT_HEADER_H = 0.46  # exhibit title + unit line reserved on top of an exhibit zone


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def r(self) -> float:
        return self.x + self.w

    @property
    def b(self) -> float:
        return self.y + self.h

    def inset(self, l=0.0, t=0.0, r=0.0, b=0.0) -> "Box":
        return Box(self.x + l, self.y + t, max(0.01, self.w - l - r), max(0.01, self.h - t - b))

    def split_v(self, top_h: float, gap: float = 0.0) -> tuple["Box", "Box"]:
        return Box(self.x, self.y, self.w, top_h), Box(self.x, self.y + top_h + gap, self.w, max(0.01, self.h - top_h - gap))

    def split_h(self, left_w: float, gap: float = 0.0) -> tuple["Box", "Box"]:
        return Box(self.x, self.y, left_w, self.h), Box(self.x + left_w + gap, self.y, max(0.01, self.w - left_w - gap), self.h)

    def columns(self, n: int, gap: float) -> list["Box"]:
        w = (self.w - gap * (n - 1)) / n
        return [Box(self.x + i * (w + gap), self.y, w, self.h) for i in range(n)]

    def rows(self, n: int, gap: float) -> list["Box"]:
        h = (self.h - gap * (n - 1)) / n
        return [Box(self.x, self.y + i * (h + gap), self.w, h) for i in range(n)]

    def to_dict(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "w": round(self.w, 4), "h": round(self.h, 4)}

    def contains(self, other: "Box", tol: float = 0.02) -> bool:
        return other.x >= self.x - tol and other.y >= self.y - tol and other.r <= self.r + tol and other.b <= self.b + tol

    def intersection(self, other: "Box") -> float:
        ix = max(0.0, min(self.r, other.r) - max(self.x, other.x))
        iy = max(0.0, min(self.b, other.b) - max(self.y, other.y))
        return ix * iy


@dataclass
class Zone:
    name: str
    role: str
    box: Box
    style: str | None = None
    spec: dict = field(default_factory=dict)


@dataclass
class Layout:
    id: str
    family: str
    name: str
    description: str
    when_to_use: str
    zones: list[dict]
    accepts: dict
    takeaway: str
    compatible_visuals: list[str]
    capacity: dict
    hierarchy: list[str]
    body_band: str = "body"  # "body" | "full" (cover/divider use the whole slide)
    raw: dict = field(default_factory=dict)

    def roles(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for z in self.zones:
            out[z["role"]] = out.get(z["role"], 0) + 1
        return out


@functools.lru_cache(maxsize=1)
def load_library(layouts_dir: str | None = None) -> dict[str, Layout]:
    root = Path(layouts_dir) if layouts_dir else LAYOUTS_DIR
    lib: dict[str, Layout] = {}
    for p in sorted(root.glob("*/*.json")):
        d = json.loads(p.read_text())
        lay = Layout(
            id=d["id"],
            family=d.get("family", p.parent.name),
            name=d.get("name", d["id"]),
            description=d.get("description", ""),
            when_to_use=d.get("when_to_use", ""),
            zones=d["zones"],
            accepts=d.get("accepts", {}),
            takeaway=d.get("takeaway", "optional"),
            compatible_visuals=d.get("compatible_visuals", []),
            capacity=d.get("capacity", {}),
            hierarchy=d.get("hierarchy", [z["name"] for z in d["zones"]]),
            body_band=d.get("body_band", "body"),
            raw=d,
        )
        if lay.id in lib:
            raise ValueError(f"Duplicate layout id {lay.id} ({p})")
        lib[lay.id] = lay
    return lib


def get_layout(layout_id: str) -> Layout:
    lib = load_library()
    if layout_id not in lib:
        raise KeyError(f"Unknown layout '{layout_id}'. Run `cpe catalog` to list layouts.")
    return lib[layout_id]


def resolve_zones(layout: Layout, with_takeaway: bool = False, grid: Grid = GRID, has_subheadline: bool = False) -> dict[str, Zone]:
    """Convert a layout's grid declaration into absolute boxes (inches)."""
    if layout.body_band == "full":
        top, bottom = grid.tracker_y, grid.body_bottom
    else:
        top = grid.body_y + (grid.subheadline_h if has_subheadline else 0.0)
        bottom = grid.body_bottom
    zones: dict[str, Zone] = {}
    if with_takeaway and layout.takeaway != "none":
        tk = Box(grid.margin_l, bottom - TAKEAWAY_H, grid.content_w, TAKEAWAY_H)
        zones["takeaway"] = Zone("takeaway", "takeaway", tk, "takeaway_bar")
        bottom = bottom - TAKEAWAY_H - SPACING["M"]
    band_h = bottom - top
    g = grid.gutter
    for z in layout.zones:
        c1, c2 = z["cols"]
        x = grid.col_x(c1)
        w = grid.span_w(c1, c2)
        t, b = float(z.get("top", 0.0)), float(z.get("bottom", 1.0))
        y0 = top + t * band_h + (g / 2 if t > 0 else 0.0)
        y1 = top + b * band_h - (g / 2 if b < 1 else 0.0)
        zones[z["name"]] = Zone(z["name"], z["role"], Box(x, y0, w, y1 - y0), z.get("style"), z)
    return zones


def catalog_markdown() -> str:
    lib = load_library()
    fams: dict[str, list[Layout]] = {}
    for lay in lib.values():
        fams.setdefault(lay.family, []).append(lay)
    lines = ["# Layout catalogue", ""]
    for fam in sorted(fams):
        lines.append(f"## {fam}")
        lines.append("")
        lines.append("| id | zones | takeaway | use when |")
        lines.append("|---|---|---|---|")
        for lay in fams[fam]:
            zs = ", ".join(f"{z['name']}[{z['cols'][0]}-{z['cols'][1]}]" for z in lay.zones)
            lines.append(f"| `{lay.id}` | {zs} | {lay.takeaway} | {lay.when_to_use} |")
        lines.append("")
    return "\n".join(lines)
