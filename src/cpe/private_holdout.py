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
    (out / "brand_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
    shutil.copy(out / "brand" / "compatibility.md", out / "brand_report.md")
    shutil.copy(out / "brand" / "layout_catalog.json", out / "layout_catalog.json")
    L = ["# Layout classification", "", "| id | layout | classification | observed use |", "|---|---|---|---|"]
    L += [f"| {x['id']} | {x['name']} | " + ", ".join(f"{c['type']} ({c['confidence']})" for c in x["classification"]) + f" | {x['usage'] or '—'} |" for x in rep["layouts"]]
    (out / "layout_classification.md").write_text("\n".join(L) + "\n")
    (out / "font_analysis.json").write_text(json.dumps({"typography": rep["typography"], "fonts": rep["fonts"]}, indent=2, ensure_ascii=False))
    with tempfile.TemporaryDirectory() as tmp:
        tpl_render = _render_template(hdir / "template.pptx", Path(tmp))
    spec = load_spec(TEST_DECK)
    spec["meta"]["brand"] = str(out / "brand")
    spec["meta"].pop("theme", None)
    deck_rep = run(spec, out / "test_deck", max_iter=2, verbose=False, compose=True)
    man = json.loads((out / "test_deck" / "build_manifest.json").read_text())
    modes = {}
    for m in man:
        c = m.get("corporate") or {"mode": "none"}
        modes[c["mode"]] = modes.get(c["mode"], 0) + 1
    comp = deck_rep.get("composition") or {}
    render = {"template_render": tpl_render,
              "test_deck": {"spec": str(TEST_DECK.relative_to(ROOT)), "qa_passed": deck_rep["passed"], "qa_errors": deck_rep["counts"]["error"],
                            "qa_warnings": deck_rep["counts"]["warning"], "qa_codes": sorted({i["code"] for i in deck_rep["issues"] if i["level"] != "info"}),
                            "composition": comp.get("deck_score"), "corporate_modes": modes,
                            "decisions": [{"slide": m["slide_id"], **(m.get("corporate") or {})} for m in man]}}
    (out / "render_analysis.json").write_text(json.dumps(render, indent=2, ensure_ascii=False, default=str))
    comparison = None
    exp_file = hdir / "expectations.json"
    if exp_file.exists():
        comparison = compare_spec(rep, json.loads(exp_file.read_text())["expectations"])
        (out / "spec_comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False, default=str))
        L = ["# CPE inference vs human-written brand specification", "", f"Agreement: {comparison['agree']}/{comparison['claims']} claims (weighted {comparison['weighted_agreement']})", "",
             "| claim | expected | CPE inferred | agrees |", "|---|---|---|---|"]
        L += [f"| {r['claim']} | {r['expected']} | {json.dumps(r['actual'], ensure_ascii=False, default=str)[:80]} | {'✅' if r['agrees'] else '❌'} |" for r in comparison["rows"]]
        (out / "spec_comparison.md").write_text("\n".join(L) + "\n")
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
    (out / "summary_sanitized.json").write_text(json.dumps(summary, indent=2))
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
