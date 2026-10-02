"""Conflicting sources: the same quantity stated differently (v1.7 start of the v1.8 work).

Real projects disagree with themselves: a forecast and an actual for the same period, management
and audited figures, two files with different values for one KPI. The fact model never picks one
silently: `detect_conflicts` lists candidate conflicts into `fact_conflicts.json`; the agent records a
resolution for each (which value is used and why, or an explicit assumption). An unresolved conflict
touching a fact the deck uses is an error.
"""
from __future__ import annotations

import re
from pathlib import Path

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
    rows = [(fb, vb, _content(_row_text(vb)), _measures(_row_text(vb)), _kind_of(fb, vb)) for fb, vb in tables
            if not re.search(r"[≤≥<>]", _row_text(vb))]  # a requirement row ("≥ 130") is a criterion, not an observation
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
    _versions(facts, out, seen)
    return rank(out)


# v2.1: the review order. A reader has time for the first few conflicts: money and large gaps first.
TYPE_WEIGHT = {"plan_vs_actual": 3, "definition_mismatch": 3, "management_vs_audited": 3, "forecast_vs_actual": 3,
               "value_mismatch": 2, "prose_mismatch": 2, "prose_vs_table": 2, "table_mismatch": 1}


def _gap(c: dict) -> float:
    vals = [abs(_base(x)) for x in c["facts"] if x.get("value") is not None]
    vals = [v for v in vals if v]
    return (max(vals) / min(vals) - 1) if len(vals) >= 2 else 0.0


def priority(c: dict, used: set | None = None) -> tuple[str, float]:
    """(high | medium | low, score), from what separated real conflicts from noise on the development
    cases (not from magnitude, which did not):
    - high: the deck uses one of the figures, or three to five sources give the same quantity three
      to five ways (a real tangle of versions);
    - low: one side is the analyst's own analysis output (it is the correction, by design) or a long
      chain across many files;
    - medium: the rest, pairs between two sources.

    v2.2 (item 4), also low:
    - one side is a presentation (.pptx): an earlier deck restates figures, it is what gets updated,
      not a source that disagrees;
    - the values differ by 40% or more: on the development cases every such "version" was another
      quantity with the same words (a quarter against the year, a share against a level)."""
    srcs = [str(x.get("source") or "") for x in c["facts"]]
    analysis = any(s.startswith("analysis/") or "/analysis/" in s for s in srcs)
    deck = any(s.lower().endswith((".pptx", ".ppt", ".key")) for s in srcs)
    apart = _gap(c) >= 0.4
    n = len(c["facts"])
    files = len(set(srcs))
    touched = bool(used and used & {x["fact"] for x in c["facts"]})
    score = TYPE_WEIGHT.get(c.get("type"), 1) + min(3.0, 10 * _gap(c)) + (4 if 3 <= n <= 5 and files >= 2 else 0) - (4 if analysis else 0) \
        - (3 if n > 5 else 0) + (6 if touched else 0)
    score -= (4 if deck else 0) + (3 if apart else 0)
    if touched or (3 <= n <= 5 and files >= 2 and not analysis and not deck and not apart):
        level = "high"
    elif analysis or n > 5 or deck or apart:
        level = "low"
    else:
        level = "medium"
    return level, round(score, 2)


def rank(conflicts: list[dict], used: set | None = None) -> list[dict]:
    for c in conflicts:
        c["priority"], c["priority_score"] = priority(c, used)
    order = {"high": 0, "medium": 1, "low": 2}
    out = sorted(conflicts, key=lambda c: (order[c["priority"]], -c["priority_score"]))
    for i, c in enumerate(out, 1):
        c["id"] = f"X{i:03d}"
    return out


def merge_reviews(old: list[dict], new: list[dict]) -> list[dict]:
    """New detections keep the reviewer's resolution or dismissal of the same conflict (two shared
    facts are enough: a group may have gained a version). Reviewed conflicts no longer detected are
    kept, marked `stale`, so no decision is lost."""
    reviewed = [c for c in old if c.get("resolution") or c.get("dismissed")]
    used = set()
    for c in new:
        ids = {x["fact"] for x in c["facts"]}
        for i, r in enumerate(reviewed):
            if len(ids & {x.get("fact") if isinstance(x, dict) else x for x in r.get("facts") or []}) >= 2:
                for k in ("resolution", "dismissed", "reviewer_note"):
                    if r.get(k):
                        c[k] = r[k]
                used.add(i)
                break
    for i, r in enumerate(reviewed):
        if i not in used:
            new.append({**r, "stale": "no longer detected with the current sources"})
    return new


