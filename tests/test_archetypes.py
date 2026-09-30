"""Archetype-aware composition: a slide is judged against what it is trying to be."""
from conftest import content_slide, mini_spec, needs_render
from cpe.pipeline import run
from cpe.qa.archetypes import ARCHETYPES, PROFILES, classify, fitness

SPARSE = {"utilization": 0.30, "empty": 0.60, "ink": 0.03, "offcentre": 0.10, "emphasis": 0.30, "regions": 1, "ratio": 2.0, "edges": 2}
FULL = {"utilization": 0.97, "empty": 0.10, "ink": 0.18, "offcentre": 0.06, "emphasis": 0.30, "regions": 1, "ratio": 1.8, "edges": 3, "proof": 1.0}


def test_every_archetype_has_a_profile():
    assert set(ARCHETYPES) == set(PROFILES)


def test_sparse_statement_is_not_penalised_but_the_same_sparse_table_is():
    assert fitness("statement", SPARSE)["score"] >= 90
    table = fitness("table", {**SPARSE, "proof": 1.0})
    assert table["score"] < 60
    assert {d["flag"] for d in table["deviations"]} >= {"DEAD_SPACE", "UNDERUSED_CANVAS"}


def test_dense_table_is_handled():
    assert fitness("table", FULL)["score"] >= 95
    assert fitness("table", {**FULL, "ink": 0.30})["score"] >= 95  # a full, dense table is what a table should be


def test_kpi_hero_can_have_large_intentional_whitespace():
    hero = {"utilization": 0.40, "empty": 0.42, "ink": 0.05, "offcentre": 0.12, "emphasis": 0.45, "regions": 1, "ratio": 1.6, "edges": 2, "proof": 1.0}
    assert fitness("kpi_hero", hero)["score"] >= 90
    assert fitness("kpi_dashboard", hero)["score"] < fitness("kpi_hero", hero)["score"] - 15
    stuck_in_a_corner = {**hero, "utilization": 0.12, "empty": 0.79, "offcentre": 0.40}
    assert fitness("kpi_hero", stuck_in_a_corner)["score"] < 60


def test_matrix_expects_its_field_used_and_balanced():
    good = {**FULL, "utilization": 0.9}
    assert fitness("matrix", good)["score"] >= 95
    assert fitness("matrix", {**good, "utilization": 0.45, "empty": 0.45})["score"] < 70
    assert fitness("matrix", {**good, "offcentre": 0.30})["score"] < fitness("chart", {**good, "offcentre": 0.30})["score"]


def test_roadmap_must_use_the_width():
    assert fitness("roadmap", FULL)["score"] >= 95
    assert fitness("roadmap", {**FULL, "utilization": 0.55, "empty": 0.40})["score"] < 70


def test_waterfall_needs_its_chart_area():
    assert fitness("waterfall", FULL)["score"] >= 95
    assert fitness("waterfall", {**FULL, "utilization": 0.60, "empty": 0.45})["score"] < 65


def test_one_severe_failure_is_not_diluted_by_many_good_metrics():
    base = fitness("chart", FULL)["score"]
    one_bad = fitness("chart", {**FULL, "empty": 0.70})
    assert base - one_bad["score"] > 25  # the worst critical metric caps the score
    assert one_bad["worst_critical"] == 0.0


def test_archetype_comes_from_content_not_layout():
    t = content_slide(visual={"type": "table", "columns": [{"label": "A"}], "rows": [["x"]]})
    assert classify(t)[0] == classify({**t, "layout": "table_commentary"})[0] == classify({**t, "layout": "exhibit_full"})[0] == "table"
    assert classify({"kind": "statement", "text": "x"})[0] == "statement"
    assert classify(content_slide(visual={"type": "kpi", "data": {"items": [{"value": "4%", "label": "x"}]}}))[0] == "kpi_hero"
    assert classify(content_slide(visual={"type": "gantt", "data": {"periods": ["Q1"], "rows": []}}))[0] == "roadmap"
    assert classify(content_slide(visual={"type": "waterfall", "data": {"steps": []}}))[0] == "waterfall"


@needs_render
def test_rendered_statement_scores_well_where_the_v11_universal_score_penalised_it(tmp_path):
    spec = mini_spec([{"id": "st", "kind": "statement", "text": "We will win on service, not on price", "support": "The rest of this document explains why"}])
    rep = run(spec, tmp_path, max_iter=1, compose=False)
    sl = rep["composition"]["slides"][0]
    assert sl["archetype"] == "statement"
    assert sl["score"] >= 90 and sl["score_v1"] < 70
    assert not rep["editorial_advice"]
