"""The slide proposition: the semantic contract of a slide (v3.1, spec §5-7).

    purpose      what the slide must achieve        "Show why gross margin declined"
    proposition  what the slide asserts (semantic)  {"statement": "...", "role": "diagnosis", "claim_type": "driver", ...}
    headline     how it is said (final copy)        "Electronics mix explains most of the 1.9 pp gross-margin decline"

Three different objects. The headline may be rewritten; the proposition may not be changed by the
wording layer (only by reasoning, upstream).

Backwards compatibility (spec §98): a slide without `proposition`
    legacy      nothing required
    standard    a provisional proposition is inferred from headline / purpose / message_type / evidence
                and marked `_inferred` (a warning)
    mbb_strict  PROPOSITION_MISSING (an error): an inferred proposition never satisfies strict mode
"""
from __future__ import annotations

import re

ROLES = ("context", "observation", "diagnosis", "driver", "comparison", "insight", "implication", "recommendation",
         "decision", "risk", "status", "impact", "implementation")
CLAIM_TYPES = ("fact", "trend", "comparison", "composition", "driver", "causal", "constraint", "risk", "opportunity",
               "recommendation", "decision", "impact", "status")
CONFIDENCE = ("high", "medium", "low")
FIELDS = ("statement", "role", "claim_type", "subject", "predicate", "direction", "magnitude", "comparison", "driver",
          "implication", "recommended_action", "decision", "timeframe", "scope", "qualifiers", "evidence_ids",
          "analysis_ids", "confidence")
# story roles (spec §64) → the closest proposition role
STORY_ROLES = {"context": "context", "problem": "observation", "diagnosis": "diagnosis", "driver": "driver",
               "implication": "implication", "option": "comparison", "recommendation": "recommendation", "impact": "impact",
               "plan": "implementation", "risk": "risk", "decision": "decision"}
# message_type → (role, claim_type) for the provisional proposition of a legacy slide
MESSAGE_ROLE = {
    "single_number": ("observation", "fact"), "ranking": ("comparison", "comparison"), "composition": ("observation", "composition"),
    "composition_change": ("observation", "composition"), "trend": ("observation", "trend"), "change_bridge": ("driver", "driver"),
    "distribution": ("observation", "fact"), "correlation": ("observation", "comparison"), "positioning": ("comparison", "comparison"),
    "causality": ("driver", "driver"), "comparison": ("comparison", "comparison"), "segmentation": ("observation", "composition"),
    "sequence": ("implementation", "fact"), "plan": ("implementation", "fact"), "hierarchy": ("diagnosis", "driver"),
    "geography": ("observation", "comparison"), "flow": ("observation", "fact"), "structure": ("implementation", "fact"),
    "status": ("status", "status"), "argument": ("insight", "fact"), "recommendation": ("recommendation", "recommendation"),
}
UP = re.compile(r"^(?:up|increase[sd]?|increasing|growth|grow|grew|grows|rise|rising|rose|higher|improve[sd]?|improvement|positive|gain|"
                r"expand|expansion|accelerat\w*|widen\w*|recover\w*|crec\w*|sub\w*|aument\w*|mejor\w*|alza|al alza|positiv[oa]|"
                r"ampl\w*|acelera\w*|duplica\w*)$", re.I)
DOWN = re.compile(r"^(?:down|decrease[sd]?|decreasing|decline[sd]?|declining|fall|falling|fell|drop|dropped|lower|negative|loss|"
                  r"erosion|erode[sd]?|shrink\w*|contract\w*|deteriorat\w*|worsen\w*|slow\w*|narrow\w*|reduc\w*|cut|"
                  r"ca[eí]\w*|baj\w*|disminu\w*|descen\w*|negativ[oa]|p[eé]rdida|erosi[oó]n|retroce\w*|empeor\w*|contrac\w*|"
                  r"reducci[oó]n|desaceler\w*|recort\w*)$", re.I)
FLAT = re.compile(r"^(?:flat|stable|unchanged|steady|stagnant|stagnat\w*|estable|plan[oa]|estancad[oa]|sin cambios)$", re.I)


def direction_of(value) -> str | None:
    """Normalise a proposition's direction to up / down / flat (None when it is not a direction)."""
    v = str(value or "").strip().lower()
    if not v:
        return None
    if UP.match(v):
        return "up"
    if DOWN.match(v):
        return "down"
    if FLAT.match(v):
        return "flat"
    return None


def text_of(p: dict) -> str:
    """Every word the proposition commits to (what the headline may legitimately say)."""
    parts = [p.get(k) for k in ("statement", "subject", "predicate", "comparison", "driver", "implication", "recommended_action",
                                "decision", "timeframe", "scope", "magnitude")]
    parts += list(p.get("qualifiers") or [])
    return " ".join(str(x) for x in parts if x)


def infer(slide: dict) -> dict:
    """Provisional proposition of a legacy slide: its own headline, read with the message type's role.
    Marked `_inferred` so strict mode never accepts it."""
    from .signatures import analyze

    head = slide.get("headline") or slide.get("text") or ""
    role, claim = MESSAGE_ROLE.get(slide.get("message_type") or "", ("insight", "fact"))
    if slide.get("story_role") in STORY_ROLES:
        role = STORY_ROLES[slide["story_role"]]
    if slide.get("kind") == "exec_summary":
        role, claim = "insight", "fact"
    a = analyze(head)
    if a["family"] == "action" and role not in ("recommendation", "decision"):
        role, claim = "recommendation", "recommendation"
    ev = [e.get("id") for e in slide.get("evidence") or [] if isinstance(e, dict) and e.get("id")]
    return {"statement": head, "role": role, "claim_type": claim, "evidence_ids": ev or ([f"evidence[{i}]" for i in range(len(slide.get("evidence") or []))]),
            "confidence": "medium", "_inferred": True, "_from": "headline + message_type (provisional, spec §98)"}


