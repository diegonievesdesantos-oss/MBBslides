"""v1.7 — consulting-intelligence layer: fact model, grounding, artifact checks, hard factuality
gates, evidence graph, ghost deck, source-to-deck benchmark. Every negative test plants one defect
in the stored development run and expects the deterministic checks to catch it."""
import json
import shutil
from pathlib import Path

import pytest

from cpe.reasoning import benchmark, checks, facts, graph, grounding
from cpe.reasoning.facts import detect_period, detect_unit, unit_from_raw

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "evals" / "source_to_deck" / "development" / "margin_recovery"
RUN = CASE / "runs" / "dev_run_01"


@pytest.fixture
def work(tmp_path):
    w = tmp_path / "work"
    shutil.copytree(RUN, w)
    return w


def _edit(w, name, fn):
    d = json.loads((w / name).read_text())
    fn(d)
    (w / name).write_text(json.dumps(d, indent=2, ensure_ascii=False))


def _codes(r, hard=None):
    return {i["code"] for i in r["issues"] if hard is None or i["hard"] == hard}


# ── fact model ───────────────────────────────────────────────────────────────────────────────────

def test_period_and_unit_semantics():
    assert detect_period("FY25E") == {"period": "FY2025", "basis": "estimate"}
    assert detect_period("Budget 2026")["basis"] == "budget"
    assert detect_period("Q3 2025")["period"] == "2025-Q3" and detect_period("LTM")["period"] == "LTM"
    assert detect_period("Revenue") is None
    assert detect_unit("Revenue (€M)") == "EUR_M" and detect_unit("Gross margin (%)") == "PCT" and detect_unit("€bn") == "EUR_BN"
    assert unit_from_raw("€1,500M") == "EUR_M" and unit_from_raw("24%") == "PCT" and unit_from_raw("3.2 pp") == "PP"


def test_fact_model_is_traceable_and_derives_changes():
    fm = facts.build_fact_model(sorted((CASE / "sources").glob("*")))
    rev = next(f for f in fm["facts"] if f["claim"].startswith("Total — Revenue FY2025"))
    assert rev["values"][0]["value"] == 1460 and rev["values"][0]["unit"] == "EUR_M" and rev["values"][0]["period"] == "FY2025"
    assert rev["source"] == {"file": "pnl_by_category.csv", "sheet": None, "range": "C6", "loc": "sheet"}
    ch = next(f for f in fm["facts"] if f["fact_type"] == "derived_change" and f["claim"].startswith("Total — revenue"))
    assert ch["values"][0]["value"] == 100 and round(ch["values"][1]["value"], 1) == 7.4 and len(ch["derived_from"]) == 2
    gm = next(f for f in fm["facts"] if f["fact_type"] == "derived_change" and f["claim"].startswith("Total — gross margin"))
    assert gm["values"][0]["unit"] == "PP"  # a change of a percentage is in points
    fc = next(f for f in fm["facts"] if "€1,500M" in f["claim"])
    assert fc["values"][0]["period"] == "FY2025" and fc["values"][0]["basis"] == "estimate"  # forecast, not actual
    assert all(v["value"] != 202 for f in fm["facts"] for v in f["values"])  # "2026" is not split into "202"


# ── grounding ────────────────────────────────────────────────────────────────────────────────────

def test_grounding_only_uses_cited_facts():
    f = [{"id": "F1", "values": [{"value": 924, "unit": "EUR_M"}]}, {"id": "F2", "values": [{"value": 857, "unit": "EUR_M"}]}]
    g = grounding.ground_numbers("EBITDA fell from €924M to €857M, a €67M (7%) decline", f)
    assert [x["status"] for x in g] == ["grounded", "grounded", "derived", "derived"]
    assert grounding.ground_numbers("EBITDA will reach €1.2bn", f)[0]["status"] == "unsupported"
    assert grounding.ground_numbers("EBITDA fell to €857M", f[:1])[0]["status"] == "unsupported"  # not cited → not grounded
    assert grounding.ground_numbers("EBITDA fell to $857M", f)[0]["status"] == "unsupported"  # never across currencies


