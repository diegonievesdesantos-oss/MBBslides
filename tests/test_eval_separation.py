"""Regression ≠ holdout ≠ human evaluation: the separation is enforced in code."""
import hashlib
import json

import pytest

from conftest import ROOT
from cpe import evals


def test_suites_have_distinct_roles():
    assert evals.SUITES["regression"]["gate"] and evals.SUITES["regression"]["baseline"]
    for h in ("holdout_v1", "holdout_v2"):
        assert not evals.SUITES[h]["gate"] and evals.SUITES[h]["baseline"] is None
    assert evals.SUITES["holdout_v1"]["retired"]
    reg = {p.name for p in (ROOT / evals.SUITES["regression"]["cases"]).glob("*.json")}
    v1 = {p.name for p in (ROOT / evals.SUITES["holdout_v1"]["cases"]).glob("*.json")} - {"SEAL.json"}
    v2 = {p.name for p in (ROOT / evals.SUITES["holdout_v2"]["cases"]).glob("*.json")}
    assert reg and v1 and v2 and not reg & v1 and not reg & v2 and not v1 & v2


@pytest.mark.parametrize("suite", ["holdout_v1", "holdout_v2"])
def test_holdout_cannot_be_baselined(tmp_path, suite):
    with pytest.raises(ValueError, match="never baselined"):
        evals.run_suite(None, tmp_path, suite=suite, update_baseline=True)


def test_holdout_v1_is_sealed_and_retired():
    assert (ROOT / "evals" / "holdout" / "public" / "RETIRED.md").exists()
    seal = json.loads((ROOT / "evals" / "holdout" / "public" / "SEAL.json").read_text())
    files = {p.name for p in (ROOT / "evals" / "holdout" / "public").glob("*.json")} - {"SEAL.json"}
    assert set(seal["files"]) == files
    for name, digest in seal["files"].items():
        assert hashlib.sha256((ROOT / "evals" / "holdout" / "public" / name).read_bytes()).hexdigest() == digest, f"{name} changed after sealing"


def test_recording_holdout_leaves_regression_untouched(tmp_path):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"regression": {"suite_composition": 87.3}}))
    s = {"suite_composition": 70.0, "cases": [], "environment": {"fingerprint": "x"}}
    evals.record_result("holdout_v2", s, path=latest, allow_dirty=True)
    d = json.loads(latest.read_text())
    assert d["regression"]["suite_composition"] == 87.3 and d["holdout"]["v2"]["suite_composition"] == 70.0


def test_private_holdout_absent_does_not_break_and_never_touches_baselines(tmp_path):
    from cpe import private_holdout

    before = (ROOT / "evals" / "regression" / "baseline.json").read_bytes()
    r = private_holdout.run(root=tmp_path / "no_private", out=tmp_path / "out")
    assert r["status"] == "skipped" and "not present" in r["reason"]
    assert (ROOT / "evals" / "regression" / "baseline.json").read_bytes() == before


def test_private_material_is_gitignored():
    gi = (ROOT / ".gitignore").read_text()
    assert "/.private/" in gi and "/private_results/" in gi
