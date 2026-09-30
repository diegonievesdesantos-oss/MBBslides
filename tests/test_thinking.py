import pytest

from conftest import content_slide, mini_spec
from cpe.core import storyline, visual_reasoning
from cpe.core.headline import lint_headline, numbers_in
from cpe.core.layout_selector import select
from cpe.core.planner import plan
from cpe.spec import DECK_TYPES, apply_patches, validate_structure


@pytest.mark.parametrize("h", ["Revenue evolution", "Market analysis", "Customer segmentation", "Resumen de mercado"])
def test_topic_headlines_are_rejected(h):
    score, issues = lint_headline(h)
    assert any(i["code"] == "HEADLINE_TOPIC" for i in issues) and score <= 50


@pytest.mark.parametrize("h", [
    "Revenue growth slowed to 3% as acquisition weakened in H2",
    "Three customer segments generate 72% of contribution margin",
    "Spain represents the largest untapped expansion opportunity",
])
def test_conclusion_headlines_pass(h):
    score, issues = lint_headline(h)
    assert not [i for i in issues if i["level"] == "error"] and score >= 80


def test_two_messages_and_vague():
    _, issues = lint_headline("Revenue grew strongly and costs fell across all business units")
    codes = {i["code"] for i in issues}
    assert "HEADLINE_TWO_MESSAGES" in codes


def test_headline_numbers_must_be_supported():
    s = content_slide(headline="Revenue grew 12% to €112M in 2025")
    _, issues = lint_headline(s["headline"], s)
    assert not [i for i in issues if i["code"] == "HEADLINE_NUMBER_UNSUPPORTED"]
    s = content_slide(headline="Revenue grew 45% in 2025")
    _, issues = lint_headline(s["headline"], s)
    assert [i for i in issues if i["code"] == "HEADLINE_NUMBER_UNSUPPORTED"]


def test_numbers_ignore_years_durations_identifiers():
    assert numbers_in("In 2025 a 24-month plan in wave 1 added 12%") == [(12.0, "%")]


def test_visual_reasoning_follows_the_message():
    assert visual_reasoning.recommend("change_bridge")[0]["visual"] == "waterfall"
    assert visual_reasoning.recommend("positioning")[0]["visual"] == "matrix_2x2"
    ranking = {"data": {"categories": ["A very long category label", "Another long label", "C"], "series": [{"name": "x", "values": [3, 2, 1]}]}}
    assert visual_reasoning.recommend("ranking", ranking)[0]["visual"] == "bar"
    many = {"data": {"categories": [str(y) for y in range(2010, 2026)], "series": [{"name": "a", "values": list(range(16))}, {"name": "b", "values": list(range(16))}]}}
    assert visual_reasoning.recommend("trend", many)[0]["visual"] == "line"
    pie = {"type": "pie", "data": {"categories": list("ABCDEFGH"), "series": [{"name": "s", "values": [1] * 8}]}}
    assert any(i["code"] == "VIS_PIE_SLICES" and i["fix"]["value"] == "bar" for i in visual_reasoning.validate({"id": "x"}, pie))


def test_auto_visual_is_resolved_with_rationale():
    s = content_slide(message_type="change_bridge", visual={"type": "auto", "data": {"steps": [{"label": "A", "value": 10, "type": "total"}, {"label": "d", "value": 2}, {"label": "B", "type": "total"}]}})
    res, _ = plan(mini_spec([s]))
    v = res["slides"][0]["_plan"]["visuals"][0]
    assert v["chosen"] == "waterfall" and v["why"]


def test_layout_selector_uses_roles_and_family():
    s = content_slide(visual={"type": "waterfall", "data": {"steps": []}}, commentary={"points": ["a", "b"]})
    lay, why = select(s)
    assert lay == "waterfall_drivers"
    s2 = content_slide(commentary={"points": ["a"]})
    lay2, _ = select(s2, prev_layout="exhibit_commentary_right")
    assert lay2 != "exhibit_commentary_right"


def test_structure_validation_requires_intent():
    spec = mini_spec([{"id": "x", "kind": "content", "visual": {"type": "bar", "data": {}}}])
    codes = {i["code"] for i in validate_structure(spec)}
    assert "INTENT_MISSING" in codes


@pytest.mark.parametrize("dt", DECK_TYPES)
def test_scaffold_every_deck_type(dt):
    spec = storyline.scaffold(dt, "T")
    assert spec["storyline"]["framework"] in storyline.FRAMEWORKS
    assert spec["slides"][1]["kind"] == "exec_summary"
    _, issues = plan(spec)
    assert any(i["code"] == "HEADLINE_PLACEHOLDER" for i in issues)  # skeleton must not pass silently


def test_storyline_lint_and_ghost_deck(alvora):
    assert not [i for i in storyline.lint_storyline(alvora) if i["level"] == "error"]
    gd = storyline.ghost_deck(alvora)
    assert "K2 · COMPLICATION" in gd and "75% of Iberian grocery growth" in gd


def test_density_split_and_capacity():
    rows = [[f"Row {i}", i] for i in range(30)]
    s = content_slide(visual={"type": "table", "title": "t", "columns": [{"label": "a"}, {"label": "b"}], "rows": rows}, message_type="comparison")
    res, issues = plan(mini_spec([s]))
    assert len(res["slides"]) >= 2 and any(i["code"] == "AUTO_SPLIT" for i in issues)
    long = content_slide(layout="exhibit_commentary_right", commentary={"points": ["word " * 60] * 6})
    _, issues = plan(mini_spec([long]))
    assert any(i["code"] == "CONTENT_OVER_CAPACITY" for i in issues)


def test_apply_patches():
    spec = mini_spec([content_slide()])
    new, log = apply_patches(spec, [
        {"op": "set", "slide": "t1", "path": "visual.type", "value": "bar"},
        {"op": "append", "slide": "t1", "path": "footnotes", "value": "Note"},
        {"op": "insert_slide_after", "slide": "t1", "value": {"id": "t2", "kind": "statement", "text": "x"}},
    ])
    assert new["slides"][0]["visual"]["type"] == "bar" and new["slides"][0]["footnotes"] == ["Note"]
    assert [s["id"] for s in new["slides"]] == ["t1", "t2"] and spec["slides"][0]["visual"]["type"] == "column"
