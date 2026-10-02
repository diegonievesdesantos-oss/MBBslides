"""Deterministic checks of every reasoning artifact, hard factuality gates and stopping criteria.

Levels: `error` blocks, `warning` asks for attention, `info` is context. HARD factual failures
(`hard: True`) block the deck whatever else passes:

    FACT_FABRICATED          a fact whose value cannot be found in the sources it cites
    UNSUPPORTED_NUMBER       a number in an insight / governing thought / headline that the cited
                             facts do not ground (directly or by one bounded operation)
    WRONG_SOURCE             a slide names a source file that none of its cited facts come from
    ARITHMETIC_ERROR         a derived fact whose stated result does not follow from its operands
    CONTRADICTED_AS_FACT     an insight / key-line point built on a REJECTED hypothesis

Quality checks (not hard): insight novelty vs the source text, causal overclaim, materiality and
decision relevance stated, governing-thought candidates compared, key-line MECE overlap, orphan
or duplicated slides, information economy. They are heuristics: a warning is a question for the
critic pass, not a verdict.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import PROTOCOL_VERSION
from .analysis import check_analyses
from .decision import check_decision
from .grounding import ground_numbers
from .rules15 import check_assumptions_in_summary, check_decision_15, check_discarded, check_partner_checklist, check_rejected_revived

CAUSAL = re.compile(r"\b(because|driven by|due to|caused by|causes|explains?|explained by|as a result of|porque|debido a|impulsad[oa] por|explica|causad[oa])\b", re.I)
STOP = set("the a an of to in on for and or with by from is are was were be this that it its as at than vs de la el los las y o en por con del al un una que se".split())


def _issue(level, code, artifact, ref, message, hard=False):
    return {"level": level, "code": code, "artifact": artifact, "ref": ref, "message": message, "hard": hard}


def _load(work: Path, name: str):
    f = work / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúñü0-9]+", (t or "").lower()) if w not in STOP and len(w) > 2}


def _jaccard(a: str, b: str) -> float:
    x, y = _words(a), _words(b)
    return len(x & y) / len(x | y) if x | y else 0.0


# ── project / business question ──────────────────────────────────────────────────────────────────

REQUIRED_PROJECT = ("audience", "decision", "question")


def check_project(p: dict | None) -> list[dict]:
    if not p:
        return [_issue("error", "PROJECT_MISSING", "project.json", None, "No business question object: storyline generation must not start without one")]
    out = [_issue("error", "PROJECT_FIELD", "project.json", k, f"'{k}' is required") for k in REQUIRED_PROJECT if not p.get(k)]
    for k in ("horizon", "scope"):
        if not p.get(k):
            out.append(_issue("warning", "PROJECT_FIELD", "project.json", k, f"'{k}' not set: state it or mark it inferred"))
    for k in p.get("inferred") or []:
        out.append(_issue("info", "PROJECT_INFERRED", "project.json", k, f"'{k}' was inferred, not given: confirm it at the storyline checkpoint"))
    q = str(p.get("question", ""))
    if q and not q.strip().endswith("?"):
        out.append(_issue("warning", "PROJECT_QUESTION", "project.json", "question", "The business question should be a question"))
    return out


# ── facts ────────────────────────────────────────────────────────────────────────────────────────

def check_facts(fm: dict | None, sources_dir: Path | None = None, work_dir: Path | None = None) -> list[dict]:
    if not fm:
        return [_issue("error", "FACTS_MISSING", "facts.json", None, "No fact model: run `cpe reason facts`")]
    out, ids = [], set()
    by_id = {f["id"]: f for f in fm["facts"]}
    source_numbers = None
    if sources_dir and Path(sources_dir).exists():
        # v1.8: against the RAW content of each file (every way a number can be read), not a fresh
        # re-extraction — an extractor upgrade must not turn an old, true fact into a fabrication
        source_numbers = {p.name: raw_numbers(p) for p in Path(sources_dir).rglob("*") if p.is_file() and not p.name.startswith(".")}
    if work_dir is not None and source_numbers is not None:
        from .analysis import output_tables

        source_numbers.update({name: raw_numbers(p) for p, name in output_tables(work_dir)})
    for f in fm["facts"]:
        if f["id"] in ids:
            out.append(_issue("error", "FACT_DUPLICATE_ID", "facts.json", f["id"], "duplicate fact id"))
        ids.add(f["id"])
        if not (f.get("source") or {}).get("file"):
            out.append(_issue("error", "FACT_UNTRACEABLE", "facts.json", f["id"], "fact without a source file", hard=True))
        if f.get("fact_type") == "derived_change" or f.get("derived_from"):
            ops = [by_id.get(x) for x in f.get("derived_from") or []]
            if None in ops:
                out.append(_issue("error", "FACT_LINEAGE", "facts.json", f["id"], "derived fact cites a fact that does not exist", hard=True))
            elif len(ops) == 2 and f.get("operation") == "last − first":
                d = ops[1]["values"][0]["value"] - ops[0]["values"][0]["value"]
                if abs(f["values"][0]["value"] - d) > 1e-6 * max(1, abs(d)):
                    out.append(_issue("error", "ARITHMETIC_ERROR", "facts.json", f["id"], f"stated change {f['values'][0]['value']} ≠ {d}", hard=True))
        elif source_numbers is not None:
            have = source_numbers.get((f.get("source") or {}).get("file"), set())
            for v in f.get("values") or []:
                if round(abs(float(v["value"])), 6) not in have:
                    out.append(_issue("error", "FACT_FABRICATED", "facts.json", f["id"], f"value {v['value']:g} is not in {f['source'].get('file')}", hard=True))
    return out


def raw_numbers(path: Path) -> set[float]:
    """Every number written in a source file, under every reading of its separators ("1.444" →
    1.444 and 1444; "3,2" → 3.2; "30.000" → 30000), plus typed spreadsheet cells. Absolute values."""
    texts, out = [], set()
    suf = path.suffix.lower()
    try:
        if suf in (".xlsx", ".xlsm"):
            import openpyxl

            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            for ws in wb.worksheets:
                for r in ws.iter_rows(values_only=True):
                    for c in r:
                        if isinstance(c, (int, float)) and not isinstance(c, bool):
                            out.add(round(abs(float(c)), 6))
                        elif c is not None:
                            texts.append(str(c))
        elif suf == ".pdf":
            import pymupdf

            texts += [pg.get_text() for pg in pymupdf.open(str(path))]
        elif suf in (".docx", ".pptx"):
            import zipfile

            with zipfile.ZipFile(path) as z:
                texts += [re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace")) for n in z.namelist() if n.endswith(".xml")]
        elif suf in (".csv", ".tsv"):
            import csv

            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            from ..ingest.readers import sniff_dialect

            dialect = sniff_dialect(raw)
            texts += [c for row in csv.reader(raw.splitlines(), dialect) for c in row]
        else:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:  # unreadable source: nothing can be verified against it
        return out
    for t in texts:
        for tok in re.findall(r"\d[\d.,]*\d|\d", t):
            for cand in (tok.replace(",", ""), tok.replace(".", "").replace(",", "."), tok.replace(",", "."), tok.replace(".", "")):
                try:
                    out.add(round(abs(float(cand)), 6))
                except ValueError:
                    pass
    return out


# ── computed facts: the agent's arithmetic, recomputed deterministically ───────────────────────────

SCALE_OF = {"": 1.0, "K": 1e3, "M": 1e6, "BN": 1e9}


def _scale(unit: str) -> tuple[str, float]:
    kind, _, sc = (unit or "").upper().partition("_")
    return kind, SCALE_OF.get(sc, 1.0)


def _safe_eval(formula: str, env: dict, units: dict | None = None) -> float:
    import ast

    tree = ast.parse(formula, mode="eval")
    units = units or {}

    def unit_of(n):
        if isinstance(n, ast.Name):
            return (units.get(n.id) or [""])[0]
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and isinstance(n.slice, ast.Constant):
            u = units.get(n.value.id) or []
            return u[n.slice.value] if isinstance(n.slice.value, int) and n.slice.value < len(u) else ""
        raise ValueError("to() converts a fact reference: to(F0012, 'EUR_K')")

    def ev(n):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "to" and len(n.args) == 2 and isinstance(n.args[1], ast.Constant):
            # v1.7.1 (DEBT F5): to(F0212, "EUR_K") — a fact in EUR read in thousands of EUR
            (fk, fs), (tk, ts) = _scale(unit_of(n.args[0])), _scale(str(n.args[1].value))
            if fk != tk:
                raise ValueError(f"to(): cannot convert {fk or 'plain'} to {tk or 'plain'}")
            return ev(n.args[0]) * fs / ts
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(n.left), ev(n.right)
            return a + b if isinstance(n.op, ast.Add) else a - b if isinstance(n.op, ast.Sub) else a * b if isinstance(n.op, ast.Mult) else a / b
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise KeyError(n.id)
            v = env[n.id]
            return v[0] if isinstance(v, list) else v
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):  # F0062[1]: the fact's second value (0-based)
            if n.value.id not in env:
                raise KeyError(n.value.id)
            i = n.slice.value if isinstance(n.slice, ast.Constant) else None
            v = env[n.value.id]
            if not isinstance(i, int) or not isinstance(v, list) or not 0 <= i < len(v):
                raise ValueError(f"{n.value.id}[{i}]: no such value")
            return v[i]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("sum", "abs") and not n.keywords:
            vals = [ev(a) for a in n.args]
            return sum(vals) if n.func.id == "sum" else abs(vals[0])
        raise ValueError(f"not allowed in a formula: {ast.dump(n)[:60]}")

    return ev(tree)


def check_computed(cf: dict | None, facts: dict) -> tuple[list[dict], dict]:
    """`computed_facts.json`: {"facts": [{id, claim, formula: "F0029 / F0041 * 100", values: [{value, unit}]}]}.
    Fact ids in the formula stand for the fact's first value. Recomputed here: a mismatch is an
    arithmetic error, an unknown id a fabrication. Valid computed facts join the fact base."""
    out, good = [], {}
    for f in (cf or {}).get("facts") or []:
        fid = f.get("id", "?")
        env = {k: [float(x["value"]) for x in v["values"]] for k, v in facts.items() if v.get("values")}
        env.update({k: [float(x["value"]) for x in v["values"]] for k, v in good.items()})
        units = {k: [x.get("unit") or "" for x in v["values"]] for k, v in {**facts, **good}.items() if v.get("values")}
        try:
            res = _safe_eval(f["formula"], env, units)
        except KeyError as e:
            out.append(_issue("error", "UNKNOWN_FACT", "computed_facts.json", fid, f"formula uses {e.args[0]}, which is not a fact", hard=True))
            continue
        except (ValueError, SyntaxError, ZeroDivisionError) as e:
            out.append(_issue("error", "FORMULA_INVALID", "computed_facts.json", fid, str(e)))
            continue
        stated = float(f["values"][0]["value"])
        bad = abs(res - stated) > max(0.005 * abs(res), 0.5 * 10 ** -_decimals(stated))
        # v1.8: a formula that adds, subtracts or divides values of incompatible periods / bases
        # (LTM with a quarter, YTD with a full year, budget with actual, run-rate with reported)
        if not f.get("periods_ok"):
            from .periods import compare as _cmp

            refs = [(r, (facts.get(r) or good.get(r) or {}).get("values") or [{}]) for r in sorted(set(re.findall(r"\b[FC]\d{4}\b", f["formula"])))]
            vals = [(r, v[0]) for r, v in refs if v and v[0].get("period")]
            for i in range(len(vals)):
                for j in range(i + 1, len(vals)):
                    why = _cmp(vals[i][1], vals[j][1])
                    if why:
                        out.append(_issue("warning", "PERIOD_MISMATCH", "computed_facts.json", fid,
                                          f"{vals[i][0]} ({vals[i][1].get('period')}) and {vals[j][0]} ({vals[j][1].get('period')}): {why}; "
                                          "if intended, set \"periods_ok\": \"<why>\""))
                        break
                else:
                    continue
                break
        if bad:  # reported once; the fact stays known so its dependants do not cascade into UNKNOWN_FACT
            out.append(_issue("error", "ARITHMETIC_ERROR", "computed_facts.json", fid, f"{f['formula']} = {res:.4g}, stated {stated:g}", hard=True))
        import re as _re

        deps = sorted(set(_re.findall(r"\b(?:[FC]\d{4}|A\d{3})\b", f["formula"])))  # F0062[1] cites F0062
        rests = [d for d in deps if (facts.get(d) or good.get(d) or {}).get("fact_type") == "assumption" or (good.get(d) or {}).get("rests_on_assumptions")]
        rests += [a for a in f.get("rests_on_assumptions") or [] if a not in rests]  # 1.5: declared when the formula cannot show it
        good[fid] = {**f, "fact_type": "computed", "derived_from": deps, "source": {"file": "computed", "loc": f["formula"]}, "confidence": 0.0 if bad else 1.0,
                     **({"arithmetic_error": True} if bad else {}),
                     **({"rests_on_assumptions": rests} if rests else {})}
    return out, good


def _decimals(v: float) -> int:
    s = f"{v:g}"
    return len(s.split(".")[1]) if "." in s else 0


# ── hypotheses and insights ──────────────────────────────────────────────────────────────────────

def check_hypotheses(h: dict | None, facts: dict) -> list[dict]:
    if not h:
        return [_issue("warning", "HYPOTHESES_MISSING", "hypotheses.json", None, "No hypotheses: the storyline will summarise instead of answering")]
    out = []
    for x in h.get("hypotheses") or []:
        for fid in (x.get("supporting_facts") or []) + (x.get("contradicting_facts") or []):
            if fid not in facts:
                out.append(_issue("error", "UNKNOWN_FACT", "hypotheses.json", x["id"], f"cites {fid}, which is not in facts.json", hard=True))
        st = x.get("status")
        if st not in ("supported", "rejected", "unresolved"):
            out.append(_issue("error", "HYPOTHESIS_STATUS", "hypotheses.json", x["id"], "status must be supported | rejected | unresolved"))
        if st == "supported" and not x.get("supporting_facts"):
            out.append(_issue("error", "HYPOTHESIS_UNSUPPORTED", "hypotheses.json", x["id"], "'supported' without supporting facts"))
        if st == "rejected" and not x.get("contradicting_facts"):
            out.append(_issue("error", "HYPOTHESIS_UNSUPPORTED", "hypotheses.json", x["id"], "'rejected' without contradicting facts"))
        if st == "supported" and x.get("contradicting_facts") and not x.get("rationale"):
            out.append(_issue("info", "HYPOTHESIS_TENSION", "hypotheses.json", x["id"], "supported despite contradicting facts: say why in the rationale"))
        c = x.get("confidence")
        if c is not None and not (0 <= c <= 1):
            out.append(_issue("error", "HYPOTHESIS_CONFIDENCE", "hypotheses.json", x["id"], "confidence must be within 0–1"))
    n = len(h.get("hypotheses") or [])
    if n and not any(x.get("status") == "rejected" for x in h["hypotheses"]) and n >= 4:
        out.append(_issue("info", "HYPOTHESES_NONE_REJECTED", "hypotheses.json", None, "No hypothesis was rejected: were alternatives really tested?"))
    return out


def check_insights(ins: dict | None, facts: dict, hyps: dict, source_text: str = "") -> list[dict]:
    if not ins:
        return [_issue("error", "INSIGHTS_MISSING", "insights.json", None, "No insights")]
    out = []
    for x in ins.get("insights") or []:
        fids = x.get("facts") or []
        missing = [f for f in fids if f not in facts]
        if missing:
            out.append(_issue("error", "UNKNOWN_FACT", "insights.json", x["id"], f"cites {', '.join(missing)}", hard=True))
        if not fids:
            out.append(_issue("error", "INSIGHT_UNGROUNDED", "insights.json", x["id"], "an insight must cite facts", hard=True))
        for g in ground_numbers(x.get("statement", ""), [facts[f] for f in fids if f in facts]):
            if g["status"] == "unsupported":
                out.append(_issue("error", "UNSUPPORTED_NUMBER", "insights.json", x["id"], f"{g['number']} is not grounded in the cited facts", hard=True))
        for hid in x.get("hypotheses") or []:
            if hyps.get(hid, {}).get("status") == "rejected":
                out.append(_issue("error", "CONTRADICTED_AS_FACT", "insights.json", x["id"], f"built on rejected hypothesis {hid}", hard=True))
        st = x.get("statement", "")
        if len(fids) == 1 and max((_jaccard(st, facts[f]["claim"]) for f in fids if f in facts), default=0) > 0.6:
            out.append(_issue("warning", "INSIGHT_RESTATES_FACT", "insights.json", x["id"], "restates one fact: an insight reasons across facts"))
        if source_text and len(st) > 30 and st.lower()[:60] in source_text.lower():
            out.append(_issue("warning", "INSIGHT_COPIED", "insights.json", x["id"], "copied from the source text: not new reasoning"))
        if CAUSAL.search(st) and (len(fids) < 2 or not x.get("hypotheses")):
            out.append(_issue("warning", "CAUSAL_OVERCLAIM", "insights.json", x["id"], "causal claim with < 2 facts or no tested hypothesis"))
        if x.get("materiality") not in ("high", "medium", "low"):
            out.append(_issue("warning", "INSIGHT_MATERIALITY", "insights.json", x["id"], "materiality (high | medium | low) not stated"))
        if not x.get("decision_relevance"):
            out.append(_issue("warning", "INSIGHT_RELEVANCE", "insights.json", x["id"], "decision relevance not stated"))
        if x.get("contradicting_facts") and not x.get("caveat"):
            out.append(_issue("warning", "INSIGHT_CAVEAT", "insights.json", x["id"], "contradicting facts listed without a caveat"))
        if not re.search(r"\d", st):
            out.append(_issue("info", "INSIGHT_UNQUANTIFIED", "insights.json", x["id"], "not quantified"))
    return out


# ── storyline ────────────────────────────────────────────────────────────────────────────────────

FRAMEWORKS = {"SCR", "CII", "PDS", "DRI", "MPO", "CGT", "HEC"}


def check_storyline(sl: dict | None, insights: dict, facts: dict, hyps: dict, project: dict | None) -> list[dict]:
    if not sl:
        return [_issue("error", "STORYLINE_MISSING", "storyline.json", None, "No storyline")]
    out = []
    cands = sl.get("candidates") or []
    if len(cands) < 2:
        out.append(_issue("warning", "GT_SINGLE_CANDIDATE", "storyline.json", None, "Only one governing-thought candidate: generate and compare alternatives"))
    for c in cands:
        if not c.get("scores"):
            out.append(_issue("warning", "GT_UNSCORED", "storyline.json", c.get("text", "")[:40], "candidate not scored against the criteria"))
    gt = sl.get("governing_thought", "")
    if not gt:
        out.append(_issue("error", "GT_MISSING", "storyline.json", None, "No governing thought"))
    gt_facts = sorted({f for k in sl.get("key_line") or [] for i in k.get("insights") or [] for f in insights.get(i, {}).get("facts") or []})
    for g in ground_numbers(gt, [facts[f] for f in gt_facts if f in facts]):
        if g["status"] == "unsupported":
            out.append(_issue("error", "UNSUPPORTED_NUMBER", "storyline.json", "governing_thought", f"{g['number']} not grounded in the key line's facts", hard=True))
    if project:
        q = f"{project.get('question', '')} {project.get('decision', '')}"
        if _jaccard(gt, q) == 0:
            out.append(_issue("warning", "GT_OFF_QUESTION", "storyline.json", "governing_thought", "shares no term with the business question / decision: does it answer it?"))
    if sl.get("framework") and sl["framework"] not in FRAMEWORKS:
        out.append(_issue("warning", "FRAMEWORK_UNKNOWN", "storyline.json", "framework", f"{sl['framework']} is not one of {', '.join(sorted(FRAMEWORKS))}"))
    if not sl.get("framework_rationale"):
        out.append(_issue("info", "FRAMEWORK_RATIONALE", "storyline.json", "framework", "why this framework for this question?"))
    kl = sl.get("key_line") or []
    if not 2 <= len(kl) <= 5:
        out.append(_issue("warning", "KEYLINE_SIZE", "storyline.json", "key_line", f"{len(kl)} key-line points (2–5 expected)"))
    for k in kl:
        if not k.get("insights"):
            out.append(_issue("error", "KEYLINE_UNSUPPORTED", "storyline.json", k.get("id"), "key-line point without supporting insights"))
        for i in k.get("insights") or []:
            if i not in insights:
                out.append(_issue("error", "UNKNOWN_INSIGHT", "storyline.json", k.get("id"), f"cites {i}"))
            for hid in insights.get(i, {}).get("hypotheses") or []:
                if hyps.get(hid, {}).get("status") == "rejected":
                    out.append(_issue("error", "CONTRADICTED_AS_FACT", "storyline.json", k.get("id"), f"rests on rejected hypothesis {hid}", hard=True))
    for a in range(len(kl)):
        for b in range(a + 1, len(kl)):
            j = _jaccard(kl[a].get("message", ""), kl[b].get("message", ""))
            if j > 0.5:
                out.append(_issue("warning", "KEYLINE_OVERLAP", "storyline.json", f"{kl[a].get('id')}/{kl[b].get('id')}", f"key-line points overlap ({j:.2f}): not MECE?"))
    used = {i for k in kl for i in k.get("insights") or []}
    for iid, x in insights.items():
        if x.get("materiality") == "high" and iid not in used:
            out.append(_issue("warning", "MATERIAL_INSIGHT_UNUSED", "storyline.json", iid, "a high-materiality insight is in no key-line point"))
    return out


# ── deck plan / slide architecture ───────────────────────────────────────────────────────────────

VISUAL_FOR = {  # message type (spec.MESSAGE_TYPES + kpi/summary) → archetypes that can carry it
    "single_number": {"kpi_hero", "kpi_dashboard"}, "kpi": {"kpi_dashboard", "kpi_hero"}, "ranking": {"chart", "table"},
    "composition": {"chart", "segmentation", "table"}, "composition_change": {"chart", "kpi_dashboard", "table"}, "trend": {"chart", "kpi_dashboard"},
    "change_bridge": {"waterfall"}, "distribution": {"chart"}, "correlation": {"chart"}, "positioning": {"matrix"},
    "comparison": {"comparison", "table", "chart", "matrix"}, "segmentation": {"segmentation", "chart", "table"}, "sequence": {"process", "timeline"},
    "plan": {"roadmap", "timeline"}, "hierarchy": {"hierarchy", "architecture"}, "geography": {"chart", "table"}, "flow": {"process", "architecture", "chart"},
    "structure": {"architecture", "operating_model", "hierarchy"}, "status": {"table", "kpi_dashboard"}, "argument": {"text_exhibit", "statement"},
    "recommendation": {"statement", "executive_summary", "text_exhibit", "roadmap"}, "summary": {"executive_summary"},
    "causality": {"process", "hierarchy", "architecture"},
}


def check_deck_plan(dp: dict | None, storyline: dict | None, insights: dict, facts: dict, project: dict | None) -> list[dict]:
    from ..design.tokens import load_profile

    profile = load_profile((project or {}).get("deck_type") or "standard")
    if not dp:
        return [_issue("error", "DECK_PLAN_MISSING", "deck_plan.json", None, "No deck plan (slide architecture)")]
    from ..core.headline import lint_headline

    out = []
    slides = dp.get("slides") or []
    kl = {k["id"]: k for k in (storyline or {}).get("key_line") or []}
    core = [s for s in slides if s.get("priority") == "core"]
    for s in slides:
        sid = s.get("id")
        if s.get("priority") not in ("core", "support", "appendix"):
            out.append(_issue("error", "SLIDE_PRIORITY", "deck_plan.json", sid, "priority must be core | support | appendix"))
        if not s.get("reason_to_exist"):
            out.append(_issue("error", "SLIDE_NO_REASON", "deck_plan.json", sid, "every slide states its reason to exist"))
        if s.get("priority") != "appendix" and s.get("role") not in ("title", "exec_summary", "divider", "next_steps") and s.get("key_line") not in kl:
            out.append(_issue("warning", "SLIDE_ORPHAN", "deck_plan.json", sid, "not attached to a key-line point"))
        for f in s.get("facts") or []:
            if f not in facts:
                out.append(_issue("error", "UNKNOWN_FACT", "deck_plan.json", sid, f"cites {f}", hard=True))
        cited = [facts[f] for f in s.get("facts") or [] if f in facts]
        for i in s.get("insights") or []:
            cited += [facts[f] for f in insights.get(i, {}).get("facts") or [] if f in facts]
        h = s.get("headline", "")
        if h and s.get("role") not in ("title", "divider"):
            for g in ground_numbers(h, cited):
                if g["status"] == "unsupported":
                    out.append(_issue("error", "UNSUPPORTED_NUMBER", "deck_plan.json", sid, f"headline {g['number']} not grounded in the slide's facts", hard=True))
                elif g["status"] == "assumption":
                    conditional = re.search(r"\b(if|assuming|assumes|assumed|would|could|about|around|approximately|estimated?|estimates?|roughly|up to|at most|upper bound|"
                                            r"si|suponiendo|supondría|supuesto|hipótesis|estim\w*|previst\w*|prevemos|calculamos|cerca de|aproximadamente|unos|hasta|como máximo)\b", h, re.I)
                    out.append(_issue("info" if conditional else "warning", "ASSUMPTION_IN_HEADLINE", "deck_plan.json", sid, f"{g['number']} rests on an assumption ({', '.join(g['facts'])}): say so on the slide"))
            lint = lint_headline(h, {"id": sid}, profile)[1]
            if any(i["code"] == "HEADLINE_TOPIC" and i["level"] == "error" for i in lint) and s.get("priority") != "appendix":
                out.append(_issue("error", "HEADLINE_TOPIC", "deck_plan.json", sid, f"'{h}' is a topic, not a conclusion"))
            for i in lint:  # same word budget as the render lint of this deck type, so the two layers agree
                if i["code"] == "HEADLINE_LONG":
                    out.append(_issue("warning", "HEADLINE_LONG", "deck_plan.json", sid, i["message"]))
        mt, arch = s.get("message_type"), s.get("archetype")
        if mt in VISUAL_FOR and arch and arch not in VISUAL_FOR[mt]:
            out.append(_issue("warning", "VISUAL_INTENT", "deck_plan.json", sid, f"message '{mt}' is usually carried by {', '.join(sorted(VISUAL_FOR[mt]))}, not {arch}"))
    for kid in kl:
        if not any(s.get("key_line") == kid and s.get("priority") == "core" for s in slides):
            out.append(_issue("error", "KEYLINE_NO_SLIDE", "deck_plan.json", kid, "key-line point has no core slide"))
    by_kl: dict = {}
    for s in core:
        by_kl.setdefault(s.get("key_line"), []).append(s)
    for kid, ss in by_kl.items():
        if kid is None:  # title, executive summary, next steps: not argument slides
            continue
        for s in ss[1:] if len(ss) > 1 else []:
            if not s.get("why_not_merge"):
                out.append(_issue("warning", "SLIDE_MERGE", "deck_plan.json", s.get("id"), f"{len(ss)} core slides on {kid}: say why they are not one"))
    heads = [s.get("headline", "") for s in slides]
    for a in range(len(heads)):
        for b in range(a + 1, len(heads)):
            if heads[a] and _jaccard(heads[a], heads[b]) > 0.7:
                out.append(_issue("warning", "SLIDE_DUPLICATE", "deck_plan.json", f"{slides[a].get('id')}/{slides[b].get('id')}", "two slides make the same point"))
    mx = (project or {}).get("max_slides")
    n_main = sum(1 for s in slides if s.get("priority") != "appendix")
    if mx and n_main > mx:
        out.append(_issue("error", "DECK_TOO_LONG", "deck_plan.json", None, f"{n_main} slides before the appendix > max {mx}"))
    if slides and not any(s.get("role") == "exec_summary" for s in slides[:3]) and n_main >= 5:
        out.append(_issue("warning", "ANSWER_NOT_FIRST", "deck_plan.json", None, "no executive summary in the first three slides"))
    return out


def information_economy(dp: dict | None, insights: dict, facts: dict) -> dict:
    slides = (dp or {}).get("slides") or []

    def used(pri):
        fs = set()
        for s in slides:
            if s.get("priority") in pri:
                fs |= set(s.get("facts") or [])
                for i in s.get("insights") or []:
                    fs |= set(insights.get(i, {}).get("facts") or [])
        return fs

    main, app = used(("core", "support")), used(("appendix",))
    return {"facts_available": len(facts), "facts_used": len(main), "facts_appendix": len(app - main), "facts_omitted": len(set(facts) - main - app),
            "slides": len(slides), "core": sum(1 for s in slides if s.get("priority") == "core"),
            "support": sum(1 for s in slides if s.get("priority") == "support"), "appendix": sum(1 for s in slides if s.get("priority") == "appendix"),
            "note": "omitting facts is expected: decision relevance, not coverage, is the goal"}


# ── the rendered spec: factuality hard gate ──────────────────────────────────────────────────────

SKIP_KEYS = {"id", "kind", "archetype", "layout", "source", "tracker", "section", "purpose", "message_type", "evidence", "format", "style", "highlight",
             "headline", "text", "reason_to_exist", "why_not_merge", "decision_role", "priority", "role", "color", "colors", "delta_colors", "variant",
             "facts", "insights", "key_line", "assumptions_note", "widths", "column_widths", "decimals", "align", "icon", "emphasis",
             "bound", "estimate", "width", "kind", "type", "delta_colors", "total_color", "proof_label", "truncate_axis"}


def _slide_leaves(s: dict, path: str = ""):
    """(path, "text"|"num", value) for every string and number a reader sees on a slide, except the
    headline (checked above), the source line and layout / styling keys."""
    if isinstance(s, dict):
        for k, v in s.items():
            if k not in SKIP_KEYS:
                yield from _slide_leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(s, list):
        for i, v in enumerate(s):
            yield from _slide_leaves(v, f"{path}[{i}]")
    elif isinstance(s, str) and re.search(r"\d", s):
        yield path, "text", s
    elif isinstance(s, (int, float)) and not isinstance(s, bool):
        yield path, "num", float(s)


def _deck_text(t: str) -> str:
    """Spell out what a reader understands: '23–25%' is 23% to 25%; '2024-25' is a period, not 25."""
    t = re.sub(r"\b((?:19|20)\d{2})\s?[-–/]\s?\d{2}\b", r"\1", t)
    return re.sub(r"(\d+(?:[.,]\d+)?)\s?[–-]\s?(\d+(?:[.,]\d+)?)\s?%", r"\1% to \2%", t)


def _value_grounded(v: float, cited: list[dict]) -> bool:
    """A chart / table number must BE a cited fact value (v1.7.1, DEBT F1). Derived cells are written as
    computed facts (`computed_facts.json`) and cited: on a slide citing 20 facts, "one operation on two"
    reaches almost any number, so it is not allowed for data values. The value may be written in another
    scale of the same quantity (10 M€ in a k€ column: ×1000, DEBT F7) or rounded as displayed."""
    if float(v).is_integer() and (abs(v) <= 10 or 1900 <= v <= 2100):
        return True  # small counts, ranks, years
    vals = [abs(float(x["value"])) for f in cited for x in f.get("values") or []]
    s = f"{abs(v):g}"
    tol = 0.5 * 10 ** -(len(s.split(".")[1]) if "." in s else 0) + 1e-6 * abs(v)  # display rounding only
    a = abs(v)
    return any(abs(x * k - a) <= tol for x in vals for k in (1, 1e3, 1e-3, 1e6, 1e-6))


def _raw_files(cited: list[dict], facts: dict) -> set[str]:
    """Source files of the cited facts, following computed-fact lineage down to the raw facts."""
    out, seen, todo = set(), set(), list(cited)
    while todo:
        f = todo.pop()
        if id(f) in seen:
            continue
        seen.add(id(f))
        file = (f.get("source") or {}).get("file")
        if f.get("fact_type") == "computed":
            todo += [facts[d] for d in f.get("derived_from") or [] if d in facts]
        elif file:
            out.add(file)
    return out


def factcheck_deck(deck: dict | None, facts: dict) -> list[dict]:
    """Headline numbers of the render spec must be grounded in the facts its evidence items cite
    (`evidence: [{"fact": "F0012"}]`); a named source file must be one of those facts' files."""
    if not deck:
        return [_issue("warning", "DECK_MISSING", "deck.json", None, "No deck.json yet")]
    out = []
    for s in deck.get("slides") or []:
        if s.get("kind", "content") not in ("content", "exec_summary", "statement"):
            continue
        sid = s.get("id")
        fids = [e.get("fact") for e in s.get("evidence") or [] if isinstance(e, dict) and e.get("fact")] + list(s.get("facts") or [])
        cited = [facts[f] for f in fids if f in facts]
        for f in fids:
            if f not in facts:
                out.append(_issue("error", "UNKNOWN_FACT", "deck.json", sid, f"cites {f}", hard=True))
        text = s.get("headline", "") if s.get("kind", "content") != "statement" else s.get("text", "")
        for g in ground_numbers(text, cited):
            if g["status"] == "unsupported":
                out.append(_issue("error", "UNSUPPORTED_NUMBER", "deck.json", sid, f"headline {g['number']} not grounded in cited facts" if cited
                                  else f"headline {g['number']} cites no facts", hard=True))
        # v1.8: every number on the slide, not only the headline — body text, KPIs, table cells, chart data
        for path, kind, val in _slide_leaves(s):
            if kind == "text" and re.fullmatch(r"\s*[-+−]?[\d.,]+\s*", val):  # a bare table cell: unit-free, like chart data
                from ..ingest.readers import _num

                kind, val = "num", _num(val.strip())[0]
                if val is None:
                    continue
            if kind == "text":
                for g in ground_numbers(val, cited):
                    if g["status"] == "unsupported":
                        out.append(_issue("error", "UNSUPPORTED_NUMBER", "deck.json", f"{sid}:{path}", f"{g['number']} not grounded in the slide's cited facts", hard=True))
            elif not _value_grounded(val, cited):
                out.append(_issue("error", "UNSUPPORTED_NUMBER", "deck.json", f"{sid}:{path}", f"data value {val:g} is not a cited fact value: cite the fact, or write the derived value as a computed fact and cite it", hard=True))
        from .binding import check_binding

        out += check_binding(s, facts, _issue)
        files = _raw_files(cited, facts)
        named = re.findall(r"[\w\-. ]+\.(?:xlsx|csv|pdf|docx|pptx|md|txt)", s.get("source") or "", re.I)
        for n in named:
            if files and n.strip() not in files:
                out.append(_issue("error", "WRONG_SOURCE", "deck.json", sid, f"source names {n.strip()}, but the cited facts come from {', '.join(sorted(files))}", hard=True))
    return out