# v2.0 (item 4): versions of one quantity across sources — the same project cost, savings or rate given
# with different values because each source counts something different (scope), on another basis
# (plan vs actual), at another cut-off, or by another method. Families group synonyms of a measure.
FAMILIES = {"cost": ("inversi", "investment", "capex", "coste", "costes", "cost", "contab", "importe", "spend", "gasto"),
            "saving": ("ahorro", "ahorros", "saving", "savings", "beneficio", "benefit"),
            "revenue": ("ventas", "ingreso", "facturaci", "revenue", "sales", "turnover"),
            "margin": ("margen", "margin", "ebitda", "ebit"),
            "rate": ("tasa", "rate", "ratio", "porcentaje", "share", "cuota"),
            "error": ("error", "errores", "defect", "incidenc"),
            "productivity": ("productividad", "productivity", "veces", "times", "rendimiento", "output"),
            "headcount": ("plantilla", "fte", "empleados", "headcount", "personas", "staff"),
            "volume": ("volumen", "volume", "líneas", "lineas", "unidades", "units", "pedidos", "orders", "pacientes", "patients", "clientes", "customers"),
            "payback": ("payback", "retorno", "recupera"),
            "price": ("precio", "price", "tarifa", "fee")}
SCOPE_RE = re.compile(r"\b(incluy\w*|inclu\w*|exclu\w*|sin|without|con|with|complet\w*|total|neto|neta|net|bruto|gross|contabiliz\w*|pendiente\w*|pending|"
                      r"a \d{1,2}/\d{1,2}|as of|cierre|cut-?off|recoge|only|solo)\b", re.I)
PLANNY = re.compile(r"\b(business case|presupuest\w*|budget\w*|previst\w*|previsi\w*|forecast\w*|objetivo|target|garant\w*|guarante\w*|ofert\w*|"
                    r"plan(?:ned)?|estimad\w*|estimat\w*|aprobad\w*|approved)\b", re.I)


GROWTH_RE = re.compile(r"\b(crec\w*|creci\w*|variaci\w*|aument\w*|growth|grow\w*|increase\w*|decrease\w*|declin\w*|desviaci\w*|deviation|"
                       r"reduc\w*|libera\w*|ahorrad\w*|menos|fewer|cut|recorte\w*|subid\w*|ca[ií]d\w*)\b|"
                       r"\d\s*%\s*(?:más|menos|more|less|above|below|por encima|por debajo)\b", re.I)
CRITERION_RE = re.compile(r"\b(necesari\w*|required|requerid\w*|umbral|threshold|break-?even|mínim\w*|minimum|máxim\w*|maximum|límite|limit|"
                          r"criterio|criterion|hurdle|garantía contractual|contractual guarantee)\b", re.I)
SLICE_RE = re.compile(r"\b(?:19|20)\d\d-(?:0[1-9]|1[0-2])\b|\b(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|jan|apr|aug|dec)[a-z]*[-\s]\d{2,4}\b|"
                      r"\bsemana\s*\d+|\bweek\s*\d+|\bS\d{1,2}\b|\bQ[1-4]\b|\btrimestre\b|\bquarter\b", re.I)
PER_RE = re.compile(r"\b(?:por|per|/)\s*(fte|empleado|persona|hora|hour|línea|linea|line|unidad|unit|cliente|customer|paciente|patient|pedido|order|tienda|store|m2|día|dia|day|mes|month)\b|"
                    r"\b(medio|media|average|avg|unitari\w*)\b", re.I)


DATE_SLICE_RE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)?\d{2}\b|\b(?:19|20)\d\d-\d{2}-\d{2}\b")  # a ledger line, a daily row
SOURCE_RE = re.compile(r"\b(según|segun|according to|per the|calculad\w*|calculated|medid\w*|measured|reportad\w*|reported|informe|report|mayor|ledger|redondead\w*|rounded)\b", re.I)
GENERIC = {"ascie", "total", "segun", "según", "hasta", "sobre", "entre", "desde", "valor", "value", "impor", "datos", "fuent", "tras", "frent"}


