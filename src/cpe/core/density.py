"""Content density engine.

Runs BEFORE drawing, on the resolved layout zones, with real font metrics.
For every text-bearing zone it answers: does the content fit at the base size?
at the legibility floor? If not, it decides — in this order —
  1. try another eligible layout with more room for that role,
  2. split mechanically-splittable content (table rows, gantt rows) into a
     continuation slide,
  3. otherwise report CONTENT_OVER_CAPACITY with the number of words to cut
     (the agent rewrites; the engine never truncates meaning).
It also checks exhibit legibility budgets (categories, series, rows, columns)
and the slide word budget of the deck profile.
"""
from __future__ import annotations

import copy

from ..design import text_metrics as tm
from ..design.tokens import FONT_FLOOR, LINE_SPACING, PARA_SPACE_AFTER, SPACING, type_style
from ..layout.engine import EXHIBIT_HEADER_H, Layout, resolve_zones
from ..spec import issue, slide_exhibits
from .headline import words
from .layout_selector import commentary_words, content_roles


def _points_text(points) -> list[str]:
    out = []
    for p in points or []:
        if isinstance(p, str):
            out.append(p)
        else:
            out.append(p.get("text", ""))
            out += list(p.get("sub", []) or [])
    return out


def text_need(paras: list[str], width: float, size: float, bold=False, bullets=True) -> float:
    plain = [p.replace("**", "") for p in paras]
    h, _ = tm.text_block_height(plain, width, size, bold, LINE_SPACING, PARA_SPACE_AFTER + 3, 0.17 if bullets else 0.0)
    return h


def zone_fit(role: str, content, box, profile: dict) -> dict:
    """Return {fits_base, fits_floor, need_base, need_floor, avail, excess_words}."""
    body = type_style("body", profile)
    size, floor = body["size"], FONT_FLOOR["body"]
    if role == "commentary":
        paras = _points_text(content.get("points") if isinstance(content, dict) else content)
        w = box.w - SPACING["M"]
        avail = box.h - ((0.35 + SPACING["S"]) if isinstance(content, dict) and content.get("title") else 0)
    elif role == "column":
        paras = _points_text(content.get("points"))
        w = box.w
        avail = box.h - 0.62 - SPACING["M"] - (0.95 if content.get("metric") else 0) - (0.45 if content.get("subtitle") else 0)
    elif role == "statements":
        items = (content.get("data") or {}).get("items") or []
        n = max(1, len(items))
        row_h = (box.h - SPACING["S"] * (n - 1)) / n
        worst = None
        for it in items:
            sup = it.get("text") or it.get("points") or ""
            sup = sup if isinstance(sup, list) else [sup]
            claim_w = (box.w - 0.55) * 0.42 - SPACING["M"]
            sup_w = box.w - 0.55 - (box.w - 0.55) * 0.42
            need_c = text_need([it.get("title", "")], claim_w, 14 * profile.get("font_scale", 1), True, False)
            need_s = text_need(sup, sup_w, size, False, len(sup) > 1)
            need_f = text_need(sup, sup_w, floor, False, len(sup) > 1)
            r = {"need_base": max(need_c, need_s), "need_floor": max(need_c, need_f), "avail": row_h - 0.08}
            if worst is None or r["need_floor"] - r["avail"] > worst["need_floor"] - worst["avail"]:
                worst = r
        worst = worst or {"need_base": 0, "need_floor": 0, "avail": box.h}
        worst["fits_base"] = worst["need_base"] <= worst["avail"]
        worst["fits_floor"] = worst["need_floor"] <= worst["avail"]
        worst["excess_words"] = 0 if worst["fits_floor"] else int(10 * (worst["need_floor"] / max(0.1, worst["avail"]) - 1) * 3)
        return worst
    else:
        return {"fits_base": True, "fits_floor": True, "need_base": 0, "need_floor": 0, "avail": box.h, "excess_words": 0}
    need_b = text_need(paras, w, size)
    need_f = text_need(paras, w, floor)
    total_words = sum(len(words(p)) for p in paras)
    excess = 0
    if need_f > avail and need_f > 0:
        excess = int(total_words * (1 - avail / need_f)) + 1
    return {"fits_base": need_b <= avail, "fits_floor": need_f <= avail, "need_base": round(need_b, 2), "need_floor": round(need_f, 2), "avail": round(avail, 2), "excess_words": excess}


