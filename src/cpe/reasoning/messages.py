"""Does each slide's message still hold? (v2.0, item 5)

Updating the numbers of a slide is not enough when its headline claims something the new numbers
contradict: "Las dos fases se pagan en menos de 5 años" with paybacks now of 9,2 and 5,8 years.
`review` reads every headline against the new values of the deck's numbers (approved edits, figures
derived from them, numbers the plan found current) and gives each slide a verdict:

    holds              no figure of the headline changed and no claim it makes is contradicted
    figures updated    its own figures changed; the claims it makes still hold → the headline with the
                       new figures substituted is proposed
    no longer holds    a threshold claim ("menos de 5 años", "más del 20%", "supera …") was true with the
                       old values and is false with the new ones → a mechanical rewrite is proposed for
                       review, never applied silently
    check              a figure of the headline is outdated or untraced and has no approved value

A threshold claim is checked against the slide's numbers written with the same unit word ("años",
"%", "M€") or about the same measure; it must hold with the OLD values, else it is not read as a
claim about them. Proposals become `set_headline` edits, unapproved.
"""
from __future__ import annotations

import re

LESS = r"menos de|por debajo de|inferior(?:es)? a|no supera[n]?|no llega[n]? a|under|less than|below|within|<|≤"
MORE = r"más de|mas de|por encima de|superior(?:es)? a|supera[n]?|above|over|more than|at least|al menos|>|≥"
CLAIM_RE = re.compile(rf"(?P<cmp>{LESS}|{MORE})\s+(?:el|un|una|los|las)?\s*(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>%|años|año|years?|meses|months?|M€|k€|€|x|veces)?", re.I)


def _unit_word(u: str | None) -> str:
    u = (u or "").lower()
    return {"año": "años", "year": "años", "years": "años", "meses": "meses", "month": "meses", "months": "meses",
            "veces": "x"}.get(u, u)


def _num_unit(q: dict) -> str:
    raw = str(q.get("raw", "")).lower()
    for w, u in (("año", "años"), ("year", "años"), ("mes", "meses"), ("%", "%"), ("x", "x"), ("m€", "M€"), ("€", "€")):
        if raw.endswith(w) or (w in ("%", "x") and raw.endswith(w)):
            return u
    ctx = (q.get("context") or "").lower()
    if re.search(r"\(años\)|años\b|years\b", ctx) and not raw.endswith("%"):
        return "años"
    return ""


def new_values(plan: dict, edits: dict) -> dict:
    """{number id: new value in its own units} from approved edits (derived ones included) and the
    numbers the plan found current; a number with neither is absent (unknown)."""
    from .deck_update import _factor, _parse_core

    hint = plan.get("decimal_mark")
    items = {q["id"]: q for s in plan["slides"] for q in s["numbers"] if q.get("id")}
    vals = {i: (-abs(q["value"]) if str(q["raw"]).startswith("-") else q["value"]) for i, q in items.items() if q["status"] == "current"}
    for e in edits.get("edits") or []:
        if e.get("op", "number") == "number" and e.get("approved") and e.get("id") in items:
            q = items[e["id"]]
            f, v = _factor(q, hint), _parse_core(str(e["replace"]).lstrip("-−"), hint)
            if f and v is not None:
                vals[e["id"]] = (-1 if str(e["replace"]).startswith(("-", "−")) else 1) * v * f
    return vals


def _approved_display(edits: dict) -> dict:
    return {e["id"]: e["replace"] for e in edits.get("edits") or [] if e.get("op", "number") == "number" and e.get("approved") and e.get("id")}


