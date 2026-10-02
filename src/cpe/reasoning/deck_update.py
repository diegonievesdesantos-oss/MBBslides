"""Existing-deck ingestion and update (v1.8): old client deck + new data + new question → updated deck.

    cpe deck ingest old.pptx -o work/         → work/old_deck.json      what the old deck says and how
                                                work/old_deck_spec.json a starting deck.json: same storyline,
                                                                         roles and exhibits rebuilt natively
                                                work/old_ghost.md       the old argument, headlines only
    cpe deck stale work/                       → work/update_plan.json/.md  every number in the old deck
                                                checked against the NEW fact model: current / outdated
                                                (with the new value and its fact id) / untraced

The old deck is a source of structure and conventions, never of facts: an old number is reused only
once the new fact model confirms it. Nothing is silently carried over.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from ..qa.proof import headline_quantities

ROLE_RULES = [
    ("agenda", r"\b(agenda|índice|indice|contents|contenido)\b"),
    ("exec_summary", r"\b(executive summary|resumen ejecutivo|resumen|summary|key messages|mensajes clave)\b"),
    ("next_steps", r"\b(next steps|próximos pasos|proximos pasos|decisions?|decisiones|asks?|la petición)\b"),
    ("appendix", r"\b(appendix|anexo|apéndice|backup)\b"),
]
CHART_TYPE = {"BAR_CLUSTERED": "bar", "COLUMN_CLUSTERED": "column", "BAR_STACKED": "stacked_bar", "COLUMN_STACKED": "stacked_column",
              "BAR_STACKED_100": "stacked_100", "COLUMN_STACKED_100": "stacked_100", "LINE": "line", "LINE_MARKERS": "line", "PIE": "pie",
              "DOUGHNUT": "donut", "AREA": "area", "XY_SCATTER": "scatter", "BUBBLE": "bubble"}


def _shape_texts(slide):
    out = []
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            size = max((r.font.size.pt for p in sh.text_frame.paragraphs for r in p.runs if r.font.size), default=0)
            is_title = bool(getattr(sh, "is_placeholder", False) and sh.placeholder_format.type is not None
                            and "TITLE" in str(sh.placeholder_format.type))
            out.append({"text": " ".join(sh.text_frame.text.split()), "size": size, "top": sh.top or 0, "title": is_title,
                        "fonts": [r.font.name for p in sh.text_frame.paragraphs for r in p.runs if r.font.name]})
    return out


NUM_RE = re.compile(r"\d[\d.,]*")


def _locate(text: str, raw: str, start: int = 0):
    """The number `raw` ("€5,6 M", "2,4x") in the slide text, from `start`."""
    core = NUM_RE.search(raw or "")
    if not core:
        return None
    return re.compile(rf"(?<![\d.,]){re.escape(core.group(0))}(?![\d])").search(text or "", start)


def _core(raw: str) -> str:
    m = NUM_RE.search(raw or "")
    return m.group(0).rstrip(".,") if m else ""


def _occurrences(text: str, raw: str) -> list:
    core = _core(raw)
    return list(re.finditer(rf"(?<![\d.,]){re.escape(core)}(?![\d])", text or "")) if core else []


def _seps(core: str, hint: str | None = None) -> tuple[str, str]:
    """(decimal, thousands) separators of a written number; `hint` is the decimal separator of the deck."""
    if "," in core and "." in core:
        return (",", ".") if core.rfind(",") > core.rfind(".") else (".", ",")
    for sep in (",", "."):
        if sep in core:
            if re.fullmatch(rf"\d{{1,3}}(\{sep}\d{{3}})+", core) and not (hint == sep and core.count(sep) == 1):
                return ("," if sep == "." else "."), sep
            return sep, ("." if sep == "," else ",")
    d = hint or "."
    return d, ("." if d == "," else ",")


def _parse_core(core: str, hint: str | None = None) -> float | None:
    """'3,2' → 3.2, '38.500' → 38500, '1,374.5' → 1374.5."""
    dec, th = _seps(core, hint)
    try:
        return float(core.replace(th, "").replace(dec, "."))
    except ValueError:
        return None


def format_like(core: str, value: float, hint: str | None = None) -> str:
    """`value` written the way `core` is: decimal and thousands separators, and its decimals unless
    they would hide more than 0.5% of the value ('4,0' for 4.034 → '4,03')."""
    dec_sep, th_sep = _seps(core, hint)
    dec = len(core.split(dec_sep)[1]) if dec_sep in core else 0
    v = abs(value)
    while dec < 3 and v and abs(round(v, dec) - v) / v > 0.005:
        dec += 1
    grouped = bool(th_sep in core) or (v >= 10000 and bool(re.search(r"\d[.,]\d{3}", core)))
    s = f"{v:,.{dec}f}" if grouped else f"{v:.{dec}f}"
    s = s.replace(",", "\x00").replace(".", dec_sep).replace("\x00", th_sep)
    return ("-" if value < 0 else "") + s


def _new_display(q: dict, c: dict) -> str | None:
    """The new value expressed in the old number's own scale and notation ('3,2' M€ → '4,03')."""
    hint = q.get("_hint") or ("," if re.search(r"\d,\d{1,2}(?!\d)", q.get("text") or "") else None)
    shown = _parse_core(q.get("core") or _core(q["raw"]), hint)
    if not shown or not q["value"]:
        return None
    factor = abs(q["value"]) / shown  # what one written unit of the old number is worth (1e6 for "3,2 M€")
    opts = [abs(c["base"]), abs(c["value"])] + [abs(c["value"]) * k for k in (1e3, 1e-3, 1e6, 1e-6)]
    best = min((o for o in opts if o), key=lambda o: abs(math.log(o / abs(q["value"]))), default=None)
    if best is None:
        return None
    sign = -1.0 if (q["value"] < 0 or str(q.get("raw", "")).startswith("-")) and c["value"] >= 0 else (-1.0 if c["value"] < 0 else 1.0)
    return format_like(q.get("core") or _core(q["raw"]), sign * best / factor, hint)  # a cost the deck shows negative stays negative


