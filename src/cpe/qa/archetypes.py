"""Slide archetypes and their expected visual profiles.

The v1.1 composition score asked "is the canvas used a lot?" for every slide. That
rewards the same composition everywhere: a statement slide with generous air lost
points, a table stretched to fill the slide won them. v1.2 asks instead

    is THIS slide's composition appropriate for what the slide is trying to be?

    SLIDE INTENT → ARCHETYPE → EXPECTED VISUAL PROFILE → RENDER
                 → OBSERVED VISUAL PROFILE → DEVIATION → COMPOSITION FITNESS

The archetype comes from the slide's CONTENT (kind + exhibit type + text roles), never
from the layout, so alternative layouts of the same content are judged against the
same expectations (qa/composition.py, compose.py).

Profiles (PROFILES) give, per observed metric, a target range [lo, hi], how fast
fitness decays outside it (`soft`), and how much the metric matters for the archetype
(`w`). Observed metrics are raw measurements of the render (qa/composition.py):

  utilization   share of the body band covered by the content's bounding box
  empty         largest empty rectangle, as a share of the body band
  ink           ink coverage of the body band (density)
  offcentre     distance of the ink's centre of mass from the body centre (balance)
  emphasis      share of the ink in the focus colours (primary + highlight). One-sided: it can say
                "nothing stands out", not "too much stands out" — the primary colour is also the
                default data ink (every bar of a single-series chart), so a high share is normal
  regions       number of separate solid regions in the ACCENT (highlight) colour only: several
                accent masses competing is what "noisy emphasis" means
  ratio         headline size / largest body text size (hierarchy)
  edges         number of isolated left edges in the text (alignment rhythm)
  proof         share of headline numbers / highlights visible in the body

How the ranges were derived is documented in docs/COMPOSITION_SCORING.md: design
reasoning first, then checked against the renders of the calibration set (the example
decks, reviewed and approved slide by slide, and the regression suite). The public
holdout (evals/holdout) was sealed before this file was written and is never used to
set these numbers.
"""
from __future__ import annotations

ARCHETYPES = [
    "statement", "kpi_hero", "kpi_dashboard", "executive_summary", "chart", "waterfall", "table", "matrix",
    "comparison", "process", "roadmap", "timeline", "operating_model", "architecture", "hierarchy",
    "segmentation", "text_exhibit",
]

EXHIBIT_ARCHETYPE = {
    "waterfall": "waterfall", "bridge": "waterfall",
    "table": "table", "heatmap": "table", "harvey_table": "table", "scorecard": "table",
    "matrix_2x2": "matrix", "portfolio": "matrix",
    "gantt": "roadmap", "roadmap": "roadmap",
    "timeline": "timeline",
    "process": "process", "value_chain": "process", "journey": "process",
    "operating_model": "operating_model", "layers": "operating_model",
    "architecture": "architecture", "flow": "architecture",
    "org_chart": "hierarchy", "tree": "hierarchy", "driver_tree": "hierarchy", "pyramid": "hierarchy",
    "mekko": "segmentation", "segmentation": "segmentation", "tile_map": "segmentation",
    "text_columns": "comparison", "comparison": "comparison",
    "bullets": "text_exhibit",
}
CHART_TYPES = {"column", "bar", "stacked_column", "stacked_bar", "stacked_100", "line", "slope", "area", "histogram", "combo",
               "scatter", "bubble", "pie", "donut", "funnel"}


def classify(slide: dict) -> tuple[str, str]:
    """(archetype, why) from the slide's kind and content — not from its layout."""
    from ..core.layout_selector import content_roles

    kind = slide.get("kind", "content")
    if kind == "statement":
        return "statement", "slide kind statement"
    if kind == "exec_summary":
        return "executive_summary", "slide kind exec_summary"
    roles = content_roles(slide)
    exhibits = roles.get("exhibit") or []
    if exhibits:
        t = exhibits[0].get("type") or "auto"
        if t in EXHIBIT_ARCHETYPE:
            return EXHIBIT_ARCHETYPE[t], f"main exhibit is a {t}"
        if t in CHART_TYPES or t == "auto":
            return "chart", f"main exhibit is a {t} chart"
        return "chart", f"main exhibit type {t} treated as a chart"
    kpis = (roles.get("kpis") or {}).get("items") or (roles.get("kpis") or {}).get("data", {}).get("items") or []
    if kpis:
        return ("kpi_hero", "a single headline figure") if len(kpis) <= 2 else ("kpi_dashboard", f"{len(kpis)} KPIs")
    if roles.get("statements"):
        return "executive_summary", "numbered statements"
    if roles.get("column"):
        return "comparison", "comparison columns"
    if roles.get("statement"):
        return "statement", "statement text"
    return "text_exhibit", "text only"


def _m(lo, hi, soft, w):
    return {"range": [lo, hi], "soft": soft, "w": w}


