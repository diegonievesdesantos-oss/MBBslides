"""Derived figures of an old deck (v2.0): totals, ratios and repeated figures, recomputed.

About half of the outdated numbers of a real deck are figures no new source restates: a table's total
column, a "net savings" row, a payback, the same total repeated as a KPI on the summary slide. They
are arithmetic on other numbers of the same deck. `relations` finds that arithmetic in the OLD deck
(where it must hold, to the deck's own rounding); `derive` recomputes each derived figure from the
new values of its parts, once every part has one.

    sum     a table's total column or total row, or "39 FTE (21 … y 18 …)" in a sentence
    ratio   payback = investment / savings, a share = part / whole (×100 for a percentage)
    same    the same figure shown elsewhere ("1,49 M€" on the summary = the table's 1.495 k€)

A relation is accepted only when it holds exactly in the old deck (within the precision each number
is written with), and a derived value only when all its parts have a new value. Nothing here
decides: derived values are proposals, marked as such, for the same review as any other edit.
"""
from __future__ import annotations

import itertools
import re

TOTAL_RE = re.compile(r"\b(total|totales|suma|sum|neto|neta|net|resultado|result|ebitda|subtotal)\b", re.I)
RATIO_RE = re.compile(r"\b(payback|años|years|ratio|veces|times|margen|margin|cobertura|coverage|por|per|%|x)\b", re.I)
MONEY_RE = re.compile(r"(€|\$|£|\bk€|\bm€|\beur|ahorr|inversi|capex|caja|cash|mantenim|coste|cost|saving|ingres|ventas|revenue|ebitda|margen|margin)", re.I)
YEAR_RE = re.compile(r"^(19|20)\d\d$")


def nid(slide: int, q: dict) -> str:
    return f"{slide}|{q['where']}|{q.get('occ', 0)}|{q['raw']}"


def _step(q: dict) -> float:
    """Half a unit of the last written digit, in the number's own value units ('3,2' M€ → 0.05e6)."""
    from .deck_update import _core, _parse_core, _seps

    core = q.get("core") or _core(q["raw"])
    shown = _parse_core(core)
    if not shown or not q["value"]:
        return abs(q["value"]) * 0.005 + 1e-9
    dec_sep, _ = _seps(core)
    dec = len(core.split(dec_sep)[1]) if dec_sep in core else 0
    return 0.5 * 10 ** -dec * abs(q["value"]) / shown


def _close(x: float, q: dict, parts: list[dict] | None = None) -> bool:
    tol = _step(q) + sum(_step(p) for p in parts or [])
    return abs(abs(x) - abs(q["value"])) <= tol + 1e-9 * max(1.0, abs(x))


def _signed(q: dict) -> float:
    return -abs(q["value"]) if str(q.get("raw", "")).startswith("-") or q["value"] < 0 else q["value"]


def _usable(q: dict) -> bool:
    return q.get("status") != "ignored" and q["kind"] in ("plain", "data", "money", "pct", "x") and not YEAR_RE.match(q.get("core") or "") and q["value"] != 0


def _tables(slide: dict) -> dict:
    """{exhibit index: {(row, col): number}} for the slide's table cells."""
    out: dict = {}
    for q in slide["numbers"]:
        m = re.match(r"exhibit\[(\d+)\]\.rows\[(\d+)\]\[(\d+)\]", q["where"])
        if m and _usable(q):
            e, r, c = map(int, m.groups())
            out.setdefault(e, {}).setdefault((r, c), []).append(q)
    return {e: {k: v[0] for k, v in cells.items() if len(v) == 1} for e, cells in out.items()}


