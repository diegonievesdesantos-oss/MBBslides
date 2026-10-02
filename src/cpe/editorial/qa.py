"""Horizontal logic (v3.1, spec §29-34, §63-65): does the deck read as an argument from its titles alone?

    GOVERNING_THOUGHT_TOPIC   the governing thought names a topic instead of answering        hard
    KEYLINE_TOPIC             a key-line point is a label ("Margin decline")                    hard
    EXEC_SUMMARY_AGENDA       an executive-summary statement is an agenda item, not a finding   hard
    EXEC_SUMMARY_LABEL        a statement leads with a label and puts the finding underneath    soft
    ORPHAN_PROPOSITION        a content slide proves no key-line point (no `section`/`supports`) hard
    KEYLINE_UNSUPPORTED       a key-line point no slide proves                                  hard
    HEADLINE_REPEATED_OPENING three consecutive titles open with the same word                  soft
    PAGE_TURN_BACKTRACK       the story jumps back two stages (recommendation → context)        info
    STRIP_NO_ASK / STRIP_NO_FACTS  the headline strip lacks what to do / what happened          soft

The headline-strip test (spec §31) asks five questions of the titles alone — what happened, why,
so what, what next, what decision — and records which ones the strip answers.
"""
from __future__ import annotations

import re

from .signatures import analyze, has_finite_verb

STAGE = {"context": 0, "observation": 1, "status": 1, "comparison": 2, "diagnosis": 2, "driver": 2, "insight": 3,
         "implication": 3, "risk": 3, "recommendation": 5, "decision": 6, "implementation": 6, "impact": 6}
QUESTIONS = (
    ("what_happened", "What happened?", {"context", "observation", "status", "comparison", "diagnosis"}),
    ("why", "Why?", {"diagnosis", "driver"}),
    ("so_what", "So what?", {"insight", "implication", "risk", "impact"}),
    ("what_next", "What should happen next?", {"recommendation", "implementation", "decision"}),
    ("decision", "What decision is required?", {"decision", "recommendation"}),
)


def _is_conclusion(text: str, lang: str | None) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    fam = analyze(t, lang)["family"]
    return fam == "action" or (fam == "declarative" and has_finite_verb(t, lang))  # a recommendation is an answer too


