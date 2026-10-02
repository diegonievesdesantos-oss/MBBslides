"""Private corporate holdouts: real corporate templates that never enter the public repository.

    .private/holdouts/<name>/template.pptx        the corporate PowerPoint (required)
    .private/holdouts/<name>/brand_spec.*         a human-authored brand specification (optional)
    .private/holdouts/<name>/expectations.json    claims transcribed from that specification (optional)

    cpe holdout private [--root .private/holdouts] [-o private_results]

For every holdout it writes to private_results/<name>/ (git-ignored):

    brand/                       the full ingest output (theme, brand model, compatibility report)
    brand_report.json / .md      what the ingest understood
    layout_catalog.json          every layout with features, classification and observed usage
    layout_classification.md     one line per layout
    font_analysis.json           declared vs observed typography, conflicts, availability, fallbacks
    render_analysis.json         (a) the ORIGINAL template rendered by LibreOffice: pages, fonts the PDF
                                 actually embeds (substitutions); (b) a public test deck generated on the
                                 ingested brand: QA verdict, composition, corporate layout modes
    spec_comparison.json / .md   CPE's conclusions vs the human-written specification

and returns a SANITIZED summary (counts and rates only: no names, colours, text or assets) that
may be recorded in evals/results/latest.json.

Protocol (docs/EVALS.md): build the generic system, freeze the rules, run the holdout, report.
Never tune the engine on a private holdout within the same cycle; never baseline it. Public CI
never runs this (the folder does not exist there) and the runner skips cleanly.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = ROOT / ".private" / "holdouts"
DEFAULT_OUT = ROOT / "private_results"
TEST_DECK = ROOT / "examples" / "alvora" / "deck.json"


def _get(d, path: str):
    cur = d
    for part in path.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _match(actual, exp: dict) -> bool:
    m = exp.get("match", "equals")
    e = exp.get("expected")
    if actual is None:
        return False
    if m == "equals":
        return str(actual).lower() == str(e).lower()
    if m == "in":
        return str(actual).lower() in [str(x).lower() for x in e]
    if m == "contains":
        return any(str(e).lower() == str(x).lower() for x in actual) if isinstance(actual, (list, tuple, set)) else str(e).lower() in str(actual).lower()
    if m == "color":  # hex colours within a small distance
        def rgb(h):
            h = str(h).lstrip("#")
            return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
        vals = actual if isinstance(actual, list) else [actual]
        return any(sum(abs(a - b) for a, b in zip(rgb(v), rgb(e))) <= exp.get("tolerance", 30) for v in vals if v and v != "picture")
    if m == "approx":
        return abs(float(actual) - float(e)) <= float(exp.get("tolerance", 0.1))
    if m == "gte":
        return float(actual) >= float(e)
    if m == "lte":
        return float(actual) <= float(e)
    if m == "truthy":
        return bool(actual) == bool(e)
    return False


def compare_spec(report: dict, expectations: list[dict]) -> dict:
    rows = []
    for exp in expectations:
        actual = _get(report, exp["path"])
        rows.append({"id": exp.get("id"), "claim": exp.get("claim"), "path": exp["path"], "expected": exp.get("expected"),
                     "match": exp.get("match", "equals"), "actual": actual, "agrees": _match(actual, exp), "weight": exp.get("weight", 1)})
    tot = sum(r["weight"] for r in rows) or 1
    return {"claims": len(rows), "agree": sum(1 for r in rows if r["agrees"]), "weighted_agreement": round(sum(r["weight"] for r in rows if r["agrees"]) / tot, 3), "rows": rows}


def _render_template(tpl: Path, work: Path) -> dict:
    """Render the original template: how faithfully does this environment draw it?"""
    import pymupdf

    from .render.renderer import RenderError, to_pdf

    try:
        pdf = to_pdf(tpl, work, timeout=600)
    except RenderError as e:
        return {"rendered": False, "error": str(e)[:300]}
    fonts = {}
    with pymupdf.open(str(pdf)) as doc:
        pages = len(doc)
        for page in doc:
            for f in page.get_fonts():
                name = f[3].split("+")[-1]
                fonts[name] = fonts.get(name, 0) + 1
    return {"rendered": True, "pages": pages, "pdf_fonts": dict(sorted(fonts.items(), key=lambda kv: -kv[1]))}


def run_one(hdir: Path, out_root: Path) -> dict:
    from .brand.ingest import ingest
    from .pipeline import run
    from .spec import load_spec

    name = hdir.name
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    rep = ingest(hdir / "template.pptx", out / "brand", name=name)
    (out / "brand_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
    shutil.copy(out / "brand" / "compatibility.md", out / "brand_report.md")
    shutil.copy(out / "brand" / "layout_catalog.json", out / "layout_catalog.json")
    L = ["# Layout classification", "", "| id | layout | classification | observed use |", "|---|---|---|---|"]
    L += [f"| {x['id']} | {x['name']} | " + ", ".join(f"{c['type']} ({c['confidence']})" for c in x["classification"]) + f" | {x['usage'] or '—'} |" for x in rep["layouts"]]
    (out / "layout_classification.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    (out / "font_analysis.json").write_text(json.dumps({"typography": rep["typography"], "fonts": rep["fonts"]}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    with tempfile.TemporaryDirectory() as tmp:
        tpl_render = _render_template(hdir / "template.pptx", Path(tmp))
    spec = load_spec(TEST_DECK)
    spec["meta"]["brand"] = str(out / "brand")
    spec["meta"].pop("theme", None)
    deck_rep = run(spec, out / "test_deck", max_iter=2, verbose=False, compose=True)
    man = json.loads((out / "test_deck" / "build_manifest.json").read_text(encoding="utf-8"))
    modes = {}
    for m in man:
        c = m.get("corporate") or {"mode": "none"}
        modes[c["mode"]] = modes.get(c["mode"], 0) + 1
    comp = deck_rep.get("composition") or {}
    render = {"template_render": tpl_render,
              "test_deck": {"spec": TEST_DECK.relative_to(ROOT).as_posix(), "qa_passed": deck_rep["passed"], "qa_errors": deck_rep["counts"]["error"],
                            "qa_warnings": deck_rep["counts"]["warning"], "qa_codes": sorted({i["code"] for i in deck_rep["issues"] if i["level"] != "info"}),
                            "composition": comp.get("deck_score"), "corporate_modes": modes,
                            "decisions": [{"slide": m["slide_id"], **(m.get("corporate") or {})} for m in man]}}
    (out / "render_analysis.json").write_text(json.dumps(render, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
    comparison = None
    exp_file = hdir / "expectations.json"
    if exp_file.exists():
        comparison = compare_spec(rep, json.loads(exp_file.read_text(encoding="utf-8"))["expectations"])
        (out / "spec_comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
        L = ["# CPE inference vs human-written brand specification", "", f"Agreement: {comparison['agree']}/{comparison['claims']} claims (weighted {comparison['weighted_agreement']})", "",
             "| claim | expected | CPE inferred | agrees |", "|---|---|---|---|"]
        L += [f"| {r['claim']} | {r['expected']} | {json.dumps(r['actual'], ensure_ascii=False, default=str)[:80]} | {'✅' if r['agrees'] else '❌'} |" for r in comparison["rows"]]
        (out / "spec_comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    cls = [x["classification"][0] for x in rep["layouts"]]
    summary = {
        "masters": len(rep["masters"]), "layouts": rep["layout_count"], "example_slides": rep["example_slides"]["count"],
        "layouts_classified_confidence_ge_0_5": round(sum(1 for c in cls if c["confidence"] >= 0.5 and c["type"] != "unknown") / max(1, len(cls)), 3),
        "layout_families": len(rep["layout_families"]), "rescaled": bool(rep["slide_size"].get("rescaled")), "masters_used": rep["masters_used"],
        "font_conflict_detected": bool(rep["typography"].get("conflict")), "corporate_font_installed": all(f.get("installed") for f in rep["fonts"].values() if f.get("font")),
        "template_pages_rendered": tpl_render.get("pages"), "test_deck_qa_passed": deck_rep["passed"], "test_deck_qa_errors": deck_rep["counts"]["error"],
        "test_deck_composition": comp.get("deck_score"), "corporate_modes": modes,
        "spec_agreement": (f"{comparison['agree']}/{comparison['claims']}" if comparison else None),
        "spec_weighted_agreement": comparison["weighted_agreement"] if comparison else None,
    }
    (out / "summary_sanitized.json").write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    return summary


def run(root: str | Path | None = None, out: str | Path | None = None, record: bool = False) -> dict:
    root = Path(root) if root else DEFAULT_ROOT
    out = Path(out) if out else DEFAULT_OUT
    holdouts = sorted(p for p in root.glob("*") if (p / "template.pptx").exists()) if root.exists() else []
    if not holdouts:
        return {"status": "skipped", "reason": f"private holdouts not present ({root}); place a template at .private/holdouts/<name>/template.pptx"}
    results = {}
    for i, h in enumerate(holdouts):
        results[f"corporate_template_{chr(65 + i)}"] = run_one(h, out)  # anonymised label in the sanitized summary
    res = {"status": "ran", "holdouts": results}
    if record:
        from .evals import record_result

        s = next(iter(results.values()))
        line = (f"{s['masters']} master(s), {s['layouts']} layouts, {round(100 * s['layouts_classified_confidence_ge_0_5'])}% classified with confidence ≥ 0.5; "
                f"font conflict {'detected' if s['font_conflict_detected'] else 'none'}; test deck QA {'passed' if s['test_deck_qa_passed'] else 'failed'}"
                + (f"; agreement with the human brand spec {s['spec_agreement']}" if s.get("spec_agreement") else ""))
        record_result("holdout_private", {"summary": line, "holdouts": results})
    return res


# ── external deck holdouts (v1.4) ────────────────────────────────────────────────────────────────
#
#   .private/holdouts/decks/*.json      deck specs (anonymized corporate examples, specs written by
#                                       someone else) — never in the repository
#   cpe holdout external [--root .private/holdouts/decks] [-o private_results/external] [--record]
#
# Runs each deck through the frozen engine, writes everything to private_results/external/
# (git-ignored), and returns a SANITIZED summary: counts, scores and per-archetype aggregates only —
# no deck names, headlines, text, numbers from the decks or renders. Never baselined.

DECKS_ROOT = ROOT / ".private" / "holdouts" / "decks"


def run_external(root: str | Path | None = None, out: str | Path | None = None, record: bool = False) -> dict:
    from . import quality
    from .evals import run_case

    root = Path(root) if root else DECKS_ROOT
    out = Path(out) if out else DEFAULT_OUT / "external"
    decks = sorted(root.glob("*.json")) if root.exists() else []
    if not decks:
        return {"status": "skipped", "reason": f"{root} not present or empty (external holdouts live outside the repository)"}
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, d in enumerate(decks):
        r = run_case(d, out, name=f"deck_{i + 1:02d}")  # anonymous names in every artefact
        results.append(r)
    comps = [r["composition"] for r in results if r.get("composition") is not None]
    prof = quality.profile(results, deck_mean=round(sum(comps) / len(comps), 1) if comps else None)
    (out / "external_report.json").write_text(json.dumps({"cases": results, "quality": prof}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    summary = {
        "status": "run", "decks": len(results), "built": sum(1 for r in results if r.get("ok")),
        "slides": prof["distribution"]["n"], "overall": prof["overall_score"], "macro_archetype": prof["macro_archetype_score"],
        "p10": prof["distribution"]["p10"], "weakest_archetype": prof["weakest_archetype"], "weakest_archetype_score": prof["weakest_archetype_score"],
        "qa_errors": sum(r.get("qa_errors") or 0 for r in results),
        "archetypes": {a: {"n": s["n"], "mean": s["mean"], "min": s["min"]} for a, s in prof["archetypes"].items()},
        "note": "sanitized aggregates of decks kept outside the repository; never baselined, never tuned on in the same cycle",
    }
    if record:
        from .evals import record_result

        record_result("holdout_external", summary)
    return summary


# ── external validation intake (v1.5, generalised in v1.6) ───────────────────────────────────────
#
#   .private/holdouts/external/decks/*.json          decks written by someone OTHER than the developer
#   .private/holdouts/external/PROVENANCE.json       attested outside authorship (see the protocol)
#   .private/holdouts/external/SEAL.json             written by `cpe holdout external-seal` (hashes)
#   .private/holdouts/corporate_unseen/<name>/template.pptx   templates never used in development
#
#   cpe holdout intake                         status of both (never runs anything)
#   cpe holdout external-seal                  hash and seal the received decks (before any render)
#   cpe holdout external-run [--record]        run ONCE per engine version, on the sealed decks
#   cpe holdout corporate-run [--record]       run every unseen template once per engine version
#
# Order (docs/EXTERNAL_HOLDOUT_PROTOCOL.md): author → receive → hash → seal → do not render →
# freeze engine → run once → report → no same-version tuning. The runners refuse missing
# provenance, a broken seal, a second run on the same engine version, and known development
# templates (the private development template): a self-authored deck or a reused template is never presented as independent.

EXTERNAL = DEFAULT_ROOT / "external"
CORPORATE_UNSEEN = DEFAULT_ROOT / "corporate_unseen"
KNOWN_DEVELOPMENT = DEFAULT_ROOT / "KNOWN_DEVELOPMENT.sha256"  # hashes only, private
RUNS = DEFAULT_ROOT / "RUNS.json"  # which engine version ran which intake (run-once guard)


def _sha256(p: Path) -> str:
    import hashlib

    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def known_development_hashes() -> set[str]:
    """Templates already used in development: every template.pptx under .private/holdouts outside
    the unseen-template intake, plus the recorded hash list."""
    out = set()
    if KNOWN_DEVELOPMENT.exists():
        out |= {line.split()[0] for line in KNOWN_DEVELOPMENT.read_text(encoding="utf-8").splitlines() if line.strip()}
    if DEFAULT_ROOT.exists():
        out |= {_sha256(t) for t in DEFAULT_ROOT.glob("*/template.pptx")}
    return out


def _decks(root: Path) -> list[Path]:
    return sorted((root / "decks").glob("*.json")) if (root / "decks").exists() else []


def seal_external(root: Path = EXTERNAL) -> dict:
    decks = _decks(root)
    if not decks:
        raise SystemExit("nothing to seal: no decks in " + _rel(root / "decks"))
    if (root / "SEAL.json").exists():
        raise SystemExit("already sealed: a seal is never rewritten (add new decks as a new holdout)")
    seal = {"sealed_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"), "files": {d.name: _sha256(d) for d in decks},
            "provenance_sha256": _sha256(root / "PROVENANCE.json") if (root / "PROVENANCE.json").exists() else None}
    (root / "SEAL.json").write_text(json.dumps(seal, indent=2) + "\n", encoding="utf-8", newline="\n")
    return seal


def _seal_ok(root: Path) -> tuple[bool, str]:
    f = root / "SEAL.json"
    if not f.exists():
        return False, "not sealed (run `cpe holdout external-seal` before anything else)"
    seal = json.loads(f.read_text(encoding="utf-8"))
    now = {d.name: _sha256(d) for d in _decks(root)}
    if now != seal["files"]:
        return False, "seal broken: decks were added, removed or edited after sealing"
    return True, "seal verified"


def _already_ran(kind: str) -> str | None:
    from . import __version__

    runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else {}
    return runs.get(kind, {}).get(__version__)


def _mark_ran(kind: str, commit: str | None) -> None:
    from . import __version__

    runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else {}
    runs.setdefault(kind, {})[__version__] = commit or "unknown"
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    RUNS.write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8", newline="\n")


def external_status(root: Path = EXTERNAL) -> dict:
    decks = _decks(root)
    prov_f = root / "PROVENANCE.json"
    prov = json.loads(prov_f.read_text(encoding="utf-8")) if prov_f.exists() else None
    if not decks:
        return {"status": "EXTERNAL HOLDOUT: AWAITING INPUT", "folder": _rel(root) + "/decks/", "decks": 0,
                "how": "docs/EXTERNAL_HOLDOUT_PROTOCOL.md (author brief: docs/EXTERNAL_AUTHOR_BRIEF.md)"}
    if not prov or prov.get("authored_by_developer") is not False or prov.get("engine_renders_seen_by_author") is not False:
        return {"status": "EXTERNAL HOLDOUT: PROVENANCE MISSING OR NOT INDEPENDENT", "decks": len(decks),
                "how": "PROVENANCE.json must attest authored_by_developer=false and engine_renders_seen_by_author=false"}
    ok, why = _seal_ok(root)
    if not ok:
        return {"status": "EXTERNAL HOLDOUT: RECEIVED, NOT SEALED" if "not sealed" in why else "EXTERNAL HOLDOUT: SEAL BROKEN", "decks": len(decks), "why": why}
    return {"status": "EXTERNAL HOLDOUT: READY", "decks": len(decks), "received": prov.get("received")}


def _templates(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("*") if (p / "template.pptx").exists()) if root.exists() else []


def corporate_status(root: Path = CORPORATE_UNSEEN) -> dict:
    tpls = _templates(root)
    if not tpls:
        return {"status": "UNSEEN CORPORATE TEMPLATE: AWAITING USER-SUPPLIED TEMPLATE", "folder": _rel(root) + "/<name>/template.pptx",
                "command": "scripts/cpe holdout corporate-run --record"}
    known = known_development_hashes()
    refused = [t.name for t in tpls if _sha256(t / "template.pptx") in known]
    if refused:
        return {"status": "UNSEEN CORPORATE TEMPLATE: REFUSED — already used in development (not unseen)", "refused": refused}
    return {"status": "UNSEEN CORPORATE TEMPLATE: READY", "templates": len(tpls)}


def run_external_holdout(out: str | Path | None = None, record: bool = False, root: Path = EXTERNAL) -> dict:
    from .environment import provenance

    st = external_status(root)
    if not st["status"].endswith("READY"):
        return {**st, "ran": False}
    prev = _already_ran("external")
    if prev:
        return {"status": f"EXTERNAL HOLDOUT: ALREADY RUN for this engine version (commit {prev[:10]}) — run once, report, no same-version tuning", "ran": False}
    pv = provenance()
    if pv.get("evaluated_source_dirty"):
        return {"status": "EXTERNAL HOLDOUT: REFUSED — engine not frozen (evaluated source is dirty); commit first", "ran": False}
    r = run_external(root / "decks", out or DEFAULT_OUT / "external", record=False)
    r["evidence"] = "external holdout (independently authored, provenance attested, sealed)"
    r["provenance"] = pv
    _mark_ran("external", pv.get("evaluated_source_commit"))
    if record:
        from .evals import record_result

        record_result("holdout_external", r)
    return {**r, "ran": True}


def run_corporate_unseen(out: str | Path | None = None, record: bool = False, root: Path = CORPORATE_UNSEEN) -> dict:
    st = corporate_status(root)
    if not st["status"].endswith("READY"):
        return {**st, "ran": False}
    prev = _already_ran("corporate_unseen")
    if prev:
        return {"status": f"UNSEEN CORPORATE TEMPLATE: ALREADY RUN for this engine version (commit {prev[:10]})", "ran": False}
    from .environment import provenance

    pv = provenance()
    out = Path(out) if out else DEFAULT_OUT / "corporate_unseen"
    results = {f"unseen_template_{chr(65 + i)}": run_one(t, out) for i, t in enumerate(_templates(root))}  # anonymised labels
    _mark_ran("corporate_unseen", pv.get("evaluated_source_commit"))
    if record:
        from .evals import record_result

        record_result("holdout_corporate_unseen", {"summary": "unseen corporate templates (sanitized aggregates)", "templates": results, "provenance": pv})
    return {"status": "ran", "ran": True, "templates": results}
