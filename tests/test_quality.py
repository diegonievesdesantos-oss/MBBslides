"""v1.4: distribution-aware quality reporting, absolute gates, attribution, profile governance."""
import json
import re

import pytest

from conftest import ROOT
from cpe import evals, quality
from cpe.qa import archetypes
from cpe.qa.archetypes import ARCHETYPES, PROFILES, fitness


def _results(spec: dict[str, list[float]], case="c") -> list[dict]:
    slides, i = {}, 0
    for arch, scores in spec.items():
        for s in scores:
            i += 1
            slides[f"s{i}"] = {"score": s, "archetype": arch, "flags": ["DEAD_SPACE"] if s < 60 else [], "attribution": {}}
    return [{"case": case, "ok": True, "composition": None, "slides": slides}]


def test_macro_archetype_score_weighs_archetypes_equally():
    # many excellent tables cannot hide a bad process
    r = _results({"table": [98] * 20, "process": [40] * 2})
    p = quality.profile(r, gates={"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "archetypes": {}})
    assert p["slide_mean"] > 90
    assert p["macro_archetype_score"] == pytest.approx((98 + 40) / 2)
    assert p["weakest_archetype"] == "process" and p["weakest_archetype_score"] == 40


def test_percentiles_and_shares():
    vals = list(range(1, 101))
    assert quality.percentile(vals, 10) == pytest.approx(10.9)
    assert quality.percentile(vals, 50) == pytest.approx(50.5)
    p = quality.profile(_results({"chart": [95] * 7 + [75, 65, 30]}), gates={"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "archetypes": {}})
    assert p["distribution"]["p10"] < 70 and p["distribution"]["median"] == 95
    assert p["share_slides_above_90"] == 0.7 and p["share_slides_above_70"] == 0.8


def test_insufficient_coverage_does_not_pretend_to_pass():
    gates = {"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "rules": {"min_floor": {"status": "enforced"}},
             "archetypes": {"process": {"mean_floor": 70, "min_floor": 35}}}
    p = quality.profile(_results({"process": [20, 25]}), gates=gates)
    st = p["archetypes"]["process"]
    assert st["coverage"] == quality.INSUFFICIENT and st["health"] == quality.INSUFFICIENT
    assert all(not b["enforced"] for b in st["breaches"])  # reported, never gated on n=2
    assert "process" in p["archetype_coverage"]["insufficient"]


def test_relative_baseline_passes_but_absolute_floor_fails():
    """bad historically + still equally bad = relative gate green; the absolute gate catches it."""
    res = [{"case": "c", "ok": True, "qa_errors": 0, "composition": 40.0,
            "slides": {f"s{i}": {"score": 39.0 if i else 30.0, "archetype": "process", "flags": [], "attribution": {}} for i in range(8)}}]
    base = {"cases": [{"case": "c", "qa_errors": 0, "composition": 40.0, "slides": {f"s{i}": {"score": 39.0 if i else 30.0, "flags": []} for i in range(8)}}]}
    regressions, _ = evals.compare(res, base)
    assert regressions == []
    gates = {"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "rules": {"min_floor": {"status": "enforced"}, "mean_floor": {"status": "provisional"}},
             "archetypes": {"process": {"mean_floor": 70, "min_floor": 35, "max_share_below_floor": 0.25}}}
    p = quality.profile(res, gates=gates)
    assert p["archetypes"]["process"]["health"] == "NOT HEALTHY"
    fails = quality.gate_failures(p)
    assert fails == ["process: catastrophic_minimum (30.0 vs 35)"]  # mean floor is provisional: reported, not failing


def test_coverage_regression_fails_the_gate():
    p = quality.profile(_results({"process": [80] * 6}), gates={"coverage": {"diagnostic_below": 5, "gate_eligible_from": 8}, "archetypes": {}})
    assert quality.gate_failures(p, {"process": 10}) == ["process: coverage regression (10 → 6 slides)"]


def test_metric_penalty_attribution_sums_to_the_lost_points():
    for arch in ("process", "kpi_hero", "table", "statement"):
        obs = {"utilization": 0.31, "empty": 0.55, "ink": 0.03, "offcentre": 0.2, "emphasis": 0.02, "regions": 7, "ratio": 1.1, "edges": 9, "proof": 0.3}
        f = fitness(arch, obs)
        lost = sum(a["penalty"] for a in f["attribution"].values())
        assert lost == pytest.approx(100 - f["score"], abs=0.15)
        for a in f["attribution"].values():
            assert {"expected", "observed", "fitness", "weight", "penalty"} <= set(a)


def test_gates_file_is_complete_and_reasoned():
    g = json.loads((ROOT / "evals" / "archetype_gates.json").read_text())
    assert set(g["archetypes"]) == set(ARCHETYPES)
    assert g["coverage"]["diagnostic_below"] < g["coverage"]["gate_eligible_from"]
    for rule in g["rules"].values():
        assert rule["status"] in ("enforced", "provisional") and len(rule["rationale"]) > 40


# ── profile governance ──────────────────────────────────────────────────────────────────────────

def test_profiles_live_in_data_and_cover_every_archetype():
    data = json.loads(archetypes.PROFILES_PATH.read_text())
    assert set(data["archetypes"]) == set(ARCHETYPES) == set(PROFILES)
    for a, v in data["archetypes"].items():
        assert v["why"] and v["evidence"]["development"] and "human" in v["evidence"], a


def test_profile_file_is_canonically_formatted():
    text = archetypes.PROFILES_PATH.read_text()
    assert archetypes.format_profiles(json.loads(text)) == text, "run archetypes.format_profiles on the file (one metric per line keeps diffs readable)"


def test_every_profile_change_is_in_the_changelog():
    data = json.loads(archetypes.PROFILES_PATH.read_text())
    log = (ROOT / "evals" / "profile_changes.md").read_text()
    sections = dict(re.findall(r"^## (\d+\.\d+\.\d+)\n(.*?)(?=^## |\Z)", log, flags=re.S | re.M))
    for a, v in data["archetypes"].items():
        for m, spec in v["metrics"].items():
            if spec and spec.get("last_changed") not in (None, "1.2.0"):
                ver = spec["last_changed"]
                assert ver in sections, f"{a}.{m} changed in {ver} but evals/profile_changes.md has no {ver} section"
                assert f"{a}." in sections[ver], f"{a}.{m} changed in {ver} without an entry"
    provisional = [f"{a}.{m}" for a, v in data["archetypes"].items() for m, s in v["metrics"].items() if s and s.get("status") == "provisional"]
    assert provisional and all(p.split(".")[0] in log for p in provisional)
