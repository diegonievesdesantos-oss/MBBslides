"""Composition metrics, the composition engine and the eval gate."""
import json

from conftest import content_slide, mini_spec, needs_render
from cpe.evals import compare
from cpe.pipeline import run
from cpe.qa.composition import _components, _largest_empty_rect


def test_largest_empty_rectangle_and_regions():
    assert _largest_empty_rect([[0, 0, 1], [0, 0, 1], [1, 1, 1]]) == 4
    assert _largest_empty_rect([[0] * 5] * 4) == 20
    assert _largest_empty_rect([[1, 1], [1, 1]]) == 0
    g = [[1, 1, 0, 0, 0], [1, 1, 0, 1, 1], [0, 0, 0, 1, 1]]
    assert _components(g) == 2  # two solid masses
    assert _components([[1, 0, 0, 0, 1]]) == 0  # specks are ignored


def test_eval_gate_detects_regressions():
    base = {"cases": [{"case": "x", "ok": True, "qa_errors": 0, "composition": 90.0, "slides": {"s1": {"score": 90.0, "flags": []}}}]}
    ok = [{"case": "x", "ok": True, "qa_errors": 0, "composition": 89.0, "slides": {"s1": {"score": 89.0, "flags": []}}}]
    assert compare(ok, base) == ([], [])
    bad = [{"case": "x", "ok": True, "qa_errors": 1, "composition": 80.0, "slides": {"s1": {"score": 80.0, "flags": ["DEAD_SPACE"]}}}]
    reg, _ = compare(bad, base)
    assert any("QA errors" in r for r in reg) and any("composition" in r for r in reg) and any("new flags" in r for r in reg)
    crashed = [{"case": "x", "ok": False, "error": "boom"}]
    assert compare(crashed, base)[0]


@needs_render
def test_composition_metrics_flag_dead_space(tmp_path):
    sparse = content_slide(headline="Two decisions are needed to start the programme in January", message_type="recommendation", evidence=[],
                           visual={"type": "table", "title": "Decisions", "columns": [{"label": "Decision"}, {"label": "Owner"}],
                                   "rows": [["Approve the reset", "CCO"], ["Approve the pilot", "CFO"]]},
                           commentary={"points": ["Both are reversible"]}, layout="table_commentary")
    rep = run(mini_spec([sparse]), tmp_path, max_iter=1, compose=False)
    sl = rep["composition"]["slides"][0]
    assert "DEAD_SPACE" in sl["flags"] and sl["score"] < 75
    assert any(i["code"] == "COMPOSITION_DEAD_SPACE" for i in rep["issues"])  # reported as an author action


@needs_render
def test_composition_engine_beats_the_default_on_sparse_content(tmp_path):
    sparse = content_slide(headline="Two decisions are needed to start the programme in January", message_type="recommendation", evidence=[],
                           visual={"type": "table", "title": "Decisions", "columns": [{"label": "Decision", "width": 4.5}, {"label": "Owner"}, {"label": "Impact (€M)", "kind": "number"}],
                                   "rows": [["Approve the pricing reset", "CCO", 60], ["Approve the pilot budget", "CFO", 18], ["Approve the programme office", "CFO", 12]]},
                           commentary={"points": ["Wave 1 is self-funding by Q4", "The pilot go / no-go returns to the board"]})
    rep = run(mini_spec([sparse]), tmp_path, max_iter=1, compose=True)
    d = rep["composition"]["decisions"]["t1"]
    assert d["chosen"]["score"] > d["default_score"] + 5  # measurably better than the compatible default
    assert any(c["verdict"].startswith("compatible but editorially weak") for c in d["candidates"])
    assert (tmp_path / "composition.md").exists()
    fixed = json.loads((tmp_path / "deck.autofixed.json").read_text())
    assert fixed["slides"][0]["_composed"] is True
