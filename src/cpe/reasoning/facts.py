"""Structured fact model: sources → atomic, traceable facts.

Each fact is ONE claim with its values, period, unit and an exact source location (file, sheet,
A1 range or line). Table cells become `table_value` facts; numeric sentences become `text_statement`
facts (lower confidence: the number's meaning comes from prose); rows with two or more periods get
`derived_change` facts (absolute and relative change, with lineage to the cells they come from).
Nothing is interpreted beyond what the source says — insights are the agent's job.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import PROTOCOL_VERSION

PERIOD_RE = re.compile(
    r"\b(?:(?P<fy>FY|CY)\s?'?(?P<fyy>\d{2}|\d{4})(?P<fs>[EABF])?|(?P<q>Q[1-4])\s?'?(?P<qy>\d{2}|\d{4})?|(?P<h>H[12])\s?'?(?P<hy>\d{2}|\d{4})?"
    r"|(?P<y>(?:19|20)\d{2})(?P<ys>[EABF])?|(?P<w>YTD|LTM|TTM|run[- ]rate))\b", re.IGNORECASE)
BASIS_WORDS = {"budget": "budget", "presupuesto": "budget", "forecast": "forecast", "previsión": "forecast", "prevista": "forecast",
               "previsto": "forecast", "projected": "forecast", "proyectad": "forecast", "expected": "forecast", "target": "target",
               "objetivo": "target", "plan": "plan", "propose": "plan", "proposes": "plan", "proposal": "plan", "proponemos": "plan",
               "propone": "plan", "propuesta": "plan", "actual": "actual", "real": "actual", "estimate": "estimate", "est.": "estimate"}
SUFFIX_BASIS = {"E": "estimate", "A": "actual", "B": "budget", "F": "forecast"}
UNIT_RE = re.compile(r"(€|\$|£|eur|usd|gbp)\s?(m|mn|bn|k|million|billion|thousand)?|\b(m|mn|bn|k)\s?(€|\$|£|eur|usd)|%|\bpp\b|\bbps\b|\bdays?\b|\bmonths?\b|\byears?\b",
                     re.IGNORECASE)


def detect_period(text: str) -> dict | None:
    """'FY25E' → {'period': 'FY2025', 'basis': 'estimate'}; 'Q3 2025' → {'period': '2025-Q3'}; 'YTD' → {'period': 'YTD'}."""
    t = str(text or "")
    m = PERIOD_RE.search(t)
    if not m:
        return None
    g = m.groupdict()

    def yy(s):
        return None if not s else (int(s) + 2000 if len(s) == 2 else int(s))

    basis = next((b for w, b in BASIS_WORDS.items() if re.search(rf"(?<![a-záéíóúñ]){re.escape(w)}(?![a-záéíóúñ])", t.lower())), None)  # "plan", not "plantilla"
    if g["fy"]:
        out = {"period": f"{g['fy'].upper()}{yy(g['fyy'])}", "basis": SUFFIX_BASIS.get((g["fs"] or "").upper(), basis or "actual")}
    elif g["q"]:
        out = {"period": f"{yy(g['qy'])}-{g['q'].upper()}" if g["qy"] else g["q"].upper(), "basis": basis or "actual"}
    elif g["h"]:
        out = {"period": f"{yy(g['hy'])}-{g['h'].upper()}" if g["hy"] else g["h"].upper(), "basis": basis or "actual"}
    elif g["y"]:
        out = {"period": g["y"], "basis": SUFFIX_BASIS.get((g["ys"] or "").upper(), basis or "actual")}
    else:
        out = {"period": g["w"].upper().replace(" ", "-"), "basis": basis or "actual"}
    return out


def detect_unit(text: str) -> str:
    """Normalised unit token of a header / label: 'EUR_M', 'USD_K', 'PCT', 'PP', 'BPS', 'DAYS', '' …"""
    t = str(text or "").replace("_", " ")  # "opening_arr_eur_m"
    t = re.sub(r"\s*(/\s*(año|year|yr|mes|month)|per (year|month|annum)|al año|a year|al mes|por año)\b", "", t, flags=re.I)  # a rate, not the unit
    m = UNIT_RE.search(t)
    if not m:
        w = next((UNIT_WORDS[x] for x in re.findall(r"[a-záéíóúñ]+", t.lower()) if x in UNIT_WORDS and UNIT_WORDS[x] != "PP"), "")
        return w
    s = m.group(0).lower().replace(" ", "")
    cur = "EUR" if ("€" in s or "eur" in s) else "USD" if ("$" in s or "usd" in s) else "GBP" if ("£" in s or "gbp" in s) else None
    scale = "BN" if ("bn" in s or "billion" in s) else "M" if re.search(r"m(n|illion)?$|^m", s.replace("€", "").replace("$", "").replace("£", "").replace("eur", "")
                                                                      .replace("usd", "").replace("gbp", "")) else "K" if ("k" in s or "thousand" in s) else ""
    if cur:
        return f"{cur}_{scale}" if scale else cur
    if s == "%":
        return "PCT"
    if s == "pp":
        return "PP"
    if s == "bps":
        return "BPS"
    return s.upper().rstrip("S") + "S" if s.startswith(("day", "month", "year")) else s.upper()


SCALE_WORDS = {"m": "M", "mn": "M", "million": "M", "millones": "M", "bn": "BN", "billion": "BN", "k": "K", "thousand": "K"}
SCALE_AFTER = re.compile(r"\s*(m|mn|million|millones|bn|billion|k|thousand)\b(?:\s+de)?\s*(€|\$|£|eur(?:os)?\b|usd\b|gbp\b|dólares\b)?", re.I)


def unit_from_raw(raw: str) -> str:
    """Unit of a number as written in prose: '€1,500M' → EUR_M, '24%' → PCT, '$3.2bn' → USD_BN."""
    r = str(raw or "").strip().lower()
    cur = "EUR" if ("€" in r or "eur" in r) else "USD" if ("$" in r or "usd" in r) else "GBP" if ("£" in r or "gbp" in r) else None
    suf = re.sub(r"[\d\s.,+\-−€$£]", "", r).replace("eur", "").replace("usd", "").replace("gbp", "")
    if suf == "%":
        return "PCT"
    if suf in ("pp", "bps"):
        return suf.upper()
    scale = {"m": "M", "mn": "M", "million": "M", "bn": "BN", "billion": "BN", "k": "K", "thousand": "K"}.get(suf, "")
    if cur:
        return f"{cur}_{scale}" if scale else cur
    return scale and f"PLAIN_{scale}"


UNIT_WORDS = {"day": "DAYS", "days": "DAYS", "día": "DAYS", "días": "DAYS", "dias": "DAYS", "week": "WEEKS", "weeks": "WEEKS", "semana": "WEEKS",
              "semanas": "WEEKS", "month": "MONTHS", "months": "MONTHS", "mes": "MONTHS", "meses": "MONTHS", "year": "YEARS", "years": "YEARS",
              "año": "YEARS", "años": "YEARS", "hour": "HOURS", "hours": "HOURS", "hora": "HOURS", "horas": "HOURS", "min": "MINUTES",
              "minutes": "MINUTES", "minutos": "MINUTES", "points": "PP", "puntos": "PP", "pts": "PP"}


def period_near(raw: str, context: str) -> dict | None:
    """The period a number belongs to in prose: the first period mentioned after it, before the next
    number ('38% in FY2025, up from 29% in FY2024' → FY2025 / FY2024); else the sentence's period."""
    i = context.find(raw)
    if i < 0:
        return detect_period(context)
    after = context[i + len(raw):]
    nxt = re.search(r"[-−+]?\d", re.sub(PERIOD_RE, lambda m: " " * len(m.group(0)), after))
    seg = after[: nxt.start()] if nxt else after
    m = PERIOD_RE.search(seg)
    if m and re.search(r"\b(than|vs\.?|versus|compared|que en|que|frente a|respecto a)\b", seg[: m.start()], re.I):
        before = detect_period(context[:i])  # "15% more than in 2025": 2025 is the base, not the number's period
        if before:
            return before
    per = detect_period(seg)
    if per:
        sent = detect_period(context)
        if sent and sent.get("basis") != "actual" and per.get("basis") == "actual":
            per["basis"] = sent["basis"]  # "the 2026 budget assumes … growth": basis from the sentence
        return per
    return detect_period(context)