# Shared expectations; archetypes override what differs.
_BASE = {
    "utilization": _m(0.70, 1.00, 0.35, 12),
    "empty": _m(0.00, 0.25, 0.35, 16),
    "ink": _m(0.06, 0.30, 0.12, 8),
    "offcentre": _m(0.00, 0.12, 0.30, 8),
    "emphasis": _m(0.05, 1.00, 0.05, 8),
    "regions": _m(0, 5, 4, 4),  # a highlighted series repeats across categories: only many masses are noise
    "ratio": _m(1.35, 9.0, 0.5, 10),
    "edges": _m(0, 5, 6, 6),
    "proof": _m(0.5, 1.0, 0.5, 14),
}


def _p(**over):
    out = {k: dict(v) for k, v in _BASE.items()}
    for k, v in over.items():
        if v is None:
            out.pop(k)
        else:
            out[k] = {**out[k], **v}
    return out


PROFILES = {
    # one sentence carries the slide: air is the point, density would be wrong
    "statement": _p(utilization=_m(0.15, 0.75, 0.35, 6), empty=_m(0.0, 0.80, 0.25, 4), ink=_m(0.01, 0.12, 0.08, 6),
                    offcentre=_m(0.0, 0.25, 0.3, 4), emphasis=_m(0.0, 1.0, 0.1, 0), regions=_m(0, 3, 6, 2), proof=None,
                    ratio=None),  # the statement text IS the message: it may be larger than any headline
    # one big figure: intentional whitespace, the figure must dominate
    # (a centred figure leaves empty bands above/below of ~40% of the body; half the slide empty is not intentional)
    "kpi_hero": _p(utilization=_m(0.25, 0.95, 0.35, 8), empty=_m(0.0, 0.50, 0.25, 12), ink=_m(0.02, 0.20, 0.08, 6),
                   offcentre=_m(0.0, 0.22, 0.3, 10), emphasis=_m(0.10, 1.0, 0.10, 12), regions=_m(0, 2, 4, 4)),
    "kpi_dashboard": _p(utilization=_m(0.70, 1.0, 0.35, 12), empty=_m(0.0, 0.30, 0.3, 14), ink=_m(0.04, 0.30, 0.10, 8),
                        emphasis=_m(0.05, 0.70, 0.08, 6), regions=_m(0, 6, 6, 4)),
    # dense by nature: text should fill the canvas in an even rhythm
    "executive_summary": _p(utilization=_m(0.75, 1.0, 0.3, 12), empty=_m(0.0, 0.25, 0.3, 16), ink=_m(0.03, 0.35, 0.12, 8),
                            emphasis=_m(0.0, 1.0, 0.08, 0), regions=_m(0, 6, 6, 2), proof=None, edges=_m(0, 6, 8, 10)),
    # solid bars are data ink, not clutter; a line chart is thin by nature
    "chart": _p(utilization=_m(0.72, 1.0, 0.35, 12), empty=_m(0.0, 0.28, 0.35, 16), ink=_m(0.01, 0.45, 0.12, 6)),
    # the bridge needs the full width and most of the height for its deltas
    "waterfall": _p(utilization=_m(0.78, 1.0, 0.3, 14), empty=_m(0.0, 0.25, 0.3, 16), ink=_m(0.03, 0.40, 0.12, 6)),
    # a table that floats in half an empty slide is the canonical failure
    "table": _p(utilization=_m(0.75, 1.0, 0.25, 16), empty=_m(0.0, 0.20, 0.25, 20), ink=_m(0.02, 0.32, 0.06, 6),
                offcentre=_m(0.0, 0.14, 0.3, 6), emphasis=_m(0.0, 1.0, 0.08, 0)),
    # a 2x2 is a square field: balance matters more than filling every corner
    "matrix": _p(utilization=_m(0.65, 1.0, 0.25, 12), empty=_m(0.0, 0.32, 0.30, 12), ink=_m(0.04, 0.28, 0.12, 6),
                 offcentre=_m(0.0, 0.10, 0.25, 14)),
    "comparison": _p(utilization=_m(0.72, 1.0, 0.3, 12), empty=_m(0.0, 0.28, 0.3, 14), offcentre=_m(0.0, 0.10, 0.25, 12),
                     edges=_m(0, 6, 8, 10)),
    "process": _p(utilization=_m(0.72, 1.0, 0.3, 12), empty=_m(0.0, 0.28, 0.3, 14), edges=_m(0, 8, 10, 6)),
    # roadmaps and timelines read left→right across the whole width
    "roadmap": _p(utilization=_m(0.78, 1.0, 0.3, 16), empty=_m(0.0, 0.28, 0.3, 12), ink=_m(0.04, 0.30, 0.12, 6)),
    # a timeline is a one-dimensional band: air above and below it is inherent, not waste
    "timeline": _p(utilization=_m(0.35, 1.0, 0.35, 10), empty=_m(0.0, 0.50, 0.3, 10), ink=_m(0.01, 0.25, 0.10, 6),
                   offcentre=_m(0.0, 0.18, 0.3, 6)),
    # layered diagrams carry a label column on the left: their ink is left-weighted by construction
    "operating_model": _p(utilization=_m(0.78, 1.0, 0.3, 14), empty=_m(0.0, 0.22, 0.3, 14), ink=_m(0.06, 0.40, 0.12, 8), edges=_m(0, 10, 10, 4),
                          offcentre=_m(0.0, 0.35, 0.3, 3)),
    "architecture": _p(utilization=_m(0.75, 1.0, 0.3, 14), empty=_m(0.0, 0.25, 0.3, 14), ink=_m(0.06, 0.40, 0.12, 8), edges=_m(0, 10, 10, 4),
                       offcentre=_m(0.0, 0.35, 0.3, 3)),
    "hierarchy": _p(utilization=_m(0.65, 1.0, 0.35, 12), empty=_m(0.0, 0.35, 0.3, 12), ink=_m(0.03, 0.30, 0.12, 6), edges=_m(0, 10, 10, 4)),
    "segmentation": _p(utilization=_m(0.72, 1.0, 0.3, 12), empty=_m(0.0, 0.28, 0.3, 14)),
    # prose: some air is fine, a sliver of text on an empty slide is not
    "text_exhibit": _p(utilization=_m(0.55, 1.0, 0.35, 12), empty=_m(0.0, 0.40, 0.3, 14), ink=_m(0.03, 0.25, 0.10, 8),
                       emphasis=_m(0.0, 0.5, 0.08, 2), regions=_m(0, 4, 6, 2)),
}