def relations(plan: dict) -> list[dict]:
    rels = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for e, cells in _tables(s).items():
            rows = sorted({r for r, _ in cells})
            cols = sorted({c for _, c in cells})
            # a total column: the right-most numeric cell of a row = the sum of the other cells of that row
            for r in rows:
                row = [(c, cells[(r, c)]) for c in cols if (r, c) in cells]
                if len(row) >= 3:
                    tgt, parts = row[-1][1], [q for _, q in row[:-1]]
                    if _close(sum(_signed(p) for p in parts), tgt, parts):
                        rels.append({"op": "sum", "target": nid(n, tgt), "parts": [nid(n, p) for p in parts], "how": "row total"})
            # a total row: a cell whose row label says total / net = the sum of the contiguous cells right above it
            for c in cols:
                col = [(r, cells[(r, c)]) for r in rows if (r, c) in cells]
                for i, (r, tgt) in enumerate(col):
                    if not TOTAL_RE.search(tgt.get("row") or tgt.get("context") or "") or i < 2:
                        continue
                    for k in range(2, i + 1):
                        parts = [q for _, q in col[i - k:i]]
                        if _close(sum(_signed(p) for p in parts), tgt, parts):
                            rels.append({"op": "sum", "target": nid(n, tgt), "parts": [nid(n, p) for p in parts], "how": "column total"})
                            break
                # a ratio row (payback = investment / savings) or a share (×100), from two other cells of the column
                for r, tgt in col:
                    if not RATIO_RE.search(tgt.get("context") or "") and tgt["kind"] not in ("pct", "x"):
                        continue
                    fits = []
                    for (_, a), (_, b) in itertools.permutations([(rr, q) for rr, q in col if q is not tgt], 2):
                        mult = 100.0 if tgt["kind"] == "pct" else 1.0
                        if b["value"] and _close(mult * abs(a["value"]) / abs(b["value"]), tgt):
                            fits.append((a, b, mult))
                    # several pairs fit (to the deck's rounding): the denominator that is itself a total / net row
                    found = next((f for f in fits if TOTAL_RE.search(f[1].get("row") or f[1].get("context") or "")), fits[0] if len(fits) == 1 else None)
                    if found:
                        a, b, mult = found
                        rels.append({"op": "ratio", "target": nid(n, tgt), "parts": [nid(n, a), nid(n, b)], "mult": mult, "how": "ratio in the column"})
        # a sentence that states a total and its parts: "39 FTE (21 en la fase 1 y 18 en la fase 2)"
        by_text: dict = {}
        for q in s["numbers"]:
            if q["where"] == "title" or q["where"].startswith("body["):
                if _usable(q):
                    by_text.setdefault(q["where"], []).append(q)
        for where, qs in by_text.items():
            for i, tgt in enumerate(qs):
                after = qs[i + 1:i + 4]
                for k in (3, 2):
                    parts = after[:k]
                    if len(parts) == k and all(p["kind"] == tgt["kind"] for p in parts) and _close(sum(p["value"] for p in parts), tgt, parts):
                        rels.append({"op": "sum", "target": nid(n, tgt), "parts": [nid(n, p) for p in parts], "how": "sum stated in the text"})
                        break
    rels += _same(plan, rels)
    return rels


def _same(plan: dict, rels: list[dict]) -> list[dict]:
    """A KPI or a sentence repeating a table figure (another scale allowed: '1,49 M€' = 1.495 k€),
    about the same measure: it follows that figure."""
    from .deck_update import _key_measures, _measure_set, _stems

    derived = {r["target"] for r in rels}
    tabled = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for q in s["numbers"]:
            if _usable(q) and q["where"].startswith("exhibit[") and ".rows[" in q["where"]:
                tabled.append((n, q, _measure_set(_stems(q.get("context") or ""))))
    out = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for q in s["numbers"]:
            if not _usable(q) or ".rows[" in q["where"]:
                continue  # table cells are what the others repeat
            ms = _key_measures(_measure_set(_stems(q.get("context") or "")))
            if not ms:
                continue
            hits = []
            for tn, t, tms in tabled:
                if not (ms & _key_measures(tms)) or (q["kind"] == "money") != bool(MONEY_RE.search(t.get("context") or "") or t["kind"] == "money"):
                    continue  # the same measure, and money only against a money row
                if (q["kind"] == "pct") != (t["kind"] == "pct") or (q["kind"] == "x") != (t["kind"] == "x"):
                    continue  # a share is not a level, a ratio is not a count
                for f in (1.0, 1e3, 1e6, 1e-3):
                    if abs(abs(q["value"]) - abs(t["value"]) * f) <= max(_step(q), _step(t) * f) + 1e-9 and len((q.get("core") or "").replace(",", "").replace(".", "")) >= 2:
                        hits.append((t, tn, f))
                        break
            # only an unambiguous match, preferably a derived total
            pref = [h for h in hits if nid(h[1], h[0]) in derived] or hits
            if len(pref) == 1:
                t, tn, f = pref[0]
                out.append({"op": "same", "target": nid(n, q), "parts": [nid(tn, t)], "mult": f, "how": f"same figure as slide {tn} {t['where']}"})
    return out


def derive(plan: dict, rels: list[dict], known: dict) -> dict:
    """{number id: (new value in its own units, relation)} for every derived number whose parts all have
    a new value. `known`: {number id: new value in its own units} (current numbers: their old value)."""
    vals = dict(known)
    out: dict = {}
    for _ in range(4):  # totals of totals, a KPI repeating a derived total
        changed = False
        for r in rels:
            if r["target"] in out or not all(p in vals for p in r["parts"]):
                continue
            pv = [vals[p] for p in r["parts"]]
            if r["op"] == "sum":
                v = sum(pv)
            elif r["op"] == "ratio":
                if not pv[1]:
                    continue
                v = r.get("mult", 1.0) * abs(pv[0]) / abs(pv[1])
            else:
                v = pv[0] * r.get("mult", 1.0)
            out[r["target"]] = (v, r)
            vals[r["target"]] = v
            changed = True
        if not changed:
            break
    return out
