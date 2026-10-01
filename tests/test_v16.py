"""v1.6 — external validation infrastructure: multi-rater voting packages, identical-image
controls, sealed run-once external holdout, unseen-template intake, cross-exhibit proof."""
import json
import zipfile

import pytest
from PIL import Image

from cpe import human
from cpe import private_holdout as ph


def _runs(tmp_path):
    roots = []
    for name, color, score in (("base", "red", 60.0), ("chal", "blue", 70.0)):
        d = tmp_path / name / "deck1"
        (d / "renders").mkdir(parents=True)
        slides = ["s1", "s2", "s3", "s4", "s5"]
        (d / "resolved.json").write_text(json.dumps({"slides": [{"id": s, "kind": "content", "_plan": {"layout": {"id": "x"}}} for s in slides]}))
        (d / "qa_report.json").write_text(json.dumps({"composition": {"slides": [{"slide_id": s, "score": score, "archetype": "chart"} for s in slides]}}))
        for i, _ in enumerate(slides, 1):
            Image.new("RGB", (40, 22), color).save(d / "renders" / f"slide-{i:02d}.png")
        roots.append(tmp_path / name)
    return roots


def _vote_all(rd, ev, choose):
    for p in json.loads((rd / "pairs.json").read_text())["pairs"]:
        human.record_vote(rd, {"evaluator": ev, "pair": p["id"], "left": p["images"][0], "right": p["images"][1], "choice": choose(p)})


def test_identical_controls_are_separate_from_preference(tmp_path):
    base, chal = _runs(tmp_path)
    rd, kp = tmp_path / "r", tmp_path / "k" / "key.json"
    human.build_round(rd, [("a->b", str(base), str(chal))], n=5, repeats=1, identical_controls=2, key_out=kp)
    key = json.loads(kp.read_text())
    ctrl = [k for k, v in key.items() if v.get("identical_control")]
    assert len(ctrl) == 2
    for c in ctrl:  # two different file names, same pixels
        a, b = key[c]["baseline"], key[c]["challenger"]
        assert a != b and (rd / "img" / a).read_bytes() == (rd / "img" / b).read_bytes()
    _vote_all(rd, "ana", lambda p: "tie" if p["id"].startswith("c") else "left")
    _vote_all(rd, "bo", lambda p: "left")
    rep = human.report(rd, kp)
    assert rep["comparisons"] == 4 * 2  # 4 main pairs × 2 raters; controls and repeats excluded
    ic = rep["identical_controls"]
    assert ic["pairs"] == 2 and ic["votes"] == 4 and ic["tie_rate"] == 0.5 and ic["by_rater"] == {"ana": 1.0, "bo": 0.0}
    assert "WITHIN" in rep["self_consistency"]["note"] and "BETWEEN" in rep["inter_rater"]["note"]
    assert rep["inter_rater"]["fleiss_kappa"] is not None and set(rep["by_rater"]) == {"ana", "bo"}


def test_voting_package_has_no_key_and_works_standalone(tmp_path):
    base, chal = _runs(tmp_path)
    rd, kp = tmp_path / "r", tmp_path / "k" / "key.json"
    human.build_round(rd, [("a->b", str(base), str(chal))], n=5, repeats=1, key_out=kp)
    human.close_round(rd, kp)  # worst case: the key is in the round (like r3 since v1.5)
    z = tmp_path / "pkg.zip"
    r = human.package_round(rd, z)
    names = zipfile.ZipFile(z).namelist()
    assert r["images"] == 8 and not any("key" in n or "STATUS" in n or "report" in n for n in names)
    assert {"r/vote_server.py", "r/VOTAR_WINDOWS.bat", "r/LEEME_README.txt", "r/pairs.json", "r/index.html"} <= set(names)
    # the stand-alone server records votes the round can import
    ex = tmp_path / "unz"
    zipfile.ZipFile(z).extractall(ex)
    import importlib.util

    spec = importlib.util.spec_from_file_location("vs", ex / "r" / "vote_server.py")
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)
    p = json.loads((ex / "r" / "pairs.json").read_text())["pairs"][0]
    vs._record({"evaluator": "cara", "pair": p["id"], "left": p["images"][1], "right": p["images"][0], "choice": "right"})
    with pytest.raises(ValueError):
        vs._record({"evaluator": "cara", "pair": p["id"], "left": "x.png", "right": "y.png", "choice": "left"})
    f = ex / "r" / "votes" / "cara.jsonl"
    assert human.import_votes(rd, f) == 1 and human.import_votes(rd, f) == 0  # idempotent, evaluator from file name
    assert human.done_pairs(rd, "cara") == [p["id"]]


