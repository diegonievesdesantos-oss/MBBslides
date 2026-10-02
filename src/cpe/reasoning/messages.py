"""Does each slide's message still hold? (v2.0, item 5)

Updating the numbers of a slide is not enough when its headline claims something the new numbers
contradict: "Las dos fases se pagan en menos de 5 años" with paybacks now of 9,2 and 5,8 years.
`review` reads every headline against the new values of the deck's numbers (approved edits, figures
derived from them, numbers the plan found current) and gives each slide a verdict:

    holds              no figure of the headline changed and no claim it makes is contradicted
    figures updated    its own figures changed; the claims it makes still hold → the headline with the
                       new figures substituted is proposed
    no longer holds    a threshold claim ("menos de 5 años", "más del 20%", "supera …") was true with the
                       old values and is false with the new ones → a mechanical rewrite is proposed for
                       review, never applied silently
    check              a figure of the headline is outdated or untraced and has no approved value

A threshold claim is checked against the slide's numbers written with the same unit word ("años",
"%", "M€") or about the same measure; it must hold with the OLD values, else it is not read as a
claim about them. Proposals become `set_headline` edits, unapproved.
"""
from __future__ import annotations

import re

LESS = r"menos de|por debajo de|inferior(?:es)? a|no supera[n]?|no llega[n]? a|under|less than|below|within|<|≤"
MORE = r"más de|mas de|por encima de|superior(?:es)? a|supera[n]?|above|over|more than|at least|al menos|>|≥"
CLAIM_RE = re.compile(rf"(?P<cmp>{LESS}|{MORE})\s+(?:el|un|una|los|las)?\s*(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>%|años|año|years?|meses|months?|M€|k€|€|x|veces)?", re.I)


def _unit_word(u: str | None) -> str:
    u = (u or "").lower()
    return {"año": "años", "year": "años", "years": "años", "meses": "meses", "month": "meses", "months": "meses",
            "veces": "x"}.get(u, u)


def _num_unit(q: dict) -> str:
    raw = str(q.get("raw", "")).lower()
    for w, u in (("año", "años"), ("year", "años"), ("mes", "meses"), ("%", "%"), ("x", "x"), ("m€", "M€"), ("€", "€")):
        if raw.endswith(w) or (w in ("%", "x") and raw.endswith(w)):
            return u
    ctx = (q.get("context") or "").lower()
    if re.search(r"\(años\)|años\b|years\b", ctx) and not raw.endswith("%"):
        return "años"
    return ""


def new_values(plan: dict, edits: dict) -> dict:
    """{number id: new value in its own units} from approved edits (derived ones included) and the
    numbers the plan found current; a number with neither is absent (unknown)."""
    from .deck_update import _factor, _parse_core

    hint = plan.get("decimal_mark")
    items = {q["id"]: q for s in plan["slides"] for q in s["numbers"] if q.get("id")}
    vals = {i: (-abs(q["value"]) if str(q["raw"]).startswith("-") else q["value"]) for i, q in items.items() if q["status"] == "current"}
    for e in edits.get("edits") or []:
        if e.get("op", "number") == "number" and e.get("approved") and e.get("id") in items:
            q = items[e["id"]]
            f, v = _factor(q, hint), _parse_core(str(e["replace"]).lstrip("-−"), hint)
            if f and v is not None:
                vals[e["id"]] = (-1 if str(e["replace"]).startswith(("-", "−")) else 1) * v * f
    return vals


def _approved_display(edits: dict) -> dict:
    return {e["id"]: e["replace"] for e in edits.get("edits") or [] if e.get("op", "number") == "number" and e.get("approved") and e.get("id")}


