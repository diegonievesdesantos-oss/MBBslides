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
            "volume", "volumen", "headcount", "plantilla", "customers", "clientes", "price", "precio", "cash", "caja", "capex", "freight", "transporte",
            # v1.9 (DEBT_V18 U3): the measures of an investment case
            "inversión", "inversion", "investment", "ahorro", "ahorros", "savings", "productividad", "productivity", "payback", "tir", "irr",
            "mantenimiento", "maintenance", "error", "errores", "fte", "líneas", "lineas", "lines")


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


RATIO_RE = re.compile(r"\d\s*(?:x\b|veces\b|times\b)", re.I)


def _kind_of(f: dict, v: dict) -> str:
    """Unit kind of a value; a unit-less value is a ratio ("X") when its sentence or column writes it so."""
    k = _kind(v.get("unit"))
    if k:
        return "" if k in DURATIONS else k  # durations are timing (protocol 1.4), not observations to reconcile
    if f.get("fact_type") == "table_value":
        return "X" if re.search(r"(veces|times|ratio)", str(v.get("column", "")), re.I) else ""
    return "X" if _num_pos(f.get("claim", ""), v["value"], ratio=True) else ""


DURATIONS = {"DAYS", "WEEKS", "MONTHS", "YEARS", "HOURS", "MINUTES"}


def _num_pos(claim: str, value: float, ratio: bool = False):
    """Position (match) of the number carrying `value` in a sentence; with ratio=True, only if it is
    written as a ratio ("2,1x", "2,6 veces")."""
    for m in re.finditer(r"\d[\d.,]*", claim or ""):
        raw = m.group(0).rstrip(".,")
        for cand in (raw.replace(".", "").replace(",", "."), raw.replace(",", "")):
            try:
                x = float(cand)
            except ValueError:
                continue
            if abs(x - abs(float(value))) <= 1e-6 * max(1.0, abs(x)):
                if ratio and not re.match(r"\s*(?:x\b|veces\b|times\b)", claim[m.end():], re.I):
                    continue
                return m
    return None


def _content(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúñü]{4,}", (text or "").lower().replace("_", " ")) if w not in STOP}


OPPOSITES = [("manual", "automatizad"), ("manual", "automat"), ("real", "presupuest"), ("actual", "budget"), ("frío", "ambiente"),
             ("frio", "ambiente"), ("previsi", "real"), ("forecast", "actual"), ("garant", "real")]


def _opposed(a: set[str], b: set[str]) -> bool:
    """Words on one side naming the opposite of words on the other (manual vs automatizada, real vs presupuesto)."""
    def has(ws, stem):
        return any(w.startswith(stem) for w in ws)
    return any((has(a, x) and has(b, y) and not has(a, y) and not has(b, x)) or (has(a, y) and has(b, x) and not has(a, x) and not has(b, y))
               for x, y in OPPOSITES)


def _ambiguous(a: set[str], b: set[str]) -> bool:
    """One side names both poles of a pair ("error manual / automatizada", "2,1 veces la productividad
    manual") and the other only one: which pole the number belongs to cannot be told from the words."""
    def has(ws, stem):
        return any(w.startswith(stem) for w in ws)
    return any((has(a, x) and has(a, y)) != (has(b, x) and has(b, y)) and (has(a, x) or has(a, y)) and (has(b, x) or has(b, y))
               for x, y in OPPOSITES)


QUAL_RES = {"phase": re.compile(r"\b(?:fase|phase|stage)[\s_]*(\d)\b|\b(total)\b", re.I),
            "year": re.compile(r"\b(?:fy|ej\.?\s*)?((?:19|20)\d\d)\b", re.I),
            "zone": re.compile(r"\b(fr[ií]o|ambiente|cold|ambient)\b", re.I)}