def unit_in_context(raw: str, context: str) -> str:
    """Unit stated by the word after a number in prose: 'from 2,1 to 4,6 días' → DAYS for both
    numbers of a range."""
    i = context.find(raw)
    if i < 0:
        return ""
    after = context[i + len(raw):]
    m = re.match(r"\s*(?:(?:to|a|y|and|-|–)\s*[-−+]?[\d.,]+\s*)?([A-Za-zÀ-ÿ]+)", after)
    return UNIT_WORDS.get(m.group(1).lower(), "") if m else ""


def _col(j: int) -> str:
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def _fmt(v: float) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".") if not float(v).is_integer() else f"{int(v):,}"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_manifest(paths: list[Path]) -> dict:
    return {"protocol": PROTOCOL_VERSION, "sources": [{"file": p.name, "sha256": _sha(p), "bytes": p.stat().st_size} for p in paths]}


def _table_facts(t: dict, next_id) -> list[dict]:
    facts = []
    header = [str(h) for h in t["header"]]
    numeric = set(t["numeric_columns"])
    year_cols = []
    for j in list(numeric):  # a year column ("year", "año", "FY") labels its row, it is not a measure
        vals = [r[j] for r in t["rows"] if j < len(r) and r[j] not in (None, "")]
        if re.fullmatch(r"\s*(year|años?|ejercicio|fy|fiscal year|period|periodo)\s*", header[j], re.I) and vals \
                and all(float(v).is_integer() and 1900 <= float(v) <= 2100 for v in vals):
            numeric.discard(j)
            year_cols.append(j)
            for r in t["rows"]:
                if j < len(r) and r[j] not in (None, ""):
                    r[j] = str(int(float(r[j])))
    label_cols = [j for j in range(len(header)) if j not in numeric]
    sheet = t["loc"].replace("sheet", "").strip() or None
    # a table-wide unit only when the LABEL column header states it ("Line (€M)"); a unit in one
    # value column ("Churn 2025 (%)") never spreads to its neighbours (found by the churn_es case)
    table_unit = detect_unit(header[label_cols[0]]) if label_cols else ""
    for i, row in enumerate(t["rows"]):
        label = " · ".join(str(row[j]) for j in label_cols if j < len(row) and str(row[j]).strip()) or f"row {i + 2}"
        cells = {}
        for j in sorted(numeric):
            if j >= len(row) or row[j] is None or row[j] == "":
                continue
            v = float(row[j])
            per = detect_period(header[j]) or next((detect_period(str(row[y])) for y in year_cols if y < len(row)), None)
            unit = detect_unit(header[j]) or detect_unit(label) or table_unit
            fid = next_id()
            rng = f"{_col(j)}{i + 2}"
            facts.append({"id": fid, "claim": f"{label} — {header[j]}: {_fmt(v)}{(' ' + unit) if unit else ''}",
                          "values": [{"value": v, "unit": unit, "period": (per or {}).get("period"), "basis": (per or {}).get("basis"), "label": label,
                                      "column": header[j]}],
                          "source": {"file": t["source"], "sheet": sheet, "range": rng, "loc": t["loc"]}, "fact_type": "table_value", "confidence": 1.0})
            cells[j] = facts[-1]
        groups: dict = {}  # one measure observed in several periods: "Revenue FY2024 (€M)" + "Revenue FY2025 (€M)"
        for j, f in cells.items():
            v = f["values"][0]
            if v["period"]:
                measure = re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", PERIOD_RE.sub("", header[j]))).strip(" -–·") or "value"
                groups.setdefault((measure.lower(), v["unit"], v["basis"]), []).append(f)
        for (measure, _, _), fs in groups.items():
            if len(fs) < 2:
                continue
            a, b = fs[0], fs[-1]
            va, vb = a["values"][0], b["values"][0]
            d = vb["value"] - va["value"]
            pct_unit = va["unit"] == "PCT"
            per = f"{va['period']}→{vb['period']}"
            vals = [{"value": d, "unit": "PP" if pct_unit else va["unit"], "period": per, "label": label, "kind": "change"}]
            if va["value"] and not pct_unit:
                vals.append({"value": d / abs(va["value"]) * 100, "unit": "PCT", "period": per, "label": label, "kind": "relative_change"})
            name = measure
            facts.append({"id": next_id(), "claim": f"{label} — {name}: {_fmt(va['value'])} → {_fmt(vb['value'])} ({per}), change {_fmt(d)}"
                          + (f" ({d / abs(va['value']) * 100:+.1f}%)" if va["value"] and not pct_unit else (" pp" if pct_unit else "")),
                          "values": vals, "source": {"file": t["source"], "sheet": sheet, "range": f"{a['source']['range']}:{b['source']['range']}", "loc": t["loc"]},
                          "fact_type": "derived_change", "confidence": 1.0, "derived_from": [a["id"], b["id"]], "operation": "last − first"})
    return facts


