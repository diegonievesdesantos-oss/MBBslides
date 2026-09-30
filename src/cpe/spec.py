"""The Deck Specification — the contract between THINKING and RENDERING.

A deck spec is plain JSON so that an agent can write, diff and patch it.
Nothing is drawn until every content slide carries a complete *slide intent*:

    purpose → headline (so-what) → supporting message → evidence → visual → layout

This module defines the vocabulary (slide kinds, visual types, message types),
loads/saves specs and validates structure. Semantic checks (is the headline a
conclusion? does the chart support it?) live in core/ and qa/.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

SLIDE_KINDS = {
    "cover",
    "agenda",
    "divider",
    "exec_summary",
    "content",
    "statement",
    "closing",
    "appendix_divider",
}

# Visual vocabulary (what the exhibit IS). Grouped for docs & reasoning.
VISUAL_TYPES = {
    # text
    "bullets": "text",
    "statements": "text",
    "text_columns": "text",
    "statement": "text",
    "quote": "text",
    "kpi": "kpi",
    # charts (native, data-editable)
    "bar": "chart",
    "column": "chart",
    "stacked_bar": "chart",
    "stacked_column": "chart",
    "stacked_100": "chart",
    "line": "chart",
    "area": "chart",
    "scatter": "chart",
    "bubble": "chart",
    "pie": "chart",
    "donut": "chart",
    "combo": "chart",
    "waterfall": "chart",
    "bridge": "chart",
    "histogram": "chart",
    "slope": "chart",
    # shape-built exhibits (editable shapes)
    "mekko": "exhibit",
    "heatmap": "table",
    "table": "table",
    "harvey_table": "table",
    "scorecard": "table",
    # diagrams (editable shapes)
    "matrix_2x2": "diagram",
    "portfolio": "diagram",
    "process": "diagram",
    "value_chain": "diagram",
    "timeline": "diagram",
    "gantt": "diagram",
    "roadmap": "diagram",
    "tree": "diagram",
    "driver_tree": "diagram",
    "org_chart": "diagram",
    "funnel": "diagram",
    "pyramid": "diagram",
    "tile_map": "diagram",
    "flow": "diagram",
    "journey": "diagram",
    "layers": "diagram",
    "operating_model": "diagram",
    "architecture": "diagram",
    "comparison": "text",
    "segmentation": "exhibit",
}

# What the slide is trying to SAY (drives visual reasoning). Extended Zelazny.
MESSAGE_TYPES = {
    "single_number": "One figure is the message (a KPI, a size, a gap).",
    "ranking": "Items compared against each other; order matters.",
    "composition": "Parts of a whole at one point in time.",
    "composition_change": "How the mix of a whole changes over time.",
    "trend": "How one or a few measures change over time.",
    "change_bridge": "What explains the change between two values (drivers).",
    "distribution": "How many items fall into ranges.",
    "correlation": "Whether two measures move together.",
    "positioning": "Where items sit on two strategic dimensions.",
    "comparison": "Options/entities compared across several criteria.",
    "segmentation": "The market splits into segments of different size and attractiveness.",
    "sequence": "Steps that happen in order.",
    "plan": "Activities scheduled over time.",
    "hierarchy": "Structure: decomposition, drivers, org.",
    "geography": "Values that vary by location.",
    "flow": "Movement between stages or entities.",
    "structure": "How a system is built (layers, operating model, architecture).",
    "status": "Where things stand vs plan (RAG).",
    "argument": "A qualitative case made of a few reasons.",
    "recommendation": "What to do, with owners and impact.",
}

DECK_TYPES = [
    "strategy_deck",
    "business_review",
    "investment_memo",
    "board_presentation",
    "market_analysis",
    "commercial_due_diligence",
    "transformation_program",
    "operating_model",
    "product_strategy",
    "financial_analysis",
    "sales_strategy",
    "implementation_roadmap",
    "executive_update",
    "project_steering_committee",
]

CONTENT_KINDS = {"content", "exec_summary"}


def load_spec(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_spec(spec: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")


def slide_exhibits(slide: dict) -> list[dict]:
    """All exhibits of a slide, whether given as `visual` or `exhibits`."""
    ex = []
    if isinstance(slide.get("visual"), dict):
        ex.append(slide["visual"])
    ex.extend(slide.get("exhibits") or [])
    return ex


def issue(level: str, code: str, msg: str, slide: str | None = None, **extra) -> dict:
    d = {"level": level, "code": code, "message": msg}
    if slide:
        d["slide"] = slide
    d.update(extra)
    return d


def validate_structure(spec: dict) -> list[dict]:
    """Structural validation. Returns a list of issues (level: error|warning)."""
    out: list[dict] = []
    meta = spec.get("meta") or {}
    if not meta.get("title"):
        out.append(issue("error", "META_TITLE", "meta.title is required"))
    dt = meta.get("deck_type")
    if dt and dt not in DECK_TYPES:
        out.append(issue("warning", "META_DECK_TYPE", f"Unknown deck_type '{dt}'. Known: {', '.join(DECK_TYPES)}"))
    st = spec.get("storyline") or {}
    if not st.get("governing_thought"):
        out.append(issue("error", "STORY_GOVERNING", "storyline.governing_thought (the one-sentence answer) is required"))
    if not st.get("key_line"):
        out.append(issue("error", "STORY_KEYLINE", "storyline.key_line (2-5 supporting arguments) is required"))
    slides = spec.get("slides") or []
    if not slides:
        out.append(issue("error", "NO_SLIDES", "spec.slides is empty"))
    ids = set()
    keyline_ids = {k.get("id") for k in st.get("key_line") or []}
    for i, s in enumerate(slides):
        sid = s.get("id") or f"#{i + 1}"
        if sid in ids:
            out.append(issue("error", "DUP_ID", f"Duplicate slide id '{sid}'", sid))
        ids.add(sid)
        kind = s.get("kind", "content")
        if kind not in SLIDE_KINDS:
            out.append(issue("error", "KIND", f"Unknown slide kind '{kind}'", sid))
        if kind in CONTENT_KINDS:
            for f in ("purpose", "headline"):
                if not s.get(f):
                    out.append(issue("error", "INTENT_MISSING", f"Slide intent incomplete: '{f}' missing", sid))
            if kind == "content":
                if not s.get("evidence"):
                    out.append(issue("warning", "INTENT_EVIDENCE", "No evidence listed: what proves the headline?", sid))
                if not slide_exhibits(s) and not any(s.get(k) for k in ("commentary", "text", "columns", "kpis", "statements")):
                    out.append(issue("error", "NO_BODY", "Slide has no exhibit, commentary or text", sid))
            sec = s.get("section")
            if sec and keyline_ids and sec not in keyline_ids:
                out.append(issue("warning", "SECTION_UNKNOWN", f"section '{sec}' is not a key_line id", sid))
        for ex in slide_exhibits(s):
            vt = ex.get("type", "auto")
            if vt != "auto" and vt not in VISUAL_TYPES:
                out.append(issue("error", "VISUAL_TYPE", f"Unknown visual type '{vt}'", sid))
        mt = s.get("message_type")
        if mt and mt not in MESSAGE_TYPES:
            out.append(issue("warning", "MESSAGE_TYPE", f"Unknown message_type '{mt}'", sid))
    return out


def get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in _split_path(path):
        cur = cur[part]
    return cur


def _split_path(path: str) -> list:
    parts: list = []
    for p in path.replace("]", "").replace("[", ".").split("."):
        if p == "":
            continue
        parts.append(int(p) if p.lstrip("-").isdigit() else p)
    return parts


def apply_patches(spec: dict, patches: list[dict]) -> tuple[dict, list[str]]:
    """Apply agent/auto patches to a spec (returns a new spec + log).

    Patch ops (slide-scoped when `slide` is given, else spec-scoped):
      {"op": "set",    "slide": "s07", "path": "layout", "value": "exhibit_full"}
      {"op": "delete", "slide": "s07", "path": "subheadline"}
      {"op": "append", "slide": "s07", "path": "footnotes", "value": "..."}
      {"op": "insert_slide_after", "slide": "s07", "value": {...slide...}}
      {"op": "remove_slide", "slide": "s07"}
      {"op": "move_slide", "slide": "s07", "after": "s03"}
    """
    new = copy.deepcopy(spec)
    log: list[str] = []
    for p in patches:
        op = p["op"]
        sid = p.get("slide")
        slides = new["slides"]
        idx = next((i for i, s in enumerate(slides) if s.get("id") == sid), None) if sid else None
        if sid and idx is None:
            log.append(f"SKIP {op}: slide '{sid}' not found")
            continue
        target = slides[idx] if idx is not None else new
        if op in ("set", "delete", "append"):
            parts = _split_path(p["path"])
            parent = target
            for part in parts[:-1]:
                if isinstance(parent, dict) and part not in parent:
                    parent[part] = {}
                parent = parent[part]
            last = parts[-1]
            if op == "set":
                parent[last] = p["value"]
            elif op == "delete":
                if isinstance(parent, dict):
                    parent.pop(last, None)
                else:
                    del parent[last]
            else:
                parent.setdefault(last, []).append(p["value"])
            log.append(f"{op} {sid or 'spec'}.{p['path']}")
        elif op == "insert_slide_after":
            slides.insert(idx + 1, p["value"])
            log.append(f"insert {p['value'].get('id')} after {sid}")
        elif op == "remove_slide":
            slides.pop(idx)
            log.append(f"remove {sid}")
        elif op == "move_slide":
            s = slides.pop(idx)
            j = next(i for i, x in enumerate(slides) if x.get("id") == p["after"])
            slides.insert(j + 1, s)
            log.append(f"move {sid} after {p['after']}")
        else:
            log.append(f"SKIP unknown op {op}")
    return new, log
