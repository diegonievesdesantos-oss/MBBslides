"""Visual reasoning engine: message → visual encoding.

Step 0 (from the comparison gate): name what the slide SAYS (message_type).
Step 1: read the SHAPE of the evidence (categories, periods, series, parts of a
whole, negatives, steps, points, rows…).
Step 2: score candidate visuals; every score carries its reason, so the choice
is explainable ("waterfall, not stacked column, because the message is what
explains the change between two totals").

`recommend()` ranks candidates. `validate()` critiques an explicit choice
against the message and the data (pie with 9 slices, line with 3 points,
column with long labels, ranking not sorted, …) and proposes a fix.
"""
from __future__ import annotations

import re

from ..spec import MESSAGE_TYPES, issue

TIME_RE = re.compile(r"^(?:FY|H[12]|Q[1-4]|CY)?\s*'?\d{2,4}(?:[-/ ]?(?:Q[1-4]|H[12]|\d{2}))?[AEFPB]?$|^(?:Q[1-4]|H[12])\s*'?\d{2,4}[AEFB]?$|^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|ene|abr|ago|dic)\w*\.?\s*'?\d{0,4}$", re.IGNORECASE)

# message_type → [(visual, base score, reason)]
BASE: dict[str, list[tuple[str, int, str]]] = {
    "single_number": [("kpi", 90, "one figure is the message: show it big with its delta"), ("statement", 60, "a single number framed as a statement"), ("column", 35, "only if the number needs its history")],
    "ranking": [("bar", 90, "ranking reads best as sorted horizontal bars (labels stay horizontal)"), ("column", 60, "columns work for ≤7 short labels"), ("table", 45, "use a table only when several attributes per item matter")],
    "composition": [("stacked_bar", 70, "parts of a whole on one bar keep a common baseline"), ("bar", 75, "sorted bars compare parts more precisely than angles"), ("donut", 55, "donut only for ≤5 parts where one share is the point"), ("pie", 45, "pie only for 2-4 parts"), ("mekko", 50, "if the whole also varies by a second dimension"), ("table", 35, "precise values")],
    "composition_change": [("stacked_column", 85, "stacks over time show total and mix together"), ("stacked_100", 80, "100% stacks isolate the mix shift"), ("area", 55, "stacked area for long series"), ("line", 50, "lines per component when totals do not matter")],
    "trend": [("column", 80, "few periods: columns make each period's level explicit"), ("line", 85, "many periods or several series: lines show direction"), ("combo", 70, "a level and a rate over the same periods"), ("slope", 60, "two points in time for several items"), ("area", 45, "volume over time")],
    "change_bridge": [("waterfall", 95, "decomposes the change between two totals into its drivers"), ("bridge", 90, "waterfall with intermediate subtotals"), ("bar", 45, "drivers ranked by size, no start/end")],
    "distribution": [("histogram", 90, "frequency by bucket"), ("column", 60, "buckets as categories"), ("scatter", 40, "individual observations")],
    "correlation": [("scatter", 90, "two measures per item: position shows the relationship"), ("bubble", 85, "add a third measure as size"), ("line", 30, "only for two series over time")],
    "positioning": [("matrix_2x2", 90, "items against two strategic dimensions with named quadrants"), ("portfolio", 85, "2x2 with bubble size (e.g. revenue)"), ("bubble", 80, "numeric axes with size"), ("scatter", 70, "numeric axes without size")],
    "comparison": [("harvey_table", 85, "options × criteria with qualitative ratings"), ("table", 80, "entities × numeric attributes"), ("heatmap", 75, "grid of numbers where hot spots are the message"), ("text_columns", 70, "2-4 options described on the same dimensions"), ("bar", 55, "one attribute across entities"), ("scorecard", 50, "status by entity")],
    "segmentation": [("mekko", 90, "segment size (width) × share/mix (height) in one exhibit"), ("stacked_100", 70, "mix by segment when sizes are not the point"), ("heatmap", 60, "attractiveness grid"), ("bubble", 55, "size × growth × share"), ("table", 45, "segment profiles")],
    "sequence": [("process", 90, "ordered steps with owners/outputs"), ("value_chain", 75, "end-to-end activity chain"), ("flow", 65, "branching or parallel steps"), ("timeline", 40, "if the steps are dated")],
    "plan": [("gantt", 90, "workstreams × time with milestones"), ("timeline", 80, "dated milestones without durations"), ("roadmap", 85, "phased plan with workstreams"), ("table", 40, "actions / owners / dates")],
    "hierarchy": [("driver_tree", 88, "value decomposed into drivers (with numbers)"), ("tree", 85, "MECE issue tree"), ("org_chart", 85, "reporting lines / roles"), ("pyramid", 55, "layered priorities with a foundation")],
    "geography": [("tile_map", 80, "geography is the message (spatial pattern)"), ("bar", 80, "ranked bars by region are usually more precise"), ("heatmap", 55, "regions × metrics")],
    "causality": [("cause_effect", 90, "causes → the effect → its consequences: arrows mean 'causes', not 'comes next'"), ("driver_tree", 70, "the effect decomposed arithmetically into drivers"), ("flow", 55, "a chain of causes with branches")],
    "flow": [("funnel", 90, "volumes lost between stages"), ("journey", 85, "stages × lanes (actions, touchpoints, pain points)"), ("flow", 80, "nodes and transfers")],
    "structure": [("operating_model", 90, "layers of the model with the changes highlighted"), ("layers", 85, "stacked layers"), ("architecture", 85, "system layers and components"), ("org_chart", 50, "if the structure is people")],
    "status": [("scorecard", 90, "RAG status by item"), ("table", 70, "status with owners and dates"), ("gantt", 60, "plan vs actual")],
    "argument": [("bullets", 75, "a few reasons, bold lead-ins"), ("text_columns", 75, "parallel reasons with equal weight"), ("statements", 70, "claims with proof"), ("statement", 55, "a single pivotal message")],
    "recommendation": [("statements", 80, "numbered recommendations with rationale"), ("table", 80, "actions with owner, timing, impact"), ("text_columns", 70, "2-4 recommendations side by side")],
}


