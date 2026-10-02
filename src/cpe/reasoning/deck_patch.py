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
                d = q.get("direct") or {}
                own = d.get("new_display") if d.get("new_display") and d["new_display"] != q["new_display"] else None
                alt = f" | its own match says {own} ({d.get('fact')})" if own else ""
                if q.get("group_disagrees"):  # v2.4: restatements of this figure got different values: the reviewer decides
                    alt += " | restatements disagree: " + "; ".join(q["group_disagrees"][:4])
                edits.append({"op": "number", "id": q.get("id"), "slide": s["slide"], "where": q["where"], "find": q["core"], "occ": q.get("occ", 0),
                              "replace": q["new_display"], "fact": q.get("fact"), "old": q["raw"], "evidence": q.get("new_claim", "") + alt,
                              "context": q.get("context", "")[:120], "approved": False, **({"derived": q["derived"]} if q.get("derived") else {}),
                              **({"direct": own} if own else {})})
            elif q["status"] in ("outdated", "untraced"):
                review.append({"slide": s["slide"], "where": q["where"], "number": q["raw"], "status": q["status"], "context": q.get("context", "")[:120],
                               **({"disagree": q["group_disagrees"][:4]} if q.get("group_disagrees") else {})})
    return {"source": plan.get("source"), "edits": edits, "review": review,
            "how": "set approved: true on each edit you accept (or change 'replace'); add replace_text / set_chart / delete_slide / note "
                   "edits by hand; then `cpe deck patch old.pptx edits.json -o new.pptx`"}


def derive_edits(plan: dict, edits: dict) -> dict:
    """v2.0: recompute totals, ratios and repeated figures from the APPROVED edits (and the numbers the
    plan found current). Each derived figure becomes a proposed edit marked `derived`, unapproved; an
    edit the reviewer approved by hand is never overwritten. Returns {"added", "updated", "unchanged"}."""
    from .deck_update import _factor, _parse_core, display_in
    from .derive import _close, derive, relations, with_groups

    hint = plan.get("decimal_mark")
    items = {q["id"]: (s["slide"], q) for s in plan["slides"] for q in s["numbers"] if q.get("id")}
    known = {i: (-abs(q["value"]) if str(q["raw"]).startswith("-") else q["value"]) for i, (_, q) in items.items() if q["status"] == "current"}
    approved = set()
    for e in edits.get("edits") or []:
        if e.get("op", "number") == "number" and e.get("approved") and e.get("id") in items:
            q = items[e["id"]][1]
            f, v = _factor(q, hint), _parse_core(str(e["replace"]).lstrip("-−"), hint)
            if f and v is not None:
                known[e["id"]] = (-1 if str(e["replace"]).startswith(("-", "−")) else 1) * v * f
                approved.add(e["id"])
    proposed = {}
    for e in edits.get("edits") or []:  # values proposed but not yet approved: a provisional derivation
        if e.get("op", "number") == "number" and not e.get("approved") and not e.get("derived") and e.get("id") in items:
            q = items[e["id"]][1]
            if e["replace"] == q.get("new_display") and q.get("new_num") is not None:
                proposed[e["id"]] = q["new_num"]  # the plan's value, not its rounded display
                continue
            f, v = _factor(q, hint), _parse_core(str(e["replace"]).lstrip("-−"), hint)
            if f and v is not None:
                proposed[e["id"]] = (-1 if str(e["replace"]).startswith(("-", "−")) else 1) * v * f
    # v2.2: one figure, one value: its group follows the member the reviewer approved, else the plan's head
    base = relations(plan)
    arith = {r["target"] for r in base if r["op"] != "same"}

    def pick(g: list) -> str | None:  # the approved member, else the plan's head, else one the deck's arithmetic gives
        ids = [i for i, _ in g]
        return (next((i for i in ids if i in approved), None) or next((i for i in ids if i in items and items[i][1].get("group_head")), None)
                or next((i for i in ids if i in arith), None))

    rels = [r for r in with_groups(plan, base, pick) if r["target"] not in approved]
    targets = {r["target"] for r in rels if r["op"] != "grow"}
    firm = derive(plan, rels, {k: v for k, v in known.items() if k not in targets or k in approved})
    loose = derive(plan, rels, {k: v for k, v in {**proposed, **known}.items() if k not in targets or k in approved})
    got = {**loose, **firm}
    pending = set(loose) - set(firm)
    by_id = {e.get("id"): e for e in edits.get("edits") or [] if e.get("op", "number") == "number"}
    stats = {"added": 0, "updated": 0, "unchanged": 0, "dropped": 0}
    for e in list(edits.get("edits") or []):  # a derived proposal whose parts are not all approved yet is withdrawn
        if e.get("derived") and not e.get("approved") and e.get("id") not in got:
            if e.get("direct"):
                e.pop("derived")
                e["replace"] = e.pop("direct")
            else:
                edits["edits"].remove(e)
            stats["dropped"] += 1
    for tid, (v, r) in got.items():
        if tid in approved or tid not in items:
            continue
        n, q = items[tid]
        if _close(v, q):
            stats["unchanged"] += 1
            if tid in by_id and not by_id[tid].get("approved"):
                edits["edits"].remove(by_id[tid])  # the parts as approved leave this figure as it was
            continue
        info = {"op": r["op"], "from": r["parts"], "how": r["how"], **({"pending_parts": True} if tid in pending else {})}
        new = {"op": "number", "id": tid, "slide": n, "where": q["where"], "find": q.get("core"), "occ": q.get("occ", 0),
               "replace": display_in(q, v, hint), "old": q["raw"], "fact": None, "derived": info,
               "evidence": f"{r['how']}: " + " , ".join(items[p][1]["raw"] for p in r["parts"] if p in items)
               + (" (some parts not approved yet: provisional)" if tid in pending else " (approved values)"),
               "context": (q.get("context") or "")[:120], "approved": False}
        if tid in by_id:
            if by_id[tid].get("replace") != new["replace"] or by_id[tid].get("derived") != info:
                new["direct"] = by_id[tid].get("replace") if not by_id[tid].get("derived") else by_id[tid].get("direct")
                by_id[tid].clear()
                by_id[tid].update(new)
                stats["updated"] += 1
        else:
            edits["edits"].append(new)
            stats["added"] += 1
    return stats


