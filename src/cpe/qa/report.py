"""QA aggregation, scoring, gate verdict, markdown report and review packet.

`passed` is computed here from the issue list — never asserted by the agent.
Exemptions must be explicit in the spec, scoped to a slide AND a code, and
carry a reason:  "qa_exemptions": [{"slide": "s07", "code": "HEADLINE_UNQUANTIFIED", "reason": "..."}]
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

PENALTY = {"error": 15, "warning": 4, "info": 1}
HEAVY = {"TEXT_OVERFLOW": 25, "RENDER_TEXT_SPILL": 25, "OFF_SLIDE": 25, "RENDER_TEXT_COLLISION": 20, "TEXT_COLLISION": 20, "PLACEHOLDER_TEXT": 25, "HEADLINE_TOPIC": 20}

LAYER_OF = {
    "geometry": {"OFF_SLIDE", "OUTSIDE_SAFE_AREA", "OUTSIDE_ZONE", "TEXT_OVERFLOW", "TEXT_COLLISION", "CONNECTOR_THROUGH_TEXT", "FONT_TOO_SMALL", "FONT_FAMILY", "COLOR_OFF_PALETTE", "LOW_CONTRAST", "PLACEHOLDER_TEXT", "HEADLINE_LINES", "HEADLINE_WIDOW", "MISALIGNED", "SHAPE_COUNT", "TINY_ELEMENT", "EMPTY_ZONE", "FIT_SHRUNK", "LABEL_COLLISION", "WATERFALL_NEGATIVE", "PIE_TOO_MANY"},
}

# v1.5 QA semantics: errors about the WRITING (storyline, headline wording, intent, spec) vs errors
# about the rendered slide. HEADLINE_LINES / HEADLINE_WIDOW are how the headline renders: visual.
AUTHORING_PREFIXES = ("STORY_", "HEADLINE_", "INTENT_", "SPEC_")
VISUAL_HEADLINE_CODES = {"HEADLINE_LINES", "HEADLINE_WIDOW"}


def is_authoring(code: str) -> bool:
    code = str(code or "")
    return code.startswith(AUTHORING_PREFIXES) and code not in VISUAL_HEADLINE_CODES


def qa_semantics(issues: list[dict]) -> dict:
    """visual_qa_passed: no error on the rendered slides. authoring_qa_passed: no error in the
    writing. `passed` (the deck gate) still requires both."""
    errs = [i for i in issues or [] if i.get("level") == "error"]
    a = sum(1 for i in errs if is_authoring(i.get("code")))
    return {"visual_qa_passed": len(errs) - a == 0, "authoring_qa_passed": a == 0, "errors_visual": len(errs) - a, "errors_authoring": a}


# The questions of the semantic-visual review (answered by the agent looking at the PNGs)
REVIEW_QUESTIONS = [
    ("one_idea", "Does the slide communicate ONE clear idea?"),
    ("five_seconds", "Is the insight understood in ~5 seconds (headline + the one highlighted element)?"),
    ("hierarchy", "Is there an evident visual hierarchy (headline → key number/element → support)?"),
    ("no_decoration", "Is every element functional (no decorative boxes, icons, colours without meaning)?"),
    ("chart_supports_headline", "Does the exhibit actually prove the headline (right data, right comparison, the number is visible)?"),
    ("focus", "Is there only one thing competing for attention (one highlight, one accent)?"),
    ("layout_fit", "Is the layout the right one for this message (would another family communicate better)?"),
    ("professional", "Would a partner / MD send this slide to a client or board without edits?"),
]
LENSES = [
    ("CEO / board", "Is it a decision or just a description? What is the ask?"),
    ("CFO", "Do numbers, units, periods and deltas reconcile across slides?"),
    ("Engagement partner", "Is the answer sharp and defensible? What is the weakest claim?"),
    ("Visual editor", "What does the eye see first, second, third? Anything to remove?"),
]


def apply_exemptions(issues: list[dict], spec: dict) -> tuple[list[dict], list[dict]]:
    ex = spec.get("qa_exemptions") or []
    keep, exempted = [], []
    for i in issues:
        hit = next((e for e in ex if e.get("reason") and e.get("code") == i["code"] and (e.get("slide") in (i.get("slide"), "*"))), None)
        (exempted if hit else keep).append({**i, "exemption": hit.get("reason")} if hit else i)
    return keep, exempted


def score(issues: list[dict], slide_ids: list[str]) -> tuple[dict, float]:
    per = {s: 100 for s in slide_ids}
    for i in issues:
        s = i.get("slide")
        if s in per:
            per[s] -= HEAVY.get(i["code"], PENALTY.get(i["level"], 0)) if i["level"] == "error" else PENALTY.get(i["level"], 0)
    per = {k: max(0, v) for k, v in per.items()}
    deck = round(sum(per.values()) / max(1, len(per)), 1)
    return per, deck


def summarize(issues: list[dict], slide_ids: list[str], exempted: list[dict] | None = None, metrics: dict | None = None, history: list | None = None, extra: dict | None = None) -> dict:
    per, deck = score(issues, slide_ids)
    levels = Counter(i["level"] for i in issues)
    errors = [i for i in issues if i["level"] == "error"]
    return {
        "passed": not errors,
        "deck_score": deck,
        "counts": {"error": levels.get("error", 0), "warning": levels.get("warning", 0), "info": levels.get("info", 0)},
        "blocking": errors,
        "slide_scores": per,
        "issues": issues,
        "exempted": exempted or [],
        "render_metrics": metrics or {},
        "iterations": history or [],
        **(extra or {}),
    }


def write(report: dict, out_dir: str | Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    jp = out_dir / "qa_report.json"
    jp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    mp = out_dir / "qa_report.md"
    mp.write_text(to_markdown(report), encoding="utf-8")
    return jp, mp


def to_markdown(r: dict) -> str:
    L = ["# QA report", ""]
    verdict = "✅ PASSED" if r["passed"] else "❌ FAILED"
    L.append(f"**Verdict:** {verdict} · **Deck score:** {r['deck_score']}/100 · errors {r['counts']['error']} · warnings {r['counts']['warning']} · info {r['counts']['info']}")
    L.append("")
    if r.get("iterations"):
        L.append("## Iterations (generate → render → inspect → patch)")
        L.append("")
        L.append("| # | errors | warnings | score | patches applied |")
        L.append("|---|---|---|---|---|")
        for h in r["iterations"]:
            L.append(f"| {h['iteration']} | {h['errors']} | {h['warnings']} | {h['score']} | {'; '.join(h.get('patches', [])) or '—'} |")
        L.append("")
    if r.get("pending_actions"):
        L.append("## Actions for the author (cannot be auto-fixed without changing the message)")
        L.append("")
        for a in r["pending_actions"]:
            L.append(f"- **{a['slide']}** `{a['code']}` — {a['action']}")
        L.append("")
    if r.get("editorial_advice"):
        L.append("## Editorial advice (composition fitness — a preference, not a QA defect; does not affect the verdict or score)")
        L.append("")
        for a in r["editorial_advice"]:
            L.append(f"- **{a['slide']}** `{a['code']}` — {a['why']}")
        L.append("")
    L.append("## Slide scores")
    L.append("")
    L.append("| slide | score | errors | warnings |")
    L.append("|---|---|---|---|")
    for sid, sc in r["slide_scores"].items():
        e = sum(1 for i in r["issues"] if i.get("slide") == sid and i["level"] == "error")
        w = sum(1 for i in r["issues"] if i.get("slide") == sid and i["level"] == "warning")
        L.append(f"| {sid} | {sc} | {e} | {w} |")
    L.append("")
    L.append("## Issues")
    L.append("")
    by = {}
    for i in r["issues"]:
        by.setdefault(i.get("slide", "deck"), []).append(i)
    for sid, lst in by.items():
        L.append(f"### {sid}")
        for i in sorted(lst, key=lambda i: ["error", "warning", "info"].index(i["level"])):
            L.append(f"- **{i['level']}** `{i['code']}` — {i['message']}")
        L.append("")
    if r.get("exempted"):
        L.append("## Exempted (with reason)")
        for i in r["exempted"]:
            L.append(f"- {i.get('slide')} `{i['code']}` — {i['exemption']}")
    return "\n".join(L) + "\n"


def review_packet(resolved: dict, report: dict, pngs: list[str], out_dir: str | Path) -> Path:
    """Markdown packet + JSON template for the semantic-visual review by the agent."""
    out_dir = Path(out_dir)
    L = ["# Visual review packet", "", "Open each PNG, answer the questions (0 = no, 1 = partly, 2 = yes), and write",
         "`review.json` + `patches.json` (see SKILL.md §8). A slide passes the review with ≥13/16 and no 0.", ""]
    L.append("**Lenses (whole deck):** " + " · ".join(f"*{n}*: {q}" for n, q in LENSES))
    L.append("")
    template = {}
    for i, s in enumerate(resolved.get("slides", [])):
        sid = s.get("id")
        png = pngs[i] if i < len(pngs) else ""
        L.append(f"## {i + 1}. {sid} — {s.get('kind', 'content')}")
        L.append(f"![{sid}]({Path(png).relative_to(out_dir).as_posix() if png else ''})")
        L.append("")
        if s.get("headline"):
            L.append(f"- **Headline:** {s['headline']}")
        if s.get("purpose"):
            L.append(f"- **Purpose:** {s['purpose']}")
        plan = s.get("_plan") or {}
        if plan.get("layout"):
            L.append(f"- **Layout:** `{plan['layout'].get('id')}` — {plan['layout'].get('why', '')}")
        for v in plan.get("visuals") or []:
            L.append(f"- **Visual:** `{v.get('chosen')}` — {v.get('why', '')}" + (f"; not: {', '.join(v.get('not', []))}" if v.get("not") else ""))
        flags = [f"`{x['code']}`" for x in report["issues"] if x.get("slide") == sid and x["level"] != "info"]
        if flags:
            L.append(f"- **Automated flags:** {', '.join(flags)}")
        L.append("")
        for key, q in REVIEW_QUESTIONS:
            L.append(f"  - [ ] {q}")
        L.append("")
        template[sid] = {"scores": {k: None for k, _ in REVIEW_QUESTIONS}, "issues": [], "patches": []}
    p = out_dir / "review.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    (out_dir / "review_template.json").write_text(json.dumps(template, indent=2), encoding="utf-8")
    return p


def evaluate_review(review: dict) -> dict:
    """Score an agent-filled review.json: per-slide total /16, pass = ≥13 and no zero."""
    out = {}
    for sid, r in review.items():
        sc = r.get("scores") or {}
        vals = [v for v in sc.values() if isinstance(v, (int, float))]
        total = sum(vals)
        out[sid] = {"total": total, "max": 2 * len(REVIEW_QUESTIONS), "passed": len(vals) == len(REVIEW_QUESTIONS) and total >= 13 and 0 not in vals}
    return {"slides": out, "passed": all(v["passed"] for v in out.values()) if out else False}
