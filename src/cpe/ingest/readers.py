"""Content ingestion: any source → a content inventory the agent can reason on.

Supported: .txt .md .csv .tsv .xlsx .json .pdf .docx .pptx
The inventory is deliberately simple and traceable:
    {"sources": [...],
     "blocks":  [{"source", "loc", "kind": "heading|text", "text"}],
     "tables":  [{"source", "loc", "header": [...], "rows": [[...]], "numeric_columns": [...]}],
     "facts":   [{"source", "loc", "value", "unit", "raw", "context"}]}
Facts are numbers with their sentence, so every number used in a headline can
be traced back to where it came from (evidence register).
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

FACT_RE = re.compile(
    # v1.7: a number starts at a digit boundary and takes all its digits ("2026" was read as "202" + "6");
    # v1.8: "35-39" is a range (no sign after a digit); "más" is not "m" (accented letters end a word too)
    r"(?P<raw>(?:[€$£]\s?)?(?<![\d.,])[-−+]?(?<![\d.,])\d+(?:[,.\s]\d{3}(?!\d))*(?:[.,]\d+)?"
    r"(?:\s?(?:%|pp|bps|x|bn|billion|mn|million|m|k|thousand|€|eur|usd)(?![a-záéíóúñü²³]))?)",
    re.IGNORECASE,
)
MONTHS = ("enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|"
          "january|february|march|april|may|june|july|august|september|october|november|december")
DATE_RE = re.compile(
    rf"\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b|\b\d{{1,2}}\s+de\s+(?:{MONTHS})\b|\b(?:{MONTHS})\s+\d{{1,2}}\b|\b\d{{1,2}}\s+(?:{MONTHS})\b"
    r"|\b(?:19|20)\d{2}-\d{2}(?:-\d{2})?\b|\b(?:19|20)\d{2}\s?[-–/]\s?(?:19|20)?\d{2}\b|\b\d{1,2}:\d{2}\b"
    # v1.9 (DEBT_V18 U4): ISO week references are periods — "semanas 31 a 40", "semana 37", "S37", "week 12", "W12", "KW 12"
    r"|\b(?:semanas?|sem\.|weeks?|wk|cw|kw)\s*\d{1,2}(?:\s*(?:a|al|y|-|–|to|and|hasta)\s*\d{1,2})?\b|\b[SW]\d{1,2}\b", re.IGNORECASE)


def mask_dates(text: str) -> str:
    """Dates, periods and times are not quantities: '22 de septiembre', '2/12/2025', '2025-26',
    '2025-01_2026-08', '10:30' are blanked (same length) before numbers are read."""
    return DATE_RE.sub(lambda m: " " * len(m.group(0)), text or "")
SENT_RE = re.compile(r"(?<=[.!?;])\s+")


UNIT_OK = re.compile(r"(€|\$|£|eur|usd|gbp)?(m|mn|bn|k|million|billion|thousand)?(€|\$|£|eur|usd|gbp)?|%|pp|bps|x")


def _num(raw, dot_decimal: bool = False, decimal_comma: bool = False) -> tuple[float | None, str]:
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):  # a typed cell (xlsx): already a number
        return float(raw), ""
    raw = re.sub(r"^[≈~±]\s*", "", re.sub(r"\*\*|__", "", str(raw)).strip())  # "**1,941**", "**≈ 5.230**"
    unit = re.sub(r"[\d\s.,+\-−]", "", raw).lower()
    if not UNIT_OK.fullmatch(unit):
        return None, unit  # "Q1 2024", "FY25", "P01": a label, not a number
    core = re.sub(r"[^\d.,\-−+]", "", raw).replace("−", "-")
    if decimal_comma:  # a document written with decimal commas: "1,829" is 1.829, "75.846" is 75846
        core = core.replace(".", "").replace(",", ".")
        try:
            return float(core), unit
        except ValueError:
            return None, unit
    if core.count(",") and core.count("."):
        core = core.replace(",", "") if core.rfind(".") > core.rfind(",") else core.replace(".", "").replace(",", ".")
    elif core.count(",") == 1 and len(core.split(",")[1]) != 3:
        core = core.replace(",", ".")
    elif core.count(",") == 1 and re.fullmatch(r"[-+]?0,\d+", core):
        core = core.replace(",", ".")  # "0,048": a decimal
    elif not dot_decimal and not core.count(",") and not re.match(r"[-+]?0\.", core) and re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+", core):
        core = core.replace(".", "")  # Spanish thousands: "30.000", "1.250.000" (v1.7; a 3-decimal figure is rare in prose)
    else:
        core = core.replace(",", "")
    try:
        return float(core), unit
    except ValueError:
        return None, unit


def extract_facts(text: str, source: str, loc: str, decimal_comma: bool = False) -> list[dict]:
    out = []
    for sent in SENT_RE.split(text):
        for m in FACT_RE.finditer(mask_dates(sent)):
            raw = m.group("raw").strip()
            v, unit = _num(raw, decimal_comma=decimal_comma)
            if v is None:
                continue
            if not unit and float(v).is_integer() and 1900 <= v <= 2100:
                continue  # a year, not a fact
            if not unit and abs(v) < 10 and len(raw) <= 2:
                continue  # list numbering, small counts
            out.append({"source": source, "loc": loc, "value": v, "unit": unit, "raw": raw, "context": sent.strip()[:300]})
    return out


DOT_DECIMAL = re.compile(r"[-+]?\d*\.(?:\d{1,2}|\d{4,})|[-+]?0\.\d+")


ARROW = re.compile(r"^\s*(.+?)\s*(?:→|->)\s*(.+?)\s*$")


def _split_arrows(header: list, rows: list) -> tuple[list, list]:
    """A column of 'before → after' cells ("81,8 % → 74,5 %") becomes two columns, "(from)" and "(to)"."""
    ncols = max([len(header)] + [len(r) for r in rows]) if (header or rows) else 0
    cols = []
    for j in range(ncols):
        vals = [str(r[j]) for r in rows if j < len(r) and str(r[j]).strip()]
        cols.append(bool(vals) and sum(bool(ARROW.match(v)) for v in vals) >= max(1, 0.6 * len(vals)))
    if not any(cols):
        return header, rows
    h2, r2 = [], [[] for _ in rows]
    for j in range(ncols):
        name = str(header[j]) if j < len(header) else ""
        if cols[j]:
            base = re.sub(r"\s*\S+\s*(?:→|->)\s*\S+\s*$", "", name).strip() or name
            fr, to = (re.findall(r"(\S+)\s*(?:→|->)\s*(\S+)", name) or [("from", "to")])[0]
            h2 += [f"{base} ({fr})", f"{base} ({to})"]
            for i, r in enumerate(rows):
                m = ARROW.match(str(r[j])) if j < len(r) else None
                r2[i] += [m.group(1), m.group(2)] if m else ["", ""]
        else:
            h2.append(name)
            for i, r in enumerate(rows):
                r2[i].append(r[j] if j < len(r) else "")
    return h2, r2


def _two_level_header(header: list, rows: list) -> tuple[list, list, bool]:
    """v1.8: a header on two rows — a group row with merged (blank) cells over a row of sub-labels:
    | | 2024 | | 2025 | |  /  | Line | Actual | Budget | Actual | Budget |  →  "2024 · Actual", …"""
    if not rows or len(rows) < 2:
        return header, rows, False
    h, sub = [str(x or "").strip() for x in header], [str(x or "").strip() for x in rows[0]]
    blanks = sum(1 for x in h[1:] if not x)
    sub_text = [x for x in sub[1:] if x]
    if not blanks or len(sub_text) < 2 or any(_num(x)[0] is not None for x in sub_text):
        return header, rows, False
    filled, last = [], ""
    for x in h:
        last = x or last
        filled.append(last)
    merged = [(f"{a} · {b}" if a and b and a != b else (b or a)) for a, b in zip(filled + [""] * (len(sub) - len(filled)), sub)]
    if h and h[0] and not sub[0]:
        merged[0] = h[0]
    return merged, rows[1:], True


TOTAL_RE = re.compile(r"^\s*(total|subtotal|sub-total|grand total|suma|total general|totales)\b", re.I)


def _table(header, rows, source, loc, dot_decimal: bool = False, decimal_comma: bool = False) -> dict:
    header, rows, two_level = _two_level_header(list(header), [list(r) for r in rows])
    header, rows = _split_arrows(list(header), [list(r) for r in rows])
    ncols = max([len(header)] + [len(r) for r in rows]) if (header or rows) else 0
    numeric, dot = [], set()
    for j in range(ncols):
        vals = [r[j] for r in rows if j < len(r) and str(r[j]).strip() not in ("", "n/a", "–", "-", "—")]
        ok = [v for v in vals if _num(v, decimal_comma=decimal_comma)[0] is not None]
        # a value column may carry a stray label cell ("Total", "4-6 sem"): numeric if most cells are numbers
        if vals and len(ok) >= max(1, 0.7 * len(vals)) and j > 0 or (vals and len(ok) == len(vals)):
            numeric.append(j)
            # one column, one convention: "1.444" next to "0.05" or "16.73" is a decimal, not 1,444
            if dot_decimal or any(isinstance(v, str) and DOT_DECIMAL.fullmatch(v.strip()) for v in vals):
                dot.add(j)
    conv, units = [], []
    for r in rows:
        parsed = [(_num(c, j in dot, decimal_comma) if j in numeric else (c, "")) for j, c in enumerate(r)]
        conv.append([v for v, _ in parsed])
        units.append([u for _, u in parsed])  # "1,6%", "140.000 €": the unit written in the cell itself
    kinds = ["total" if r and TOTAL_RE.match(str(r[0] if not str(r[0]).strip() == "" else (r[1] if len(r) > 1 else ""))) else
             ("subtotal" if r and re.match(r"^\s*sub", str(r[0]), re.I) else "row") for r in rows]
    return {"source": source, "loc": loc, "header": list(header), "rows": conv, "numeric_columns": numeric, "cell_units": units,
            "decimal_comma": decimal_comma, "row_kinds": kinds, "two_level_header": two_level}


def decimal_comma_document(txt: str) -> bool:
    """A document written with decimal commas (Spanish, most of Europe): more "80,4"-style decimals
    than "80.4"-style ones, and no "1,250,000"-style thousands."""
    comma = len(re.findall(r"(?<![\d.,])\d+,\d{1,2}(?![\d,])", txt))
    dot = len(re.findall(r"(?<![\d.,])\d+\.\d{1,2}(?![\d.])", txt))
    return comma > dot and not re.search(r"\d,\d{3},\d{3}", txt)


def read_text(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    dc = decimal_comma_document(txt)
    blocks, facts, tables = [], [], []
    para: list[str] = []
    md_table: list[list[str]] = []
    md_start = 0
    ln_no = 0

    def flush():
        if para:
            t = " ".join(para).strip()
            blocks.append({"source": path.name, "loc": f"line {ln_no}", "kind": "text", "text": t})
            facts.extend(extract_facts(t, path.name, f"line {ln_no}", decimal_comma=dc))
            para.clear()

    for ln_no, line in enumerate(txt.splitlines(), start=1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not md_table:
                md_start = ln_no
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                md_table.append(cells)
            continue
        if md_table:
            tables.append(_table(md_table[0], md_table[1:], path.name, f"line {md_start}", decimal_comma=dc))
            md_table = []
        if not s:
            flush()
        elif s.startswith("#"):
            flush()
            blocks.append({"source": path.name, "loc": f"line {ln_no}", "kind": "heading", "text": s.lstrip("#").strip()})
        else:
            para.append(s.lstrip("-*• ").strip() if s[:2] in ("- ", "* ", "• ") else s)
            if s[:2] in ("- ", "* ", "• "):
                flush()
    flush()
    if md_table:
        tables.append(_table(md_table[0], md_table[1:], path.name, f"line {md_start}", decimal_comma=dc))
    return {"blocks": blocks, "facts": facts, "tables": tables}


def sniff_dialect(raw: str):
    """Delimiter from whole lines only (a 22-column file cut at 2048 characters made the sniffer give up);
    falls back to a comma."""
    if not raw.strip():
        return csv.excel
    head = "\n".join(raw.splitlines()[:30])
    try:
        return csv.Sniffer().sniff(head, delimiters=",;\t|")
    except csv.Error:
        first = raw.splitlines()[0]
        best = max(",;\t|", key=first.count)
        d = csv.excel()
        d.delimiter = best if first.count(best) else ","
        return d


def read_csv(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    dialect = sniff_dialect(raw)
    rows = list(csv.reader(io.StringIO(raw), dialect))
    if not rows:
        return {"blocks": [], "facts": [], "tables": []}
    # comma-separated values cannot carry a decimal comma unquoted: a dot is a decimal point
    return {"blocks": [], "facts": [], "tables": [_table(rows[0], rows[1:], path.name, "sheet", dot_decimal=dialect.delimiter == ",")]}


def read_xlsx(path: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    tables, blocks, facts = [], [], []
    for ws in wb.worksheets:
        rows = [[("" if c is None else c) for c in r] for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(str(c).strip() for c in r)]
        # prose in cells (a "Notes" sheet, a comment column) is text: read it as sentences, not as table labels
        for i, r in enumerate(rows, start=1):
            for c in r:
                if isinstance(c, str) and len(c) > 40 and c.count(" ") >= 5:
                    loc = f"sheet {ws.title} row {i}"
                    blocks.append({"source": path.name, "loc": loc, "kind": "text", "text": c.strip()})
                    facts.extend(extract_facts(c.strip(), path.name, loc))
        if rows and not all(sum(1 for c in r if str(c).strip()) == 1 and isinstance(next(c for c in r if str(c).strip()), str) for r in rows):
            tables.append(_table([str(h) for h in rows[0]], rows[1:], path.name, f"sheet {ws.title}"))
    return {"blocks": blocks, "facts": facts, "tables": tables + ooxml_charts(path)}


def read_pdf(path: Path) -> dict:
    import pymupdf

    doc = pymupdf.open(str(path))
    blocks, facts, tables = [], [], []
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text("blocks"):
            t = " ".join(b[4].split())
            if not t:
                continue
            blocks.append({"source": path.name, "loc": f"p.{pno}", "kind": "text", "text": t})
            facts.extend(extract_facts(t, path.name, f"p.{pno}"))
        try:
            for tb in page.find_tables().tables:
                data = tb.extract()
                if data and len(data) > 1:
                    tables.append(_table([str(c or "") for c in data[0]], [[c or "" for c in r] for r in data[1:]], path.name, f"p.{pno}"))
        except Exception:
            pass
    doc.close()
    return {"blocks": blocks, "facts": facts, "tables": tables}


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


C_NS = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def ooxml_charts(path: Path) -> list[dict]:
    """v1.8: the data behind charts embedded in .docx / .xlsx / .pptx. A chart part caches its
    categories and values; an Excel chart may only reference cells, which are then read from the
    workbook. A chart in a source becomes a table: its claim is rebuilt from the numbers, never from a picture."""
    out = []
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        return out
    wb = None

    def resolve(ref: str) -> list:
        nonlocal wb
        if not ref or path.suffix.lower() not in (".xlsx", ".xlsm"):
            return []
        m = re.match(r"^'?(.*?)'?!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", ref)
        if not m:
            return []
        import openpyxl

        wb = wb or openpyxl.load_workbook(path, data_only=True, read_only=False)
        ws = wb[m.group(1)] if m.group(1) in wb.sheetnames else wb.worksheets[0]
        rng = f"{m.group(2)}{m.group(3)}" + (f":{m.group(4)}{m.group(5)}" if m.group(4) else "")
        cells = ws[rng]
        flat = [c for row in (cells if isinstance(cells, tuple) else ((cells,),)) for c in (row if isinstance(row, tuple) else (row,))]
        return [c.value for c in flat]

    def values(el, tag):
        part = el.find(f"{C_NS}{tag}")
        if part is None:
            return []
        pts = [v.text for v in part.iterfind(f".//{C_NS}pt/{C_NS}v")]
        if pts:
            return pts
        f = part.find(f".//{C_NS}f")
        return resolve(f.text if f is not None else "")

    with z:
        for name in sorted(n for n in z.namelist() if re.search(r"/charts/chart\d+\.xml$", n)):
            root = etree.fromstring(z.read(name))
            t_el = root.find(f".//{C_NS}title")
            title = " ".join((x.text or "") for x in t_el.iter(f"{A_NS}t")).strip() if t_el is not None else ""
            series = []
            for ser in root.iter(f"{C_NS}ser"):
                nm = values(ser, "tx")
                nm = str(nm[0]) if nm else f"series {len(series) + 1}"
                series.append((nm, values(ser, "cat"), values(ser, "val")))
            if not series or not any(v for _, _, v in series):
                continue
            cats = max((c for _, c, _ in series), key=len) or [str(k + 1) for k in range(max(len(v) for _, _, v in series))]
            rows = [[c] + [(sv[k] if k < len(sv) else "") for _, _, sv in series] for k, c in enumerate(cats)]
            out.append(_table([title[:80] or "category"] + [n for n, _, _ in series], rows, path.name,
                              f"chart {name.rsplit('/', 1)[-1].removesuffix('.xml')}", dot_decimal=True))
    return out


def read_docx(path: Path) -> dict:
    blocks, facts, tables = [], [], []
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    n = 0
    for el in body:
        n += 1
        if el.tag == f"{W}p":
            t = "".join(x.text or "" for x in el.iter(f"{W}t")).strip()
            if not t:
                continue
            style = el.find(f"{W}pPr/{W}pStyle")
            kind = "heading" if style is not None and "eading" in (style.get(f"{W}val") or "") else "text"
            blocks.append({"source": path.name, "loc": f"para {n}", "kind": kind, "text": t})
            if kind == "text":
                facts.extend(extract_facts(t, path.name, f"para {n}"))
        elif el.tag == f"{W}tbl":
            rows = [["".join(x.text or "" for x in tc.iter(f"{W}t")).strip() for tc in tr.iter(f"{W}tc")] for tr in el.iter(f"{W}tr")]
            if rows:
                tables.append(_table(rows[0], rows[1:], path.name, f"table at {n}"))
    return {"blocks": blocks, "facts": facts, "tables": tables + ooxml_charts(path)}


def read_pptx(path: Path) -> dict:
    from pptx import Presentation

    prs = Presentation(str(path))
    blocks, facts, tables = [], [], []
    for i, slide in enumerate(prs.slides, start=1):
        for sh in slide.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                t = " ".join(sh.text_frame.text.split())
                blocks.append({"source": path.name, "loc": f"slide {i}", "kind": "text", "text": t})
                facts.extend(extract_facts(t, path.name, f"slide {i}"))
            if getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text for c in r.cells] for r in sh.table.rows]
                tables.append(_table(rows[0], rows[1:], path.name, f"slide {i}"))
            if getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                try:
                    cats = list(ch.plots[0].categories)
                    rows = [[c] + [s.values[k] for s in ch.plots[0].series] for k, c in enumerate(cats)]
                    tables.append(_table(["category"] + [s.name for s in ch.plots[0].series], rows, path.name, f"slide {i} chart"))
                except Exception:
                    pass
    return {"blocks": blocks, "facts": facts, "tables": tables}


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks, facts, tables = [], [], []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        header = list(data[0].keys())
        tables.append(_table(header, [[r.get(h, "") for h in header] for r in data], path.name, "root"))
    else:
        txt = json.dumps(data, ensure_ascii=False)
        blocks.append({"source": path.name, "loc": "root", "kind": "text", "text": txt[:5000]})
    return {"blocks": blocks, "facts": facts, "tables": tables}


READERS = {".txt": read_text, ".md": read_text, ".csv": read_csv, ".tsv": read_csv, ".xlsx": read_xlsx, ".xlsm": read_xlsx, ".pdf": read_pdf, ".docx": read_docx, ".pptx": read_pptx, ".json": read_json}


def ingest(paths: list[str | Path]) -> dict:
    inv = {"sources": [], "blocks": [], "facts": [], "tables": []}
    for p in paths:
        path = Path(p)
        reader = READERS.get(path.suffix.lower())
        if reader is None:
            inv["sources"].append({"file": path.name, "status": f"unsupported extension {path.suffix}"})
            continue
        part = reader(path)
        inv["sources"].append({"file": path.name, "status": "ok", "blocks": len(part["blocks"]), "tables": len(part["tables"]), "facts": len(part["facts"])})
        for k in ("blocks", "facts", "tables"):
            inv[k].extend(part[k])
    return inv


def summary_markdown(inv: dict, max_facts: int = 60) -> str:
    L = ["# Content inventory", ""]
    for s in inv["sources"]:
        L.append(f"- `{s['file']}`: {s['status']}" + (f" — {s['blocks']} text blocks, {s['tables']} tables, {s['facts']} facts" if s["status"] == "ok" else ""))
    L += ["", "## Headings", ""]
    L += [f"- {b['text']} ({b['source']} {b['loc']})" for b in inv["blocks"] if b["kind"] == "heading"][:40]
    L += ["", f"## Facts (first {max_facts})", "", "| value | unit | context | where |", "|---|---|---|---|"]
    for f in inv["facts"][:max_facts]:
        ctx = f["context"].replace("|", "/")[:120]
        L.append(f"| {f['value']:g} | {f['unit']} | {ctx} | {f['source']} {f['loc']} |")
    L += ["", "## Tables", ""]
    for t in inv["tables"]:
        L.append(f"- {t['source']} {t['loc']}: {len(t['rows'])} rows × {len(t['header'])} cols — header: {', '.join(map(str, t['header'][:8]))}")
    return "\n".join(L) + "\n"
