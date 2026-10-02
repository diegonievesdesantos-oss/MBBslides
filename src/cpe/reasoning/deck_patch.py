"""Update the original deck in place (v1.9, D1): change only what has to change.

    cpe deck edits work/                     → work/edits.json/.md   one proposed edit per OUTDATED number
                                               of the update plan (old → new, its fact), approved: false
    cpe deck patch old.pptx work/edits.json -o new.pptx [--mark] [--accept-proposed]
                                             → new.pptx + patch_report.json/.md

The original file is opened and saved by python-pptx, so everything not edited stays as it was:
masters, layouts, artwork, animations, notes, every other number. Only APPROVED edits are applied
(`--accept-proposed` applies the proposals as they are, for a dry run). An edit is never guessed:
a number that cannot be found where the plan says (moved, split oddly, already changed) is
reported, not replaced somewhere else.

Edit operations (edits.json → "edits"):
  number         {slide, where, find, replace, occ}   a number in a text, a table cell or a chart point
  replace_text   {slide, find, replace}               a phrase anywhere on the slide (texts and tables)
  set_chart      {slide, exhibit, series, values}     a whole series of a chart
  delete_slide   {slide}
  note           {slide, text}                        appended to the speaker notes
Every applied change is also written to the slide's notes (what changed, from which fact), and
`--mark` highlights changed text in yellow for the reviewer.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def proposed_edits(plan: dict) -> dict:
    """One `number` edit per outdated number with a proposed new value; the rest listed for review."""
    edits, review = [], []
    for s in plan["slides"]:
        for q in s["numbers"]:
            if q["status"] == "outdated" and q.get("new_display") and q.get("core"):
                edits.append({"op": "number", "slide": s["slide"], "where": q["where"], "find": q["core"], "occ": q.get("occ", 0),
                              "replace": q["new_display"], "fact": q.get("fact"), "old": q["raw"], "evidence": q.get("new_claim", ""),
                              "context": q.get("context", "")[:120], "approved": False})
            elif q["status"] in ("outdated", "untraced"):
                review.append({"slide": s["slide"], "where": q["where"], "number": q["raw"], "status": q["status"], "context": q.get("context", "")[:120]})
    return {"source": plan.get("source"), "edits": edits, "review": review,
            "how": "set approved: true on each edit you accept (or change 'replace'); add replace_text / set_chart / delete_slide / note "
                   "edits by hand; then `cpe deck patch old.pptx edits.json -o new.pptx`"}


def edits_markdown(e: dict) -> str:
    L = [f"# Proposed edits — {e.get('source')}", "", f"{len(e['edits'])} number edits proposed (none applied until approved); "
         f"{len(e['review'])} numbers to review by hand.", "", "| # | slide | where | old → new | fact | context |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(e["edits"], 1):
        L.append(f"| {i} | {x['slide']} | {x['where']} | {x['old']} → **{x['replace']}** | {x.get('fact') or ''} | {x['context'][:60]} |")
    L += ["", "## To review by hand (no new value proposed)", ""]
    L += [f"- slide {r['slide']} {r['where']}: {r['number']} ({r['status']}) — {r['context'][:80]}" for r in e["review"]]
    return "\n".join(L) + "\n"


def _texts(slide) -> list:
    """The slide's text shapes in the order deck ingest numbers them: the title first, then the body."""
    from .deck_update import _shape_texts

    texts = _shape_texts(slide)
    shapes = [sh for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    sentences = [t for t in texts if len(t["text"].split()) >= 4 and t["size"] >= 16]
    title = (next((t["text"] for t in texts if t["title"]), None)
             or (min(sentences, key=lambda t: t["top"])["text"] if sentences else None)
             or (max(texts, key=lambda t: (t["size"], -t["top"]))["text"] if texts else ""))
    title_shape = next((sh for sh, t in zip(shapes, texts) if t["text"] == title), None)
    body = [sh for sh, t in zip(shapes, texts) if t["text"] != title]
    return [title_shape] + body


def _exhibits(slide) -> list:
    out = []
    for sh in slide.shapes:
        if getattr(sh, "has_chart", False) and sh.has_chart:
            out.append(("chart", sh))
        if getattr(sh, "has_table", False) and sh.has_table:
            out.append(("table", sh))
    return out


def _replace_in_frame(tf, find: str, replace: str, occ: int, mark: bool, number: bool = True) -> bool:
    """Replace the occ-th occurrence of `find` in a text frame, inside its run so formatting is kept.
    A number must stand alone ("3,2" not inside "13,25")."""
    # a number takes its own sign with it ("-150" → "-210"), never a hyphen of a range ("2-4 °C")
    pat = re.compile(rf"(?:(?<![\w.,])[-−])?(?<![\d.,]){re.escape(find.lstrip('-−'))}(?![\d])" if number else re.escape(find))
    seen = 0
    for p in tf.paragraphs:
        runs = list(p.runs)
        full = "".join(r.text for r in runs)
        for m in pat.finditer(full):
            if seen < occ:
                seen += 1
                continue
            pos = 0
            for r in runs:  # the run holding the match start; a match split across runs is merged into it
                end = pos + len(r.text)
                if pos <= m.start() < end:
                    before = r.text[:m.start() - pos]
                    if m.end() <= end:
                        after = r.text[m.end() - pos:]
                    else:
                        after, rest = "", m.end() - end
                        for r2 in runs[runs.index(r) + 1:]:
                            cut = min(rest, len(r2.text))
                            r2.text = r2.text[cut:]
                            rest -= cut
                            if rest <= 0:
                                break
                    if not mark:
                        r.text = before + replace + after
                        return True
                    # only the new text is highlighted: the run is split in three, each keeping its formatting
                    r.text = before
                    new_r, tail = copy.deepcopy(r._r), copy.deepcopy(r._r)
                    r._r.addnext(new_r)
                    new_r.addnext(tail)
                    _set_text(new_r, replace)
                    _set_text(tail, after)
                    _highlight(new_r)
                    for el in (r._r, tail):
                        if not _get_text(el):
                            el.getparent().remove(el)
                    return True
                pos = end
    return False


# a:rPr children that must come after a:highlight (ECMA-376 CT_TextCharacterProperties order)
_AFTER_HIGHLIGHT = {f"{A}{t}" for t in ("uLnTx", "uLn", "uFillTx", "uFill", "latin", "ea", "cs", "sym", "hlinkClick", "hlinkMouseOver", "rtl", "extLst")}


def _set_text(r_el, text: str) -> None:
    r_el.find(f"{A}t").text = text


def _get_text(r_el) -> str:
    t = r_el.find(f"{A}t")
    return t.text or "" if t is not None else ""


def _highlight(r_el) -> None:
    rpr = r_el.find(f"{A}rPr")
    if rpr is None:
        rpr = r_el.makeelement(f"{A}rPr", {})
        r_el.insert(0, rpr)
    for h in rpr.findall(f"{A}highlight"):
        rpr.remove(h)
    hl = rpr.makeelement(f"{A}highlight", {})
    hl.append(hl.makeelement(f"{A}srgbClr", {"val": "FFF200"}))
    nxt = next((c for c in rpr if c.tag in _AFTER_HIGHLIGHT), None)
    if nxt is not None:
        nxt.addprevious(hl)
    else:
        rpr.append(hl)


def _number(slide, e: dict, mark: bool) -> str | None:
    where = e["where"]
    if where == "title" or where.startswith("body["):
        shapes = _texts(slide)
        k = 0 if where == "title" else int(re.search(r"\[(\d+)\]", where).group(1)) + 1
        if k >= len(shapes) or shapes[k] is None:
            return f"{where}: text not found"
        return None if _replace_in_frame(shapes[k].text_frame, e["find"], e["replace"], e.get("occ", 0), mark) else f"{where}: '{e['find']}' not found"
    m = re.match(r"exhibit\[(\d+)\]\.rows\[(\d+)\]\[(\d+)\]", where)
    if m:
        ex = _exhibits(slide)
        i, r, c = map(int, m.groups())
        if i >= len(ex) or ex[i][0] != "table":
            return f"{where}: table not found"
        rows = list(ex[i][1].table.rows)
        if r + 1 >= len(rows) or c >= len(rows[r + 1].cells):
            return f"{where}: cell not found"
        cell = rows[r + 1].cells[c]
        return None if _replace_in_frame(cell.text_frame, e["find"], e["replace"], e.get("occ", 0), mark) else f"{where}: '{e['find']}' not found"
    m = re.match(r"exhibit\[(\d+)\]\.(.+)\[(.*)\]$", where)
    if m:
        i, series, cat = int(m.group(1)), m.group(2), m.group(3)
        ex = _exhibits(slide)
        if i >= len(ex) or ex[i][0] != "chart":
            return f"{where}: chart not found"
        from .deck_update import _parse_core

        v = _parse_core(e["replace"].lstrip("-"))
        if v is None:
            return f"{where}: '{e['replace']}' is not a number"
        v = -v if e["replace"].startswith("-") else v
        return _set_point(ex[i][1].chart, series, cat, v)
    return f"{where}: location not understood"


def _set_point(chart, series: str, cat: str, value: float) -> str | None:
    plot = chart.plots[0]
    cats = [str(c) for c in plot.categories]
    data = {s.name: list(s.values) for p in chart.plots for s in p.series}
    if series not in data or cat not in cats:
        return f"chart point {series}[{cat}] not found"
    data[series][cats.index(cat)] = value
    return _replace_chart(chart, cats, data)


def _replace_chart(chart, cats: list, data: dict) -> str | None:
    from pptx.chart.data import CategoryChartData

    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in data.items():
        cd.add_series(name, [None if v is None else float(v) for v in vals])
    chart.replace_data(cd)  # keeps the chart's formatting; only its data changes
    return None


def apply_edits(pptx_in: str | Path, edits: dict, pptx_out: str | Path, mark: bool = False, accept_proposed: bool = False) -> dict:
    from pptx import Presentation

    prs = Presentation(str(pptx_in))
    slides = list(prs.slides)
    applied, failed, skipped = [], [], []
    notes: dict = {}
    deletes = []
    for e in edits.get("edits") or []:
        op = e.get("op", "number")
        if op == "number" and not (e.get("approved") or accept_proposed):
            skipped.append(e)
            continue
        n = int(e["slide"])
        if not 1 <= n <= len(slides):
            failed.append({**e, "why": f"slide {n} does not exist"})
            continue
        slide = slides[n - 1]
        why = None
        if op == "number":
            why = _number(slide, e, mark)
            line = f"{e.get('old') or e['find']} → {e['replace']}" + (f" ({e['fact']})" if e.get("fact") else "")
        elif op == "replace_text":
            frames = [sh.text_frame for sh in slide.shapes if sh.has_text_frame]
            frames += [c.text_frame for sh in slide.shapes if getattr(sh, "has_table", False) and sh.has_table for r in sh.table.rows for c in r.cells]
            hits = sum(_replace_in_frame(tf, e["find"], e["replace"], 0, mark, number=False) for tf in frames)
            why = None if hits else f"'{e['find']}' not found"
            line = f"'{e['find']}' → '{e['replace']}'"
        elif op == "set_chart":
            ex = _exhibits(slide)
            i = int(e.get("exhibit", 0))
            if i >= len(ex) or ex[i][0] != "chart":
                why = "chart not found"
            else:
                ch = ex[i][1].chart
                cats = [str(c) for c in ch.plots[0].categories]
                data = {s.name: list(s.values) for p in ch.plots for s in p.series}
                if e["series"] not in data or len(e["values"]) != len(cats):
                    why = f"series '{e['series']}' not found or {len(e['values'])} values for {len(cats)} categories"
                else:
                    data[e["series"]] = e["values"]
                    why = _replace_chart(ch, e.get("categories") or cats, data)
            line = f"chart series '{e.get('series')}' replaced"
        elif op == "delete_slide":
            deletes.append(n)
            line = "slide deleted"
        elif op == "note":
            line = e["text"]
        else:
            why = f"unknown op '{op}'"
            line = ""
        if why:
            failed.append({**e, "why": why})
        else:
            applied.append(e)
            notes.setdefault(n, []).append(line)
    for n, lines in notes.items():
        if n in deletes:
            continue
        tf = slides[n - 1].notes_slide.notes_text_frame
        prefix = (tf.text + "\n\n") if tf.text.strip() else ""
        tf.text = prefix + "Updated by cpe deck patch:\n" + "\n".join(f"- {x}" for x in lines)
    lst = prs.slides._sldIdLst
    ids = list(lst)
    for n in sorted(set(deletes), reverse=True):
        sid = ids[n - 1]
        prs.part.drop_rel(sid.rId)
        lst.remove(sid)
    Path(pptx_out).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(pptx_out))
    return {"source": Path(pptx_in).name, "output": Path(pptx_out).name, "applied": applied, "failed": failed,
            "skipped_unapproved": len(skipped), "slides_deleted": sorted(set(deletes)), "marked": mark}


