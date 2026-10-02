"""Is a number in a sentence grounded in a set of facts?

A number is GROUNDED when it equals a cited fact's value (at the precision it is written with), or
is ONE bounded operation (sum, difference, share, ratio) on two cited facts — the same arithmetic
lineage rules as the slide proof check (qa/proof.py). Only the facts the sentence cites count:
never every number in the sources.
"""
from __future__ import annotations

import re

from ..qa.proof import REL_TOL, headline_quantities

SCALE = {"K": 1e3, "M": 1e6, "BN": 1e9}


def fact_scalars(facts: list[dict]) -> list[dict]:
    out = []
    for i, f in enumerate(facts):
        for v in f.get("values") or []:
            unit = (v.get("unit") or "").upper()
            cur, _, sc = unit.partition("_")
            if cur == "PLAIN":
                kind, currency, scale = "plain", None, SCALE.get(sc, 1.0)
            elif cur in ("EUR", "USD", "GBP"):
                kind, currency, scale = "money", cur, SCALE.get(sc, 1.0)
            elif unit == "PCT":
                kind, currency, scale = "pct", None, 1.0
            elif unit == "PP":
                kind, currency, scale = "pp", None, 1.0
            elif unit == "BPS":
                kind, currency, scale = "pp", None, 0.01
            else:
                kind, currency, scale = "plain", None, 1.0
            out.append({"label": f"{f['id']}:{v.get('label') or v.get('period') or ''}", "kind": kind, "currency": currency,
                        "value": abs(float(v["value"])) * scale, "raw": f"{v['value']:g}", "exhibit": i, "fact": f["id"],
                        "assumption": f.get("fact_type") == "assumption" or bool(f.get("rests_on_assumptions"))})
    return out


def _ops(a: dict, b: dict, q: dict):
    if a["kind"] != b["kind"] or a["currency"] != b["currency"]:
        return
    if q["kind"] == a["kind"] and (q["kind"] != "money" or q["currency"] in (None, a["currency"])):
        yield "sum", a["value"] + b["value"]
        yield "difference", abs(a["value"] - b["value"])
    if q["kind"] == "pct" and a["kind"] in ("money", "plain") and b["value"]:
        if a["value"] < b["value"]:
            yield "share", a["value"] / b["value"] * 100
        yield "percent change", abs(a["value"] / b["value"] - 1) * 100
    if q["kind"] == "pp" and a["kind"] == "pct":
        yield "percentage-point change", abs(a["value"] - b["value"])
    if q["kind"] == "x" and b["value"]:
        yield "ratio", a["value"] / b["value"]


def spell_ranges(t: str) -> str:
    """'23–25%' is 23% and 25%; '2024-25' is a period, not 25."""
    t = re.sub(r"\b((?:19|20)\d{2})\s?[-–/]\s?\d{2}\b", r"\1", t)
    return re.sub(r"(\d+(?:[.,]\d+)?)\s?[–-]\s?(\d+(?:[.,]\d+)?)\s?%", r"\1% to \2%", t)


def _unit_scale(s: dict) -> float:
    """The scale a fact's value was multiplied by (EUR_M → 1e6), to compare a bare number as written."""
    try:
        return s["value"] / float(s["raw"]) if float(s["raw"]) else 1.0
    except (ValueError, ZeroDivisionError):
        return 1.0


def _scaled_plain(q: dict, s: dict, tol: float) -> bool:
    """v1.9 (DEBT_V18 U9): a plain number written with a scale word ("4,59 M de líneas", "120k") is
    compared at full scale, against the fact at full scale or in another scale of the same quantity
    (a table of thousands, a unit in millions). Only when the text states the scale."""
    if q["kind"] != "plain" or (q.get("scale") or 1.0) <= 1.0 or s["kind"] != "plain":
        return False
    return any(abs(s["value"] * k - q["value"]) <= tol for k in (1.0, 1e3, 1e6))


def ground_numbers(text: str, facts: list[dict], max_pairs_facts: int = 12) -> list[dict]:
    """Per number in `text`: {"number", "status": grounded|derived|unsupported, "facts": [...]}.
    `facts` must be the facts the sentence CITES, not the whole fact base."""
    scal = fact_scalars(facts)
    out = []
    text = spell_ranges(text)
    for q in headline_quantities(text):
        tol = 0.5 * 10 ** (-q["decimals"]) * (q["scale"] or 1.0) + REL_TOL * q["value"]
        direct = [s for s in scal if (s["kind"] == q["kind"] or q["kind"] == "plain" or (q["kind"] == "x" and s["kind"] == "plain")) and (q["kind"] != "money" or q["currency"] in (None, s["currency"]))
                  and (abs((s["value"] / (1.0 if q["kind"] != "plain" else _unit_scale(s)) if q["kind"] == "plain" else s["value"]) - q["value"]) <= tol
                       or _scaled_plain(q, s, tol))]
        # a bare number ("10.4") may name a fact in its own unit (€10.4M): compared as written
        if direct:
            real = [s for s in direct if not s.get("assumption")]
            out.append({"number": q["raw"], "status": "grounded" if real else "assumption", "facts": sorted({s["fact"] for s in (real or direct)})})
            continue
        if q["kind"] == "plain" and q["value"] <= 30 and float(q["value"]).is_integer():
            # protocol 1.4: small whole counts (people, stores, waves, weeks) are not checked; amounts,
            # percentages, ratios and large counts are. A check must never cost the reader a fact.
            out.append({"number": q["raw"], "status": "grounded", "facts": [], "note": "small count: not checked"})
            continue
        hit = None
        if len({s["fact"] for s in scal}) <= max_pairs_facts:
            for a in scal:
                for b in scal:
                    if a is b or hit:
                        continue
                    for op, res in _ops(a, b, q):
                        if abs(res - q["value"]) <= tol:
                            hit = (op, a, b)
                            break
        if hit:
            out.append({"number": q["raw"], "status": "derived", "facts": sorted({hit[1]["fact"], hit[2]["fact"]}), "operation": hit[0]})
        else:
            out.append({"number": q["raw"], "status": "unsupported", "facts": []})
    return out
