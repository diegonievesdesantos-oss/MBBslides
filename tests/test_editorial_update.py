"""v3.1 update workflow (spec §49-54, §88): messages.review decides whether the old argument holds; the Action
Title Engine checks the wording of what is true now; nothing is approved without a person."""
import json

from cpe.reasoning import messages
from cpe.reasoning.deck_update import ingest_deck, update_plan
from test_v20 import _approve, _bc_deck, _deck_with


def _plan(tmp_path, slides):
    _deck_with(tmp_path / "d.pptx", slides)
    return update_plan(ingest_deck(tmp_path / "d.pptx"), [])


SLIDES = [
    ("Las dos fases se pagan en menos de 5 años", [("Concepto", "Fase 1", "Fase 2"), ("Payback simple (años)", "4,4", "3,1")], None),
    ("El ahorro anual alcanza 1,2 M€ en 2027", [("Concepto", "2027"), ("Ahorro anual (M€)", "1,2")], None),
    ("Plan de inversión", [("Concepto", "Fase 1"), ("Inversión (M€)", "2,0")], None),
]


def test_holding_headline_is_preserved(tmp_path):
    plan = _plan(tmp_path, SLIDES)
    e = {"edits": []}
    rev = {r["slide"]: r for r in messages.review(plan, e)}
    messages.headline_edits(list(rev.values()), e, plan)
    assert rev[1]["verdict"] != "no longer holds" and not [x for x in e["edits"] if x["op"] == "set_headline"]


def test_number_changes_but_claim_holds_updates_figures_without_a_rewrite(tmp_path):
    plan = _plan(tmp_path, SLIDES)
    e = {"edits": []}
    _approve(plan, e, 2, "title", "€1,2 M", "1,4")
    rev = {r["slide"]: r for r in messages.review(plan, e)}
    messages.headline_edits(list(rev.values()), e, plan)
    assert rev[2]["verdict"] == "figures updated"
    assert not any(x["op"] == "set_headline" and x["slide"] == 2 for x in e["edits"])  # the number edit carries the change


def test_claim_no_longer_holds_goes_through_the_ate_and_stays_unapproved(tmp_path):
    plan = _plan(tmp_path, SLIDES)
    e = {"edits": []}
    _approve(plan, e, 1, "exhibit[0].rows[0][1]", "4,4", "6,1")
    _approve(plan, e, 1, "exhibit[0].rows[0][2]", "3,1", "3,1")
    rev = messages.review(plan, e)
    messages.headline_edits(rev, e, plan)
    sh = next(x for x in e["edits"] if x["op"] == "set_headline" and x["slide"] == 1)
    assert sh["approved"] is False
    assert sh["proposition"]["statement"] == sh["text"] or sh["editorial"]["status"] == "rejected"
    assert sh["editorial"]["status"] in ("passed", "rejected") and "candidates" in sh["editorial"]
    assert "6,1" in sh["text"]


def test_agent_candidates_are_selected_by_the_ate(tmp_path):
    plan = _plan(tmp_path, SLIDES)
    e = {"edits": []}
    _approve(plan, e, 1, "exhibit[0].rows[0][1]", "4,4", "6,1")
    _approve(plan, e, 1, "exhibit[0].rows[0][2]", "3,1", "3,1")
    rev = messages.review(plan, e)
    messages.headline_edits(rev, e, plan)
    sh = next(x for x in e["edits"] if x["op"] == "set_headline")
    sh["candidates"] = ["Plan de pagos", "La fase 1 tarda ahora 6,1 años en pagarse y la fase 2, 3,1 años"]
    messages.headline_edits(messages.review(plan, e), e, plan)
    sh = next(x for x in e["edits"] if x["op"] == "set_headline")
    assert sh["text"] != "Plan de pagos" and sh["approved"] is False


def test_topic_title_kept_by_default_and_flagged_with_normalize(tmp_path):
    plan = _plan(tmp_path, SLIDES)
    e = {"edits": []}
    messages.headline_edits(messages.review(plan, e), e, plan)
    assert not any(x["op"] == "set_headline" and x["slide"] == 3 for x in e["edits"])  # conservative default
    messages.headline_edits(messages.review(plan, e), e, plan, normalize=True)
    sh = next(x for x in e["edits"] if x["op"] == "set_headline" and x["slide"] == 3)
    assert sh["needs_wording"] and sh["text"] is None and sh["approved"] is False and "HEADLINE_TOPIC" in sh["editorial"]["hard"]
    sh["candidates"] = ["La fase 1 requiere una inversión de 2,0 M€"]
    messages.headline_edits(messages.review(plan, e), e, plan, normalize=True)
    sh = next(x for x in e["edits"] if x["op"] == "set_headline" and x["slide"] == 3)
    assert sh["text"] == "La fase 1 requiere una inversión de 2,0 M€" and not sh["needs_wording"] and sh["approved"] is False
    # a reviewer's own decision is never touched again
    sh["approved"] = True
    messages.headline_edits(messages.review(plan, e), e, plan, normalize=True)
    assert next(x for x in e["edits"] if x["op"] == "set_headline" and x["slide"] == 3)["approved"] is True


def test_rebuilt_slide_always_goes_through_the_ate(tmp_path):
    from cpe.cli import main
    from cpe.editorial import compile_editorial

    _bc_deck(tmp_path / "old.pptx")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "n.md").write_text("# Nota\n\nSin cifras nuevas.\n", encoding="utf-8")
    work = tmp_path / "work"
    assert main(["update", str(tmp_path / "old.pptx"), str(tmp_path / "src"), "-o", str(work), "--normalize-editorial"]) == 0
    assert json.loads((work / "update.json").read_text())["normalize_editorial"] is True
    plan = json.loads((work / "update_plan.json").read_text(encoding="utf-8"))
    e = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    for where, raw, new in (("exhibit[0].rows[5][1]", "4,9", "6,1"), ("exhibit[0].rows[5][2]", "4,1", "4,5")):
        _approve(plan, e, 2, where, raw, new)
    (work / "edits.json").write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    assert main(["update", "--rebuild", str(work), "--no-render"]) == 0
    spec = json.loads((work / "rewrite" / "deck.json").read_text(encoding="utf-8"))
    s = spec["slides"][0]
    assert spec["meta"]["editorial_mode"] == "mbb_strict" and s["proposition"]["statement"] and s["evidence"]
    compiled, rep = compile_editorial(spec)
    assert compiled["slides"][0]["_editorial"]["compiled"] and rep["mode"] == "mbb_strict"
    rs = json.loads((work / "rewrite" / "out" / "editorial_report.json").read_text(encoding="utf-8"))
    assert rs["slides"][0]["proposition"]["statement"]  # the rebuild ran the compiler before the planner
    e = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    assert all(not x.get("approved") for x in e["edits"] if x["op"] in ("set_headline", "replace_slide"))


def test_unworded_normalization_is_never_applied(tmp_path):
    from cpe.reasoning.deck_patch import write_patch

    _deck_with(tmp_path / "d.pptx", SLIDES)
    edits = tmp_path / "edits.json"
    edits.write_text(json.dumps({"edits": [{"op": "set_headline", "slide": 3, "text": None, "needs_wording": True, "approved": True}]}), encoding="utf-8")
    r = write_patch(tmp_path / "d.pptx", edits, tmp_path / "new.pptx")
    assert not r["applied"] and r["failed"] and "needs_wording" in r["failed"][0]["why"]