def review(plan: dict, edits: dict) -> list[dict]:
    from .deck_update import _parse_core, display_in

    hint = plan.get("decimal_mark")
    vals = new_values(plan, edits)
    shown = _approved_display(edits)
    out = []
    for s in plan["slides"]:
        head = s.get("headline") or ""
        nums = [q for q in s["numbers"] if q.get("id") and q["status"] != "ignored"]
        in_head = [q for q in s["numbers"] if q["where"] == "title" and q["status"] != "ignored"]
        changed = [q for q in in_head if q["id"] in shown and str(shown[q["id"]]) != str(q.get("core"))]
        unknown = [q for q in in_head if q["id"] not in vals and q["id"] not in shown]
        claims = []
        for m in CLAIM_RE.finditer(head):
            unit = _unit_word(m.group("unit"))
            thr = _parse_core(m.group("num"), hint)
            if thr is None or not unit:
                continue
            less = bool(re.fullmatch(LESS, m.group("cmp"), re.I))
            rel = [q for q in nums if q["where"] != "title" and _num_unit(q) == unit]
            parts = [q for q in rel if not re.search(r"\btotal(es)?\b", q.get("context") or "", re.I)]
            rel = parts or rel  # "las dos fases": the phases, not their total column
            if not rel:
                continue
            olds = [abs(q["value"]) for q in rel]
            if not all((v < thr) if less else (v > thr) for v in olds):
                continue  # not a claim about these numbers (it was not true of them)
            news = [vals.get(q["id"]) for q in rel]
            if any(v is None for v in news):
                claims.append({"claim": m.group(0), "status": "cannot check", "unknown": [q["raw"] for q, v in zip(rel, news) if v is None]})
                continue
            holds = all((abs(v) < thr) if less else (abs(v) > thr) for v in news)
            ex = rel[0]
            claims.append({"claim": m.group(0), "status": "holds" if holds else "no longer holds", "span": [m.start(), m.end()],
                           "old": [q["raw"] for q in rel],
                           "new": [display_in(q, abs(v), hint) for q, v in zip(rel, news)], "unit": unit, "ex": ex["raw"]})
        claims += _superlatives(head, nums, vals) + _signs(head, in_head, vals) + _orders(head, in_head, vals) + _breakeven(head, s, vals)
        proposal = head
        for q in sorted(changed, key=lambda q: -len(q.get("core") or "")):  # the new figures in the headline
            proposal = re.sub(rf"(?<![\d.,]){re.escape(q['core'])}(?![\d])", str(shown[q["id"]]), proposal, count=1)
        broken = [c for c in claims if c["status"] == "no longer holds"]
        for c in broken:
            if c.get("kind") == "breakeven" and c["new"][0][:2] in ("19", "20"):
                proposal = proposal.replace(c["old"][0], c["new"][0], 1)
                continue
            if c.get("kind") == "sign":  # v2.2: "ahorra 0,89 M€" → "cuesta 0,12 M€"
                opp = _opposite(c["verb"], OPP_VERB)
                if opp:
                    proposal = re.sub(rf"\b{re.escape(c['verb'])}\b", opp, proposal, count=1)
                    new = str(shown.get(c["id"], ""))
                    if new[:1] in "-−" and new:
                        proposal = proposal.replace(new, new[1:], 1)
                continue
            if c.get("kind") == "order":  # v2.2: "supera" → "no cubre"
                opp = None if c.get("tie") else _opposite(c["word"], OPP_ORDER)
                if opp:
                    proposal = re.sub(rf"\b{re.escape(c['word'])}\b", opp, proposal, count=1)
                continue
            if c.get("kind") == "breakeven":
                continue  # no mechanical rewrite: the argument itself changed
            if c.get("kind") == "superlative":  # the claimed winner becomes the actual one
                if c.get("winner_label"):
                    proposal = re.sub(re.escape(c["entity"]), c["winner_label"], proposal, count=1, flags=re.I)
                continue
            vals_txt = _join([v for v in dict.fromkeys(c["new"])])  # mechanical: the threshold phrase becomes the actual values
            proposal = proposal.replace(c["claim"].strip(), f"{vals_txt} {c['unit']}".strip(), 1)
        verdict = ("no longer holds" if broken else "check" if [q for q in unknown if q["status"] in ("outdated", "untraced")]
                   else "figures updated" if changed else "holds")
        out.append({"slide": s["slide"], "headline": head, "verdict": verdict, "claims": claims,
                    "changed": [{"old": q["raw"], "new": shown[q["id"]]} for q in changed],
                    "unresolved": [{"number": q["raw"], "status": q["status"]} for q in unknown if q["status"] in ("outdated", "untraced")],
                    "proposal": proposal if proposal != head else None})
    return out


