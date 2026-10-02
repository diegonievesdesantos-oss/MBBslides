"""Editorial compiler (v3.1, spec §75): the deck's wording contract, settled before composition and planning.

    compile_editorial(spec, profile=None, mode=None) → (compiled_spec, editorial_report)

     1. normalise propositions (explicit, or provisional from the headline in `standard`)
     2. validate their lineage (evidence / analysis ids, the magnitude's numbers)
     3. classify the headline type each proposition calls for
     4. collect candidates (`headline`, `headline_candidates`)
     5. validate every candidate (core/headline lint + proposition fidelity)
     6. select one (lexicographic ranking; a safe deterministic rewrite only when the proposition fixes it)
     7. detect parallel groups      8. establish their signatures      9. request rewrites (never silent)
    10. validate the groups        11. horizontal logic (key line, exec summary, orphans, strip)
    12. the report                 13. the compiled spec (`_editorial` on every slide)

Modes (meta.editorial_mode, spec §56): `mbb_strict` (hard findings are errors), `standard` (the
default for specs that do not say: hard findings are warnings, missing propositions are inferred),
`legacy` (report only, nothing rewritten). `cpe scaffold` writes `mbb_strict` into every new deck.

Deterministic and idempotent: the same spec gives the same result, and compiling a compiled spec
changes nothing (the selected headline is a candidate of the next run, and wins again).
"""
from __future__ import annotations

import copy
import re

from . import action_titles as ate
from . import parallel as pwg
from . import proposition as P
from .qa import horizontal
from .signatures import language

MODES = ("mbb_strict", "standard", "legacy")
LEVEL = {"mbb_strict": {"hard": "error", "soft": "warning", "info": "info"},
         "standard": {"hard": "warning", "soft": "info", "info": "info"},
         "legacy": {"hard": "info", "soft": "info", "info": "info"}}


def mode_of(spec: dict, override: str | None = None) -> str:
    m = override or (spec.get("meta") or {}).get("editorial_mode") or "standard"
    if m not in MODES:
        raise ValueError(f"Unknown editorial_mode '{m}' (known: {', '.join(MODES)})")
    return m


def deck_language(spec: dict) -> str | None:
    meta = spec.get("meta") or {}
    if meta.get("language") in ("es", "en"):
        return meta["language"]
    votes = {"es": 0, "en": 0}
    for s in spec.get("slides") or []:
        lg = language(" ".join(str(s.get(k) or "") for k in ("headline", "text", "purpose")))
        if lg:
            votes[lg] += 1
    tot = votes["es"] + votes["en"]
    if not tot or min(votes.values()) >= 0.2 * tot:
        return None  # a bilingual deck (an archetype battery) has no single language to enforce: set meta.language
    return max(votes, key=votes.get)


def _ctx(spec: dict, profile: dict | None) -> dict:
    from ..core.headline import _collect_values, derivable, numbers_in

    meta = spec.get("meta") or {}
    vals: list[float] = []
    for sl in spec.get("slides") or []:
        if sl.get("kind", "content") == "content":
            v, t = _collect_values(sl)
            vals += list(derivable(v)) + [n for tt in t + [sl.get("headline", "")] for n, _ in numbers_in(tt)]
    year = None
    m = re.search(r"(?:19|20)\d\d", str(meta.get("date") or ""))
    if m:
        year = int(m.group(0))
    st = spec.get("storyline") or {}
    deck_text = " ".join(str(x or "") for x in [meta.get("title"), meta.get("subtitle"), meta.get("client"), st.get("governing_thought")]
                         + [k.get("message") for k in st.get("key_line") or []])
    return {"profile": profile or {}, "lang": deck_language(spec), "deck_values": vals, "deck_year": year, "deck_text": deck_text,
            "capitalization": ((meta.get("editorial") or {}).get("capitalization") or "sentence")}