def edits_markdown(e: dict) -> str:
    nums = [x for x in e["edits"] if x.get("op", "number") == "number"]
    other = [x for x in e["edits"] if x.get("op", "number") != "number"]
    ok = sum(1 for x in nums if x.get("approved"))
    L = [f"# Proposed edits — {e.get('source')}", "", f"{len(nums)} number edits ({ok} approved ✓; only approved ones are applied); "
         f"{len(e.get('review') or [])} numbers to review by hand.", "",
         "| # | slide | where | old → new | source | context |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(nums, 1):
        d = x.get("derived") or {}
        src = x.get("fact") or (f"derived: {d['how']}" + (" (provisional)" if d.get("pending_parts") else "") if d else "by hand")
        if x.get("direct") and x["direct"] != x.get("replace"):
            src += f"; its own match said {x['direct']}"
        L.append(f"| {i} | {x.get('slide')} | {x.get('where')} | {x.get('old', x.get('find'))} → **{x.get('replace')}** {'✓' if x.get('approved') else ''} "
                 f"| {src} | {(x.get('context') or '')[:60]} |")
    if other:
        L += ["", "## Other edits", ""] + [f"- slide {x.get('slide')}: {x.get('op')} {x.get('text') or x.get('find') or x.get('series') or ''}" for x in other]
    L += ["", "## To review by hand (no new value proposed)", ""]
    L += [f"- slide {r['slide']} {r['where']}: {r['number']} ({r['status']}) — {r['context'][:80]}"
          + (f" — restatements disagree: {'; '.join(r['disagree'])}" if r.get("disagree") else "") for r in e.get("review") or []]
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


def _set_frame_text(tf, text: str, mark: bool) -> None:
    """The whole text of a frame replaced, in its first run (so the headline keeps its formatting)."""
    paras = list(tf.paragraphs)
    runs = [r for p in paras for r in p.runs]
    if not runs:
        tf.text = text
        return
    first = runs[0]
    first.text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    for p in paras[1:]:
        p._p.getparent().remove(p._p)
    if mark:
        _highlight(first._r)


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
    replaces: dict = {}
    order = {"number": 0, "set_chart": 0, "replace_text": 1, "set_headline": 2, "note": 3, "replace_slide": 4, "delete_slide": 4}
    # a headline rewrite after its numbers; the later occurrences of a figure in one text first, so earlier ones keep their place
    for e in sorted(edits.get("edits") or [], key=lambda x: (order.get(x.get("op", "number"), 5), -int(x.get("occ") or 0))):
        op = e.get("op", "number")
        if op in ("number", "set_headline", "replace_slide") and not (e.get("approved") or accept_proposed):
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
        elif op == "set_headline" and not e.get("text"):
            why = "no wording yet (needs_wording): add an action title to the edit's `candidates` and re-run"
            line = ""
        elif op == "set_headline":
            shapes = _texts(slide)
            why = None if shapes and shapes[0] is not None else "no headline found"
            if not why:
                _set_frame_text(shapes[0].text_frame, e["text"], mark)
            line = f"headline rewritten: '{e['text']}'"
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
        elif op == "replace_slide":  # v2.0: a rebuilt slide takes this one's place, on its layout
            src = Path(e["from"])
            if not src.exists():
                why = f"rebuilt deck {src} not found"
            else:
                replaces[n] = e
            line = f"slide rebuilt: '{e.get('headline', '')}'"
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
        target = slides[n - 1]
        tf = target.notes_slide.notes_text_frame
        prefix = (tf.text + "\n\n") if tf.text.strip() else ""
        tf.text = prefix + "Updated by cpe deck patch:\n" + "\n".join(f"- {x}" for x in lines)
    lst = prs.slides._sldIdLst
    ids = list(lst)
    built: dict = {}
    from pptx import Presentation as _P

    from .rebuild import transplant_slide

    for n in sorted(set(replaces) - set(deletes), reverse=True):  # all insertions first: new part names stay unique
        e = replaces[n]
        src = built.setdefault(e["from"], _P(e["from"]))
        new = transplant_slide(prs, list(src.slides)[int(e.get("index", 0))], n - 1, slides[n - 1].slide_layout, old_slide=slides[n - 1])
        new.notes_slide.notes_text_frame.text = f"Rebuilt by cpe update (old slide {n}). " + "\n".join(notes.get(n, []))
    for n in sorted(set(deletes) | set(replaces), reverse=True):
        sid = ids[n - 1]  # the old slide's own entry, wherever the insertions moved it
        prs.part.drop_rel(sid.rId)
        lst.remove(sid)
    Path(pptx_out).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(pptx_out))
    return {"source": Path(pptx_in).name, "output": Path(pptx_out).name, "applied": applied, "failed": failed,
            "skipped_unapproved": len(skipped), "slides_deleted": sorted(set(deletes)), "slides_rebuilt": sorted(set(replaces) - set(deletes)), "marked": mark}


def report_markdown(r: dict) -> str:
    L = [f"# Patch report — {r['source']} → {r['output']}", "",
         f"Applied {len(r['applied'])} · failed {len(r['failed'])} · not approved {r['skipped_unapproved']} · slides deleted {r['slides_deleted']}", ""]
    if r["failed"]:
        L += ["## Not applied (left as they were)", ""] + [f"- slide {f.get('slide')}: {f['why']}" for f in r["failed"]] + [""]
    L += ["## Applied", ""] + [f"- slide {a['slide']} {a.get('where', a.get('op'))}: {a.get('old', a.get('find', ''))} → {a.get('replace', '')}" for a in r["applied"]]
    return "\n".join(L) + "\n"


def write_edits(work: str | Path, rederive: bool = False) -> dict:
    """Write work/edits.json from the plan; with `rederive`, keep the reviewed edits.json and recompute
    the derived figures from what was approved."""
    work = Path(work)
    plan = json.loads((work / "update_plan.json").read_text(encoding="utf-8"))
    if rederive and (work / "edits.json").exists():
        e = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    else:
        e = proposed_edits(plan)
    e["derived"] = derive_edits(plan, e)
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
