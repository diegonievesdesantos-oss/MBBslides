"""Visual composition engine.

    CONTENT → LAYOUT CANDIDATES → COMPOSITION CANDIDATES → RENDER
            → COMPOSITION SCORING → BEST CANDIDATE → (QA / PATCH loop)

The layout selector answers "which layouts are *compatible* with this content?".
This engine answers "which composition *reads best* with THIS amount of
content?". For every content slide whose layout is not fixed it:

  1. takes the selector's compatible layouts (best + alternatives),
  2. crosses them with composition variants (content scale for sparse slides,
     table rows stretched to the zone),
  3. renders ALL candidates of the deck in one LibreOffice pass,
  4. rejects candidates with QA errors (overflow, collisions, …),
  5. scores the rest with the composition metrics (qa/composition.py) —
     dead space, utilization, balance, density, emphasis, proof, hierarchy,
     alignment — and flags "compatible but editorially weak" ones,
  6. keeps the best (the default wins ties, for stability and variety).

The decision and every rejected alternative are recorded in `_plan.composition`
so the choice is explainable, and the chosen layout / variant is written back
into the spec (marked `_composed`) before the normal QA/patch loop runs.
"""
from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from .core import layout_selector
from .core.planner import plan
from .design.tokens import theme_for
from .layout.engine import get_layout
from .pptx.builder import build
from .qa import composition, geometry, render_checks
from .render import renderer

EDITORIAL_FLOOR = 70.0  # below this a compatible candidate is "editorially weak"
TIE_MARGIN = 1.5  # the default must be beaten by more than this
LAYOUT_SWITCH_MARGIN = 3.0  # a different layout must beat the default by more than this
REPEAT_PENALTY = 2.5  # same layout as the previous slide: monotony
MAX_LAYOUTS = 3


def _variants(slide: dict, layout_id: str) -> list[dict]:
    """Composition variants worth trying for this content amount."""
    from .core.headline import words

    roles = layout_selector.content_roles(slide)
    wc = len(words(" ".join(str(p) for p in (roles.get("commentary") or {}).get("points", []) if isinstance(roles.get("commentary"), dict))))
    has_table = any(e.get("rows") for e in roles.get("exhibit") or [])
    n_rows = max((len(e.get("rows") or []) for e in roles.get("exhibit") or []), default=0)
    only_text = not roles.get("exhibit") and (roles.get("commentary") or roles.get("column") or roles.get("statements") or roles.get("kpis"))
    out = [{}]
    sparse_table = has_table and n_rows <= 6
    sparse_text = (only_text and wc < 60) or (roles.get("kpis") and not roles.get("exhibit"))
    if sparse_table:
        out += [{"scale": 1.2, "table_stretch": 0.6}, {"scale": 1.35, "table_stretch": 0.9}]
    elif sparse_text:
        out += [{"scale": 1.2}, {"scale": 1.4}]
    elif roles.get("commentary") and wc < 30:
        out += [{"scale": 1.15}]
    return out


def _candidates(slide: dict, prev: str | None, profile: dict) -> list[dict]:
    if slide.get("kind", "content") not in ("content",) or (slide.get("layout") and slide.get("layout") != "auto" and not slide.get("_composed")):
        return []
    try:
        best, why = layout_selector.select({**slide, "layout": "auto"}, prev, profile)
    except (KeyError, ValueError):
        return []
    layouts = [best] + [a for a in why.get("alternatives", []) if a != best][: MAX_LAYOUTS - 1]
    out = []
    for lay in layouts:
        for v in _variants(slide, lay):
            out.append({"layout": lay, "variant": v, "default": lay == best and not v})
    return out if len(out) > 1 else []