def evidence_universe(spec: dict) -> set[str]:
    """Ids a proposition may cite: slide evidence ids anywhere in the deck, deck-level facts/evidence/analyses,
    key-line ids (an executive summary proves the key line) and, when given, the fact model's ids."""
    ids: set[str] = set()
    for s in spec.get("slides") or []:
        for i, e in enumerate(s.get("evidence") or []):
            if isinstance(e, dict) and e.get("id"):
                ids.add(str(e["id"]))
    for k in ("facts", "evidence", "analyses"):
        for e in spec.get(k) or []:
            if isinstance(e, dict) and e.get("id"):
                ids.add(str(e["id"]))
    for k in (spec.get("storyline") or {}).get("key_line") or []:
        if k.get("id"):
            ids.add(str(k["id"]))
    fm = (spec.get("meta") or {}).get("fact_model")
    if fm:
        import json
        from pathlib import Path

        try:
            data = json.loads(Path(fm).read_text(encoding="utf-8"))
            for f in data.get("facts") or []:
                if isinstance(f, dict) and f.get("id"):
                    ids.add(str(f["id"]))
            for a in data.get("analyses") or []:
                if isinstance(a, dict) and a.get("id"):
                    ids.add(str(a["id"]))
        except (OSError, ValueError):
            pass
    return ids


def validate(p: dict, slide: dict, universe: set[str]) -> list[tuple[str, str, str]]:
    """(code, severity class, message) for a proposition: 'hard' fails strict mode, 'soft' warns."""
    from ..core.headline import unsupported_numbers

    out = []
    if not isinstance(p, dict):
        return [("PROPOSITION_MISSING", "hard", "`proposition` must be an object")]
    st = str(p.get("statement") or "").strip()
    if not st or "TODO" in st or re.search(r"\[[^\]]+\]", st):
        out.append(("PROPOSITION_PLACEHOLDER", "hard", "proposition.statement is missing or still a placeholder: say exactly what the slide asserts"))
    if p.get("role") and p["role"] not in ROLES:
        out.append(("PROPOSITION_ROLE", "soft", f"Unknown proposition role '{p['role']}' (known: {', '.join(ROLES)})"))
    if not p.get("role"):
        out.append(("PROPOSITION_ROLE", "soft", "proposition.role is missing: what does this slide do in the argument?"))
    if p.get("claim_type") and p["claim_type"] not in CLAIM_TYPES:
        out.append(("PROPOSITION_CLAIM_TYPE", "soft", f"Unknown claim_type '{p['claim_type']}' (known: {', '.join(CLAIM_TYPES)})"))
    if not p.get("claim_type"):
        out.append(("PROPOSITION_CLAIM_TYPE", "soft", "proposition.claim_type is missing: causal, comparative and recommendation wording depend on it"))
    if p.get("confidence") and p["confidence"] not in CONFIDENCE:
        out.append(("PROPOSITION_CONFIDENCE", "soft", f"Unknown confidence '{p['confidence']}' (high / medium / low)"))
    ev, an = list(p.get("evidence_ids") or []), list(p.get("analysis_ids") or [])
    if not ev and not an:
        out.append(("PROPOSITION_NO_LINEAGE", "hard", "The proposition cites no evidence_ids or analysis_ids: what proves it?"))
    n_ev = len(slide.get("evidence") or [])
    unresolved = [i for i in ev + an if str(i) not in universe and not _index_ref(str(i), n_ev)]
    if unresolved and universe:
        out.append(("PROPOSITION_EVIDENCE_UNRESOLVED", "hard", f"evidence/analysis ids {unresolved} are not in the deck's evidence, facts or analyses"))
    elif unresolved:
        out.append(("PROPOSITION_EVIDENCE_UNVERIFIED", "soft", f"ids {unresolved} cannot be checked: the deck carries no evidence ids (set meta.fact_model or give evidence ids)"))
    from .action_titles import CAUSAL_C, CAUSAL_OK_C

    if CAUSAL_C.search(st) and p.get("claim_type") and p["claim_type"] not in CAUSAL_OK_C:
        out.append(("PROPOSITION_CAUSAL_TYPE", "soft", f"The proposition itself uses causal wording ('{CAUSAL_C.search(st).group(0)}') on a "
                    f"{p['claim_type']} claim: make it a causal/driver claim with evidence, or say 'is associated with'"))
    mag = str(p.get("magnitude") or "")
    if mag and slide.get("kind", "content") == "content":
        bad = unsupported_numbers(mag, slide)
        if bad:
            out.append(("PROPOSITION_NUMBER_UNSUPPORTED", "hard", f"proposition.magnitude '{mag}' is not in / derivable from the slide's evidence or exhibit"))
    return out


def _index_ref(ref: str, n: int) -> bool:
    m = re.fullmatch(r"evidence\[(\d+)\]", ref)
    return bool(m) and int(m.group(1)) < n