def test_external_holdout_seal_and_run_once(tmp_path, monkeypatch):
    root = tmp_path / "external"
    (root / "decks").mkdir(parents=True)
    (root / "decks" / "a.json").write_text("{}")
    (root / "PROVENANCE.json").write_text(json.dumps({"authored_by_developer": False, "engine_renders_seen_by_author": False, "received": "2026-10-02"}))
    assert ph.external_status(root)["status"] == "EXTERNAL HOLDOUT: RECEIVED, NOT SEALED"
    ph.seal_external(root)
    assert ph.external_status(root)["status"] == "EXTERNAL HOLDOUT: READY"
    with pytest.raises(SystemExit):
        ph.seal_external(root)  # a seal is never rewritten
    (root / "decks" / "a.json").write_text('{"edited": true}')
    assert ph.external_status(root)["status"] == "EXTERNAL HOLDOUT: SEAL BROKEN"
    (root / "decks" / "a.json").write_text("{}")
    monkeypatch.setattr(ph, "RUNS", tmp_path / "RUNS.json")
    ph._mark_ran("external", "abc123")
    r = ph.run_external_holdout(root=root)
    assert not r["ran"] and "ALREADY RUN" in r["status"]


def test_self_authored_decks_are_never_external(tmp_path):
    root = tmp_path / "external"
    (root / "decks").mkdir(parents=True)
    (root / "decks" / "a.json").write_text("{}")
    (root / "PROVENANCE.json").write_text(json.dumps({"authored_by_developer": True, "engine_renders_seen_by_author": False}))
    assert "NOT INDEPENDENT" in ph.external_status(root)["status"]
    assert not ph.run_external_holdout(root=root)["ran"]


def test_cross_exhibit_proof_requires_explicit_single_quantities():
    from cpe.qa.proof import derive_across, headline_quantities, slide_scalars

    slide = {"visual": {"type": "bar", "unit": "€M", "data": {"categories": ["Revenue"], "series": [{"name": "Revenue", "values": [120]}]}},
             "exhibits": [{"type": "table", "columns": [{"label": "Line"}, {"label": "€M", "kind": "number"}],
                           "rows": [["Material", 50], ["Labour", 30], ["Total cost", 80]]}]}
    sc = slide_scalars(slide)
    assert {s["label"] for s in sc} == {"Revenue", "Total cost · €M"}  # Material / Labour are not single quantities

    def prove(h):
        return derive_across(headline_quantities(h)[0], sc)

    p = prove("A €40M contribution")
    assert p["status"] == "derived_proof" and p["operation"] == "difference across exhibits" and len(p["lineage"]) == 2
    assert prove("Costs are 67% of revenue")["operation"] == "share across exhibits"
    assert prove("A €7M gap")["status"] == "unknown"
    assert prove("A $40M contribution")["status"] == "unknown"  # never across currencies
    one = {"visual": slide["visual"]}
    assert derive_across(headline_quantities("€40M")[0], slide_scalars(one))["status"] == "unknown"  # one exhibit: not this rule
    many = {"exhibits": [{"type": "kpi", "data": {"items": [{"value": f"€{v}M", "label": f"k{v}"}]}} for v in range(11, 23)]}
    assert "more than" in derive_across(headline_quantities("€25M")[0], slide_scalars(many))["reason"]