def report_markdown(r: dict) -> str:
    L = [f"# Patch report — {r['source']} → {r['output']}", "",
         f"Applied {len(r['applied'])} · failed {len(r['failed'])} · not approved {r['skipped_unapproved']} · slides deleted {r['slides_deleted']}", ""]
    if r["failed"]:
        L += ["## Not applied (left as they were)", ""] + [f"- slide {f.get('slide')}: {f['why']}" for f in r["failed"]] + [""]
    L += ["## Applied", ""] + [f"- slide {a['slide']} {a.get('where', a.get('op'))}: {a.get('old', a.get('find', ''))} → {a.get('replace', '')}" for a in r["applied"]]
    return "\n".join(L) + "\n"


def write_edits(work: str | Path) -> dict:
    work = Path(work)
    plan = json.loads((work / "update_plan.json").read_text(encoding="utf-8"))
    e = proposed_edits(plan)
    (work / "edits.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (work / "edits.md").write_text(edits_markdown(e), encoding="utf-8", newline="\n")
    return e


def write_patch(pptx_in: str | Path, edits_path: str | Path, pptx_out: str | Path, mark: bool = False, accept_proposed: bool = False) -> dict:
    edits = json.loads(Path(edits_path).read_text(encoding="utf-8"))
    r = apply_edits(pptx_in, edits, pptx_out, mark, accept_proposed)
    out = Path(pptx_out).parent
    (out / "patch_report.json").write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    (out / "patch_report.md").write_text(report_markdown(r), encoding="utf-8", newline="\n")
    return r
