"""Planner: deck spec (thinking) → resolved slide specifications (ready to render).

For every slide it
  1. validates the slide intent (structure, headline, evidence),
  2. resolves `visual.type: auto` with the visual reasoning engine and
     critiques explicit choices,
  3. selects a layout (unless fixed in the spec),
  4. runs the density engine; on overflow tries other eligible layouts and,
     for tables, splits into continuation slides,
  5. records the rationale of every decision in `_plan` (traceability).
"""
from __future__ import annotations

import copy

from ..design.tokens import load_profile
from ..layout.engine import get_layout, load_library
from ..spec import CONTENT_KINDS, issue, slide_exhibits, validate_structure
from . import density, layout_selector, storyline, visual_reasoning
from .headline import lint_headline


def profile_for(spec: dict) -> dict:
    meta = spec.get("meta") or {}
    return load_profile(meta.get("profile") or meta.get("deck_type") or "standard")


def plan(spec: dict, auto_split: bool | None = None) -> tuple[dict, list[dict]]:
    from ..design.tokens import activate, theme_for

    spec = copy.deepcopy(spec)
    meta = spec.setdefault("meta", {})
    activate(theme_for(meta))  # measurement fonts + brand grid before any fitting decision
    profile = profile_for(spec)
    auto_split = meta.get("auto_split", True) if auto_split is None else auto_split
    issues: list[dict] = []
    issues += validate_structure(spec)
    issues += storyline.lint_storyline(spec)
    headline_scores = {}
    out_slides: list[dict] = []
    prev_layout = None
    agenda_items = [s.get("title") for s in spec.get("slides", []) if s.get("kind") == "divider"]
    # the executive summary may quote any number proven elsewhere in the deck
    from .headline import _collect_values, derivable, numbers_in

    deck_values: list[float] = []
    for sl in spec.get("slides", []):
        if sl.get("kind", "content") == "content":
            v, t = _collect_values(sl)
            deck_values += list(derivable(v)) + [n for tt in t + [sl.get("headline", "")] for n, _ in numbers_in(tt)]
    for slide in spec.get("slides", []):
        s = copy.deepcopy(slide)
        s.setdefault("kind", "content")
        sid = s.get("id")
        s["_plan"] = {"visuals": [], "layout": None}
        if s["kind"] in CONTENT_KINDS:
            sc, hi = lint_headline(s.get("headline", ""), s, profile, deck_values if s["kind"] == "exec_summary" else None)
            headline_scores[sid] = sc
            issues += hi
            if s["kind"] == "content" and _has_data(s) and not s.get("source"):
                issues.append(issue("error", "SOURCE_MISSING", "Data slide without a source line", sid))
        # visual reasoning
        for k, ex in enumerate(slide_exhibits(s)):
            ex["_headline"] = s.get("headline", "")  # lets exhibits put the headline's proof on the slide
            ex_path = ("visual" if k == 0 else f"exhibits[{k - 1}]") if isinstance(s.get("visual"), dict) else f"exhibits[{k}]"
            if ex.get("type", "auto") == "auto":
                vt, why = visual_reasoning.choose(s, ex, profile)
                ex["type"] = vt
                ex["_auto"] = True
                s["_plan"]["visuals"].append(why)
            else:
                s["_plan"]["visuals"].append({"chosen": ex["type"], "why": "explicit in spec"})
                issues += [{**v, "exhibit_path": ex_path} for v in visual_reasoning.validate(s, ex, profile)]
        if s["kind"] == "agenda" and not s.get("items"):
            s["items"] = agenda_items or [k.get("message") for k in spec.get("storyline", {}).get("key_line", [])]
        # layout
        try:
            lay_id, why = layout_selector.select(s, prev_layout, profile)
        except (KeyError, ValueError) as e:
            issues.append(issue("error", "LAYOUT_NONE", str(e), sid))
            continue
        s["_plan"]["layout"] = {"id": lay_id, **why}
        pieces = [s]
        if s["kind"] in CONTENT_KINDS:
            lay = get_layout(lay_id)
            d_issues, rep = density.check_slide(s, lay, profile)
            if any(i["code"] == "CONTENT_OVER_CAPACITY" for i in d_issues) and (not slide.get("layout") or slide.get("layout") == "auto"):
                # try the alternatives, keep the first that fits
                roles = layout_selector.content_roles(s)
                for alt in layout_selector.eligible(s, roles, load_library()):
                    if alt.id == lay_id:
                        continue
                    a_issues, a_rep = density.check_slide(s, alt, profile)
                    if not any(i["code"] == "CONTENT_OVER_CAPACITY" for i in a_issues):
                        s["_plan"]["layout"] = {"id": alt.id, "why": f"switched from {lay_id}: content did not fit", "score": None}
                        lay_id, d_issues, rep = alt.id, a_issues, a_rep
                        issues.append(issue("info", "LAYOUT_SWITCH_DENSITY", f"Layout switched to {alt.id} so the text fits without going below the floor", sid))
                        break
            split = next((i for i in d_issues if i["code"] in ("TABLE_OVER_CAPACITY", "DENSITY_TABLE_ROWS")), None)
            if split and auto_split and split.get("split_at") and split.get("rows", 0) > split["split_at"]:
                pieces = density.split_table_slide(s, split["split_at"])
                issues.append(issue("warning", "AUTO_SPLIT", f"Table split into {len(pieces)} slides; better: summarise to the rows that prove the headline", sid))
                d_issues = [i for i in d_issues if i["code"] not in ("TABLE_OVER_CAPACITY", "DENSITY_TABLE_ROWS")]
            issues += d_issues
            s["_plan"]["fit"] = rep
        for piece in pieces:
            piece["_plan"] = copy.deepcopy(s["_plan"])
            out_slides.append(piece)
        prev_layout = lay_id
    for i, s in enumerate(out_slides, start=1):
        s["_page"] = i
    spec["slides"] = out_slides
    spec["_headline_scores"] = headline_scores
    spec["_profile"] = profile
    return spec, issues


def _has_data(s: dict) -> bool:
    from ..spec import VISUAL_TYPES

    return any(VISUAL_TYPES.get(e.get("type"), "") in ("chart", "table", "exhibit") or e.get("type") in ("kpi", "tile_map", "funnel") for e in slide_exhibits(s)) or bool(s.get("kpis"))