# v2.1 (item 4): more claims a headline makes, each checked against the slide's own numbers and only when it
# was true of the old values (else it is not a claim about them).
ENTITY = r"(?:fase|phase|etapa|stage|zona|zone|regi[oó]n|region|tienda|store|l[ií]nea|line|segmento|segment|opci[oó]n|option|escenario|scenario|planta|plant|canal|channel)\s*[\w\d]+"
SUP_RE = re.compile(rf"(?P<ent>{ENTITY})\s+(?:es|is|ser[ií]a|would be|resulta|queda como|remains)\s+(?:la |el |lo |the )?(?P<cmp>m[aá]s|menos|most|least|mejor|peor|best|worst)\s+(?P<adj>[a-záéíóúñ]+)", re.I)
# adjective → (row of the measure, which value wins)
ADJ = {"rentable": [(r"payback|retorno simple|periodo de recuperaci", "min"), (r"\btir\b|\birr\b", "max"), (r"ahorro neto|net saving|beneficio|profit", "max")],
       "profitable": [(r"payback", "min"), (r"\birr\b|\btir\b", "max"), (r"net saving|profit|ahorro neto", "max")],
       "barata": [(r"coste|cost|inversi|capex|precio|price", "min")], "barato": [(r"coste|cost|inversi|capex|precio|price", "min")],
       "cheap": [(r"cost|capex|price|coste|inversi", "min")], "cara": [(r"coste|cost|inversi|capex|precio|price", "max")],
       "caro": [(r"coste|cost|inversi|capex|precio|price", "max")], "expensive": [(r"cost|capex|price", "max")],
       "productiva": [(r"productiv", "max")], "productivo": [(r"productiv", "max")], "productive": [(r"productiv", "max")],
       "eficiente": [(r"coste por|cost per|productiv", "min")], "r[aá]pida": [(r"plazo|payback|tiempo|time", "min")],
       # v2.2 (item 5)
       "rentables": [(r"payback|retorno simple|periodo de recuperaci", "min"), (r"\btir\b|\birr\b", "max"), (r"ahorro neto|beneficio", "max")],
       "atractiv[ao]s?": [(r"\bvan\b|\bnpv\b|valor actual", "max"), (r"\btir\b|\birr\b", "max"), (r"payback|periodo de recuperaci", "min")],
       "attractive": [(r"\bnpv\b|\bvan\b", "max"), (r"\birr\b|\btir\b", "max"), (r"payback", "min")],
       "valios[ao]s?": [(r"\bvan\b|\bnpv\b|valor", "max")], "valuable": [(r"\bnpv\b|value", "max")],
       "econ[oó]mic[ao]s?": [(r"coste|cost|inversi|capex|precio|price", "min")], "costos[ao]s?": [(r"coste|cost|inversi|capex|precio|price", "max")],
       "barat[ao]s": [(r"coste|cost|inversi|capex|precio|price", "min")], "car[ao]s": [(r"coste|cost|inversi|capex|precio|price", "max")],
       "cheaper|cheapest": [(r"cost|capex|price|coste|inversi", "min")],
       "r[aá]pid[ao]s?": [(r"plazo|payback|tiempo|time|meses|months|semanas|weeks", "min")], "lent[ao]s?": [(r"plazo|payback|tiempo|time", "max")],
       "fast|quick": [(r"time|payback|lead|months|weeks|plazo", "min")], "slow": [(r"time|payback|lead|plazo", "max")],
       "eficientes": [(r"coste por|cost per|productiv", "min")], "efficient": [(r"cost per|coste por|productiv", "min")],
       "productiv[ao]s": [(r"productiv", "max")],
       "grandes?": [(r"volumen|volume|ventas|sales|ingres|revenue|capacidad|capacity|superficie|area", "max")],
       "peque[ñn][ao]s?": [(r"volumen|volume|ventas|sales|ingres|revenue|capacidad|capacity|superficie|area", "min")],
       "large|big": [(r"volume|sales|revenue|capacity|volumen|ventas", "max")], "small": [(r"volume|sales|revenue|capacity|volumen|ventas", "min")],
       "profitable|profitably": [(r"payback", "min"), (r"\birr\b|\btir\b", "max"), (r"net saving|profit|ahorro neto", "max")]}