def review(plan: dict, edits: dict) -> list[dict]:
    from .deck_update import _parse_core, display_in

    hint = plan.get("decimal_mark")
    vals = new_values(plan, edits)
    shown = _approved_display(edits)
    out = []
    for s in plan["slides"]:
        head = s.get("headline") or ""
        nums = [q for q in s["numbers"] if q.get("id") and q["status"] != "ignored"]
        in_head = [q for q in s["numbers"] if q["where"] == "title" and q["status"] != "ignored"]
        changed = [q for q in in_head if q["id"] in shown and str(shown[q["id"]]) != str(q.get("core"))]
        unknown = [q for q in in_head if q["id"] not in vals and q["id"] not in shown]
        claims = []
        for m in CLAIM_RE.finditer(head):
            unit = _unit_word(m.group("unit"))
            thr = _parse_core(m.group("num"), hint)
            if thr is None or not unit:
                continue
            less = bool(re.fullmatch(LESS, m.group("cmp"), re.I))
            rel = [q for q in nums if q["where"] != "title" and _num_unit(q) == unit]
            parts = [q for q in rel if not re.search(r"\btotal(es)?\b", q.get("context") or "", re.I)]
            rel = parts or rel  # "las dos fases": the phases, not their total column
            if not rel:
                continue
            olds = [abs(q["value"]) for q in rel]
            if not all((v < thr) if less else (v > thr) for v in olds):
                continue  # not a claim about these numbers (it was not true of them)
            news = [vals.get(q["id"]) for q in rel]
            if any(v is None for v in news):
                claims.append({"claim": m.group(0), "status": "cannot check", "unknown": [q["raw"] for q, v in zip(rel, news) if v is None]})
                continue
            holds = all((abs(v) < thr) if less else (abs(v) > thr) for v in news)
            ex = rel[0]
            claims.append({"claim": m.group(0), "status": "holds" if holds else "no longer holds", "span": [m.start(), m.end()],
                           "old": [q["raw"] for q in rel],
                           "new": [display_in(q, abs(v), hint) for q, v in zip(rel, news)], "unit": unit, "ex": ex["raw"]})
        proposal = head
        for q in sorted(changed, key=lambda q: -len(q.get("core") or "")):  # the new figures in the headline
            proposal = re.sub(rf"(?<![\d.,]){re.escape(q['core'])}(?![\d])", str(shown[q["id"]]), proposal, count=1)
        broken = [c for c in claims if c["status"] == "no longer holds"]
        for c in broken:  # mechanical: the threshold phrase becomes the actual values
            vals_txt = _join([v for v in dict.fromkeys(c["new"])])
            proposal = proposal.replace(c["claim"].strip(), f"{vals_txt} {c['unit']}".strip(), 1)
        verdict = ("no longer holds" if broken else "check" if [q for q in unknown if q["status"] in ("outdated", "untraced")]
                   else "figures updated" if changed else "holds")
        out.append({"slide": s["slide"], "headline": head, "verdict": verdict, "claims": claims,
                    "changed": [{"old": q["raw"], "new": shown[q["id"]]} for q in changed],
                    "unresolved": [{"number": q["raw"], "status": q["status"]} for q in unknown if q["status"] in ("outdated", "untraced")],
                    "proposal": proposal if proposal != head else None})
    return out


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def headline_edits(rev: list[dict], edits: dict) -> int:
    """Add a `set_headline` proposal (unapproved) for every slide whose message no longer holds; keep a
    reviewer's own set_headline untouched. Returns how many were added or refreshed."""
    have = {e["slide"]: e for e in edits.get("edits") or [] if e.get("op") == "set_headline"}
    n = 0
    for r in rev:
        if r["verdict"] != "no longer holds" or not r["proposal"]:
            continue
        e = have.get(r["slide"])
        if e and (e.get("approved") or e.get("by_hand")):
            continue
        new = {"op": "set_headline", "slide": r["slide"], "text": r["proposal"], "old": r["headline"], "approved": False,
               "why": "; ".join(f"'{c['claim']}' no longer holds: {', '.join(c['old'])} → {', '.join(c['new'])}" for c in r["claims"]
                                if c["status"] == "no longer holds") + " (mechanical rewrite: check the message)"}
        if e:
            e.clear()
            e.update(new)
        else:
            edits["edits"].append(new)
        n += 1
    return n


def markdown(rev: list[dict]) -> str:
    L = ["# Do the slides' messages still hold?", "", "| slide | verdict | headline | why |", "|---|---|---|---|"]
    for r in rev:
        why = "; ".join([f"'{c['claim']}' {c['status']}" + (f": {', '.join(c['old'])} → {', '.join(c['new'])}" if c.get("new") else "")
                         for c in r["claims"]] + [f"{c['old']} → {c['new']}" for c in r["changed"]]
                        + [f"{u['number']} {u['status']}, no approved value" for u in r["unresolved"]])
        L.append(f"| {r['slide']} | **{r['verdict']}** | {r['headline'][:80]} | {why} |")
    props = [r for r in rev if r["proposal"]]
    if props:
        L += ["", "## Proposed headlines", ""] + [f"- slide {r['slide']} ({r['verdict']}): {r['proposal']}" for r in props]
    return "\n".join(L) + "\n"
