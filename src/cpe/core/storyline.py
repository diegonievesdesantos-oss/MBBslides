"""Storyline engine.

The storyline is modelled explicitly (pyramid principle):

    governing_thought           ← the one-sentence answer (top of the pyramid)
      key_line[1..5]            ← the arguments that prove it (MECE, same logical type)
        slides                  ← each proves one key-line point with evidence

Frameworks give the key line its narrative shape. Deck types give a default
framework, density profile and a slide skeleton. `ghost_deck` renders the
headline-only read-through that consultants use to test horizontal logic.
"""
from __future__ import annotations

import re

from ..spec import CONTENT_KINDS, DECK_TYPES, issue

FRAMEWORKS = {
    "SCR": {
        "name": "Situation → Complication → Resolution",
        "roles": ["situation", "complication", "resolution"],
        "use": "Default for recommendations: frame the context the audience agrees with, the change that creates tension, the answer.",
        "questions": ["What is true and uncontroversial?", "What changed / what is the problem?", "What should we do?"],
    },
    "CII": {
        "name": "Context → Insight → Implication",
        "roles": ["context", "insight", "implication"],
        "use": "Research read-outs and market analysis where the value is a non-obvious finding.",
        "questions": ["What do we look at?", "What did we find that is not obvious?", "So what for the business?"],
    },
    "PDS": {
        "name": "Problem → Drivers → Solution",
        "roles": ["problem", "drivers", "solution"],
        "use": "Performance problems: quantify the gap, decompose into root causes, address each.",
        "questions": ["How big is the problem?", "What causes it (MECE)?", "Which levers fix it?"],
    },
    "DRI": {
        "name": "Diagnosis → Recommendation → Impact",
        "roles": ["diagnosis", "recommendation", "impact"],
        "use": "Transformation and operating-model work: evidence, what to change, value at stake.",
        "questions": ["Where do we stand?", "What do we change?", "What is it worth and when?"],
    },
    "MPO": {
        "name": "Market → Position → Opportunity",
        "roles": ["market", "position", "opportunity"],
        "use": "Strategy, CDD and growth decks: where the profit pool is, where we stand, where to play.",
        "questions": ["How attractive is the market?", "How do we (or the target) compete?", "Where is the upside?"],
    },
    "CGT": {
        "name": "Current state → Gap → Target state",
        "roles": ["current", "gap", "target"],
        "use": "Capability, maturity and roadmap decks.",
        "questions": ["What exists today?", "What is missing vs ambition/benchmark?", "What does good look like and how do we get there?"],
    },
    "HEC": {
        "name": "Hypothesis → Evidence → Conclusion",
        "roles": ["hypothesis", "evidence", "conclusion"],
        "use": "Investment memos and due diligence: test the thesis explicitly.",
        "questions": ["What must be true?", "What does the data say, for and against?", "Do we believe it (and at what price)?"],
    },
}

# deck type → default framework, profile and slide skeleton (archetypes, not content)
DECK_BLUEPRINTS = {
    "strategy_deck": ("MPO", ["exec_summary", "market_size", "market_growth", "segmentation", "competitive_position", "options", "recommendation", "roadmap", "financial_impact", "next_steps"]),
    "business_review": ("SCR", ["exec_summary", "kpi_overview", "revenue_trend", "margin_bridge", "segment_performance", "issues", "actions", "outlook"]),
    "investment_memo": ("HEC", ["exec_summary", "thesis", "market", "competitive_position", "financials", "value_creation", "risks", "valuation_returns", "recommendation"]),
    "board_presentation": ("SCR", ["exec_summary", "performance", "key_issue", "options", "recommendation", "decision_required"]),
    "market_analysis": ("CII", ["exec_summary", "market_size", "growth_drivers", "segmentation", "geography", "competitive_landscape", "implications"]),
    "commercial_due_diligence": ("HEC", ["exec_summary", "market_size", "market_growth", "customer_research", "competitive_position", "business_plan_review", "risks", "conclusion"]),
    "transformation_program": ("DRI", ["exec_summary", "case_for_change", "diagnosis", "target_state", "initiatives", "roadmap", "value_at_stake", "governance"]),
    "operating_model": ("CGT", ["exec_summary", "current_state", "pain_points", "design_principles", "target_operating_model", "org_structure", "transition"]),
    "product_strategy": ("MPO", ["exec_summary", "customer_needs", "market", "positioning", "product_roadmap", "business_case"]),
    "financial_analysis": ("PDS", ["exec_summary", "pnl_overview", "revenue_bridge", "cost_structure", "cash", "scenarios", "recommendation"]),
    "sales_strategy": ("PDS", ["exec_summary", "pipeline_funnel", "segment_economics", "coverage_model", "levers", "targets", "plan"]),
    "implementation_roadmap": ("CGT", ["exec_summary", "objectives", "workstreams", "roadmap", "milestones", "risks", "governance"]),
    "executive_update": ("SCR", ["exec_summary", "progress", "issues", "decisions_needed"]),
    "project_steering_committee": ("SCR", ["exec_summary", "status_scorecard", "plan_vs_actual", "risks_issues", "decisions_required", "next_steps"]),
}