VQUAL = {"phase": re.compile(r"\b(?:fase|phase|stage)[\s_]*(\d)\b", re.I),
         "year": QUAL_RES["year"], "zone": QUAL_RES["zone"]}  # versions: "inversión total" is the whole project, not a total column


def _own_delta(text: str, value: float) -> bool:
    """Is THIS number a change ("crece un 6%", "12 FTE menos", "un 10% por encima")? Words of another
    number of the sentence do not count."""
    m = _num_pos(text, value)
    if m is None:
        return bool(GROWTH_RE.search(text))
    before, after = text[max(0, m.start() - 40):m.start()], text[m.end():m.end() + 25]
    return bool(re.search(r"\b(crec\w*|creci\w*|variaci\w*|aument\w*|reduc\w*|libera\w*|growth|increase\w*|decrease\w*|declin\w*|desviaci\w*|cut)\b[^.;\d]*$", before, re.I)
                or re.match(r"\s*(%|pp|p\.p\.)?\s*(más|menos|more|less|above|below|por encima|por debajo|fewer)\b", after, re.I)
                or re.search(r"[+−-]\s*$", before))


REF_RE = re.compile(r"\b(up from|down from|from|desde|frente a(?: los| las| el| la)?|compared (?:with|to)|vs\.?|versus|respecto a(?:l)?|que en|than|antes|previously|was)\s*[£$€]?\s*$", re.I)


def _is_reference(claim: str, value: float) -> bool:
    m = _num_pos(claim, value)
    return bool(m and REF_RE.search(claim[max(0, m.start() - 22):m.start()]))


def _qset(rx, t: str) -> set:
    return {next(g for g in m.groups() if g).lower().replace("í", "i") for m in rx.finditer(t)}


def _shared_quals(ta: str, tb: str) -> int:
    """How many of phase / year / zone both name, and the same."""
    return sum(1 for cat, rx in VQUAL.items() if cat != "year" and _qset(rx, ta) & _qset(rx, tb))  # a shared year says little


def _both_clash(ta: str, tb: str) -> bool:
    for cat, rx in VQUAL.items():
        qa = {next(g for g in m.groups() if g).lower().replace("í", "i") for m in rx.finditer(ta)}
        qb = {next(g for g in m.groups() if g).lower().replace("í", "i") for m in rx.finditer(tb)}
        if qa and qb and not (qa & qb):
            return True
    return False


SPAN_RE = re.compile(r"\b(anual\w*|al año|per year|a year|annual\w*|yearly)\b|\b(en (?:\w+ )?(?:\d+|dos|tres|cuatro|cinco) años|in (?:\d+|two|three|four|five) years|acumulad\w*|cumulative)\b", re.I)


def _per(text: str) -> str:
    m = PER_RE.search(text or "")
    unit = (m.group(1) or "avg").lower()[:4] if m else ""
    sp = SPAN_RE.search(text or "")
    return unit + ("|cum" if sp and sp.group(2) else "")


def _slice_key(text: str) -> str:
    m = SLICE_RE.search(text or "") or DATE_SLICE_RE.search(text or "")
    return m.group(0).lower() if m else ""


HEAD_STOP = STOP | {"total", "valor", "value", "importe", "amount", "cifra", "figure", "dato", "data", "nuevo", "nueva", "new", "nivel", "level",
                    "anual", "annual", "año", "year", "mes", "month", "trimestre", "quarter", "fecha", "date", "según", "segun", "hasta", "sobre", "unos",
                    "unas", "cerca", "around", "about", "approximately", "aproximadamente", "este", "esta", "this", "that", "ese", "esa", "came", "fue", "es",
                    "son", "was", "were", "has", "have", "ha", "han", "of", "de", "del", "at", "in", "en", "is", "are", "be", "un", "una", "al",
                    # qualifiers and connectives are not measures
                    "fase", "phase", "stage", "zona", "zone", "frío", "frio", "ambiente", "real", "actual", "plan", "for", "the", "and", "with", "con",
                    "por", "para", "los", "las", "que", "como", "más", "mas", "menos", "end", "from", "ahead", "after", "before", "tras", "antes",
                    "resultado", "result", "hipotesis", "hipótesis", "calculo", "cálculo", "concepto", "comentario", "comment", "note", "nota"}