# ── conflicts between sources and critic findings ───────────────────────────────────────────────

def check_conflicts(work: Path, fm: dict | None, used: set[str]) -> list[dict]:
    from .conflicts import detect_conflicts

    if not fm:
        return []
    found = detect_conflicts(fm.get("facts") or [])
    recorded = _load(work, "fact_conflicts.json") or {}
    out, res = [], {}
    for c in recorded.get("conflicts") or []:
        ids = [x.get("fact") if isinstance(x, dict) else x for x in c.get("facts") or []] if isinstance(c, dict) else []
        if not ids or not all(isinstance(x, str) for x in ids):
            out.append(_issue("error", "CONFLICT_FORMAT", "fact_conflicts.json", None,
                              'each conflict is {"facts": [{"fact": "F0012"}, …], "resolution": "…"}'))
            continue
        res[tuple(sorted(ids))] = c.get("resolution")
    for c in found:
        key = tuple(sorted(x["fact"] for x in c["facts"]))
        if res.get(key):
            continue
        touches = used & set(key)
        desc = f"{c['type']} on {'/'.join(c['measure'])} {c['period']}: " + " vs ".join(f"{x['value']:g} ({x['basis']}, {x['source']})" for x in c["facts"])
        out.append(_issue("error" if touches else "warning", "FACT_CONFLICT_UNRESOLVED", "fact_conflicts.json", "/".join(key),
                          desc + (" — the deck uses one of these facts: record which value is used and why" if touches else " — record a resolution")))
    return out


