"""Headline engine: lint + scoring of action titles.

A headline is the slide's conclusion — what an executive should understand
after five seconds. This module cannot write headlines (the agent does), but it
deterministically rejects the usual failures:

  HEADLINE_TOPIC           a topic label ("Revenue evolution") instead of a claim
  HEADLINE_TWO_MESSAGES    two claims joined by "and"/"y" → split or choose
  HEADLINE_VAGUE           unquantified intensifiers ("significant", "strong")
  HEADLINE_LONG            over the profile word budget
  HEADLINE_UNQUANTIFIED    data slide whose headline carries no number
  HEADLINE_NUMBER_UNSUPPORTED  a number in the headline that the evidence /
                           exhibit data cannot produce (the chart must prove it)
"""
from __future__ import annotations

import itertools
import math
import re

from ..spec import issue

GENERIC_NOUNS = {
    "overview", "analysis", "evolution", "update", "summary", "segmentation", "landscape", "performance", "results",
    "market", "revenue", "revenues", "sales", "costs", "cost", "agenda", "introduction", "background", "context",
    "trends", "trend", "financials", "roadmap", "timeline", "structure", "strategy", "review", "status", "outlook",
    "benchmark", "benchmarking", "comparison", "change", "breakdown", "split", "distribution", "mix", "view", "profile", "deep-dive", "options", "next", "steps", "appendix", "methodology", "approach",
    "resumen", "análisis", "evolución", "mercado", "ventas", "costes", "contexto", "tendencias", "estrategia",
    "situación", "segmentación", "panorama", "resultados", "visión", "general", "hoja", "ruta", "próximos", "pasos",
}

VERBS = {
    # English
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "will", "would", "should", "must", "can", "could", "may",
    "grew", "grows", "grow", "fell", "falls", "fall", "rose", "rises", "rise", "declined", "declines", "decline", "increased",
    "increases", "decreased", "decreases", "doubled", "doubles", "halved", "tripled", "reached", "reaches", "represents",
    "represent", "accounts", "account", "explains", "explain", "drives", "drive", "drove", "generates", "generate",
    "generated", "outperforms", "outperform", "outperformed", "lags", "lag", "lagged", "remains", "remain", "stays",
    "requires", "require", "needs", "need", "enables", "enable", "unlocks", "unlock", "delivers", "deliver", "adds", "add",
    "report", "reports", "reported", "share", "shares", "differ", "differs", "fill", "fills", "passed", "pass", "passes",
    "stands", "stand", "sit", "trail", "hit", "hits", "halve", "halves", "grew", "drop", "drops", "dropped",
    "reporta", "reportan", "comparten", "difieren", "llena", "supera", "caen", "suben", "crecen", "pierde", "pierden", "gana", "ganan",
    "offers", "offer", "creates", "create", "concentrates", "concentrate", "slowed", "slows", "accelerated", "accelerates",
    "shifted", "shifts", "shift", "leads", "lead", "led", "wins", "win", "lost", "loses", "lose", "captures", "capture",
    "exceeds", "exceed", "exceeded", "trails", "trail", "dominate", "dominates", "depends", "depend", "costs", "cost",
    "pays", "pay", "saves", "save", "cut", "cuts", "reduce", "reduces", "reduced", "improve", "improves", "improved",
    "expand", "expands", "expanded", "enter", "enters", "prioritise", "prioritize", "focus", "focuses", "invest",
    "invests", "recommend", "recommends", "should", "stabilised", "stabilized", "recovered", "recovers", "peaked", "peaks",
    "comes", "come", "came", "sits", "sit", "hold", "holds", "held", "makes", "make", "made", "takes", "take", "took",
    "brings", "bring", "keeps", "keep", "gains", "gain", "gained", "moves", "move", "moved", "shows", "show", "showed",
    "point", "points", "suggests", "suggest", "implies", "imply", "limits", "limit", "constrains", "constrain", "fund",
    "funds", "returns", "return", "breaks", "break", "closes", "close", "narrows", "narrow", "widens", "widen", "widened",
    "runs", "run", "ran", "manages", "manage", "oversees", "oversee", "owns", "own", "sets", "set", "covers", "cover",
    "removes", "remove", "gate", "gates", "cuts", "rose", "secures", "secure", "lose", "loses", "arrive", "arrives",
    "ramp", "ramps", "offers", "delivered", "delivering", "review", "ask", "asks", "asked", "approve", "decide",
    # Spanish
    "es", "son", "fue", "fueron", "está", "están", "ha", "han", "será", "serán", "debe", "deben", "puede", "pueden",
    "crece", "crecen", "creció", "cae", "caen", "cayó", "sube", "suben", "subió", "representa", "representan", "explica",
    "explican", "genera", "generan", "supera", "superan", "requiere", "requieren", "concentra", "concentran", "permite",
    "permiten", "aporta", "aportan", "duplica", "alcanza", "alcanzó", "lidera", "lideran", "mantiene", "necesita",
    "ofrece", "reduce", "mejora", "amplía", "entrar", "priorizar", "invertir", "recomendamos", "se",
}

