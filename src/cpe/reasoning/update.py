"""One command to update an existing deck (v2.0).

    cpe update old.pptx sources/ -o work
        ingest the old deck → fact model of the new sources (+ recorded analyses in work/) →
        update plan (current / outdated / untraced / ignored, derived figures) → work/edits.json
    (review work/edits.json: approve, correct "replace", add edits for what the plan left untraced)
    cpe update --apply work -o new.pptx [--mark] [--accept-derived]
        recompute derived figures from what was approved → patch the ORIGINAL pptx → update_report.md

Re-running the first step is safe: a reviewed edits.json is kept (approvals, corrections, hand-made
edits); only proposals for numbers it does not cover yet are added, and derived figures recomputed.
The old deck is never modified; the output is a new file.
"""
from __future__ import annotations

import json
from pathlib import Path


def prepare(old_pptx: str | Path, sources: str | Path, work: str | Path) -> dict:
    from . import deck_patch, deck_update, facts

    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    inv = deck_update.write_ingest(old_pptx, work)
    fm = facts.write_fact_model(sources, work)
    plan = deck_update.write_plan(work)
    fresh = deck_patch.proposed_edits(plan)
    path = work / "edits.json"
    kept = 0
    if path.exists():
        e = json.loads(path.read_text(encoding="utf-8"))
        have = {x.get("id") for x in e.get("edits") or [] if x.get("id")}
        for x in fresh["edits"]:
            if x["id"] not in have:
                e["edits"].append(x)
        kept = sum(1 for x in e["edits"] if x.get("approved"))
        e["review"] = fresh["review"]
    else:
        e = fresh
    e["derived"] = deck_patch.derive_edits(plan, e)
    rev = _messages(work, plan, e)
    path.write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (work / "edits.md").write_text(deck_patch.edits_markdown(e), encoding="utf-8", newline="\n")
    meta = {"messages": {v: sum(1 for r in rev if r["verdict"] == v) for v in ("holds", "figures updated", "no longer holds", "check")},
            "old_pptx": str(Path(old_pptx).resolve()), "sources": str(Path(sources).resolve()), "slides": len(inv["slides"]),
            "facts": fm["stats"]["facts"], "plan": plan["totals"], "edits": len(e["edits"]), "approved_kept": kept}
    (work / "update.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return meta


def _messages(work: Path, plan: dict, e: dict) -> list[dict]:
    """v2.0 item 5: each headline against the new values; set_headline proposals where it no longer holds."""
    from . import messages

    rev = messages.review(plan, e)
    messages.headline_edits(rev, e)
    (work / "messages.json").write_text(json.dumps(rev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (work / "messages.md").write_text(messages.markdown(rev), encoding="utf-8", newline="\n")
    return rev


def apply(work: str | Path, out: str | Path, mark: bool = False, accept_derived: bool = False) -> dict:
    from . import deck_patch

    work = Path(work)
    meta = json.loads((work / "update.json").read_text(encoding="utf-8"))
    plan = json.loads((work / "update_plan.json").read_text(encoding="utf-8"))
    e = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    e["derived"] = deck_patch.derive_edits(plan, e)
    if accept_derived:  # arithmetic on approved values only; provisional ones stay for review
        for x in e["edits"]:
            if x.get("derived") and not x["derived"].get("pending_parts"):
                x["approved"] = True
    rev = _messages(work, plan, e)  # with the derived figures now approved, the claims are re-read
    (work / "edits.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    r = deck_patch.write_patch(meta["old_pptx"], work / "edits.json", out, mark=mark)
    changed = {x["id"] for x in r["applied"] if x.get("id")}
    rewritten = {x["slide"] for x in r["applied"] if x.get("op") == "set_headline"}
    rewrite = [{"slide": m["slide"], "headline": m["headline"], "verdict": m["verdict"], "rewritten": m["slide"] in rewritten,
                "why": [c for c in m["claims"] if c["status"] != "holds"] + [{"changed": c} for c in m["changed"]] + [{"unresolved": u} for u in m["unresolved"]]}
               for m in rev if m["verdict"] != "holds"]
    applied_ids = changed | {x.get("id") for x in r["failed"] if x.get("id")}
    left = [{"slide": s["slide"], "where": q["where"], "number": q["raw"], "status": q["status"]} for s in plan["slides"] for q in s["numbers"]
            if q["status"] in ("outdated", "untraced") and q.get("id") not in applied_ids and str(s["slide"]) not in {str(d) for d in r["slides_deleted"]}]
    rep = {**r, "rewrite_headlines": rewrite, "left_unchanged": left, "derived": e["derived"]}
    Path(out).parent.joinpath("update_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    Path(out).parent.joinpath("update_report.md").write_text(report_markdown(rep), encoding="utf-8", newline="\n")
    return rep


def rebuild(work: str | Path, slides: list[int] | None = None, render: bool = True) -> dict:
    """v2.0 item 5: build the slides whose message no longer holds in the old deck's own style and
    propose replacing them (unapproved `replace_slide` edits). The spec in work/rewrite/deck.json is
    kept once written: edit it (headline, exhibit) and run --rebuild again."""
    from ..brand.ingest import ingest as brand_ingest
    from ..pipeline import run
    from ..spec import load_spec
    from . import deck_patch
    from .rebuild import rewrite_spec

    work = Path(work)
    meta = json.loads((work / "update.json").read_text(encoding="utf-8"))
    if not (work / "brand" / "theme.json").exists():
        brand_ingest(meta["old_pptx"], work / "brand")
    plan = json.loads((work / "update_plan.json").read_text(encoding="utf-8"))
    e0 = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    e0["derived"] = deck_patch.derive_edits(plan, e0)
    _messages(work, plan, e0)  # the claims re-read with what is approved now
    (work / "edits.json").write_text(json.dumps(e0, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    rw = work / "rewrite"
    rw.mkdir(exist_ok=True)
    spec_path = rw / "deck.json"
    if not spec_path.exists() or slides:
        spec = rewrite_spec(work, slides)
        if not spec["slides"]:
            return {"slides": [], "why": "no slide whose message no longer holds (pass --slides to choose)"}
        spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    r = run(load_spec(str(spec_path)), str(rw / "out"), do_render=render, name="rebuilt")
    built = (rw / "out" / "rebuilt.pptx").resolve()
    e = json.loads((work / "edits.json").read_text(encoding="utf-8"))
    e["edits"] = [x for x in e["edits"] if x.get("op") != "replace_slide" or x.get("approved")]
    for k, s in enumerate(spec["slides"]):
        n = s.get("_old_slide") or int(s["id"][1:])
        if any(x.get("op") == "replace_slide" and x["slide"] == n for x in e["edits"]):
            continue
        e["edits"].append({"op": "replace_slide", "slide": n, "from": str(built), "index": k, "headline": s.get("headline"),
                           "approved": False, "qa": {"passed": r.get("passed"), "score": r.get("deck_score")}})
    (work / "edits.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {"slides": [s.get("_old_slide") for s in spec["slides"]], "spec": str(spec_path), "built": str(built),
            "qa": {"passed": r.get("passed"), "score": r.get("deck_score"), "errors": (r.get("counts") or {}).get("error")}}


def report_markdown(r: dict) -> str:
    L = [f"# Update report — {r['source']} → {r['output']}", "",
         f"- **Applied:** {len(r['applied'])} edits ({sum(1 for a in r['applied'] if a.get('derived'))} derived); "
         f"**failed:** {len(r['failed'])}; **not approved:** {r['skipped_unapproved']}; **slides deleted:** {r['slides_deleted'] or 'none'}; "
         f"**slides rebuilt:** {r.get('slides_rebuilt') or 'none'}.",
         f"- **Left unchanged for review:** {len(r['left_unchanged'])} old numbers the plan found outdated or could not trace.", ""]
    if r["rewrite_headlines"]:
        L += ["## Slides whose message changed (messages.md has the detail)", ""]
        L += [f"- slide {w['slide']} — **{w['verdict']}**{' (headline rewritten)' if w['rewritten'] else ''}: {w['headline']}"
              for w in r["rewrite_headlines"]] + [""]
    if r["failed"]:
        L += ["## Not applied", ""] + [f"- slide {f.get('slide')}: {f['why']}" for f in r["failed"]] + [""]
    L += ["## Left unchanged (outdated or untraced, no approved edit)", ""]
    L += [f"- slide {x['slide']} {x['where']}: {x['number']} ({x['status']})" for x in r["left_unchanged"]]
    return "\n".join(L) + "\n"