def data_shape(ex: dict) -> dict:
    d = ex.get("data") or {}
    shape: dict = {}
    cats = [str(c) for c in d.get("categories") or []]
    series = d.get("series") or []
    if cats:
        shape["n_categories"] = len(cats)
        shape["time_axis"] = sum(bool(TIME_RE.match(c.strip())) for c in cats) >= max(2, int(0.7 * len(cats)))
        shape["avg_label_len"] = sum(len(c) for c in cats) / len(cats)
        shape["max_label_len"] = max(len(c) for c in cats)
    if series:
        shape["n_series"] = len(series)
        vals = [v for s in series for v in s.get("values", []) if isinstance(v, (int, float))]
        shape["has_negative"] = any(v < 0 for v in vals)
        if len(series) == 1 and vals:
            tot = sum(vals)
            shape["parts_of_100"] = abs(tot - 100) < 1.5 or abs(tot - 1) < 0.02
        shape["secondary_axis"] = any(s.get("axis") == "secondary" for s in series)
        if cats and len(series) == 1:
            v = [x for x in series[0].get("values", []) if isinstance(x, (int, float))]  # gaps (None / n/a) do not count
            shape["sorted"] = v == sorted(v, reverse=True) or v == sorted(v)
    if d.get("steps"):
        shape["n_steps"] = len(d["steps"])
        shape["has_subtotals"] = sum(1 for s in d["steps"] if s.get("type") in ("total", "subtotal")) > 2
    if d.get("points"):
        shape["n_points"] = len(d["points"])
        shape["has_size"] = any("size" in q for q in d["points"])
    if ex.get("rows"):
        shape["n_rows"] = len(ex["rows"])
        shape["n_cols"] = len(ex.get("columns") or ex.get("header") or (ex["rows"][0] if isinstance(ex["rows"][0], list) else ex["rows"][0].get("cells", [])))
    for k in ("events", "stages", "levels", "layers", "nodes"):
        if d.get(k):
            shape[f"n_{k}"] = len(d[k])
    if d.get("rows") and d.get("periods"):
        shape["n_workstreams"] = len(d["rows"])
    if d.get("root"):
        shape["tree"] = True
    return shape


