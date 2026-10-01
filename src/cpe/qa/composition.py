"""Composition metrics: visual quality made measurable.

v1.2: the SCORE is archetype fitness (qa/archetypes.py): the observed visual profile
of the render compared with the profile expected for what the slide is (a statement,
a KPI hero, a table, a roadmap…). The v1.1 universal score is still computed
(`score_v1`) for continuity and comparison, but no longer drives decisions.
Composition is editorial PREFERENCE, reported as advice — it never enters the hard QA
verdict or the QA score (see `advice_from`).

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

import re
from dataclasses import dataclass, field

from ..design.tokens import GRID, SLIDE_H, SLIDE_W, hex_to_rgb
from ..layout.engine import Box
from .archetypes import classify, fitness

FIGURE_RE = re.compile(r"^[▲▼+\-−–~≈<>]?\s*[$€£¥]?\s*\d[\d.,\s]*\s*(%|[A-Za-zµ€$£×x]{1,6}\.?)?(\s+[a-z]{1,6})?$")
FLAG_BELOW = 0.6  # a metric whose fitness to the archetype falls below this is named as a critique

SCORE_NAME = "archetype-fitness composition score"

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
    archetype: str = "chart"
    archetype_why: str = ""
    observed: dict = field(default_factory=dict)
    fitness: dict = field(default_factory=dict)
    deviations: list = field(default_factory=list)
    attribution: dict = field(default_factory=dict)
    score_v1: float = 0.0
    flags_v1: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"slide_id": self.slide_id, "archetype": self.archetype, "archetype_why": self.archetype_why, "score": round(self.score, 1),
                "observed": {k: round(v, 3) for k, v in self.observed.items()}, "fitness": self.fitness, "deviations": self.deviations, "attribution": self.attribution, "flags": self.flags,
                "score_v1": round(self.score_v1, 1), "flags_v1": self.flags_v1,
                "metrics": {k: round(v, 3) for k, v in self.metrics.items()}, "raw": self.raw}


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
    agrid = [[0] * nx for _ in range(ny)]  # accent (highlight colour) only: the deliberate emphasis
    ar, ag, ab = focus_rgbs[-1]
    ink = focus = total = dark = 0
    wx = wy = wsum = 0.0
    step = 2
    for j in range(ny):
        y0, y1 = int(j * ch / ny), int((j + 1) * ch / ny)
        for i in range(nx):
            x0, x1 = int(i * cw / nx), int((i + 1) * cw / nx)
            c_ink = n = c_focus = c_acc = 0
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
                            if abs(r - ar) + abs(g - ag) + abs(b - ab) < 60:
                                c_acc += 1
            total += n
            ink += c_ink
            if n and c_focus / n > 0.55:  # solid focus-coloured mass (fills, hero numbers), not text strokes
                egrid[j][i] = 1
            if n and c_acc / n > 0.55:
                agrid[j][i] = 1
            if n and c_ink / n > 0.02:
                grid[j][i] = 1
                w = c_ink / n
                wx += (i + 0.5) / nx * w
                wy += (j + 0.5) / ny * w
                wsum += w
    com = (wx / wsum, wy / wsum) if wsum else (0.5, 0.5)
    _mark_rules(crop, grid)
    return grid, dark / max(1, total), focus / max(1, ink), com, _components(egrid), _components(agrid), _occupancy(crop, grid)


def _occupancy(crop, grid) -> list[list[int]]:
    """(v1.5) What the composition OCCUPIES, for utilization and dead space — not the same as ink:

    * a visible filled panel (a KPI card, a tinted band) occupies its area even when its fill is
      too light to count as ink — the reader sees the card, not only the text inside it;
    * an isolated thin VERTICAL line running through otherwise empty cells (a separator drawn to
      the foot of the slide under a strip of figures) does not make that empty space "used".
    Found by the r2 scorer–human disagreement on KPI dashboards (docs/KPI_DASHBOARD_DIAGNOSIS.md);
    horizontal rules keep their v1.2 meaning (they structure the rows they separate)."""
    from collections import Counter

    cw, ch = crop.size
    ny, nx = len(grid), len(grid[0])
    small = crop.resize((max(1, cw // 4), max(1, ch // 4)))
    pixels = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
    bg = Counter(pixels).most_common(1)[0][0]  # the page colour actually drawn
    px = small.load()
    sw, sh = small.size
    occ = [row[:] for row in grid]
    # panels: ≥ 60% of the cell differs from the page colour, but is not ink
    for j in range(ny):
        y0, y1 = int(j * sh / ny), max(int(j * sh / ny) + 1, int((j + 1) * sh / ny))
        for i in range(nx):
            if occ[j][i]:
                continue
            x0, x1 = int(i * sw / nx), max(int(i * sw / nx) + 1, int((i + 1) * sw / nx))
            n = diff = 0
            for y in range(y0, min(y1, sh)):
                for x in range(x0, min(x1, sw)):
                    n += 1
                    r, g, b = px[x, y]
                    if max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2])) >= 6:
                        diff += 1
            if n and diff / n >= 0.6:
                occ[j][i] = 1
    # isolated vertical lines: a run of ≥ 6 occupied cells in one column whose left and right
    # neighbours are all empty — a separator crossing empty space, not content
    for i in range(nx):
        j = 0
        while j < ny:
            if not occ[j][i]:
                j += 1
                continue
            k = j
            while k < ny and occ[k][i] and not (i > 0 and occ[k][i - 1]) and not (i < nx - 1 and occ[k][i + 1]):
                k += 1
            if k - j >= 6:
                for r in range(j, k):
                    occ[r][i] = 0
            j = max(k, j + 1)
    return occ


def _mark_rules(crop, grid) -> None:
    """Hairline rules (table rows, dividers) are 1 px: the 2-px sampling above can miss them.
    A pixel row whose faint ink spans ≥ 40% of the band is a rule — it structures the space
    it crosses, so the cells it runs through are not empty (for dead space / utilization)."""
    from PIL import Image

    g = crop.convert("L").point(lambda v: 255 if v < 245 else 0)
    cw, ch = g.size
    ny, nx = len(grid), len(grid[0])
    col = g.resize((1, ch), Image.BOX)
    means = [col.getpixel((0, y)) for y in range(ch)]
    for y, m in enumerate(means):
        if m < 0.4 * 255:
            continue
        bb = g.crop((0, y, cw, y + 1)).getbbox()
        if not bb:
            continue
        j = min(ny - 1, int(y * ny / ch))
        for i in range(int(bb[0] * nx / cw), min(nx, int((bb[2] - 1) * nx / cw) + 1)):
            grid[j][i] = 1


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


SCALE_UNITS = {"bn", "b", "m", "mn", "mm", "k", "mil", "millones", "billion", "million"}


def _scaled_match(v: float, unit: str, body_nums: set) -> bool:
    """(v1.4) "€1.2bn" in the headline is proven by "1,210" in an exhibit in €M: the same number at
    another scale (×1000 / ÷1000), within the precision the headline was written with."""
    u = (unit or "").lower().strip("€$£¥%. ")
    if u in SCALE_UNITS:
        factors = (1000.0, 0.001)
    elif not u and v >= 10_000 and float(v).is_integer():  # "€61,000,000" proven by "61" in an exhibit in €M
        factors = (1e-3, 1e-6, 1e-9)
    else:
        return False
    dec = len(repr(float(v)).split(".")[1].rstrip("0")) if "." in repr(float(v)) else 0
    half = 0.5 * 10 ** (-dec)
    for f in factors:
        if any(abs(v * f - b) <= max(half * f, 0.01 * v * f) for b in body_nums):
            return True
    return False


def measure(png_path: str, spans: list[dict], slide: dict, manifest: dict, theme) -> SlideComposition:
    from ..core.headline import numbers_in

    sid = manifest.get("slide_id") or slide.get("id", "?")
    band = Box(GRID.margin_l, GRID.body_y, GRID.content_w, GRID.body_bottom - GRID.body_y)
    focus_cols = [hex_to_rgb(theme.c("primary")), hex_to_rgb(theme.c("highlight"))]
    grid, coverage, emph_share, (cx, cy), regions, accent_regions, occ = _ink_grid(png_path, band, focus_cols)
    ny, nx = len(grid), len(grid[0])
    sc = SlideComposition(sid)
    # dead space (on occupancy: panels occupy, isolated separators do not)
    empty = _largest_empty_rect(occ) / (nx * ny)
    sc.raw["largest_empty_share"] = round(empty, 3)
    sc.metrics["dead_space"] = max(0.0, min(1.0, 1 - (empty - 0.18) / 0.4))
    # utilization
    bb = _bbox(occ)
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
    sc.raw["accent_regions"] = accent_regions
    presence = _band(0.05, 1.0, emph_share, 0.05)
    singularity = 1.0 if regions <= 3 else max(0.0, 1 - (regions - 3) * 0.12) if emph_share > 0.35 else max(0.3, 1 - (regions - 3) * 0.05)
    sc.metrics["emphasis"] = presence * singularity
    # evidence: headline numbers / highlighted labels visible in the body
    import re

    head = re.sub(r"\s*\(\d+/\d+\)\s*$", "", slide.get("headline") or "")  # "(1/2)" continuation marker is not a claim
    body_text = " ".join(s["text"] for s in spans if s["box"].y >= GRID.body_y - 0.05)
    body_nums = {abs(v) for v, _ in numbers_in(body_text)}
    hnums = [(abs(v), u) for v, u in numbers_in(head)]
    # counts are proven by the exhibit's structure ("twelve plants" = twelve rows), not by a printed number
    counts = set()
    for ex in [slide.get("visual")] + list(slide.get("exhibits") or []):
        if isinstance(ex, dict):
            data = ex.get("data") or {}
            for coll in (ex.get("rows"), data.get("categories"), data.get("steps"), data.get("events"), data.get("items"), data.get("stages"), data.get("rows"), data.get("points")):
                if coll:
                    counts.add(float(len(coll)))
            if ex.get("_rows_total"):
                counts.add(float(ex["_rows_total"]))
    checks = []
    from .proof import derive, headline_quantities, slide_series

    hq = headline_quantities(head)
    series = None
    proofs = []
    for i, (v, unit) in enumerate(hnums):
        q = next((x for x in hq if abs(x["value"] / (x["scale"] or 1) - v) < 1e-9), None)
        rounding = 0.5 * 10 ** (-q["decimals"]) if q else 0.0  # "21%" is proven by 21.4: the headline rounds
        if any(abs(v - b) <= max(0.051, 0.01 * v, rounding) for b in body_nums):
            rec = {"status": "direct"}
        elif v in counts:
            rec = {"status": "count"}
        elif _scaled_match(v, unit, body_nums):
            rec = {"status": "scaled"}
        else:  # (v1.5) arithmetic lineage: sum / difference / ratio / % change / pp / share of a visible series
            series = slide_series(slide) if series is None else series
            rec = derive(q, series) if q else {"status": "unknown", "reason": "unit not parsed"}
            if q and rec["status"] == "unknown":  # v1.6: two single quantities of two exhibits
                from .proof import derive_across, slide_scalars

                across = derive_across(q, slide_scalars(slide))
                rec = across if across["status"] != "unknown" else rec
        rec.setdefault("headline_value", f"{v:g}{unit}")
        proofs.append(rec)
        checks.append(rec["status"] != "unknown")
    sc.raw["proof"] = proofs
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
    def wordy(t):  # big figures ("€13M", "85%") are a deliberate emphasis device, not competing text
        if FIGURE_RE.match(t.strip()):  # (v1.4) a figure with a short unit ("4.5 days", "2 min", "−3 pts") is still a figure
            return False
        return sum(ch.isalpha() for ch in t) >= max(4, 0.5 * len(t.strip()))

    bmax = max([s["size"] for s in spans if s["box"].y >= GRID.body_y - 0.05 and s["box"].b <= GRID.body_bottom + 0.05 and wordy(s["text"])
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
    # v1.1 universal composite (kept for continuity; not used for decisions)
    sc.score_v1 = sum(WEIGHTS[k] * sc.metrics[k] for k in WEIGHTS) / sum(WEIGHTS.values()) * 100
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
            sc.flags_v1.append(names[k])
    # v1.2: fitness of the observed profile to the archetype's expected profile
    sc.archetype, sc.archetype_why = classify(slide)
    sc.observed = {
        "utilization": util, "empty": empty, "ink": coverage,
        "offcentre": (abs(cx - 0.5) ** 2 + max(0.0, abs(cy - 0.45) - 0.1) ** 2) ** 0.5,
        "emphasis": emph_share, "regions": float(accent_regions), "ratio": ratio, "edges": float(len(clusters)),
    }
    if checks and slide.get("kind") not in ("exec_summary", "statement"):
        sc.observed["proof"] = sum(checks) / len(checks)
    f = fitness(sc.archetype, sc.observed)
    sc.score = f["score"] if f["score"] is not None else sc.score_v1
    sc.fitness, sc.deviations = f["per_metric"], f["deviations"]
    sc.attribution = f.get("attribution") or {}
    for d in sc.deviations:
        if d["flag"] and d["fitness"] < FLAG_BELOW and d["flag"] not in sc.flags:
            sc.flags.append(d["flag"])
    return sc


REMEDIES = {
    "DEAD_SPACE": "Even the best composition leaves a large empty area: the content is too thin for this kind of slide — add the proof (numbers, comparison) or merge it into a neighbouring slide.",
    "UNDERUSED_CANVAS": "The content uses little of the slide for what it is: give it more data/proof, or turn it into a different slide type (statement, KPI).",
    "OVERFILLED": "The content crowds the canvas for this kind of slide: cut or split.",
    "PROOF_NOT_VISIBLE": "The headline's number or highlighted item is not visible in the exhibit: label it or highlight it.",
    "NO_FOCAL_POINT": "Nothing stands out: highlight the one element that proves the headline.",
    "NOISY_EMPHASIS": "Too much in the focus colour: keep one highlight and grey the context.",
    "OVERDENSE": "Very dense for this kind of slide: cut or split.",
    "SPARSE": "Very little ink for this kind of slide: add the proof or merge the slide.",
    "OFF_BALANCE": "The visual weight sits on one side: check the layout choice.",
    "WEAK_HIERARCHY": "The body text competes with the headline: reduce it or reword as a statement slide.",
    "RAGGED_ALIGNMENT": "Many unrelated left edges: align the text blocks.",
}


def advice_from(comps: list["SlideComposition"]) -> list[dict]:
    """Composition flags → EDITORIAL ADVICE (level "advice").

    Advice is a preference, not a defect: it never enters the hard-QA issue list, the QA
    score or the pass/fail verdict. A slide with a mediocre composition is still valid;
    a slide with clipping is not.
    """
    out = []
    for c in comps:
        why = {d["flag"]: d for d in c.deviations if d.get("flag")}
        for f in c.flags:
            d = why.get(f)
            detail = f" — {c.archetype}: {d['meaning']} ({d['metric']} {d['value']} vs expected {d['expected'][0]}–{d['expected'][1]})" if d else f" — {c.archetype}"
            out.append({"level": "advice", "code": f"COMPOSITION_{f}", "message": f"{REMEDIES.get(f, f)}{detail} · fitness {c.score:.0f}", "slide": c.slide_id,
                        "archetype": c.archetype})
    return out


MEASURED_KINDS = ("content", "exec_summary", "statement")


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


# v1.7: composition fitness must not reward a BROKEN slide (human round r3, expert rater: v1.4
# waterfalls with negative totals — bars missing, labels off the slide — scored 100 while QA had
# already flagged them). Broken = content lost, outside or overlapping, or a chart that cannot encode
# its data. Other QA errors (contrast, small type, palette) still fail the QA gate but are not
# "broken": on r3 the expert tied every pair whose only difference was low contrast.
BROKEN_CODES = {"OFF_SLIDE", "OUTSIDE_ZONE", "TEXT_OVERFLOW", "TEXT_COLLISION", "LABEL_COLLISION", "CONNECTOR_THROUGH_TEXT", "PLACEHOLDER_TEXT",
                "RENDER_OFF_SLIDE", "RENDER_TEXT_SPILL", "RENDER_TEXT_COLLISION", "RENDER_LABEL_TRUNCATED", "WATERFALL_NEGATIVE"}


def integrity_issues(issues: list[dict], slide_id: str) -> list[str]:
    return sorted({i["code"] for i in issues or [] if i.get("slide") == slide_id and i.get("code") in BROKEN_CODES
                   and (i.get("level") == "error" or i.get("code") == "WATERFALL_NEGATIVE")})


def apply_integrity(comps: list["SlideComposition"], issues: list[dict], manifests: list[dict] | None = None) -> None:
    """Re-score every measured slide with the observed `integrity` (1 intact, 0 broken)."""
    warn = list(issues or [])
    for m in manifests or []:  # painter warnings (e.g. WATERFALL_NEGATIVE) live in the manifest
        warn += [{"slide": m.get("slide_id"), "level": "warning", "code": w.get("code")} for w in m.get("warnings") or []]
    for sc in comps:
        bad = integrity_issues(warn, sc.slide_id)
        sc.observed["integrity"] = 0.0 if bad else 1.0
        sc.raw["integrity_issues"] = bad
        f = fitness(sc.archetype, sc.observed)
        if f["score"] is None:
            continue
        sc.score = f["score"]
        sc.fitness, sc.deviations = f["per_metric"], f["deviations"]
        sc.attribution = f.get("attribution") or {}
        for d in sc.deviations:
            if d["flag"] and d["fitness"] < FLAG_BELOW and d["flag"] not in sc.flags:
                sc.flags.append(d["flag"])


def measure_deck(pdf_path: str, pngs: list[str], resolved: dict, manifests: list[dict], theme) -> list[SlideComposition]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    out = []
    for i, (page, png) in enumerate(zip(doc, pngs)):
        slide = resolved["slides"][i] if i < len(resolved["slides"]) else {}
        man = manifests[i] if i < len(manifests) else {}
        if slide.get("kind", "content") not in MEASURED_KINDS:
            continue
        out.append(measure(png, spans_with_line_starts(page), slide, man, theme))
    doc.close()
    return out