def _window(text: str, m) -> str:
    """The words that belong to this number: back to the previous number (or 70 characters), forward
    to the next one (or 30): "fase 1: 3,2 · fase 2: 2,4" gives 3,2 its own words, not 2,4's."""
    before = [n.end() for n in NUM_RE.finditer(text[:m.start()])
              if not re.search(r"\b(fase|phase|stage)\s*$", text[max(0, n.start() - 8):n.start()], re.I)]  # "fase 1" is a name, not a number
    start = max(before[-1] if before else 0, m.start() - 70)
    if not before:
        start = max(0, m.start() - 160)
    elif len(re.findall(r"[A-Za-záéíóúñ]{4,}", text[start:m.start()])) < 2:
        # "reduce 39 FTE (21 en la fase 1": the words before the previous number name this one too
        ws = list(re.finditer(r"[A-Za-záéíóúñ]{2,}", text[:m.start()]))
        start = ws[-5].start() if len(ws) >= 5 else 0
        if not _measure_set(_stems(text[start:m.start()])):
            cl = max(text.rfind(c, 0, m.start()) for c in ".;")
            start = max(cl + 1, m.start() - 120, 0)
    nxt = NUM_RE.search(text, m.end() + 1)
    stop = re.search(r"[.;](?:\s|$)", text[m.end():])
    end = min(nxt.start() if nxt else len(text), m.end() + 30, m.end() + stop.start() if stop else len(text))
    return text[start:end].strip()


def _unit_after(text: str, m) -> str:
    """The unit word written right after a number ("1.640 h/FTE" → "h", "142 FTE" → "fte")."""
    if not m:
        return ""
    w = re.match(r"\s*([%€$£x×]|[A-Za-záéíóúñ/]+)", text[m.end():])
    return w.group(1).lower() if w else ""


def _pair_label(label: str, k: int) -> str:
    """'Tasa de error manual / automatizada' with a cell '0,9% / 0,2%': the k-th number is about the k-th
    alternative ('Tasa de error manual', 'Tasa de error automatizada')."""
    parts = [p.strip() for p in label.split("/")]
    if len(parts) != 2:
        return label
    head = parts[0].rsplit(" ", 1)[0] if " " in parts[0] else ""
    return parts[0] if k == 0 else f"{head} {parts[1]}".strip()


SECTION_RE = re.compile(r"\b(fase|phase|stage|zona|zone|wave|ola)\b", re.I)


def _is_kpi(text: str) -> bool:
    """A body element that is only a number and its unit ("26%", "142 FTE", "3,7 años")."""
    return bool(NUM_RE.search(text)) and len(text.split()) <= 3 and len(NUM_RE.sub("", text).strip()) <= 12