VAGUE = {
    "significant", "significantly", "various", "several", "some", "important", "interesting", "robust", "strong",
    "substantial", "considerable", "many", "numerous", "key", "notable", "impressive", "massive", "huge",
    "significativo", "significativa", "importante", "varios", "algunos", "fuerte", "considerable", "notable",
}

NUM_RE = re.compile(r"(?<![\w.,])[-−+]?(?:\d+,\d{1,2}(?!\d)|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\s*(?:%|pp|x|bn|mn|m|k|b)(?![A-Za-z]))?", re.IGNORECASE)


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9%€$£.,'’\-]+", text or "")


def _tokens(text: str) -> list[str]:
    return [w.lower().strip(".,;:!?()'’\"") for w in (text or "").split()]


def has_verb(text: str, within: int | None = None) -> bool:
    toks = _tokens(text)
    if within:
        toks = toks[:within]
    if any(t in VERBS and not (i > 0 and toks[i - 1] in ("to", "para")) for i, t in enumerate(toks)):
        return True
    # English inflection heuristics on non-initial tokens
    for t in toks[1:]:
        if len(t) > 4 and (t.endswith("ed") or (t.endswith("es") and not t.endswith("ies"))):
            return True
    return False


DURATION_RE = re.compile(r"^\s*[- ]?(?:month|week|year|day|quarter|hour|minute|wave|step|phase|mes|semana|año|día|trimestre|fase|ola)", re.IGNORECASE)


def numbers_in(text: str) -> list[tuple[float, str]]:
    out = []
    text = text or ""
    for m in NUM_RE.finditer(text):
        raw = m.group(0).strip()
        if DURATION_RE.match(text[m.end():]):
            continue  # durations / counts of time units are plan facts, not data claims
        prev = text[: m.start()].rstrip().split(" ")[-1].lower() if text[: m.start()].strip() else ""
        if prev in ("wave", "waves", "phase", "step", "stage", "q", "h", "fy", "tier", "level", "option", "scenario", "ola", "fase", "hub", "top"):
            continue  # identifiers ("wave 1", "phase 2"), not quantities
        unit = re.sub(r"[-−+\d.,\s]", "", raw).lower()
        num = raw.replace("−", "-")
        num = num.replace(",", ".") if re.search(r"\d,\d{1,2}(?!\d)", num) else num.replace(",", "")  # Spanish decimal comma
        num = re.sub(r"[^\d.\-+]", "", num)
        try:
            v = float(num)
        except ValueError:
            continue
        # ignore plain years
        if unit == "" and 1900 <= v <= 2100 and float(v).is_integer():
            continue
        out.append((v, unit))
    return out