def recommend(message_type: str, ex: dict | None = None, profile: dict | None = None) -> list[dict]:
    ex = ex or {}
    profile = profile or {}
    sh = data_shape(ex)
    cands = {v: [s, [r]] for v, s, r in BASE.get(message_type, BASE["argument"])}

    def adj(v, delta, why):
        if v in cands:
            cands[v][0] += delta
            cands[v][1].append(why)
        elif delta > 0:
            cands[v] = [delta, [why]]

    n = sh.get("n_categories", 0)
    k = sh.get("n_series", 0)
    if n:
        if sh.get("max_label_len", 0) > 14 or n > 9:
            adj("column", -30, "labels are long / many categories: columns would wrap or crowd")
            adj("stacked_column", -15, "long labels crowd a column axis")
            adj("bar", +15, "horizontal bars keep long labels readable")
        if sh.get("time_axis"):
            adj("bar", -40, "time runs left→right; do not put periods on a vertical axis")
            adj("stacked_bar", -30, "time runs left→right")
            if n > 8 or k >= 3:
                adj("line", +15, f"{n} periods / {k} series: a line shows direction without clutter")
                adj("column", -15, "too many periods for columns")
            elif n <= 3 and k >= 2:
                adj("slope", +10, "two/three periods for several items")
            if n < 4:
                adj("line", -30, f"only {n} periods: a line suggests a trend the data cannot show")
        if sh.get("has_negative"):
            for v in ("pie", "donut", "stacked_100", "mekko", "area"):
                adj(v, -60, "negative values cannot be parts of a whole")
        if k == 1 and not sh.get("parts_of_100") and message_type == "composition":
            adj("pie", -25, "values do not sum to a whole")
            adj("donut", -25, "values do not sum to a whole")
        if n > 5:
            adj("pie", -60, f"{n} slices are unreadable as angles")
            adj("donut", -50, f"{n} slices are unreadable as angles")
        if k > profile.get("max_chart_series", 4):
            adj("column", -20, f"{k} series exceed the {profile.get('max_chart_series', 4)}-series budget: split or small multiples")
            adj("line", -10, "many series: highlight one, grey the rest")
        if sh.get("secondary_axis"):
            adj("combo", +30, "a level and a rate share the category axis")
    if sh.get("has_subtotals"):
        adj("bridge", +10, "intermediate subtotals present")
    if sh.get("n_points") and sh.get("has_size"):
        adj("bubble", +10, "points carry a size measure")
        adj("portfolio", +5, "points carry a size measure")
    if sh.get("n_rows", 0) > profile.get("max_table_rows", 10):
        adj("table", -20, f"{sh['n_rows']} rows exceed the table budget: summarise or split")
    if sh.get("n_workstreams"):
        adj("gantt", +10, "workstreams with periods")
    if sh.get("n_events") and not sh.get("n_workstreams"):
        adj("timeline", +15, "dated events without durations")
    ranked = sorted(({"visual": v, "score": max(0, min(100, s)), "reasons": r} for v, (s, r) in cands.items()), key=lambda d: -d["score"])
    return ranked


def choose(slide: dict, ex: dict, profile: dict | None = None) -> tuple[str, dict]:
    """Resolve `type: auto` for an exhibit. Returns (visual, rationale)."""
    mt = slide.get("message_type") or infer_message_type(slide, ex)
    ranked = recommend(mt, ex, profile)
    feasible = [r for r in ranked if _feasible(r["visual"], ex)]
    best = (feasible or ranked)[0]
    alt = [r for r in (feasible or ranked)[1:3]]
    rationale = {
        "message_type": mt,
        "chosen": best["visual"],
        "why": "; ".join(best["reasons"]),
        "not": [f"{a['visual']} (score {a['score']}): {a['reasons'][0]}" for a in alt],
    }
    return best["visual"], rationale


def _feasible(visual: str, ex: dict) -> bool:
    """Can the given data feed this visual?"""
    d = ex.get("data") or {}
    need = {
        "waterfall": "steps", "bridge": "steps", "scatter": "points", "bubble": "points", "matrix_2x2": "items", "portfolio": "items",
        "process": "steps", "value_chain": "steps", "timeline": "events", "gantt": "rows", "roadmap": "rows", "tree": "root",
        "driver_tree": "root", "org_chart": "root", "funnel": "stages", "pyramid": "levels", "layers": "layers",
        "operating_model": "layers", "architecture": "layers", "journey": "stages", "flow": "nodes", "cause_effect": "causes", "causal_chain": "causes", "mekko": "columns",
        "segmentation": "columns", "tile_map": "values",
    }
    if visual in need:
        return bool(d.get(need[visual]) or (visual == "tile_map" and d.get("tiles")))
    if visual in ("table", "heatmap", "harvey_table", "scorecard"):
        return bool(ex.get("rows"))
    if visual in ("kpi",):
        return bool(d.get("items") or ex.get("items"))
    if visual in ("bullets", "statements", "text_columns", "statement", "quote"):
        return bool(d.get("items") or d.get("points") or d.get("text"))
    return bool(d.get("categories") and d.get("series"))


def infer_message_type(slide: dict, ex: dict) -> str:
    sh = data_shape(ex)
    if sh.get("n_steps") and (ex.get("data") or {}).get("steps") and any(s.get("type") in ("total", "subtotal") for s in ex["data"]["steps"]):
        return "change_bridge"
    if sh.get("n_points"):
        return "positioning" if (ex.get("data") or {}).get("items") else "correlation"
    if sh.get("n_workstreams") or sh.get("n_events"):
        return "plan"
    if sh.get("tree"):
        return "hierarchy"
    if sh.get("n_categories"):
        if sh.get("time_axis"):
            return "composition_change" if sh.get("n_series", 1) > 1 and ex.get("type") in ("stacked_column", "stacked_100") else "trend"
        return "composition" if sh.get("parts_of_100") else "ranking"
    if sh.get("n_rows"):
        return "comparison"
    return "argument"


