"""The review as a spreadsheet (v2.1, item 3): no JSON editing.

    cpe update --sheet work        → work/review.xlsx
    (open it in Excel / LibreOffice / Google Sheets: approve, correct, dismiss, write a headline)
    cpe update --read-sheet work   → the decisions into edits.json and fact_conflicts.json
    cpe update --apply work -o new.pptx  reads the sheet first when it is newer than edits.json

Four sheets, one row per decision, the columns to fill on the right and in colour:
  Changes     every proposed number edit (from a fact, derived, or by hand) and every number the plan
              left for review: Approve (yes / no), Corrected value, Comment.
              A number left for review becomes an edit when it gets a value and "yes".
  Headlines   every slide whose message changed: Approve the proposal, or write your own headline.
  Conflicts   the versions of one quantity across sources, by priority: Decision ("use" a fact or
              "dismiss"), the fact to use, the reason. A dismissal needs a reason.
  Slides      keep / delete / rebuild each slide (rebuild uses `cpe update --rebuild`).
Rows are matched back by the key in column A, so sorting or filtering the sheet is safe.
"""
from __future__ import annotations

import json
from pathlib import Path

LANG = {
    "es": {"Changes": "Cambios", "Headlines": "Titulares", "Conflicts": "Conflictos", "Slides": "Diapositivas",
           "key": "clave", "slide": "Diapositiva", "where": "Dónde", "old": "Antes", "new": "Propuesto", "origin": "Origen",
           "context": "Contexto", "evidence": "Evidencia", "approve": "¿Aprobar? (sí/no)", "value": "Valor corregido", "comment": "Comentario",
           "verdict": "Veredicto", "headline": "Titular actual", "proposal": "Propuesta", "own": "Titular propio",
           "priority": "Prioridad", "state": "Estado", "type": "Tipo", "versions": "Versiones", "decision": "Decisión (usar / descartar)",
           "use": "Hecho a usar", "why": "Motivo", "action": "Acción (mantener / eliminar / reconstruir)",
           "yes": ("sí", "si", "s", "yes", "y", "x", "ok"), "no": ("no", "n"), "fact": "hecho", "derived": "derivado", "hand": "a mano",
           "review": "revisar (sin propuesta)"},
    "en": {"Changes": "Changes", "Headlines": "Headlines", "Conflicts": "Conflicts", "Slides": "Slides",
           "key": "key", "slide": "Slide", "where": "Where", "old": "Old", "new": "Proposed", "origin": "Origin",
           "context": "Context", "evidence": "Evidence", "approve": "Approve? (yes/no)", "value": "Corrected value", "comment": "Comment",
           "verdict": "Verdict", "headline": "Current headline", "proposal": "Proposal", "own": "Your headline",
           "priority": "Priority", "state": "State", "type": "Type", "versions": "Versions", "decision": "Decision (use / dismiss)",
           "use": "Fact to use", "why": "Reason", "action": "Action (keep / delete / rebuild)",
           "yes": ("yes", "y", "x", "ok", "sí", "si"), "no": ("no", "n"), "fact": "fact", "derived": "derived", "hand": "by hand",
           "review": "review (no proposal)"},
}


def _lang(plan: dict) -> dict:
    return LANG["es" if plan.get("decimal_mark") == "," else "en"]


