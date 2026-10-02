"""End-to-end pipeline with the self-correction loop.

    editorial compile (v3.1) → [compose] → plan → build → render → QA (content + geometry + render) → autofix patches
      ↑__________________________________________________________|   (≤ max_iter)

Artifacts in out_dir:
    deck.pptx            final native, editable deck
    deck.pdf, renders/   what LibreOffice drew (one PNG per slide) + contact_sheet.png
    resolved.json        the slide specifications actually rendered (with rationale)
    build_manifest.json  zones, boxes and fitting decisions per slide
    qa_report.json/.md   verdict (passed), score, issues, iterations, pending actions
    review.md            semantic-visual review packet for the agent (+ review_template.json)
    ghost_deck.md        headline-only read-through
    editorial_report.*   v3.1 Editorial QA (action titles, parallel wording, horizontal logic): its own verdict
    headline_strip.md    the titles alone, against the five questions of the strip test
    editorial_ghost_deck.md  the ghost deck with role, signature, score and parallel status
    deck.autofixed.json  the spec after automatic patches (only if any were applied)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .core.planner import plan
from .core.storyline import ghost_deck
from .design.tokens import theme_for
from .pptx.builder import build, save_manifest
from .qa import autofix, composition, geometry, render_checks
from .qa import report as rep
from .render import renderer
from .spec import apply_patches, save_spec


def _template_not_used(meta: dict, theme) -> list[dict]:
    """v3.0: a corporate template the engine could not use (a 4:3 canvas) is a deck-level warning, not a
    silent fallback to its colours and fonts."""
    if not meta.get("brand"):
        return []
    comp = Path(getattr(theme, "source_dir", "") or "") / "compatibility.json"
    try:
        r = json.loads(comp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if r.get("masters_used", True):
        return []
    sz = r.get("slide_size") or {}
    return [{"level": "warning", "code": "BRAND_TEMPLATE_NOT_USED", "slide": None,
             "message": f"The corporate template was NOT used: its slide size {sz.get('width_in')}×{sz.get('height_in')} in is not 16:9, "
                        "so only its colours and fonts were applied (no master, layouts or logo). See the brand's compatibility.md."}]


FACTUAL_CODES = {"HEADLINE_NUMBER_UNSUPPORTED", "SOURCE_MISSING", "PROOF_NOT_VISIBLE", "BROKEN_EXHIBIT"}
SEMANTIC_PATHS = ("headline", "headline_candidates", "proposition", "text")  # wording belongs to the editorial layer (spec §77)


def _keep_wording(compiled: dict, after: dict, findings: list) -> dict:
    """Composition candidates and autofix patches may change layout, never the compiled wording (spec §77-78)."""
    want = {s.get("id"): s for s in compiled.get("slides") or []}
    for s in after.get("slides") or []:
        w = want.get(s.get("id"))
        if w is None:
            continue
        for k in ("headline", "text"):
            if k in w and s.get(k) != w[k]:
                findings.append({"code": "EDITORIAL_WORDING_RESTORED", "class": "soft", "level": "warning", "slide": s.get("id"),
                                 "message": f"A layout step changed the compiled {k}; restored (wording only changes through the editorial layer)"})
                s[k] = w[k]
    return after


def run(spec: dict, out_dir: str | Path, max_iter: int = 3, do_render: bool = True, dpi: int = 110, name: str = "deck", verbose: bool = True, compose: bool = False,
        editorial_mode: str | None = None) -> dict:
    from .core.planner import profile_for
    from .editorial import compile_editorial, strip_editorial
    from .editorial import report as ed_report

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    history = []
    tried: dict = {}
    # v3.1: the wording contract is settled first — composition and planning see the final headlines (spec §35-36)
    current, editorial = compile_editorial(spec, profile_for(spec), editorial_mode)
    compiled = current
    applied_any = False
    decisions: dict = {}
    if compose and do_render:
        import shutil
        import tempfile

        from .compose import compose as run_compose
        from .compose import summarize as compose_summary

        scratch = Path(tempfile.mkdtemp(prefix="cpe_compose_"))  # candidate renders are scratch, not artefacts
        try:
            current, decisions = run_compose(current, scratch, verbose=verbose)
            current = _keep_wording(compiled, current, editorial["findings"])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        (out / "composition.md").write_text(compose_summary(decisions), encoding="utf-8", newline="\n")
    final = None
    for it in range(1, max_iter + 1):
        t0 = time.time()
        resolved, content_issues = plan(current)
        (out / "resolved.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
        pptx_path = out / f"{name}.pptx"
        manifests = build(resolved, pptx_path)
        save_manifest(manifests, out / "build_manifest.json")
        theme = theme_for(resolved.get("meta", {}))
        profile = resolved.get("_profile") or {}
        issues = list(content_issues)
        issues += geometry.check(str(pptx_path), manifests, theme, profile)
        issues += _template_not_used(resolved.get("meta", {}), theme)  # v3.0: never silent
        metrics = {}
        render_info = {}
        comp = []
        advice = []
        if do_render:
            try:
                render_info = renderer.render(pptx_path, out, dpi=dpi)
                r_issues, metrics = render_checks.check(render_info["pdf"], str(pptx_path), manifests, render_info["pngs"])
                # the render is the ground truth for line breaks: drop the model-based duplicates
                issues = [i for i in issues if i["code"] not in ("HEADLINE_WIDOW", "HEADLINE_LINES")] + r_issues
                comp = composition.measure_deck(render_info["pdf"], render_info["pngs"], resolved, manifests, theme)
                composition.apply_integrity(comp, issues, manifests)  # a broken slide cannot score well (v1.7)
                advice = composition.advice_from(comp)  # editorial preference: never part of hard QA
                from .brand.rules import deck_advice

                advice += deck_advice(resolved, manifests, theme)
            except renderer.RenderError as e:
                issues.append({"level": "warning", "code": "RENDER_UNAVAILABLE", "message": str(e)})
        issues, exempted = rep.apply_exemptions(issues, current)
        slide_ids = [s.get("id") for s in resolved["slides"]]
        patches, pending = autofix.propose(current, resolved, issues, tried)
        summary = rep.summarize(issues, slide_ids, exempted, metrics)
        history.append({"iteration": it, "errors": summary["counts"]["error"], "warnings": summary["counts"]["warning"], "score": summary["deck_score"], "patches": [p.get("reason", p["op"]) for p in patches if p.get("path") != "_autofix_layout"], "seconds": round(time.time() - t0, 1)})
        if verbose:
            print(f"[iter {it}] errors={summary['counts']['error']} warnings={summary['counts']['warning']} score={summary['deck_score']} patches={len([p for p in patches if p.get('path') != '_autofix_layout'])}")
        final = (resolved, issues, exempted, metrics, render_info, pending, comp, advice)
        if not patches or it == max_iter:
            if patches and it == max_iter:
                history[-1]["patches"] = ["(not applied: iteration budget exhausted) " + x for x in history[-1]["patches"]]
            break
        current, log = apply_patches(current, [p for p in patches if not str(p.get("path") or "").startswith(SEMANTIC_PATHS)])
        current = _keep_wording(compiled, current, editorial["findings"])
        applied_any = True
    resolved, issues, exempted, metrics, render_info, pending, comp, advice = final
    comp_d = [c.to_dict() for c in comp]
    advice_ed = [{"slide": a["slide"] or "deck", "code": a["code"], "action": autofix.AGENT_ACTIONS.get(a["code"], a["message"]), "why": a["message"]} for a in advice]
    _typography(editorial, issues)
    report = rep.summarize(issues, [s.get("id") for s in resolved["slides"]], exempted, metrics, history,
                           {"pending_actions": pending, "artifacts": {"pptx": str(out / f"{name}.pptx"), **render_info},
                            "editorial_advice": advice_ed,
                            "composition": {"metric": composition.SCORE_NAME,
                                            "deck_score": round(sum(c["score"] for c in comp_d) / len(comp_d), 1) if comp_d else None,
                                            "deck_score_v1": round(sum(c["score_v1"] for c in comp_d) / len(comp_d), 1) if comp_d else None,
                                            "slides": comp_d, "decisions": decisions}})
    _dimensions(report, editorial, issues)
    rep.write(report, out)
    ed_report.write(editorial, current, out)
    from .brand.fidelity import write_run_reports  # v1.8: corporate usage + brand fidelity, kept apart from the deck score

    write_run_reports(out, out / f"{name}.pptx", theme_for(resolved.get("meta", {})), json.loads((out / "build_manifest.json").read_text(encoding="utf-8")), issues, resolved)
    (out / "ghost_deck.md").write_text(ghost_deck(current), encoding="utf-8", newline="\n")
    if render_info.get("pngs"):
        rep.review_packet(resolved, report, render_info["pngs"], out)
    if applied_any or decisions:
        save_spec(strip_editorial(current), out / f"{name}.autofixed.json")
    return report


def _typography(editorial: dict, issues: list) -> None:
    """Post-render headline QA (spec §48): line count and widows are only known after the render. A title still
    over two lines is an editorial fit warning: compression must go back through the ATE, never be cut by autofix."""
    typo = [i for i in issues if i.get("code") in ("HEADLINE_LINES", "HEADLINE_WIDOW", "RENDER_HEADLINE_LINES", "RENDER_HEADLINE_WIDOW")]
    editorial["typography"] = [{"slide": i.get("slide"), "code": i["code"], "level": i["level"], "message": i["message"]} for i in typo]
    for i in typo:
        if i["code"].endswith("HEADLINE_LINES"):
            editorial["findings"].append({"code": "EDITORIAL_HEADLINE_FIT", "class": "soft", "level": "warning", "slide": i.get("slide"),
                                          "message": "The rendered title runs over two lines: request a semantically safe compression (new candidate through the ATE)"})


def _dimensions(report: dict, editorial: dict, issues: list) -> None:
    """Separate verdicts (spec §18, §82): no composite. The deck passes only when every dimension passes."""
    from .qa.report import qa_semantics

    sem = qa_semantics(issues)
    errs = [i for i in issues if i.get("level") == "error"]
    fact = [i for i in errs if i.get("code") in FACTUAL_CODES]
    brand = [i for i in errs if str(i.get("code", "")).startswith("BRAND_")]
    ed_ok = editorial["passed"]
    report["dimensions"] = {
        "factual": {"passed": not fact, "errors": len(fact)},
        "editorial": {"passed": ed_ok, "errors": editorial["summary"]["hard_errors"], "mode": editorial["mode"], "report": "editorial_report.md"},
        "visual": {"passed": sem["visual_qa_passed"], "errors": sem["errors_visual"]},
        "authoring": {"passed": sem["authoring_qa_passed"], "errors": sem["errors_authoring"]},
        "brand": {"passed": not brand, "errors": len(brand)},
    }
    report["qa_passed_without_editorial"] = report["passed"]
    report["passed"] = report["passed"] and ed_ok
    report["editorial"] = {**editorial["summary"], "passed": ed_ok, "mode": editorial["mode"]}
