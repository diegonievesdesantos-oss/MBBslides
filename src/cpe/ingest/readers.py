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
    # v1.7: a number starts at a digit boundary and takes all its digits ("2026" was read as "202" + "6")
    r"(?P<raw>(?:[€$£]\s?)?[-−+]?(?<![\d.,])\d+(?:[,.\s]\d{3}(?!\d))*(?:[.,]\d+)?(?:\s?(?:%|pp|bps|x|bn|billion|mn|million|m|k|thousand|€|eur|usd)(?![a-z]))?)",
    re.IGNORECASE,
)
SENT_RE = re.compile(r"(?<=[.!?;])\s+")


UNIT_OK = re.compile(r"(€|\$|£|eur|usd|gbp)?(m|mn|bn|k|million|billion|thousand)?(€|\$|£|eur|usd|gbp)?|%|pp|bps|x")


def _num(raw, dot_decimal: bool = False) -> tuple[float | None, str]:
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):  # a typed cell (xlsx): already a number
        return float(raw), ""
    raw = str(raw)
    unit = re.sub(r"[\d\s.,+\-−]", "", raw).lower()
    if not UNIT_OK.fullmatch(unit):
        return None, unit  # "Q1 2024", "FY25", "P01": a label, not a number
    core = re.sub(r"[^\d.,\-−+]", "", raw).replace("−", "-")
    if core.count(",") and core.count("."):
        core = core.replace(",", "") if core.rfind(".") > core.rfind(",") else core.replace(".", "").replace(",", ".")
    elif core.count(",") == 1 and len(core.split(",")[1]) != 3:
        core = core.replace(",", ".")
    elif not dot_decimal and not core.count(",") and re.fullmatch(r"[-+]?\d{1,3}(?:\.\d{3})+", core):
        core = core.replace(".", "")  # Spanish thousands: "30.000", "1.250.000" (v1.7; a 3-decimal figure is rare in prose)
    else:
        core = core.replace(",", "")
    try:
        return float(core), unit
    except ValueError:
        return None, unit


def extract_facts(text: str, source: str, loc: str) -> list[dict]:
    out = []
    for sent in SENT_RE.split(text):
        for m in FACT_RE.finditer(sent):
            raw = m.group("raw").strip()
            v, unit = _num(raw)
            if v is None:
                continue
            if not unit and float(v).is_integer() and 1900 <= v <= 2100:
                continue  # a year, not a fact
            if not unit and abs(v) < 10 and len(raw) <= 2:
                continue  # list numbering, small counts
            out.append({"source": source, "loc": loc, "value": v, "unit": unit, "raw": raw, "context": sent.strip()[:300]})
    return out


DOT_DECIMAL = re.compile(r"[-+]?\d*\.(?:\d{1,2}|\d{4,})|[-+]?0\.\d+")


def _table(header, rows, source, loc, dot_decimal: bool = False) -> dict:
    ncols = max([len(header)] + [len(r) for r in rows]) if (header or rows) else 0
    numeric, dot = [], set()
    for j in range(ncols):
        vals = [r[j] for r in rows if j < len(r) and str(r[j]).strip() != ""]
        if vals and all(_num(v)[0] is not None for v in vals):
            numeric.append(j)
            # one column, one convention: "1.444" next to "0.05" or "16.73" is a decimal, not 1,444
            if dot_decimal or any(isinstance(v, str) and DOT_DECIMAL.fullmatch(v.strip()) for v in vals):
                dot.add(j)
    conv = []
    for r in rows:
        conv.append([(_num(c, j in dot)[0] if j in numeric else c) for j, c in enumerate(r)])
    return {"source": source, "loc": loc, "header": list(header), "rows": conv, "numeric_columns": numeric}


def read_text(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="replace")
    blocks, facts, tables = [], [], []
    para: list[str] = []
    md_table: list[list[str]] = []
    ln_no = 0

    def flush():
        if para:
            t = " ".join(para).strip()
            blocks.append({"source": path.name, "loc": f"line {ln_no}", "kind": "text", "text": t})
            facts.extend(extract_facts(t, path.name, f"line {ln_no}"))
            para.clear()

    for ln_no, line in enumerate(txt.splitlines(), start=1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                md_table.append(cells)
            continue
        if md_table:
            tables.append(_table(md_table[0], md_table[1:], path.name, f"line {ln_no}"))
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
        tables.append(_table(md_table[0], md_table[1:], path.name, "end"))
    return {"blocks": blocks, "facts": facts, "tables": tables}


def read_csv(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(raw[:2048], delimiters=",;\t|") if raw.strip() else csv.excel
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
    return {"blocks": blocks, "facts": facts, "tables": tables}


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
    return {"blocks": blocks, "facts": facts, "tables": tables}


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
    data = json.loads(path.read_text())
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