def _heads(text: str, value) -> set[str]:
    """The measure named right before the number ("ARR of £28.6m", "new bookings came in at £3.7m"), or
    the head of a row label: works for metrics no fixed list names."""
    if value is not None:
        m = _num_pos(text, value)
        if m is None:
            return set()
        pre = text[max(0, m.start() - 60):m.start()]
        post = re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑ]{3,}", text[m.end():m.end() + 14])[:1]  # "£3.7m ACV", "212 personas"
        lead = re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑ]{3,}", text)[:3]  # the subject of the clause
    else:
        pre, post, lead = text[:60], [], []
    toks = re.findall(r"[A-Za-záéíóúñüÁÉÍÓÚÑ]{3,}", pre)
    toks = (toks[-4:] + post + lead) if value is not None else toks[:3]
    out = set()
    for t in toks:
        lt = t.lower()
        if lt in HEAD_STOP:
            continue
        out.add("h:" + (t if t.isupper() and len(t) <= 5 else lt[:6]))
    return out


def _families(text: str) -> set[str]:
    t = (text or "").lower()
    words = re.findall(r"[a-záéíóúñü]+", t)
    return {fam for fam, stems in FAMILIES.items() if any(w.startswith(st) for w in words for st in stems)}


def _stems5(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-záéíóúñü]{4,}", (text or "").lower().replace("_", " ")) if w not in STOP}


SUBJ_RE = re.compile(r"\b(?:fase|phase|stage)[\s_]*\d\b|\b(?:fr[ií]o|ambiente|cold|ambient)\b", re.I)


def _version_items(facts: list[dict]) -> list[dict]:
    paras: dict = {}  # the sentences of one paragraph: "La fase 1 … arrancó. La inversión total asciende a 3,52 M€"
    for f in facts:
        if f.get("fact_type") == "text_statement":
            paras.setdefault((f["source"].get("file"), f["source"].get("loc")), []).append(f.get("claim", ""))
    sizes: dict = {}
    rowsum: dict = {}
    for f in facts:
        if f.get("fact_type") == "table_value":
            sizes[f["source"].get("file")] = sizes.get(f["source"].get("file"), 0) + 1
            for v in f.get("values") or []:
                k = (f["source"].get("file"), f["source"].get("loc"), v.get("label"), _kind(v.get("unit")))
                rowsum[k] = rowsum.get(k, 0.0) + _base(v)
    items = []
    for f in facts:
        if f.get("fact_type") in ("derived_change", "assumption"):
            continue
        file = str(f["source"].get("file") or "")
        for v in f.get("values") or []:
            kind = _kind_of(f, v)
            if not kind and re.search(r"\b(personas|empleados|fte|ftes|people|employees|staff|headcount|plantilla|camas|beds|tiendas|stores|clientes|customers|pacientes|patients|usuarios|users)\b",
                                      f"{f.get('claim', '')} {v.get('label') or ''} {v.get('column') or ''}", re.I):
                kind = "COUNT"  # a head count or a count of units: unit-less, still a quantity with versions
            if not kind or kind in DURATIONS:
                continue
            if f.get("fact_type") == "table_value":
                text = f"{v.get('label') or ''} — {v.get('column') or ''}"
                fam = _families(str(v.get("column") or "")) or _families(text)
                fam |= _heads(str(v.get("label") or ""), None) | _heads(str(v.get("column") or ""), None)
            else:
                text = _local(f.get("claim", ""), v["value"])
                if text is None:
                    continue  # a limit or target is a criterion, not a version
                fam = _families(text) | _heads(text, v["value"])
            if not fam:
                continue
            if CRITERION_RE.search(text):
                continue  # a threshold is a criterion, not a version
            if f.get("fact_type") != "table_value" and _is_reference(f.get("claim", ""), v["value"]):
                continue  # "up from £27.4m", "frente a los 3,2 M€ aprobados": another period or the base, cited for comparison
            subj = text
            if f.get("fact_type") == "text_statement" and not SUBJ_RE.search(text):  # the paragraph or its heading names the subject
                around = " ".join(paras.get((file, f["source"].get("loc")), [])) + " " + " ".join((f.get("where") or {}).values())
                subj = f"{text} " + " ".join(dict.fromkeys(m.group(0) for m in SUBJ_RE.finditer(around)))
            if not VQUAL["phase"].search(subj):  # "coste_fase1.csv", "detalle_fase2_real.csv": the file names the phase
                subj += " " + " ".join(m.group(0) for m in VQUAL["phase"].finditer(Path(file).stem.replace("_", " ").replace("fase", " fase ")))
            quals = {"text": f"{subj} {v.get('period') or ''}", "file": Path(file).stem}
            items.append({"f": f, "v": v, "file": file, "kind": kind, "fam": fam, "words": _stems5(text), "full": set(re.findall(r"[a-záéíóúñü]{4,}", text.lower())),
                          "quals": quals, "text": text, "plan": bool(PLANNY.search(text) or PLANNY.search(Path(file).stem.replace("_", " "))),
                          "base": abs(_base(v)), "per": _per(text), "delta": _own_delta(text, v["value"]) if f.get("fact_type") != "table_value" else bool(GROWTH_RE.search(text)),
                          "slice_key": _slice_key(text if f.get("fact_type") != "table_value" else f"{v.get('label') or ''}"),
                          "slice": f.get("fact_type") == "table_value" and bool(SLICE_RE.search(str(v.get("label") or "")) or DATE_SLICE_RE.search(str(v.get("label") or ""))),
                          "analysis": file.startswith("analysis/") or "/analysis/" in file,
                          "records": f.get("fact_type") == "table_value" and sizes.get(file, 0) >= 40,
                          "row_total": abs(rowsum.get((f["source"].get("file"), f["source"].get("loc"), v.get("label"), _kind(v.get("unit"))), 0.0))
                          if f.get("fact_type") == "table_value" else None})
    return items


