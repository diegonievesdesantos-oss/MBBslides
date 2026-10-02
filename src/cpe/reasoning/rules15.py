"""Protocol 1.5 checks: the owner's review of the first real-project update (v1.8).

The v1 deck got every figure right but reasoned badly in five ways. The checks below catch what can
be caught from the artifacts; everything is a warning or info (they ask a question, they do not
block), like the 1.1 / 1.2 decision frame.

R1 contingency      an investment option carries a contingency (or the overrun of a comparable past
                    project) in its cost_components, or the decision states why none applies.
R2 decision design  gates state a threshold with margin over the break-even and a test long enough
                    to avoid the bias of a short, coached trial; when a counterparty's price or
                    deadline is involved, renegotiating and deferring are options.
R3 discarded        evidence an insight classes as unrepresentative (`discards`) is not used later
                    to support another claim.
R4 coherence        numbers in the executive summary and in headlines are not grounded only in
                    assumptions; a rejected hypothesis is not revived as a risk.
R5 checklist        the partner review records capacity, sunk costs, contingency, external
                    deadlines and unsourced history (state "no finding" when it does not apply).
"""
from __future__ import annotations

import re

from .grounding import ground_numbers

GATE_MARGIN = 0.05        # a gate's threshold must clear the break-even by at least 5%
GATE_MIN_WEEKS = 8        # a sustained-performance test shorter than this repeats the SAT bias
INVEST = re.compile(r"inver|capex|invest|price|precio|sistema|obra", re.I)
CONTINGENCY = re.compile(r"conting|overrun|sobrecoste|desv", re.I)
PRICE_OR_DEADLINE = re.compile(r"precio|price|oferta|offer|proveedor|supplier|vendor|plazo|deadline", re.I)


def _issue(level, code, artifact, ref, message, hard=False):
    return {"level": level, "code": code, "artifact": artifact, "ref": ref, "message": message, "hard": hard}


def check_decision_15(sl: dict | None) -> list[dict]:
    d = (sl or {}).get("decision") or {}
    if not d:
        return []
    out = []
    opts = d.get("options") or []
    # R1: contingency on investment options
    inv = [o for o in opts if any(INVEST.search(k) for k in (o.get("cost_components") or {}))]
    if inv and not d.get("contingency") and not any(CONTINGENCY.search(k) for o in inv for k in o.get("cost_components") or {}):
        out.append(_issue("warning", "CONTINGENCY_MISSING", "storyline.json", "options",
                          "investment options carry no contingency: if a comparable past phase or project overran, carry that overrun (or a stated "
                          "contingency) into the cost and show the threshold with and without it; set decision.contingency with the reason if none applies"))
    # R2: gates with margin and a long-enough test
    for g in d.get("gates") or []:
        ref = g.get("statement", "")[:40]
        thr, be = g.get("threshold"), g.get("break_even")
        if thr is not None and be is not None:
            try:
                thr, be = float(thr), float(be)
                if be and (thr - be) / abs(be) < GATE_MARGIN:
                    out.append(_issue("warning", "GATE_NO_MARGIN", "storyline.json", ref,
                                      f"threshold {thr:g} is within {GATE_MARGIN:.0%} of the break-even {be:g}: the gate must clear it with margin"))
            except (TypeError, ValueError):
                pass
        elif re.search(r"\d", g.get("criterion", "")):
            out.append(_issue("info", "GATE_UNQUANTIFIED", "storyline.json", ref, "state the gate's threshold and break_even so its margin can be checked"))
        wk = g.get("period_weeks")
        if wk is not None and float(wk) < GATE_MIN_WEEKS:
            out.append(_issue("warning", "GATE_SHORT_TEST", "storyline.json", ref,
                              f"a {float(wk):g}-week test after targeted training repeats the bias of an acceptance test: sustain it for {GATE_MIN_WEEKS} weeks or more"))
    text = " ".join([d.get("current_plan", {}).get("statement", "")] + [o.get("statement", "") for o in opts]
                    + [k for o in opts for k in (o.get("cost_components") or {})])
    kinds = {(o.get("kind") or "").lower() for o in opts}
    if inv or PRICE_OR_DEADLINE.search(text) or d.get("external_deadline"):
        if not kinds & {"renegotiate", "renegociar"}:
            out.append(_issue("warning", "OPTION_RENEGOTIATE_MISSING", "storyline.json", "options",
                              "a counterparty's price or deadline is involved: compare renegotiating (price, payment tied to performance) as an option (kind: renegotiate)"))
        if not kinds & {"defer", "aplazar"}:
            out.append(_issue("warning", "OPTION_DEFER_MISSING", "storyline.json", "options",
                              "compare deferring the decision (kind: defer); a counterparty's deadline is a negotiation fact, not a decision criterion"))
    return out