def _qual_clash(ta: str, tb: str) -> bool:
    """Two labels naming different phases (fase 1 vs fase 2 vs total), different years, or a zone on
    one side only (zona frío vs the whole warehouse; "fase 2" vs an unphased row): not the same quantity."""
    for cat, rx in QUAL_RES.items():
        qa = {next(g for g in m.groups() if g).lower().replace("í", "i") for m in rx.finditer(ta)}
        qb = {next(g for g in m.groups() if g).lower().replace("í", "i") for m in rx.finditer(tb)}
        if qa != qb and (qa and qb or cat in ("zone", "phase")):
            return True
    return False


BASE_RE = re.compile(r"(?:\bs/|\bsobre|\bvs\.?|\bfrente a|\brespecto a(?:l)?|\bque en|\bthan|\bover|\bcompared (?:to|with))\s+(?:\w+\s+)?$", re.I)


def _period_is_base(claim: str, period: str) -> bool:
    """The period appears only as a comparison base ("+8% s/ real FY2026"): it is not the number's period."""
    hits = [m.start() for m in re.finditer(re.escape(period), claim, re.I)]
    return bool(hits) and all(BASE_RE.search(claim[max(0, h - 25):h]) for h in hits)


def _row_text(v: dict) -> str:
    return f"{v.get('label') or ''} {v.get('column') or ''}"


LIMIT_RE = re.compile(r"(≤|≥|<=|>=|\bm[aá]ximo\b|\bm[ií]nimo\b|\bat most\b|\bat least\b|\bno (?:debe|puede) superar\b|\bhasta un\b|\bobjetivo\b|\btarget\b)\s*\S{0,12}$", re.I)


def _local(claim: str, value: float) -> str | None:
    """The words around the number that carries `value` in its sentence; None when that number is a
    limit or a target (a criterion, not an observation) or cannot be found."""
    m = _num_pos(claim, value)
    if m is None or LIMIT_RE.search(claim[max(0, m.start() - 25):m.start()]):
        return None
    prev = [n.end() for n in re.finditer(r"\d[\d.,]*", claim[:m.start()])]
    start = max(0, m.start() - 70) if prev and prev[-1] > m.start() - 70 else max(0, m.start() - 160, prev[-1] if prev else 0)
    return claim[start:m.end() + 25]  # back to the previous number, or up to 160 characters when there is none


