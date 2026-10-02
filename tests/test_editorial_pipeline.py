"""v3.1 pipeline integration (spec §35-38, §76-78, §81-83, §87)."""
import copy
import json

import pytest

from cpe import pipeline
from cpe.core import planner
from cpe.editorial import compile_editorial
from cpe.render import renderer

GOOD = "Revenue grew 12% in 2026 to €224m"


def spec(headline=GOOD, mode="mbb_strict", statement="Revenue grew 12% in 2026"):
    return {
        "meta": {"title": "Pipeline test", "deck_type": "business_review", "theme": "meridian", "editorial_mode": mode, "language": "en"},
        "storyline": {"framework": "SCR", "governing_thought": "Revenue growth is back and should be protected",
                      "key_line": [{"id": "K1", "role": "situation", "message": "Revenue grew 12% in 2026"}]},
        "slides": [
            {"id": "s01", "kind": "cover", "title": "Pipeline test"},
            {"id": "s02", "kind": "content", "section": "K1", "purpose": "Show the revenue trend", "message_type": "trend",
             "proposition": {"statement": statement, "role": "observation", "claim_type": "trend", "subject": "revenue", "direction": "up",
                             "magnitude": "12%", "timeframe": "2026", "evidence_ids": ["F1"], "confidence": "high"},
             "headline": headline, "evidence": [{"id": "F1", "claim": "Revenue 2025 €200m, 2026 €224m", "values": [200, 224]}],
             "visual": {"type": "column", "data": {"categories": ["2025", "2026"], "series": [{"name": "Revenue (€m)", "values": [200, 224]}]}},
             "source": "Company accounts"},
        ],
    }


@pytest.fixture
def no_render(monkeypatch):
    def fail(*a, **k):
        raise renderer.RenderError("render disabled in this test")

    monkeypatch.setattr(renderer, "render", fail)


def test_ate_runs_before_compose_and_planner(tmp_path, monkeypatch, no_render):
    seen = {}
    real_plan = planner.plan

    def spy_plan(s, *a, **k):
        seen.setdefault("plan", copy.deepcopy(s))
        return real_plan(s, *a, **k)

    def spy_compose(s, scratch, verbose=False):
        seen["compose"] = copy.deepcopy(s)
        return s, {}

    monkeypatch.setattr(pipeline, "plan", spy_plan)
    import cpe.compose as comp

    monkeypatch.setattr(comp, "compose", spy_compose)
    pipeline.run(spec(), tmp_path, max_iter=1, verbose=False, compose=True)
    assert seen["compose"]["slides"][1]["_editorial"]["compiled"]
    assert seen["plan"]["slides"][1]["_editorial"]["status"] == "passed"


def test_planner_keeps_its_own_headline_lint(tmp_path):
    compiled, _ = compile_editorial(spec("Revenue grew significantly in 2026", statement="Revenue grew significantly in 2026"), profile={})
    _, issues = planner.plan(compiled)
    assert any(i["code"] == "HEADLINE_VAGUE" for i in issues)  # the planner's lint, independent of the ATE


def test_strict_spec_planned_without_compiler_is_flagged():
    _, issues = planner.plan(spec())
    assert any(i["code"] == "EDITORIAL_NOT_COMPILED" and i["level"] == "error" for i in issues)
    _, issues = planner.plan(compile_editorial(spec())[0])
    assert not any(i["code"] == "EDITORIAL_NOT_COMPILED" for i in issues)


def test_artifacts_metadata_and_separate_verdicts(tmp_path, no_render):
    rep = pipeline.run(spec(), tmp_path, max_iter=1, verbose=False)
    for f in ("editorial_report.json", "editorial_report.md", "headline_strip.md", "editorial_ghost_deck.md", "ghost_deck.md", "qa_report.md"):
        assert (tmp_path / f).exists(), f
    resolved = json.loads((tmp_path / "resolved.json").read_text())
    ed = resolved["slides"][1]["_editorial"]
    assert ed["compiled"] and ed["status"] == "passed" and ed["headline_type"] == "factual"
    assert set(rep["dimensions"]) == {"factual", "editorial", "visual", "authoring", "brand"}
    assert "Editorial QA" in (tmp_path / "qa_report.md").read_text()


def test_failing_editorial_qa_fails_the_deck_even_when_visual_qa_passes(tmp_path, no_render):
    # causal wording on a trend: the lint cannot see it, the editorial layer can
    rep = pipeline.run(spec("A new pricing policy drove 12% revenue growth in 2026"), tmp_path, max_iter=1, verbose=False)
    assert rep["qa_passed_without_editorial"] and not rep["dimensions"]["editorial"]["passed"] and not rep["passed"]
    assert (tmp_path / "deck.pptx").exists()  # still rendered for debugging (spec §83)
    rep = pipeline.run(spec("A new pricing policy drove 12% revenue growth in 2026", mode="standard"), tmp_path / "std", max_iter=1, verbose=False)
    assert rep["dimensions"]["editorial"]["passed"]  # standard mode: a warning, not a gate


def test_visual_autofix_never_rewrites_the_compiled_headline(tmp_path, monkeypatch, no_render):
    from cpe.qa import autofix

    calls = {"n": 0}

    def propose(current, resolved, issues, tried):
        calls["n"] += 1
        return ([{"op": "set", "slide": "s02", "path": "headline", "value": "Revenue up", "reason": "shorten"}] if calls["n"] == 1 else []), []

    monkeypatch.setattr(autofix, "propose", propose)
    pipeline.run(spec(), tmp_path, max_iter=2, verbose=False)
    resolved = json.loads((tmp_path / "resolved.json").read_text())
    assert resolved["slides"][1]["headline"] == GOOD


def test_compile_is_idempotent_and_deterministic():
    a, ra = compile_editorial(spec(headline="Revenue evolution"), profile={})
    b, rb = compile_editorial(a, profile={})
    c, _ = compile_editorial(spec(headline="Revenue evolution"), profile={})
    strip = lambda s: [x.get("headline") for x in s["slides"]]  # noqa: E731
    assert strip(a) == strip(b) == strip(c)
    assert ra["summary"]["hard_errors"] == rb["summary"]["hard_errors"]


def test_autofixed_spec_keeps_the_authoring_contract_clean():
    from cpe.editorial import strip_editorial

    compiled, _ = compile_editorial(spec(), profile={})
    assert "_editorial" in compiled["slides"][1] and "_editorial" not in strip_editorial(compiled)["slides"][1]