def _kpi_labels_before(body: list[str]) -> bool:
    """Whether a slide's KPI labels sit above their numbers ("Plantilla almacén" / "142 FTE") or below
    ("5,6 M€" / "Inversión total"): decided by what precedes the first hero number."""
    for j, t in enumerate(body):
        if _is_kpi(t):
            return j > 0 and not NUM_RE.search(body[j - 1]) and len(body[j - 1].split()) <= 8
    return False


def ingest_deck(path: str | Path) -> dict:
    from pptx import Presentation

    prs = Presentation(str(path))
    slides, fonts, n = [], Counter(), len(prs.slides)
    for i, slide in enumerate(prs.slides, start=1):
        texts = _shape_texts(slide)
        for t in texts:
            fonts.update(t["fonts"])
        # the action title: a title placeholder, else the top-most SENTENCE in a large size (a KPI hero
        # "€13.6bn" is large but is not the headline), else the largest text
        sentences = [t for t in texts if len(t["text"].split()) >= 4 and t["size"] >= 16]
        title = (next((t["text"] for t in texts if t["title"]), None)
                 or (min(sentences, key=lambda t: t["top"])["text"] if sentences else None)
                 or (max(texts, key=lambda t: (t["size"], -t["top"]))["text"] if texts else ""))
        body = [t["text"] for t in texts if t["text"] != title]
        exhibits = []
        for sh in slide.shapes:
            if getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                try:
                    plot = ch.plots[0]
                    exhibits.append({"type": CHART_TYPE.get(str(ch.chart_type).split(".")[-1].split(" ")[0], "column"),
                                     "title": ch.chart_title.text_frame.text if ch.has_title else "",
                                     "categories": [str(c) for c in plot.categories],
                                     "series": [{"name": s.name, "values": [v for v in s.values]} for s in plot.series]})
                except Exception:  # an unusual chart: keep its presence, not its data
                    exhibits.append({"type": "chart", "unreadable": True})
            if getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text for c in r.cells] for r in sh.table.rows]
                exhibits.append({"type": "table", "header": rows[0] if rows else [], "rows": rows[1:]})
        words = sum(len(t["text"].split()) for t in texts)
        labels = " ".join([title] + [b for b in body if len(b.split()) <= 4])  # trackers / section labels ("Executive summary")
        low = labels.lower()
        role = next((r for r, rx in ROLE_RULES if re.search(rx, low)), None)
        if i == 1:
            role = "title"
        elif not role and not exhibits and words <= 12:
            role = "divider"
        role = role or "content"
        numbers = []
        labels_before = _kpi_labels_before(body)
        section = ""
        for k, text in enumerate([title] + body):
            where = "title" if k == 0 else f"body[{k - 1}]"
            if k and SECTION_RE.search(text) and len(text.split()) <= 6:
                section = text  # "Fase 1 · Zona ambiente": the heading of what follows
            pos = 0
            for q in headline_quantities(text):
                m = _locate(text, q["raw"], pos)
                pos = m.end() if m else pos
                ctx = _window(text, m) if m else text[:160]
                if k and _is_kpi(text):  # a hero number: its words are the short label next to it
                    j = k - 1 - 1 if labels_before else k - 1 + 1
                    if 0 <= j < len(body) and not NUM_RE.search(body[j]) and len(body[j].split()) <= 8:
                        ctx = f"{text} {body[j]}"
                occ = len(_occurrences(text[:m.start()], q["raw"])) if m else 0
                numbers.append({"where": where, "raw": q["raw"], "value": q["value"], "kind": q["kind"], "context": ctx,
                                "text": text[:400], "unit_after": _unit_after(text, m), "section": section, "core": _core(q["raw"]), "occ": occ})
        for e_i, ex in enumerate(exhibits):
            for s in ex.get("series") or []:
                for k, v in enumerate(s["values"]):
                    if isinstance(v, (int, float)):
                        cat = (ex.get("categories") or [""] * (k + 1))[k] if k < len(ex.get("categories") or []) else ""
                        numbers.append({"where": f"exhibit[{e_i}].{s['name']}[{cat}]", "raw": f"{v:g}", "value": float(v), "kind": "data",
                                        "context": f"{ex.get('title') or ''} {s['name']} {cat}".strip()})
            for r_i, row in enumerate(ex.get("rows") or []):
                for c_i, cell in enumerate(row[1:], start=1):
                    qs = headline_quantities(cell)
                    hdr = (ex.get("header") or [""] * (c_i + 1))[c_i] if c_i < len(ex.get("header") or []) else ""
                    cpos = 0
                    for k, q in enumerate(qs):
                        label = _pair_label(row[0], k) if len(qs) == 2 and "/" in cell else row[0]
                        cm = _locate(cell, q["raw"], cpos)
                        cpos = cm.end() if cm else cpos
                        numbers.append({"where": f"exhibit[{e_i}].rows[{r_i}][{c_i}]", "raw": q["raw"], "value": q["value"], "kind": q["kind"],
                                        "context": f"{label} {hdr}".strip(), "text": cell, "unit_after": _unit_after(cell, cm),
                                        "core": _core(q["raw"]), "occ": len(_occurrences(cell[:cm.start()], q["raw"])) if cm else 0})
        slides.append({"n": i, "role": role, "layout": slide.slide_layout.name, "headline": title, "body": body, "exhibits": exhibits,
                       "numbers": numbers, "words": words, "is_last": i == n})
    return {"source": Path(path).name, "slides": slides,
            "conventions": {"fonts": [f for f, _ in fonts.most_common(4)], "slide_count": n,
                            "layouts": Counter(s["layout"] for s in slides).most_common(8)}}


