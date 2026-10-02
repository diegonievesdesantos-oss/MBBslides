"""Derived figures of an old deck (v2.0): totals, ratios and repeated figures, recomputed.

About half of the outdated numbers of a real deck are figures no new source restates: a table's total
column, a "net savings" row, a payback, the same total repeated as a KPI on the summary slide. They
are arithmetic on other numbers of the same deck. `relations` finds that arithmetic in the OLD deck
(where it must hold, to the deck's own rounding); `derive` recomputes each derived figure from the
new values of its parts, once every part has one.

    sum     a table's total column or total row, or "39 FTE (21 … y 18 …)" in a sentence
    ratio   payback = investment / savings, a share = part / whole (×100 for a percentage)
    same    the same figure shown elsewhere ("1,49 M€" on the summary = the table's 1.495 k€)
    grow    v2.2: a projection that grows at a rate the deck states ("Demanda prevista (+6%/año)"):
            each point = the previous one × (1 + rate); a point with its own new value keeps it
    line    v2.2: a cumulative cash curve that follows the simple payback model: point = −investment
            + n × annual savings, both figures of the deck
    group   v2.2: every restatement of one figure across the deck ("3,2 M€" in the summary, the plan
            table's 3.200 k€, the recommendation's "fase 1 por 3,2 M€") follows one value

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
    rels += _cumulative(plan)
    rels += _growth(plan)  # v2.2 (item 3)
    rels += _payback_curve(plan, {r["target"] for r in rels})
    rels += _same(plan, rels)
    rels += _same_slide(plan, {r["target"] for r in rels})
    return rels


def _same_slide(plan: dict, taken: set) -> list[dict]:
    """A headline repeating, word for word, a figure shown on its own slide ("se recupera en 3,7 años"
    and the KPI "3,7 años"): it follows that figure."""
    out = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        body = [q for q in s["numbers"] if _usable(q) and q["where"] != "title"]
        for q in s["numbers"]:
            if q["where"] != "title" or not _usable(q) or nid(n, q) in taken or len(re.sub(r"\D", "", q["raw"])) < 2:
                continue
            same = [b for b in body if b["raw"] == q["raw"]]
            if len(same) == 1:
                out.append({"op": "same", "target": nid(n, q), "parts": [nid(n, same[0])], "mult": 1.0, "how": f"same figure as {same[0]['where']}"})
    return out


CUM_RE = re.compile(r"acumulad|cumulativ|running total|cumulative|a origen|year-to-date|ytd", re.I)


def chart_series(slide: dict) -> dict:
    """{(exhibit, series): [numbers in category order]} for a slide's chart points."""
    out: dict = {}
    for q in slide["numbers"]:
        m = re.match(r"exhibit\[(\d+)\]\.(.+)\[(.*)\]$", q["where"])
        if m and q["kind"] == "data":
            out.setdefault((int(m.group(1)), m.group(2)), []).append(q)
    return out


def _cumulative(plan: dict) -> list[dict]:
    """v2.1 (item 5): a cumulative series (a cash curve) is the running sum of a flow series. When the
    deck shows that flow (or its yearly values), each point = the previous point + this year's flow."""
    rels = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        series = chart_series(s)
        for (e, name), pts in series.items():
            for (e2, name2), flows in series.items():
                if e2 != e or name2 == name or len(flows) != len(pts):
                    continue
                if all(_close(pts[k - 1]["value"] + flows[k]["value"], pts[k], [pts[k - 1], flows[k]]) for k in range(1, len(pts))):
                    for k in range(1, len(pts)):
                        rels.append({"op": "sum", "target": nid(n, pts[k]), "parts": [nid(n, pts[k - 1]), nid(n, flows[k])], "how": f"cumulative of '{name2}'"})
                    if _close(flows[0]["value"], pts[0]):  # a sum of one: the curve starts at the first flow
                        rels.append({"op": "sum", "target": nid(n, pts[0]), "parts": [nid(n, flows[0])], "how": f"cumulative of '{name2}'"})
                    break
    return rels


RATE_RE = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*%")


def _growth(plan: dict) -> list[dict]:
    """v2.2 (item 3): a chart series whose points grow at a rate the slide states, for at least its
    last three points: each = the previous × (1 + rate). The rate is the slide's own percentage when
    it shows one (then it follows that figure), else the one in the series' name."""
    rels = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        pcts = [q for q in s["numbers"] if q["kind"] == "pct" and _usable(q) and not q["where"].startswith("exhibit[")]
        for (e, name), pts in chart_series(s).items():
            if len(pts) < 3:
                continue
            rates = [(q["value"], q) for q in pcts] + [(float(m.replace(",", ".")), None) for m in RATE_RE.findall(name)]
            for g, q in rates:
                if not g:
                    continue
                ok = [k for k in range(1, len(pts)) if _close(pts[k - 1]["value"] * (1 + g / 100.0), pts[k], [pts[k - 1]])]
                tail = len(pts)
                while tail - 1 in ok:
                    tail -= 1
                if len(pts) - tail >= 3:  # the last three points or more grow at that rate
                    for k in range(tail, len(pts)):
                        r = {"op": "grow", "target": nid(n, pts[k]), "parts": [nid(n, pts[k - 1])], "rate": g,
                             "how": f"grows {g:g}% a year from the previous point ('{name}')"}
                        if q is not None:
                            r["parts"].append(nid(n, q))
                        rels.append(r)
                    break
    return rels


