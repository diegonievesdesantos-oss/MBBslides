"""Decision frame (protocol 1.1): what the storyline asks the client to DECIDE, and how defensible it is.

Added after the first expert storyline round (s1, development data). The expert preferred each
system for a different set of strengths, and a good storyline needs both:

    numeric discipline   figures reconcile; the gap to the target is stated, not hidden; every lever
                         is quantified separately; claims do not exceed what the data says
    governance           validation gates, approval criteria, tracking KPIs
    decision thinking    the current plan / budget is tested and, if it does not hold, shown why;
                         options are compared on what each costs; upper bounds and what must be
                         validated before committing are marked; the close is approvable proposals,
                         not assignments for later; problem or risk comes before the solution

The agent writes them into `storyline.json["decision"]`; these checks make each one observable. Only
arithmetic and grounding are hard (a lever total that does not add up is an ARITHMETIC_ERROR, an
impact no cited fact supports is an UNSUPPORTED_NUMBER); the rest are warnings for the critic pass.

    "decision": {
      "target":       {"value": 1.5, "unit": "PP", "facts": ["F0003"]},
      "levers":       [{"id": "L1", "statement": …, "impact": {"value": 0.9, "unit": "PP"}, "facts": [...],
                        "bound": "point|upper|lower|range", "validate": "what to test, by whom, by when"}],
      "identified":   {"value": 1.4, "unit": "PP"},
      "gap":          {"value": 0.1, "unit": "PP", "how_closed": …},
      "current_plan": {"statement": …, "verdict": "holds|partly|does_not_hold", "facts": [...], "cost_if_kept": {…}},
      "options":      [{"id": "O1", "statement": …, "cost": {"value": …, "unit": …}, "facts": [...], "chosen": true,
                        "cost_components": {"price": …, "switching": …, "risk": …}}],   (1.2: same keys for every option)
      "asks":         [{"statement": …, "type": "approve|reject|reallocate|stop|commission", "owner": …}],
      "gates":        [{"statement": …, "criterion": …, "when": …}],
      "kpis":         [{"name": …, "target": …, "cadence": …}]
    }
"""
from __future__ import annotations

import re

from .grounding import ground_numbers

APPROVABLE = {"approve", "reject", "reallocate", "stop", "decide"}
PROBLEM_ROLES = {"problem", "risk", "situation", "complication", "diagnosis", "problem_diagnosis", "context"}
SOLUTION_ROLES = {"solution", "recommendation", "lever", "levers", "plan", "action", "decision"}
HEDGE = re.compile(r"\b(up to|about|around|approximately|roughly|at most|estimated|potential|if|hasta|como máximo|cerca de|aproximadamente|unos|potencial|si)\b", re.I)
UNIT_FMT = {"PCT": "{v}%", "PP": "{v} pp", "BPS": "{v} bps", "EUR": "€{v}", "EUR_K": "€{v}K", "EUR_M": "€{v}M", "EUR_BN": "€{v}bn",
            "USD": "${v}", "USD_K": "${v}K", "USD_M": "${v}M", "USD_BN": "${v}bn", "GBP_M": "£{v}M"}


def _issue(level, code, ref, message, hard=False):
    return {"level": level, "code": code, "artifact": "storyline.json", "ref": ref, "message": message, "hard": hard}


def quantity_text(q: dict) -> str:
    v = f"{float(q['value']):g}"
    return UNIT_FMT.get((q.get("unit") or "").upper(), "{v}").format(v=v)


def _dec(v) -> int:
    s = f"{float(v):g}"
    return len(s.split(".")[1]) if "." in s else 0


def _same_unit(*qs) -> bool:
    return len({(q.get("unit") or "").upper() for q in qs}) == 1


