"""Headline proof with arithmetic lineage (v1.5).

A headline figure is PROVEN when the reader can find it on the slide. Up to v1.4 that meant the
same number (or the same number at another scale) printed in the body. Consulting headlines are
often DERIVED: "€61M opportunity" over three bars of 24, 19 and 18; "costs fell 18%" over a
series from 100 to 82. This module proves such figures deterministically — no model, no guessing:

    headline quantity  → normalised (kind, value)        "€61M" → (money, 61 000 000)
    slide series       → normalised series per exhibit   chart series, waterfall steps, numeric
                                                          table columns, KPI values, funnel stages
    bounded derivations on ONE series at a time:
        sum                 all values; the k largest (k = 2, 3); waterfall deltas
        difference          last − first (time order as given); waterfall end total − start total
        ratio               last ÷ first                                   (headline "×" / "x")
        percent change      (last ÷ first − 1) × 100                       (headline "%")
        percentage points   last − first of a % series                     (headline "pp")
        part / total        a value or the k largest ÷ the series total    (headline "%")

Units are normalised first (€/$/£, k/M/bn, %, pp, bps, ×) and never combined across kinds or
currencies. Tolerance is the precision the headline was written with (half of its last digit)
plus 0.5%. Conservative by design — UNKNOWN beats a false proof:
  * no combination search (no arbitrary subsets), one series per derivation;
  * plain integers below 10 and plain numbers without a matching series kind are never derived
    (coincidences are too likely);
  * if derivations of DIFFERENT kinds match one figure, the figure is reported as ambiguous and
    not proven.
Every decision is returned as machine-readable provenance (status, operation, operands, result).
"""
from __future__ import annotations

import re

from ..core.headline import DURATION_RE, NUM_RE

CURRENCIES = {"€": "EUR", "$": "USD", "£": "GBP", "eur": "EUR", "usd": "USD", "gbp": "GBP"}
SCALES = {"k": 1e3, "m": 1e6, "mn": 1e6, "mm": 1e6, "bn": 1e9, "b": 1e9, "thousand": 1e3, "million": 1e6, "billion": 1e9,
          "mil": 1e3, "millones": 1e6, "m€": 1e6, "k€": 1e3}
REL_TOL = 0.005