# "la fase 2 tiene el mayor ahorro": the noun says the measure, mayor / menor which value wins
SUP2_RE = re.compile(rf"(?P<ent>{ENTITY})\s+(?:tiene|aporta|ofrece|genera|logra|consigue|presenta|has|offers|delivers|brings|yields)\s+"
                     rf"(?:la |el |los |las |the )?(?P<cmp>mayor(?:es)?|menor(?:es)?|m[aá]s alt[ao]s?|m[aá]s baj[ao]s?|highest|lowest|largest|smallest|biggest|best|worst)\s+"
                     rf"(?P<noun>[a-záéíóúñ]{{4,}})", re.I)
POS_VERB = re.compile(r"\b(ahorra\w*|ahorro de|genera\w*|gana\w*|crece\w*|sube\w*|aumenta\w*|mejora\w*|aporta\w*|saves?|generates?|earns?|grows?|rises?|increases?|improves?|adds?)\b[^.;\d]{0,25}$", re.I)
ORDER_RE = re.compile(r"\b(supera\w*|por encima de|m[aá]s que|exceeds?|above|higher than|greater than|more than|por debajo de|menos que|below|lower than|less than|inferior a|superior a)\b", re.I)


# v2.2 (item 5): the word that says the opposite, for a sign or an order that flipped (same person and number)
OPP_VERB = {"ahorra": "cuesta", "ahorran": "cuestan", "ahorraría": "costaría", "ahorrarían": "costarían", "ahorrará": "costará",
            "ahorrarán": "costarán", "genera": "consume", "generan": "consumen", "generará": "consumirá", "generarán": "consumirán",
            "gana": "pierde", "ganan": "pierden", "ganará": "perderá", "crece": "cae", "crecen": "caen", "crecerá": "caerá",
            "crecerán": "caerán", "sube": "baja", "suben": "bajan", "subirá": "bajará", "aumenta": "disminuye", "aumentan": "disminuyen",
            "aumentará": "disminuirá", "mejora": "empeora", "mejoran": "empeoran", "mejorará": "empeorará", "aporta": "resta", "aportan": "restan",
            "saves": "costs", "save": "cost", "generates": "consumes", "generate": "consume", "earns": "loses", "earn": "lose",
            "grows": "shrinks", "grow": "shrink", "rises": "falls", "rise": "fall", "increases": "decreases", "increase": "decrease",
            "improves": "worsens", "improve": "worsen", "adds": "subtracts", "add": "subtract"}
OPP_ORDER = {"supera": "no alcanza", "superan": "no alcanzan", "superará": "no alcanzará", "por encima de": "por debajo de",
             "por debajo de": "por encima de", "más que": "menos que", "mas que": "menos que", "menos que": "más que",
             "superior a": "inferior a", "inferior a": "superior a", "exceeds": "falls short of", "exceed": "fall short of",
             "above": "below", "below": "above", "higher than": "lower than", "lower than": "higher than",
             "greater than": "less than", "more than": "less than", "less than": "more than"}


def _opposite(word: str, table: dict) -> str | None:
    w = table.get(word.lower())
    if not w:
        return None
    return w[:1].upper() + w[1:] if word[:1].isupper() else w