def _waterfall_steps(ex: dict) -> list[dict]:
    """A waterfall drawn as stacked columns (an invisible Base + visible Total / Increase / Decrease
    series, as MBBslides and most consultants draw them) back to its steps."""
    ser = {x["name"]: [float(v or 0) for v in x["values"]] for x in ex["series"]}
    steps = []
    for k, cat in enumerate(ex["categories"]):
        tot = sum(abs(ser[n][k]) for n in ser if n.startswith("Total"))
        up = sum(abs(ser[n][k]) for n in ser if n.startswith("Increase"))
        down = sum(abs(ser[n][k]) for n in ser if n.startswith("Decrease"))
        if tot:
            neg = any(ser[n][k] < 0 for n in ser if n.startswith("Total"))
            steps.append({"label": cat, "value": -tot if neg else tot, "type": "total"})
        else:
            steps.append({"label": cat, "value": up - down})
    return steps


def to_spec(inv: dict, title: str = "") -> dict:
    """A starting deck.json that keeps the old storyline, roles and exhibits (rebuilt as native,
    editable visuals). Every number in it is still the OLD number until `update_plan` confirms it."""
    slides = []
    for s in inv["slides"]:
        sid = f"s{s['n']:02d}"
        if s["role"] == "title":
            slides.append({"id": sid, "kind": "cover", "title": s["headline"], "subtitle": " ".join(s["body"][:1])})
            continue
        if s["role"] == "divider":
            slides.append({"id": sid, "kind": "divider", "title": s["headline"]})
            continue
        sl = {"id": sid, "kind": "exec_summary" if s["role"] == "exec_summary" else "content", "headline": s["headline"],
              "purpose": f"(from the old deck, slide {s['n']}: {s['role']})", "_old_slide": s["n"]}
        ex = next((e for e in s["exhibits"] if not e.get("unreadable")), None)
        if ex and ex["type"] == "table":
            sl["visual"] = {"type": "table", "columns": [{"label": h} for h in ex["header"]], "rows": ex["rows"]}
        elif ex and {x["name"] for x in ex["series"]} >= {"Base"} and any(x["name"].startswith(("Increase", "Decrease", "Total")) for x in ex["series"]):
            sl["visual"] = {"type": "waterfall", "title": ex.get("title") or "", "data": {"steps": _waterfall_steps(ex)}}
        elif ex:
            sl["visual"] = {"type": ex["type"], "title": ex.get("title") or "", "data": {"categories": ex["categories"], "series": ex["series"]}}
        elif s["body"]:
            sl["commentary"] = {"points": s["body"][:5]}
        slides.append(sl)
    return {"meta": {"title": title or (inv["slides"][0]["headline"] if inv["slides"] else ""), "from_deck": inv["source"]},
            "storyline": {"governing_thought": next((s["headline"] for s in inv["slides"] if s["role"] == "exec_summary"), "")}, "slides": slides}