def validate(slide: dict, ex: dict, profile: dict | None = None) -> list[dict]:
    """Critique an explicit visual choice. Each issue may carry a `fix` patch."""
    profile = profile or {}
    sid = slide.get("id")
    vt = ex.get("type")
    sh = data_shape(ex)
    out: list[dict] = []
    mt = slide.get("message_type")
    if mt and mt not in MESSAGE_TYPES:
        return out
    n, k = sh.get("n_categories", 0), sh.get("n_series", 0)
    if vt in ("pie", "donut") and n > 5:
        out.append(issue("warning", "VIS_PIE_SLICES", f"{vt} with {n} slices: use sorted bars", sid, fix={"path": "type", "value": "bar"}))
    if vt in ("pie", "donut") and sh.get("has_negative"):
        out.append(issue("error", "VIS_PIE_NEGATIVE", "Pie/donut with negative values", sid, fix={"path": "type", "value": "bar"}))
    if vt == "line" and n and n < 4:
        out.append(issue("warning", "VIS_LINE_FEW_POINTS", f"Line with {n} points implies a trend; use columns", sid, fix={"path": "type", "value": "column"}))
    if vt in ("column", "stacked_column") and (sh.get("max_label_len", 0) > 16 or n > 12) and not sh.get("time_axis"):
        out.append(issue("warning", "VIS_COLUMN_LABELS", "Long or many category labels on a column chart: use horizontal bars", sid, fix={"path": "type", "value": "bar" if vt == "column" else "stacked_bar"}))
    if vt in ("bar", "stacked_bar") and sh.get("time_axis"):
        out.append(issue("warning", "VIS_TIME_VERTICAL", "Time on a vertical axis; time should run left→right", sid, fix={"path": "type", "value": "column" if vt == "bar" else "stacked_column"}))
    if vt in ("stacked_column", "stacked_bar", "stacked_100") and k > 5:
        out.append(issue("warning", "VIS_STACK_SEGMENTS", f"{k} stacked segments: group the tail into 'Other'", sid))
    if k > profile.get("max_chart_series", 4) and vt not in ("stacked_column", "stacked_bar", "stacked_100", "area", "table", "heatmap"):
        out.append(issue("warning", "VIS_TOO_MANY_SERIES", f"{k} series exceed the budget ({profile.get('max_chart_series', 4)}): highlight one, grey or drop the rest", sid))
    if n > profile.get("max_chart_categories", 12) and vt in ("column", "bar", "stacked_column", "stacked_bar"):
        out.append(issue("warning", "VIS_TOO_MANY_CATEGORIES", f"{n} categories exceed the budget ({profile.get('max_chart_categories', 12)}): top-N + 'Other'", sid))
    if vt == "bar" and (mt == "ranking" or not mt) and k == 1 and not sh.get("sorted") and not ex.get("sort"):
        out.append(issue("info", "VIS_UNSORTED", "Ranking bars are easier to read sorted", sid, fix={"path": "sort", "value": "desc"}))
    if vt in ("waterfall", "bridge") and not (ex.get("data") or {}).get("steps"):
        out.append(issue("error", "VIS_DATA_MISMATCH", "Waterfall needs data.steps", sid))
    if vt == "combo" and not sh.get("secondary_axis"):
        out.append(issue("warning", "VIS_COMBO_AXIS", "Combo chart without a secondary-axis series: use a column chart", sid, fix={"path": "type", "value": "column"}))
    if mt:
        ranked = recommend(mt, ex, profile)
        scores = {r["visual"]: r["score"] for r in ranked}
        top = ranked[0]
        if vt not in scores:
            out.append(issue("info", "VIS_OFF_MESSAGE", f"'{vt}' is not a usual encoding for a {mt} message; consider '{top['visual']}' ({top['reasons'][0]})", sid))
        elif scores[vt] + 30 < top["score"] and _feasible(top["visual"], ex):
            out.append(issue("info", "VIS_BETTER_OPTION", f"'{top['visual']}' fits a {mt} message better than '{vt}' ({top['reasons'][0]})", sid))
    if ex.get("type") in ("line", "column", "bar", "stacked_column", "combo") and not ex.get("title"):
        out.append(issue("info", "VIS_NO_TITLE", "Exhibit without title/unit: state what is measured and in which unit", sid))
    return out
