"""Evidence graph: SOURCE → FACT → DERIVED FACT → INSIGHT → KEY LINE → SLIDE → HEADLINE.

`trace(work, text)` answers "why is this sentence in the deck?": it finds the headline, governing
thought, key-line point or insight closest to `text` and returns its lineage down to source
locations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .checks import _jaccard, _load


def build_graph(work_dir: str | Path) -> dict:
    work = Path(work_dir)
    facts = {f["id"]: f for f in (_load(work, "facts.json") or {}).get("facts", [])}
    from .checks import check_computed

    facts.update(check_computed(_load(work, "computed_facts.json"), facts)[1])
    insights = {i["id"]: i for i in (_load(work, "insights.json") or {}).get("insights", [])}
    hyps = {h["id"]: h for h in (_load(work, "hypotheses.json") or {}).get("hypotheses", [])}
    sl = _load(work, "storyline.json") or {}
    dp = _load(work, "deck_plan.json") or {}
    deck = _load(work, "deck.json") or {}
    nodes, edges = {}, []

    def node(i, kind, label, **kw):
        nodes[i] = {"id": i, "kind": kind, "label": label, **kw}

    for f in facts.values():
        src = f["source"]
        sid = "S:" + src["file"]
        node(sid, "source", src["file"])
        node(f["id"], "derived_fact" if f.get("derived_from") else "fact", f["claim"], source=src)
        edges.append((sid, f["id"]))
        for d in f.get("derived_from") or []:
            edges.append((d, f["id"]))
    for h in hyps.values():
        node(h["id"], "hypothesis", h["statement"], status=h.get("status"))
        edges += [(f, h["id"]) for f in h.get("supporting_facts") or []]
    for i in insights.values():
        node(i["id"], "insight", i["statement"])
        edges += [(f, i["id"]) for f in i.get("facts") or []] + [(h, i["id"]) for h in i.get("hypotheses") or []]
    if sl.get("governing_thought"):
        node("GT", "governing_thought", sl["governing_thought"])
    for k in sl.get("key_line") or []:
        node(k["id"], "key_line", k.get("message", ""))
        edges += [(i, k["id"]) for i in k.get("insights") or []] + [(k["id"], "GT")]
    for s in dp.get("slides") or []:
        nid = "SL:" + s["id"]
        node(nid, "slide", s.get("headline", ""), priority=s.get("priority"), reason=s.get("reason_to_exist"))
        edges += [(f, nid) for f in s.get("facts") or []] + [(i, nid) for i in s.get("insights") or []]
        if s.get("key_line"):
            edges.append((s["key_line"], nid))
    for s in deck.get("slides") or []:
        nid = "SL:" + str(s.get("id"))
        if nid not in nodes:
            node(nid, "slide", s.get("headline", ""))
        for e in s.get("evidence") or []:
            if isinstance(e, dict) and e.get("fact"):
                edges.append((e["fact"], nid))
    edges = sorted(set(edges))
    return {"nodes": nodes, "edges": [list(e) for e in edges]}


def _parents(g: dict, nid: str) -> list[str]:
    return [a for a, b in g["edges"] if b == nid and a in g["nodes"]]


def lineage(g: dict, nid: str, depth: int = 0, seen=None) -> dict:
    seen = seen if seen is not None else set()
    n = g["nodes"][nid]
    out = {"id": nid, "kind": n["kind"], "label": n["label"][:160]}
    if n.get("source"):
        out["source"] = n["source"]
    if nid in seen or depth > 8:
        return out
    seen.add(nid)
    ps = [lineage(g, p, depth + 1, seen) for p in _parents(g, nid) if g["nodes"][p]["kind"] != "governing_thought"]
    if ps:
        out["because"] = ps
    return out


def trace(work_dir: str | Path, text: str) -> dict:
    g = build_graph(work_dir)
    cands = [n for n in g["nodes"].values() if n["kind"] in ("slide", "governing_thought", "key_line", "insight")]
    if not cands:
        return {"match": None}
    best = max(cands, key=lambda n: (_jaccard(text, n["label"]), n["kind"] == "slide"))
    score = _jaccard(text, best["label"])
    if score < 0.2:
        return {"match": None, "best_score": round(score, 2)}
    if best["kind"] == "governing_thought":  # its support is the key line
        lin = {"id": "GT", "kind": "governing_thought", "label": best["label"],
               "because": [lineage(g, k) for k in g["nodes"] if g["nodes"][k]["kind"] == "key_line"]}
    else:
        lin = lineage(g, best["id"])
    return {"match": best["id"], "score": round(score, 2), "lineage": lin}


def trace_markdown(t: dict) -> str:
    if not t.get("match"):
        return "No sentence of the deck matches.\n"
    L = []

    def walk(n, d):
        src = n.get("source")
        loc = f"  ← {src['file']}" + (f"{(' [' + str(src['sheet']) + ']') if src.get('sheet') else ''} {src.get('range')}" if src.get("range") else f" {src.get('loc', '')}") if src else ""
        label = re.sub(r"\s+", " ", n["label"])
        L.append("  " * d + f"- **{n['kind']}** {n['id']}: {label}{loc}")
        for c in n.get("because") or []:
            walk(c, d + 1)

    walk(t["lineage"], 0)
    return "\n".join(L) + "\n"


def save_graph(work_dir: str | Path) -> Path:
    g = build_graph(work_dir)
    p = Path(work_dir) / "evidence_graph.json"
    p.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
