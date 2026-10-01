"""Metamorphic robustness evaluation (v1.4).

    Does a small content change cause a catastrophic visual-quality collapse?

Each SEED is a valid development slide (evals/robustness/seeds.json points at slides of the
regression suite). PERTURBATIONS make small, realistic edits to it — a 20% longer headline, two
more process steps, a table 6 → 9 rows, two more chart series, longer (translated-length) text,
"€1.2M" → "€1,200,000", one source → three. The seed and its variants are rendered in one deck
(separated by dividers, so layout-monotony rules do not couple them) and compared:

    score delta     archetype-fitness composition change (variant − seed)
    layout change   the composed layout id differs from the seed's
    font change     the smallest body font size drops by ≥ 2 pt
    QA              new visual QA errors on the variant (overflow, collision, clipping, …)
    flags           composition flags the seed did not have

A variant is CATASTROPHIC when its score drops by ≥ CATASTROPHIC_DROP points or it gains a visual
QA error. The run reports median and P90 quality drop and the catastrophic rate. This signal is
SEPARATE from the composition score (never averaged into it) and gates CI only against its own
baseline (evals/robustness/baseline.json): more catastrophic variants than recorded fails.

    cpe robustness [-o out/robustness] [--update-baseline] [--record]
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEEDS = ROOT / "evals" / "robustness" / "seeds.json"
BASELINE = ROOT / "evals" / "robustness" / "baseline.json"
CATASTROPHIC_DROP = 25.0
VISUAL_QA = ("TEXT_OVERFLOW", "TEXT_COLLISION", "RENDER_TEXT_COLLISION", "RENDER_TEXT_SPILL", "RENDER_OFF_SLIDE", "RENDER_LABEL_TRUNCATED", "RENDER_SMALL_TEXT")

LONGER = " across all regions, with the largest effect in the second half of the year"
LONGER_ES = " en todas las regiones, con el mayor efecto en la segunda mitad del año"


def _visual(s: dict) -> dict:
    return s.get("visual") if isinstance(s.get("visual"), dict) else {}


def _data(s: dict) -> dict:
    v = _visual(s)
    return v.get("data") if isinstance(v.get("data"), dict) else v


def _spanish(s: dict) -> bool:
    return bool(re.search(r"[áéíóúñ¿¡]", json.dumps(s, ensure_ascii=False)))


# ── perturbations: each returns a modified copy, or None when it does not apply ──────────────────

def headline_longer(s: dict) -> dict | None:
    """+~20% words in the headline."""
    if not s.get("headline"):
        return None
    out = copy.deepcopy(s)
    words = out["headline"].split()
    extra = (LONGER_ES if _spanish(s) else LONGER).split()[: max(2, len(words) // 5 + 1)]
    out["headline"] = out["headline"].rstrip(".") + " " + " ".join(extra)
    return out


def text_longer(s: dict) -> dict | None:
    """All body text ~25% longer — the typical English → Spanish expansion."""
    out = copy.deepcopy(s)
    changed = False

    def grow(t: str) -> str:
        nonlocal changed
        if not isinstance(t, str) or len(t.split()) < 2:
            return t
        changed = True
        w = t.split()
        return t + " " + " ".join(w[: max(1, len(w) // 4)]).lower()

    d = _data(out)
    for key in ("points", "steps", "items", "events"):
        coll = d.get(key) if isinstance(d, dict) else None
        for i, it in enumerate(coll or []):
            if isinstance(it, str):
                coll[i] = grow(it)
            elif isinstance(it, dict):
                for f in ("text", "title", "label"):
                    if f in it:
                        it[f] = grow(it[f])
    for col in out.get("columns") or []:
        col["points"] = [grow(p) for p in col.get("points") or []]
    if isinstance(out.get("commentary"), dict):
        out["commentary"]["points"] = [grow(p) for p in out["commentary"].get("points") or []]
    return out if changed else None


def more_steps(s: dict) -> dict | None:
    """Process: +2 steps."""
    v = _visual(s)
    if v.get("type") not in ("process", "value_chain"):
        return None
    out = copy.deepcopy(s)
    st = _data(out)["steps"]
    for k in range(2):
        proto = copy.deepcopy(st[-1])
        proto["title"] = f"{proto.get('title', 'Step')} {k + 2}"
        st.append(proto)
    return out


def more_rows(s: dict) -> dict | None:
    """Table: ×1.5 rows (6 → 9)."""
    v = _visual(s)
    if not v.get("rows") or not isinstance(v["rows"][0], list):
        return None
    out = copy.deepcopy(s)
    rows = _visual(out)["rows"]
    n = len(rows)
    for i in range(max(1, n // 2)):
        r = copy.deepcopy(rows[i % n])
        r[0] = f"{r[0]} (B)"
        rows.append(r)
    return out


def more_series(s: dict) -> dict | None:
    """Category chart: +2 series."""
    v = _visual(s)
    d = _data(s)
    if v.get("type") not in ("column", "bar", "line", "stacked_column", "stacked_bar") or not d.get("series"):
        return None
    out = copy.deepcopy(s)
    ser = _data(out)["series"]
    base = ser[0]["values"]
    for k, f in enumerate((0.8, 0.6)):
        ser.append({"name": f"Series {len(ser) + 1}", "values": [round(x * f, 1) if isinstance(x, (int, float)) else x for x in base]})
    return out


def full_numbers(s: dict) -> dict | None:
    """'€1.2M' → '€1,200,000' (and 'k' / 'bn') in the headline and KPI values."""
    rx = re.compile(r"([€$£]?)(\d+(?:\.\d+)?)\s?(k|M|bn)\b")
    mult = {"k": 1e3, "M": 1e6, "bn": 1e9}

    def full(t):
        return rx.sub(lambda m: f"{m.group(1)}{int(round(float(m.group(2)) * mult[m.group(3)])):,}", t) if isinstance(t, str) else t

    out = copy.deepcopy(s)
    before = json.dumps(out, ensure_ascii=False)
    if out.get("headline"):
        out["headline"] = full(out["headline"])
    for it in (_data(out).get("items") or []) if isinstance(_data(out), dict) else []:
        if isinstance(it, dict) and "value" in it:
            it["value"] = full(str(it["value"]))
    return out if json.dumps(out, ensure_ascii=False) != before else None


def more_sources(s: dict) -> dict | None:
    """One source → three sources."""
    if s.get("kind", "content") != "content" or not s.get("source"):
        return None
    out = copy.deepcopy(s)
    out["source"] = f"{s['source']}; company annual reports 2023–2025; team analysis of 14 interviews and market model (illustrative)"
    return out


def more_items(s: dict) -> dict | None:
    """Lists, KPI sets, comparison columns, timelines: +1 item."""
    out = copy.deepcopy(s)
    if out.get("columns"):
        out["columns"].append({"title": "Option D", "points": ["Medium cost", "18 months", "Partial control"]})
        return out
    d = _data(out)
    for key in ("points", "items", "events"):
        coll = d.get(key) if isinstance(d, dict) else None
        if coll:
            coll.append(copy.deepcopy(coll[-1]))
            return out
    return None


PERTURBATIONS = {f.__name__: f for f in (headline_longer, text_longer, more_steps, more_rows, more_series, full_numbers, more_sources, more_items)}


# ── running ──────────────────────────────────────────────────────────────────────────────────────

def load_seeds(path: Path = SEEDS) -> list[dict]:
    """[{case, slide, theme, slide_spec}] resolved from the seed references."""
    ref = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in ref["seeds"]:
        spec = json.loads((ROOT / "evals" / "regression" / "cases" / f"{r['case']}.json").read_text(encoding="utf-8"))
        s = next(x for x in spec["slides"] if x.get("id") == r["slide"])
        out.append({"case": r["case"], "slide": r["slide"], "meta": spec["meta"], "storyline": spec.get("storyline"), "spec": s})
    return out


def _deck(seed: dict, variants: list[tuple[str, dict]]) -> dict:
    slides = [{**copy.deepcopy(seed["spec"]), "id": "seed", "layout": "auto"}]
    for i, (name, v) in enumerate(variants):
        slides.append({"id": f"div{i}", "kind": "divider", "title": name})
        slides.append({**v, "id": f"v_{name}", "layout": "auto"})
    return {"meta": {**seed["meta"], "title": f"robustness {seed['case']}/{seed['slide']}"}, "storyline": seed.get("storyline"), "slides": slides}


def _slide_facts(run_dir: Path, rep: dict) -> dict:
    res = json.loads((run_dir / "resolved.json").read_text())
    layouts = {s.get("id"): ((s.get("_plan") or {}).get("layout") or {}).get("id") for s in res["slides"]}
    comp = {c["slide_id"]: c for c in (rep.get("composition") or {}).get("slides", [])}
    qa: dict = {}
    for i in rep.get("issues") or []:
        if i.get("level") == "error" and str(i.get("code", "")).startswith(VISUAL_QA) and i.get("slide"):
            qa.setdefault(i["slide"], []).append(i["code"])
    out = {}
    for sid, c in comp.items():
        sizes = (c.get("raw") or {}).get("body_font_sizes") or []
        out[sid] = {"score": c["score"], "flags": c["flags"], "layout": layouts.get(sid), "min_font": min(sizes) if sizes else None, "visual_qa": qa.get(sid, [])}
    return out


def run(out_dir: str | Path, seeds_path: Path = SEEDS) -> dict:
    from .pipeline import run as pipeline_run

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in load_seeds(seeds_path):
        variants = [(n, v) for n, f in PERTURBATIONS.items() if (v := f(seed["spec"])) is not None]
        name = f"{seed['case']}__{seed['slide']}"
        rep = pipeline_run(_deck(seed, variants), out / name, max_iter=1, verbose=False, compose=True)
        facts = _slide_facts(out / name, rep)
        base = facts.get("seed")
        if not base:
            continue
        for n, _ in variants:
            v = facts.get(f"v_{n}")
            if not v:
                rows.append({"seed": name, "perturbation": n, "error": "not measured"})
                continue
            delta = round(v["score"] - base["score"], 1)
            new_qa = sorted(set(v["visual_qa"]) - set(base["visual_qa"]))
            font_drop = (base["min_font"] - v["min_font"]) if base["min_font"] and v["min_font"] else 0
            rows.append({"seed": name, "perturbation": n, "seed_score": base["score"], "score": v["score"], "delta": delta,
                         "layout_change": v["layout"] != base["layout"], "font_drop": font_drop, "new_visual_qa": new_qa,
                         "new_flags": sorted(set(v["flags"]) - set(base["flags"])),
                         "catastrophic": delta <= -CATASTROPHIC_DROP or bool(new_qa)})
        print(f"[robustness] {name:40} {len(variants)} variants", flush=True)
    summary = summarize(rows)
    (out / "robustness_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (out / "robustness_report.md").write_text(to_markdown(summary))
    return summary


def summarize(rows: list[dict]) -> dict:
    from .quality import percentile

    ok = [r for r in rows if "delta" in r]
    drops = [max(0.0, -r["delta"]) for r in ok]
    cat = [r for r in ok if r["catastrophic"]]
    by: dict = {}
    for r in ok:
        b = by.setdefault(r["perturbation"], {"n": 0, "drops": [], "catastrophic": 0, "layout_changes": 0})
        b["n"] += 1
        b["drops"].append(max(0.0, -r["delta"]))
        b["catastrophic"] += int(r["catastrophic"])
        b["layout_changes"] += int(r["layout_change"])
    return {
        "variants": len(ok), "seeds": len({r["seed"] for r in ok}),
        "median_drop": percentile(drops, 50), "p90_drop": percentile(drops, 90),
        "catastrophic": len(cat), "catastrophic_rate": round(len(cat) / len(ok), 3) if ok else None,
        "layout_change_rate": round(sum(r["layout_change"] for r in ok) / len(ok), 3) if ok else None,
        "font_drop_rate": round(sum(1 for r in ok if r["font_drop"] >= 2) / len(ok), 3) if ok else None,
        "by_perturbation": {k: {"n": v["n"], "median_drop": percentile(v["drops"], 50), "p90_drop": percentile(v["drops"], 90),
                                "catastrophic": v["catastrophic"], "layout_changes": v["layout_changes"]} for k, v in sorted(by.items())},
        "catastrophic_cases": [f"{r['seed']} · {r['perturbation']}: {r['seed_score']} → {r['score']}" + (f" (new QA {', '.join(r['new_visual_qa'])})" if r["new_visual_qa"] else "")
                               for r in cat],
        "definition": f"catastrophic = composition drop ≥ {CATASTROPHIC_DROP:g} points or a new visual QA error; separate from the composition score",
        "rows": rows,
    }


def compare(summary: dict, baseline: dict) -> list[str]:
    """CI gate: no more catastrophic variants than the recorded baseline."""
    out = []
    if summary["catastrophic"] > baseline.get("catastrophic", 0):
        out.append(f"catastrophic variants {baseline.get('catastrophic', 0)} → {summary['catastrophic']}")
    if summary["variants"] < baseline.get("variants", 0):
        out.append(f"robustness coverage regression: {baseline.get('variants')} → {summary['variants']} variants")
    return out


def to_markdown(s: dict) -> str:
    L = ["# Robustness (metamorphic) report", "", f"_{s['definition']}_", "",
         f"Seeds {s['seeds']} · variants {s['variants']} · median drop {s['median_drop']} · P90 drop {s['p90_drop']} · "
         f"catastrophic {s['catastrophic']} ({s['catastrophic_rate']}) · layout changes {s['layout_change_rate']} · font drops ≥2pt {s['font_drop_rate']}", "",
         "| perturbation | n | median drop | P90 drop | catastrophic | layout changes |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['median_drop']} | {v['p90_drop']} | {v['catastrophic']} | {v['layout_changes']} |" for k, v in s["by_perturbation"].items()]
    if s["catastrophic_cases"]:
        L += ["", "## Catastrophic variants", ""] + [f"- {c}" for c in s["catastrophic_cases"]]
    return "\n".join(L) + "\n"
