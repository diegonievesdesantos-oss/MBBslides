"""v1.4: robustness, sealed holdout v2, provenance, human agreement, engine/metric fixes."""
import hashlib
import json
import subprocess

import pytest

from conftest import ROOT
from cpe import evals, human, robustness
from cpe.results_report import render_block, verify_provenance

# ── robustness ──────────────────────────────────────────────────────────────────────────────────


def test_perturbations_are_small_deterministic_and_applicable():
    proc = {"id": "p", "headline": "Claims take five steps", "visual": {"type": "process", "data": {"steps": [{"title": "A", "text": "x y"}, {"title": "B"}]}},
            "source": "S"}
    a, b = robustness.more_steps(proc), robustness.more_steps(proc)
    assert a == b and len(a["visual"]["data"]["steps"]) == 4 and len(proc["visual"]["data"]["steps"]) == 2
    h = robustness.headline_longer(proc)["headline"]
    assert 1.15 <= len(h.split()) / len(proc["headline"].split()) <= 1.8
    assert robustness.more_rows(proc) is None  # not a table: does not apply
    assert "1,200,000" in robustness.full_numbers({"headline": "Savings of €1.2M", "visual": {}})["headline"]
    assert robustness.more_sources(proc)["source"].count(";") == 2


def test_catastrophic_changes_are_detected_and_gated_against_baseline():
    rows = [{"seed": "s", "perturbation": "headline_longer", "seed_score": 90, "score": 89, "delta": -1, "layout_change": False, "font_drop": 0, "new_visual_qa": [], "new_flags": [], "catastrophic": False},
            {"seed": "s", "perturbation": "more_rows", "seed_score": 90, "score": 85, "delta": -5, "layout_change": True, "font_drop": 2, "new_visual_qa": ["TEXT_OVERFLOW"], "new_flags": [], "catastrophic": True},
            {"seed": "t", "perturbation": "more_items", "seed_score": 95, "score": 55, "delta": -40, "layout_change": True, "font_drop": 0, "new_visual_qa": [], "new_flags": [], "catastrophic": True}]
    s = robustness.summarize(rows)
    assert s["catastrophic"] == 2 and s["variants"] == 3 and s["p90_drop"] > 20
    # v1.5 also enforces "no new visual QA error" against the baseline (here: 1 recorded)
    assert robustness.compare(s, {"catastrophic": 1, "variants": 3, "new_visual_errors": 1}) == ["catastrophic variants 1 → 2"]
    assert robustness.compare(s, {"catastrophic": 2, "variants": 3, "new_visual_errors": 1}) == []
    assert "composition" not in s  # a separate signal, never folded into the score


def test_robustness_seeds_are_development_slides():
    for s in robustness.load_seeds():
        assert (ROOT / "evals" / "regression" / "cases" / f"{s['case']}.json").exists()


# ── holdout v2 ──────────────────────────────────────────────────────────────────────────────────


def test_holdout_v2_hashes_are_immutable():
    assert evals.verify_seal(ROOT / "evals" / "holdout" / "v2" / "SEAL.json") == []
    seal = json.loads((ROOT / "evals" / "holdout" / "v2" / "SEAL.json").read_text())
    assert len(seal["files"]) >= 20 and "not a truly externally authored" in seal["authorship"]


def test_holdout_v2_refuses_the_development_loop(tmp_path):
    with pytest.raises(evals.HoldoutGuard, match="release candidate"):
        evals.run_suite(None, tmp_path, suite="holdout_v2")
    with pytest.raises((evals.HoldoutGuard, ValueError)):
        evals.run_suite(None, tmp_path, suite="holdout_v2", release_candidate=True, match="V01")


def test_holdout_v2_detects_tampering(tmp_path):
    d = tmp_path / "v2"
    (d / "cases").mkdir(parents=True)
    (d / "cases" / "a.json").write_text("{}")
    (d / "SEAL.json").write_text(json.dumps({"files": {"a.json": hashlib.sha256(b"{}").hexdigest()}}))
    assert evals.verify_seal(d / "SEAL.json") == []
    (d / "cases" / "a.json").write_text('{"tuned": true}')
    assert evals.verify_seal(d / "SEAL.json") == ["changed: a.json"]


