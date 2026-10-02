"""Conflicting sources: the same quantity stated differently (v1.7 start of the v1.8 work).

Real projects disagree with themselves: a forecast and an actual for the same period, management
and audited figures, two files with different values for one KPI. The fact model never picks one
silently: `detect_conflicts` lists candidate conflicts into `fact_conflicts.json`; the agent records a
resolution for each (which value is used and why, or an explicit assumption). An unresolved conflict
touching a fact the deck uses is an error.
"""
from __future__ import annotations

import re

MEASURES = ("revenue", "sales", "ventas", "ingresos", "ebitda", "ebit", "margin", "margen", "cost", "costs", "coste", "costes", "profit", "beneficio",
            "volume", "volumen", "headcount", "plantilla", "customers", "clientes", "price", "precio", "cash", "caja", "capex", "freight", "transporte")


def _measures(text: str) -> set[str]:
    t = (text or "").lower()
    return {m for m in MEASURES if re.search(rf"\b{m}\b", t)}


STOP = set("de la el los las del al en por para con un una y o que se su sus es son the of to in for and a an on at by is are".split())


def _scope(text: str) -> str | None:
    """'group' / 'local' definition of a figure ("EBITDA del grupo" vs "EBITDA España")."""
    t = (text or "").lower()
    if re.search(r"\b(group|grupo|consolidated|consolidad[oa])\b", t):
        return "group"
    if re.search(r"\b(local|country|país|pais|segment|segmento|division|división|filial|subsidiary)\b", t):
        return "local"
    return None


def _bigrams(text: str) -> set[str]:
    """Content-word pairs of a sentence ('coste de cierre' → 'coste cierre')."""
    w = [x for x in re.findall(r"[a-záéíóúñü]+", (text or "").lower()) if x not in STOP and len(x) > 2]
    return {f"{a} {b}" for a, b in zip(w, w[1:])}


def _kind(unit: str) -> str:
    u = (unit or "").upper()
    return u.split("_")[0] if "_" in u else u


_row_sums: dict = {}
_labels: dict = {}


def _row_key(f: dict, v: dict) -> tuple:
    return (f["source"].get("file"), f["source"].get("loc"), v.get("label"), _kind(v.get("unit")), v.get("period"))


def _same(a: float, b: float, va: dict, vb: dict, tolerance: float) -> bool:
    """Equal up to sign ("lost 5.2" vs "-5,196") and to the precision the coarser figure is written with."""
    a, b = abs(a), abs(b)
    step = max(_step(va), _step(vb))
    return abs(a - b) <= max(tolerance * max(a, b, 1e-9), step / 2 + 1e-9)


def _step(v: dict) -> float:
    s = f"{float(v['value']):g}"
    dec = len(s.split(".")[1]) if "." in s and "e" not in s else 0
    sc = {"K": 1e3, "M": 1e6, "BN": 1e9}.get((v.get("unit") or "").upper().partition("_")[2], 1.0)
    return 10 ** -dec * sc


def _base(v: dict) -> float:
    sc = {"K": 1e3, "M": 1e6, "BN": 1e9}.get((v.get("unit") or "").upper().partition("_")[2], 1.0)
    return float(v["value"]) * sc