def check_critique(cr: dict | None) -> list[dict]:
    if cr is None:
        return [_issue("warning", "CRITIQUE_MISSING", "critique.json", None, "No critic findings recorded (fact checker, partner, red team, editor, data-viz)")]
    out = []
    roles = {f.get("critic") for f in cr.get("findings") or []}
    for role in ("FACT CHECKER", "PARTNER REVIEW", "RED TEAM", "EDITOR", "DATA-VIZ REVIEW"):
        if role not in roles:
            out.append(_issue("info", "CRITIC_ROLE_MISSING", "critique.json", role, "no finding recorded for this critic (state 'no finding' explicitly)"))
    for f in cr.get("findings") or []:
        if f.get("severity") not in ("high", "medium", "low", "none"):
            out.append(_issue("warning", "CRITIC_FORMAT", "critique.json", f.get("id"), "severity must be high | medium | low | none"))
        if f.get("severity") == "high" and not f.get("resolved"):
            out.append(_issue("error", "CRITIC_UNRESOLVED", "critique.json", f.get("id"), f"unresolved high-severity finding ({f.get('critic')}): {f.get('finding', '')[:100]}"))
    return out


# ── everything ───────────────────────────────────────────────────────────────────────────────────

def check_work(work_dir: str | Path, sources_dir: str | Path | None = None) -> dict:
    work = Path(work_dir)
    project = _load(work, "project.json") or _load(work.parent, "project.json")
    fm = _load(work, "facts.json")
    facts = {f["id"]: f for f in (fm or {}).get("facts", [])}
    assumptions = {a["id"]: {**a, "fact_type": "assumption", "source": {"file": "assumptions.json", "loc": a["id"]}, "confidence": None,
                             "claim": a.get("statement", "")} for a in (_load(work, "assumptions.json") or {}).get("assumptions", [])}
    facts.update(assumptions)
    computed_issues, computed = check_computed(_load(work, "computed_facts.json"), facts)
    facts.update(computed)
    hy = _load(work, "hypotheses.json")
    hyps = {h["id"]: h for h in (hy or {}).get("hypotheses", [])}
    ins = _load(work, "insights.json")
    insights = {i["id"]: i for i in (ins or {}).get("insights", [])}
    sl, dp, deck = _load(work, "storyline.json"), _load(work, "deck_plan.json"), _load(work, "deck.json")
    st = _load(work, "source_text.json")
    source_text = " ".join(b["text"] for b in (st or {}).get("blocks", []))
    if sources_dir is None and (work.parent / "sources").exists():
        sources_dir = work.parent / "sources"
    dp_used = {f for x in ((dp or {}).get("slides") or []) for f in (x.get("facts") or [])}
    dp_used |= {f for x in insights.values() for f in x.get("facts") or []}
    stages = {
        "project": check_project(project),
        "conflicts": check_conflicts(work, fm, dp_used),
        "critique": check_critique(_load(work, "critique.json")) + check_partner_checklist(_load(work, "critique.json")),
        "facts": check_facts(fm, Path(sources_dir) if sources_dir else None, work) + computed_issues + check_analyses(work, sources_dir),
        "hypotheses": check_hypotheses(hy, facts),
        "insights": check_insights(ins, facts, hyps, source_text) + check_discarded(ins, deck),
        "storyline": check_storyline(sl, insights, facts, hyps, project) + check_decision(sl, facts, project) + check_decision_15(sl) + check_rejected_revived(sl, hyps),
        "deck_plan": check_deck_plan(dp, sl, insights, facts, project),
        "deck": factcheck_deck(deck, facts) + check_assumptions_in_summary(deck, facts),
    }
    issues = [i for v in stages.values() for i in v]
    hard = [i for i in issues if i["hard"]]
    stop = {
        "no_hard_factual_errors": not hard,
        "storyline_passes": not any(i["level"] == "error" for i in stages["storyline"]),
        "ghost_deck_passes": not any(i["level"] == "error" for i in stages["deck_plan"]),
        "no_unsupported_headlines": not any(i["code"] == "UNSUPPORTED_NUMBER" and i["artifact"] in ("deck_plan.json", "deck.json") for i in issues),
        "no_unresolved_high_critic_finding": not any(i["code"] == "CRITIC_UNRESOLVED" for i in issues),
        "no_unresolved_conflict_in_use": not any(i["code"] == "FACT_CONFLICT_UNRESOLVED" and i["level"] == "error" for i in issues),
    }
    return {"protocol": PROTOCOL_VERSION, "status": "blocked" if hard else ("needs_work" if any(i["level"] == "error" for i in issues) else "pass"),
            "stopping_criteria": stop, "counts": {lvl: sum(1 for i in issues if i["level"] == lvl) for lvl in ("error", "warning", "info")},
            "hard_failures": len(hard), "information_economy": information_economy(dp, insights, facts),
            "stages": {k: {"errors": sum(1 for i in v if i["level"] == "error"), "warnings": sum(1 for i in v if i["level"] == "warning")} for k, v in stages.items()},
            "issues": issues}