# ── the stored development run passes; planted defects are caught ─────────────────────────────

def test_dev_run_passes_all_checks():
    r = checks.check_work(RUN, CASE / "sources")
    assert r["status"] == "pass" and r["hard_failures"] == 0 and all(r["stopping_criteria"].values())


def test_fabricated_fact_is_hard_failure(work):
    _edit(work, "facts.json", lambda d: d["facts"][0]["values"][0].update(value=39))
    assert "FACT_FABRICATED" in _codes(checks.check_work(work, CASE / "sources"), hard=True)


def test_wrong_computation_is_arithmetic_error(work):
    _edit(work, "computed_facts.json", lambda d: d["facts"][3]["values"][0].update(value=1.9))
    r = checks.check_work(work, CASE / "sources")
    assert "ARITHMETIC_ERROR" in _codes(r, hard=True) and r["status"] == "blocked"


def test_invented_headline_number_is_blocked(work):
    def bump(d):
        s = next(x for x in d["slides"] if x["id"] == "s06")
        s["headline"] = "Freight cost rose €12M after the new carrier contract"
    _edit(work, "deck_plan.json", bump)
    _edit(work, "deck.json", bump)
    r = checks.check_work(work, CASE / "sources")
    bad = [i for i in r["issues"] if i["code"] == "UNSUPPORTED_NUMBER"]
    assert {i["artifact"] for i in bad} == {"deck_plan.json", "deck.json"} and all(i["hard"] for i in bad)
    assert not r["stopping_criteria"]["no_unsupported_headlines"]


def test_insight_on_rejected_hypothesis_is_contradicted(work):
    _edit(work, "insights.json", lambda d: d["insights"][1].update(hypotheses=["H1"]))
    assert "CONTRADICTED_AS_FACT" in _codes(checks.check_work(work, CASE / "sources"), hard=True)


def test_wrong_source_attribution(work):
    def src(d):
        next(x for x in d["slides"] if x["id"] == "s06")["source"] = "Source: pnl_by_category.csv"
    _edit(work, "deck.json", src)
    assert "WRONG_SOURCE" in _codes(checks.check_work(work, CASE / "sources"), hard=True)


def test_assumptions_are_flagged_not_hidden(work):
    def plain(d):
        next(x for x in d["slides"] if x["id"] == "s07")["headline"] = "Repricing electronics adds 3 pp there and 0.6 pp to the group"
    _edit(work, "deck_plan.json", plain)
    r = checks.check_work(work, CASE / "sources")
    w = [i for i in r["issues"] if i["code"] == "ASSUMPTION_IN_HEADLINE" and i["ref"] == "s07"]
    assert w and all(i["level"] == "warning" for i in w) and not any(i["hard"] for i in w)  # unhedged → warning
    hedged = [i for i in r["issues"] if i["code"] == "ASSUMPTION_IN_HEADLINE" and i["ref"] == "s08"]
    assert hedged and all(i["level"] == "info" for i in hedged)  # "about 1.1 pp" is stated as an estimate


def test_storyline_and_architecture_quality_checks(work):
    def one(d):
        d["candidates"] = d["candidates"][:1]
        d["key_line"][1]["insights"] = []
    _edit(work, "storyline.json", one)

    def plan(d):
        d["slides"].append({"id": "s99", "priority": "core", "headline": "Other topics", "reason_to_exist": ""})
        d["slides"] = [s for s in d["slides"] if s["id"] != "s06"]  # K2 loses its slide
    _edit(work, "deck_plan.json", plan)
    c = _codes(checks.check_work(work, CASE / "sources"))
    assert {"GT_SINGLE_CANDIDATE", "KEYLINE_UNSUPPORTED", "SLIDE_NO_REASON", "SLIDE_ORPHAN", "HEADLINE_TOPIC", "KEYLINE_NO_SLIDE"} <= c


def test_missing_business_question_blocks_storyline(work):
    (work / "project.json").unlink()
    c = _codes(checks.check_work(work, CASE / "sources"))
    assert "PROJECT_MISSING" in c


# ── evidence graph and ghost deck ────────────────────────────────────────────────────────────────

