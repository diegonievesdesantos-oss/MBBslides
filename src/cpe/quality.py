"""Distribution-aware quality profile of an eval run (v1.4).

A single mean hides structure: 87.5 overall coexisted with process and comparison slides at 39.
Every eval run therefore reports, next to the historical overall score,

    overall_score            mean of deck composition scores (continuity with v1.1–v1.3)
    macro_archetype_score    mean of the per-archetype means: every archetype weighs the same
    weakest_archetype        lowest archetype mean (with its n)
    distribution             P10 / P25 / median / P75 / P90 of slide fitness
    share_slides_above_*     share of slides at or above 90 / 80 / 70
    archetype_coverage       how many archetypes are measured, and how well
    archetypes               per archetype: n, mean, median, min, P10, flags, coverage, health
    absolute_floor_breaches  absolute expectations not met (evals/archetype_gates.json)

and a metric-level diagnosis per archetype (`diagnostics_markdown`): where the points go, from the
penalty attribution of every slide (qa/archetypes.py:attribution).

Coverage decides how much a number may claim:
    n < diagnostic_below            INSUFFICIENT COVERAGE — reported, never gated, never "healthy"
    diagnostic_below ≤ n < eligible PROVISIONAL — breaches reported as warnings
    n ≥ gate_eligible_from          GATE ELIGIBLE — an enforced gate can fail the run
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATES = ROOT / "evals" / "archetype_gates.json"
INSUFFICIENT = "INSUFFICIENT COVERAGE"


def percentile(values: list[float], p: float) -> float | None:
    """Linear interpolation between closest ranks (the usual 'linear' definition)."""
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (k - lo), 1)


def load_gates(path: Path = GATES) -> dict:
    if not path.exists():
        return {"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "archetypes": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def slide_rows(results: list[dict]) -> list[dict]:
    rows = []
    for r in results:
        for sid, s in (r.get("slides") or {}).items():
            if s.get("score") is None:
                continue
            rows.append({"case": r["case"], "slide": sid, "archetype": s.get("archetype") or "?", "score": s["score"],
                         "flags": s.get("flags") or [], "attribution": s.get("attribution") or {}})
    return rows


def coverage_level(n: int, cov: dict) -> str:
    if n < cov["diagnostic_below"]:
        return INSUFFICIENT
    return "gate_eligible" if n >= cov["gate_eligible_from"] else "provisional"


RULE_OF = {"mean_floor": "mean_below_floor", "min_floor": "catastrophic_minimum", "max_share_below_floor": "too_many_slides_below_floor"}


def _health(st: dict, gate: dict | None, rules: dict | None = None) -> tuple[str, list[dict]]:
    """(health, breaches) of one archetype against its absolute gate. A breach is ENFORCED only when
    its rule is enforced (evals/archetype_gates.json `rules`) and the archetype is gate-eligible."""
    rules = rules or {}
    breaches = []
    if gate:
        floor = gate.get("mean_floor")
        if floor is not None and st["mean"] < floor:
            breaches.append({"rule": "mean_below_floor", "key": "mean_floor", "value": st["mean"], "floor": floor})
        cat = gate.get("min_floor")
        if cat is not None and st["min"] < cat:
            breaches.append({"rule": "catastrophic_minimum", "key": "min_floor", "value": st["min"], "floor": cat})
        share = gate.get("max_share_below_floor")
        if floor is not None and share is not None and st["share_below_floor"] is not None and st["share_below_floor"] > share:
            breaches.append({"rule": "too_many_slides_below_floor", "key": "max_share_below_floor", "value": st["share_below_floor"], "floor": share})
        for b in breaches:
            b["enforced"] = (rules.get(b.pop("key")) or {}).get("status") == "enforced" and st["coverage"] == "gate_eligible"
    if st["coverage"] == INSUFFICIENT:
        return INSUFFICIENT, breaches
    return ("NOT HEALTHY" if breaches else "HEALTHY"), breaches


def profile(results: list[dict], gates: dict | None = None, deck_mean: float | None = None) -> dict:
    gates = gates if gates is not None else load_gates()
    cov = gates.get("coverage") or {"diagnostic_below": 5, "gate_eligible_from": 8}
    rows = slide_rows(results)
    scores = [r["score"] for r in rows]
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["archetype"], []).append(r)
    arch = {}
    for a, rs in sorted(by.items()):
        sc = [r["score"] for r in rs]
        flags: dict[str, int] = {}
        for r in rs:
            for f in r["flags"]:
                flags[f] = flags.get(f, 0) + 1
        g = (gates.get("archetypes") or {}).get(a)
        floor = (g or {}).get("mean_floor")
        st = {"n": len(sc), "mean": round(sum(sc) / len(sc), 1), "median": percentile(sc, 50), "min": round(min(sc), 1), "p10": percentile(sc, 10),
              "flags": dict(sorted(flags.items(), key=lambda kv: -kv[1])), "coverage": coverage_level(len(sc), cov),
              "share_below_floor": round(sum(1 for x in sc if x < floor) / len(sc), 3) if floor is not None else None}
        st["health"], st["breaches"] = _health(st, g, gates.get("rules"))
        st["gate_status"] = "enforced: " + ", ".join(k for k, r in (gates.get("rules") or {}).items() if r.get("status") == "enforced") if g else "none"
        arch[a] = st
    means = {a: s["mean"] for a, s in arch.items()}
    weakest = min(means, key=means.get) if means else None
    eligible = {a: m for a, m in means.items() if arch[a]["coverage"] != INSUFFICIENT}
    weakest_cov = min(eligible, key=eligible.get) if eligible else None
    from .qa.archetypes import ARCHETYPES

    breaches = [{"archetype": a, **b} for a, s in arch.items() for b in s["breaches"]]
    return {
        "overall_score": deck_mean,
        "slide_mean": round(sum(scores) / len(scores), 1) if scores else None,
        "macro_archetype_score": round(sum(means.values()) / len(means), 1) if means else None,
        "weakest_archetype": weakest, "weakest_archetype_score": means.get(weakest), "weakest_archetype_n": arch[weakest]["n"] if weakest else None,
        "weakest_covered_archetype": weakest_cov, "weakest_covered_archetype_score": eligible.get(weakest_cov),
        "distribution": {"n": len(scores), "min": round(min(scores), 1) if scores else None, "p10": percentile(scores, 10), "p25": percentile(scores, 25),
                         "median": percentile(scores, 50), "p75": percentile(scores, 75), "p90": percentile(scores, 90)},
        "share_slides_above_90": _share(scores, 90), "share_slides_above_80": _share(scores, 80), "share_slides_above_70": _share(scores, 70),
        "archetype_coverage": {"measured": len(arch), "of": len(ARCHETYPES),
                               "gate_eligible": sorted(a for a, s in arch.items() if s["coverage"] == "gate_eligible"),
                               "provisional": sorted(a for a, s in arch.items() if s["coverage"] == "provisional"),
                               "insufficient": sorted(a for a, s in arch.items() if s["coverage"] == INSUFFICIENT),
                               "missing": sorted(set(ARCHETYPES) - set(arch)),
                               "rule": f"n < {cov['diagnostic_below']}: diagnostic only · {cov['diagnostic_below']} ≤ n < {cov['gate_eligible_from']}: provisional · n ≥ {cov['gate_eligible_from']}: gate eligible"},
        "archetypes": arch,
        "absolute_floor_breaches": breaches,
        "not_healthy": sorted(a for a, s in arch.items() if s["health"] == "NOT HEALTHY"),
    }


def _share(v: list[float], t: float) -> float | None:
    return round(sum(1 for x in v if x >= t) / len(v), 3) if v else None


def gate_failures(prof: dict, baseline_counts: dict | None = None) -> list[str]:
    """What fails a gated run: an ENFORCED absolute breach on a gate-eligible archetype, or an
    archetype losing coverage against the baseline. Provisional breaches are reported only."""
    out = [f"{b['archetype']}: {b['rule']} ({b['value']} vs {b['floor']})" for b in prof["absolute_floor_breaches"] if b.get("enforced")]
    for a, n in (baseline_counts or {}).items():
        now = (prof["archetypes"].get(a) or {}).get("n", 0)
        if now < n:
            out.append(f"{a}: coverage regression ({n} → {now} slides)")
    return out


def attribution_summary(rows: list[dict]) -> dict:
    """Mean penalty (points lost) per metric over an archetype's slides; slides where a metric was
    not scored count as 0 for it."""
    tot: dict[str, float] = {}
    for r in rows:
        for k, a in r["attribution"].items():
            tot[k] = tot.get(k, 0.0) + a["penalty"]
    n = max(1, len(rows))
    return {k: round(v / n, 1) for k, v in sorted(tot.items(), key=lambda kv: -kv[1])}


def diagnostics(results: list[dict], prof: dict | None = None) -> dict:
    prof = prof or profile(results)
    rows = slide_rows(results)
    out = {}
    for a, st in prof["archetypes"].items():
        rs = [r for r in rows if r["archetype"] == a]
        out[a] = {"n": st["n"], "mean": st["mean"], "min": st["min"], "health": st["health"],
                  "penalty_by_metric": attribution_summary(rs),
                  "dominant_flags": {f: round(c / st["n"], 2) for f, c in st["flags"].items()},
                  "worst_slides": [f"{r['case']}/{r['slide']} {r['score']}" for r in sorted(rs, key=lambda r: r["score"])[:5]]}
    return out


def diagnostics_markdown(results: list[dict], prof: dict | None = None, title: str = "Archetype diagnostics") -> str:
    prof = prof or profile(results)
    d = diagnostics(results, prof)
    L = [f"# {title}", "", "Per archetype: where the composition points go (mean penalty per metric from the score attribution), which "
         "flags dominate, and the worst slides. Low scores must be explained before anything is changed: is the SLIDE bad, or is the METRIC wrong?", ""]
    for a, x in sorted(d.items(), key=lambda kv: kv[1]["mean"]):
        L += [f"## {a.upper()}", "", f"n slides: {x['n']} · mean: {x['mean']} · min: {x['min']} · {x['health']}", ""]
        if x["penalty_by_metric"]:
            L += ["penalty contribution (points, mean per slide):", "", "| metric | points |", "|---|---|"]
            L += [f"| {k} | −{v} |" for k, v in x["penalty_by_metric"].items() if v >= 0.05]
            L.append("")
        if x["dominant_flags"]:
            L += ["dominant flags: " + ", ".join(f"`{f}` {int(round(s * 100))}%" for f, s in x["dominant_flags"].items()), ""]
        L += ["worst slides: " + ", ".join(x["worst_slides"]), ""]
    return "\n".join(L) + "\n"


def profile_markdown(p: dict) -> list[str]:
    d = p["distribution"]
    cov = p["archetype_coverage"]
    L = ["## Quality profile", "", "| signal | value |", "|---|---|",
         f"| overall (mean of decks, historical) | {p['overall_score']} |", f"| slide mean | {p['slide_mean']} |",
         f"| macro archetype (each archetype weighs the same) | **{p['macro_archetype_score']}** |",
         f"| weakest archetype | **{p['weakest_archetype']}** {p['weakest_archetype_score']} (n={p['weakest_archetype_n']}) |",
         f"| weakest archetype with sufficient coverage | {p['weakest_covered_archetype']} {p['weakest_covered_archetype_score']} |",
         f"| slide P10 / P25 / median / P75 / P90 | **{d['p10']}** / {d['p25']} / {d['median']} / {d['p75']} / {d['p90']} |",
         f"| slides ≥ 90 / ≥ 80 / ≥ 70 | {p['share_slides_above_90']} / {p['share_slides_above_80']} / {p['share_slides_above_70']} |",
         f"| archetypes measured | {cov['measured']} of {cov['of']} (gate eligible {len(cov['gate_eligible'])}, provisional {len(cov['provisional'])}, insufficient {len(cov['insufficient'])}) |",
         f"| absolute floor breaches | {len(p['absolute_floor_breaches'])} ({sum(1 for b in p['absolute_floor_breaches'] if b.get('enforced'))} enforced) |",
         "", f"Coverage rule: {cov['rule']}.", "",
         "| archetype | n | mean | median | min | P10 | coverage | health | gate | flags |", "|---|---|---|---|---|---|---|---|---|---|"]
    for a, s in sorted(p["archetypes"].items(), key=lambda kv: kv[1]["mean"]):
        fl = ", ".join(f"{k}×{v}" for k, v in s["flags"].items()) or "—"
        L.append(f"| {a} | {s['n']} | {s['mean']} | {s['median']} | {s['min']} | {s['p10']} | {s['coverage']} | {s['health']} | {s['gate_status']} | {fl} |")
    if p["absolute_floor_breaches"]:
        L += ["", "Absolute floor breaches:", ""]
        L += [f"- {b['archetype']}: {b['rule']} ({b['value']} vs {b['floor']}){' — ENFORCED' if b.get('enforced') else ' — provisional, reported only'}"
              for b in p["absolute_floor_breaches"]]
    return L + [""]


def archetype_sheets(results: list[dict], run_root: Path, out_dir: Path, archetypes: list[str] | None = None, below: float = 80.0, cols: int = 3) -> list[Path]:
    """One contact sheet per archetype (worst slide first, score and flags printed on each tile):
    the visual evidence needed to decide whether the slide or the metric is wrong."""
    from PIL import Image, ImageDraw

    rows = slide_rows(results)
    by: dict[str, list[dict]] = {}
    for r in rows:
        by.setdefault(r["archetype"], []).append(r)
    if archetypes is None:
        archetypes = [a for a, rs in by.items() if sum(x["score"] for x in rs) / len(rs) < below]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    tw, th = 640, 360
    for a in archetypes:
        rs = sorted(by.get(a, []), key=lambda r: r["score"])
        tiles = []
        for r in rs:
            run = run_root / r["case"]
            try:
                ids = [s.get("id") for s in json.loads((run / "resolved.json").read_text())["slides"]]
                png = run / "renders" / f"slide-{ids.index(r['slide']) + 1:02d}.png"
                im = Image.open(png).convert("RGB").resize((tw, th))
            except (OSError, ValueError, KeyError):
                continue
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, th - 22, tw, th], fill=(20, 20, 20))
            dr.text((6, th - 18), f"{r['case']}/{r['slide']}  {r['score']}  {' '.join(r['flags'])}", fill=(255, 220, 80))
            tiles.append(im)
        if not tiles:
            continue
        nrows = -(-len(tiles) // cols)
        sheet = Image.new("RGB", (cols * (tw + 8) + 8, nrows * (th + 8) + 8), (200, 200, 200))
        for i, im in enumerate(tiles):
            sheet.paste(im, (8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 8)))
        p = out_dir / f"sheet_{a}.png"
        sheet.save(p)
        paths.append(p)
    return paths