def _versions(facts: list[dict], out: list[dict], seen: set) -> None:
    items = _version_items(facts)
    best: dict = {}
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a["file"] == b["file"] or a["kind"] != b["kind"] or not (a["fam"] & b["fam"]) or a["f"]["id"] == b["f"]["id"]:
                continue
            if a["analysis"] and b["analysis"]:
                continue  # two outputs of the analyst's own model: scenarios, not versions
            if a["slice"] != b["slice"] or a["per"] != b["per"] or a["delta"] != b["delta"]:
                continue  # a month against a year, a cost per FTE against a total, a change against a level
            if a["slice"] and a["slice_key"] != b["slice_key"]:
                continue  # two different months / days / weeks
            x, y = a["base"], b["base"]
            if not x or not y or max(x, y) / min(x, y) > 1.7:
                continue  # versions differ by scope or basis, not by multiples: a part of the total, another quantity
            if _same(abs(_base(a["v"])), abs(_base(b["v"])), a["v"], b["v"], 0.01):
                continue  # the same figure, to the precision each is written with
            ta, tb = a["quals"]["text"], b["quals"]["text"]
            if _both_clash(ta, tb):
                continue  # both name a phase / zone / year, and not the same one
            if _opposed(a["full"], b["full"]):
                continue
            fam_stems = {st[:5] for fam in (a["fam"] & b["fam"]) for st in FAMILIES.get(fam, (fam[2:],))}
            shared = {w for w in (a["words"] & b["words"]) - GENERIC if w[:5] not in fam_stems and not any(w.startswith(st[:4]) for st in fam_stems)}
            ratio = max(x, y) / min(x, y)
            # the measure family, the unit and the magnitude already match; words, subject and closeness rank the candidates
            if any(t["row_total"] and abs(t["row_total"] - t["base"]) > 1e-9 and abs(o["base"] - t["row_total"]) <= 0.015 * t["row_total"]
                   for t, o in ((a, b), (b, a))):
                continue  # the other figure is this row's total (fixed + variable cost): a part and its whole
            if a["records"] and b["records"]:
                continue  # two rows of two data exports: reconciling them is an analysis, not a conflict between statements
            sc = len(shared) + 2 * _shared_quals(ta, tb) + (1 if ratio <= 1.3 else 0) + (1 if a["kind"] in ("EUR", "USD", "GBP") and min(x, y) >= 1e6 else 0)
            marked = any(SCOPE_RE.search(t["text"]) or PLANNY.search(t["text"]) or SOURCE_RE.search(t["text"]) for t in (a, b))
            anchored = bool(shared) or _shared_quals(ta, tb) > 0 or bool((a["fam"] & b["fam"]) - set(FAMILIES))
            if sc < 1 or not anchored or (sc < 2 and not marked):
                continue  # the same measure is not enough: a shared word, subject or named metric anchors it
            for me, other in ((a, b), (b, a)):  # each value keeps its best matches (ties included) in each other file
                k = (me["f"]["id"], id(me["v"]), other["file"])
                if k not in best or sc > best[k][0]:
                    best[k] = (sc, [other])
                elif sc == best[k][0]:
                    best[k][1].append(other)
    pairs = {}
    by_key = {(it["f"]["id"], id(it["v"])): it for it in items}
    for (fid, vid, ofile), (sc, others) in best.items():
        if len(others) > 2:
            continue  # many equally good candidates in one file: the match is not specific enough
        me = by_key[(fid, vid)]
        for other in others:
            key = tuple(sorted((me["f"]["id"], other["f"]["id"])))
            if key in seen or key in pairs:
                continue
            back = best.get((other["f"]["id"], id(other["v"]), me["file"]))
            if back and len(back[1]) <= 2 and any(x is me for x in back[1]):  # mutual: both sides rank each other first
                pairs[key] = (sc, me, other)
    # one conflict per quantity: the pairs that share a version join (a cost given as 3,52 / 3,74 / 4,03 M€)
    parent: dict = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    node = {}
    for key, (sc, a, b) in pairs.items():
        ka, kb = (a["f"]["id"], id(a["v"])), (b["f"]["id"], id(b["v"]))
        node[ka], node[kb] = a, b
        parent[find(ka)] = find(kb)
    groups: dict = {}
    for key, (sc, a, b) in pairs.items():
        groups.setdefault(find((a["f"]["id"], id(a["v"]))), []).append((key, sc, a, b))
    for members in groups.values():
        vers = {}
        for key, sc, a, b in members:
            seen.add(key)
            for it in (a, b):
                vers[(it["f"]["id"], id(it["v"]))] = it
        its = sorted(vers.values(), key=lambda it: it["base"])
        if len({it["file"] for it in its}) > 6:  # a chain across many files is not one quantity: keep its pairs
            chunks = [[a, b] for _, _, a, b in members]
        else:
            chunks = [its]
        for its in chunks:
            plan = {it["plan"] for it in its}
            kind = ("plan_vs_actual" if len(plan) > 1 else
                    "definition_mismatch" if any(SCOPE_RE.search(it["text"]) for it in its) else "value_mismatch")
            fams = set.intersection(*(it["fam"] for it in its)) or set.union(*(it["fam"] for it in its))
            out.append({"id": f"X{len(out) + 1:03d}", "type": kind, "measure": sorted(fams), "period": None,
                        "version_score": max(sc for _, sc, _, _ in members), "versions": len(its),
                        "facts": [{"fact": it["f"]["id"], "value": it["v"]["value"], "unit": it["v"]["unit"], "basis": it["v"].get("basis"),
                                   "source": it["file"], "says": it["text"][:120]} for it in its],
                        "resolution": None})


def review_conflict(work, cid: str, dismiss: bool, why: str, use: str | None = None) -> dict:
    """Record a reviewer's decision on one conflict in fact_conflicts.json (kept across re-runs)."""
    import json

    path = Path(work) / "fact_conflicts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    c = next((x for x in data.get("conflicts") or [] if x.get("id") == cid), None)
    if c is None:
        raise SystemExit(f"no conflict {cid} in {path}")
    if dismiss:
        if not why.strip():
            raise SystemExit("a dismissal needs a reason (--why): it is kept and shown to the next reviewer")
        c["dismissed"] = why.strip()
        c.pop("resolution", None)
    else:
        if use and use not in {x["fact"] for x in c["facts"]}:
            raise SystemExit(f"{use} is not one of the facts of {cid}")
        c["resolution"] = (f"use {use}" + (f": {why.strip()}" if why.strip() else "")) if use else (why.strip() or "resolved")
        c.pop("dismissed", None)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return c