# what the deviation means, per metric and direction (for editorial explanations)
MEANING = {
    ("utilization", "low"): "content uses too little of the canvas",
    ("utilization", "high"): "content crowds the whole canvas",
    ("empty", "high"): "a large area is left empty",
    ("ink", "low"): "too sparse",
    ("ink", "high"): "too dense",
    ("offcentre", "high"): "visual weight is off-balance",
    ("emphasis", "low"): "nothing stands out",
    ("emphasis", "high"): "too much is emphasised",
    ("regions", "high"): "several elements compete for attention",
    ("ratio", "low"): "the headline does not dominate the body text",
    ("edges", "high"): "ragged alignment",
    ("proof", "low"): "the headline's proof is not visible",
}

FLAG_OF = {
    ("utilization", "low"): "UNDERUSED_CANVAS", ("utilization", "high"): "OVERFILLED",
    ("empty", "high"): "DEAD_SPACE", ("ink", "low"): "SPARSE", ("ink", "high"): "OVERDENSE",
    ("offcentre", "high"): "OFF_BALANCE", ("emphasis", "low"): "NO_FOCAL_POINT", ("emphasis", "high"): "NOISY_EMPHASIS",
    ("regions", "high"): "NOISY_EMPHASIS", ("ratio", "low"): "WEAK_HIERARCHY", ("edges", "high"): "RAGGED_ALIGNMENT",
    ("proof", "low"): "PROOF_NOT_VISIBLE",
}


def fit(value: float, spec: dict) -> tuple[float, str | None]:
    """Fitness in [0, 1] of one observed value against a profile entry, and the direction of any deviation."""
    lo, hi = spec["range"]
    if lo <= value <= hi:
        return 1.0, None
    d, side = (lo - value, "low") if value < lo else (value - hi, "high")
    return max(0.0, 1 - d / spec["soft"]), side


CRITICAL_WEIGHT = 10  # metrics weighted at least this much are what the archetype is about
WORST_SHARE = 0.3  # share of the score given to the worst critical metric


def fitness(archetype: str, observed: dict) -> dict:
    """Score = fitness of the observed profile to the archetype's expected profile.

    (1 − WORST_SHARE) × weighted mean fitness + WORST_SHARE × the worst fitness among the
    archetype's critical metrics. A plain mean lets many "fine" metrics dilute one severe
    failure (half the slide empty, the proof invisible); composition quality is bounded by
    its worst failure.
    """
    prof = PROFILES.get(archetype) or PROFILES["chart"]
    per, dev = {}, []
    num = den = 0.0
    for k, spec in prof.items():
        if k not in observed or observed[k] is None or not spec["w"]:
            continue
        f, side = fit(observed[k], spec)
        per[k] = round(f, 3)
        num += spec["w"] * f
        den += spec["w"]
        if side:
            dev.append({"metric": k, "value": round(observed[k], 3), "expected": spec["range"], "direction": side, "fitness": round(f, 3),
                        "weight": spec["w"], "meaning": MEANING.get((k, side), f"{k} {side}"), "flag": FLAG_OF.get((k, side))})
    dev.sort(key=lambda d: (d["fitness"] - 1) * d["weight"])
    if not den:
        return {"score": None, "per_metric": per, "deviations": dev}
    crit = [per[k] for k, spec in prof.items() if k in per and spec["w"] >= CRITICAL_WEIGHT]
    worst = min(crit) if crit else 1.0
    score = 100 * ((1 - WORST_SHARE) * num / den + WORST_SHARE * worst)
    return {"score": round(score, 1), "per_metric": per, "deviations": dev, "worst_critical": round(worst, 3)}