# archetype → suggested message type + visual (a starting hypothesis, never binding)
ARCHETYPES = {
    "exec_summary": ("argument", "statements"),
    "market_size": ("composition", "stacked_column"),
    "market_growth": ("trend", "column"),
    "growth_drivers": ("argument", "bullets"),
    "segmentation": ("segmentation", "mekko"),
    "geography": ("geography", "tile_map"),
    "competitive_position": ("positioning", "matrix_2x2"),
    "competitive_landscape": ("comparison", "harvey_table"),
    "options": ("comparison", "harvey_table"),
    "recommendation": ("recommendation", "text_columns"),
    "roadmap": ("plan", "gantt"),
    "financial_impact": ("change_bridge", "waterfall"),
    "next_steps": ("recommendation", "table"),
    "kpi_overview": ("single_number", "kpi"),
    "revenue_trend": ("trend", "combo"),
    "margin_bridge": ("change_bridge", "waterfall"),
    "segment_performance": ("comparison", "heatmap"),
    "issues": ("argument", "bullets"),
    "actions": ("recommendation", "table"),
    "outlook": ("trend", "line"),
    "thesis": ("argument", "statements"),
    "market": ("trend", "column"),
    "financials": ("trend", "combo"),
    "value_creation": ("change_bridge", "waterfall"),
    "risks": ("comparison", "table"),
    "valuation_returns": ("comparison", "table"),
    "performance": ("single_number", "kpi"),
    "key_issue": ("change_bridge", "waterfall"),
    "decision_required": ("recommendation", "statement"),
    "implications": ("argument", "text_columns"),
    "customer_research": ("ranking", "bar"),
    "business_plan_review": ("trend", "combo"),
    "conclusion": ("argument", "statements"),
    "case_for_change": ("single_number", "kpi"),
    "diagnosis": ("hierarchy", "driver_tree"),
    "target_state": ("structure", "operating_model"),
    "initiatives": ("comparison", "harvey_table"),
    "value_at_stake": ("change_bridge", "waterfall"),
    "governance": ("hierarchy", "org_chart"),
    "current_state": ("structure", "layers"),
    "pain_points": ("flow", "journey"),
    "design_principles": ("argument", "text_columns"),
    "target_operating_model": ("structure", "operating_model"),
    "org_structure": ("hierarchy", "org_chart"),
    "transition": ("plan", "gantt"),
    "customer_needs": ("ranking", "bar"),
    "positioning": ("positioning", "matrix_2x2"),
    "product_roadmap": ("plan", "gantt"),
    "business_case": ("change_bridge", "waterfall"),
    "pnl_overview": ("comparison", "table"),
    "revenue_bridge": ("change_bridge", "bridge"),
    "cost_structure": ("composition", "bar"),
    "cash": ("trend", "column"),
    "scenarios": ("comparison", "table"),
    "pipeline_funnel": ("flow", "funnel"),
    "segment_economics": ("comparison", "heatmap"),
    "coverage_model": ("structure", "layers"),
    "levers": ("hierarchy", "driver_tree"),
    "targets": ("single_number", "kpi"),
    "plan": ("plan", "gantt"),
    "objectives": ("argument", "text_columns"),
    "workstreams": ("structure", "layers"),
    "milestones": ("plan", "timeline"),
    "progress": ("status", "scorecard"),
    "decisions_needed": ("recommendation", "statements"),
    "status_scorecard": ("status", "scorecard"),
    "plan_vs_actual": ("plan", "gantt"),
    "risks_issues": ("status", "table"),
    "decisions_required": ("recommendation", "statements"),
}