def test_holdout_v2_is_not_in_ci_or_the_regression_loop():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "holdout_v2" not in ci and "holdout/v2" not in ci
    reg = {p.name for p in (ROOT / "evals" / "regression" / "cases").glob("*.json")}
    assert not reg & {p.name for p in (ROOT / "evals" / "holdout" / "v2" / "cases").glob("*.json")}


# ── provenance ──────────────────────────────────────────────────────────────────────────────────


def test_dirty_evaluation_cannot_be_published_as_release_truth(tmp_path):
    latest = tmp_path / "latest.json"
    dirty = {"suite_composition": 1.0, "cases": [], "environment": {"fingerprint": "f", "provenance": {"evaluated_commit": "a" * 40, "dirty": True, "dirty_paths": ["src/x.py"]}}}
    with pytest.raises(evals.DirtyEvaluation):
        evals.record_result("regression", dirty, path=latest)
    evals.record_result("regression", dirty, path=latest, allow_dirty=True)
    d = json.loads(latest.read_text())
    assert d["regression"]["provenance"]["release_truth"] is False
    assert any("dirty" in p for p in verify_provenance(d))


def test_evaluated_commit_is_recorded_and_verified_against_engine_inputs(tmp_path):
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    clean = {"evaluated_commit": head, "dirty": False, "release_truth": True}
    data = {k: {"provenance": clean} for k in ("regression", "examples", "robustness")}
    probs = verify_provenance(data)
    # HEAD vs HEAD: only uncommitted work could differ, and verify compares commits
    assert not any("dirty" in p or "not in this repository" in p for p in probs)
    data["regression"]["provenance"] = {**clean, "evaluated_commit": "0" * 40}
    assert any("not in this repository" in p for p in verify_provenance(data))
    data["regression"] = {"suite_composition": 87.5}
    assert any("no evaluated_commit" in p for p in verify_provenance(data))


def test_environment_records_full_provenance():
    from cpe import environment

    p = environment.provenance()
    assert {"evaluated_commit", "git_tree", "dirty", "engine_version", "container_digest", "eval_timestamp_utc"} <= set(p)
    assert "evals/results/" in environment.RESULT_PATHS and "src" in environment.ENGINE_PATHS


def test_readme_block_reports_distribution_not_a_single_number():
    block = render_block({"regression": {"suite_composition": 88.0, "overall": {"macro_archetype_score": 82.1, "weakest_archetype": "process", "weakest_archetype_score": 73.5},
                                         "distribution": {"p10": 71.8}}, "holdout": {}})
    assert "macro archetype" in block and "weakest archetype" in block and "P10" in block
    assert "Holdout v2" in block and "NOT RUN YET" in block
    assert "quality =" not in block.lower()


# ── human ───────────────────────────────────────────────────────────────────────────────────────


def _key():
    return {"p1": {"baseline": "a.png", "challenger": "b.png", "baseline_score": 40, "challenger_score": 80, "archetype": "process", "deck": "d", "slide": "s1"},
            "p2": {"baseline": "c.png", "challenger": "d.png", "baseline_score": 90, "challenger_score": 60, "archetype": "table", "deck": "d", "slide": "s2"},
            "p3": {"baseline": "e.png", "challenger": "f.png", "baseline_score": 70, "challenger_score": 70.5, "archetype": "chart", "deck": "d", "slide": "s3"}}


def test_score_human_agreement_per_pair():
    key = _key()
    votes = [{"pair": "p1", "left": "a.png", "right": "b.png", "choice": "right", "evaluator": "x"},   # humans: challenger, scorer: challenger → agree
             {"pair": "p2", "left": "c.png", "right": "d.png", "choice": "right", "evaluator": "x"},   # humans: challenger, scorer: baseline → disagree
             {"pair": "p3", "left": "e.png", "right": "f.png", "choice": "left", "evaluator": "x"}]    # no meaningful score gap → tie
    v = {x["pair"]: x["agreement"] for x in human.pair_verdicts(votes, key)}
    assert v == {"p1": "agree", "p2": "disagree", "p3": "tie"}
    md = human.disagreements_markdown(human.pair_verdicts(votes, key), "rx")
    assert "p2" in md and "**strong**" in md and "p1" not in md