def check_slide(slide: dict, layout: Layout, profile: dict) -> tuple[list[dict], dict]:
    """Fit analysis of one slide on one layout."""
    sid = slide.get("id")
    roles = content_roles(slide)
    zones = resolve_zones(layout, with_takeaway=bool(slide.get("takeaway")), has_subheadline=bool(slide.get("subheadline")))
    out: list[dict] = []
    report: dict = {}
    by_role: dict[str, list] = {}
    for z in zones.values():
        by_role.setdefault(z.role, []).append(z)
    if roles.get("commentary") and by_role.get("commentary"):
        z = by_role["commentary"][0]
        if z.style == "columns":
            r = {"fits_base": True, "fits_floor": True, "excess_words": 0}
            pts = _points_text(roles["commentary"].get("points"))
            cols = max(1, len(pts))
            cw = (z.box.w - 0.22 * (cols - 1)) / cols
            for ptxt in pts:
                need = text_need([ptxt], cw, FONT_FLOOR["body"], bullets=False)
                if need > z.box.h - SPACING["S"]:
                    r = {"fits_base": False, "fits_floor": False, "excess_words": int(len(words(ptxt)) * (1 - (z.box.h - SPACING['S']) / need)) + 1}
        else:
            r = zone_fit("commentary", roles["commentary"], z.box, profile)
        report["commentary"] = r
        _, nb = commentary_words(roles["commentary"])
        if nb > profile.get("max_bullets_per_zone", 5):
            out.append(issue("warning", "DENSITY_BULLETS", f"{nb} bullets in commentary (budget {profile.get('max_bullets_per_zone', 5)}): keep the 3-4 that prove the headline", sid))
        for ptxt in _points_text(roles["commentary"].get("points") if isinstance(roles["commentary"], dict) else roles["commentary"]):
            if len(words(ptxt)) > profile.get("max_words_per_bullet", 22):
                out.append(issue("info", "DENSITY_LONG_BULLET", f"Bullet of {len(words(ptxt))} words: lead with the point, cut the rest ('{ptxt[:50]}…')", sid))
                break
        if not r["fits_floor"]:
            out.append(issue("error", "CONTENT_OVER_CAPACITY", f"Commentary does not fit even at {FONT_FLOOR['body']} pt: cut ~{r['excess_words']} words or split the slide", sid, role="commentary", excess_words=r["excess_words"]))
        elif not r["fits_base"]:
            out.append(issue("info", "DENSITY_SHRINK", "Commentary fits only by shrinking text towards the floor; consider trimming", sid))
    if roles.get("column") and by_role.get("column"):
        for z, col in zip(by_role["column"], roles["column"]):
            r = zone_fit("column", col, z.box, profile)
            if not r["fits_floor"]:
                out.append(issue("error", "CONTENT_OVER_CAPACITY", f"Column '{col.get('title', '')}' does not fit: cut ~{r['excess_words']} words", sid, role="column", excess_words=r["excess_words"]))
    if roles.get("statements") and by_role.get("statements"):
        r = zone_fit("statements", roles["statements"], by_role["statements"][0].box, profile)
        report["statements"] = r
        if not r["fits_floor"]:
            out.append(issue("error", "CONTENT_OVER_CAPACITY", "An executive-summary row does not fit: shorten the supporting text or drop a point", sid, role="statements"))
    # exhibit legibility budgets
    for ex in roles.get("exhibit") or []:
        d = ex.get("data") or {}
        vt = ex.get("type")
        if vt in ("table", "heatmap", "harvey_table", "scorecard"):
            nr = len(ex.get("rows") or [])
            nc = len(ex.get("columns") or ex.get("header") or [])
            if nr > profile.get("max_table_rows", 10):
                out.append(issue("warning", "DENSITY_TABLE_ROWS", f"Table with {nr} rows (budget {profile.get('max_table_rows', 10)}): show top rows + 'Other', or split", sid, rows=nr, split_at=profile.get("max_table_rows", 10)))
            if nc > profile.get("max_table_cols", 7):
                out.append(issue("warning", "DENSITY_TABLE_COLS", f"Table with {nc} columns (budget {profile.get('max_table_cols', 7)}): drop columns that do not prove the headline", sid))
            ez = next((z for z in by_role.get("exhibit", []) if True), None)
            if ez is not None:
                avail = ez.box.h - (EXHIBIT_HEADER_H if ex.get("title") else 0)
                min_row = tm.line_height_in(FONT_FLOOR["table_body"]) + 0.13
                if (nr + 1) * min_row > avail:
                    cap = int(avail / min_row) - 1
                    out.append(issue("error", "TABLE_OVER_CAPACITY", f"{nr} rows cannot fit in {avail:.2f} in even at the floor (max ≈{cap}); split or summarise", sid, rows=nr, split_at=max(3, cap)))
        cats = d.get("categories") or []
        if vt in ("column", "stacked_column", "line", "combo", "histogram") and cats and roles.get("exhibit"):
            ez = by_role.get("exhibit", [None])[0]
            if ez is not None:
                slot = ez.box.w / len(cats)
                longest = max(tm.text_width_in(str(c), type_style("chart_axis", profile)["size"]) for c in cats)
                if longest > 3 * slot:
                    out.append(issue("warning", "DENSITY_AXIS_LABELS", f"Category labels (up to {longest:.1f} in) will wrap into ≥3 lines in {slot:.2f} in slots: use bars or shorter labels", sid, fix={"path": "type", "value": "bar"} if vt == "column" else None))
        if vt == "gantt" and len(d.get("rows") or []) > 8:
            out.append(issue("warning", "DENSITY_GANTT_ROWS", "More than 8 workstreams on one roadmap: group them", sid))
        if vt in ("process", "value_chain") and len(d.get("steps") or []) > 6:
            out.append(issue("warning", "DENSITY_PROCESS_STEPS", f"{len(d['steps'])} process steps: group into ≤6 phases", sid))
        if vt in ("matrix_2x2", "portfolio") and len(d.get("items") or []) > 12:
            out.append(issue("warning", "DENSITY_MATRIX_ITEMS", "More than 12 items in a 2x2: label only the ones that matter", sid))
        if vt in ("tree", "driver_tree", "org_chart") and d.get("root"):
            from ..diagrams.diagrams import _depth, _leaves

            if _leaves(d["root"]) > 12 or _depth(d["root"]) > 4:
                out.append(issue("warning", "DENSITY_TREE", "Tree with >12 leaves or >4 levels: show 3 levels, move detail to backup", sid))
    # slide word budget
    total = len(words(slide.get("headline", "")))
    for role in ("commentary",):
        wc, _ = commentary_words(roles.get(role))
        total += wc
    for col in roles.get("column") or []:
        total += sum(len(words(t)) for t in _points_text(col.get("points")))
    for it in ((roles.get("statements") or {}).get("data") or {}).get("items") or []:
        sup = it.get("text") or it.get("points") or ""
        total += len(words(it.get("title", ""))) + sum(len(words(s)) for s in (sup if isinstance(sup, list) else [sup]))
    total += len(words(slide.get("takeaway", "")))
    budget = profile.get("max_words_per_slide", 110) * (1.4 if slide.get("kind") == "exec_summary" else 1.0)
    report["words"] = total
    if total > budget:
        out.append(issue("warning", "DENSITY_WORDS", f"{total} words on the slide (budget {int(budget)} for this deck profile)", sid, words=total))
    return out, report


def split_table_slide(slide: dict, split_at: int) -> list[dict]:
    """Mechanical split of a table slide into continuation slides (fallback)."""
    exs = slide_exhibits(slide)
    tbl = next((e for e in exs if e.get("rows")), None)
    if not tbl:
        return [slide]
    rows = tbl["rows"]
    chunks = [rows[i : i + split_at] for i in range(0, len(rows), split_at)]
    out = []
    for k, ch in enumerate(chunks):
        s = copy.deepcopy(slide)
        target = s["visual"] if isinstance(s.get("visual"), dict) and s["visual"].get("rows") else next(e for e in s.get("exhibits", []) if e.get("rows"))
        target["rows"] = ch
        if k > 0:
            s["id"] = f"{slide.get('id')}_{k + 1}"
            s["headline"] = slide.get("headline", "") + f" ({k + 1}/{len(chunks)})"
            s["_continuation_of"] = slide.get("id")
        elif len(chunks) > 1:
            s["headline"] = slide.get("headline", "") + f" (1/{len(chunks)})"
        out.append(s)
    return out
