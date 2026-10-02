"""Cell-to-fact binding (v1.8, closes the DEBT F1 residual).

Since 1.7.1 every table cell and chart value must BE a cited fact value. That still lets a real value
sit in the wrong cell: on a slide citing "Norte 70" and "Sur 50", a table printing Norte 50 passes.
Two checks close it:

- **Explicit binding (hard).** An evidence item may name the cell it supports:
  `{"fact": "F0012", "at": "visual.rows[1][2]"}` (a table cell) or
  `{"fact": "F0013", "at": "visual.data.series[0].values[3]"}` (a chart point). The value at that
  path must be a value of that fact (any scale, display rounding). A wrong value or a path that does
  not exist is an error.
- **Label binding (warning).** For a table cell or chart point that is not explicitly bound, its row
  label (first text cell / category) and column label (header / series name) are compared with the
  claims of the cited facts holding that value. When none of those facts mentions the row label but
  another cited fact that mentions it holds a different value, the cell is probably misplaced.
"""
from __future__ import annotations

import re
import unicodedata

from .conflicts import STOP

SCALES = (1, 1e3, 1e-3, 1e6, 1e-6)
GENERIC = {"total", "valor", "value", "importe", "cifra", "dato", "eur", "usd", "pct"}


def _words(t) -> set[str]:
    t = unicodedata.normalize("NFKD", str(t or "").lower().replace("_", " "))
    return {w for w in re.findall(r"[a-zñ]{3,}", "".join(c for c in t if not unicodedata.combining(c)))} - STOP


def _matches(v: float, fact: dict) -> bool:
    s = f"{abs(v):g}"
    tol = 0.5 * 10 ** -(len(s.split(".")[1]) if "." in s else 0) + 1e-6 * abs(v)
    return any(abs(abs(float(x["value"])) * k - abs(v)) <= tol for x in fact.get("values") or [] for k in SCALES)


def _fact_text(f: dict) -> str:
    return " ".join([f.get("claim") or ""] + [str(x.get("label") or "") + " " + str(x.get("period") or "") for x in f.get("values") or []])


def _num(c):
    if isinstance(c, bool):
        return None
    if isinstance(c, (int, float)):
        return float(c)
    if isinstance(c, dict):
        return _num(c.get("value"))
    if isinstance(c, str) and re.fullmatch(r"\s*[-+−]?[\d.,]+\s*", c):
        from ..ingest.readers import _num as rn
        return rn(c.strip())[0]
    return None


def _label(c) -> str:
    if isinstance(c, dict):
        return str(c.get("label") or c.get("text") or c.get("value") or "")
    return str(c or "")


def cells(visual: dict, base: str = "visual"):
    """(path, value, row label, column label) for every numeric table cell and chart point."""
    if not isinstance(visual, dict):
        return
    if isinstance(visual.get("rows"), list):
        cols = [_label(c) for c in visual.get("columns") or []]
        for i, row in enumerate(visual["rows"]):
            if not isinstance(row, list):
                continue
            rlabel = next((_label(c) for c in row if _num(c) is None and _label(c)), "")
            for j, c in enumerate(row):
                v = _num(c)
                if v is not None:
                    yield f"{base}.rows[{i}][{j}]", v, rlabel, cols[j] if j < len(cols) else ""
    data = visual.get("data") if isinstance(visual.get("data"), dict) else visual
    if isinstance(data.get("series"), list):
        cats = [_label(c) for c in data.get("categories") or []]
        pre = f"{base}.data" if data is not visual else base
        for k, s in enumerate(data["series"]):
            if not isinstance(s, dict):
                continue
            for j, c in enumerate(s.get("values") or []):
                v = _num(c)
                if v is not None:
                    yield f"{pre}.series[{k}].values[{j}]", v, cats[j] if j < len(cats) else "", _label(s.get("name"))
    if isinstance(data.get("steps"), list):
        pre = f"{base}.data" if data is not visual else base
        for j, st in enumerate(data["steps"]):
            v = _num(st.get("value")) if isinstance(st, dict) else None
            if v is not None:
                yield f"{pre}.steps[{j}].value", v, _label(st.get("label")), ""


def _get(obj, path: str):
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            i = int(part[1:-1])
            if not isinstance(obj, list) or i >= len(obj):
                return KeyError
            obj = obj[i]
        else:
            if not isinstance(obj, dict) or part not in obj:
                return KeyError
            obj = obj[part]
    return obj


def check_binding(slide: dict, facts: dict, issue) -> list[dict]:
    sid = slide.get("id")
    out = []
    ev = [e for e in slide.get("evidence") or [] if isinstance(e, dict) and e.get("fact")]
    bound = set()
    for e in ev:
        at = e.get("at")
        if not at:
            continue
        for p in [at] if isinstance(at, str) else list(at):
            bound.add(p)
            got = _get(slide, p)
            f = facts.get(e["fact"])
            if got is KeyError:
                out.append(issue("error", "BINDING_PATH_MISSING", "deck.json", f"{sid}:{p}", f"evidence {e['fact']} is bound to {p}, which does not exist on the slide", True))
                continue
            v = _num(got)
            if f is None:
                continue
            if v is None or not _matches(v, f):
                out.append(issue("error", "CELL_MISBOUND", "deck.json", f"{sid}:{p}",
                                 f"{p} shows {got!r}, which is not a value of {e['fact']} ({(f.get('claim') or '')[:80]})", True))
    cited = [facts[e["fact"]] for e in ev if e["fact"] in facts] + [facts[x] for x in slide.get("facts") or [] if x in facts]
    if len(cited) < 2:
        return out
    for path, v, rlabel, clabel in cells(slide.get("visual") or {}):
        if path in bound or (float(v).is_integer() and abs(v) <= 10):
            continue
        rw = _words(rlabel) - _words(clabel)
        if not rw:
            continue
        holders = [f for f in cited if _matches(v, f)]
        if not holders or any(rw & _words(_fact_text(f)) for f in holders):
            continue
        cw = _words(clabel) - GENERIC
        need = min(2, len(rw))
        # the fact that should be in this cell names the row strongly, and the column too when it has its own words
        about = [f for f in cited if len(rw & _words(_fact_text(f))) >= need and (not cw or cw & _words(_fact_text(f))) and not _matches(v, f)]
        if about:
            out.append(issue("warning", "CELL_MISBOUND", "deck.json", f"{sid}:{path}",
                             f"{v:g} in row '{rlabel}' is a value of {', '.join(f['id'] for f in holders[:2])}, which is not about '{rlabel}'; "
                             f"{about[0]['id']} is ({(about[0].get('claim') or '')[:70]}). Bind the cell with \"at\" or fix it"))
    return out