def _payback_curve(plan: dict, taken: set) -> list[dict]:
    """v2.2 (item 3): a cumulative cash curve the deck cannot sum (no flows shown) but whose tail is the
    simple payback model: point(year) = −investment + n × annual savings, with the investment and the
    savings figures of the deck (any slide, any scale). Only an unambiguous fit, over 3+ points."""
    from .deck_update import _key_measures, _measure_set, _stems

    figs = {"inver": [], "ahorr": []}
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for q in s["numbers"]:
            if not _usable(q) or q["where"].startswith("exhibit[") and ".rows[" not in q["where"]:
                continue
            ms = _key_measures(_measure_set(_stems(q.get("context") or "")))
            for m in figs:
                if m in ms and (q["kind"] == "money" or MONEY_RE.search(q.get("context") or "")):
                    figs[m].append((n, q))
    rels = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for (e, name), pts in chart_series(s).items():
            generic = len(name) < 3 or re.fullmatch(r"(serie|series|valor|value|datos|data)\s*\d*", name.strip(), re.I)
            if not CUM_RE.search(name + (" " + (s.get("headline") or "") if generic else "")) or len(pts) < 4:
                continue
            if any(nid(n, p) in taken for p in pts[1:]):
                continue  # already the running sum of flows the slide shows
            fits = []
            for ni, i in figs["inver"]:
                for nd, d in figs["ahorr"]:
                    for fi in (1.0, 1e-3, 1e-6, 1e3):
                        for fd in (1.0, 1e-3, 1e-6, 1e3):
                            I, D = abs(i["value"]) * fi, abs(d["value"]) * fd
                            if not D or I < D or I > 30 * D:
                                continue
                            tol = lambda k, m: _step(pts[k]) + _step(i) * fi + m * _step(d) * fd
                            last = len(pts) - 1
                            m_last = round((pts[last]["value"] + I) / D)
                            k0 = last
                            while k0 >= 0 and m_last - (last - k0) >= 1 and abs(-I + (m_last - (last - k0)) * D - pts[k0]["value"]) <= tol(k0, m_last - (last - k0)):
                                k0 -= 1
                            if last - k0 >= 3:
                                fits.append((last - k0, (ni, i, fi), (nd, d, fd), m_last))
            if not fits:
                continue
            best = max(f[0] for f in fits)
            top = [f for f in fits if f[0] == best]
            vals = {(round(abs(f[1][1]["value"]) * f[1][2], 9), round(abs(f[2][1]["value"]) * f[2][2], 9)) for f in top}
            if len(vals) != 1:
                continue  # two different pairs of figures fit as well: ambiguous
            span, (ni, i, fi), (nd, d, fd), m_last = min(top, key=lambda f: (".rows[" not in f[1][1]["where"], ".rows[" not in f[2][1]["where"]))
            last = len(pts) - 1
            for k in range(last - span + 1, last + 1):
                rels.append({"op": "line", "target": nid(n, pts[k]), "parts": [nid(ni, i), nid(nd, d)], "fi": fi, "fd": fd, "n": m_last - (last - k),
                             "how": f"payback curve: −investment ({i['raw']}) + {m_last - (last - k)} × annual savings ({d['raw']})"})
    return rels


def unrecomputable(plan: dict, rels: list[dict]) -> dict:
    """{number id: why} for the points of a cumulative series the deck cannot recompute: its flows
    are not shown, so a new curve needs the analysis (or values approved point by point)."""
    targets = {r["target"] for r in rels}
    out = {}
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for (e, name), pts in chart_series(s).items():
            generic = len(name) < 3 or re.fullmatch(r"(serie|series|valor|value|datos|data)\s*\d*", name.strip(), re.I)
            label = name + (" " + (s.get("headline") or "") if generic else "")  # the series' own name, or the slide's when it has none
            if CUM_RE.search(label) and not any(nid(n, p) in targets for p in pts[1:]):
                for p in pts:
                    out[nid(n, p)] = f"cumulative series '{name}': its yearly flows are not in the deck, so it cannot be recomputed from approved values — rebuild it in the analysis or approve its points"
    return out


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
            if r["op"] == "grow" and r["target"] in vals:
                continue  # a projected point with its own new value (an actual, a new forecast) keeps it
            pv = [vals[p] for p in r["parts"]]
            if r["op"] == "grow":
                rate = pv[1] if len(pv) > 1 else r["rate"]
                v = pv[0] * (1 + rate / 100.0)
            elif r["op"] == "line":
                v = -abs(pv[0]) * r["fi"] + r["n"] * pv[1] * r["fd"]
            elif r["op"] == "sum":
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