def horizontal(spec: dict, lang: str | None, props: dict[str, dict]) -> tuple[list[dict], dict]:
    """Deck-level findings (code, class, message, slide) and the headline strip."""
    out: list[dict] = []
    st = spec.get("storyline") or {}
    meta = spec.get("meta") or {}
    partial = bool(meta.get("partial") or st.get("collection"))
    gt = st.get("governing_thought") or ""
    if st.get("collection"):
        gt, st = "", {**st, "key_line": []}  # a declared collection (archetype battery) is not a storyline
    if gt and not _is_conclusion(gt, lang):
        out.append(_f("GOVERNING_THOUGHT_TOPIC", "hard", f"The governing thought '{gt[:70]}' names a topic: it must be the one-sentence answer"))
    kl = st.get("key_line") or []
    for k in kl:
        if k.get("message") and not _is_conclusion(k["message"], lang) and "TODO" not in k["message"]:
            out.append(_f("KEYLINE_TOPIC", "hard", f"Key-line point {k.get('id')} '{k['message'][:60]}' is a label, not an argument (spec §33)"))
    slides = spec.get("slides") or []
    for s in slides:
        if s.get("kind") != "exec_summary":
            continue
        from ..spec import slide_exhibits

        items = [it for ex in slide_exhibits(s) for it in ((ex.get("data") or {}).get("items") or ex.get("items") or [])] or list(s.get("statements") or [])
        for i, it in enumerate(items):
            title = str(it.get("title") or it.get("label") or "") if isinstance(it, dict) else str(it)
            body = str(it.get("text") or "") if isinstance(it, dict) else ""
            if title and _is_conclusion(title, lang):
                continue
            first = re.split(r"(?<=[.;:])\s", body, maxsplit=1)[0] if body else ""
            if first and _is_conclusion(first, lang) and title:
                out.append(_f("EXEC_SUMMARY_LABEL", "soft", f"Statement {i + 1} leads with the label '{title[:40]}'; lead with the finding (answer first)", s.get("id")))
            elif not (first and _is_conclusion(first, lang)):
                out.append(_f("EXEC_SUMMARY_AGENDA", "hard", f"Statement {i + 1} '{(title or body)[:50]}' is an agenda item, not a conclusion (spec §34)", s.get("id")))
    content = [s for s in slides if s.get("kind", "content") == "content"]
    if not partial:
        keys = {k.get("id") for k in kl}
        in_appendix = False
        used = set()
        for s in slides:
            if s.get("kind") == "appendix_divider":
                in_appendix = True
            if s.get("kind", "content") != "content":
                continue
            sec = s.get("section")
            if sec in keys:
                used.add(sec)
            elif not (in_appendix or s.get("appendix") or s.get("supports")):
                out.append(_f("ORPHAN_PROPOSITION", "hard", "The slide proves no key-line point: give it a `section` (or `supports`: the slide it substantiates)", s.get("id")))
        for k in kl:
            if k.get("id") not in used and content:
                out.append(_f("KEYLINE_UNSUPPORTED", "hard", f"Key-line point {k.get('id')} ('{(k.get('message') or '')[:50]}') has no slide that proves it"))
    # repeated openings (spec §15 HEADLINE_REPEATED_OPENING)
    stop = {"the", "a", "an", "el", "la", "los", "las", "un", "una"}
    firsts = []
    for s in content:
        toks = [t for t in re.findall(r"[a-záéíóúñü0-9]+", (s.get("headline") or "").lower()) if t not in stop]
        firsts.append((s.get("id"), toks[0] if toks else ""))
    for i in range(2, len(firsts)):
        if firsts[i][1] and firsts[i][1] == firsts[i - 1][1] == firsts[i - 2][1]:
            out.append(_f("HEADLINE_REPEATED_OPENING", "soft", f"Three consecutive titles open with '{firsts[i][1]}'", firsts[i][0]))
    # page-turn (spec §63): advisory
    prev = None
    for s in content:
        r = (props.get(s.get("id")) or {}).get("role")
        if r in STAGE:
            if prev and STAGE[r] <= STAGE[prev[1]] - 3:
                out.append(_f("PAGE_TURN_BACKTRACK", "info", f"The story goes back from {prev[1]} ({prev[0]}) to {r}: check the transition", s.get("id")))
            prev = (s.get("id"), r)
    strip = headline_strip(spec, props)
    if not partial and content:
        if not strip["answers"]["what_happened"]:
            out.append(_f("STRIP_NO_FACTS", "soft", "From the titles alone a reader does not learn what happened"))
        if st.get("decision_sought") and not (strip["answers"]["what_next"] or strip["answers"]["decision"]):
            out.append(_f("STRIP_NO_ASK", "soft", f"The deck seeks a decision ('{st['decision_sought'][:50]}') but no title says what to do"))
    return out, strip


def headline_strip(spec: dict, props: dict[str, dict]) -> dict:
    rows = []
    roles = set()
    for i, s in enumerate(spec.get("slides") or [], start=1):
        kind = s.get("kind", "content")
        if kind in ("cover", "divider", "agenda", "appendix_divider", "closing"):
            continue
        text = s.get("text") if kind == "statement" and s.get("text") else s.get("headline")
        r = (props.get(s.get("id")) or {}).get("role")
        if r:
            roles.add(r)
        rows.append({"n": i, "slide": s.get("id"), "kind": kind, "role": r, "headline": text or ""})
    answers = {q: bool(roles & rs) for q, _, rs in QUESTIONS}
    asked = [q for q, _, _ in QUESTIONS if q != "decision" or (spec.get("storyline") or {}).get("decision_sought")]
    return {"rows": rows, "answers": answers, "coherence": round(sum(answers[q] for q in asked) / len(asked), 2) if asked else None,
            "questions": [{"id": q, "question": t, "answered": answers[q]} for q, t, _ in QUESTIONS if q in asked]}


def _f(code: str, cls: str, message: str, slide: str | None = None) -> dict:
    return {"code": code, "class": cls, "message": message, "slide": slide}
