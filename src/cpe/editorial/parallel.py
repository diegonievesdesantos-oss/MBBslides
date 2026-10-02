"""Parallel Wording Guarantee (v3.1, spec §19-29, §57-62).

Elements that represent the same logical category must use the same linguistic architecture. The
guarantee works on GROUPS, never on the whole deck:

    explicit     `parallel_group` on slides, key-line points, exhibits or items        → mandatory, exact
    structural   process steps, roadmap workstreams, recommendation cards, options,     → mandatory, exact
                 comparison criteria, design principles, operating-model pillars
                 executive-summary statements, key-line arguments                       → mandatory, family
    headlines    consecutive content slides of one section with the same explicit      → advisory, family
                 proposition role and claim type

`exact` groups share one signature (VERB_OBJECT_OUTCOME…); `family` groups share one family
(declarative conclusions may differ in syntax, tense and modality: spec §57). Truth outranks
symmetry (spec §27): the guarantee reports and asks for rewrites; it never rewrites a member.
"""
from __future__ import annotations

import re
from collections import Counter

from .signatures import analyze

CODES = ("PARALLEL_SIGNATURE_MISMATCH", "PARALLEL_ROLE_MISMATCH", "PARALLEL_TENSE_MISMATCH", "PARALLEL_VOICE_MISMATCH",
         "PARALLEL_GRANULARITY_MISMATCH", "PARALLEL_LENGTH_OUTLIER", "PARALLEL_PUNCTUATION_MISMATCH", "PARALLEL_NUMBERING_MISMATCH",
         "PARALLEL_CAPITALIZATION_MISMATCH", "PARALLEL_REPEATED_OPENING", "PARALLEL_GENERIC_VERB")
FAMILY_CONTEXTS = {"exec_summary", "key_line", "headlines"}
# contexts where the members are labels by nature (value-chain stages, criteria): one form, whichever it is
BROAD_DOMAINS = {"finance", "operations", "sales", "marketing", "procurement", "it", "hr", "technology", "organisation", "organization",
                 "digital", "growth", "customer", "customers", "people", "data", "pricing", "costs", "cost", "supply", "logistics",
                 "finanzas", "operaciones", "ventas", "compras", "tecnología", "tecnologia", "organización", "organizacion",
                 "crecimiento", "clientes", "personas", "datos", "precios", "costes", "logística", "logistica"}
OUTCOME_VERBS = {"increase", "grow", "raise", "boost", "improve", "deliver", "achieve", "reach", "double", "lift", "add", "generate",
                 "aumentar", "incrementar", "mejorar", "crecer", "elevar", "duplicar", "alcanzar", "lograr", "generar", "sumar"}
KPI = re.compile(r"\b(?:ebitda|ebit|revenue|revenues|sales|margin|margins|profit|profitability|cash|roi|roce|ingresos|ventas|margen|"
                 r"beneficio|rentabilidad|caja)\b", re.I)
GENERIC = {"improve", "enhance", "optimise", "optimize", "leverage", "drive", "strengthen", "mejorar", "optimizar", "potenciar",
           "impulsar", "reforzar", "fortalecer"}
DECLARATIVE_ROLES = {"context", "observation", "diagnosis", "driver", "comparison", "insight", "implication", "risk", "status", "impact"}


def _member(ref: str, text: str, role: str | None = None, slide: str | None = None) -> dict | None:
    t = str(text or "").strip()
    if not t:
        return None
    return {"ref": ref, "text": t, "role": role, "slide": slide}


def _items(ex: dict) -> list:
    d = ex.get("data") or {}
    return d.get("items") or ex.get("items") or []


def _item_text(it) -> str:
    if isinstance(it, dict):
        return str(it.get("title") or it.get("label") or it.get("text") or "")
    return str(it)


STRUCTURAL = {  # exhibit type → (context, where the members are)
    "process": "process_steps", "value_chain": "process_steps", "journey": "process_steps",
    "gantt": "roadmap_workstreams", "roadmap": "roadmap_workstreams",
    "harvey_table": "options", "operating_model": "operating_model_pillars",
}
CARD_ARCHETYPES = {"recommendation": "recommendation_cards", "design_principles": "design_principles", "initiatives": "initiative_list",
                   "objectives": "objectives", "levers": "levers", "actions": "recommendation_cards", "next_steps": "recommendation_cards",
                   "decisions_needed": "recommendation_cards", "decisions_required": "recommendation_cards"}


