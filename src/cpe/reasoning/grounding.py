"""Is a number in a sentence grounded in a set of facts?

A number is GROUNDED when it equals a cited fact's value (at the precision it is written with), or
is ONE bounded operation (sum, difference, share, ratio) on two cited facts — the same arithmetic
lineage rules as the slide proof check (qa/proof.py). Only the facts the sentence cites count:
never every number in the sources.
"""
from __future__ import annotations

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


def ground_numbers(text: str, facts: list[dict], max_pairs_facts: int = 12) -> list[dict]:
    """Per number in `text`: {"number", "status": grounded|derived|unsupported, "facts": [...]}.
    `facts` must be the facts the sentence CITES, not the whole fact base."""
    scal = fact_scalars(facts)
    out = []
    for q in headline_quantities(text):
        tol = 0.5 * 10 ** (-q["decimals"]) * (q["scale"] or 1.0) + REL_TOL * q["value"]
        direct = [s for s in scal if s["kind"] == q["kind"] and (q["kind"] != "money" or q["currency"] in (None, s["currency"]))
                  and abs(s["value"] - q["value"]) <= tol]
        if direct:
            real = [s for s in direct if not s.get("assumption")]
            out.append({"number": q["raw"], "status": "grounded" if real else "assumption", "facts": sorted({s["fact"] for s in (real or direct)})})
            continue
        if q["kind"] == "plain" and q["value"] < 10:
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
