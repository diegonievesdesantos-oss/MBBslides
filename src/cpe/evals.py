"""Visual-quality evals: a reproducible benchmark that makes quality testable.

Each case in `evals/cases/*.json` is a deck spec designed to stress one weak
spot (sparse content, text overload, big/small tables, many series, long
numbers, Spanish, dense diagrams, waterfalls, long headlines…). The runner
generates, renders and QA-checks every case, measures composition
(qa/composition.py) and compares against a committed baseline.

A run FAILS (exit 1) when any case
  * crashes, cannot be built or cannot be rendered,
  * has more QA errors than its baseline,
  * loses more than `tolerance` composition points (deck or any slide), or
  * gains a composition flag on a slide that did not have it.
`--update-baseline` records the current results as the new reference.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from .pipeline import run
from .spec import load_spec

TOLERANCE = 2.0


def run_case(path: Path, out_dir: Path, compose: bool = True) -> dict:
    t0 = time.time()
    res = {"case": path.stem, "ok": False}
    try:
        spec = load_spec(path)
        res["purpose"] = (spec.get("eval") or {}).get("purpose", "")
        rep = run(spec, out_dir / path.stem, max_iter=2, verbose=False, compose=compose)
        comp = rep.get("composition") or {}
        res.update(
            ok=bool(rep.get("artifacts", {}).get("pngs")),
            qa_passed=rep["passed"],
            qa_errors=rep["counts"]["error"],
            qa_warnings=rep["counts"]["warning"],
            qa_score=rep["deck_score"],
            composition=comp.get("deck_score"),
            slides={s["slide_id"]: {"score": s["score"], "flags": s["flags"]} for s in comp.get("slides", [])},
            pending=len(rep.get("pending_actions") or []),
        )
        if not res["ok"]:
            res["error"] = "not rendered"
    except Exception as e:  # a crash is a result, not an abort
        res["error"] = f"{type(e).__name__}: {e}"
        res["trace"] = traceback.format_exc()[-2000:]
    res["seconds"] = round(time.time() - t0, 1)
    return res


def compare(results: list[dict], baseline: dict, tolerance: float = TOLERANCE) -> tuple[list[str], list[str]]:
    regressions, improvements = [], []
    base = {c["case"]: c for c in baseline.get("cases", [])}
    for r in results:
        name = r["case"]
        if not r.get("ok"):
            regressions.append(f"{name}: failed to build/render ({r.get('error')})")
            continue
        b = base.get(name)
        if not b:
            continue
        if r["qa_errors"] > b.get("qa_errors", 0):
            regressions.append(f"{name}: QA errors {b.get('qa_errors', 0)} → {r['qa_errors']}")
        if r["composition"] is not None and b.get("composition") is not None:
            d = r["composition"] - b["composition"]
            if d < -tolerance:
                regressions.append(f"{name}: composition {b['composition']} → {r['composition']} ({d:+.1f})")
            elif d > tolerance:
                improvements.append(f"{name}: composition {b['composition']} → {r['composition']} ({d:+.1f})")
        for sid, s in (r.get("slides") or {}).items():
            bs = (b.get("slides") or {}).get(sid)
            if not bs:
                continue
            if s["score"] < bs["score"] - tolerance * 2:
                regressions.append(f"{name}/{sid}: slide composition {bs['score']} → {s['score']}")
            new = set(s["flags"]) - set(bs["flags"])
            if new:
                regressions.append(f"{name}/{sid}: new flags {sorted(new)}")
            gone = set(bs["flags"]) - set(s["flags"])
            if gone:
                improvements.append(f"{name}/{sid}: fixed {sorted(gone)}")
    return regressions, improvements


def run_suite(cases_dir: str | Path, out_dir: str | Path, baseline_path: str | Path | None = None, update_baseline: bool = False, compose: bool = True, tolerance: float = TOLERANCE) -> dict:
    cases = sorted(Path(cases_dir).glob("*.json"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for c in cases:
        r = run_case(c, out, compose=compose)
        results.append(r)
        print(f"[eval] {r['case']:28} {'ok ' if r.get('ok') else 'ERR'} composition={r.get('composition')} qa_errors={r.get('qa_errors')} ({r['seconds']}s)", flush=True)
    comps = [r["composition"] for r in results if r.get("composition") is not None]
    flags: dict[str, int] = {}
    for r in results:
        for s in (r.get("slides") or {}).values():
            for f in s["flags"]:
                flags[f] = flags.get(f, 0) + 1
    summary = {
        "suite_composition": round(sum(comps) / len(comps), 1) if comps else None,
        "cases": results,
        "flag_counts": dict(sorted(flags.items(), key=lambda kv: -kv[1])),
        "slides_measured": sum(len(r.get("slides") or {}) for r in results),
    }
    regressions, improvements = [], []
    if baseline_path and Path(baseline_path).exists() and not update_baseline:
        regressions, improvements = compare(results, json.loads(Path(baseline_path).read_text()), tolerance)
    summary["regressions"] = regressions
    summary["improvements"] = improvements
    summary["passed"] = all(r.get("ok") for r in results) and not regressions
    if update_baseline and baseline_path:
        slim = {"suite_composition": summary["suite_composition"], "cases": [{k: r.get(k) for k in ("case", "ok", "qa_errors", "composition", "slides")} for r in results]}
        Path(baseline_path).write_text(json.dumps(slim, indent=2))
    (out / "eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (out / "eval_report.md").write_text(to_markdown(summary))
    return summary


def to_markdown(s: dict) -> str:
    L = ["# Visual-quality eval report", ""]
    L.append(f"**Verdict:** {'✅ PASSED' if s['passed'] else '❌ FAILED'} · **Suite composition:** {s['suite_composition']}/100 · slides measured: {s['slides_measured']}")
    L.append("")
    if s["regressions"]:
        L += ["## Regressions", ""] + [f"- {x}" for x in s["regressions"]] + [""]
    if s["improvements"]:
        L += ["## Improvements vs baseline", ""] + [f"- {x}" for x in s["improvements"]] + [""]
    L += ["## Cases", "", "| case | purpose | composition | QA errors | QA warnings | author actions | flags |", "|---|---|---|---|---|---|---|"]
    for r in s["cases"]:
        fl = sorted({f for sl in (r.get("slides") or {}).values() for f in sl["flags"]})
        L.append(f"| `{r['case']}` | {r.get('purpose', '')} | {r.get('composition')} | {r.get('qa_errors')} | {r.get('qa_warnings')} | {r.get('pending')} | {', '.join(fl) or '—'} |")
    L += ["", "## Composition flags across the suite", ""]
    for f, n in s["flag_counts"].items():
        L.append(f"- `{f}`: {n} slide(s)")
    L += ["", "Metric definitions: `src/cpe/qa/composition.py`."]
    return "\n".join(L) + "\n"