def test_kendall_tau_b_and_bootstrap():
    assert human.kendall_tau_b([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    assert human.kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    lo, hi = human.bootstrap_ci([1, 2, 3, 4, 5, 6], [-1, -1, 0, 1, 1, 1])
    assert lo is not None and lo <= hi <= 1.0


def test_r1_is_preserved_and_status_changes_after_calibration(tmp_path):
    r1 = ROOT / "evals" / "human_reference" / "rounds" / "r1"
    key = json.loads((r1 / "key.json").read_text())
    assert len(json.loads((r1 / "pairs.json").read_text())["pairs"]) == 40 and len(key) == 40
    assert human.read_status(r1)["blind"] is True  # no votes have been used to change the engine
    rd = tmp_path / "rx"
    rd.mkdir()
    (rd / "pairs.json").write_text(json.dumps({"pairs": []}))
    st = human.mark_used_for_calibration(rd, "process profile")
    assert st["blind"] is False and st["used_for_calibration"] and "development data" in st["status"]


def test_no_votes_are_invented(tmp_path):
    latest = tmp_path / "latest.json"
    human.record_status(ROOT / "evals" / "human_reference" / "rounds" / "r1", path=latest)
    r1 = json.loads(latest.read_text())["human_reference"]["rounds"]["r1"]
    assert "0 votes" in r1["status"] and "challenger_preference" not in r1


def test_r2_quotas_keep_rounds_separate():
    import inspect

    assert "quotas" in inspect.signature(human.build_round).parameters
    # r2 now holds the votes of its single evaluator (v1.5); r1 still has none
    r2_votes = [f for f in (ROOT / "evals" / "human_reference" / "rounds" / "r2" / "votes").glob("*.jsonl")]
    assert len(r2_votes) == 1
    assert not list((ROOT / "evals" / "human_reference" / "rounds" / "r1" / "votes").glob("*.jsonl"))


# ── engine and metric fixes found by the battery / robustness ───────────────────────────────────


def test_bullets_and_commentary_are_both_kept():
    from cpe.core.layout_selector import content_roles

    s = {"visual": {"type": "bullets", "data": {"points": ["a", "b"]}}, "commentary": {"points": ["so what"]}}
    r = content_roles(s)
    assert r["text"]["points"] == ["a", "b"] and r["commentary"]["points"] == ["so what"]
    s2 = {**s, "visual": None, "exhibits": [{"type": "bar", "data": {}}, {"type": "bullets", "data": {"points": ["a"]}}]}
    assert content_roles(s2)["commentary"]["points"] == ["a", "so what"]  # merged beside an exhibit, not replaced


def test_text_forms_and_semantic_classification():
    from cpe.pptx.text_components import text_form
    from cpe.qa.archetypes import classify

    assert text_form(["One claim"]) == "argument" and text_form(["a", "b"]) == "list"
    assert text_form([" ".join(["word"] * 60)]) == "narrative" and text_form(["“A quote”"]) == "quote"
    assert classify({"visual": {"type": "bullets", "data": {"points": ["The contract expires in March"]}}})[0] == "statement"
    assert classify({"visual": {"type": "bullets", "data": {"points": ["a", "b", "c"]}}})[0] == "text_exhibit"
    flow1 = {"visual": {"type": "flow", "data": {"nodes": [{"id": "a", "col": 0}, {"id": "b", "col": 1}], "edges": []}}}
    assert classify(flow1)[0] == "process"


def test_figures_with_units_and_scaled_proof():
    from cpe.qa.composition import FIGURE_RE, _scaled_match

    for t in ("4.5 days", "2 min", "€13M", "−3 pts", "2,35 €"):
        assert FIGURE_RE.match(t), t
    for t in ("Field adjuster, 9 days", "12 direcciones"):
        assert not FIGURE_RE.match(t), t
    assert _scaled_match(1.2, "€bn", {1210.0}) and _scaled_match(61000000.0, "", {61.0})
    assert not _scaled_match(1.5, "€bn", {1210.0}) and not _scaled_match(350.0, "km", {0.35})