def check_discarded(ins: dict | None, deck: dict | None) -> list[dict]:
    """R3: facts an insight discards (`discards`) must not support another insight or a slide claim."""
    insights = (ins or {}).get("insights") or []
    discarded = {}
    for x in insights:
        for f in x.get("discards") or []:
            discarded[f] = x["id"]
    out = []
    for x in insights:
        for f in x.get("facts") or []:
            if f in discarded and discarded[f] != x["id"] and f not in (x.get("discards") or []):
                out.append(_issue("warning", "DISCARDED_EVIDENCE_REUSED", "insights.json", x["id"],
                                  f"{f} was classed as unrepresentative in {discarded[f]} and now supports this insight"))
    for s in (deck or {}).get("slides") or []:
        if s.get("kind") != "cover":
            for e in s.get("evidence") or []:
                if isinstance(e, dict) and e.get("fact") in discarded and not e.get("as_discarded"):
                    out.append(_issue("warning", "DISCARDED_EVIDENCE_REUSED", "deck.json", s.get("id"),
                                      f"cites {e['fact']}, classed as unrepresentative in {discarded[e['fact']]}; mark the evidence item \"as_discarded\": true if it is shown only to be set aside"))
    return out


def check_assumptions_in_summary(deck: dict | None, facts: dict) -> list[dict]:
    """R4: a number in the executive summary or a headline that only an assumption supports."""
    out = []
    for s in (deck or {}).get("slides") or []:
        cited = [facts[e["fact"]] for e in s.get("evidence") or [] if isinstance(e, dict) and e.get("fact") in facts]
        if not cited:
            continue
        texts = [("headline", s.get("headline", ""))]
        if s.get("kind") == "exec_summary":
            for i, it in enumerate(((s.get("visual") or {}).get("data") or {}).get("items") or []):
                texts += [(f"items[{i}]", it.get("title", "")), (f"items[{i}].text", it.get("text", ""))]
        for where, t in texts:
            for g in ground_numbers(t, cited):
                if g["status"] == "assumption":
                    out.append(_issue("warning", "ASSUMPTION_IN_SUMMARY", "deck.json", f"{s.get('id')}:{where}",
                                      f"{g['number']} rests only on an assumption: keep it out of headlines and the summary, or label it as an assumption"))
    return out


def check_rejected_revived(sl: dict | None, hyps: dict) -> list[dict]:
    """R4: a rejected hypothesis cited as a risk or as support of an option."""
    out = []
    d = (sl or {}).get("decision") or {}
    for o in d.get("options") or []:
        for h in o.get("risks_from") or []:
            if (hyps.get(h) or {}).get("status") == "rejected":
                out.append(_issue("warning", "REJECTED_HYPOTHESIS_REVIVED", "storyline.json", o.get("id"),
                                  f"uses rejected hypothesis {h} as a risk: what the analysis rejected cannot argue for or against an option"))
    return out


CHECKLIST = {
    "capacity": r"capacid|capacity|satur",
    "sunk_costs": r"hundid|sunk",
    "contingency": r"conting|sobrecoste|overrun",
    "external_deadline": r"plazo|deadline|fecha (?:del|de la) (?:proveedor|oferta)",
    "unsourced_history": r"sin fuente|unsourced|no source|histór|historic",
}


def check_partner_checklist(cr: dict | None) -> list[dict]:
    """R5: the partner review states each checklist item, even as 'no finding'."""
    if not cr:
        return []
    txt = " ".join(f"{f.get('finding', '')} {f.get('action', '')}" for f in cr.get("findings") or [] if f.get("critic") == "PARTNER REVIEW")
    if not txt:
        return []
    missing = [k for k, rx in CHECKLIST.items() if not re.search(rx, txt, re.I)]
    return [_issue("info", "PARTNER_CHECKLIST", "critique.json", "PARTNER REVIEW",
                   f"partner review does not address: {', '.join(missing)} (state 'no finding' when it does not apply)")] if missing else []