# ── v2.2 (item 2): one figure, one value across the deck ────────────────────────

ENT_RE = re.compile(r"\b(fase|phase|stage|etapa|zona|zone|escenario|scenario|opci[oó]n|option|planta|plant|site|lote|lot)\s*([0-9]+|[ivx]+\b|[a-d]\b)", re.I)
MULT_RE = re.compile(r"(multiplica\w*|veces|times|\bx\s*$|multiplie\w*)", re.I)


def _where_in_text(q: dict) -> tuple[str, re.Match | None]:
    """(the number's own text, the match of the number in it): its paragraph when known, else its context."""
    core, occ = q.get("core") or "", q.get("occ", 0)
    pat = rf"(?<![\d.,]){re.escape(core)}(?![\d])"
    ms = list(re.finditer(pat, q.get("text") or "")) if core else []
    if len(ms) > occ:
        return q["text"], ms[occ]
    m = re.search(pat, q.get("context") or "") if core else None  # the context is cut around this very occurrence
    return q.get("context") or "", m


def _local(q: dict) -> tuple[str, str]:
    """(the words just before the number, the words just after it, up to the next number)."""
    ctx, m = _where_in_text(q)
    if not m:
        return ctx, ""
    before, after = ctx[max(0, m.start() - 45):m.start()], ctx[m.end():m.end() + 30]
    after = re.split(r"\d", after)[0]
    before = re.split(r"[.;](?:\s|$)", before)[-1]  # the same sentence
    return before, after


POST_ENT_RE = re.compile(r"^\s*(?:[^\w\s(]{0,2}\s*)?(?:[mk]?€|m|k|%|\w{1,5})?\s*(?:en|de|del|para|in|for|of|on)\s+(?:la|el|the)?\s*"
                         r"(fase|phase|stage|etapa|zona|zone|escenario|scenario|opcion|option|planta|plant|site|lote|lot)\s*([0-9]+|[ivx]+\b|[a-d]\b)")


def _entities(q: dict) -> set:
    """The phase / zone / option a number is about: for a table cell, its row and column; in a
    sentence, the one named right after it ("2,4 M€ en la fase 2"), else the nearest one before it
    ("fase 1 (3,2 M€) y la fase 2 (2,4 M€)")."""
    from .deck_update import _plain

    if ".rows[" in q["where"]:
        return {(a[:4], b) for a, b in ENT_RE.findall(_plain(q.get("context") or ""))}
    ctx, m = _where_in_text(q)
    if m:
        post = POST_ENT_RE.match(_plain(ctx[m.end():m.end() + 40]))
        if post:
            return {(post.group(1)[:4], post.group(2))}
    before, after = _local(q)
    found = ENT_RE.findall(_plain(before)) or ENT_RE.findall(_plain(after))[:1]
    return {(a[:4], b) for a, b in found[-1:]}


def _measures(q: dict) -> set:
    from .deck_update import _key_measures, _measure_set, _stems

    if ".rows[" in q["where"] or re.match(r"exhibit\[\d+\]\.(.+)\[(.*)\]$", q["where"]):
        text = q.get("context") or ""
    else:  # the few words around the number say what it is ("39 FTE", "Invertir 5,6 M€")
        before, after = _local(q)
        wb, wa = re.findall(r"[^\W\d_]+", before), re.findall(r"[^\W\d_]+", after)
        for k in (3, 6):  # the nearest words first
            got = _key_measures(_measure_set(_stems(" ".join(wb[-k:] + wa[:k]))))
            if got:
                return got
        return set()
    return _key_measures(_measure_set(_stems(text)))


def _cls(q: dict) -> str:
    if q["kind"] == "pct":
        return "pct"
    if q["kind"] == "x" or (q["kind"] == "plain" and MULT_RE.search(_local(q)[0][-25:])):
        return "x"
    return "level"


UNIT_WORDS = {"fte", "ftes", "dias", "dia", "days", "day", "meses", "mes", "months", "month", "semanas", "weeks", "horas", "hours", "anos", "años",
              "years", "personas", "people", "empleados", "employees", "tiendas", "stores", "centros", "sites", "clientes", "customers",
              "pedidos", "orders", "lineas", "lines", "unidades", "units", "puestos", "camiones", "trucks", "m2", "km", "kg", "t", "toneladas"}