def compose(spec: dict, work_dir: str | Path | None = None, dpi: int = 70, verbose: bool = True) -> tuple[dict, dict]:
    """Return (spec with chosen compositions, decisions per slide)."""
    resolved, _ = plan(spec)
    profile = resolved.get("_profile") or {}
    theme = theme_for(resolved.get("meta", {}))
    cand_slides, index = [], []
    prev = None
    for s in spec.get("slides", []):
        cands = _candidates(s, prev, profile)
        rs = next((r for r in resolved["slides"] if r.get("id") == s.get("id")), None)
        if cands and rs is not None:
            for k, c in enumerate(cands):
                cs = copy.deepcopy(rs)
                cs["id"] = f"{s['id']}~{k}"
                cs["_plan"] = {**(cs.get("_plan") or {}), "layout": {"id": c["layout"], "why": "composition candidate"}}
                cs["_compose"] = c["variant"]
                cand_slides.append(cs)
                index.append((s["id"], k, c))
            prev = cands[0]["layout"]
        elif rs is not None:
            prev = (rs.get("_plan") or {}).get("layout", {}).get("id")
    decisions: dict = {}
    if not cand_slides:
        return spec, decisions
    cand_deck = {**resolved, "slides": cand_slides}
    tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="cpe_compose_"))
    tmp.mkdir(parents=True, exist_ok=True)
    pptx = tmp / "candidates.pptx"
    manifests = build(cand_deck, pptx)
    issues = geometry.check(str(pptx), manifests, theme, profile)
    info = renderer.render(pptx, tmp, dpi=dpi)
    r_issues, _ = render_checks.check(info["pdf"], str(pptx), manifests, info["pngs"])
    issues += r_issues
    comps = {c.slide_id: c for c in composition.measure_deck(info["pdf"], info["pngs"], cand_deck, manifests, theme)}
    by_slide: dict[str, list] = {}
    for sid, k, c in index:
        cid = f"{sid}~{k}"
        errs = [i for i in issues if i.get("slide") == cid and i["level"] == "error"]
        comp = comps.get(cid)
        score = comp.score if comp else 0.0
        verdict = "ok"
        if errs:
            verdict = "rejected: QA errors (" + ", ".join(sorted({e["code"] for e in errs})) + ")"
        elif score < EDITORIAL_FLOOR:
            verdict = "compatible but editorially weak (" + ", ".join(comp.flags if comp else []) + ")"
        by_slide.setdefault(sid, []).append({"k": k, "layout": c["layout"], "variant": c["variant"], "default": c["default"], "score": round(score, 1),
                                             "flags": comp.flags if comp else [], "errors": len(errs), "verdict": verdict})
    new = copy.deepcopy(spec)
    prev_layout = None
    for s in new["slides"]:
        cands = by_slide.get(s.get("id"))
        if not cands:
            if s.get("kind", "content") == "content":
                rs = next((r for r in resolved["slides"] if r.get("id") == s.get("id")), {})
                prev_layout = (rs.get("_plan") or {}).get("layout", {}).get("id")
            continue
        ok = [c for c in cands if not c["errors"]]
        default = next((c for c in cands if c["default"]), cands[0])
        for c in cands:
            c["adjusted"] = c["score"] - (REPEAT_PENALTY if c["layout"] == prev_layout else 0.0)
        best = max(ok, key=lambda c: c["adjusted"]) if ok else default
        # changing the layout costs deck consistency: it must win clearly; a variant only needs a small margin
        def margin(c):
            return LAYOUT_SWITCH_MARGIN if c["layout"] != default["layout"] else TIE_MARGIN

        if default in ok:
            pool = [c for c in ok if c is default or c["adjusted"] - default["adjusted"] > margin(c)]
            best = max(pool, key=lambda c: c["adjusted"])
        prev_layout = best["layout"]
        for c in cands:
            if c is best:
                c["verdict"] = "chosen"
        s["layout"] = best["layout"]
        s["_composed"] = True
        if best["variant"]:
            s["_compose"] = best["variant"]
        else:
            s.pop("_compose", None)
        decisions[s["id"]] = {"chosen": {"layout": best["layout"], "variant": best["variant"], "score": best["score"]},
                              "default_score": default["score"], "candidates": cands}
        if verbose:
            gain = best["score"] - default["score"]
            print(f"[compose] {s['id']:6} {best['layout']:30} {str(best['variant'] or ''):34} score {best['score']:5.1f} ({gain:+.1f} vs default)", flush=True)
    return new, decisions


def summarize(decisions: dict) -> str:
    L = ["# Composition decisions", "", "| slide | chosen | variant | score | vs default | rejected / weak alternatives |", "|---|---|---|---|---|---|"]
    for sid, d in decisions.items():
        ch = d["chosen"]
        alts = "; ".join(f"`{c['layout']}` {c['variant'] or ''} {c['score']} — {c['verdict']}" for c in d["candidates"] if c["verdict"] != "chosen" and c["verdict"] != "ok")
        L.append(f"| {sid} | `{ch['layout']}` | {ch['variant'] or '—'} | {ch['score']} | {ch['score'] - d['default_score']:+.1f} | {alts or '—'} |")
    return "\n".join(L) + "\n"


def layout_family(layout_id: str) -> str:
    return get_layout(layout_id).family