def scaffold(deck_type: str, title: str = "", governing_thought: str = "", theme: str = "meridian") -> dict:
    """Skeleton deck spec with placeholders the agent must replace (the lint flags any left)."""
    if deck_type not in DECK_BLUEPRINTS:
        raise ValueError(f"Unknown deck_type '{deck_type}'. Known: {', '.join(DECK_TYPES)}")
    fw, archetypes = DECK_BLUEPRINTS[deck_type]
    roles = FRAMEWORKS[fw]["roles"]
    key_line = [{"id": f"K{i + 1}", "role": r, "message": f"TODO: {FRAMEWORKS[fw]['questions'][i]}"} for i, r in enumerate(roles)]
    slides = [{"id": "s01", "kind": "cover", "title": title or "TODO title", "subtitle": "TODO: subtitle states the answer"}]
    n = 2
    for a in archetypes:
        mt, vt = ARCHETYPES.get(a, ("argument", "bullets"))
        s = {
            "id": f"s{n:02d}",
            "kind": "exec_summary" if a == "exec_summary" else "content",
            "archetype": a,
            "section": key_line[min(len(key_line) - 1, (archetypes.index(a) * len(key_line)) // max(1, len(archetypes)))]["id"] if a != "exec_summary" else None,
            "purpose": f"TODO: what must the audience accept after this slide? ({a})",
            "headline": "TODO: full-sentence conclusion (so-what), ideally quantified",
            "message_type": mt,
            "evidence": [],
            "visual": {"type": vt if a != "exec_summary" else "statements", "data": {}},
            "source": "TODO",
        }
        slides.append(s)
        n += 1
    return {
        "meta": {"title": title or "TODO title", "deck_type": deck_type, "theme": theme, "date": "", "client": ""},
        "storyline": {"framework": fw, "governing_thought": governing_thought or "TODO: one-sentence answer", "audience": "TODO", "decision_sought": "TODO", "key_line": key_line},
        "slides": slides,
    }


def ghost_deck(spec: dict) -> str:
    """Headline-only read-through: if this does not read as an argument, the deck will not."""
    st = spec.get("storyline", {})
    out = [f"# Ghost deck — {spec.get('meta', {}).get('title', '')}", ""]
    out.append(f"**Governing thought:** {st.get('governing_thought', '')}")
    out.append("")
    kl = {k["id"]: k for k in st.get("key_line", [])}
    current = None
    for i, s in enumerate(spec.get("slides", []), start=1):
        kind = s.get("kind", "content")
        if kind in ("cover",):
            continue
        if kind == "divider":
            out.append(f"\n## {s.get('title', '')}")
            continue
        sec = s.get("section")
        if sec and sec != current and sec in kl:
            current = sec
            out.append(f"\n### {sec} · {kl[sec].get('role', '').upper()} — {kl[sec].get('message', '')}")
        out.append(f"{i:>2}. {s.get('headline') or s.get('title', '')}")
    return "\n".join(out) + "\n"


def _content_words(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "in", "on", "to", "and", "or", "for", "by", "with", "is", "are", "was", "be", "as", "at", "from", "that", "this", "its", "our", "we", "will", "can", "de", "la", "el", "en", "y", "los", "las", "del", "que", "un", "una", "por", "con", "para", "se", "es"}
    return {w for w in re.findall(r"[a-záéíóúñü0-9%]+", text.lower()) if w not in stop and len(w) > 2}


def lint_storyline(spec: dict) -> list[dict]:
    out: list[dict] = []
    st = spec.get("storyline") or {}
    slides = spec.get("slides") or []
    kl = st.get("key_line") or []
    fw = st.get("framework")
    if fw and fw not in FRAMEWORKS:
        out.append(issue("warning", "STORY_FRAMEWORK", f"Unknown framework '{fw}'. Known: {', '.join(FRAMEWORKS)}"))
    if kl and not 2 <= len(kl) <= 5:
        out.append(issue("warning", "STORY_KEYLINE_SIZE", f"Key line has {len(kl)} points; 2-5 keeps the pyramid readable"))
    gt = st.get("governing_thought", "")
    n_gt = sum(1 for w in (gt or "").split() if re.search(r"[A-Za-zÀ-ÿ0-9]", w))  # words as a reader counts them (DEBT L4)
    if gt and n_gt > 35:
        out.append(issue("warning", "STORY_GT_LONG", f"Governing thought has {n_gt} words (over 35): it should fit in one breath"))
    content = [s for s in slides if s.get("kind", "content") == "content"]
    # exec summary present and early
    es_idx = next((i for i, s in enumerate(slides) if s.get("kind") == "exec_summary"), None)
    # a declared slide COLLECTION (the archetype battery: variations of one archetype) is not a
    # storyline and needs no executive summary; every other storyline rule still applies
    if len(content) >= 5 and es_idx is None and not st.get("collection"):
        out.append(issue("error", "STORY_NO_EXEC_SUMMARY", "Decks with ≥5 content slides need an executive summary (answer first)"))
    elif es_idx is not None and es_idx > 2:
        out.append(issue("warning", "STORY_EXEC_LATE", "Executive summary should be slide 2-3 (answer first)"))
    # each key-line point is supported by at least one slide, and in order
    used = [s.get("section") for s in content if s.get("section")]
    for k in kl:
        if k.get("id") not in used:
            out.append(issue("warning", "STORY_UNSUPPORTED_KEYLINE", f"Key-line point {k.get('id')} ('{k.get('message', '')[:60]}') has no supporting slide"))
    order = [k.get("id") for k in kl]
    seen = []
    for sec in used:
        if not seen or seen[-1] != sec:
            seen.append(sec)
    if len(seen) != len(set(seen)):
        out.append(issue("warning", "STORY_SECTION_ORDER", "Sections are interleaved; group slides by key-line point: " + " → ".join(seen)))
    elif order and [s for s in order if s in seen] != seen:
        out.append(issue("info", "STORY_SECTION_SEQUENCE", "Slide sections do not follow key-line order"))
    # repeated / near-duplicate headlines
    heads = [(s.get("id"), s.get("headline", "")) for s in content]
    for i in range(len(heads)):
        for j in range(i + 1, len(heads)):
            a, b = _content_words(heads[i][1]), _content_words(heads[j][1])
            if a and b and len(a & b) / max(1, min(len(a), len(b))) > 0.8:
                out.append(issue("warning", "STORY_DUP_HEADLINE", f"Headlines of {heads[i][0]} and {heads[j][0]} say nearly the same thing", heads[j][0]))
    # exec summary covers the key line
    if es_idx is not None and kl:
        es = slides[es_idx]
        items = ((es.get("visual") or {}).get("data") or {}).get("items") or es.get("statements") or []
        es_text = " ".join((it.get("title", "") + " " + str(it.get("text", ""))) if isinstance(it, dict) else str(it) for it in items)
        if items and len(items) < len(kl):
            out.append(issue("warning", "STORY_ES_COVERAGE", f"Executive summary has {len(items)} points for {len(kl)} key-line arguments", es.get("id")))
        if es_text and gt:
            if not _content_words(gt) & _content_words(es_text + " " + es.get("headline", "")):
                out.append(issue("info", "STORY_ES_GT", "Executive summary does not echo the governing thought vocabulary", es.get("id")))
    # layout monotony (adjacent slides)
    prev = None
    run = 0
    for s in slides:
        lay = s.get("layout")
        if lay and lay != "auto" and lay == prev:
            run += 1
            if run >= 2:
                out.append(issue("warning", "STORY_LAYOUT_MONOTONY", f"Three consecutive slides use layout '{lay}'", s.get("id")))
        else:
            run = 0
        prev = lay
    # closing / next steps for decision decks
    if st.get("decision_sought") and content:
        last = [s for s in slides if s.get("kind", "content") in CONTENT_KINDS | {"closing", "statement"}][-1]
        mt = last.get("message_type")
        if mt not in ("recommendation", "plan", "status") and last.get("kind") not in ("closing", "statement"):
            out.append(issue("info", "STORY_NO_ASK", "The deck seeks a decision but does not end on a recommendation / next steps slide", last.get("id")))
    return out