def detect(spec: dict) -> list[dict]:
    """The parallel groups of a deck spec (explicit first; structural groups only where structure proves siblinghood)."""
    from ..spec import slide_exhibits

    groups: dict[str, dict] = {}

    def add(gid: str, kind: str, context: str, members: list, mandatory: bool, strict: str, role: str | None = None, **kw):
        members = [m for m in members if m]
        if len(members) < 2:
            return
        g = groups.setdefault(gid, {"id": gid, "kind": kind, "context": context, "members": [], "mandatory": mandatory,
                                    "strictness": strict, "semantic_role": role, **kw})
        g["members"] += members

    st = spec.get("storyline") or {}
    kl = st.get("key_line") or []
    explicit_kl = {}
    for k in kl:
        if k.get("parallel_group"):
            explicit_kl.setdefault(k["parallel_group"], []).append(_member(f"key_line.{k.get('id')}", k.get("message"), k.get("parallel_role") or k.get("role")))
    for gid, ms in explicit_kl.items():
        add(gid, "explicit", "key_line", ms, True, "exact")
    rest = [k for k in kl if not k.get("parallel_group")]
    if len(rest) >= 2:
        add("key_line", "structural", "key_line", [_member(f"key_line.{k.get('id')}", k.get("message")) for k in rest], True, "family")
    slides = spec.get("slides") or []
    for s in slides:
        sid = s.get("id")
        kind = s.get("kind", "content")
        ed = s.get("editorial") or {}
        pg = ed.get("parallel_group") or s.get("parallel_group")
        if pg and kind in ("content", "exec_summary", "statement"):
            field = "text" if kind == "statement" and s.get("text") else "headline"
            role = ed.get("parallel_role") or s.get("parallel_role")
            prole = (s.get("proposition") or {}).get("role")
            add(pg, "explicit", "headlines", [_member(f"{sid}.headline", s.get(field), prole, sid)], True, "exact", role)
        for k, ex in enumerate(slide_exhibits(s)):
            vt = ex.get("type")
            path = f"{sid}.exhibit[{k}]"
            its = _items(ex)
            # explicit, item level or exhibit level
            per_item = {}
            for i, it in enumerate(its):
                if isinstance(it, dict) and it.get("parallel_group"):
                    per_item.setdefault(it["parallel_group"], []).append(_member(f"{path}.items[{i}]", _item_text(it), it.get("role"), sid))
            for gid, ms in per_item.items():
                add(gid, "explicit", "items", ms, True, "exact", role=ex.get("parallel_role"))
            if ex.get("parallel_group"):
                add(ex["parallel_group"], "explicit", "items", [_member(f"{path}.items[{i}]", _item_text(it), it.get("role") if isinstance(it, dict) else None, sid)
                                                                for i, it in enumerate(its) if not (isinstance(it, dict) and it.get("parallel_group"))]
                    + _structural_members(ex, path, sid), True, "exact", role=ex.get("parallel_role"))
                continue
            if per_item:
                continue
            if kind == "exec_summary" and vt in ("statements", "bullets", "text_columns"):
                labs = [str(it.get("label") or "").strip().lower() for it in its if isinstance(it, dict)]
                if labs and all(labs) and len(set(labs)) == len(labs) and (ex.get("data") or {}).get("style") in ("scr", "pyramid", "sco") \
                        or set(labs) & {"situation", "complication", "resolution", "situación", "complicación", "resolución"}:
                    continue  # SCR statements play different roles: not siblings (spec §34: parallel where logically equivalent)
                add(f"{sid}.exec_summary", "structural", "exec_summary", [_member(f"{path}.items[{i}]", _item_text(it), slide=sid) for i, it in enumerate(its)], True, "family")
                continue
            if vt in STRUCTURAL:
                add(f"{path}.{STRUCTURAL[vt]}", "structural", STRUCTURAL[vt], _structural_members(ex, path, sid), True, "exact")
                continue
            ctx = CARD_ARCHETYPES.get(s.get("archetype") or "") or ("recommendation_cards" if s.get("message_type") == "recommendation" else None)
            if ctx and vt in ("text_columns", "statements", "bullets", "comparison"):
                add(f"{path}.{ctx}", "structural", ctx, [_member(f"{path}.items[{i}]", _item_text(it), slide=sid) for i, it in enumerate(its)], True, "exact")
        if kind == "exec_summary" and s.get("statements") and not slide_exhibits(s):
            add(f"{sid}.exec_summary", "structural", "exec_summary", [_member(f"{sid}.statements[{i}]", _item_text(it), slide=sid) for i, it in enumerate(s["statements"])], True, "family")
    # headline families (spec §22): consecutive, same section, same explicit role and claim type
    run: list[dict] = []

    def flush():
        if len(run) >= 2 and not any((r.get("editorial") or {}).get("parallel_group") or r.get("parallel_group") for r in run):
            p0 = run[0]["proposition"]
            add(f"headlines.{run[0].get('section')}.{p0.get('role')}.{run[0].get('id')}", "inferred", "headlines",
                [_member(f"{r.get('id')}.headline", r.get("headline"), r["proposition"].get("role"), r.get("id")) for r in run], False, "family", p0.get("role"))

    for s in slides:
        p = s.get("proposition") if isinstance(s.get("proposition"), dict) else None
        ok = s.get("kind", "content") == "content" and p and not p.get("_inferred") and p.get("role") and p.get("claim_type") and s.get("section")
        if ok and run and run[-1].get("section") == s.get("section") and run[-1]["proposition"].get("role") == p.get("role") \
                and run[-1]["proposition"].get("claim_type") == p.get("claim_type"):
            run.append(s)
            continue
        flush()
        run = [s] if ok else []
    flush()
    return list(groups.values())