def compile_editorial(spec: dict, profile: dict | None = None, mode: str | None = None) -> tuple[dict, dict]:
    if profile is None:
        from ..core.planner import profile_for

        profile = profile_for(spec)
    out = copy.deepcopy(spec)
    mode = mode_of(out, mode)
    lv = LEVEL[mode]
    ctx = _ctx(out, profile)
    universe = P.evidence_universe(out)
    findings: list[dict] = []
    props: dict[str, dict] = {}
    slides_rep = []
    for s in out.get("slides") or []:
        kind = s.get("kind", "content")
        sid = s.get("id")
        s.pop("_editorial", None)
        if kind in ate.EXEMPT_KINDS:
            s["_editorial"] = {"compiled": True, "exempt": True, "status": "exempt", "reason": f"{kind}: a title-style label is allowed (spec §41)"}
            slides_rep.append({"slide": sid, "kind": kind, "status": "exempt"})
            continue
        if kind not in ate.ACTION_KINDS:
            continue
        if kind == "statement" and not s.get("proposition") and mode != "mbb_strict":
            s["_editorial"] = {"compiled": True, "status": "not_checked", "reason": "statement slide without proposition (standard mode)"}
            continue
        sf: list[dict] = []
        raw = s.get("proposition")
        if isinstance(raw, dict) and raw:
            prop = raw
        elif mode == "mbb_strict":
            prop = None
            sf.append(_fd("PROPOSITION_MISSING", "hard", "Strict content slide without a proposition: state what it asserts, about what, with what evidence (spec §55)", sid))
        else:
            prop = P.infer(s)
            if mode == "standard":
                sf.append(_fd("PROPOSITION_INFERRED", "soft", "No proposition: a provisional one was inferred from the headline and message type (spec §98)", sid))
        if prop is not None and not prop.get("_inferred"):
            for code, cls, msg in P.validate(prop, s, universe):
                sf.append(_fd(code, cls, msg, sid))
        if prop:
            props[sid] = prop
        sel = ate.select(s, prop, ctx, allow_rewrite=mode != "legacy")
        best = sel["selected"]
        field = ate.title_field(s)
        before = s.get(field)
        if mode != "legacy" and best["passed"] and best["text"] != (before or ""):
            s[field] = best["text"]
            how = "deterministic rewrite: " + best.get("derivation", "") if best["origin"] == "deterministic" else f"selected {best['origin']}"
            sf.append(_fd("HEADLINE_SELECTED", "info", f"'{before}' → '{best['text']}' ({how})", sid))
        shown = best if (best["passed"] or mode == "legacy") else next(e for e in sel["candidates"] if e["origin"] == "headline")
        for code, cls, msg in shown["issues"]:
            sf.append(_fd(code, cls, msg, sid))
        if not best["passed"]:
            exp = (prop or {}).get("statement")
            sf.append(_fd("HEADLINE_UNRESOLVED", "hard", f"No acceptable action title among {len(sel['candidates'])} candidate(s)"
                          + (f". Expected proposition: \"{exp}\"" if exp else "") + ". Regenerate the headline (or add headline_candidates).", sid))
        status = "failed" if any(f["class"] == "hard" for f in sf) else "passed"
        idx = next((i for i, e in enumerate(sel["candidates"]) if e is best), 0)
        s["_editorial"] = {
            "compiled": True, "mode": mode, "status": status, "headline_score": best["score"], "dimensions": best["dimensions"],
            "headline_type": best["headline_type"], "observed_type": best["observed_type"], "signature": best["signature"],
            "proposition_fidelity": "failed" if set(best["hard"]) & ate.FIDELITY else "passed",
            "evidence_support": "failed" if "HEADLINE_NUMBER_UNSUPPORTED" in best["hard"] or any(f["code"] in ("PROPOSITION_NO_LINEAGE", "PROPOSITION_NUMBER_UNSUPPORTED", "PROPOSITION_EVIDENCE_UNRESOLVED") for f in sf) else "passed",
            "proposition": "inferred" if (prop or {}).get("_inferred") else "explicit" if prop else "missing",
            "candidate_count": len(sel["candidates"]), "selected_candidate": idx, "selected_origin": best["origin"],
            "reasons": [f["code"] for f in sf if f["class"] != "info"],
        }
        slides_rep.append({"slide": sid, "kind": kind, "status": status, "headline": s.get(field), "was": before if before != s.get(field) else None,
                           "proposition": prop, "score": best["score"], "dimensions": best["dimensions"], "headline_type": best["headline_type"],
                           "signature": best["signature"], "candidates": [{"origin": e["origin"], "text": e["text"], "passed": e["passed"], "score": e["score"],
                                                                         "hard": e["hard"], **({"derivation": e["derivation"]} if e.get("derivation") else {})}
                                                                        for e in sel["candidates"]],
                           "findings": sf})
        findings += sf
    # parallel groups
    groups = [pwg.check(g, ctx["lang"]) for g in pwg.detect(out)] if mode != "legacy" or True else []
    gfind = []
    for g in groups:
        for f in g["findings"]:
            slide = next((m.get("slide") for m in g["members"] if m["ref"] in f["members"]), None) or (g["members"][0].get("slide") if g["members"] else None)
            gfind.append(_fd(f["code"], f["class"], f"[{g['id']}] {f['message']}", slide, group=g["id"]))
        for m in g["members"]:
            s = next((x for x in out.get("slides") or [] if x.get("id") == m.get("slide")), None)
            if s is not None and m["ref"].endswith(".headline") and "_editorial" in s:
                s["_editorial"].update(parallel_group=g["id"], parallel_status=g["status"])
    findings += gfind
    hfind, strip = horizontal(out, ctx["lang"], props)
    findings += [_fd(f["code"], f["class"], f["message"], f.get("slide")) for f in hfind]
    for f in findings:
        f["level"] = lv[f["class"]]
    for s in out.get("slides") or []:
        ed = s.get("_editorial")
        if ed and ed.get("status") not in ("exempt", "not_checked"):
            mine = [f for f in findings if f.get("slide") == s.get("id") and f["level"] == "error"]
            ed["status"] = "failed" if mine else "passed"
    errors = [f for f in findings if f["level"] == "error"]
    for r in slides_rep:
        if r.get("status") not in ("exempt",):
            r["status"] = "failed" if any(f.get("slide") == r["slide"] and f["level"] == "error" for f in findings) else "passed"
    checked = [r for r in slides_rep if r["status"] != "exempt"]
    mand = [g for g in groups if g["mandatory"]]
    report = {
        "mode": mode, "language": ctx["lang"], "passed": not errors,
        "summary": {
            "slides_checked": len(checked), "slides_passed": sum(r["status"] == "passed" for r in checked),
            "hard_errors": len(errors), "warnings": sum(f["level"] == "warning" for f in findings),
            "mean_headline_score": round(sum(r["score"] for r in checked) / len(checked), 1) if checked else None,
            "propositions": {"explicit": sum(1 for r in checked if r.get("proposition") and not r["proposition"].get("_inferred")),
                             "inferred": sum(1 for r in checked if r.get("proposition") and r["proposition"].get("_inferred")),
                             "missing": sum(1 for r in checked if not r.get("proposition"))},
            "headlines_selected": sum(1 for f in findings if f["code"] == "HEADLINE_SELECTED"),
            "groups_checked": len(groups), "mandatory_groups": len(mand),
            "mandatory_groups_passed": sum(g["status"] != "failed" for g in mand),
            "orphan_propositions": sum(f["code"] == "ORPHAN_PROPOSITION" for f in findings),
            "unsupported_keyline_points": sum(f["code"] == "KEYLINE_UNSUPPORTED" for f in findings),
            "strip_coherence": strip["coherence"],
        },
        "slides": slides_rep, "groups": groups, "strip": strip, "findings": findings,
    }
    return out, report


def _fd(code: str, cls: str, message: str, slide: str | None = None, **kw) -> dict:
    return {"code": code, "class": cls, "message": message, "slide": slide, **kw}


def strip_editorial(spec: dict) -> dict:
    """The authoring spec without the compiler's diagnostic metadata (spec §40: it must not contaminate the contract)."""
    out = copy.deepcopy(spec)
    for s in out.get("slides") or []:
        s.pop("_editorial", None)
    return out