def lint_headline(headline: str, slide: dict | None = None, profile: dict | None = None, extra_values: list[float] | None = None) -> tuple[int, list[dict]]:
    sid = (slide or {}).get("id")
    out: list[dict] = []
    h = (headline or "").strip()
    profile = profile or {}
    if not h or "TODO" in h or "lorem" in h.lower() or re.search(r"\[[^\]]+\]", h):
        return 0, [issue("error", "HEADLINE_PLACEHOLDER", "Headline missing or still a placeholder", sid)]
    toks = _tokens(h)
    n = len(toks)
    score = 100
    verb = has_verb(h)
    generic = sum(1 for t in toks if t in GENERIC_NOUNS)
    if not verb and (n <= 10 or generic >= 1):
        out.append(issue("error", "HEADLINE_TOPIC", f"'{h}' reads as a topic, not a conclusion. State what the data shows (subject + verb + so-what)", sid))
        score -= 50
    elif not verb:
        out.append(issue("warning", "HEADLINE_NO_VERB", "Headline has no verb; action titles are full sentences", sid))
        score -= 20
    maxw = profile.get("headline_max_words", 20)
    if n > maxw:
        out.append(issue("warning", "HEADLINE_LONG", f"Headline has {n} words (budget {maxw}); cut to the claim", sid))
        score -= 10 + 2 * (n - maxw)
    if n < 5 and verb:
        out.append(issue("info", "HEADLINE_SHORT", "Very short headline; make sure it carries the so-what", sid))
        score -= 5
    joined = re.search(r"\b(and|y)\b", h, re.IGNORECASE)
    if joined:
        left, right = h[: joined.start()], h[joined.end():]
        if has_verb(left) and has_verb(right, within=4) and len(_tokens(right)) >= 4:
            out.append(issue("warning", "HEADLINE_TWO_MESSAGES", "Headline joins two claims; one slide = one message (split the slide or subordinate one claim)", sid))
            score -= 15
    vague = [t for t in toks if t in VAGUE]
    nums = numbers_in(h)
    if vague and not nums:
        out.append(issue("warning", "HEADLINE_VAGUE", f"Vague intensifier(s) {sorted(set(vague))} without a number; quantify", sid))
        score -= 10
    if h.endswith("?"):
        out.append(issue("info", "HEADLINE_QUESTION", "Question headlines defer the answer; prefer the answer", sid))
        score -= 5
    if n >= 4 and sum(1 for w in h.split() if w[:1].isupper()) / n > 0.7:
        out.append(issue("info", "HEADLINE_TITLE_CASE", "Title Case reads like a label; use sentence case for action titles", sid))
        score -= 5
    if slide is not None and _is_data_slide(slide) and not nums:
        out.append(issue("info", "HEADLINE_UNQUANTIFIED", "Data slide without a number in the headline; the strongest action titles quantify", sid))
        score -= 5
    if slide is not None and nums:
        unsupported = unsupported_numbers(h, slide, extra_values)
        for v, unit in unsupported:
            out.append(issue("warning", "HEADLINE_NUMBER_UNSUPPORTED", f"'{v:g}{unit}' in the headline is not found in / derivable from the evidence or exhibit data", sid))
            score -= 10
    return max(0, min(100, score)), out


def _is_data_slide(slide: dict) -> bool:
    from ..spec import VISUAL_TYPES, slide_exhibits

    return any(VISUAL_TYPES.get(e.get("type"), "") in ("chart", "table") for e in slide_exhibits(slide))


