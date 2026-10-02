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

import json
from pathlib import Path

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
    "process": "process", "value_chain": "process", "journey": "process", "cause_effect": "process", "causal_chain": "process",
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
        if t == "flow" and len({n.get("row", 0) for n in ((exhibits[0].get("data") or {}).get("nodes") or [])}) == 1:
            # (v1.4) a single row of boxes and arrows is a linear sequence, not a layered architecture
            return "process", "main exhibit is a single-row flow (a sequence)"
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
    if roles.get("text"):
        # (v1.4) text_exhibit had become a fallback bucket. One short argument with nothing else on
        # the slide IS a statement (one sentence carries the slide, air is the point) and is judged
        # as one; lists, paragraphs and quotes stay text exhibits (docs/COMPOSITION_SCORING.md)
        from ..core.headline import words
        from ..pptx.text_components import text_form

        form = text_form(roles["text"].get("points"))
        if form == "argument" and not roles.get("commentary"):
            return "statement", "a single short argument (text form: argument)"
        pts = roles["text"].get("points") or []
        if form == "quote" and len(pts) <= 3 and len(words(" ".join(str(x) for x in pts))) <= 45 and not roles.get("commentary"):
            return "statement", "short quotations carry the slide (text form: quote)"
        return "text_exhibit", f"text only (form: {form})"
    return "text_exhibit", "text only"


PROFILES_PATH = Path(__file__).parent / "archetype_profiles.json"


def load_profiles(path: Path = PROFILES_PATH) -> tuple[dict, dict]:
    """(base, profiles) from the governed profile file. Ranges live in data, not code, so every
    calibration change is a visible diff with its reason (evals/profile_changes.md)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    base = {k: {"range": list(v["range"]), "soft": v["soft"], "w": v["w"]} for k, v in data["base"].items()}
    profiles = {}
    for name, a in data["archetypes"].items():
        prof = {k: dict(v) for k, v in base.items()}
        for k, v in (a.get("metrics") or {}).items():
            if v is None:
                prof.pop(k, None)
            else:
                prof[k] = {"range": list(v["range"]), "soft": v["soft"], "w": v["w"]}
        profiles[name] = prof
    return base, profiles


def format_profiles(data: dict) -> str:
    """Canonical text of archetype_profiles.json: one metric per line, so calibration diffs are readable."""
    c = lambda o: json.dumps(o, ensure_ascii=False)  # noqa: E731
    L = ["{", ' "_doc": ' + json.dumps(data["_doc"], indent=2, ensure_ascii=False).replace("\n", "\n ") + ",", ' "base": {']
    base = list(data["base"].items())
    L += [f'  "{k}": {c(v)}' + ("," if i < len(base) - 1 else "") for i, (k, v) in enumerate(base)]
    L += [" },", ' "archetypes": {']
    arch = list(data["archetypes"].items())
    for i, (a, v) in enumerate(arch):
        L += [f'  "{a}": {{', f'   "why": {c(v["why"])},', f'   "evidence": {c(v["evidence"])},', '   "metrics": {']
        m = list(v["metrics"].items())
        L += [f'    "{k}": {c(x)}' + ("," if j < len(m) - 1 else "") for j, (k, x) in enumerate(m)]
        L += ["   }", "  }" + ("," if i < len(arch) - 1 else "")]
    return "\n".join(L + [" }", "}"]) + "\n"


_BASE, PROFILES = load_profiles()

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
    ("integrity", "low"): "the slide is broken: a visual QA error or a chart that cannot encode its data",
}

FLAG_OF = {
    ("utilization", "low"): "UNDERUSED_CANVAS", ("utilization", "high"): "OVERFILLED",
    ("empty", "high"): "DEAD_SPACE", ("ink", "low"): "SPARSE", ("ink", "high"): "OVERDENSE",
    ("offcentre", "high"): "OFF_BALANCE", ("emphasis", "low"): "NO_FOCAL_POINT", ("emphasis", "high"): "NOISY_EMPHASIS",
    ("regions", "high"): "NOISY_EMPHASIS", ("ratio", "low"): "WEAK_HIERARCHY", ("edges", "high"): "RAGGED_ALIGNMENT",
    ("proof", "low"): "PROOF_NOT_VISIBLE", ("integrity", "low"): "BROKEN_EXHIBIT",
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
    crit = {k: per[k] for k, spec in prof.items() if k in per and spec["w"] >= CRITICAL_WEIGHT}
    worst_k = min(crit, key=crit.get) if crit else None
    worst = crit[worst_k] if crit else 1.0
    score = 100 * ((1 - WORST_SHARE) * num / den + WORST_SHARE * worst)
    return {"score": round(score, 1), "per_metric": per, "deviations": dev, "worst_critical": round(worst, 3),
            "attribution": attribution(prof, observed, per, den, worst_k)}


def attribution(prof: dict, observed: dict, per: dict, den: float, worst_k: str | None) -> dict:
    """Where the points went: for each scored metric, expected range, observed value, fitness,
    weight and the points it costs. The penalties sum to 100 − score (before rounding):
    (1 − WORST_SHARE)·100·w·(1 − f)/Σw for every metric, plus WORST_SHARE·100·(1 − f) charged to
    the worst critical metric."""
    out = {}
    for k, f in per.items():
        spec = prof[k]
        pen = (1 - WORST_SHARE) * 100 * spec["w"] * (1 - f) / den
        if k == worst_k:
            pen += WORST_SHARE * 100 * (1 - f)
        out[k] = {"expected": spec["range"], "observed": round(observed[k], 3), "fitness": f, "weight": spec["w"], "penalty": round(pen, 2)}
    return out