def detect_conflicts(facts: list[dict], tolerance: float = 0.01) -> list[dict]:
    out, seen = [], set()
    obs = []
    for f in facts:
        if f.get("fact_type") in ("derived_change", "computed", "assumption"):
            continue
        for v in f.get("values") or []:
            if not v.get("period") or not v.get("unit"):
                continue
            label = f"{v.get('label', '')} {v.get('column', '')} {f.get('claim', '')}" if f.get("fact_type") == "table_value" else f.get("claim", "")
            ms = _measures(label)
            if ms:
                obs.append((f, v, ms))
    _row_sums.clear()
    _labels.clear()
    for f in facts:
        if f.get("fact_type") == "table_value":
            for v in f.get("values") or []:
                _labels.setdefault((f["source"].get("file"), f["source"].get("loc")), set()).add(str(v.get("label") or ""))
                k = _row_key(f, v)
                _row_sums[k] = _row_sums.get(k, 0.0) + _base(v)
    for i, (fa, va, ma) in enumerate(obs):
        for fb, vb, mb in obs[i + 1:]:
            if fa["id"] == fb["id"] or va["period"] != vb["period"] or _kind(va["unit"]) != _kind(vb["unit"]) or not (ma & mb):
                continue
            if fa.get("fact_type") == fb.get("fact_type") == "table_value" and (
                    va.get("label") != vb.get("label") or (fa["source"].get("file"), fa["source"].get("loc")) == (fb["source"].get("file"), fb["source"].get("loc"))):
                continue  # two rows (Fresh vs Grocery) or two columns (fixed vs variable cost) of one table are not a conflict
            a, b = _base(va), _base(vb)
            if _same(a, b, va, vb, tolerance):
                continue
            row_sum = _row_sums.get(_row_key(fa if fa.get("fact_type") == "table_value" else fb, va if fa.get("fact_type") == "table_value" else vb))
            if fa.get("fact_type") != fb.get("fact_type") and row_sum is not None and _same(abs(a if fa.get("fact_type") != "table_value" else b), abs(row_sum), va, vb, tolerance):
                continue  # prose states the row total ("fixed plus variable cost"): part vs total, not a conflict
            pair = {fa.get("fact_type"): (fa, va), fb.get("fact_type"): (fb, vb)}
            if set(pair) == {"text_statement", "table_value"}:  # prose vs a table row: only the row the prose talks about
                (_, vt), (fx, _) = pair["table_value"], pair["text_statement"]
                lab = str(vt.get("label") or "")
                if not (re.search(r"\b(total|group|grupo|overall)\b", lab, re.I) or (lab and lab.lower() in fx["claim"].lower())):
                    continue
                ft = pair["table_value"][0]
                if lab.lower() not in fx["claim"].lower() and any(o and o.lower() != lab.lower() and re.search(rf"\b{re.escape(o.lower())}\b", fx["claim"].lower())
                                                                  for o in _labels.get((ft["source"].get("file"), ft["source"].get("loc")), ())):
                    continue  # the prose names another row ("Valencia cost …"), not the total
            key = tuple(sorted((fa["id"], fb["id"])))
            if key in seen:
                continue
            seen.add(key)
            bases = {(va.get("basis") or "actual"), (vb.get("basis") or "actual")}
            scope = {_scope(fa.get("claim", "") + " " + str(va.get("label") or "")), _scope(fb.get("claim", "") + " " + str(vb.get("label") or ""))}
            kind = ("management_vs_audited" if bases == {"management", "audited"} or bases == {"actual", "audited"} else
                    "forecast_vs_actual" if len(bases) > 1 else
                    "definition_mismatch" if scope == {"group", "local"} else "value_mismatch")
            out.append({"id": f"X{len(out) + 1:03d}", "type": kind, "measure": sorted(ma & mb), "period": va["period"],
                        "facts": [{"fact": fa["id"], "value": va["value"], "unit": va["unit"], "basis": va.get("basis"), "source": fa["source"].get("file")},
                                  {"fact": fb["id"], "value": vb["value"], "unit": vb["unit"], "basis": vb.get("basis"), "source": fb["source"].get("file")}],
                        "resolution": None})
    # v1.7.1 (DEBT F2): two sources stating the same quantity in prose, neither with a period
    # ("cierre: 1,5 M€" in one memo, "3,2 M€" in the finance note). Conservative: same unit kind,
    # a shared measure word AND a shared two-word phrase, different files, values >10% apart.
    texts = [(f, v) for f in facts if f.get("fact_type") == "text_statement" for v in f.get("values") or []
             if not v.get("period") and _kind(v.get("unit")) in ("EUR", "USD", "GBP")]  # money only: shares and rates legitimately differ
    for i, (fa, va) in enumerate(texts):
        for fb, vb in texts[i + 1:]:
            if fa["id"] == fb["id"] or fa["source"].get("file") == fb["source"].get("file") or _kind(va["unit"]) != _kind(vb["unit"]):
                continue
            ma, mb = _measures(fa.get("claim", "")), _measures(fb.get("claim", ""))
            shared = _bigrams(fa.get("claim", "")) & _bigrams(fb.get("claim", ""))
            if not (ma & mb) or not shared:
                continue
            a, b = abs(_base(va)), abs(_base(vb))
            if abs(a - b) <= 0.10 * max(a, b, 1e-9):
                continue
            key = tuple(sorted((fa["id"], fb["id"])))
            if key in seen:
                continue
            seen.add(key)
            out.append({"id": f"X{len(out) + 1:03d}", "type": "prose_mismatch", "measure": sorted(ma & mb), "period": None, "phrase": sorted(shared)[0],
                        "facts": [{"fact": fa["id"], "value": va["value"], "unit": va["unit"], "basis": va.get("basis"), "source": fa["source"].get("file")},
                                  {"fact": fb["id"], "value": vb["value"], "unit": vb["unit"], "basis": vb.get("basis"), "source": fb["source"].get("file")}],
                        "resolution": None})
    return out