def build_fact_model(paths: list[str | Path]) -> dict:
    """Read sources and return {"protocol", "facts": [...], "stats": {...}}."""
    from ..ingest.readers import ingest

    paths = [Path(p) for p in paths]
    inv = ingest(paths)
    n = [0]

    def next_id():
        n[0] += 1
        return f"F{n[0]:04d}"

    facts = []
    for t in inv["tables"]:
        facts += _table_facts(t, next_id)
    by_sentence: dict = {}  # one text fact per sentence, with every number it states
    for f in inv["facts"]:
        by_sentence.setdefault((f["source"], f["loc"], f["context"]), []).append(f)
    for (src, loc, ctx), fs in by_sentence.items():
        vals = []
        for f in fs:
            per = period_near(f["raw"], ctx)
            unit = unit_from_raw(f["raw"])
            after = ctx[ctx.find(f["raw"]) + len(f["raw"]):] if f["raw"] in ctx else ""
            if unit.startswith("PLAIN_") and re.match(r"\s*(€|eur)", after, re.I):  # "12 M€"
                unit = "EUR_" + unit.split("_")[1]
            sa = SCALE_AFTER.match(after)
            if sa and (unit in ("EUR", "USD", "GBP") or (not unit and sa.group(2))):  # "25 EUR M", "3,2 millones de euros"
                cur = unit or {"€": "EUR", "$": "USD", "£": "GBP"}.get(sa.group(2), (sa.group(2) or "eur")[:3].upper().replace("DÓL", "USD"))
                unit = f"{cur}_{SCALE_WORDS[sa.group(1).lower()]}"
            elif not unit and re.match(r"\s*(euros?|dólares|dollars)\b", after, re.I):  # "250.000 euros"
                unit = "USD" if re.match(r"\s*d", after, re.I) else "EUR"
            vals.append({"value": f["value"], "unit": unit or unit_in_context(f["raw"], ctx), "raw": f["raw"],
                         "period": (per or {}).get("period"), "basis": (per or {}).get("basis")})
        facts.append({"id": next_id(), "claim": ctx, "values": vals,
                      "source": {"file": src, "loc": loc}, "fact_type": "text_statement", "confidence": 0.8})
    stats = {"sources": len(inv["sources"]), "tables": len(inv["tables"]), "facts": len(facts),
             "by_type": {k: sum(1 for f in facts if f["fact_type"] == k) for k in ("table_value", "derived_change", "text_statement")}}
    return {"protocol": PROTOCOL_VERSION, "facts": facts, "stats": stats, "blocks": inv["blocks"]}