def _collect_values(slide: dict) -> tuple[list[float], list[str]]:
    from ..spec import slide_exhibits

    vals: list[float] = []
    texts: list[str] = []
    for ev in slide.get("evidence") or []:
        if isinstance(ev, dict):
            for k in ("value", "values"):
                v = ev.get(k)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
                elif isinstance(v, list):
                    vals += [float(x) for x in v if isinstance(x, (int, float))]
            texts.append(" ".join(str(ev.get(k, "")) for k in ("claim", "text", "value")))
        else:
            texts.append(str(ev))
    texts.append(slide.get("supporting_message", ""))
    for ex in slide_exhibits(slide):
        data = ex.get("data") or {}
        for s in data.get("series") or []:
            vals += [float(v) for v in s.get("values", []) if isinstance(v, (int, float))]
        for st in data.get("steps") or []:
            if isinstance(st, dict) and isinstance(st.get("value"), (int, float)):
                vals.append(float(st["value"]))
        for q in data.get("points") or []:
            if not isinstance(q, dict):
                continue
            for k in ("x", "y", "size"):
                if isinstance(q.get(k), (int, float)):
                    vals.append(float(q[k]))
        for r in ex.get("rows") or []:
            cells = (r.get("cells") or []) if isinstance(r, dict) else r  # gantt rows are dicts without cells
            vals += [float(c) for c in cells if isinstance(c, (int, float))]
        for c in data.get("columns") or []:
            if isinstance(c, dict):
                if isinstance(c.get("total"), (int, float)):
                    vals.append(float(c["total"]))
                vals += [float(v) for v in (c.get("parts") or {}).values() if isinstance(v, (int, float))]
        for st in data.get("stages") or []:
            if isinstance(st, dict) and isinstance(st.get("value"), (int, float)):
                vals.append(float(st["value"]))
        for k in ("items",):
            for it in data.get(k) or []:
                if isinstance(it, dict):
                    texts.append(" ".join(str(it.get(k, "")) for k in ("value", "title", "text", "delta", "label", "note")))
    for k in slide.get("kpis", {}).get("items", []) if isinstance(slide.get("kpis"), dict) else slide.get("kpis") or []:
        texts.append(str(k.get("value", "")) + " " + str(k.get("delta", "")))
    return vals, texts


def derivable(vals: list[float]) -> set[float]:
    """Numbers a reader could derive from the exhibit: values, sums, shares,
    differences, growth rates and CAGRs (bounded to keep it cheap)."""
    vals = [v for v in vals if isinstance(v, (int, float)) and not math.isnan(v)][:60]
    out = set(vals)
    total = sum(v for v in vals if v > 0)
    if total:
        out |= {v / total * 100 for v in vals}
    for a, b in itertools.combinations(vals[:40], 2):
        out.add(a + b)
        out.add(abs(a - b))
        if a:
            out.add((b / a - 1) * 100)
            out.add(b / a)
            out.add(b / a * 100)
        if b:
            out.add((a / b - 1) * 100)
            out.add(a / b)
            out.add(a / b * 100)
    for a, b in itertools.combinations(vals[:25], 2):
        for n in range(2, 11):
            if a > 0 and b > 0:
                out.add(((b / a) ** (1 / n) - 1) * 100)
                out.add(((a / b) ** (1 / n) - 1) * 100)
    # partial sums of the largest values (e.g. "top-3 account for 72%")
    srt = sorted((v for v in vals if v > 0), reverse=True)
    acc = 0.0
    for v in srt[:10]:
        acc += v
        out.add(acc)
        if total:
            out.add(acc / total * 100)
    return out


def unsupported_numbers(headline: str, slide: dict, extra_values: list[float] | None = None) -> list[tuple[float, str]]:
    vals, texts = _collect_values(slide)
    extra = list(extra_values or [])
    text_nums = {abs(v) for t in texts for v, _ in numbers_in(t)}
    cands = {abs(x) for x in derivable(vals)} | text_nums | {abs(x) for x in extra}
    cands |= {c / 1000 for c in cands} | {c * 1000 for c in cands}  # €M in data, €bn in headline
    bad = []
    for v, unit in numbers_in(headline):
        a = abs(v)
        if a == 0:
            continue
        ok = any(abs(a - c) <= max(0.51, 0.03 * a) if unit in ("%", "pp") else abs(a - c) <= max(0.05 * a, 0.51) for c in cands)
        # tolerate "~" / rounding to one significant figure for large values
        if not ok and a >= 10:
            ok = any(abs(a - c) / a <= 0.06 for c in cands)
        if not ok:
            bad.append((v, unit))
    return bad
