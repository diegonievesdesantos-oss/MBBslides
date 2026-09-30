"""Number formatting shared by native chart labels (Excel format codes) and
overlay labels (Python strings), so both always print the same thing.

Exhibit format spec (all optional):
    {"decimals": 1, "prefix": "€", "suffix": "M", "percent": false,
     "thousands": true, "plus": false}
`percent: true` means values are already in percent units (12.5 → "12.5%").
"""
from __future__ import annotations

import math


def fmt_spec(ex: dict) -> dict:
    f = dict(ex.get("format") or {})
    f.setdefault("decimals", _auto_decimals(ex))
    f.setdefault("prefix", "")
    f.setdefault("suffix", "")
    f.setdefault("percent", False)
    f.setdefault("thousands", True)
    f.setdefault("plus", False)
    return f


def _auto_decimals(ex: dict) -> int:
    vals = []
    data = ex.get("data") or {}
    for s in data.get("series") or []:
        vals += [v for v in s.get("values", []) if isinstance(v, (int, float))]
    for st in data.get("steps") or []:
        if isinstance(st.get("value"), (int, float)):
            vals.append(st["value"])
    if not vals:
        return 0
    m = max(abs(v) for v in vals)
    # Reduce precision: large numbers need no decimals; small ones one.
    if m >= 100:
        return 0
    if all(float(v).is_integer() for v in vals):
        return 0
    return 1


def fmt(v: float | None, f: dict, plus: bool | None = None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    d = int(f.get("decimals", 0))
    s = f"{abs(v):,.{d}f}" if f.get("thousands", True) else f"{abs(v):.{d}f}"
    sign = "−" if v < 0 else ("+" if (plus if plus is not None else f.get("plus")) and v > 0 else "")
    pct = "%" if f.get("percent") else ""
    return f"{sign}{f.get('prefix', '')}{s}{f.get('suffix', '')}{pct}"


def excel_code(f: dict, plus: bool | None = None) -> str:
    d = int(f.get("decimals", 0))
    core = ("#,##0" if f.get("thousands", True) else "0") + ("." + "0" * d if d else "")
    pre = f'"{f["prefix"]}"' if f.get("prefix") else ""
    suf = f'"{f["suffix"]}"' if f.get("suffix") else ""
    pct = '"%"' if f.get("percent") else ""
    pos = f"{pre}{core}{suf}{pct}"
    neg = f"-{pre}{core}{suf}{pct}"
    if plus if plus is not None else f.get("plus"):
        return f"+{pos};{neg};{pos}"
    return f"{pos};{neg}"


def nice_scale(lo: float, hi: float, ticks: int = 5, include_zero: bool = True) -> tuple[float, float, float]:
    """Round axis bounds (lo, hi, step) — 1/2/2.5/5 × 10^n steps."""
    if include_zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / max(1, ticks)
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if step >= raw:
            break
    nlo = math.floor(lo / step) * step
    nhi = math.ceil(hi / step) * step
    return nlo, nhi, step


def compact(v: float) -> str:
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "k")):
        if a >= div:
            return f"{v / div:.1f}".rstrip("0").rstrip(".") + suf
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}"


def cagr(first: float, last: float, periods: int) -> float:
    if first <= 0 or last <= 0 or periods <= 0:
        return float("nan")
    return (last / first) ** (1 / periods) - 1