def _entity_key(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")).strip()


def _sup_claims(head: str) -> list[tuple]:
    """(match, rules, worse) for each superlative of the headline: "la fase 2 es la más rentable" (the
    adjective's measures) or, v2.2, "la fase 2 tiene el mayor ahorro" (the noun is the measure)."""
    out = []
    for m in SUP_RE.finditer(head):
        adj = (m.group("adj") or "").lower()
        rules = next((v for k, v in ADJ.items() if re.fullmatch(k, adj)), None)
        if rules:
            out.append((m, rules, m.group("cmp").lower() in ("menos", "least", "peor", "worst")))
    for m in SUP2_RE.finditer(head):
        cmp = m.group("cmp").lower()
        low = bool(re.match(r"menor|m[aá]s baj|lowest|smallest|worst", cmp))
        stem = _entity_key(m.group("noun"))[:5]
        if cmp in ("best", "worst"):
            continue  # "the best result": which value wins depends on the measure
        out.append((m, [(stem, "min" if low else "max")], False))
    return out


def _superlatives(head: str, nums: list[dict], vals: dict) -> list[dict]:
    out = []
    for m, rules, worse in _sup_claims(head):
        ent = re.sub(r"^(la|el|the)\s+", "", m.group("ent").strip(), flags=re.I)
        kind_word = _entity_key(ent).split(" ")[0]
        for row_rx, best in rules:
            cells = [q for q in nums if q["where"].startswith("exhibit[") and (re.search(row_rx, q.get("row") or q.get("context") or "", re.I)
                                                                              or re.search(row_rx, _entity_key(q.get("row") or q.get("context") or "")))
                     and not re.search(r"\btotal(es)?\b", q.get("context") or "", re.I)]
            ents = {}
            for q in cells:
                hit = re.search(rf"{kind_word}\s*[\w\d]+", _entity_key(q.get("context") or ""))
                if hit:
                    ents.setdefault(hit.group(0), q)
            if len(ents) < 2 or _entity_key(ent) not in ents:
                continue
            pick = (min if (best == "min") != worse else max)
            old_w = pick(ents, key=lambda e: abs(ents[e]["value"]))
            if old_w != _entity_key(ent):
                continue  # it was not true of these numbers: not the claim's evidence
            news = {e: vals.get(q["id"]) for e, q in ents.items()}
            if any(v is None for v in news.values()):
                out.append({"kind": "superlative", "claim": m.group(0), "status": "cannot check", "unknown": [ents[e]["raw"] for e, v in news.items() if v is None]})
                break
            new_w = pick(news, key=lambda e: abs(news[e]))
            label = re.search(rf"{kind_word}\s*[\w\d]+", (ents[new_w].get("context") or ""), re.I)
            out.append({"kind": "superlative", "claim": m.group(0), "status": "holds" if new_w == old_w else "no longer holds", "entity": ent,
                        "winner_label": label.group(0) if label and new_w != old_w else None,
                        "old": [f"{e}: {ents[e]['raw']}" for e in ents], "new": [f"{e}: {news[e]:g}" for e in news], "measure": row_rx.split("|")[0]})
            break
    return out


def _signs(head: str, in_head: list[dict], vals: dict) -> list[dict]:
    """'ahorra 0,89 M€', 'genera 7,8 M€', 'crece un 6%' with a new value below zero: the direction flipped."""
    from .deck_update import _locate

    out = []
    for q in in_head:
        m = _locate(head, q["raw"], 0)
        if not m or not POS_VERB.search(head[max(0, m.start() - 40):m.start()]) or q["id"] not in vals:
            continue
        old_v = -abs(q["value"]) if str(q["raw"]).startswith("-") else q["value"]
        if old_v < 0:
            continue
        if vals[q["id"]] < 0:
            verb = POS_VERB.search(head[max(0, m.start() - 40):m.start()]).group(1)
            out.append({"kind": "sign", "claim": head[max(0, m.start() - 25):m.end()].strip(), "status": "no longer holds",
                        "old": [q["raw"]], "new": [f"{vals[q['id']]:g}"], "verb": verb, "id": q["id"]})
    return out


def _orders(head: str, in_head: list[dict], vals: dict) -> list[dict]:
    """'el ahorro (1,2 M€) supera la inversión anual (0,9 M€)': two figures of the headline in an order."""
    from .deck_update import _locate

    out = []
    pos = sorted(((m.start(), q) for q in in_head if (m := _locate(head, q["raw"], 0))), key=lambda t: t[0])
    for (pa, a), (pb, b) in zip(pos, pos[1:]):
        mid = ORDER_RE.search(head[pa:pb + 1]) or ORDER_RE.search(head[max(0, pa - 40):pa])
        if not mid:
            continue
        more = not re.search(r"debajo|menos|below|lower|less|inferior", mid.group(0), re.I)
        if ((abs(a["value"]) > abs(b["value"])) if more else (abs(a["value"]) < abs(b["value"]))) is False:
            continue  # not an order these two figures had
        if a["id"] not in vals or b["id"] not in vals:
            continue
        va, vb = abs(vals[a["id"]]), abs(vals[b["id"]])
        ok = va > vb if more else va < vb
        out.append({"kind": "order", "claim": head[pa:pb + len(b["raw"])], "status": "holds" if ok else "no longer holds",
                    "old": [a["raw"], b["raw"]], "new": [f"{va:g}", f"{vb:g}"], "word": mid.group(0), "tie": va == vb})
    return out


BREAK_RE = re.compile(r"\b(se recupera|recupera(?:da)?|payback|break-?even|pays? (?:itself )?back|se paga|retorno)\b[^.;]{0,30}?\b(?:en|in|by|a)\s+((?:19|20)\d\d)\b", re.I)


def _breakeven(head: str, slide: dict, vals: dict) -> list[dict]:
    """'La inversión se recupera en 2030' against the slide's cumulative curve: the first year it is ≥ 0."""
    from .derive import CUM_RE, chart_series

    m = BREAK_RE.search(head)
    if not m:
        return []
    year = m.group(2)
    for (e, name), pts in chart_series(slide).items():
        if not CUM_RE.search(name):
            continue
        cats = [re.search(r"\[([^\[\]]*)\]$", p["where"]).group(1) for p in pts]

        def cross(values):
            return next((c for c, v in zip(cats, values) if v >= 0), None)

        if cross([p["value"] if not str(p["raw"]).startswith("-") else -abs(p["value"]) for p in pts]) != year:
            continue
        news = [vals.get(p["id"]) for p in pts]
        if any(v is None for v in news):
            return [{"kind": "breakeven", "claim": m.group(0), "status": "cannot check", "unknown": [f"{name} {c}" for c, v in zip(cats, news) if v is None][:3]}]
        new_year = cross(news)
        return [{"kind": "breakeven", "claim": m.group(0), "status": "holds" if new_year == year else "no longer holds",
                 "old": [year], "new": [new_year or "after the last year shown"]}]
    return []


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def revised_proposition(r: dict, plan_slide: dict | None, vals: dict) -> dict:
    """v3.1 (spec §50-52): what the slide can assert NOW, as a proposition for the Action Title Engine.
    messages.review decides whether the old argument holds; this states the argument that is true with the new
    values (the mechanical proposal), its kind of claim, and the numbers that prove it (lineage)."""
    kinds = {c.get("kind") for c in r["claims"] if c["status"] == "no longer holds"}
    claim = "comparison" if kinds & {"superlative", "order"} else "trend" if "sign" in kinds else "fact"
    nums = [q for q in (plan_slide or {}).get("numbers") or [] if q.get("id") and q["status"] != "ignored"]
    direction = None
    for c in r["claims"]:
        if c.get("kind") == "sign" and c["status"] == "no longer holds":
            direction = "down"
    return {"statement": r.get("proposal") or r["headline"], "role": "comparison" if claim == "comparison" else "observation",
            "claim_type": claim, "direction": direction, "evidence_ids": [q["id"] for q in nums if q["id"] in vals] or [q["id"] for q in nums],
            "confidence": "medium", "_from": "messages.review (the claim that holds with the new values)"}


def _ate_slide(plan_slide: dict | None, vals: dict, shown: dict, prop: dict) -> dict:
    """The slide as the ATE reads it: the plan's numbers with their NEW values as evidence."""
    ev = []
    for q in (plan_slide or {}).get("numbers") or []:
        if not q.get("id") or q["status"] == "ignored":
            continue
        v = vals.get(q["id"], q.get("value"))
        ev.append({"id": q["id"], "claim": f"{q.get('context') or ''} {shown.get(q['id'], q.get('raw'))}".strip(), "value": abs(v) if isinstance(v, (int, float)) else v})
    return {"id": f"s{(plan_slide or {}).get('slide', 0)}", "kind": "content", "headline": prop.get("statement"), "proposition": prop, "evidence": ev}


def ate_review(text_candidates: list[str], prop: dict | None, slide: dict, lang: str | None) -> dict:
    """Run the Action Title Engine on candidate wordings for an existing-deck slide (standard mode: findings, not gates)."""
    from ..editorial import action_titles as ate

    s = {**slide, "headline": text_candidates[0] if text_candidates else "", "headline_candidates": text_candidates[1:]}
    sel = ate.select(s, prop, {"lang": lang, "profile": {}}, allow_rewrite=False)
    best = max(sel["candidates"], key=lambda e: e["rank"])
    return {"status": "passed" if best["passed"] else "rejected", "selected": best["text"], "hard": best["hard"], "score": best["score"],
            "candidates": [{"text": e["text"], "passed": e["passed"], "hard": e["hard"]} for e in sel["candidates"]],
            "issues": [f"{c}: {m}" for c, cls, m in best["issues"] if cls != "info"]}


def headline_edits(rev: list[dict], edits: dict, plan: dict | None = None, normalize: bool = False) -> int:
    """`set_headline` proposals, unapproved, never applied silently (spec §52-53):

    - a slide whose message no longer holds: messages.review's proposal becomes a revised proposition and goes
      through the Action Title Engine with any wording the agent added to the edit (`candidates`); the edit
      records the proposition and the ATE verdict;
    - with `normalize` (`cpe update --normalize-editorial`): also a slide whose message holds but whose title is
      not an action title (a topic label, two messages…): flagged for rewording (`needs_wording` until a
      candidate passes the ATE);
    - a headline that holds is preserved: no edit. A reviewer's own (approved or hand-written) edit is never touched.
    Returns how many were added or refreshed."""
    have = {e["slide"]: e for e in edits.get("edits") or [] if e.get("op") == "set_headline"}
    vals = new_values(plan, edits) if plan else {}
    shown = _approved_display(edits)
    by_slide = {s["slide"]: s for s in (plan or {}).get("slides") or []}
    lang = _deck_lang(rev)
    n = 0
    for r in rev:
        e = have.get(r["slide"])
        if e and (e.get("approved") or e.get("by_hand")):
            continue
        extra = [c for c in (e or {}).get("candidates") or [] if c]
        if r["verdict"] == "no longer holds" and r["proposal"]:
            prop = revised_proposition(r, by_slide.get(r["slide"]), vals)
            ate = ate_review([r["proposal"]] + extra, prop, _ate_slide(by_slide.get(r["slide"]), vals, shown, prop), lang)
            text = ate["selected"] if ate["status"] == "passed" else r["proposal"]
            new = {"op": "set_headline", "slide": r["slide"], "text": text, "old": r["headline"], "approved": False, "proposition": prop,
                   "editorial": ate, "candidates": extra,
                   "why": "; ".join(f"'{c['claim']}' no longer holds: {', '.join(c['old'])} → {', '.join(c['new'])}" for c in r["claims"]
                                    if c["status"] == "no longer holds")
                   + (" (mechanical rewrite, checked by the Action Title Engine: review the message)" if ate["status"] == "passed"
                      else f" (mechanical rewrite REJECTED by the Action Title Engine: {', '.join(ate['hard'])}; add wording in `candidates`)")}
        elif normalize and r["verdict"] in ("holds", "figures updated"):
            ate = ate_review([r["headline"]] + extra, None, _ate_slide(by_slide.get(r["slide"]), vals, shown, {"statement": r["headline"]}), lang)
            if ate["status"] == "passed" and ate["selected"] == r["headline"]:
                continue  # already an action title: preserved
            ok = ate["status"] == "passed"
            new = {"op": "set_headline", "slide": r["slide"], "text": ate["selected"] if ok else None, "old": r["headline"], "approved": False,
                   "normalize": True, "needs_wording": not ok, "editorial": ate, "candidates": extra,
                   "why": f"editorial normalization (--normalize-editorial): {', '.join(ate['hard']) or 'a candidate reads better'}"
                          + ("" if ok else "; write the action title in `candidates` and re-run")}
        else:
            continue
        if e:
            e.clear()
            e.update(new)
        else:
            edits["edits"].append(new)
        n += 1
    return n


def _deck_lang(rev: list[dict]) -> str | None:
    from ..editorial.signatures import language

    votes = [language(r.get("headline") or "") for r in rev]
    es, en = votes.count("es"), votes.count("en")
    return "es" if es > en else "en" if en > es else None


def markdown(rev: list[dict]) -> str:
    L = ["# Do the slides' messages still hold?", "", "| slide | verdict | headline | why |", "|---|---|---|---|"]
    for r in rev:
        why = "; ".join([f"'{c['claim']}' {c['status']}" + (f": {', '.join(c['old'])} → {', '.join(c['new'])}" if c.get("new") else "")
                         for c in r["claims"]] + [f"{c['old']} → {c['new']}" for c in r["changed"]]
                        + [f"{u['number']} {u['status']}, no approved value" for u in r["unresolved"]])
        L.append(f"| {r['slide']} | **{r['verdict']}** | {r['headline'][:80]} | {why} |")
    props = [r for r in rev if r["proposal"]]
    if props:
        L += ["", "## Proposed headlines", ""] + [f"- slide {r['slide']} ({r['verdict']}): {r['proposal']}" for r in props]
    return "\n".join(L) + "\n"
