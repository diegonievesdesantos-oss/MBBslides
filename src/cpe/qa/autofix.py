"""Deterministic self-correction: QA issues → spec patches.

The autofix only changes FORM, never the message:
  * a visual encoding the reasoning engine flagged with a concrete fix
    (column → bar for long labels, sort a ranking, time back on the x axis…);
  * the layout, when text or an exhibit does not fit its zone (next eligible
    alternative, tracked so that no layout is tried twice);
Anything that would require rewriting content (headline too long, too many
words, missing source, unsupported number…) becomes a *pending action* for the
author with a precise instruction.
"""
from __future__ import annotations

FIT_CODES = {"TEXT_OVERFLOW", "RENDER_TEXT_SPILL", "CONTENT_OVER_CAPACITY", "OUTSIDE_ZONE", "RENDER_TEXT_COLLISION", "TEXT_COLLISION"}

AGENT_ACTIONS = {
    "HEADLINE_LINES": "Shorten the headline to ≤2 lines (~16-18 words): keep subject + verb + number, drop qualifiers.",
    "RENDER_HEADLINE_LINES": "Shorten the headline to ≤2 lines.",
    "HEADLINE_WIDOW": "Reword the headline so the last line is not a single word.",
    "RENDER_HEADLINE_WIDOW": "Reword the headline so the last line is not a single word.",
    "HEADLINE_TOPIC": "Replace the topic label with a conclusion: what does the data show, and so what?",
    "HEADLINE_PLACEHOLDER": "Write the headline.",
    "HEADLINE_TWO_MESSAGES": "Keep one claim in the headline; move the other to the commentary or its own slide.",
    "HEADLINE_NUMBER_UNSUPPORTED": "Add the evidence that produces this number (evidence[].value) or correct the number.",
    "HEADLINE_LONG": "Cut the headline to the claim.",
    "HEADLINE_VAGUE": "Quantify the claim.",
    "CONTENT_OVER_CAPACITY": "Cut the text (see excess_words) or split the argument across two slides.",
    "DENSITY_WORDS": "Cut words: keep only what proves the headline.",
    "DENSITY_BULLETS": "Keep the 3-4 bullets that prove the headline.",
    "SOURCE_MISSING": "Add the source line (data slides must cite their source).",
    "PLACEHOLDER_TEXT": "Replace the placeholder text.",
    "STORY_NO_EXEC_SUMMARY": "Add an executive summary slide after the cover (answer first).",
    "STORY_UNSUPPORTED_KEYLINE": "Add a slide proving this key-line point or remove the point.",
    "INTENT_MISSING": "Complete the slide intent (purpose + headline) before rendering.",
    "TABLE_OVER_CAPACITY": "Summarise the table to the rows that prove the headline.",
    "AUTO_SPLIT": "Replace the mechanical split by a summary table (top rows + 'Other').",
    "RENDER_TEXT_COLLISION": "Shorten the colliding labels or reduce the number of labelled items.",
    "TEXT_COLLISION": "Shorten the colliding texts or change the layout.",
    "LABEL_COLLISION": "Label only the items that matter (or shorten the labels).",
    "COMPOSITION_DEAD_SPACE": "Content too thin for a full slide: add the proof or merge into a neighbouring slide.",
    "COMPOSITION_UNDERUSED_CANVAS": "Give the exhibit more data/proof or merge the slide.",
    "COMPOSITION_PROOF_NOT_VISIBLE": "Make the headline's number / item visible in the exhibit (label or highlight it).",
    "COMPOSITION_NO_FOCAL_POINT": "Highlight the one element that proves the headline.",
    "COMPOSITION_NOISY_EMPHASIS": "Keep one highlight; grey the context.",
    "COMPOSITION_OVERFILLED": "Cut or split: the content crowds the slide for its type.",
    "COMPOSITION_OVERDENSE": "Cut or split the content.",
    "COMPOSITION_SPARSE": "Add the proof or merge the slide.",
    "COMPOSITION_OFF_BALANCE": "Rebalance: try another layout or add the missing counterpart.",
    "COMPOSITION_WEAK_HIERARCHY": "Make the headline dominate: shorten body text or turn the slide into a statement.",
    "COMPOSITION_RAGGED_ALIGNMENT": "Align the text blocks to fewer left edges.",
    "BRAND_BOOKEND": "Add a closing slide (kind: closing): the brand opens and closes on its colour.",
    "BRAND_COLOUR_SHARE": "Mark the sections with dividers (kind: divider) on the brand colour.",
}