UNIT_TEXT = {"EUR": "€", "EUR_K": "k€", "EUR_M": "M€", "EUR_BN": "bn€", "USD": "$", "USD_K": "k$", "USD_M": "M$", "USD_BN": "bn$",
             "GBP": "£", "GBP_K": "k£", "GBP_M": "M£", "PCT": "%", "PP": "pp", "BPS": "bps", "PLAIN_K": "k", "PLAIN_M": "M"}


# measure stems (5 letters, no accents) and their synonyms: the quantity a number is about
MEASURE_STEMS = {"inver": "inver", "capex": "inver", "ahorr": "ahorr", "savin": "ahorr", "produ": "produ", "veces": "produ", "error": "error",
                 "plant": "plant", "fte": "plant", "ftes": "plant", "linea": "linea", "lines": "linea", "volum": "linea", "deman": "linea",
                 "payba": "payba", "tir": "tir", "irr": "tir", "mante": "mante", "licen": "mante", "creci": "creci", "varia": "creci",
                 "coste": "coste", "cost": "coste", "costs": "coste", "caja": "caja", "cash": "caja", "merma": "merma", "capac": "capac",
                 "horas": "horas", "hours": "horas", "ocupa": "ocupa", "preci": "preci", "price": "preci", "ventas": "venta", "venta": "venta",
                 "ingre": "venta", "reven": "venta", "ebitd": "ebitd", "marge": "marge", "margi": "marge"}
# words that make a figure a restatement of a plan, an offer or the old deck, not an observation
PLAN_RE = re.compile(r"\b(presupuest\w*|budget\w*|business case|previst\w*|previsi\w*|aprobad\w*|approved|garant\w*|guarantee\w*|ofert\w*|"
                     r"offer\w*|anterior|deck|objetivo|target|plan(?:ned)?|forecast)\b", re.I)
CODE_COL_RE = re.compile(r"\b(asiento|n[ºo°]|num|id|c[oó]digo|code|cuenta|account|factura|invoice|pedido|order|ref)\b", re.I)
NON_FIGURE_UNITS = {"°c", "ºc", "niveles", "levels", "ubicaciones", "puestos", "locations"}