def _structural_members(ex: dict, path: str, sid: str) -> list:
    d = ex.get("data") or {}
    vt = ex.get("type")
    out = []
    if vt in ("process", "value_chain", "journey"):
        for i, st in enumerate(d.get("steps") or d.get("stages") or []):
            out.append(_member(f"{path}.steps[{i}]", _item_text(st), slide=sid))
    elif vt in ("gantt", "roadmap"):
        for i, r in enumerate(d.get("rows") or []):
            out.append(_member(f"{path}.rows[{i}]", r.get("label") if isinstance(r, dict) else r, slide=sid))
    elif vt == "harvey_table":
        for i, c in enumerate(ex.get("columns") or []):
            if i == 0:
                continue  # the criteria column header
            out.append(_member(f"{path}.columns[{i}]", c.get("label") if isinstance(c, dict) else c, slide=sid))
    elif vt == "operating_model":
        for i, p in enumerate(d.get("pillars") or []):
            out.append(_member(f"{path}.pillars[{i}]", _item_text(p), slide=sid))
    else:
        for i, it in enumerate(_items(ex)):
            out.append(_member(f"{path}.items[{i}]", _item_text(it), slide=sid))
    return [m for m in out if m]


# ── the checks ────────────────────────────────────────────────────────────────

def _object_words(a: dict) -> list[str]:
    """Content words after the leading verb and before the outcome marker ('Automate finance' → ['finance'])."""
    body = re.split(r"\b(?:to|by|so that|in order to|para|con el fin de|a fin de|mediante|y así)\b", a["body"], maxsplit=1, flags=re.I)[0]
    toks = re.findall(r"[a-záéíóúñü0-9€%.,]+", body.lower())[1:]
    stop = {"the", "a", "an", "our", "its", "their", "all", "el", "la", "los", "las", "un", "una", "de", "del", "su", "sus", "and", "y"}
    return [t for t in toks if t not in stop]


