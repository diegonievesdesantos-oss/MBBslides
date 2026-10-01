"""Human-reference evaluation: blind A/B tool and statistics, kept apart from the automatic score."""
import json
import threading
import urllib.error
import urllib.request

import pytest
from PIL import Image

from cpe import human


def _fake_run(root, deck, slides, color):
    d = root / deck
    (d / "renders").mkdir(parents=True)
    res = {"slides": [{"id": sid, "kind": "content", "_plan": {"layout": {"id": "exhibit_full"}}} for sid in slides]}
    (d / "resolved.json").write_text(json.dumps(res))
    comp = {"composition": {"slides": [{"slide_id": sid, "score": 60.0 + 10 * (color == "blue"), "archetype": "chart"} for sid in slides]}}
    (d / "qa_report.json").write_text(json.dumps(comp))
    for i, sid in enumerate(slides, 1):
        Image.new("RGB", (40, 22), color if sid != "same" else "white").save(d / "renders" / f"slide-{i:02d}.png")


@pytest.fixture
def round_dir(tmp_path):
    base, chal = tmp_path / "base", tmp_path / "chal"
    for root, col in ((base, "red"), (chal, "blue")):
        _fake_run(root, "deck1", ["s1", "s2", "s3", "same"], col)
        _fake_run(root, "deck2", ["t1", "t2"], col)
    out = tmp_path / "round"
    r = human.build_round(out, [("v1->v2", str(base), str(chal))], n=6, repeats=1)
    assert r["pairs"] == 6  # 5 differing slides + 1 repeat; the identical slide is skipped
    return out


def test_round_is_blind(round_dir):
    pairs = json.loads((round_dir / "pairs.json").read_text())
    blob = json.dumps(pairs)
    for leak in ("baseline", "challenger", "v1->v2", "exhibit_full", "score", "deck1", "s1"):
        assert leak not in blob
    key = json.loads((round_dir / "key.json").read_text())
    assert all({"baseline", "challenger", "comparison"} <= set(k) for k in key.values())
    assert "key.json" not in (round_dir / "index.html").read_text()


def test_server_votes_resume_and_never_serves_the_key(round_dir):
    from http.server import ThreadingHTTPServer  # noqa: F401 — serve() uses it

    port = 18765
    t = threading.Thread(target=human.serve, args=(round_dir, port), daemon=True)
    t.start()
    import time

    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/pairs.json")
            break
        except OSError:
            time.sleep(0.1)
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/key.json")
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/img/../key.json")
    pairs = json.loads((round_dir / "pairs.json").read_text())["pairs"]
    p = pairs[0]
    body = json.dumps({"evaluator": "r-abc", "pair": p["id"], "left": p["images"][1], "right": p["images"][0], "choice": "left", "ms": 900}).encode()
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/vote", data=body, headers={"Content-Type": "application/json"}))
    state = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/state?evaluator=r-abc").read())
    assert state["done"] == [p["id"]]  # an interrupted session resumes where it stopped
    bad = json.dumps({"evaluator": "r-abc", "pair": p["id"], "left": "x.png", "right": "y.png", "choice": "left"}).encode()
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/vote", data=bad))


def test_report_statistics(round_dir):
    key = json.loads((round_dir / "key.json").read_text())
    pairs = {p["id"]: p for p in json.loads((round_dir / "pairs.json").read_text())["pairs"]}
    votes = []
    for ev in ("ann", "bob"):
        for pid, k in key.items():
            chal_left = pairs[pid]["images"][0] == k["challenger"]
            choice = "left" if chal_left else "right"  # both always prefer the challenger
            votes.append({"evaluator": ev, "pair": pid, "left": pairs[pid]["images"][0], "right": pairs[pid]["images"][1], "choice": choice})
    f = round_dir / "import.jsonl"
    f.write_text("\n".join(json.dumps(v) for v in votes))
    assert human.import_votes(round_dir, f) == len(votes)
    r = human.report(round_dir)
    assert r["evaluators"] == 2 and r["comparisons"] == 10  # 5 pairs × 2 evaluators, repeats reported separately
    assert r["challenger_wins"] == 10 and r["challenger_preference"] == 1.0
    lo, hi = r["challenger_preference_ci95"]
    assert 0.65 < lo < 0.75 and hi == 1.0  # Wilson interval stays honest at small n
    assert r["inter_rater"]["percent_agreement"] == 1.0
    assert r["self_consistency"] == {"repeated_pairs": 2, "consistent": 2}
    assert r["score_agreement"]["rate"] == 1.0  # challenger also has the higher automatic score here
    assert "Wilson" in human.to_markdown(r)


def test_wilson_and_fleiss_reference_values():
    assert human.wilson(0, 0) == (None, None)
    lo, hi = human.wilson(8, 10)
    assert (lo, hi) == (0.49, 0.943)
    # Fleiss (1971)-style check: perfect agreement → 1, systematic disagreement → negative
    assert human.fleiss_kappa([["challenger", "challenger"], ["baseline", "baseline"], ["tie", "tie"]]) == 1.0
    assert human.fleiss_kappa([["challenger", "baseline"], ["baseline", "challenger"]]) < 0


def test_human_results_never_enter_the_automatic_score(tmp_path, monkeypatch):
    from cpe import evals

    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"regression": {"suite_composition": 87.3}}))
    monkeypatch.setattr(evals, "LATEST", latest)
    evals.record_result("human_reference", {"round": "r1", "challenger_preference": 0.2}, path=latest)
    data = json.loads(latest.read_text())
    assert data["regression"]["suite_composition"] == 87.3  # untouched
    assert data["human_reference"]["challenger_preference"] == 0.2
    import inspect

    from cpe.qa import archetypes, composition

    src = inspect.getsource(composition) + inspect.getsource(archetypes)
    assert "import human" not in src and "from .. import human" not in src and "cpe.human" not in src
    assert "human_reference" not in src and "latest.json" not in src  # votes are never read by the scorer