def _plain(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").replace("_", " ")


def _stems(t: str) -> set[str]:
    from .conflicts import STOP
    out = set()
    if re.search(r"(por hora|per hour|/\s*h(?:ora)?\b|lineas por hora|lines per hour)", _plain(t)):
        out.add("produ")
    for w in re.findall(r"[a-zñ]{3,}", _plain(t)):
        if w in STOP or w in {"con", "mas", "than", "with", "from", "desde", "hasta", "por", "valor", "value", "importe", "total"}:
            continue
        st = w[:5]
        out.add(MEASURE_STEMS.get(st, MEASURE_STEMS.get(w, st)))
    return out


def _measure_set(stems: set[str]) -> set[str]:
    return stems & set(MEASURE_STEMS.values())


# the most specific measure decides: "capacidad de 4,6 M de líneas" is about capacity, not about lines
MEASURE_TIER = {**dict.fromkeys(("capac", "payba", "tir", "merma", "ocupa", "caja", "error", "mante", "produ", "creci", "preci", "horas"), 1),
                **dict.fromkeys(("ahorr", "inver", "coste", "ebitd", "marge", "venta"), 2), **dict.fromkeys(("linea", "plant"), 3)}


def _key_measures(ms: set[str]) -> set[str]:
    if not ms:
        return ms
    top = min(MEASURE_TIER.get(m, 3) for m in ms)
    return {m for m in ms if MEASURE_TIER.get(m, 3) == top}


MONTH_RE = re.compile(r"\b(?:19|20)\d\d-(?:0[1-9]|1[0-2])\b|\b(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|jan|apr|aug|dec)\w*[-\s]\d{2,4}\b", re.I)


def _quals(t: str) -> dict:
    t = _plain(t)
    return {"phase": set(re.findall(r"\b(?:fase|phase|stage)\s*(\d)", t)),
            "year": {y[-4:] for y in re.findall(r"\b(?:fy)?((?:19|20)\d\d)\b", t)},
            "zone": set(re.findall(r"\b(frio|ambiente|cold|ambient)\b", t))}


def _clash(qa: dict, qb: dict) -> bool:
    """Both sides name a phase / year / zone and they have none in common."""
    return any(qa[k] and qb[k] and not (qa[k] & qb[k]) for k in qa)


def _cand_kind(f: dict, v: dict, text: str) -> str:
    u = str(v.get("unit") or "").upper()
    cur = u.split("_")[0]
    if re.search(r"(veces|times|ratio)", str(v.get("column") or ""), re.I) or re.search(r"\d\s*(x|veces|times)\b", text, re.I):
        return "x"
    if cur in ("EUR", "USD", "GBP"):
        return "money"
    if u in ("PCT", "PP", "BPS"):
        return "pct"
    if u in ("YEARS", "MONTHS", "WEEKS", "DAYS", "HOURS", "MINUTES"):
        return "duration"
    return "plain"


def _candidates(facts: list[dict], exclude_files: set[str]) -> list[dict]:
    """Every value of the new fact model with the words that say what it is about."""
    from .conflicts import _local, _num_pos

    out = []
    for f in facts:
        src = f.get("source") or {}
        file = str(src.get("file") or "")
        if f.get("fact_type") in ("derived_change", "assumption") or Path(file).name in exclude_files:
            continue
        for v in f.get("values") or []:
            if f.get("fact_type") == "table_value":
                if CODE_COL_RE.search(str(v.get("column") or "")):
                    continue  # a ledger entry number, an invoice id: not a quantity
                text = f"{v.get('label') or ''} — {v.get('column') or ''}"
            else:
                claim = f.get("claim", "")
                m = _num_pos(claim, v["value"])
                if m is None or re.search(r"[A-Za-z0-9]-$", claim[max(0, m.start() - 2):m.start()]) or re.match(r"-[A-Za-z0-9]", claim[m.end():]):
                    continue  # part of a code ("K-ES-2025-118", "CO-01")
                text = _local(claim, v["value"])
                if text is None:
                    continue  # a limit or a target, not an observation
            unit = str(v.get("unit") or "").upper()
            scale = {"K": 1e3, "M": 1e6, "BN": 1e9}.get(unit.partition("_")[2], 1.0)
            stems = _stems(text)
            measures = _measure_set(stems)
            if f.get("fact_type") == "table_value" and _measure_set(_stems(str(v.get("column") or ""))):
                measures = _measure_set(_stems(str(v.get("column") or "")))  # "payback_anios", "productividad_veces": the column says what the value is
            quals, fq = _quals(f"{text} {v.get('period') or ''}"), _quals(Path(file).stem)
            quals = {k: quals[k] or fq[k] for k in quals}  # the file name ("ahorro_fase1.csv") only when the row says nothing
            out.append({"fact": f["id"], "value": float(v["value"]), "base": float(v["value"]) * scale, "unit": unit, "kind": _cand_kind(f, v, text),
                        "period": str(v.get("period") or ""), "stems": stems, "measures": measures, "text": text, "quals": quals,
                        "month": bool(MONTH_RE.search(text)), "words": set(re.findall(r"[a-zñ]{4,}", _plain(text))),
                        "plan": bool(PLAN_RE.search(_plain(text)) or PLAN_RE.search(_plain(Path(file).stem).replace(" ", "_").replace("_", " "))),
                        "analysis": file.startswith("analysis/") or "/analysis/" in file or f.get("fact_type") == "computed"})
    return out


def _non_figure(q: dict, slide_n: int) -> str | None:
    """Why an old 'number' is not a figure to update: a page number, a code, a phase index, a spec."""
    text, raw = q.get("text") or q.get("context") or "", q["raw"]
    if text.strip() == raw.strip() and q["kind"] == "plain" and q["value"] == slide_n:
        return "page number"
    m = _locate(text, raw, 0)
    if m:
        before, after = text[max(0, m.start() - 8):m.start()], text[m.end():m.end() + 2]
        if re.search(r"[A-Za-z0-9]-$", before) or re.match(r"-[A-Za-z0-9]", after) or re.search(r"\b(rev|ref|n[ºo°])\.?\s*$", before, re.I):
            return "code"
        if q["kind"] == "plain" and re.search(r"\b(fase|phase|stage|step|paso)\s*$", before, re.I):
            return "phase index"
    if (q.get("unit_after") or "") in NON_FIGURE_UNITS or re.match(r"\s*-\s*\d+\s*°", text[m.end():] if m else ""):
        return "specification"
    return None


def _kind_ok(q: dict, c: dict) -> bool:
    k, ua = q["kind"], q.get("unit_after") or ""
    if k == "money":
        return c["kind"] == "money"
    if k == "pct":
        return c["kind"] == "pct"
    if k == "x":
        return c["kind"] in ("x", "plain")
    if ua in ("h", "horas", "hours", "h/fte"):
        return c["kind"] in ("duration", "plain")
    if c["kind"] == "pct":  # a unit-less number is a share only under a "%" label, not next to "+6%/año"
        return bool(re.search(r"\(%\)|(?<![\d+\-.,])\s%|^%|\bpct\b|porcentaje|percent", q.get("context") or ""))
    if c["kind"] == "money":  # a bare number counts as money only under a money label
        return bool(re.search(r"(€|\$|£|k€|m€|eur|ahorr|inversi|capex|caja|mantenim|coste|cost|saving)", _plain(q.get("context") or ""))) and \
            ua not in ("fte", "ftes", "lineas", "líneas", "lines", "años", "years", "x", "%")
    if c["kind"] == "x":
        return bool(re.search(r"(veces|times|\bx\b|multiplica)", _plain(q.get("context") or "")))
    return c["kind"] in ("plain", "duration")


def _close_vals(q: dict, c: dict) -> bool:
    a = abs(q["value"])
    if q["kind"] == "money" or (c["kind"] == "money" and q["kind"] in ("plain", "data")):
        bs = [abs(c["base"])] if q["kind"] == "money" else [abs(c["base"]), abs(c["value"]), abs(c["base"]) / 1e3, abs(c["base"]) / 1e6]
    elif q["kind"] in ("plain", "data"):
        bs = [abs(c["value"]) * k for k in (1, 1e3, 1e-3, 1e6, 1e-6)]
    else:
        bs = [abs(c["value"])]
    return any(abs(a - b) <= 0.015 * max(a, b, 1e-9) for b in bs)


def _same_magnitude(q: dict, c: dict) -> bool:
    """Within 3x of each other (at some scale for unit-less numbers): an update, not another quantity."""
    a = abs(q["value"])
    if q["kind"] == "money":
        bs = [abs(c["base"])]
    elif c["kind"] == "money":
        bs = [abs(c["base"]), abs(c["value"]), abs(c["base"]) / 1e3, abs(c["base"]) / 1e6]
    else:
        bs = [abs(c["value"]) * k for k in (1, 1e3, 1e-3, 1e6, 1e-6)]
    return any(b and a and max(a, b) / min(a, b) <= 3 for b in bs)


def _match(q: dict, slide: dict, cands: list[dict]) -> tuple[str, list[dict], dict | None]:
    from .conflicts import _opposed

    ctx = q.get("context") or ""
    st = _stems(ctx)
    ms = _measure_set(st)
    if not ms and q["kind"] == "data":
        ms = _measure_set(_stems(slide.get("headline") or ""))  # a bare chart point: its slide says what it measures
        st = st | ms
    if not ms:
        return "untraced", [], None
    key = _key_measures(ms)
    words = set(re.findall(r"[a-zñ]{4,}", _plain(ctx)))
    qq = _quals(ctx)
    sq = _quals(q.get("section") or "")
    qq = {k: qq[k] or sq[k] for k in qq}
    scored = []
    for c in cands:
        if not (key & c["measures"]) or not _kind_ok(q, c) or _clash(qq, c["quals"]) or _opposed(words, c["words"]) or not _same_magnitude(q, c):
            continue
        sc = len(st & c["stems"]) + sum(1 for k in ("year", "phase", "zone") if qq[k] and qq[k] & c["quals"][k])
        part = sum(1 for k in ("phase", "zone") if c["quals"][k] and not qq[k])  # a part (one zone) of an unqualified whole
        if sc >= (1 if q["kind"] == "x" else 2):
            scored.append((sc - 0.5 * part, c))
    if not scored:
        return "untraced", [], None
    obs = [(sc, c) for sc, c in scored if not c["plan"]]
    pool = obs or scored
    top = max(sc for sc, _ in pool)
    group = [c for sc, c in pool if sc == top]
    near = [(sc, c) for sc, c in pool if c["analysis"] and sc >= top - 1]
    if near:  # the analysis outputs are the current numbers of record, unless clearly about something else
        best = max(sc for sc, _ in near)
        group = [c for sc, c in near if sc == best]
    primary = max(group, key=lambda c: (not c["month"], c["period"], c["analysis"]))  # an aggregate over a monthly slice, then the latest
    if _close_vals(q, primary):
        if primary["plan"]:
            return "untraced", group, None  # only a restatement of the old plan repeats it: not a confirmation
        return "current", group, primary
    return "outdated", group, primary


def update_plan(inv: dict, facts: list[dict]) -> dict:
    """Every number of the old deck against the new fact model. A number is matched on what it is about
    (its own words: measure, phase, zone, year; its unit), never on its value alone:
    - CURRENT: the best-matching new fact (analysis outputs and the latest period first) holds it;
    - OUTDATED: that fact holds another value (the proposed new value);
    - UNTRACED: no new fact speaks to it, or only a restatement of the old plan does (a budget, an offer);
    - IGNORED: not a figure (page number, document code, phase index, specification)."""
    cands = _candidates(facts, {Path(str(inv.get("source") or "")).name})
    alltext = " ".join(q.get("text") or "" for s in inv["slides"] for q in s["numbers"])
    hint = "," if len(re.findall(r"\d,\d{1,2}(?!\d)", alltext)) > len(re.findall(r"\d\.\d{1,2}(?!\d)", alltext)) else "."  # the deck's decimal mark
    out = []
    for s in inv["slides"]:
        items = []
        for q in s["numbers"]:
            why = _non_figure(q, s["n"])
            if why:
                items.append({**q, "status": "ignored", "why": why})
                continue
            status, group, primary = _match(q, s, cands)
            if status == "current":
                items.append({**q, "status": "current", "facts": sorted({c["fact"] for c in group})[:3]})
            elif status == "outdated":
                u = UNIT_TEXT.get(primary["unit"], "")
                newv = f"{primary['value']:g}{u}" if u == "%" else (f"{primary['value']:g} {u}" if u else f"{primary['value']:g}")
                items.append({**q, "status": "outdated", "new_value": newv, "fact": primary["fact"], "new_claim": primary["text"][:140],
                              "new_display": _new_display({**q, "_hint": hint}, primary)})
            else:
                items.append({**q, "status": "untraced"})
        st = Counter(i["status"] for i in items)
        live = len(items) - st["ignored"]
        action = "keep" if not live or st["current"] == live else ("update" if st["outdated"] else "review")
        out.append({"slide": s["n"], "role": s["role"], "headline": s["headline"], "action": action, "counts": dict(st), "numbers": items})
    tot = Counter(i["status"] for s in out for i in s["numbers"])
    return {"source": inv["source"], "slides": out, "totals": dict(tot),
            "rule": "an old number is matched on its own words (measure, phase, zone, year) and unit, never on its value alone; "
                    "it is reused only when the best-matching new fact holds it; restatements of the old plan never confirm it"}


def plan_markdown(plan: dict) -> str:
    L = [f"# Update plan — {plan['source']}", "", f"Numbers in the old deck: {plan['totals']}", "", "| slide | role | action | current | outdated | untraced | headline |",
         "|---|---|---|---|---|---|---|"]
    for s in plan["slides"]:
        c = s["counts"]
        L.append(f"| {s['slide']} | {s['role']} | **{s['action']}** | {c.get('current', 0)} | {c.get('outdated', 0)} | {c.get('untraced', 0)} | {s['headline'][:70]} |")
    L += ["", "## Outdated numbers", ""]
    for s in plan["slides"]:
        for q in s["numbers"]:
            if q["status"] == "outdated":
                L.append(f"- slide {s['slide']} {q['where']}: **{q['raw']} → {q['new_value']}** ({q['fact']}: {q['new_claim']})")
    return "\n".join(L) + "\n"


def write_ingest(pptx: str | Path, work: str | Path) -> dict:
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    inv = ingest_deck(pptx)
    (work / "old_deck.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    (work / "old_deck_spec.json").write_text(json.dumps(to_spec(inv), indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    ghost = ["# Old deck — the argument from its headlines", ""] + [f"{s['n']}. [{s['role']}] {s['headline']}" for s in inv["slides"]]
    (work / "old_ghost.md").write_text("\n".join(ghost) + "\n", encoding="utf-8", newline="\n")
    return inv


def write_plan(work: str | Path) -> dict:
    work = Path(work)
    inv = json.loads((work / "old_deck.json").read_text(encoding="utf-8"))
    facts = json.loads((work / "facts.json").read_text(encoding="utf-8")).get("facts", [])
    plan = update_plan(inv, facts)
    (work / "update_plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (work / "update_plan.md").write_text(plan_markdown(plan), encoding="utf-8", newline="\n")
    return plan
