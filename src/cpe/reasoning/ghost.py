"""Ghost deck from the deck plan — the argument from headlines alone, before any rendering."""
from __future__ import annotations

from pathlib import Path

from .checks import _load


def ghost_markdown(work_dir: str | Path) -> str:
    work = Path(work_dir)
    dp = _load(work, "deck_plan.json") or {}
    sl = _load(work, "storyline.json") or {}
    kl = {k["id"]: k for k in sl.get("key_line") or []}
    L = ["# Ghost deck", "", f"**Governing thought:** {sl.get('governing_thought', '—')}", "",
         "| # | headline | role in the argument | evidence | priority |", "|---|---|---|---|---|"]
    for n, s in enumerate(dp.get("slides") or [], 1):
        role = s.get("role") or (f"{s['key_line']}: {kl[s['key_line']]['message'][:60]}" if s.get("key_line") in kl else "—")
        ev = ", ".join((s.get("insights") or []) + (s.get("facts") or [])) or "—"
        L.append(f"| {n} | {s.get('headline', '').replace('|', '/')} | {role.replace('|', '/')} | {ev} | {s.get('priority', '')} |")
    app = [s for s in dp.get("slides") or [] if s.get("priority") == "appendix"]
    L += ["", f"Read the headlines top to bottom: they must make the argument alone. {len(app)} appendix slide(s)."]
    return "\n".join(L) + "\n"


def write_ghost(work_dir: str | Path) -> Path:
    p = Path(work_dir) / "ghost_deck.md"
    p.write_text(ghost_markdown(work_dir), encoding="utf-8")
    return p


def enrich_evidence(work_dir: str | Path) -> int:
    """Fill deck.json evidence items that cite a fact id with the fact's claim, values and source,
    so the render pipeline's headline-proof check sees the same numbers as the reasoning check."""
    import json

    from .checks import check_computed

    work = Path(work_dir)
    deck = _load(work, "deck.json")
    facts = {f["id"]: f for f in (_load(work, "facts.json") or {}).get("facts", [])}
    facts.update({a["id"]: {**a, "claim": a.get("statement", ""), "source": {"file": "assumptions.json"}}
                  for a in (_load(work, "assumptions.json") or {}).get("assumptions", [])})
    facts.update(check_computed(_load(work, "computed_facts.json"), facts)[1])
    n = 0
    for s in (deck or {}).get("slides") or []:
        for e in s.get("evidence") or []:
            f = facts.get(e.get("fact")) if isinstance(e, dict) else None
            if f:
                e.setdefault("claim", f["claim"])  # the agent's wording stays; the source text is kept beside it
                e["fact_claim"] = f["claim"]
                e["values"] = [v["value"] for v in f.get("values") or []]
                e["source"] = (f.get("source") or {}).get("file")
                n += 1
    (work / "deck.json").write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return n
