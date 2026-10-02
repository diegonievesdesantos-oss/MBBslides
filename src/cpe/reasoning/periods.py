"""Period semantics (v1.8): what a period label means, and when two periods must not be compared.

Real material mixes FY2024, FY25E, LTM, YTD, Q3, run-rate, calendar and fiscal years. Comparing an
LTM figure with a quarter, a YTD figure with a full year, a budget with an actual, or a run-rate with
a reported year is a classic consulting error. The fact model records each value's period and basis;
these helpers say what each one is and flag incompatible combinations. A flag is a warning, never
a block: some comparisons are deliberate ("actual vs budget"), and the agent then says so.

    period_info("FY2025")   → {"kind": "FY", "months": 12, "year": 2025, "fiscal": True}
    period_info("2025-Q3")  → {"kind": "Q", "months": 3, "year": 2025}
    period_info("LTM")      → {"kind": "LTM", "months": 12}
    compare(a, b)           → None if comparable, else the reason they are not
"""
from __future__ import annotations

import re

MONTHS = {"Q": 3, "H": 6, "FY": 12, "CY": 12, "YEAR": 12, "LTM": 12, "TTM": 12, "MONTH": 1}


def period_info(period: str | None) -> dict:
    p = str(period or "").strip().upper()
    if not p:
        return {"kind": None}
    m = re.fullmatch(r"(FY|CY)(\d{4})", p)
    if m:
        return {"kind": m.group(1), "months": 12, "year": int(m.group(2)), "fiscal": m.group(1) == "FY"}
    m = re.fullmatch(r"(?:(\d{4})-)?([QH])([1-4])", p)
    if m:
        return {"kind": m.group(2), "months": MONTHS[m.group(2)], "year": int(m.group(1)) if m.group(1) else None, "n": int(m.group(3))}
    m = re.fullmatch(r"(\d{4})-(\d{2})", p)
    if m:
        return {"kind": "MONTH", "months": 1, "year": int(m.group(1)), "n": int(m.group(2))}
    if re.fullmatch(r"\d{4}", p):
        return {"kind": "YEAR", "months": 12, "year": int(p)}
    if p in ("LTM", "TTM"):
        return {"kind": "LTM", "months": 12}
    if p == "YTD":
        return {"kind": "YTD", "months": None}
    if p.startswith("RUN"):
        return {"kind": "RUNRATE", "months": 12, "annualised": True}
    if "→" in p:
        return {"kind": "CHANGE"}
    return {"kind": "OTHER"}


def compare(a: dict, b: dict) -> str | None:
    """`a`, `b`: fact values ({period, basis, …}). Returns why they are not like-for-like, or None."""
    pa, pb = period_info(a.get("period")), period_info(b.get("period"))
    ka, kb = pa.get("kind"), pb.get("kind")
    ba, bb = (a.get("basis") or "actual"), (b.get("basis") or "actual")
    if ka is None or kb is None or "CHANGE" in (ka, kb):
        return None
    if ba != bb and {ba, bb} & {"budget", "forecast", "target", "plan", "estimate"}:
        return f"{bb} compared with {ba}"
    if "RUNRATE" in (ka, kb) and ka != kb:
        return "an annualised run-rate compared with a reported period"
    if "YTD" in (ka, kb) and ka != kb:
        return "a year-to-date figure compared with a full or different period"
    ma, mb = pa.get("months"), pb.get("months")
    if ma and mb and ma != mb:
        return f"a {ma}-month period compared with a {mb}-month period"
    if {ka, kb} == {"FY", "CY"} or ({ka, kb} == {"FY", "YEAR"} and pa.get("year") == pb.get("year")):
        return "a fiscal year compared with a calendar year (check the fiscal year end)"
    return None
