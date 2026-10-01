"""Visual-quality evals in three separate layers (docs/EVALS.md).

    REGRESSION  evals/regression/cases   the development set: visible, used while building,
                                         gates CI against evals/regression/baseline.json
    HOLDOUT     evals/holdout/public     unseen cases: never used to tune weights, thresholds or
                                         archetype profiles; run at milestones, REPORTED, never gated
                                         and never baselined
                .private/holdouts/*      private corporate holdouts (cpe holdout private)
    HUMAN       evals/human_reference    blind A/B preference votes (cpe human …): an independent
                                         signal, never part of the automatic score

Each case is a deck spec that stresses one weak spot. The runner generates, renders and QA-checks
every case, measures composition (qa/composition.py: archetype fitness + the v1.1 universal score
for continuity) and records the environment manifest (environment.py).

A regression run FAILS (exit 1) when any case
  * crashes, cannot be built or cannot be rendered,
  * has more QA errors than its baseline,
  * loses more than `tolerance` composition points (deck) or 2×tolerance (slide), or
  * gains a composition flag on a slide that did not have it.
`--update-baseline` records the current results as the new reference (regression suite only).
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from . import __version__
from .pipeline import run
from .spec import load_spec

TOLERANCE = 2.0
# QA errors about the WRITING (storyline, headline wording) rather than the rendered slide: counted
# apart in reports so authoring lint in fixture decks does not read as a visual defect
AUTHORING_CODES = ("STORY_", "HEADLINE_")
ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / "evals" / "results" / "latest.json"

SUITES = {
    "regression": {"cases": "evals/regression/cases", "baseline": "evals/regression/baseline.json", "gate": True},
    "holdout": {"cases": "evals/holdout/public", "baseline": None, "gate": False},
    "examples": {"cases": None, "baseline": None, "gate": True, "decks": {
        "alvora": "examples/alvora/deck.json",
        "gallery": "examples/gallery/deck.json",
        "alvora_on_kestrel": "examples/brand/alvora_on_kestrel.json",
    }},
}


def run_case(path: Path, out_dir: Path, compose: bool = True, name: str | None = None, max_iter: int = 2) -> dict:
    t0 = time.time()
    res = {"case": name or path.stem, "ok": False}
    try:
        spec = load_spec(path)
        res["purpose"] = (spec.get("eval") or {}).get("purpose", "")
        rep = run(spec, out_dir / res["case"], max_iter=max_iter, verbose=False, compose=compose)
        comp = rep.get("composition") or {}
        res.update(
            ok=bool(rep.get("artifacts", {}).get("pngs")),
            qa_passed=rep["passed"],
            qa_errors=rep["counts"]["error"],
            qa_errors_authoring=sum(1 for i in rep.get("issues") or [] if i.get("level") == "error" and str(i.get("code", "")).startswith(AUTHORING_CODES)),
            qa_warnings=rep["counts"]["warning"],
            qa_score=rep["deck_score"],
            composition=comp.get("deck_score"),
            composition_v1=comp.get("deck_score_v1"),
            slides={s["slide_id"]: {"score": s["score"], "archetype": s.get("archetype"), "flags": s["flags"], "v1": s.get("score_v1"),
                    "attribution": s.get("attribution") or {}} for s in comp.get("slides", [])},
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


def _cases(suite: str, cases_dir: str | Path | None, match: str | None = None) -> list[tuple[str, Path]]:
    cfg = SUITES[suite]
    if cfg.get("decks") and not cases_dir:
        out = [(n, ROOT / p) for n, p in cfg["decks"].items()]
    else:
        d = Path(cases_dir) if cases_dir else ROOT / cfg["cases"]
        out = [(p.stem, p) for p in sorted(d.glob("*.json")) if p.name != "SEAL.json"]
    return [c for c in out if not match or match in c[0]]


def _aggregate(results: list[dict]) -> dict:
    comps = [r["composition"] for r in results if r.get("composition") is not None]
    v1 = [r["composition_v1"] for r in results if r.get("composition_v1") is not None]
    flags: dict[str, int] = {}
    arche: dict[str, list] = {}
    for r in results:
        for s in (r.get("slides") or {}).values():
            for f in s["flags"]:
                flags[f] = flags.get(f, 0) + 1
            arche.setdefault(s.get("archetype") or "?", []).append(s["score"])
    return {
        "suite_composition": round(sum(comps) / len(comps), 1) if comps else None,
        "suite_composition_v1": round(sum(v1) / len(v1), 1) if v1 else None,
        "flag_counts": dict(sorted(flags.items(), key=lambda kv: -kv[1])),
        "by_archetype": {k: {"slides": len(v), "mean": round(sum(v) / len(v), 1)} for k, v in sorted(arche.items())},
        "slides_measured": sum(len(r.get("slides") or {}) for r in results),
        "qa_errors": sum(r.get("qa_errors") or 0 for r in results),
        "qa_errors_authoring": sum(r.get("qa_errors_authoring") or 0 for r in results),
        "qa_warnings": sum(r.get("qa_warnings") or 0 for r in results),
        "cases_ok": sum(1 for r in results if r.get("ok")),
        "cases_total": len(results),
    }


def run_suite(cases_dir: str | Path | None, out_dir: str | Path, baseline_path: str | Path | None = None, update_baseline: bool = False, compose: bool = True,
              tolerance: float = TOLERANCE, suite: str = "regression", record: bool = False, match: str | None = None) -> dict:
    from . import environment

    if suite not in SUITES:
        raise ValueError(f"unknown suite {suite!r} (choose from {', '.join(SUITES)})")
    cfg = SUITES[suite]
    if update_baseline and not cfg["baseline"]:
        raise ValueError(f"the {suite} suite has no baseline: holdout results are reported, never baselined (docs/EVALS.md)")
    if baseline_path is None and cfg["baseline"]:
        baseline_path = ROOT / cfg["baseline"]
    env = environment.manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    if match and (record or update_baseline):
        raise ValueError("--match runs a subset: it cannot record results or update the baseline")
    for name, c in _cases(suite, cases_dir, match):
        r = run_case(c, out, compose=compose, name=name, max_iter=3 if suite == "examples" else 2)
        results.append(r)
        print(f"[eval:{suite}] {r['case']:28} {'ok ' if r.get('ok') else 'ERR'} composition={r.get('composition')} qa_errors={r.get('qa_errors')} ({r['seconds']}s)", flush=True)
    from . import quality
    from .qa.composition import SCORE_NAME

    summary = {"suite": suite, "version": __version__, "metric": SCORE_NAME, **_aggregate(results), "cases": results, "environment": env}
    summary["quality"] = quality.profile(results, deck_mean=summary["suite_composition"])
    regressions, improvements, env_notes = [], [], []
    if baseline_path and Path(baseline_path).exists() and not update_baseline:
        base = json.loads(Path(baseline_path).read_text())
        regressions, improvements = compare(results, base, tolerance)
        regressions += quality.gate_failures(summary["quality"], None if match else base.get("archetype_counts"))
        if base.get("environment_fingerprint") and base["environment_fingerprint"] != env["fingerprint"]:
            env_notes.append(f"Environment differs from the baseline's ({base['environment_fingerprint']} → {env['fingerprint']}): "
                             "differences may come from the renderer/fonts, not the engine. Use `scripts/cpe-docker eval` for comparable numbers.")
    if suite == "examples":
        regressions += [f"{r['case']}: QA gate failed ({r.get('qa_errors')} errors)" for r in results if r.get("ok") and not r.get("qa_passed")]
    summary["regressions"] = regressions
    summary["improvements"] = improvements
    summary["environment_notes"] = env_notes
    summary["passed"] = all(r.get("ok") for r in results) and not (cfg["gate"] and regressions)
    if update_baseline and baseline_path:
        slim = {"suite_composition": summary["suite_composition"], "environment_fingerprint": env["fingerprint"], "engine_version": __version__,
                "archetype_counts": {a: st["n"] for a, st in summary["quality"]["archetypes"].items()},
                "cases": [{**{k: r.get(k) for k in ("case", "ok", "qa_errors", "composition")},
                           "slides": {sid: {k: v for k, v in sl.items() if k != "attribution"} for sid, sl in (r.get("slides") or {}).items()}} for r in results]}
        Path(baseline_path).write_text(json.dumps(slim, indent=2) + "\n")
    (out / "eval_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (out / "eval_report.md").write_text(to_markdown(summary))
    (out / "archetype_diagnostics.md").write_text(quality.diagnostics_markdown(results, summary["quality"], f"Archetype diagnostics — {suite}"))
    if suite != "holdout_v2":  # sealed holdout renders are not opened during development
        quality.archetype_sheets(results, out, out / "archetype_sheets")
    if record:
        record_result(suite, summary)
    return summary


def _slim(summary: dict) -> dict:
    keep = ("suite_composition", "suite_composition_v1", "slides_measured", "qa_errors", "qa_errors_authoring", "qa_warnings", "cases_ok", "cases_total", "by_archetype", "flag_counts", "passed")
    from .qa.composition import SCORE_NAME

    out = {"metric": summary.get("metric") or SCORE_NAME, **{k: summary.get(k) for k in keep}}
    out["cases"] = {r["case"]: {"composition": r.get("composition"), "qa_score": r.get("qa_score"), "qa_errors": r.get("qa_errors"),
                                "qa_warnings": r.get("qa_warnings"), "qa_passed": r.get("qa_passed")} for r in summary["cases"]}
    q = summary.get("quality") or {}
    if q:
        out["overall"] = {k: q.get(k) for k in ("overall_score", "slide_mean", "macro_archetype_score", "weakest_archetype", "weakest_archetype_score",
                                                "weakest_archetype_n", "weakest_covered_archetype", "weakest_covered_archetype_score",
                                                "share_slides_above_90", "share_slides_above_80", "share_slides_above_70")}
        out["overall"]["qa_errors"] = summary.get("qa_errors")
        out["overall"]["qa_errors_visual"] = (summary.get("qa_errors") or 0) - (summary.get("qa_errors_authoring") or 0)
        out["distribution"] = q.get("distribution")
        out["archetypes"] = {a: {k: v for k, v in st.items() if k != "breaches"} for a, st in (q.get("archetypes") or {}).items()}
        out["absolute_gates"] = {"breaches": q.get("absolute_floor_breaches"), "not_healthy": q.get("not_healthy"), "coverage": q.get("archetype_coverage")}
        out.pop("by_archetype", None)
    out["environment_fingerprint"] = summary["environment"]["fingerprint"]
    out["engine"] = {"version": summary["environment"].get("cpe_version"), "commit": summary["environment"].get("commit")}
    return out


def record_result(section: str, summary: dict, path: Path = LATEST) -> dict:
    """Write one signal into evals/results/latest.json — the single source of truth for current numbers."""
    data = json.loads(path.read_text()) if path.exists() else {}
    data["version"] = __version__
    if section in ("regression", "examples"):
        data[section] = _slim(summary)
    elif section == "holdout":
        data.setdefault("holdout", {})["public"] = _slim(summary)
    elif section == "holdout_private":  # sanitized aggregates only
        data.setdefault("holdout", {})["private"] = summary
    else:
        data[section] = summary
    if "environment" in summary:
        env = dict(summary["environment"])
        env.pop("installed_font_families", None)
        data["environment"] = env
    data.setdefault("holdout", {}).setdefault("public", None)
    data["holdout"].setdefault("private", {"status": "private corporate holdouts run outside the public repo; only sanitized aggregates are recorded here"})
    data.setdefault("human_reference", {"status": "no votes imported yet"})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return data


def to_markdown(s: dict) -> str:
    L = [f"# Visual-quality eval report — {s['suite']}", ""]
    L.append(f"**Verdict:** {'✅ PASSED' if s['passed'] else '❌ FAILED'} · **Composition (archetype fitness):** {s['suite_composition']}/100 · "
             f"v1.1 universal score: {s.get('suite_composition_v1')} · slides measured: {s['slides_measured']}")
    if s["suite"] == "holdout":
        L += ["", "> Holdout: reported, never gated, never baselined. Do not tune weights, thresholds or archetype profiles on these cases (docs/EVALS.md)."]
    L.append("")
    for n in s.get("environment_notes") or []:
        L += [f"> ⚠️ {n}", ""]
    if s["regressions"]:
        L += ["## Regressions", ""] + [f"- {x}" for x in s["regressions"]] + [""]
    if s["improvements"]:
        L += ["## Improvements vs baseline", ""] + [f"- {x}" for x in s["improvements"]] + [""]
    if s.get("quality"):
        from .quality import profile_markdown

        L += profile_markdown(s["quality"])
    L += ["## Cases", "", "| case | purpose | composition | v1.1 score | QA errors | QA warnings | author actions | flags |", "|---|---|---|---|---|---|---|---|"]
    for r in s["cases"]:
        fl = sorted({f for sl in (r.get("slides") or {}).values() for f in sl["flags"]})
        L.append(f"| `{r['case']}` | {r.get('purpose', '')} | {r.get('composition')} | {r.get('composition_v1')} | {r.get('qa_errors')} | {r.get('qa_warnings')} | {r.get('pending')} | {', '.join(fl) or '—'} |")
    L += ["", "## By archetype", "", "| archetype | slides | mean fitness |", "|---|---|---|"]
    L += [f"| {k} | {v['slides']} | {v['mean']} |" for k, v in s.get("by_archetype", {}).items()]
    L += ["", "## Composition flags across the suite", ""]
    for f, n in s["flag_counts"].items():
        L.append(f"- `{f}`: {n} slide(s)")
    e = s.get("environment") or {}
    L += ["", "## Environment", "", f"- engine {e.get('cpe_version')} · commit `{e.get('commit')}` · container `{e.get('container_image')}`",
          f"- {e.get('os')} · Python {e.get('python')} · {e.get('libreoffice')} · fontconfig {e.get('fontconfig')}",
          f"- render fingerprint `{e.get('fingerprint')}`", "", "Metric definitions: `src/cpe/qa/composition.py`, profiles: `src/cpe/qa/archetypes.py`."]
    return "\n".join(L) + "\n"