def report_markdown(r: dict) -> str:
    L = [f"# Reasoning check — {r['status'].upper()}", "", f"_protocol {r['protocol']}_ · errors {r['counts']['error']} · warnings {r['counts']['warning']} · "
         f"hard factual failures **{r['hard_failures']}**", "", "| stage | errors | warnings |", "|---|---|---|"]
    L += [f"| {k} | {v['errors']} | {v['warnings']} |" for k, v in r["stages"].items()]
    L += ["", "Stopping criteria: " + " · ".join(f"{k} {'✅' if v else '❌'}" for k, v in r["stopping_criteria"].items()), ""]
    ie = r["information_economy"]
    L += [f"Information economy: {ie['facts_used']} of {ie['facts_available']} facts used, {ie['facts_appendix']} in appendix, {ie['facts_omitted']} omitted · "
          f"{ie['core']} core / {ie['support']} support / {ie['appendix']} appendix slides", ""]
    for lvl in ("error", "warning", "info"):
        items = [i for i in r["issues"] if i["level"] == lvl]
        if items:
            L += [f"## {lvl}s", ""] + [f"- {'**HARD** ' if i['hard'] else ''}`{i['code']}` {i['artifact']} {i['ref'] or ''}: {i['message']}" for i in items] + [""]
    return "\n".join(L) + "\n"