def check_decision(sl: dict | None, facts: dict, project: dict | None = None) -> list[dict]:
    if not sl:
        return []
    d = sl.get("decision")
    if not d:
        return [_issue("warning", "DECISION_FRAME_MISSING", "decision", "no decision frame: target, levers, current plan, options, asks, gates and KPIs are not stated")]
    out = []
    target, identified, gap = d.get("target"), d.get("identified"), d.get("gap")
    levers = d.get("levers") or []

    # numeric discipline: every lever quantified and grounded in what it cites
    for lv in levers:
        ref = lv.get("id") or lv.get("statement", "")[:30]
        imp = lv.get("impact")
        if not imp or imp.get("value") is None:
            out.append(_issue("warning", "LEVER_UNQUANTIFIED", ref, "lever without a quantified impact: a CFO cannot defend it"))
            continue
        cited = [facts[f] for f in lv.get("facts") or [] if f in facts]
        unknown = [f for f in lv.get("facts") or [] if f not in facts]
        if unknown:
            out.append(_issue("error", "UNKNOWN_FACT", ref, f"cites {', '.join(unknown)}"))
        for g in ground_numbers(quantity_text(imp), cited):
            if g["status"] == "unsupported":
                out.append(_issue("error", "UNSUPPORTED_NUMBER", ref, f"lever impact {g['number']} not grounded in the lever's facts", hard=True))
            elif g["status"] == "assumption" and not lv.get("validate"):
                out.append(_issue("warning", "UNCERTAINTY_UNMARKED", ref, f"impact {g['number']} rests on an assumption: say what must be validated before committing"))
        if lv.get("bound") in ("upper", "range") and not lv.get("validate"):
            out.append(_issue("warning", "UNCERTAINTY_UNMARKED", ref, "upper-bound / range impact without what to validate before committing"))

    # the levers add up to what is claimed, and the gap to the target is stated
    q = [lv["impact"] for lv in levers if (lv.get("impact") or {}).get("value") is not None]
    if identified and q and _same_unit(identified, *q):
        s = sum(float(x["value"]) for x in q)
        tol = 10 ** -max(_dec(x["value"]) for x in q + [identified]) + 1e-9  # one unit of the last digit shown
        if abs(s - float(identified["value"])) > tol:
            out.append(_issue("error", "ARITHMETIC_ERROR", "identified", f"levers sum to {s:g} but identified is {float(identified['value']):g}", hard=True))
    if target and identified and _same_unit(target, identified):
        diff = float(target["value"]) - float(identified["value"])
        if diff > 10 ** -max(_dec(target["value"]), _dec(identified["value"])) / 2:
            if not gap:
                out.append(_issue("warning", "GAP_NOT_STATED", "gap", f"identified {quantity_text(identified)} vs target {quantity_text(target)}: state the gap and how it closes"))
            elif _same_unit(gap, target):
                tol = 10 ** -max(_dec(target["value"]), _dec(identified["value"]), _dec(gap["value"])) + 1e-9
                if abs(abs(float(gap["value"])) - diff) > tol:
                    out.append(_issue("error", "ARITHMETIC_ERROR", "gap", f"gap {float(gap['value']):g} ≠ target − identified = {diff:g}", hard=True))
    elif target and not identified and levers:
        out.append(_issue("warning", "GAP_NOT_STATED", "identified", "a target is set but the levers' total is not stated"))

    # no overclaiming: an upper bound is not a promise
    gt = sl.get("governing_thought", "")
    if identified and any(lv.get("bound") in ("upper", "range") for lv in levers):
        num = f"{float(identified['value']):g}"
        for m in re.finditer(re.escape(num), gt):
            if not HEDGE.search(gt[max(0, m.start() - 25):m.start()]):
                out.append(_issue("warning", "OVERCLAIM_BOUND", "governing_thought", f"{num} rests on upper-bound levers but is stated as certain"))
                break

    # decision thinking
    cp = d.get("current_plan")
    if not cp:
        out.append(_issue("warning", "CURRENT_PLAN_NOT_TESTED", "current_plan", "the plan / budget in force is not tested: does it hold, and what does keeping it cost?"))
    elif cp.get("verdict") in ("partly", "does_not_hold") and not (cp.get("facts") or cp.get("cost_if_kept")):
        out.append(_issue("warning", "CURRENT_PLAN_UNSUPPORTED", "current_plan", "says the current plan does not hold without the facts or cost that show it"))
    opts = d.get("options") or []
    if len(opts) < 2:
        out.append(_issue("warning", "OPTIONS_NOT_COMPARED", "options", "fewer than two options: compare alternatives (including keeping the current plan) on what each costs"))
    for o in opts:
        if not o.get("cost"):
            out.append(_issue("warning", "OPTION_UNCOSTED", o.get("id") or o.get("statement", "")[:30], "option without a cost / impact"))
    # 1.2 (s2): options compared on the SAME basis — a risk or cost charged to one option and not to
    # another it also applies to decides the comparison (packaging: stoppage risk on 100% only, not on 70/30)
    comps = {o.get("id") or str(n): set((o.get("cost_components") or {}).keys()) for n, o in enumerate(opts)}
    if len(opts) >= 2:
        if not any(comps.values()):
            out.append(_issue("info", "OPTION_COMPONENTS_MISSING", "options", "list each option's cost_components (price, switching, risk, …) so they are compared on the same basis"))
        else:
            allc = set().union(*comps.values())
            for oid, c in comps.items():
                if c != allc:
                    out.append(_issue("warning", "OPTIONS_DIFFERENT_BASIS", oid, f"missing {', '.join(sorted(allc - c))} that another option is charged: "
                                      "apply each cost and risk to every option it touches (0 if it truly does not apply)"))
    asks = d.get("asks") or []
    if not asks:
        out.append(_issue("warning", "ASK_MISSING", "asks", "no decision asked of the audience"))
    elif not any(a.get("type") in APPROVABLE for a in asks):
        out.append(_issue("warning", "ASK_DEFERRED", "asks", "the close is assignments for later, not proposals the audience can approve today"))
    for a in asks:
        if a.get("type") in APPROVABLE and not a.get("owner"):
            out.append(_issue("info", "ASK_NO_OWNER", a.get("statement", "")[:30], "who carries it out?"))

    # governance
    if not d.get("gates"):
        out.append(_issue("warning", "GATES_MISSING", "gates", "no validation gate / approval criterion before the money is committed"))
    if not d.get("kpis"):
        out.append(_issue("warning", "KPIS_MISSING", "kpis", "no tracking KPI"))

    # narrative order: the problem or risk before the solution
    roles = [(k.get("role") or "").lower() for k in sl.get("key_line") or []]
    p = next((i for i, r in enumerate(roles) if r in PROBLEM_ROLES), None)
    s = next((i for i, r in enumerate(roles) if r in SOLUTION_ROLES), None)
    if s is not None and (p is None or s < p):
        out.append(_issue("warning", "SOLUTION_BEFORE_PROBLEM", "key_line", "the solution comes before the problem or risk it answers"))
    # the storyline stands alone with data
    kl = sl.get("key_line") or []
    if kl and sum(1 for k in kl if re.search(r"\d", k.get("message", ""))) * 2 < len(kl):
        out.append(_issue("info", "KEYLINE_WITHOUT_NUMBERS", "key_line", "most key-line points carry no number: the argument should stand on data without the deck"))
    return out