EXTRACTOR_VERSION = "1.8"  # bump when extraction changes what facts or values are produced


def fact_key(f: dict) -> tuple:
    """Where a fact sits in its source, independent of the extractor version: a table cell (or cell
    pair for a derived change), or a sentence location plus the values it states."""
    src = f.get("source") or {}
    if src.get("range"):
        return ("cell", src.get("file"), src.get("sheet"), src.get("range"))
    vals = tuple(sorted(round(abs(float(v["value"])), 6) for v in f.get("values") or []))
    return ("text", src.get("file"), src.get("loc"), vals)


def preserve_ids(old: list[dict], new: list[dict]) -> tuple[list[dict], dict]:
    """Give re-extracted facts the ids of the same facts in the previous model, so hypotheses,
    insights, storylines, deck plans and decks keep pointing at the right facts after an extractor
    upgrade. New facts get fresh ids after the highest old one; old facts that are no longer
    extracted are reported (a citation of one is then an UNKNOWN_FACT)."""
    by_key: dict = {}
    for f in old:
        by_key.setdefault(fact_key(f), f["id"])
    loose: dict = {}  # text facts whose values changed (a unit fix): same sentence, first value
    for f in old:
        k = fact_key(f)
        if k[0] == "text" and k[3]:
            loose.setdefault((k[1], k[2], k[3][0]), f["id"])
    nums = [int(re.sub(r"\D", "", f["id"]) or 0) for f in old if re.fullmatch(r"F\d+", f["id"])]
    nxt = max(nums, default=0)
    mapping, used, added = {}, set(), []
    for f in new:
        k = fact_key(f)
        oid = by_key.get(k)
        if oid is None and k[0] == "text" and k[3]:
            oid = loose.get((k[1], k[2], k[3][0]))
        if oid is None or oid in used:
            nxt += 1
            oid = f"F{nxt:04d}"
            added.append(oid)
        used.add(oid)
        mapping[f["id"]] = oid
    out = []
    for f in new:
        g = {**f, "id": mapping[f["id"]]}
        if g.get("derived_from"):
            g["derived_from"] = [mapping.get(x, x) for x in g["derived_from"]]
        out.append(g)
    dropped = sorted(f["id"] for f in old if f["id"] not in used)
    return out, {"kept": len(used) - len(added), "added": added, "dropped": dropped,
                 "note": "ids preserved by source location; a citation of a dropped id is an UNKNOWN_FACT"}