def _load(work: Path, name: str, default):
    p = work / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write_sheet(work: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    work = Path(work)
    plan = _load(work, "update_plan.json", {"slides": []})
    edits = _load(work, "edits.json", {"edits": [], "review": []})
    msgs = _load(work, "messages.json", [])
    conf = _load(work, "fact_conflicts.json", {"conflicts": []})
    L = _lang(plan)
    wb = Workbook()
    fill = PatternFill("solid", fgColor="FFF4C2")
    bold = Font(bold=True)

    def sheet(title, headers, rows, inputs, widths, choices=None):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for c in ws[1]:
            c.font = bold
        for r in rows:
            ws.append(r)
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
                if c.column_letter in inputs:
                    c.fill = fill
        for col, opts in (choices or {}).items():
            dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{col}2:{col}{max(2, len(rows) + 1)}")
        ws.column_dimensions["A"].hidden = True  # the key that ties a row back to its decision
        ws.freeze_panes = "B2"
        return ws

    yes, no = L["yes"][0], L["no"][0]
    rows = []
    for e in edits.get("edits") or []:
        if e.get("op", "number") != "number" or not e.get("id"):
            continue
        origin = L["derived"] if e.get("derived") else (L["fact"] + f" {e['fact']}" if e.get("fact") else L["hand"])
        state = yes if e.get("approved") else ""
        rows.append([f"edit:{e['id']}", e.get("slide"), e.get("where"), e.get("old"), e.get("replace"), origin,
                     (e.get("context") or "")[:200], (e.get("evidence") or "")[:200], state, "", ""])
    have = {r[0][5:] for r in rows}
    for s in plan.get("slides") or []:
        for q in s["numbers"]:
            if q.get("id") and q["id"] not in have and q["status"] in ("outdated", "untraced"):
                rows.append([f"num:{q['id']}", s["slide"], q["where"], q["raw"], "", L["review"], (q.get("context") or "")[:200], "", "", "", ""])
    rows.sort(key=lambda r: (int(r[1] or 0), str(r[2])))
    sheet(L["Changes"], [L["key"], L["slide"], L["where"], L["old"], L["new"], L["origin"], L["context"], L["evidence"], L["approve"], L["value"], L["comment"]],
          rows, {"I", "J", "K"}, {"B": 8, "C": 18, "D": 12, "E": 12, "F": 16, "G": 50, "H": 40, "I": 12, "J": 14, "K": 30}, {"I": [yes, no]})
    hrows = []
    heads = {e["slide"]: e for e in edits.get("edits") or [] if e.get("op") == "set_headline"}
    for m in msgs:
        if m.get("verdict") == "holds":
            continue
        e = heads.get(m["slide"])
        hrows.append([f"head:{m['slide']}", m["slide"], m["verdict"], m["headline"], (e or {}).get("text") or m.get("proposal") or "",
                      yes if (e or {}).get("approved") else "", "", ""])
    sheet(L["Headlines"], [L["key"], L["slide"], L["verdict"], L["headline"], L["proposal"], L["approve"], L["own"], L["comment"]],
          hrows, {"F", "G", "H"}, {"B": 8, "C": 16, "D": 50, "E": 50, "F": 12, "G": 50, "H": 30}, {"F": [yes, no]})
    crows = []
    use_w, dis_w = ("usar", "descartar") if L is LANG["es"] else ("use", "dismiss")
    for c in conf.get("conflicts") or []:
        state = "descartado" if c.get("dismissed") and L is LANG["es"] else "dismissed" if c.get("dismissed") else \
            ("resuelto" if L is LANG["es"] else "resolved") if c.get("resolution") else ""
        vers = "\n".join(f"{x['fact']}: {x['value']:g} — {x['source']}" + (f" — {x['says'][:80]}" if x.get("says") else "") for x in c["facts"])
        crows.append([f"conf:{','.join(sorted(x['fact'] for x in c['facts']))}", c.get("id"), c.get("priority", ""), state, c.get("type"), vers,
                      "", "", c.get("dismissed") or c.get("resolution") or ""])
    sheet(L["Conflicts"], [L["key"], "ID", L["priority"], L["state"], L["type"], L["versions"], L["decision"], L["use"], L["why"]],
          crows, {"G", "H", "I"}, {"B": 6, "C": 9, "D": 11, "E": 18, "F": 70, "G": 14, "H": 12, "I": 40}, {"G": [use_w, dis_w]})
    srows = []
    acts = ("mantener", "eliminar", "reconstruir") if L is LANG["es"] else ("keep", "delete", "rebuild")
    deleted = {e["slide"] for e in edits.get("edits") or [] if e.get("op") == "delete_slide"}
    for s in plan.get("slides") or []:
        srows.append([f"slide:{s['slide']}", s["slide"], s.get("headline", ""), acts[1] if s["slide"] in deleted else "", ""])
    sheet(L["Slides"], [L["key"], L["slide"], L["headline"], L["action"], L["comment"]], srows, {"D", "E"},
          {"B": 8, "C": 70, "D": 16, "E": 30}, {"D": list(acts)})
    del wb[wb.sheetnames[0]]
    out = work / "review.xlsx"
    wb.save(out)
    return out


def _cell(v) -> str:
    return "" if v is None else str(v).strip()


def read_sheet(work: str | Path) -> dict:
    """The sheet's decisions into edits.json / fact_conflicts.json. Returns counts and problems."""
    from openpyxl import load_workbook

    from .deck_update import _parse_core

    work = Path(work)
    plan = _load(work, "update_plan.json", {"slides": []})
    L = _lang(plan)
    wb = load_workbook(work / "review.xlsx", data_only=True)
    edits = _load(work, "edits.json", {"edits": []})
    conf = _load(work, "fact_conflicts.json", {"conflicts": []})
    items = {q["id"]: (s["slide"], q) for s in plan.get("slides") or [] for q in s["numbers"] if q.get("id")}
    by_id = {e.get("id"): e for e in edits.get("edits") or [] if e.get("op", "number") == "number" and e.get("id")}
    st = {"approved": 0, "rejected": 0, "corrected": 0, "added": 0, "headlines": 0, "conflicts": 0, "slides": 0, "problems": []}
    yes, no = L["yes"], L["no"]
    hint = plan.get("decimal_mark")

    def rows(name):
        if name not in wb.sheetnames:
            return []
        ws = wb[name]
        return [[_cell(c.value) for c in r] for r in ws.iter_rows(min_row=2)]

    for r in rows(L["Changes"]):
        key, ok, val, note = r[0], r[8].lower(), r[9], r[10]
        if not key or (not ok and not val):
            continue
        kind, nid = key.split(":", 1)
        if val and _parse_core(val.lstrip("-−"), hint) is None:
            st["problems"].append(f"{L['Changes']} {r[1]} {r[2]}: '{val}' is not a number")
            continue
        if kind == "edit" and nid in by_id:
            e = by_id[nid]
            if ok in no:
                e["approved"] = False
                st["rejected"] += 1
                continue
            if val:
                e["replace"], e["corrected_by_reviewer"] = val, True
                st["corrected"] += 1
            if ok in yes or val:
                e["approved"] = True
                st["approved"] += 1
            if note:
                e["reviewer_note"] = note
        elif kind == "num" and nid in items and val and ok not in no:
            n, q = items[nid]
            edits["edits"].append({"op": "number", "id": nid, "slide": n, "where": q["where"], "find": q.get("core"), "occ": q.get("occ", 0),
                                   "replace": val, "old": q["raw"], "approved": True, "by_hand": True, **({"reviewer_note": note} if note else {})})
            st["added"] += 1
        elif ok in yes and not val and kind == "num":
            st["problems"].append(f"{L['Changes']} {r[1]} {r[2]}: approved without a value")
    heads = {e["slide"]: e for e in edits.get("edits") or [] if e.get("op") == "set_headline"}
    for r in rows(L["Headlines"]):
        key, prop, ok, own, note = r[0], r[4], r[5].lower(), r[6], r[7]
        if not key or not (ok or own):
            continue
        n = int(key.split(":", 1)[1])
        text = own or (prop if ok in yes else "")
        e = heads.get(n)
        if ok in no and not own:
            if e:
                e["approved"] = False
            continue
        if not text:
            continue
        if e:
            e.update(text=text, approved=True, by_hand=bool(own))
        else:
            edits["edits"].append({"op": "set_headline", "slide": n, "text": text, "approved": True, "by_hand": bool(own)})
        st["headlines"] += 1
    use_w, dis_w = ("usar", "descartar") if L is LANG["es"] else ("use", "dismiss")
    cmap = {",".join(sorted(x["fact"] for x in c["facts"])): c for c in conf.get("conflicts") or []}
    for r in rows(L["Conflicts"]):
        key, dec, fact, why = r[0], r[6].lower(), r[7], r[8]
        if not key or not dec:
            continue
        c = cmap.get(key.split(":", 1)[1])
        if c is None:
            st["problems"].append(f"{L['Conflicts']} {r[1]}: no longer detected")
            continue
        if dec.startswith(dis_w[:4]) or dec.startswith("dism") or dec.startswith("desc"):
            if not why:
                st["problems"].append(f"{L['Conflicts']} {r[1]}: a dismissal needs a reason")
                continue
            c["dismissed"] = why
            c.pop("resolution", None)
        else:
            if fact and fact not in {x["fact"] for x in c["facts"]}:
                st["problems"].append(f"{L['Conflicts']} {r[1]}: {fact} is not one of its facts")
                continue
            c["resolution"] = (f"use {fact}" if fact else "resolved") + (f": {why}" if why else "")
            c.pop("dismissed", None)
        st["conflicts"] += 1
    acts = {"mantener": "keep", "keep": "keep", "eliminar": "delete", "delete": "delete", "reconstruir": "rebuild", "rebuild": "rebuild"}
    rebuild = []
    for r in rows(L["Slides"]):
        key, act = r[0], acts.get(r[3].lower())
        if not key or not act:
            continue
        n = int(key.split(":", 1)[1])
        edits["edits"] = [e for e in edits["edits"] if not (e.get("op") == "delete_slide" and e.get("slide") == n)]
        if act == "delete":
            edits["edits"].append({"op": "delete_slide", "slide": n, "approved": True})
        elif act == "rebuild":
            rebuild.append(n)
        st["slides"] += 1
    st["rebuild"] = rebuild
    (work / "edits.json").write_text(json.dumps(edits, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (work / "fact_conflicts.json").write_text(json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return st