def decision_summary(sl: dict | None, issues: list[dict]) -> dict:
    """Benchmark dimension: which decision-frame elements are present (no score)."""
    d = (sl or {}).get("decision") or {}
    codes = {i["code"] for i in issues if i["artifact"] == "storyline.json"}
    lv = d.get("levers") or []
    return {"frame": bool(d), "levers": len(lv), "levers_quantified": sum(1 for x in lv if (x.get("impact") or {}).get("value") is not None),
            "gap_stated": bool(d.get("gap")) or (bool(d) and "GAP_NOT_STATED" not in codes and bool(d.get("target"))),
            "current_plan_tested": bool(d.get("current_plan")), "options_costed": sum(1 for o in d.get("options") or [] if o.get("cost")),
            "approvable_asks": sum(1 for a in d.get("asks") or [] if a.get("type") in APPROVABLE),
            "deferred_asks": sum(1 for a in d.get("asks") or [] if a.get("type") not in APPROVABLE),
            "bounds_marked": sum(1 for x in lv if x.get("bound") in ("upper", "range", "lower")), "gates": len(d.get("gates") or []),
            "kpis": len(d.get("kpis") or []), "problem_first": "SOLUTION_BEFORE_PROBLEM" not in codes,
            "warnings": sorted(c for c in codes if c in DECISION_CODES)}


DECISION_CODES = {"DECISION_FRAME_MISSING", "LEVER_UNQUANTIFIED", "UNCERTAINTY_UNMARKED", "GAP_NOT_STATED", "OVERCLAIM_BOUND", "CURRENT_PLAN_NOT_TESTED",
                  "CURRENT_PLAN_UNSUPPORTED", "OPTIONS_NOT_COMPARED", "OPTION_UNCOSTED", "ASK_MISSING", "ASK_DEFERRED", "GATES_MISSING", "KPIS_MISSING",
                  "SOLUTION_BEFORE_PROBLEM", "KEYLINE_WITHOUT_NUMBERS", "OPTIONS_DIFFERENT_BASIS", "OPTION_COMPONENTS_MISSING"}


# ── the same signals in any storyline.md (heuristic, bilingual) ────────────────────────────────

TEXT_SIGNALS = {
    "gap_to_target": r"\b(gap|shortfall|remaining|short of|vs (?:the )?[\d.,]+ ?(?:pp|%)? target|brecha|faltan?|restante|hasta el objetivo|frente al objetivo)\b",
    "upper_bound": r"\b(upper bound|up to|at most|ceiling|cota superior|como máximo|hasta un máximo)\b",
    "to_validate": r"\b(validat\w*|confirm\w*|test\w*|pilot\w*|valid\w*|comprob\w*|prueba\w*|piloto)\b",
    "gate": r"\b(gate[ds]?|go/no-go|approval criteri\w*|hurdle|criterio de aprobación|umbral)\b",
    "kpi_tracking": r"\b(kpis?|track\w*|monitor\w*|report \w+ (?:monthly|quarterly)|seguimiento|mensual|trimestral)\b",
    "current_plan_challenged": r"\b(do not approve|reject|not approve|reset|replace the|no aprobar|rechaz\w*|posponer|budget(?:ed)? .{0,40}(?:would|cost)|presupuesto .{0,40}(?:costar|restar))\b",
    "options_costed": r"\b(option|alternative|instead of|versus|opción|alternativa|en lugar de)\b",
    "deferred_ask": r"\b(commission|study|analy[sz]e|estimate the|further analysis|estudiar|analizar|estimar el)\b",
}


def decision_signals_text(md: str) -> dict:
    """Counts of decision-frame cues in a storyline.md, for comparing systems that do not write
    `storyline.json`. Lexical cues, not verdicts: a reader decides whether they are well used."""
    low = md.lower()
    return {k: len(re.findall(p, low, re.I)) for k, p in TEXT_SIGNALS.items()}