def write_fact_model(sources_dir: str | Path, work_dir: str | Path) -> dict:
    src = Path(sources_dir)
    paths = sorted(p for p in src.rglob("*") if p.is_file() and not p.name.startswith("."))
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    (work / "source_manifest.json").write_text(json.dumps(source_manifest(paths), indent=2) + "\n", encoding="utf-8")
    fm = build_fact_model(paths)
    blocks = fm.pop("blocks")
    prev = work / "facts.json"
    if prev.exists():  # re-extraction keeps the ids the agent's artifacts already cite (v1.8)
        old = json.loads(prev.read_text(encoding="utf-8"))
        fm["facts"], refresh = preserve_ids(old.get("facts") or [], fm["facts"])
        (work / "facts_refresh.json").write_text(json.dumps(refresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fm["extractor"] = EXTRACTOR_VERSION
    (work / "facts.json").write_text(json.dumps(fm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from .conflicts import detect_conflicts

    cf = work / "fact_conflicts.json"
    if not cf.exists():  # never overwrite the agent's resolutions
        cf.write_text(json.dumps({"protocol": PROTOCOL_VERSION, "conflicts": detect_conflicts(fm["facts"])}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (work / "source_text.json").write_text(json.dumps({"protocol": PROTOCOL_VERSION, "blocks": blocks}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fm