def _close(va: dict, vb: dict, kind: str) -> bool:
    a, b = abs(_base(va)), abs(_base(vb))
    tol = 0.05 if kind in ("X", "PCT") else 0.10
    return abs(a - b) <= tol * max(a, b, 1e-9) or _same(a, b, va, vb, 0.0)


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
            if not v.get("period") or not v.get("unit") or _period_is_base(f.get("claim", ""), str(v["period"])):
                continue
            if f.get("fact_type") == "table_value":
                label = f"{v.get('label', '')} {v.get('column', '')} {f.get('claim', '')}"
            else:  # v1.9: the words around THIS number, not the whole sentence ("0,5% menos" vs "5,4% sobre ventas")
                label = _local(f.get("claim", ""), v["value"]) or ""
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
            if fa.get("fact_type") == fb.get("fact_type") == "text_statement" and fa["source"].get("file") == fb["source"].get("file"):
                continue  # v1.9: two numbers of one document are its own statements, not two sources disagreeing
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
    # v1.9 (DEBT_V18 U3): prose against a period-less table (an analysis output, a model). Each number
    # of a sentence is read with the words around it (not the whole sentence), compared with the ONE
    # table row that best matches those words (same measure, ≥ 2 shared words), in another file, same
    # unit kind. Limits ("≤ 5 años", "mínimo del 12%") are criteria, not observations, and are skipped.
    tables = [(f, v) for f in facts if f.get("fact_type") == "table_value" for v in f.get("values") or [] if not v.get("period")]
    prose = [(f, v) for f in facts if f.get("fact_type") == "text_statement" for v in f.get("values") or [] if not v.get("period")]
    rows = [(fb, vb, _content(_row_text(vb)), _measures(_row_text(vb)), _kind_of(fb, vb)) for fb, vb in tables]
    for fa, va in prose:
        ctx = _local(fa.get("claim", ""), va["value"])
        if ctx is None:
            continue
        ka, wa, ma = _kind_of(fa, va), _content(ctx), _measures(ctx)
        if not ka or not ma:
            continue
        best, score = [], 2
        for fb, vb, wb, mb, kb in rows:
            if (kb != ka or fa["source"].get("file") == fb["source"].get("file") or not (ma & mb) or _opposed(wa, wb)
                    or _ambiguous(_content(fa.get("claim", "")), wb) or _qual_clash(ctx, _row_text(vb))):
                continue
            sc = len(wa & wb)
            if sc > score:
                best, score = [(fb, vb)], sc
            elif sc == score and best:
                best.append((fb, vb))
        if not best or any(_close(va, vb, ka) for _, vb in best):
            continue  # the best-matching row confirms the sentence
        fb, vb = best[0]
        key = tuple(sorted((fa["id"], fb["id"])))
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": f"X{len(out) + 1:03d}", "type": "prose_vs_table", "measure": sorted(ma & _measures(_row_text(vb))), "period": None,
                    "facts": [{"fact": fa["id"], "value": va["value"], "unit": va["unit"], "basis": va.get("basis"), "source": fa["source"].get("file")},
                              {"fact": fb["id"], "value": vb["value"], "unit": vb["unit"], "basis": vb.get("basis"), "source": fb["source"].get("file")}],
                    "resolution": None})
    # v1.9 (DEBT_V18 U3): two period-less tables in different files stating the same row (a model and
    # the deck built on it: "Ahorro neto anual · fase 2" 643 vs 763). Same rules: measure, ≥ 3 shared
    # words between label + column, no opposite qualifiers, the best-matching row only.
    for i, (fa, va, wa, ma, ka) in enumerate(rows):
        if not ma or not ka and not wa:
            continue
        best, score = [], 2
        for fb, vb, wb, mb, kb in rows:
            if (fb["source"].get("file") == fa["source"].get("file") or (kb or "") != (ka or "") or not (ma & mb) or _opposed(wa, wb)
                    or _ambiguous(wa, wb) or _qual_clash(_row_text(va), _row_text(vb))):
                continue
            sc = len(wa & wb)
            if sc > score:
                best, score = [(fb, vb)], sc
            elif sc == score and best:
                best.append((fb, vb))
        if not best or any(_close(va, vb, ka) for _, vb in best):
            continue
        fb, vb = best[0]
        key = tuple(sorted((fa["id"], fb["id"])))
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": f"X{len(out) + 1:03d}", "type": "table_mismatch", "measure": sorted(ma & _measures(_row_text(vb))), "period": None,
                    "facts": [{"fact": fa["id"], "value": va["value"], "unit": va["unit"], "basis": va.get("basis"), "source": fa["source"].get("file")},
                              {"fact": fb["id"], "value": vb["value"], "unit": vb["unit"], "basis": vb.get("basis"), "source": fb["source"].get("file")}],
                    "resolution": None})
    # v1.7.1 (DEBT F2): two sources stating the same quantity in prose, neither with a period
    # ("cierre: 1,5 M€" in one memo, "3,2 M€" in the finance note). Conservative: same unit kind,
    # a shared measure word AND a shared two-word phrase, different files, values >10% apart.
    # money, and (v1.9) ratios written as "2,1x" / "2,6 veces"; plain shares and rates legitimately differ
    texts = [(f, v) for f in facts if f.get("fact_type") == "text_statement" for v in f.get("values") or []
             if not v.get("period") and _kind_of(f, v) in ("EUR", "USD", "GBP", "X")]
    for i, (fa, va) in enumerate(texts):
        for fb, vb in texts[i + 1:]:
            if fa["id"] == fb["id"] or fa["source"].get("file") == fb["source"].get("file") or _kind_of(fa, va) != _kind_of(fb, vb):
                continue
            ca, cb = _local(fa.get("claim", ""), va["value"]), _local(fb.get("claim", ""), vb["value"])
            if ca is None or cb is None:
                continue
            ma, mb = _measures(ca), _measures(cb)
            shared = _bigrams(ca) & _bigrams(cb)
            if not (ma & mb) or not shared:
                continue
            if _close(va, vb, _kind_of(fa, va)):
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