def test_trace_returns_lineage_to_source_cells():
    t = graph.trace(RUN, "Mix explains 1.45 pp of the gross-margin decline")
    assert t["match"] == "SL:s04"
    flat = json.dumps(t)
    assert "C0004" in flat and "pnl_by_category.csv" in flat and '"range": "D6"' in flat
    assert graph.trace(RUN, "completely unrelated sentence about weather")["match"] is None


def test_ghost_deck_reads_as_an_argument():
    from cpe.reasoning.ghost import ghost_markdown

    md = ghost_markdown(RUN)
    assert "Governing thought" in md and md.count("\n| ") >= 9 and "appendix" in md


# ── benchmark ────────────────────────────────────────────────────────────────────────────────────

def test_benchmark_dimensions_are_separate():
    r = benchmark.evaluate(CASE, RUN, {"model": "test"})
    assert r["factuality"]["status"] == "PASS" and r["fact_grounding"]["critical_fact_recall"] == 1.0
    assert r["insight_quality"]["conclusions"] == {"C1": True, "C2": True, "C3": True} and r["storyline"]["traps_triggered"] == []
    assert "score" not in r and "total" not in r  # no aggregate on purpose


def test_benchmark_catches_traps(work):
    def trap(d):
        d["governing_thought"] = "Margin fell because volume fell; revenue reached €1,500M but sold less"
    _edit(work, "storyline.json", trap)
    r = benchmark.evaluate(CASE, work)
    assert {"T1", "T2"} <= set(r["storyline"]["traps_triggered"])
    assert r["factuality"]["status"] == "FAIL"  # €1,500M is not grounded in the key line's facts


def test_reasoning_protocol_is_versioned():
    from cpe.reasoning import PROTOCOL_VERSION

    assert PROTOCOL_VERSION == "1.0"
    assert json.loads((RUN / "facts.json").read_text())["protocol"] == PROTOCOL_VERSION
    assert "development run — NOT evidence" in (RUN / "RUN.json").read_text()
    for d in ("development", "sealed", "external"):
        assert (ROOT / "evals" / "source_to_deck" / d).is_dir()


def test_conflicts_must_be_resolved_when_used(work):
    (work / "fact_conflicts.json").unlink()
    r = checks.check_work(work, CASE / "sources")
    bad = [i for i in r["issues"] if i["code"] == "FACT_CONFLICT_UNRESOLVED"]
    assert bad and bad[0]["level"] == "error" and "forecast_vs_actual" in bad[0]["message"]  # €1,500M forecast vs €1,460M actual
    assert not r["stopping_criteria"]["no_unresolved_conflict_in_use"]


def test_unresolved_high_critic_finding_stops_the_loop(work):
    _edit(work, "critique.json", lambda d: d["findings"][0].update(resolved=False))
    r = checks.check_work(work, CASE / "sources")
    assert "CRITIC_UNRESOLVED" in _codes(r) and not r["stopping_criteria"]["no_unresolved_high_critic_finding"]
    (work / "critique.json").unlink()
    assert "CRITIQUE_MISSING" in _codes(checks.check_work(work, CASE / "sources"))


def test_blind_storyline_ab_round(tmp_path):
    from cpe import human

    a, b, ctx = tmp_path / "a", tmp_path / "b", tmp_path / "ctx"
    for d in (a, b, ctx):
        d.mkdir()
    for case in ("c1", "c2", "c3"):
        (a / f"{case}.md").write_text(f"GT v1.6 agent: {case}\n- K1\n- K2")
        (b / f"{case}.md").write_text(f"GT v1.7 agent: {case}\n- K1'\n- K2'\n- K3'")
        (ctx / f"{case}.md").write_text(f"Question for {case}?")
    rd, kp = tmp_path / "s1", tmp_path / "keys" / "s1" / "key.json"
    r = human.build_text_round(rd, [("agent-1.6->agent-1.7", str(a), str(b))], context_dir=ctx, repeats=1, key_out=kp)
    assert r["pairs"] == 4 and kp.exists() and not (rd / "key.json").exists()
    bundle = (rd / "pairs.json").read_text() + (rd / "STATUS.json").read_text()
    assert "1.6" not in bundle and "1.7" not in bundle and "agent" not in bundle
    pairs = json.loads((rd / "pairs.json").read_text())
    assert pairs["meta"]["kind"] == "text" and all("context" in p for p in pairs["pairs"])
    for p in pairs["pairs"]:
        human.record_vote(rd, {"evaluator": "ana", "pair": p["id"], "left": p["images"][0], "right": p["images"][1], "choice": "left"})
    rep = human.report(rd, kp)
    assert rep["comparisons"] == 3 and rep["by_archetype"].keys() == {"storyline"}
    z = human.package_round(rd, tmp_path / "s1.zip")
    assert z["texts"] == 3 * 3 and z["images"] == 0  # A, B and context per case


