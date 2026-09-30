"""Command line: `python -m cpe <command>` (or `scripts/cpe <command>`).

Thinking commands (no drawing):
  ingest     files → inventory.json + inventory.md (blocks, tables, facts with context)
  scaffold   deck type → skeleton deck.json with storyline and slide intents to fill
  outline    deck.json → ghost deck (headline-only read-through)
  lint       deck.json → structure, storyline, headline, visual and density issues
  recommend  message type (+ exhibit) → ranked visual encodings with reasons
  plan       deck.json → resolved.json (visual + layout + fit decisions, with rationale)
Rendering commands:
  build      deck.json → deck.pptx (+ build_manifest.json)
  render     deck.pptx → PDF, PNGs, contact sheet
  qa         deck.pptx (+ manifest) → qa_report.json/.md  (exit 1 if not passed)
  run        the full loop: plan → build → render → QA → autofix → … (exit 1 if not passed)
  patch      deck.json + patches.json → patched deck.json
  review     score an agent-filled review.json (semantic visual QA)
  brand      `brand ingest template.pptx -o brands/acme` → brand theme + compatibility report
  eval       visual-quality benchmark over evals/cases vs evals/baseline.json (exit 1 on regression)
Reference:
  catalog    layout library (markdown)        themes    available themes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _p(*a):
    print(*a, flush=True)


def cmd_ingest(a):
    from .ingest.readers import ingest, summary_markdown

    inv = ingest(a.files)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=2, ensure_ascii=False, default=str))
    out.with_suffix(".md").write_text(summary_markdown(inv))
    _p(f"inventory: {len(inv['blocks'])} blocks, {len(inv['tables'])} tables, {len(inv['facts'])} facts → {out} (+ .md)")


def cmd_scaffold(a):
    from .core.storyline import scaffold
    from .spec import save_spec

    spec = scaffold(a.deck_type, a.title or "", a.governing_thought or "", a.theme)
    save_spec(spec, a.out)
    _p(f"skeleton with {len(spec['slides'])} slides ({spec['storyline']['framework']}) → {a.out}")


def cmd_outline(a):
    from .core.storyline import ghost_deck
    from .spec import load_spec

    txt = ghost_deck(load_spec(a.spec))
    if a.out:
        Path(a.out).write_text(txt)
    _p(txt)


def cmd_lint(a):
    from .core.planner import plan
    from .spec import load_spec

    _, issues = plan(load_spec(a.spec))
    levels = {"error": 0, "warning": 0, "info": 0}
    for i in issues:
        levels[i["level"]] += 1
        if i["level"] != "info" or a.verbose:
            _p(f"{i['level']:7} {i['code']:28} {i.get('slide', '-'):6} {i['message']}")
    _p(f"\n{levels['error']} errors, {levels['warning']} warnings, {levels['info']} info")
    return 1 if levels["error"] else 0


def cmd_recommend(a):
    from .core.visual_reasoning import recommend

    ex = json.loads(Path(a.exhibit).read_text()) if a.exhibit else {}
    for r in recommend(a.message_type, ex)[:6]:
        _p(f"{r['score']:>3}  {r['visual']:16} {'; '.join(r['reasons'])}")


def cmd_plan(a):
    from .core.planner import plan
    from .spec import load_spec

    res, issues = plan(load_spec(a.spec))
    Path(a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    for s in res["slides"]:
        lay = (s.get("_plan") or {}).get("layout") or {}
        vis = ", ".join(v.get("chosen", "") for v in (s.get("_plan") or {}).get("visuals", []))
        _p(f"{s.get('id', ''):6} {s.get('kind', ''):12} {lay.get('id', ''):32} {vis}")
    _p(f"→ {a.out} ({sum(1 for i in issues if i['level'] == 'error')} errors, {sum(1 for i in issues if i['level'] == 'warning')} warnings)")


def cmd_build(a):
    from .core.planner import plan
    from .pptx.builder import build, save_manifest
    from .spec import load_spec

    res, _ = plan(load_spec(a.spec))
    out = Path(a.out)
    m = build(res, out)
    save_manifest(m, out.with_name("build_manifest.json"))
    _p(f"built {len(m)} slides → {out}")


def cmd_render(a):
    from .render.renderer import render

    info = render(a.pptx, a.out or Path(a.pptx).parent, dpi=a.dpi)
    _p(f"PDF {info['pdf']}\n{len(info['pngs'])} PNGs\ncontact sheet {info['contact_sheet']}")


def cmd_qa(a):
    from .design.tokens import load_profile, load_theme
    from .qa import geometry, render_checks
    from .qa import report as rep
    from .render import renderer

    pptx = Path(a.pptx)
    out = Path(a.out or pptx.parent)
    manifests = json.loads(Path(a.manifest).read_text()) if a.manifest else []
    theme = load_theme(a.theme)  # a built-in name, a theme JSON or a brand directory
    profile = load_profile(a.profile)
    issues = geometry.check(str(pptx), manifests, theme, profile)
    metrics = {}
    if not a.no_render:
        info = renderer.render(pptx, out, dpi=a.dpi)
        ri, metrics = render_checks.check(info["pdf"], str(pptx), manifests, info["pngs"])
        issues += ri
    from pptx import Presentation

    ids = [m.get("slide_id") for m in manifests] or [f"#{i}" for i in range(1, len(Presentation(str(pptx)).slides) + 1)]
    r = rep.summarize(issues, ids, metrics=metrics)
    rep.write(r, out)
    _p(f"{'PASSED' if r['passed'] else 'FAILED'} score {r['deck_score']} errors {r['counts']['error']} warnings {r['counts']['warning']} → {out / 'qa_report.md'}")
    return 0 if r["passed"] else 1


def cmd_run(a):
    from .pipeline import run
    from .spec import load_spec

    r = run(load_spec(a.spec), a.out, max_iter=a.max_iter, do_render=not a.no_render, dpi=a.dpi, name=a.name, compose=not a.no_compose)
    _p(f"\n{'PASSED' if r['passed'] else 'FAILED'} · score {r['deck_score']} · errors {r['counts']['error']} · warnings {r['counts']['warning']}")
    if r.get("pending_actions"):
        _p("Pending author actions:")
        for x in r["pending_actions"]:
            _p(f"  - {x['slide']} {x['code']}: {x['action']}")
    _p(f"Artifacts in {a.out}: {a.name}.pptx, renders/, contact_sheet.png, qa_report.md, review.md, ghost_deck.md")
    return 0 if r["passed"] else 1


def cmd_patch(a):
    from .spec import apply_patches, load_spec, save_spec

    spec = load_spec(a.spec)
    patches = json.loads(Path(a.patches).read_text())
    if isinstance(patches, dict):  # review.json style {slide: {patches: [...]}}
        flat = []
        for sid, r in patches.items():
            for p in r.get("patches", []):
                flat.append({"slide": sid, **p} if "slide" not in p else p)
        patches = flat
    new, log = apply_patches(spec, patches)
    save_spec(new, a.out or a.spec)
    for line in log:
        _p(line)


def cmd_review(a):
    from .qa.report import evaluate_review

    r = evaluate_review(json.loads(Path(a.review).read_text()))
    for sid, v in r["slides"].items():
        _p(f"{sid:6} {v['total']}/{v['max']} {'ok' if v['passed'] else 'REVISE'}")
    _p("REVIEW PASSED" if r["passed"] else "REVIEW: revise the flagged slides")
    return 0 if r["passed"] else 1


def cmd_eval(a):
    from .evals import run_suite

    r = run_suite(a.cases, a.out, a.baseline, update_baseline=a.update_baseline, compose=not a.no_compose, tolerance=a.tolerance)
    for x in r["regressions"]:
        _p(f"REGRESSION  {x}")
    for x in r["improvements"]:
        _p(f"improved    {x}")
    _p(f"\n{'PASSED' if r['passed'] else 'FAILED'} · suite composition {r['suite_composition']} · report {a.out}/eval_report.md")
    return 0 if r["passed"] else 1


def cmd_brand(a):
    from .brand.ingest import ingest

    r = ingest(a.template, a.out, name=a.name, base_theme=a.base_theme)
    f = r["fonts"]
    _p(f"brand '{r['brand']}' → {a.out}/theme.json  (use it with \"meta\": {{\"brand\": \"{a.out}\"}})")
    _p(f"slide size {r['slide_size']['width_in']}×{r['slide_size']['height_in']} in · masters used: {r['masters_used']} · base layout: {r['base_layout']}")
    for role, x in f.items():
        if x.get("font"):
            _p(f"font {role:7} {x['font']:24} {x['status']:28} measured with {x['measure_family']} ({x['measurement']})")
    for u in r["unsupported"]:
        _p(f"unsupported: {u}")
    _p(f"report: {a.out}/compatibility.md")


def cmd_measure(a):
    """Composition metrics of an existing run directory (any engine version)."""
    from .design.tokens import theme_for
    from .qa.composition import measure_deck

    d = Path(a.run_dir)
    resolved = json.loads((d / "resolved.json").read_text())
    manifests = json.loads((d / "build_manifest.json").read_text())
    pngs = sorted(str(p) for p in (d / "renders").glob("slide-*.png"))
    comps = measure_deck(str(d / f"{a.name}.pdf"), pngs, resolved, manifests, theme_for(resolved.get("meta", {})))
    out = {"deck_score": round(sum(c.score for c in comps) / len(comps), 1) if comps else None, "slides": [c.to_dict() for c in comps]}
    (d / "composition_measure.json").write_text(json.dumps(out, indent=2))
    for c in comps:
        _p(f"{c.slide_id:8} {c.score:5.1f} {', '.join(c.flags)}")
    _p(f"deck composition {out['deck_score']}")


def cmd_catalog(a):
    from .layout.engine import catalog_markdown

    txt = catalog_markdown()
    if a.out:
        Path(a.out).write_text(txt)
    _p(txt)


def cmd_themes(a):
    from .design.tokens import available_themes

    _p("\n".join(available_themes()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cpe", description="Consulting Presentation Engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest"); s.add_argument("files", nargs="+"); s.add_argument("-o", "--out", default="inventory.json"); s.set_defaults(f=cmd_ingest)
    s = sub.add_parser("scaffold"); s.add_argument("--deck-type", required=True); s.add_argument("--title"); s.add_argument("--governing-thought"); s.add_argument("--theme", default="meridian"); s.add_argument("-o", "--out", default="deck.json"); s.set_defaults(f=cmd_scaffold)
    s = sub.add_parser("outline"); s.add_argument("spec"); s.add_argument("-o", "--out"); s.set_defaults(f=cmd_outline)
    s = sub.add_parser("lint"); s.add_argument("spec"); s.add_argument("-v", "--verbose", action="store_true"); s.set_defaults(f=cmd_lint)
    s = sub.add_parser("recommend"); s.add_argument("message_type"); s.add_argument("--exhibit"); s.set_defaults(f=cmd_recommend)
    s = sub.add_parser("plan"); s.add_argument("spec"); s.add_argument("-o", "--out", default="resolved.json"); s.set_defaults(f=cmd_plan)
    s = sub.add_parser("build"); s.add_argument("spec"); s.add_argument("-o", "--out", default="out/deck.pptx"); s.set_defaults(f=cmd_build)
    s = sub.add_parser("render"); s.add_argument("pptx"); s.add_argument("-o", "--out"); s.add_argument("--dpi", type=int, default=110); s.set_defaults(f=cmd_render)
    s = sub.add_parser("qa"); s.add_argument("pptx"); s.add_argument("--manifest"); s.add_argument("--theme", default="meridian"); s.add_argument("--profile", default="standard"); s.add_argument("-o", "--out"); s.add_argument("--no-render", action="store_true"); s.add_argument("--dpi", type=int, default=110); s.set_defaults(f=cmd_qa)
    s = sub.add_parser("run"); s.add_argument("spec"); s.add_argument("-o", "--out", default="out"); s.add_argument("--max-iter", type=int, default=3); s.add_argument("--no-render", action="store_true"); s.add_argument("--dpi", type=int, default=110); s.add_argument("--name", default="deck"); s.add_argument("--no-compose", action="store_true", help="skip the composition engine"); s.set_defaults(f=cmd_run)
    s = sub.add_parser("patch"); s.add_argument("spec"); s.add_argument("patches"); s.add_argument("-o", "--out"); s.set_defaults(f=cmd_patch)
    s = sub.add_parser("review"); s.add_argument("review"); s.set_defaults(f=cmd_review)
    s = sub.add_parser("eval"); s.add_argument("cases", nargs="?", default="evals/cases"); s.add_argument("-o", "--out", default="out/evals"); s.add_argument("--baseline", default="evals/baseline.json"); s.add_argument("--update-baseline", action="store_true"); s.add_argument("--no-compose", action="store_true"); s.add_argument("--tolerance", type=float, default=2.0); s.set_defaults(f=cmd_eval)
    s = sub.add_parser("brand"); bs = s.add_subparsers(dest="brand_cmd", required=True)
    s2 = bs.add_parser("ingest"); s2.add_argument("template"); s2.add_argument("-o", "--out", required=True); s2.add_argument("--name"); s2.add_argument("--base-theme", default="meridian"); s2.set_defaults(f=cmd_brand)
    s = sub.add_parser("measure"); s.add_argument("run_dir"); s.add_argument("--name", default="deck"); s.set_defaults(f=cmd_measure)
    s = sub.add_parser("catalog"); s.add_argument("-o", "--out"); s.set_defaults(f=cmd_catalog)
    s = sub.add_parser("themes"); s.set_defaults(f=cmd_themes)
    a = ap.parse_args(argv)
    return a.f(a) or 0


if __name__ == "__main__":
    sys.exit(main())
