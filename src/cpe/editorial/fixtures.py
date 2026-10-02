"""Editorial fixture runner (v3.1, spec §90-94): `cpe editorial eval --set dev|holdout`.

Each fixture (evals/editorial/README.md) is turned into a minimal deck, compiled in its own mode,
and compared with the author's expectation. The signals are reported separately, never as a
composite with composition or visual scores:

    agreement                 cases whose outcome matches the expectation (per file, per language)
    valid_pass_rate           valid / faithful headlines the engine accepts (false rejections = 1 - it)
    invalid_catch_rate        failing headlines the engine rejects with an acceptable code
    unsupported_claims_passed failing numeric / causal / drift cases the engine let through
    parallel_agreement        parallel groups judged as the author judged them
    non_parallel_respected    sequences left unflagged and unchanged
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .compiler import compile_editorial
from .parallel import check, detect

ROOT = Path(__file__).resolve().parents[3]
SETS = {"dev": ROOT / "evals" / "editorial" / "dev", "holdout": ROOT / "evals" / "editorial" / "holdout"}
DECK_CODES = {"GOVERNING_THOUGHT_TOPIC", "KEYLINE_TOPIC", "KEYLINE_UNSUPPORTED", "ORPHAN_PROPOSITION", "STRIP_NO_ASK", "STRIP_NO_FACTS",
              "HEADLINE_REPEATED_OPENING", "PAGE_TURN_BACKTRACK"}


def verify_seal(d: Path) -> list[str]:
    seal = json.loads((d / "SEAL.json").read_text(encoding="utf-8"))
    have = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.glob("*.json") if p.name != "SEAL.json"}
    bad = [f"changed: {n}" for n, h in seal["files"].items() if have.get(n) not in (None, h)]
    bad += [f"missing: {n}" for n in seal["files"] if n not in have] + [f"not sealed: {n}" for n in have if n not in seal["files"]]
    return bad


def _deck(case: dict, slides: list[dict], key_line: list | None = None) -> dict:
    deck = case.get("deck") or {}
    return {"meta": {"title": "Fixture", "language": deck.get("language") or case.get("lang"), "editorial_mode": deck.get("editorial_mode", "mbb_strict"),
                     "partial": True},
            "storyline": {"governing_thought": "", "key_line": key_line or []}, "slides": slides}


def run_headline(case: dict) -> dict:
    slide = json.loads(json.dumps(case["slide"]))
    spec = _deck(case, [slide])
    out, rep = compile_editorial(spec, profile={})
    sid = slide.get("id")
    errs = [f for f in rep["findings"] if f.get("slide") == sid and f["level"] == "error" and f["code"] not in DECK_CODES and not f.get("group")]
    got = "failed" if errs else "passed"
    exp = case["expect"]
    ok = got == exp["status"]
    codes = sorted({f["code"] for f in errs})
    if ok and got == "failed" and exp.get("codes"):
        ok = bool(set(codes) & set(exp["codes"]))
    sel = None
    if exp.get("selected"):
        s2 = out["slides"][0]
        sel = s2.get("text") if s2.get("kind") == "statement" and s2.get("text") else s2.get("headline")
        ok = ok and sel == exp["selected"]
    return {"id": case["id"], "type": "headline", "lang": case.get("lang"), "tags": case.get("tags") or [], "expected": exp["status"],
            "got": got, "codes": codes, "expected_codes": exp.get("codes") or [], "ok": ok, "selected": sel,
            "messages": [f["message"] for f in errs][:4]}


CONTEXT_SLIDE = {
    "recommendations": lambda ms, ex: {"kind": "content", "message_type": "recommendation", "visual": {"type": "text_columns", "data": {"items": [{"title": m} for m in ms]}, **ex}},
    "cards": lambda ms, ex: {"kind": "content", "message_type": "recommendation", "visual": {"type": "text_columns", "data": {"items": [{"title": m} for m in ms]}, **ex}},
    "design_principles": lambda ms, ex: {"kind": "content", "archetype": "design_principles", "visual": {"type": "text_columns", "data": {"items": [{"title": m} for m in ms]}, **ex}},
    "process_steps": lambda ms, ex: {"kind": "content", "visual": {"type": "process", "data": {"steps": [{"label": m} for m in ms]}, **ex}},
    "options": lambda ms, ex: {"kind": "content", "visual": {"type": "harvey_table", "columns": ["Criteria"] + ms, "rows": [], **ex}},
    "roadmap_workstreams": lambda ms, ex: {"kind": "content", "visual": {"type": "gantt", "data": {"rows": [{"label": m} for m in ms]}, **ex}},
    "exec_summary": lambda ms, ex: {"kind": "exec_summary", "visual": {"type": "statements", "data": {"items": [{"title": m} for m in ms]}, **ex}},
}


def run_parallel(case: dict) -> dict:
    g = case["group"]
    ms = g["members"]
    ctx = g.get("context")
    ex = {"parallel_group": "G"} if g.get("explicit") else {}
    if ctx == "key_line":
        kl = [{"id": f"K{i + 1}", "message": m, **({"parallel_group": "G"} if g.get("explicit") else {})} for i, m in enumerate(ms)]
        spec = _deck(case, [], kl)
    else:
        s = CONTEXT_SLIDE.get(ctx, CONTEXT_SLIDE["recommendations"])(ms, ex)
        s.update(id="s01", headline="x")
        spec = _deck(case, [s])
    groups = [check(gr, case.get("lang")) for gr in detect(spec)]
    fs = [f for gr in groups for f in gr["findings"] if f["class"] in ("hard", "soft")]
    got = "failed" if any(f["class"] == "hard" for f in fs) else "flagged" if fs else "passed"
    exp = case["expect"]["status"]
    ok = got == exp or (exp == "flagged" and got == "failed")
    if ok and exp in ("failed", "flagged") and case["expect"].get("codes"):
        ok = bool({f["code"] for f in fs} & set(case["expect"]["codes"]))
    return {"id": case["id"], "type": "parallel", "lang": case.get("lang"), "tags": case.get("tags") or [], "expected": exp, "got": got,
            "codes": sorted({f["code"] for f in fs}), "expected_codes": case["expect"].get("codes") or [], "ok": ok, "groups": len(groups),
            "messages": [f["message"] for f in fs][:3]}


def run_sequence(case: dict) -> dict:
    slides = json.loads(json.dumps(case["slides"]))
    secs = sorted({s.get("section") for s in slides if s.get("section")})
    spec = _deck(case, slides, [{"id": k, "message": "x"} for k in secs])
    out, rep = compile_editorial(spec, profile={})
    flags = [f for f in rep["findings"] if f["code"].startswith("PARALLEL_") and f["level"] in ("error", "warning")]
    changed = [s["id"] for s, o in zip(case["slides"], out["slides"]) if s.get("headline") != o.get("headline")]
    errs = [f for f in rep["findings"] if f["level"] == "error" and f["code"] not in DECK_CODES and not f.get("group")]
    exp = case["expect"]
    ok = len(flags) <= exp.get("parallel_flags", 0) and (not exp.get("headlines_unchanged") or not changed)
    return {"id": case["id"], "type": "sequence", "lang": case.get("lang"), "tags": case.get("tags") or [], "expected": "unflagged",
            "got": "unflagged" if not flags and not changed else "flagged", "ok": ok, "parallel_flags": len(flags), "changed": changed,
            "slide_errors": sorted({f"{f['slide']}:{f['code']}" for f in errs}), "messages": [f["message"] for f in flags][:3]}


def run_set(which: str = "dev", root: Path | None = None) -> dict:
    d = root or SETS[which]
    if which == "holdout" and root is None:
        bad = verify_seal(d)
        if bad:
            raise RuntimeError("editorial holdout seal broken: " + "; ".join(bad))
    results = []
    for f in sorted(d.glob("*.json")):
        if f.name == "SEAL.json":
            continue
        for case in json.loads(f.read_text(encoding="utf-8")):
            run = {"headline": run_headline, "parallel": run_parallel, "sequence": run_sequence}[case["type"]]
            r = run(case)
            r["file"] = f.stem
            results.append(r)
    return {"set": which, "cases": len(results), "metrics": metrics(results), "results": results}


def metrics(rs: list[dict]) -> dict:
    def rate(xs):
        return round(sum(1 for x in xs if x["ok"]) / len(xs), 3) if xs else None

    head = [r for r in rs if r["type"] == "headline"]
    valid = [r for r in head if r["expected"] == "passed"]
    invalid = [r for r in head if r["expected"] == "failed"]
    unsupported = [r for r in invalid if r["file"] in ("numeric", "causality", "drift")]
    out = {
        "agreement": rate(rs), "by_file": {f: rate([r for r in rs if r["file"] == f]) for f in sorted({r["file"] for r in rs})},
        "by_language": {lg: rate([r for r in rs if r["lang"] == lg]) for lg in sorted({r["lang"] for r in rs if r["lang"]})},
        "valid_pass_rate": round(sum(r["got"] == "passed" for r in valid) / len(valid), 3) if valid else None,
        "invalid_catch_rate": rate(invalid),
        "unsupported_claims_passed": sum(r["got"] == "passed" for r in unsupported),
        "unsupported_claims_total": len(unsupported),
        "parallel_agreement": rate([r for r in rs if r["type"] == "parallel"]),
        "non_parallel_respected": rate([r for r in rs if r["type"] == "sequence"]),
        "n": {"headline": len(head), "valid": len(valid), "invalid": len(invalid), "parallel": sum(r["type"] == "parallel" for r in rs),
              "sequence": sum(r["type"] == "sequence" for r in rs)},
    }
    return out


def record(r: dict, latest: Path | None = None) -> Path:
    """evals/results/latest.json → `editorial.dev` / `editorial.holdout`: the metrics with their provenance.
    A holdout result is recorded once per release and kept as history (never overwritten by a re-run)."""
    from .. import __version__, environment

    latest = latest or ROOT / "evals" / "results" / "latest.json"
    data = json.loads(latest.read_text(encoding="utf-8")) if latest.exists() else {}
    ed = data.setdefault("editorial", {})
    prev = ed.get(r["set"])
    if r["set"] == "holdout" and prev and str((prev.get("provenance") or {}).get("engine_version", ""))[:3] == __version__[:3]:
        raise RuntimeError("the editorial holdout result of this release is already recorded: it runs once")
    ed[r["set"]] = {"cases": r["cases"], "metrics": r["metrics"], "provenance": environment.provenance(),
                    "disagreements": [{k: x.get(k) for k in ("id", "file", "expected", "got", "codes")} for x in r["results"] if not x["ok"]]}
    latest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return latest
