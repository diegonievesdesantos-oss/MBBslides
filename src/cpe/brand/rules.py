"""Deck-level brand conventions inferred from the corporate template (editorial advice, not QA).

The ingest infers conventions from how the template's example slides are built (brand/model.py →
`rules`) and stores them in the brand theme (`extras.brand_rules`). A generated deck is checked
against them here. Like composition, these are preferences of the brand system, so they are
reported as editorial advice and never change the QA verdict.
"""
from __future__ import annotations


def deck_advice(resolved: dict, manifests: list[dict], theme) -> list[dict]:
    rules = (theme.extras or {}).get("brand_rules") or {}
    slides = resolved.get("slides") or []
    if not rules or not slides:
        return []
    out = []
    kinds = [s.get("kind", "content") for s in slides]
    native = {m.get("slide_id") for m in manifests if (m.get("corporate") or {}).get("mode") == "native"}
    if rules.get("bookend"):
        first_ok = kinds[0] == "cover"
        last_ok = kinds[-1] in ("closing", "divider") and slides[-1].get("id") in native
        if not (first_ok and last_ok):
            missing = " and ".join(x for x, ok in (("open", first_ok), ("close", last_ok)) if not ok)
            out.append({"level": "advice", "code": "BRAND_BOOKEND", "slide": slides[-1].get("id") if not last_ok else slides[0].get("id"),
                        "message": f"The template's example decks open and close on the brand colour (bookend); this deck does not {missing} that way: "
                                   "add a closing slide (kind: closing) — it is generated on the template's own layout."})
    share = rules.get("brand_colour_slide_share")
    if share and share >= 0.15 and len(slides) >= 5:
        coloured = sum(1 for s in slides if s.get("id") in native and s.get("kind") in ("cover", "divider", "appendix_divider", "closing"))
        if coloured / len(slides) < share * 0.6:
            out.append({"level": "advice", "code": "BRAND_COLOUR_SHARE", "slide": None,
                        "message": f"{coloured}/{len(slides)} slides on the brand colour vs ~{round(100 * share)}% in the template's examples: "
                                   "the brand marks sections with brand-colour dividers (kind: divider)."})
    return out