def _exhibit_path(slide: dict, idx: int = 0) -> str:
    if isinstance(slide.get("visual"), dict):
        return "visual" if idx == 0 else f"exhibits[{idx - 1}]"
    return f"exhibits[{idx}]"


def propose(spec: dict, resolved: dict, issues: list[dict], tried: dict) -> tuple[list[dict], list[dict]]:
    """Return (patches, pending_actions)."""
    patches: list[dict] = []
    pending: list[dict] = []
    orig = {s.get("id"): s for s in spec.get("slides", [])}
    res = {s.get("id"): s for s in resolved.get("slides", [])}
    done_slides: set = set()
    for i in issues:
        sid = i.get("slide")
        if not sid:
            continue
        base_id = (res.get(sid) or {}).get("_continuation_of") or sid
        src = orig.get(base_id)
        if src is None:
            continue
        # 1. visual fixes proposed by the reasoning engine
        fix = i.get("fix")
        if fix and i["level"] in ("warning", "error"):
            path = f"{i.get('exhibit_path', _exhibit_path(src))}.{fix['path']}"
            key = (base_id, path, str(fix["value"]))
            if key not in tried.setdefault("visual", set()):
                tried["visual"].add(key)
                patches.append({"op": "set", "slide": base_id, "path": path, "value": fix["value"], "reason": i["code"]})
                continue
        # 2. layout alternatives when something does not fit
        in_body = i.get("zone") not in (None, "chrome") or i["code"] == "CONTENT_OVER_CAPACITY"
        if i["code"] in FIT_CODES and i["level"] == "error" and in_body and base_id not in done_slides:
            if src.get("layout") and src.get("layout") != "auto" and not src.get("_autofix_layout") and not src.get("_composed"):
                pending.append({"slide": base_id, "code": i["code"], "action": "Fixed layout in spec does not fit; " + AGENT_ACTIONS.get(i["code"], "revise content")})
                done_slides.add(base_id)
                continue
            alts = ((res.get(sid) or {}).get("_plan") or {}).get("layout", {}).get("alternatives") or []
            alts = tried.setdefault("alts", {}).setdefault(base_id, alts) or alts
            used = tried.setdefault("layouts", {}).setdefault(base_id, {((res.get(sid) or {}).get("_plan") or {}).get("layout", {}).get("id")})
            nxt = next((a for a in alts if a not in used), None)
            if nxt:
                used.add(nxt)
                patches.append({"op": "set", "slide": base_id, "path": "layout", "value": nxt, "reason": f"{i['code']}: try layout {nxt}"})
                patches.append({"op": "set", "slide": base_id, "path": "_autofix_layout", "value": True, "reason": "marker"})
                done_slides.add(base_id)
                continue
        if i["code"] in AGENT_ACTIONS and i["level"] in ("error", "warning"):
            act = AGENT_ACTIONS[i["code"]]
            if i.get("excess_words"):
                act += f" (≈{i['excess_words']} words over)"
            pending.append({"slide": base_id, "code": i["code"], "action": act})
    # dedupe pending
    seen = set()
    uniq = []
    for a in pending:
        k = (a["slide"], a["code"])
        if k not in seen:
            seen.add(k)
            uniq.append(a)
    return patches, uniq
