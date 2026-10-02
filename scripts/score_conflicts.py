"""Score `fact_conflicts.json` against an answer key (conflict groups and decoys).

    python scripts/score_conflicts.py WORK GOLD.json [-v]

A gold version is matched to the facts of its file holding its value (any scale). A conflict group is
FOUND when one detected conflict links two of its versions. A detected conflict is CORRECT when both
its facts belong to versions of one group, a DECOY hit when it links items of one decoy, otherwise
UNLABELLED (counted against precision: the key lists what a careful analyst would flag).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cpe.reasoning.deck_update import _parse_core  # noqa: E402


def _num(s: str) -> float | None:
    s = s.strip().lstrip("+")
    neg = s.startswith(("-", "−"))
    v = _parse_core(s.lstrip("-−"), "," if "," in s and "." not in s else None)
    return -v if v is not None and neg else v


def _near(x: float, w: float) -> bool:
    return any(abs(x * k - w) <= 0.005 * max(w, 1e-9) for k in (1, 1e3, 1e-3, 1e6, 1e-6))


def _match(facts: list[dict], item: dict) -> set[str]:
    want = _num(item["value"])
    if want is None:
        return set()
    out = set()
    for f in facts:
        if Path(str(f["source"].get("file") or "")).name != Path(item["file"]).name:
            continue
        for v in f.get("values") or []:
            x = abs(float(v["value"]))
            if any(abs(x * k - abs(want)) <= 0.005 * max(abs(want), 1e-9) for k in (1, 1e3, 1e-3, 1e6, 1e-6)):
                out.add(f["id"])
    return out


def score(work: Path, gold: dict, verbose: bool = False) -> dict:
    facts = json.loads((work / "facts.json").read_text(encoding="utf-8"))["facts"]
    found = json.loads((work / "fact_conflicts.json").read_text(encoding="utf-8")).get("conflicts") or []
    groups = {g["id"]: [_match(facts, v) for v in g["versions"]] for g in gold.get("conflicts") or []}
    decoys = {d["id"]: [_match(facts, v) for v in d["items"]] for d in gold.get("decoys") or []}
    missing = {gid: [gold_v["value"] for gold_v, m in zip(next(g for g in gold["conflicts"] if g["id"] == gid)["versions"], ms) if not m]
               for gid, ms in groups.items()}
    hit, correct, decoy_hits, unlabelled = set(), 0, 0, []
    import itertools

    for c in found:  # a pair, or (v2.0) a group of versions: correct when two of its facts are two versions of one group
        g, dec, gs = None, False, set()
        for xa, xb in itertools.combinations(c["facts"], 2):
            a, b = xa["fact"], xb["fact"]
            g = next((gid for gid, ms in groups.items() if any(a in m for m in ms) and any(b in m for m in ms)
                      and next(i for i, m in enumerate(ms) if a in m) != next(i for i, m in enumerate(ms) if b in m)), None)
            if not g:  # the same values restated in a file the key did not list: still that group
                for gr in gold.get("conflicts") or []:
                    vals = [abs(_num(v["value"]) or 0) for v in gr["versions"]]
                    ia = [i for i, w in enumerate(vals) if _near(abs(xa["value"]), w)]
                    ib = [i for i, w in enumerate(vals) if _near(abs(xb["value"]), w)]
                    if ia and ib and set(ia) != set(ib):
                        g = gr["id"]
                        break
            if g:
                gs.add(g)
                g = None
                continue
            dec = dec or any(any(a in m for m in ms) and any(b in m for m in ms) for ms in decoys.values())
        if gs:  # a group of versions may join two planted groups about one quantity (a cost executed / total)
            hit |= gs
            correct += 1
        elif dec:
            decoy_hits += 1
        else:
            unlabelled.append(c)
    n = len(found)
    res = {"groups": len(groups), "found": len(hit), "detected": n, "correct": correct, "decoy_hits": decoy_hits, "unlabelled": len(unlabelled),
           "precision": round(correct / n, 3) if n else None, "recall": round(len(hit) / len(groups), 3) if groups else None,
           "missed": sorted(set(groups) - hit), "versions_not_in_facts": {k: v for k, v in missing.items() if v}}
    if verbose:
        fm = {f["id"]: f for f in facts}
        for c in unlabelled:
            print("  UNLABELLED", c["type"], " || ".join(f"{fm[x['fact']]['source'].get('file')}: {fm[x['fact']]['claim'][:70]}" for x in c["facts"][:4]))
    return res


if __name__ == "__main__":
    r = score(Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")), "-v" in sys.argv)
    print(json.dumps(r, ensure_ascii=False))
