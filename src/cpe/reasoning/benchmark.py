"""Source-to-deck benchmark: does a work folder contain the RIGHT deck for a case?

A case (evals/source_to_deck/<set>/<case>/) holds
    sources/          raw files the system reads
    project.json      the brief: audience, decision, question, horizon, scope, max_slides
    reference.json    what a good answer must contain — never a deck to match literally:
        critical_facts         [{"id", "description", "value", "unit", "period"?}]  must be in facts.json
        required_conclusions   [{"id", "description", "any_of": [[term, …], …], "numbers": ["€12M", …]}]
                               a conclusion is reached when ONE term group fully appears (and its
                               numbers, if listed) in an insight, the governing thought or a core headline
        traps                  [{"id", "description", "forbidden": [[term, …]], "numbers": [...]}]
                               a trap is triggered by the same rule in the governing thought or a core headline
        acceptable_frameworks  ["SCR", "DRI", …]
        reference_governing_thought, notes   (for human reviewers only, never scored)

Dimensions are reported SEPARATELY; there is deliberately no total score (docs/SOURCE_TO_DECK.md).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..qa.proof import headline_quantities
from . import PROTOCOL_VERSION
from .checks import _load, check_work
from .grounding import fact_scalars


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower())


def _group_hit(text: str, groups: list[list[str]], numbers: list[str] | None = None) -> bool:
    t = _norm(text)
    if not any(all(term.lower() in t for term in g) for g in groups or []):
        return False
    if numbers:
        have = {(q["kind"], round(q["value"], 6)) for q in headline_quantities(text)}
        for n in numbers:
            q = headline_quantities(n)
            if q and (q[0]["kind"], round(q[0]["value"], 6)) not in have:
                return False
    return True


def evaluate(case_dir: str | Path, work_dir: str | Path, run_meta: dict | None = None) -> dict:
    case, work = Path(case_dir), Path(work_dir)
    ref = json.loads((case / "reference.json").read_text(encoding="utf-8"))
    project = json.loads((case / "project.json").read_text(encoding="utf-8"))
    chk = check_work(work, case / "sources")
    facts = {f["id"]: f for f in (_load(work, "facts.json") or {}).get("facts", [])}
    from .checks import check_computed

    facts.update(check_computed(_load(work, "computed_facts.json"), facts)[1])
    insights = (_load(work, "insights.json") or {}).get("insights", [])
    sl = _load(work, "storyline.json") or {}
    dp = _load(work, "deck_plan.json") or {}
    slides = dp.get("slides") or []
    core = [s for s in slides if s.get("priority") == "core"]
    issues = chk["issues"]

    def count(codes, artifact=None):
        return sum(1 for i in issues if i["code"] in codes and (artifact is None or i["artifact"] == artifact))

    # FACT GROUNDING
    scal = fact_scalars(list(facts.values()))
    found = []
    for cf in ref.get("critical_facts") or []:
        u = cf.get("unit", "")
        cur = next((c for c in "€$£" if c in u), "")
        q = headline_quantities(f"{cur}{cf['value']:g}{u.replace(cur, '')}")
        hit = any(abs(s["value"] - q[0]["value"]) <= 1e-6 * max(1, q[0]["value"]) + 0.005 * q[0]["value"] for s in scal if q and s["kind"] == q[0]["kind"]) if q else False
        found.append(hit)
    fabricated = count({"FACT_FABRICATED"})
    fact_grounding = {"critical_fact_recall": round(sum(found) / len(found), 3) if found else None, "critical_facts": f"{sum(found)}/{len(found)}",
                      "facts": len(facts), "fabricated_facts": fabricated,
                      "fact_precision": round(1 - fabricated / len(facts), 3) if facts else None,
                      "traceable": round(sum(1 for f in facts.values() if (f.get("source") or {}).get("file")) / len(facts), 3) if facts else None,
                      "arithmetic_errors": count({"ARITHMETIC_ERROR"})}
    # INSIGHT QUALITY
    unsupported_ins = {i["ref"] for i in issues if i["artifact"] == "insights.json" and i["hard"]}
    texts_ins = [i.get("statement", "") for i in insights]
    concl = {c["id"]: any(_group_hit(t, c.get("any_of"), c.get("numbers")) for t in texts_ins + [sl.get("governing_thought", "")] + [s.get("headline", "") for s in core])
             for c in ref.get("required_conclusions") or []}
    insight_quality = {"insights": len(insights), "supported": len(insights) - len(unsupported_ins), "unsupported": len(unsupported_ins),
                       "material_conclusion_coverage": f"{sum(concl.values())}/{len(concl)}", "conclusions": concl,
                       "restating_facts": count({"INSIGHT_RESTATES_FACT", "INSIGHT_COPIED"}), "causal_overclaims": count({"CAUSAL_OVERCLAIM"}),
                       "with_decision_relevance": sum(1 for i in insights if i.get("decision_relevance"))}
    # STORYLINE
    gt = sl.get("governing_thought", "")
    traps = {t["id"]: any(_group_hit(x, t.get("forbidden"), t.get("numbers")) for x in [gt] + [s.get("headline", "") for s in core]) for t in ref.get("traps") or []}
    storyline = {"governing_thought": gt, "candidates_compared": len(sl.get("candidates") or []),
                 "framework": sl.get("framework"), "framework_acceptable": (sl.get("framework") in ref["acceptable_frameworks"]) if ref.get("acceptable_frameworks") else None,
                 "answer_first": not any(i["code"] == "ANSWER_NOT_FIRST" for i in issues),
                 "key_line_points": len(sl.get("key_line") or []), "unsupported_key_line_points": count({"KEYLINE_UNSUPPORTED"}),
                 "mece_overlaps": count({"KEYLINE_OVERLAP"}), "traps_triggered": [k for k, v in traps.items() if v],
                 "errors": chk["stages"]["storyline"]["errors"]}
    # SLIDE ARCHITECTURE
    core_heads = [s.get("headline", "") for s in core]
    covered = {c["id"]: any(_group_hit(h, c.get("any_of"), c.get("numbers")) for h in core_heads + [gt]) for c in ref.get("required_conclusions") or []}
    architecture = {"slides": len(slides), "core": len(core), "appendix": sum(1 for s in slides if s.get("priority") == "appendix"),
                    "max_slides": project.get("max_slides"), "within_length": not any(i["code"] == "DECK_TOO_LONG" for i in issues),
                    "required_messages_on_core_slides": f"{sum(covered.values())}/{len(covered)}", "orphan_slides": count({"SLIDE_ORPHAN"}),
                    "duplicates": count({"SLIDE_DUPLICATE"}), "unjustified_extra_slides": count({"SLIDE_MERGE", "SLIDE_NO_REASON"}),
                    "information_economy": chk["information_economy"]}
    # HEADLINES
    heads = [s for s in slides if s.get("headline") and s.get("role") not in ("title", "divider")]
    topic = count({"HEADLINE_TOPIC"}, "deck_plan.json")
    unsup = {i["ref"] for i in issues if i["code"] == "UNSUPPORTED_NUMBER" and i["artifact"] == "deck_plan.json"}
    with_num = [s for s in heads if re.search(r"\d", s["headline"])]
    headlines = {"headlines": len(heads), "conclusion_rate": round(1 - topic / len(heads), 3) if heads else None,
                 "numbers_proven_rate": round(1 - len(unsup & {s["id"] for s in with_num}) / len(with_num), 3) if with_num else None,
                 "mean_words": round(sum(len(s["headline"].split()) for s in heads) / len(heads), 1) if heads else None}
    # VISUAL INTENT
    vi = [s for s in slides if s.get("message_type") and s.get("archetype")]
    visual_intent = {"slides_with_intent": len(vi), "mismatches": count({"VISUAL_INTENT"}),
                     "accuracy": round(1 - count({"VISUAL_INTENT"}) / len(vi), 3) if vi else None}
    factuality = {"hard_failures": chk["hard_failures"], "status": "FAIL" if chk["hard_failures"] else "PASS",
                  "by_code": {c: sum(1 for i in issues if i["hard"] and i["code"] == c) for c in sorted({i["code"] for i in issues if i["hard"]})}}
    return {"protocol": PROTOCOL_VERSION, "case": case.name, "run": run_meta or {}, "factuality": factuality, "fact_grounding": fact_grounding,
            "insight_quality": insight_quality, "storyline": storyline, "slide_architecture": architecture, "headlines": headlines,
            "visual_intent": visual_intent, "reasoning_check_status": chk["status"],
            "note": "dimensions are separate on purpose; there is no total score"}


def to_markdown(r: dict) -> str:
    L = [f"# Source-to-deck evaluation — {r['case']}", "", f"_protocol {r['protocol']}_ · run: {json.dumps(r['run'])}", "",
         f"**Factuality (hard gate): {r['factuality']['status']}** — {r['factuality']['hard_failures']} hard failures {r['factuality']['by_code'] or ''}", ""]
    for dim in ("fact_grounding", "insight_quality", "storyline", "slide_architecture", "headlines", "visual_intent"):
        L += [f"## {dim.replace('_', ' ')}", ""]
        for k, v in r[dim].items():
            L.append(f"- {k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
        L.append("")
    L.append(f"_{r['note']}_")
    return "\n".join(L) + "\n"
