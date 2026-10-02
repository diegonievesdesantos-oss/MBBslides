"""Editorial artifacts (v3.1, spec §30-31, §47, §81): what the compiler found, written for a reader.

    editorial_report.json / .md   Action titles · Parallel wording · Horizontal logic, with every finding
    headline_strip.md             the titles alone, and the five questions they must answer
    editorial_ghost_deck.md       the ghost deck with role, signature, score and parallel status per title
"""
from __future__ import annotations

import json
from pathlib import Path


def to_markdown(rep: dict) -> str:
    s = rep["summary"]
    verdict = "PASSED" if rep["passed"] else "FAILED"
    L = [f"# Editorial QA: {verdict}", "", f"Mode `{rep['mode']}` · language {rep.get('language') or 'undetermined'}", "",
         "## Action titles", "",
         f"- slides checked: {s['slides_checked']} · passed: {s['slides_passed']}",
         f"- hard errors: {s['hard_errors']} · warnings: {s['warnings']}",
         f"- mean diagnostic score: {s['mean_headline_score']}  (diagnostic only: a score never overrides a hard failure)",
         f"- propositions: {s['propositions']['explicit']} explicit, {s['propositions']['inferred']} inferred, {s['propositions']['missing']} missing",
         f"- headlines selected or rewritten by the engine: {s['headlines_selected']}", "",
         "## Parallel wording", "",
         f"- groups checked: {s['groups_checked']} · mandatory groups passed: {s['mandatory_groups_passed']} / {s['mandatory_groups']}", ""]
    for g in rep["groups"]:
        L.append(f"- `{g['id']}` ({g['kind']}, {g['context']}, {'mandatory' if g['mandatory'] else 'advisory'}) → **{g['status']}** · target {g.get('target_signature')}")
    L += ["", "## Horizontal logic", "",
          f"- orphan propositions: {s['orphan_propositions']} · unsupported key-line points: {s['unsupported_keyline_points']}",
          f"- headline strip coherence: {s['strip_coherence']}", ""]
    errs = [f for f in rep["findings"] if f["level"] in ("error", "warning")]
    if errs:
        L += ["## Findings", "", "| level | slide | code | message |", "|---|---|---|---|"]
        for f in sorted(errs, key=lambda f: (f["level"] != "error", str(f.get("slide")))):
            L.append(f"| {f['level']} | {f.get('slide') or 'deck'} | {f['code']} | {f['message'].replace('|', '/')[:220]} |")
        L.append("")
    sel = [f for f in rep["findings"] if f["code"] == "HEADLINE_SELECTED"]
    if sel:
        L += ["## Headlines the engine selected", ""] + [f"- {f['slide']}: {f['message']}" for f in sel] + [""]
    return "\n".join(L) + "\n"


def explain(rep: dict) -> str:
    """`cpe editorial explain`: per slide, proposition → selected headline → candidates → findings."""
    L = [f"# Editorial explain ({rep['mode']})", ""]
    for r in rep["slides"]:
        if r.get("status") == "exempt":
            L.append(f"## {r['slide']} · {r['kind']} · exempt\n")
            continue
        p = r.get("proposition") or {}
        L += [f"## {r['slide']} · {r['kind']} · **{r['status']}** · score {r['score']}", "",
              f"- headline: {r.get('headline')}" + (f"  (was: {r['was']})" if r.get("was") else ""),
              f"- headline type: {r['headline_type']} · signature: {r['signature']}",
              f"- proposition ({'inferred' if p.get('_inferred') else 'explicit' if p else 'missing'}): {p.get('statement', '—')}",
              f"  role {p.get('role')} · claim {p.get('claim_type')} · evidence {p.get('evidence_ids') or p.get('analysis_ids') or '—'} · confidence {p.get('confidence')}",
              "- candidates:"]
        for c in r["candidates"]:
            L.append(f"  - [{'ok' if c['passed'] else 'rejected'}] ({c['origin']}, {c['score']}) {c['text']}" + (f" — {', '.join(c['hard'])}" if c["hard"] else "")
                     + (f" — {c['derivation']}" if c.get("derivation") else ""))
        fs = [f for f in r["findings"] if f["class"] != "info"]
        if fs:
            L.append("- findings:")
            L += [f"  - {f['code']}: {f['message']}" for f in fs]
        gs = [g for g in rep["groups"] if any(m.get("slide") == r["slide"] for m in g["members"])]
        for g in gs:
            L.append(f"- parallel group `{g['id']}` → {g['status']}")
        L.append("")
    return "\n".join(L) + "\n"


def headline_strip_md(spec: dict, rep: dict) -> str:
    st = rep["strip"]
    L = [f"# Headline strip — {(spec.get('meta') or {}).get('title', '')}", "",
         "Read only the titles. Can a senior executive reconstruct the argument?", ""]
    for r in st["rows"]:
        L.append(f"{r['n']:>2}. {r['headline']}" + (f"   _({r['role']})_" if r.get("role") else ""))
    L += ["", "| question | answered by the titles |", "|---|---|"]
    L += [f"| {q['question']} | {'yes' if q['answered'] else '**no**'} |" for q in st["questions"]]
    L += ["", f"Coherence (questions answered): {st['coherence']}", ""]
    return "\n".join(L)


def editorial_ghost(spec: dict, rep: dict) -> str:
    st = spec.get("storyline") or {}
    kl = {k.get("id"): k for k in st.get("key_line") or []}
    by = {r["slide"]: r for r in rep["slides"]}
    grp = {}
    for g in rep["groups"]:
        for m in g["members"]:
            if m["ref"].endswith(".headline"):
                grp[m.get("slide")] = g
    L = [f"# Editorial ghost deck — {(spec.get('meta') or {}).get('title', '')}", "", "## Governing thought", st.get("governing_thought", ""), ""]
    cur = None
    for i, s in enumerate(spec.get("slides") or [], start=1):
        kind = s.get("kind", "content")
        if kind in ("cover", "agenda", "closing"):
            continue
        if kind in ("divider", "appendix_divider"):
            L.append(f"\n## {s.get('title', '')}")
            continue
        sec = s.get("section")
        if sec and sec != cur and sec in kl:
            cur = sec
            L.append(f"\n### {sec} · {str(kl[sec].get('role', '')).upper()} — {kl[sec].get('message', '')}")
        r = by.get(s.get("id")) or {}
        text = s.get("text") if kind == "statement" and s.get("text") else s.get("headline")
        L.append(f"{i:02d}. {text}")
        p = r.get("proposition") or {}
        g = grp.get(s.get("id"))
        meta = [f"role: {p.get('role', '—')}", f"signature: {r.get('signature', '—')}", f"ATE: {r.get('score', '—')} ({r.get('status', '—')})"]
        if g:
            meta.append(f"parallel group: {g['id']} → {g['status']}")
        L.append("    " + " · ".join(meta))
    return "\n".join(L) + "\n"


def write(rep: dict, spec: dict, out: str | Path) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "editorial_report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8", newline="\n")
    (out / "editorial_report.md").write_text(to_markdown(rep), encoding="utf-8", newline="\n")
    (out / "headline_strip.md").write_text(headline_strip_md(spec, rep), encoding="utf-8", newline="\n")
    (out / "editorial_ghost_deck.md").write_text(editorial_ghost(spec, rep), encoding="utf-8", newline="\n")
