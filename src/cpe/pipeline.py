"""End-to-end pipeline with the self-correction loop.

    plan → build → render → QA (content + geometry + render) → autofix patches
      ↑__________________________________________________________|   (≤ max_iter)

Artifacts in out_dir:
    deck.pptx            final native, editable deck
    deck.pdf, renders/   what LibreOffice drew (one PNG per slide) + contact_sheet.png
    resolved.json        the slide specifications actually rendered (with rationale)
    build_manifest.json  zones, boxes and fitting decisions per slide
    qa_report.json/.md   verdict (passed), score, issues, iterations, pending actions
    review.md            semantic-visual review packet for the agent (+ review_template.json)
    ghost_deck.md        headline-only read-through
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


def run(spec: dict, out_dir: str | Path, max_iter: int = 3, do_render: bool = True, dpi: int = 110, name: str = "deck", verbose: bool = True, compose: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    history = []
    tried: dict = {}
    current = spec
    applied_any = False
    decisions: dict = {}
    if compose and do_render:
        import shutil
        import tempfile

        from .compose import compose as run_compose
        from .compose import summarize as compose_summary

        scratch = Path(tempfile.mkdtemp(prefix="cpe_compose_"))  # candidate renders are scratch, not artefacts
        try:
            current, decisions = run_compose(spec, scratch, verbose=verbose)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        (out / "composition.md").write_text(compose_summary(decisions))
    final = None
    for it in range(1, max_iter + 1):
        t0 = time.time()
        resolved, content_issues = plan(current)
        (out / "resolved.json").write_text(json.dumps(resolved, indent=2, ensure_ascii=False, default=str))
        pptx_path = out / f"{name}.pptx"
        manifests = build(resolved, pptx_path)
        save_manifest(manifests, out / "build_manifest.json")
        theme = theme_for(resolved.get("meta", {}))
        profile = resolved.get("_profile") or {}
        issues = list(content_issues)
        issues += geometry.check(str(pptx_path), manifests, theme, profile)
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
                advice = composition.advice_from(comp)  # editorial preference: never part of hard QA
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
        current, log = apply_patches(current, patches)
        applied_any = True
    resolved, issues, exempted, metrics, render_info, pending, comp, advice = final
    comp_d = [c.to_dict() for c in comp]
    editorial = [{"slide": a["slide"], "code": a["code"], "action": autofix.AGENT_ACTIONS.get(a["code"], a["message"]), "why": a["message"]} for a in advice]
    report = rep.summarize(issues, [s.get("id") for s in resolved["slides"]], exempted, metrics, history,
                           {"pending_actions": pending, "artifacts": {"pptx": str(out / f"{name}.pptx"), **render_info},
                            "editorial_advice": editorial,
                            "composition": {"metric": composition.SCORE_NAME,
                                            "deck_score": round(sum(c["score"] for c in comp_d) / len(comp_d), 1) if comp_d else None,
                                            "deck_score_v1": round(sum(c["score_v1"] for c in comp_d) / len(comp_d), 1) if comp_d else None,
                                            "slides": comp_d, "decisions": decisions}})
    rep.write(report, out)
    (out / "ghost_deck.md").write_text(ghost_deck(current))
    if render_info.get("pngs"):
        rep.review_packet(resolved, report, render_info["pngs"], out)
    if applied_any or decisions:
        save_spec(current, out / f"{name}.autofixed.json")
    return report
