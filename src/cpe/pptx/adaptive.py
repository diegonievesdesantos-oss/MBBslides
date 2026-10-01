"""Adaptive vertical composition (v1.4).

Components used to draw at fixed sizes from the top of their zone: sparse content became a thin
strip under the headline with most of the slide empty (process, comparison, KPI strip, gantt,
text slides were the weakest archetypes in v1.3.3 for exactly that reason). Each component now

  1. measures its content's natural height at a candidate type scale,
  2. takes the LARGEST scale on a bounded ladder whose block still fits comfortably
     (type grows for sparse content, never past readable caps, never to fill space by itself),
  3. places the block on the zone's optical centre (slightly above the geometric centre).

Dense content keeps scale ≤ 1 and the full height, exactly as before.
"""
from __future__ import annotations

from collections.abc import Callable

from ..layout.engine import Box

LADDER = (1.5, 1.35, 1.2, 1.1, 1.0, 0.92, 0.85)
OPTICAL = 0.42  # share of the free space left ABOVE a centred block


def pick_scale(block_h: Callable[[float], float], avail: float, fill: float = 0.82, ladder: tuple = LADDER, cap: float | None = None) -> tuple[float, float]:
    """(scale, block height): the largest scale whose block uses at most `fill` of `avail`."""
    for k in ladder:
        if cap is not None and k > cap:
            continue
        h = block_h(k)
        if h <= avail * fill:
            return k, h
    k = ladder[-1]
    return k, block_h(k)


def optical_top(box: Box, h: float, bias: float = OPTICAL) -> float:
    return box.y + max(0.0, (box.h - h) * bias)


def size(base: float, k: float, cap: float) -> float:
    return round(min(cap, base * k) * 2) / 2


HIERARCHY = 1.36  # the headline must stay this much larger than any body text (archetype metric `ratio`)


def body_cap(p, cap: float) -> float:
    """Upper bound for scaled body type: never rival the headline."""
    return min(cap, int(p.style("headline")["size"] / HIERARCHY * 2) / 2)