def test_fact_model_on_spanish_excel_case():
    case = ROOT / "evals" / "source_to_deck" / "development" / "churn_es"
    fm = facts.build_fact_model(sorted((case / "sources").glob("*")))
    cli = next(f for f in fm["facts"] if f["claim"].startswith("Particulares — Clientes 2025"))
    assert cli["values"][0]["unit"] == "" and cli["source"]["sheet"] == "Clientes" and cli["source"]["range"] == "C2"  # % of a neighbour column does not spread
    ing = next(f for f in fm["facts"] if f["claim"].startswith("Particulares — Ingresos 2025"))
    assert ing["values"][0]["unit"] == "EUR_M" and ing["source"]["sheet"] == "Ingresos"  # "M€"
    txt = next(f for f in fm["facts"] if "resolución" in f["claim"])
    assert [v["value"] for v in txt["values"]] == [2.1, 4.6]  # Spanish decimal comma
    assert next(f for f in fm["facts"] if "30.000" in f["claim"])["values"][0]["value"] == 30000  # Spanish thousands


# ── v1.7: integrity metric (waterfall scorer blind spot, r3) ─────────────────────────────────────

def test_broken_slide_cannot_score_well():
    from cpe.qa.archetypes import fitness
    from cpe.qa.composition import BROKEN_CODES, integrity_issues

    ok = {"utilization": 0.9, "empty": 0.1, "ink": 0.15, "offcentre": 0.05, "emphasis": 0.2, "regions": 2, "ratio": 2.0, "edges": 3, "proof": 1.0}
    good = fitness("waterfall", {**ok, "integrity": 1.0})["score"]
    broken = fitness("waterfall", {**ok, "integrity": 0.0})
    assert good >= 99 and good - broken["score"] >= 30 and broken["worst_critical"] == 0.0
    issues = [{"slide": "w1", "level": "error", "code": "OFF_SLIDE"}, {"slide": "k1", "level": "error", "code": "LOW_CONTRAST"},
              {"slide": "w2", "level": "warning", "code": "WATERFALL_NEGATIVE"}, {"slide": "h1", "level": "error", "code": "HEADLINE_TOPIC"}]
    assert integrity_issues(issues, "w1") == ["OFF_SLIDE"] and integrity_issues(issues, "w2") == ["WATERFALL_NEGATIVE"]
    assert integrity_issues(issues, "k1") == [] and integrity_issues(issues, "h1") == []  # contrast / authoring are not "broken"
    assert "LOW_CONTRAST" not in BROKEN_CODES


def test_r3_is_development_data_with_blind_result_preserved():
    from cpe import human

    rd = ROOT / "evals" / "human_reference" / "rounds" / "r3"
    st = human.read_status(rd)
    assert st["used_for_calibration"] is True and "expert" in st["evidence_standard"]
    v = json.loads((rd / "VALIDATION_v1.5.json").read_text())
    assert (v["challenger_wins"], v["baseline_wins"], v["ties"]) == (9, 1, 28)
    prof = json.loads((ROOT / "src" / "cpe" / "qa" / "archetype_profiles.json").read_text())
    assert prof["base"]["integrity"]["w"] >= 10 and prof["archetypes"]["kpi_dashboard"]["metrics"]["utilization"]["status"] == "provisional"