def _num(raw: str) -> float | None:
    s = raw.replace("−", "-").replace("–", "-").strip()
    s = s.replace(",", ".") if re.search(r"\d,\d{1,2}(?!\d)", s) else s.replace(",", "")
    s = re.sub(r"[^\d.\-+]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _decimals(raw: str) -> int:
    m = re.search(r"[.,](\d{1,2})(?!\d)", raw)
    return len(m.group(1)) if m else 0


def unit_of(text: str) -> dict:
    """Unit description of an exhibit / column label: {"kind", "currency", "scale"}."""
    t = (text or "").lower()
    cur = next((v for k, v in CURRENCIES.items() if k in t), None)
    if re.search(r"(^|[^a-z])pp([^a-z]|$)|percentage points|puntos", t):
        return {"kind": "pp", "currency": None, "scale": 1.0}
    if "%" in t or "percent" in t:
        return {"kind": "pct", "currency": None, "scale": 1.0}
    scale = 1.0
    for k, v in sorted(SCALES.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"(^|[^a-z]){re.escape(k)}([^a-z]|$)", t.replace("€", " ").replace("$", " ").replace("£", " ")):
            scale = v
            break
    return {"kind": "money" if cur else "plain", "currency": cur, "scale": scale}


def headline_quantities(text: str) -> list[dict]:
    """Numbers of a headline with their unit, skipping years, identifiers and durations
    (same filters as core.headline.numbers_in)."""
    out = []
    text = text or ""
    for m in NUM_RE.finditer(text):
        raw = m.group(0).strip()
        rest = text[m.end():]
        if DURATION_RE.match(rest):
            continue
        before = text[: m.start()]
        prev = before.rstrip().split(" ")[-1].lower() if before.strip() else ""
        if prev in ("wave", "waves", "phase", "step", "stage", "q", "h", "fy", "tier", "level", "option", "scenario", "ola", "fase", "hub", "top"):
            continue
        v = _num(re.sub(r"[a-zA-Z%]+$", "", raw))
        if v is None:
            continue
        suffix = re.sub(r"[-−+\d.,\s]", "", raw).lower()
        word = re.match(r"\s*(bps|pts|points|puntos|pp)\b", rest, re.IGNORECASE)
        cur = next((CURRENCIES[c] for c in ("€", "$", "£") if before.endswith(c) or before.endswith(c + " ") or rest.lstrip().startswith(c)), None)
        if suffix == "" and 1900 <= v <= 2100 and float(v).is_integer():
            continue
        if suffix == "pp" or (word and word.group(1).lower() in ("pp", "pts", "points", "puntos")):
            kind, scale = "pp", 1.0
        elif word and word.group(1).lower() == "bps":
            kind, scale = "pp", 0.01
        elif suffix == "%":
            kind, scale = "pct", 1.0
        elif suffix == "x":
            kind, scale = "x", 1.0
        else:
            scale = SCALES.get(suffix, 1.0)
            kind = "money" if cur else "plain"
        out.append({"raw": raw if not cur else f"{'€' if cur == 'EUR' else '$' if cur == 'USD' else '£'}{raw}", "value": abs(v) * scale, "kind": kind,
                    "currency": cur, "decimals": _decimals(raw), "scale": scale})
    return out


def _values(seq) -> list[float]:
    out = []
    for x in seq or []:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            out.append(float(x))
        elif isinstance(x, str):
            v = _num(x)
            if v is not None and re.search(r"\d", x):
                out.append(v)
    return out


def slide_series(slide: dict) -> list[dict]:
    """Normalised numeric series of a slide's exhibits: [{"name", "kind", "currency", "values",
    "waterfall"?: {...}}]. Values are in base units (money scaled to units of currency)."""
    out = []
    exs = [slide.get("visual")] + list(slide.get("exhibits") or [])
    for ex in exs:
        if not isinstance(ex, dict):
            continue
        d = ex.get("data") if isinstance(ex.get("data"), dict) else ex
        u = unit_of(ex.get("unit", ""))
        t = ex.get("type")
        if t in ("waterfall", "bridge") and d.get("steps"):
            deltas, totals, run = [], [], 0.0
            for st in d["steps"]:
                if st.get("type") in ("total", "subtotal"):
                    if st.get("value") is not None and st.get("type") == "total" and not totals and not deltas:
                        run = float(st["value"])
                    totals.append(run)
                else:
                    v = float(st.get("value") or 0)
                    deltas.append(v)
                    run += v
            out.append({"name": "waterfall", **u, "values": deltas, "waterfall": {"start": totals[0] if totals else 0.0, "end": totals[-1] if totals else run,
                                                                                   "deltas": deltas}})
            continue
        for s in d.get("series") or []:
            vals = _values(s.get("values"))
            if len(vals) >= 2:
                out.append({"name": s.get("name", "series"), **u, "values": vals})
        if d.get("stages"):
            vals = _values([st.get("value") for st in d["stages"] if isinstance(st, dict)])
            if len(vals) >= 2:
                out.append({"name": "stages", **u, "values": vals})
        if ex.get("rows") and ex.get("columns"):
            for j, c in enumerate(ex["columns"]):
                if isinstance(c, dict) and c.get("kind") == "number":
                    vals = _values([r[j] for r in ex["rows"] if isinstance(r, list) and j < len(r)])
                    if len(vals) >= 2:
                        out.append({"name": c.get("label", f"col{j}"), **unit_of(c.get("label", "")), "values": vals})
    return out


def _fmt(v: float, s: dict) -> str:
    sc = s.get("scale", 1.0) or 1.0
    return f"{v / sc:g}"


def _candidates(s: dict) -> list[tuple[str, float, list[float], str]]:
    """(operation, result, operands, result kind) for one series. Results are in base units."""
    v = s["values"]
    sc = s.get("scale", 1.0) or 1.0
    base = [x * sc for x in v]
    kind = s["kind"]
    out = []
    if s.get("waterfall"):
        w = s["waterfall"]
        start, end = w["start"] * sc, w["end"] * sc
        pos = [x * sc for x in w["deltas"] if x > 0]
        neg = [x * sc for x in w["deltas"] if x < 0]
        if pos:
            out.append(("sum of increases", sum(pos), pos, kind))
        if neg:
            out.append(("sum of decreases", abs(sum(neg)), neg, kind))
        if w["deltas"]:
            out.append(("sum of steps", abs(sum(x * sc for x in w["deltas"])), [x * sc for x in w["deltas"]], kind))
        if start:
            out.append(("difference end − start", abs(end - start), [end, start], kind))
            out.append(("percent change", abs(end / start - 1) * 100, [end, start], "pct"))
            if kind == "pct":
                out.append(("percentage-point change", abs(end - start), [end, start], "pp"))
        return out
    if len(base) >= 2:
        out.append(("sum", abs(sum(base)), base, kind))
        top = sorted(base, reverse=True)
        for k in (2, 3):
            if len(top) > k:
                out.append((f"sum of the {k} largest", sum(top[:k]), top[:k], kind))
        first, last = base[0], base[-1]
        out.append(("difference last − first", abs(last - first), [last, first], kind))
        if first:
            out.append(("percent change last vs first", abs(last / first - 1) * 100, [last, first], "pct"))
            out.append(("ratio last ÷ first", abs(last / first), [last, first], "x"))
        if kind == "pct":
            out.append(("percentage-point change", abs(last - first), [last, first], "pp"))
        tot = sum(base)
        if tot and kind != "pct" and all(x >= 0 for x in base):
            for x in base:
                out.append(("part ÷ total", x / tot * 100, [x, tot], "pct"))
            for k in (2, 3):
                if len(top) > k:
                    out.append((f"{k} largest ÷ total", sum(top[:k]) / tot * 100, [*top[:k], tot], "pct"))
    return out


# derivations that are the same arithmetic fact (a waterfall's net change is both the sum of its
# steps and end − start) count as one family; different families matching one figure = ambiguous
FAMILY = {"sum of steps": "net change", "difference end − start": "net change", "sum of increases": "sum", "sum of decreases": "sum",
          "sum": "sum", "sum of the 2 largest": "sum", "sum of the 3 largest": "sum", "difference last − first": "difference",
          "percent change": "percent change", "percent change last vs first": "percent change", "ratio last ÷ first": "ratio",
          "percentage-point change": "pp change", "part ÷ total": "share", "2 largest ÷ total": "share", "3 largest ÷ total": "share"}


def _compatible(q: dict, s: dict, rkind: str) -> bool:
    if q["kind"] == "money":
        return rkind == "money" and (s.get("currency") in (None, q["currency"]))
    if q["kind"] == "plain":
        return rkind in ("plain", "money") and s["kind"] != "pct"
    return rkind == q["kind"]


def derive(q: dict, series: list[dict]) -> dict:
    """Try to prove one headline quantity from the slide's series. Returns provenance."""
    rec = {"headline_value": q["raw"], "status": "unknown"}
    if q["kind"] == "plain" and (q["value"] < 10 or float(q["value"]).is_integer() and q["value"] < 10):
        rec["reason"] = "small plain number: too likely to match by coincidence"
        return rec
    if q["kind"] == "plain" and not any(s["kind"] == "plain" for s in series):
        rec["reason"] = "no series of a compatible kind"
        return rec
    half = 0.5 * 10 ** (-q["decimals"]) * (q["scale"] or 1.0)
    tol = half + REL_TOL * q["value"]
    hits = []
    for s in series:
        for op, res, operands, rkind in _candidates(s):
            if not _compatible(q, s, rkind):
                continue
            if abs(res - q["value"]) <= tol:
                hits.append((op, res, operands, s))
    if not hits:
        rec["reason"] = "no bounded derivation matches within tolerance"
        return rec
    families = {FAMILY.get(h[0], h[0]) for h in hits}
    if len(families) > 1:
        rec.update(status="unknown", reason=f"ambiguous: {len(families)} different kinds of derivation match", candidates=sorted({h[0] for h in hits}))
        return rec
    op, res, operands, s = hits[0]
    rec.update(status="derived_proof", operation=op, series=s.get("name"), operands=[_fmt(x, s) for x in operands],
               normalized_result=round(res, 6), tolerance=round(tol, 6))
    return rec
