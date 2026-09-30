"""Composition metrics: visual quality made measurable.

Every metric is computed on what was actually rendered (PNG ink + PDF text
spans) inside the body band, plus the slide spec for intent-related metrics.
All scores are in [0, 1] (1 = good); the composite is 0–100.

  dead_space        largest empty rectangle of the body (as a share of the body).
                    "The table floats in half an empty slide" becomes a number.
  utilization       share of the body covered by the bounding box of the content.
  balance           how close the visual centre of mass is to the body centre
                    (horizontal weighted more than vertical: top-heavy is normal).
  density           ink coverage inside a comfortable band (not empty, not a wall).
  emphasis          focal-point strength: some ink is in the focus colours
                    (primary / highlight) AND it forms few regions — one clear
                    focal point, not many things shouting.
  evidence          the headline's numbers and highlighted items are visible in
                    the exhibit (the proof is on the slide, not only in the title).
  hierarchy         headline clearly dominates the body type; few body sizes.
  alignment         few distinct left edges for text lines (a visible rhythm).

Flags turn low scores into named critiques: DEAD_SPACE, UNDERUSED_CANVAS,
OFF_BALANCE, NO_FOCAL_POINT, NOISY_EMPHASIS, SPARSE, OVERDENSE,
PROOF_NOT_VISIBLE, WEAK_HIERARCHY, RAGGED_ALIGNMENT.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..design.tokens import GRID, SLIDE_H, SLIDE_W, hex_to_rgb
from ..layout.engine import Box

WEIGHTS = {
    "dead_space": 20,
    "utilization": 12,
    "balance": 10,
    "density": 10,
    "emphasis": 10,
    "evidence": 16,
    "hierarchy": 10,
    "alignment": 12,
}

THRESHOLDS = {  # below → flag
    "dead_space": 0.55,
    "utilization": 0.6,
    "balance": 0.55,
    "density": 0.5,
    "emphasis": 0.5,
    "evidence": 0.5,
    "hierarchy": 0.6,
    "alignment": 0.5,
}

CELL = 0.1  # inches per analysis cell


@dataclass
class SlideComposition:
    slide_id: str
    metrics: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict:
        return {"slide_id": self.slide_id, "score": round(self.score, 1), "metrics": {k: round(v, 3) for k, v in self.metrics.items()}, "raw": self.raw, "flags": self.flags}


def _ink_grid(png_path: str, band: Box, focus_rgbs: list[tuple[int, int, int]]):
    from PIL import Image

    im = Image.open(png_path).convert("RGB")
    W, H = im.size
    sx, sy = W / SLIDE_W, H / SLIDE_H
    crop = im.crop((int(band.x * sx), int(band.y * sy), int(band.r * sx), int(band.b * sy)))
    cw, ch = crop.size
    nx, ny = max(1, round(band.w / CELL)), max(1, round(band.h / CELL))
    px = crop.load()
    grid = [[0] * nx for _ in range(ny)]
    egrid = [[0] * nx for _ in range(ny)]
    ink = focus = total = dark = 0
    wx = wy = wsum = 0.0
    step = 2
    for j in range(ny):
        y0, y1 = int(j * ch / ny), int((j + 1) * ch / ny)
        for i in range(nx):
            x0, x1 = int(i * cw / nx), int((i + 1) * cw / nx)
            c_ink = n = c_focus = 0
            for y in range(y0, y1, step):
                for x in range(x0, x1, step):
                    r, g, b = px[x, y]
                    n += 1
                    if min(r, g, b) < 232:
                        c_ink += 1
                        if (r * 299 + g * 587 + b * 114) / 1000 < 200:
                            dark += 1
                        if any(abs(r - fr) + abs(g - fg) + abs(b - fb) < 60 for fr, fg, fb in focus_rgbs):
                            focus += 1
                            c_focus += 1
            total += n
            ink += c_ink
            if n and c_focus / n > 0.55:  # solid focus-coloured mass (fills, hero numbers), not text strokes
                egrid[j][i] = 1
            if n and c_ink / n > 0.02:
                grid[j][i] = 1
                w = c_ink / n
                wx += (i + 0.5) / nx * w
                wy += (j + 0.5) / ny * w
                wsum += w
    com = (wx / wsum, wy / wsum) if wsum else (0.5, 0.5)
    return grid, dark / max(1, total), focus / max(1, ink), com, _components(egrid)


def _components(g) -> int:
    """Connected regions (8-neighbourhood) of focus-coloured cells; tiny specks ignored."""
    ny, nx = len(g), len(g[0]) if g else 0
    seen = [[False] * nx for _ in range(ny)]
    count = 0
    for j in range(ny):
        for i in range(nx):
            if g[j][i] and not seen[j][i]:
                size, stack = 0, [(j, i)]
                seen[j][i] = True
                while stack:
                    y, x = stack.pop()
                    size += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = y + dy, x + dx
                            if 0 <= yy < ny and 0 <= xx < nx and g[yy][xx] and not seen[yy][xx]:
                                seen[yy][xx] = True
                                stack.append((yy, xx))
                if size >= 3:
                    count += 1
    return count


def _largest_empty_rect(grid) -> int:
    """Largest all-zero rectangle (in cells) — classic histogram stack algorithm."""
    if not grid:
        return 0
    nx = len(grid[0])
    heights = [0] * nx
    best = 0
    for row in grid:
        for i, v in enumerate(row):
            heights[i] = heights[i] + 1 if v == 0 else 0
        hts = heights + [0]
        stack: list[int] = []
        for i, h in enumerate(hts):
            while stack and hts[stack[-1]] >= h:
                top = stack.pop()
                left = stack[-1] + 1 if stack else 0
                best = max(best, hts[top] * (i - left))
            stack.append(i)
    return best


def _bbox(grid):
    rows = [j for j, row in enumerate(grid) if any(row)]
    cols = [i for i in range(len(grid[0])) if any(row[i] for row in grid)] if grid else []
    if not rows or not cols:
        return None
    return min(cols), min(rows), max(cols), max(rows)


def _band(lo: float, hi: float, v: float, soft: float) -> float:
    """1 inside [lo, hi], decaying linearly to 0 at `soft` outside."""
    if lo <= v <= hi:
        return 1.0
    d = lo - v if v < lo else v - hi
    return max(0.0, 1 - d / soft)


def measure(png_path: str, spans: list[dict], slide: dict, manifest: dict, theme) -> SlideComposition:
    from ..core.headline import numbers_in

    sid = manifest.get("slide_id") or slide.get("id", "?")
    band = Box(GRID.margin_l, GRID.body_y, GRID.content_w, GRID.body_bottom - GRID.body_y)
    focus_cols = [hex_to_rgb(theme.c("primary")), hex_to_rgb(theme.c("highlight"))]
    grid, coverage, emph_share, (cx, cy), regions = _ink_grid(png_path, band, focus_cols)
    ny, nx = len(grid), len(grid[0])
    sc = SlideComposition(sid)
    # dead space
    empty = _largest_empty_rect(grid) / (nx * ny)
    sc.raw["largest_empty_share"] = round(empty, 3)
    sc.metrics["dead_space"] = max(0.0, min(1.0, 1 - (empty - 0.18) / 0.4))
    # utilization
    bb = _bbox(grid)
    util = 0.0 if bb is None else ((bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1)) / (nx * ny)
    sc.raw["utilization"] = round(util, 3)
    sc.metrics["utilization"] = _band(0.75, 1.0, util, 0.5)
    # balance (centre of mass of ink weight)
    sc.raw["center_of_mass"] = [round(cx, 3), round(cy, 3)]
    sc.metrics["balance"] = max(0.0, 1 - (abs(cx - 0.5) / 0.35) ** 2 * 0.6 - max(0.0, abs(cy - 0.45) - 0.12) / 0.5)
    # density
    sc.raw["ink_coverage"] = round(coverage, 3)
    sc.metrics["density"] = _band(0.06, 0.30, coverage, 0.12)
    # emphasis
    # focal-point strength: something must stand out (share) and it must be ONE thing, not many (regions)
    sc.raw["emphasis_share"] = round(emph_share, 3)
    sc.raw["focus_regions"] = regions
    presence = _band(0.05, 1.0, emph_share, 0.05)
    singularity = 1.0 if regions <= 3 else max(0.0, 1 - (regions - 3) * 0.12) if emph_share > 0.35 else max(0.3, 1 - (regions - 3) * 0.05)
    sc.metrics["emphasis"] = presence * singularity
    # evidence: headline numbers / highlighted labels visible in the body
    head = slide.get("headline") or ""
    body_text = " ".join(s["text"] for s in spans if s["box"].y >= GRID.body_y - 0.05)
    body_nums = {abs(v) for v, _ in numbers_in(body_text)}
    hnums = [abs(v) for v, _ in numbers_in(head)]
    checks = []
    for v in hnums:
        checks.append(any(abs(v - b) <= max(0.051, 0.01 * v) for b in body_nums))
    hls = []
    for ex in [slide.get("visual")] + list(slide.get("exhibits") or []):
        if isinstance(ex, dict):
            hls += [str(h) for h in ex.get("highlight") or [] if not isinstance(h, int)]
    for h in hls:
        checks.append(any(w.lower() in head.lower() for w in h.split() if len(w) > 3) or h.lower() in body_text.lower())
    sc.raw["proof_checks"] = f"{sum(checks)}/{len(checks)}"
    if slide.get("kind") == "exec_summary":
        sc.metrics["evidence"] = 1.0  # the summary quotes numbers proven on later slides
    else:
        sc.metrics["evidence"] = (sum(checks) / len(checks)) if checks else 0.8
    # hierarchy
    head_sizes = [s["size"] for s in spans if s["box"].y < GRID.body_y - 0.1 and s["size"] >= 16]
    body_sizes = sorted({round(s["size"]) for s in spans if s["box"].y >= GRID.body_y - 0.05 and s["box"].b <= GRID.body_bottom + 0.05})
    hmax = max(head_sizes) if head_sizes else 22
    zones = {n: (z.get("role"), Box(z["x"], z["y"], z["w"], z["h"])) for n, z in (manifest.get("zones") or {}).items()}
    kpi_boxes = [b for r, b in zones.values() if r == "kpis"]
    bmax = max([s["size"] for s in spans if s["box"].y >= GRID.body_y - 0.05 and s["box"].b <= GRID.body_bottom + 0.05 and len(s["text"]) > 3
                and not any(k.contains(s["box"], 0.05) for k in kpi_boxes)] or [12])
    ratio = hmax / max(1, bmax)
    sc.raw["headline_body_ratio"] = round(ratio, 2)
    sc.raw["body_font_sizes"] = body_sizes
    sc.metrics["hierarchy"] = min(1.0, max(0.0, (ratio - 1.0) / 0.6)) * (1.0 if len(body_sizes) <= 5 else max(0.4, 1 - 0.12 * (len(body_sizes) - 5)))
    # alignment rhythm: distinct left edges of text lines in the body
    text_boxes = [b for r, b in zones.values() if r in ("commentary", "column", "statements", "kpis", "takeaway", "statement")]
    lefts = sorted(s["box"].x for s in spans if s.get("line_start") and any(b.contains(s["box"], 0.05) for b in text_boxes))
    clusters = []
    for x in lefts:
        if not clusters or x - clusters[-1][-1] > 0.05:
            clusters.append([x])
        else:
            clusters[-1].append(x)
    big = [c for c in clusters if len(c) >= 2]
    singles = len(clusters) - len(big)
    sc.raw["left_edges"] = len(clusters)
    sc.metrics["alignment"] = 1.0 if not lefts else max(0.0, min(1.0, 1 - max(0, singles - 4) * 0.08 - max(0, len(big) - 10) * 0.05))
    # composite + flags
    sc.score = sum(WEIGHTS[k] * sc.metrics[k] for k in WEIGHTS) / sum(WEIGHTS.values()) * 100
    names = {
        "dead_space": "DEAD_SPACE",
        "utilization": "UNDERUSED_CANVAS",
        "balance": "OFF_BALANCE",
        "density": "SPARSE" if coverage < 0.06 else "OVERDENSE",
        "emphasis": "NO_FOCAL_POINT" if emph_share < 0.05 else "NOISY_EMPHASIS",
        "evidence": "PROOF_NOT_VISIBLE",
        "hierarchy": "WEAK_HIERARCHY",
        "alignment": "RAGGED_ALIGNMENT",
    }
    for k, t in THRESHOLDS.items():
        if sc.metrics[k] < t:
            sc.flags.append(names[k])
    return sc


REMEDIES = {
    "DEAD_SPACE": "Even the best composition leaves a large empty area: the content is too thin for a full slide — add the proof (numbers, comparison) or merge it into a neighbouring slide.",
    "UNDERUSED_CANVAS": "The exhibit uses little of the slide: give it more data/proof or merge the slide.",
    "PROOF_NOT_VISIBLE": "The headline's number or highlighted item is not visible in the exhibit: label it or highlight it.",
    "NO_FOCAL_POINT": "Nothing stands out: highlight the one element that proves the headline.",
    "NOISY_EMPHASIS": "Too much in the focus colour: keep one highlight and grey the context.",
    "OVERDENSE": "Very dense slide: cut or split.",
}


def issues_from(comps: list["SlideComposition"]) -> list[dict]:
    """Composition flags the engine could not fix → warnings with a remedy for the author."""
    out = []
    for c in comps:
        for f in c.flags:
            if f in REMEDIES:
                out.append({"level": "warning", "code": f"COMPOSITION_{f}", "message": f"{REMEDIES[f]} (composition score {c.score:.0f})", "slide": c.slide_id})
    return out


def spans_with_line_starts(page) -> list[dict]:
    """PDF spans with a `line_start` flag (first span of each rendered line)."""
    out = []
    d = page.get_text("dict")
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            first = True
            for sp in line.get("spans", []):
                t = sp.get("text", "")
                if not t.strip():
                    continue
                x0, y0, x1, y1 = sp["bbox"]
                out.append({"text": t, "box": Box(x0 / 72, y0 / 72, (x1 - x0) / 72, (y1 - y0) / 72), "size": sp.get("size", 0), "line_start": first})
                first = False
    return out


def measure_deck(pdf_path: str, pngs: list[str], resolved: dict, manifests: list[dict], theme) -> list[SlideComposition]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    out = []
    for i, (page, png) in enumerate(zip(doc, pngs)):
        slide = resolved["slides"][i] if i < len(resolved["slides"]) else {}
        man = manifests[i] if i < len(manifests) else {}
        if slide.get("kind", "content") not in ("content", "exec_summary"):
            continue
        out.append(measure(png, spans_with_line_starts(page), slide, man, theme))
    doc.close()
    return out