def check(group: dict, lang: str | None = None) -> dict:
    """Findings for one group: (code, 'hard'|'soft'|'info', message, member refs)."""
    ms = group["members"]
    an = [analyze(m["text"], lang) for m in ms]
    for m, a in zip(ms, an):
        m["signature"], m["family"] = a["signature"], a["family"]
    exact = group["strictness"] == "exact"
    mandatory = group["mandatory"]
    explicit = group["kind"] == "explicit"
    found: list[tuple[str, str, str, list[str]]] = []

    def sev(hard_when: bool) -> str:
        return "hard" if mandatory and hard_when else "soft"

    fam = Counter(a["family"] for a in an)
    target_family = _majority(fam, an[0]["family"])
    if exact and group["context"] in ("process_steps", "options", "operating_model_pillars", "roadmap_workstreams") and set(fam) == {"noun"}:
        target_family = "noun"  # value-chain stages, option names, pillar labels: labels are a legitimate family
    if group["context"] in FAMILY_CONTEXTS or group["strictness"] == "family" or (target_family == "declarative" and not group.get("target_signature")):
        exact = exact and target_family != "declarative" or bool(group.get("target_signature"))
        target_family = "declarative" if fam.get("declarative", 0) >= max(fam.values()) else target_family
    label = {"noun", "gerund"}  # nominal gerunds ("Pricing & promo reset") are labels among labels

    def same(f):
        return f == target_family or (f in label and target_family in label)

    off = [m["ref"] for m, a in zip(ms, an) if not same(a["family"])]
    if off:
        found.append(("PARALLEL_SIGNATURE_MISMATCH", sev(True),
                      f"{len(off)} of {len(ms)} members are not {target_family} like their siblings: "
                      + "; ".join(f"'{m['text'][:50]}' ({a['signature']})" for m, a in zip(ms, an) if not same(a["family"])), off))
    sigs = Counter(a["signature"] for a in an if same(a["family"]))
    target = _majority(sigs, next((a["signature"] for a in an if a["family"] == target_family), an[0]["signature"]))
    group["target_signature"] = target if exact else target_family
    if exact and not off:
        off2 = [m["ref"] for m, a in zip(ms, an) if a["signature"] != target and not (target_family in label and a["family"] in label)]
        if off2:
            found.append(("PARALLEL_SIGNATURE_MISMATCH", sev(explicit), f"Same family, different shape: target {target}; "
                          + "; ".join(f"'{m['text'][:50]}' ({a['signature']})" for m, a in zip(ms, an) if a["signature"] != target), off2))
    # role (explicit roles only)
    roles = [m.get("role") for m in ms]
    want = group.get("semantic_role")
    if group["context"] != "key_line":
        if want:
            bad = [m["ref"] for m in ms if m.get("role") and m["role"] != want]
        else:
            rc = Counter(r for r in roles if r)
            bad = [m["ref"] for m in ms if m.get("role") and len(rc) > 1 and m["role"] != _majority(rc, None)]
        if bad:
            found.append(("PARALLEL_ROLE_MISMATCH", sev(True), f"Members play different roles in the argument ({sorted(set(r for r in roles if r))}): they are not siblings", bad))
    # tense: instructions all in one form; declarative exact groups in one tense
    if target_family == "action":
        tc = Counter(a["tense"] for a in an if a["family"] == "action")
        if len(tc) > 1:
            t0 = _majority(tc, None)
            found.append(("PARALLEL_TENSE_MISMATCH", sev(True), f"Mixed verb forms ({dict(tc)}): keep every member {t0}",
                          [m["ref"] for m, a in zip(ms, an) if a["family"] == "action" and a["tense"] != t0]))
    elif exact and target_family == "declarative":
        tc = Counter(("past" if a["tense"] in ("past", "perfect") else "present") for a in an if a["tense"] in ("past", "present", "perfect"))
        if len(tc) > 1:
            t0 = _majority(tc, None)
            found.append(("PARALLEL_TENSE_MISMATCH", sev(explicit), f"Mixed tenses ({dict(tc)}) in a group that should read as one family", []))
    # voice
    vc = Counter(a["voice"] for a in an)
    if len(vc) > 1 and (exact or explicit):  # declarative families may mix voice (spec §57: not identical syntax)
        found.append(("PARALLEL_VOICE_MISMATCH", sev(explicit and exact), "Active and passive voice mixed: "
                      + "; ".join(f"'{m['text'][:50]}'" for m, a in zip(ms, an) if a["voice"] == "passive"),
                      [m["ref"] for m, a in zip(ms, an) if a["voice"] == "passive"]))
    # granularity (spec §26): a KPI outcome posing as an action among operational actions; a whole function among specific objects
    if target_family == "action" and len(ms) >= 2:
        objs = [_object_words(a) for a in an]
        kpi_act = [i for i, a in enumerate(an) if a["family"] == "action" and a["lead"] in OUTCOME_VERBS and KPI.search(" ".join(objs[i])) and a["has_number"]]
        broad = [i for i, o in enumerate(objs) if len(o) == 1 and o[0] in BROAD_DOMAINS]
        specific = [i for i, o in enumerate(objs) if not (len(o) == 1 and o[0] in BROAD_DOMAINS)]
        bad = sorted(set(kpi_act if 0 < len(kpi_act) < len(ms) else []) | set(broad if broad and len(specific) >= len(ms) / 2 else []))
        if bad:
            found.append(("PARALLEL_GRANULARITY_MISMATCH", sev(explicit), "Members sit at different levels: "
                          + "; ".join(f"'{ms[i]['text'][:50]}'" + (" (a quantified outcome, not an action)" if i in kpi_act else " (a whole function)") for i in bad),
                          [ms[i]["ref"] for i in bad]))
    # numbers: some members quantified, others not (instruction / label groups only)
    if target_family != "declarative" and len(ms) >= 3:
        nq = sum(a["has_number"] for a in an)
        if 0 < nq < len(ms) and not all(a["numbered"] for a in an):
            found.append(("PARALLEL_NUMBERING_MISMATCH", "soft", f"{nq} of {len(ms)} members carry a figure: quantify all or none", []))
    if 0 < sum(a["numbered"] for a in an) < len(ms):
        found.append(("PARALLEL_NUMBERING_MISMATCH", "soft", "Some members are enumerated ('1.', 'Option A —') and others are not", []))
    # punctuation, capitalisation
    term = Counter(a["terminal"] for a in an)
    if len(term) > 1:
        found.append(("PARALLEL_PUNCTUATION_MISMATCH", "soft", f"Terminal punctuation is mixed ({dict(term)})", []))
    cs = Counter(a["case"] for a in an if a["words"] >= 2)
    if len(cs) > 1:
        found.append(("PARALLEL_CAPITALIZATION_MISMATCH", "soft", f"Capitalisation is mixed ({dict(cs)})", []))
    # length (spec §24 max_length_spread, read against the group median)
    lens = sorted(a["words"] for a in an)
    med = lens[len(lens) // 2]
    spread = group.get("max_length_spread", 0.35)
    out_len = [m["ref"] for m, a in zip(ms, an) if med and abs(a["words"] - med) >= 3 and abs(a["words"] - med) / med > 2 * spread]
    if out_len and len(ms) >= 3:
        found.append(("PARALLEL_LENGTH_OUTLIER", "soft", f"Member length far from the group's ({med} words)", out_len))
    # repetition (spec §62): advisory only
    leads = Counter(a["lead"] for a in an if a["family"] == "action")
    if leads and len(ms) >= 3 and max(leads.values()) >= 3:
        found.append(("PARALLEL_REPEATED_OPENING", "info", f"'{leads.most_common(1)[0][0]}' opens {max(leads.values())} members: choose more precise verbs", []))
    gen = [a["lead"] for a in an if a["lead"] in GENERIC]
    if len(gen) >= max(2, len(ms) / 2):
        found.append(("PARALLEL_GENERIC_VERB", "info", f"Generic verbs {sorted(set(gen))}: name the actual action", []))
    hard = [f for f in found if f[1] == "hard"]
    return {**{k: v for k, v in group.items() if k != "members"}, "members": [{k: m[k] for k in ("ref", "text", "signature", "family", "slide", "role") if k in m} for m in ms],
            "findings": [{"code": c, "class": cls, "message": msg, "members": refs} for c, cls, msg, refs in found],
            "status": "failed" if hard else "warning" if any(f[1] == "soft" for f in found) else "passed"}


def _majority(c: Counter, default):
    if not c:
        return default
    top = c.most_common()
    best = top[0][1]
    tied = [k for k, n in top if n == best]
    return default if default in tied else tied[0]
