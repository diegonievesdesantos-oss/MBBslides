"""v3.1 CLI, fixtures runner and human round of the Editorial Logic Layer (spec §80, §90-94)."""
import json

import pytest

from cpe.cli import main

EX = "examples/alvora/deck.json"


def test_editorial_check_explain_ghost_on_the_strict_example(tmp_path, capsys):
    assert main(["editorial", "check", EX, "-o", str(tmp_path)]) == 0
    assert "Editorial QA: PASSED" in (tmp_path / "editorial_report.md").read_text()
    assert main(["editorial", "explain", EX]) == 0
    assert "candidates:" in capsys.readouterr().out
    assert main(["editorial", "ghost", EX, "-o", str(tmp_path / "g")]) == 0
    strip = (tmp_path / "g" / "headline_strip.md").read_text()
    assert "What should happen next?" in strip and "Coherence" in strip


def test_editorial_check_fails_closed_on_a_topic_title(tmp_path):
    d = json.loads(open(EX).read())
    d["slides"][3]["headline"] = "Revenue growth"
    p = tmp_path / "deck.json"
    p.write_text(json.dumps(d))
    assert main(["editorial", "check", str(p), "-o", str(tmp_path / "out")]) == 1
    rep = json.loads((tmp_path / "out" / "editorial_report.json").read_text())
    assert {"HEADLINE_TOPIC", "HEADLINE_UNRESOLVED"} <= {f["code"] for f in rep["findings"] if f["level"] == "error"}


def test_normalize_writes_provisional_propositions_to_confirm(tmp_path):
    d = json.loads(open(EX).read())
    for s in d["slides"]:
        s.pop("proposition", None)
    d["meta"].pop("editorial_mode")
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps(d))
    assert main(["editorial", "normalize", str(p), "-o", str(tmp_path / "n.json")]) == 0
    n = json.loads((tmp_path / "n.json").read_text())
    props = [s["proposition"] for s in n["slides"] if s.get("proposition")]
    assert len(props) == 11 and all(x["_to_confirm"] for x in props) and n["meta"]["editorial_mode"] == "standard"


def test_scaffold_is_strict(tmp_path):
    assert main(["scaffold", "--deck-type", "business_review", "-o", str(tmp_path / "d.json")]) == 0
    assert json.loads((tmp_path / "d.json").read_text())["meta"]["editorial_mode"] == "mbb_strict"


def test_fixture_runner_and_holdout_seal(tmp_path):
    from cpe.editorial import fixtures

    r = fixtures.run_set("dev")
    assert r["cases"] >= 200 and set(r["metrics"]) >= {"agreement", "valid_pass_rate", "invalid_catch_rate", "unsupported_claims_passed"}
    d = tmp_path / "h"
    d.mkdir()
    (d / "a.json").write_text("[]")
    (d / "SEAL.json").write_text(json.dumps({"files": {"a.json": "0" * 64}}))
    assert fixtures.verify_seal(d) == ["changed: a.json"]


def test_editorial_human_round_is_built_without_votes(tmp_path):
    from cpe import human

    pairs = [{"case": f"c{i}", "proposition": "Revenue grew 12% in 2026", "evidence": ["Revenue 2025 €200m, 2026 €224m"],
              "baseline": "Revenue evolution", "challenger": "Revenue grew 12% in 2026"} for i in range(3)]
    (tmp_path / "pairs.json").write_text(json.dumps(pairs))
    r = human.build_editorial_round(tmp_path / "round", tmp_path / "pairs.json", key_out=tmp_path / "private")
    assert r["headline"]["pairs"] >= 3
    rd = tmp_path / "round" / "headlines"
    assert not any((rd / "votes").iterdir())
    meta = json.loads((rd / "pairs.json").read_text())["meta"]
    assert "action title" in meta["instructions"]
    with pytest.raises(SystemExit):  # never overwritten once people voted
        (rd / "votes" / "ev1.jsonl").write_text("{}\n")
        human.build_editorial_round(tmp_path / "round", tmp_path / "pairs.json", key_out=tmp_path / "private")