def _unit(q: dict) -> str:
    """The count unit written right after the number ("45 FTE", "45 días"), if it is one."""
    from .deck_update import _plain

    u = _plain(str(q.get("unit_after") or ""))
    return u if u in UNIT_WORDS else ""


def _scale(a: dict, b: dict) -> float | None:
    """f such that a's value = f × b's value (a power of ten), when the two are the same figure."""
    for f in (1.0, 1e3, 1e-3, 1e6, 1e-6, 1e9, 1e-9):
        if abs(abs(a["value"]) - abs(b["value"]) * f) <= max(_step(a), _step(b) * f) + 1e-9 * abs(a["value"]):
            return f
    return None


def _digits(q: dict) -> int:
    return len(re.sub(r"\D", "", q.get("core") or q["raw"]).lstrip("0"))


def _same_figure(a: tuple, b: tuple) -> tuple | None:
    """a, b: (slide, number, info). None when they cannot be one figure; else (scale between them,
    whether the pair is evidence that they are: the same measure, or a distinctive figure next to one
    that says what it is)."""
    (na, qa, ia), (nb, qb, ib) = a, b
    if ia["cls"] != ib["cls"] or _signed(qa) * _signed(qb) < 0 or ia["money"] != ib["money"]:
        return None
    ta, tb = qa["where"].split(".")[0], qb["where"].split(".")[0]
    if na == nb and ta == tb and ta.startswith("exhibit["):
        return None  # two cells of one table, two points of one chart: two quantities
    if ia["ents"] and ib["ents"] and not (ia["ents"] & ib["ents"]):
        return None
    if ia["unit"] and ib["unit"] and ia["unit"] != ib["unit"]:
        return None  # "45 FTE" and "45 días": the units the numbers are written with differ
    if ia["ms"] and ib["ms"] and not (ia["ms"] & ib["ms"]):
        return None
    f = _scale(qa, qb)
    if f is None:
        return None
    shared = bool(ia["ms"] & ib["ms"])
    one = bool(ia["ms"] or ib["ms"]) and min(ia["digits"], ib["digits"]) >= 2
    return f, shared or one


def groups(plan: dict) -> list[list[tuple]]:
    """Restatements of one figure across slides: [[(number id, f)], …] with f = that number's value
    over the group's first number's value. Built anchor-first (table cells, then KPIs and text): a
    number joins a group only if it is the same figure as every member that says what it is about."""
    nums = []
    for s in plan["slides"]:
        n = s["n"] if "n" in s else s["slide"]
        for q in s["numbers"]:
            if not _usable(q) or q.get("status") == "ignored":
                continue
            ctx = q.get("context") or ""
            nums.append((n, q, {"cls": _cls(q), "ents": _entities(q), "ms": _measures(q), "digits": _digits(q), "unit": _unit(q),
                                "money": q["kind"] == "money" or bool(MONEY_RE.search(ctx))}))
    rank = lambda x: (0 if ".rows[" in x[1]["where"] else 1 if x[1]["where"].startswith("exhibit[") else 2 if x[1]["where"] != "title" else 3)
    nums.sort(key=rank)
    out: list[list] = []
    for x in nums:
        for g in out:
            fs = [_same_figure(x, m) for m, _ in g]
            if all(f is not None for f in fs) and any(f[1] for f in fs):
                g.append((x, fs[0][0] * g[0][1]))
                break
        else:
            out.append([(x, 1.0)])
    return [[(nid(n, q), f) for (n, q, _), f in g] for g in out if len({n for (n, _, _), _ in g}) >= 2]


def with_groups(plan: dict, rels: list[dict], pick) -> list[dict]:
    """`rels` with each group's pairwise `same` relations replaced by the group's own: every member
    follows the head `pick(group)` chose, unless table arithmetic derives it."""
    grels = group_relations(plan, {r["target"] for r in rels if r["op"] != "same"}, pick)
    covered = {r["target"] for r in grels}
    return [r for r in rels if not (r["op"] == "same" and r["target"] in covered)] + grels


def group_relations(plan: dict, taken: set, pick) -> list[dict]:
    """A `same` relation from each group's head (`pick(group)`: a number id, or None) to every other
    member that no table arithmetic already derives."""
    where = {nid(s["n"] if "n" in s else s["slide"], q): (s["n"] if "n" in s else s["slide"], q["where"]) for s in plan["slides"] for q in s["numbers"]}
    out = []
    for gi, g in enumerate(groups(plan)):
        head = pick(g)
        if head is None:
            continue
        fh = dict(g)[head]
        hn, hw = where[head]
        for m, f in g:
            if m != head and m not in taken:
                out.append({"op": "same", "target": m, "parts": [head], "mult": f / fh, "group": gi,
                            "how": f"same figure as slide {hn} {hw} (one figure, one value across the deck)"})
    return out
