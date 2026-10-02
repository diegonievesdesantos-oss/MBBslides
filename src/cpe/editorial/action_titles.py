"""Action Title Engine (v3.1, spec §8-17, §41-46, §65-74).

The engine does not write prose. It owns the deterministic part of the headline:

    1. understand the proposition          (role, claim_type → the headline type it calls for)
    2. receive candidate wording           (`headline` + `headline_candidates` from the reasoning agent)
    3. prove the wording kept the meaning  (numbers, sign/direction, entity, scope, period, causal
                                            strength, recommendation/decision, confidence, language)
    4. rank and select                     (lexicographic: validity first, prettiness last)
    5. fail closed                         (HEADLINE_UNRESOLVED when no candidate is acceptable)

and one safe rewrite: when the proposition fully determines the sentence (subject + direction +
magnitude + period of a factual/trend claim) it can state it ("Revenue declined 8% in 2026"), and the
result goes through the same checks as any candidate.

`core/headline.lint_headline` is reused as the first layer (topic, two messages, vagueness, length,
unsupported numbers); its codes keep their meaning and the planner still runs it independently.
"""
from __future__ import annotations

import re

from ..core.headline import GENERIC_NOUNS, lint_headline, numbers_in
from . import proposition as P
from .signatures import analyze, has_finite_verb, language, mixed_language

ACTION_KINDS = {"content", "exec_summary", "statement"}  # must carry an action title (spec §41)
EXEMPT_KINDS = {"cover", "divider", "agenda", "appendix_divider", "closing"}  # title-style labels allowed

HARD = {"HEADLINE_MISSING", "HEADLINE_PLACEHOLDER", "HEADLINE_TOPIC", "HEADLINE_PROPOSITION_MISMATCH", "HEADLINE_NUMBER_UNSUPPORTED",
        "HEADLINE_CAUSALITY_UNSUPPORTED", "HEADLINE_COMPARISON_UNSUPPORTED", "HEADLINE_DIRECTION_MISMATCH",
        "HEADLINE_TIMEFRAME_MISMATCH", "HEADLINE_TWO_GOVERNING_MESSAGES", "HEADLINE_UNRESOLVED", "HEADLINE_LANGUAGE_MISMATCH"}
FIDELITY = {"HEADLINE_PROPOSITION_MISMATCH", "HEADLINE_CAUSALITY_UNSUPPORTED", "HEADLINE_COMPARISON_UNSUPPORTED",
            "HEADLINE_DIRECTION_MISMATCH", "HEADLINE_TIMEFRAME_MISMATCH", "HEADLINE_LANGUAGE_MISMATCH"}
LINT_MAP = {"HEADLINE_TWO_MESSAGES": "HEADLINE_TWO_GOVERNING_MESSAGES"}

TOPIC_LABELS = {
    "market overview", "revenue evolution", "financial performance", "cost analysis", "customer segmentation", "key findings",
    "strategic priorities", "next steps", "current situation", "competitive landscape", "executive summary", "overview",
    "background", "context", "introduction", "agenda", "summary", "recommendations", "conclusions", "appendix", "methodology",
    "implementation roadmap", "roadmap", "market analysis", "situación actual", "resumen ejecutivo", "próximos pasos",
    "panorama competitivo", "análisis de costes", "evolución de ingresos", "evolución de ventas", "conclusiones",
    "recomendaciones", "contexto", "visión general", "hoja de ruta", "prioridades estratégicas", "segmentación de clientes",
}
INSTRUCTION = {"explain", "show", "describe", "present", "analyse", "analyze", "outline", "illustrate", "summarise", "summarize",
               "discuss", "explore", "detail", "depict", "overview", "mostrar", "explicar", "describir", "presentar", "analizar",
               "resumir", "exponer", "detallar", "ilustrar", "muestra", "explica", "describe", "presenta", "analiza"}
# causal language (spec §43): tier C needs a causal/driver claim; tier E (attribution) also a composition/impact one
CAUSAL_C = re.compile(r"\b(?:caus(?:e|es|ed|ing)|caused by|driv(?:e|es|ing|en)|drove|driven by|results? (?:from|in)|resulted (?:from|in)|"
                      r"due to|because|owing to|leads? to|led to|trigger(?:s|ed)?|stems? from|fuel(?:s|ed|led)?|as a result of|"
                      r"causa(?:n|do|da|ron)?|caus[oó]|provoca(?:n|do|da|ron)?|provoc[oó]|se debe(?:n)? a|debido a|deb(?:e|en|i[oó]) a|"
                      r"impuls(?:a|an|ado|ada|aron|ó)|porque|a causa del?|como consecuencia del?|conduce(?:n)? al?|origina(?:n|do)?|"
                      r"por culpa del?|gracias al?|debido al|se debe(?:n)? al|thanks to)\b", re.I)
CAUSAL_E = re.compile(r"\b(?:explain(?:s|ed|ing)?|accounts? for|accounted for|attributable to|attributed to|responsible for|"
                      r"explica(?:n|do|da|ron)?|explic[oó]|se explica(?:n)? por|atribuible(?:s)? a|responsable(?:s)? de)\b", re.I)
CAUSAL_OK_C = {"causal", "driver"}
CAUSAL_OK_E = {"causal", "driver", "composition", "impact"}
SUPERLATIVE = re.compile(r"\b(?:best|worst|highest|lowest|largest|smallest|biggest|leading|leader|top|most \w+|least \w+|"
                         r"outperform(?:s|ed|ing)?|lag(?:s|ged|ging)?|trail(?:s|ed|ing)?|beat(?:s)?|ahead of|behind|"
                         r"\w+er than|more \w+ than|less \w+ than|"
                         r"(?:el|la|los|las) (?:mayor(?:es)?|menor(?:es)?|mejor(?:es)?|peor(?:es)?|m[aá]s \w+|menos \w+)|"
                         r"l[ií]der(?:es)?|lidera(?:n)?|supera(?:n)?|por encima de|por debajo de|m[aá]s \w+ que|menos \w+ que|"
                         r"mayor(?:es)? que|menor(?:es)? que|mejor(?:es)? que|peor(?:es)? que)\b", re.I)
COMPARISON_OK = {"comparison", "driver", "composition", "status"}  # status compares against plan
POS_CMP = re.compile(r"\b(?:more|higher|greater|larger|bigger|above|over|exceed(?:s|ed)?|outperform(?:s|ed)?|beat(?:s)?|ahead of|leads?|"
                     r"m[aá]s|mayor(?:es)?|supera(?:n)?|por encima de|lidera(?:n)?)\b", re.I)
NEG_CMP = re.compile(r"\b(?:less|lower|fewer|smaller|below|under|lag(?:s|ged)?|trail(?:s|ed)?|behind|"
                     r"menos|menor(?:es)?|por debajo de|queda(?:n)? por detr[aá]s)\b", re.I)
MAX_SUP = re.compile(r"\b(?:highest|largest|biggest|the most(?! of)|top|leading|leader|el mayor|la mayor|los mayores|las mayores|"
                     r"m[aá]s alt[oa]s?|l[ií]der|lidera)\b", re.I)
MIN_SUP = re.compile(r"\b(?:lowest|smallest|least|el menor|la menor|los menores|las menores|m[aá]s baj[oa]s?)\b", re.I)
RECO = re.compile(r"\b(?:should|ought to|we recommend|recommend(?:s|ed)?|it is time to|"
                  r"deber[ií]a(?:n)?|recomendamos|recomienda(?:n)?|proponemos|conviene|hay que|habr[ií]a que|es preciso)\b", re.I)
MUST = re.compile(r"\b(?:must|needs? to|has to|have to|(?<!se )debe(?:n)?(?! a\b)|tiene(?:n)? que|es necesario|necesita(?:n)?)\b", re.I)
DECISION = re.compile(r"\b(?:approv(?:e|es|ed|ing|al)|decid(?:e|es|ed|ing)|decision|sign[- ]off|green[- ]light|"
                      r"authori[sz](?:e|es|ed|ing|ation)|ratif(?:y|ies|ied)|apr(?:ue|o)b(?:a|ar|ación|acion|ado|ada|amos|emos|e|en)|"
                      r"decidir|decisi[oó]n|autoriz(?:ar|aci[oó]n)|ratificar)\b", re.I)
DECISION_DONE = re.compile(r"\b(?:ha(?:s|ve)? (?:been )?(?:approved|decided|signed off|authori[sz]ed)|was (?:approved|decided)|approved|decided|"
                           r"se ha decidido|se decidi[oó]|ha(?:n)? aprobado|aprob[oó]|se aprob[oó]|est[aá] aprobad[oa]|ha(?:n)? decidido|decidi[oó])\b", re.I)
RISK = re.compile(r"\b(?:at risk|risks?|threaten(?:s|ed)?|jeopardi[sz]e[sd]?|endanger(?:s|ed)?|en riesgo|riesgo|amenaza(?:n)?|pone(?:n)? en peligro)\b", re.I)
STATUS = re.compile(r"\b(?:on track|off track|behind (?:plan|schedule)|ahead of (?:plan|schedule)|on schedule|delayed|en plazo|"
                    r"seg[uú]n lo previsto|retrasad[oa]s?|en l[ií]nea con el plan|por delante del plan)\b", re.I)
IMPLICATION = re.compile(r"\b(?:will|would|unless|without|implies|means|therefore|so that|si no|sin|a menos que|implica|supone que|"
                         r"por tanto|har[aá]|ser[aá]|quedar[aá])\b", re.I)
UNIVERSAL = re.compile(r"\b(?:all|every|entire|whole|across the (?:group|board|business|company)|group-wide|company-wide|network-wide|"
                       r"todos|todas|toda la|todo el|cada|en todas|en todos|el conjunto)\b", re.I)
HEDGE = re.compile(r"\b(?:may|might|could|likely|probably|possibly|suggests?|appears?|seems?|indicates?|preliminary|estimated|"
                   r"early signs|podr[ií]a(?:n)?|probablemente|posiblemente|parece(?:n)?|sugiere(?:n)?|apunta(?:n)?|indicios|"
                   r"estimad[oa]s?|previsiblemente|puede(?:n)?)\b", re.I)
CERTAIN = re.compile(r"\b(?:will|certainly|clearly|definitely|proves?|proven|guarantee[sd]?|undoubtedly|always|"
                     r"sin duda|demuestra(?:n)?|garantiza(?:n)?|seguro|siempre|claramente)\b", re.I)
APPROX = r"(?:~|≈|about|around|approximately|approx\.?|roughly|nearly|almost|c\.|circa|some|over|more than|less than|under|up to|at least|" \
         r"aproximadamente|alrededor de|cerca de|casi|en torno a|unos|unas|m[aá]s de|menos de|hasta|al menos|aprox\.?)"
NEUTRAL_CHANGE = re.compile(r"\b(?:chang(?:ed|es)|moved?|moves|shift(?:ed|s)|var(?:ied|ies)|evolv(?:ed|es)|cambi[oó]|cambia(?:n)?|"
                            r"vari[oó]|var[ií]a(?:n)?|evolucion[oó]|evoluciona(?:n)?|se movi[oó]|se mueve)\b", re.I)
DIR_UP = {"grew", "grow", "grows", "growing", "growth", "rose", "rise", "rises", "risen", "rising", "increased", "increase", "increases",
          "increasing", "up", "gained", "gains", "expanded", "expands", "expand", "doubled", "doubles", "tripled", "triples",
          "improved", "improves", "improve", "improvement", "accelerated", "accelerates", "recovered", "recovers", "surged",
          "jumped", "climbed", "widened", "widens", "rebounded", "crece", "crecen", "creció", "crecieron", "crecimiento",
          "sube", "suben", "subió", "subieron", "subida", "aumenta", "aumentan", "aumentó", "aumentaron", "aumento", "mejora",
          "mejoran", "mejoró", "mejoraron", "duplica", "duplicó", "dobla", "triplica", "repunta", "repuntó", "acelera", "aceleró",
          "amplía", "amplió", "alza", "recupera", "recuperó", "gana", "ganan", "ganó", "incrementa", "incrementó", "incremento"}
DIR_DOWN = {"fell", "fall", "falls", "falling", "fallen", "declined", "decline", "declines", "declining", "decreased", "decrease",
            "decreases", "dropped", "drop", "drops", "down", "lost", "loses", "shrank", "shrinks", "shrink", "contracted",
            "contraction", "erosion", "eroded", "erodes", "halved", "halves", "deteriorated", "worsened", "worsens", "slowed",
            "slows", "slowdown", "loss", "losses", "reduced", "reduction", "narrowed", "narrows", "weakened", "slipped", "plunged", "cut", "cuts",
            "cae", "caen", "cayó", "cayeron", "caída", "baja", "bajan", "bajó", "bajaron", "bajada", "disminuye", "disminuyen",
            "disminuyó", "disminuyeron", "disminución", "pierde", "pierden", "perdió", "perdieron", "pérdida", "empeora",
            "empeoró", "retrocede", "retrocedió", "retroceso", "reduce", "reducen", "redujo", "reducción", "desciende",
            "descendió", "descenso", "contrae", "contrajo", "contracción", "erosión", "erosiona", "frena", "frenó", "desacelera",
            "desaceleró", "recorta", "recortó", "merma", "mermó"}
NEGATION = {"not", "no", "never", "nunca", "sin", "without", "didn't", "did", "hardly"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
          "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
          "monday", "tuesday", "wednesday", "thursday", "friday", "q1", "q2", "q3", "q4", "h1", "h2", "fy"}
BUZZ = re.compile(r"\b(?:unlock(?:ing)? (?:sustainable )?value|sustainable value|strategic transformation|differentiated value proposition|"
                  r"foundations? for (?:long-term )?success|best[- ]in[- ]class|world[- ]class|holistic|synerg(?:y|ies)|"
                  r"leverag(?:e|ing) (?:our|the) (?:strengths|capabilities)|next level|game[- ]changer|"
                  r"transformaci[oó]n estrat[eé]gica|valor sostenible|propuesta de valor diferencial|bases para el [eé]xito)\b", re.I)
WEAK_VERB = re.compile(r"^(?:the |this |el |la |este |esta )?(?:\w+ )?(?:chart|slide|page|table|exhibit|gr[aá]fico|p[aá]gina|tabla)?\s*"
                       r"(?:shows?|showed|illustrates?|depicts?|presents?|highlights?|displays?|summari[sz]es?|muestra(?:n)?|"
                       r"presenta(?:n)?|ilustra(?:n)?|resume(?:n)?|recoge(?:n)?)\b", re.I)
REDUNDANT = re.compile(r"\b(?:this slide|this page|the chart|the following|as shown|see below|esta p[aá]gina|esta diapositiva|"
                       r"el gr[aá]fico|a continuaci[oó]n|la siguiente|como se muestra)\b", re.I)

YEAR_RE = re.compile(r"(?<![\d.,])(?:19|20)\d\d(?![\d.,])")
QUARTER_RE = re.compile(r"\b(?:Q|T)([1-4])\b|\b([1-4])T\b|\bH([12])\b|\bS([12])\b", re.I)


def title_field(slide: dict) -> str:
    """The field that carries the action title: a statement slide's message is its text."""
    return "text" if slide.get("kind") == "statement" and slide.get("text") else "headline"


def headline_type(prop: dict) -> str:
    """Taxonomy of spec §12 from the proposition (what the headline must be)."""
    ct, role = prop.get("claim_type"), prop.get("role")
    if role == "decision" or ct == "decision":
        return "decision"
    if role == "recommendation" or ct == "recommendation":
        return "recommendation"
    if ct == "causal":
        return "causal"
    if ct in ("driver", "composition") or role == "driver":
        return "driver"
    if ct == "comparison" or role == "comparison":
        return "comparative"
    if ct in ("risk", "constraint") or role == "risk":
        return "risk"
    if ct == "status" or role == "status":
        return "status"
    if role in ("implication", "impact") or ct in ("impact", "opportunity"):
        return "implication"
    return "factual"


def observed_type(text: str) -> str:
    a = analyze(text)
    if DECISION.search(text):
        return "decision"
    if a["family"] == "action" or RECO.search(text):
        return "recommendation"
    if STATUS.search(text):
        return "status"
    if RISK.search(text):
        return "risk"
    if CAUSAL_C.search(text):
        return "causal"
    if CAUSAL_E.search(text) or a["signature"] == "DRIVER_EXPLAINS_OUTCOME":
        return "driver"
    if SUPERLATIVE.search(text):
        return "comparative"
    if IMPLICATION.search(text) or a["signature"] == "CONDITION_IMPLIES_CONSEQUENCE":
        return "implication"
    return "factual"


COMPATIBLE_TYPES = {
    "factual": {"factual", "driver", "comparative", "status"}, "comparative": {"comparative", "factual", "driver"},
    "driver": {"driver", "factual", "comparative", "causal"}, "causal": {"causal", "driver", "factual"},
    "implication": {"implication", "factual", "risk", "driver", "comparative"}, "risk": {"risk", "implication", "factual"},
    "status": {"status", "factual", "risk"}, "recommendation": {"recommendation", "implication"},
    "decision": {"decision", "recommendation", "implication"},
}


# ── slide data the checks read ────────────────────────────────────────────────

def slide_series(slide: dict) -> dict[str, float]:
    """label → value of the first chart series (categories) and of single-series evidence."""
    from ..spec import slide_exhibits

    out: dict[str, float] = {}
    for ex in slide_exhibits(slide):
        d = ex.get("data") or {}
        cats = [str(c) for c in d.get("categories") or []]
        ser = d.get("series") or []
        if cats and ser and isinstance(ser[0], dict):
            vals = ser[0].get("values") or []
            for c, v in zip(cats, vals):
                if isinstance(v, (int, float)):
                    out.setdefault(c, float(v))
        for st in d.get("steps") or []:
            if isinstance(st, dict) and isinstance(st.get("value"), (int, float)) and st.get("label"):
                out.setdefault(str(st["label"]), float(st["value"]))
        for r in ex.get("rows") or []:
            cells = r.get("cells") if isinstance(r, dict) else r
            if isinstance(cells, list) and len(cells) >= 2 and isinstance(cells[0], str):
                num = next((c for c in cells[1:] if isinstance(c, (int, float))), None)
                if num is not None:
                    out.setdefault(cells[0], float(num))
    return out


def slide_labels(slide: dict) -> set[str]:
    """Entity labels the slide shows: categories, series, table first column, step labels."""
    from ..spec import slide_exhibits

    labs: set[str] = set(slide_series(slide))
    for ex in slide_exhibits(slide):
        d = ex.get("data") or {}
        for s in d.get("series") or []:
            if isinstance(s, dict) and s.get("name"):
                labs.add(str(s["name"]))
        labs |= {str(c) for c in d.get("categories") or []}
        for r in ex.get("rows") or []:
            cells = r.get("cells") if isinstance(r, dict) else r
            if isinstance(cells, list) and cells and isinstance(cells[0], str):
                labs.add(cells[0])
            elif isinstance(r, dict) and r.get("label"):
                labs.add(str(r["label"]))
        for p in d.get("points") or []:
            if isinstance(p, dict) and p.get("label"):
                labs.add(str(p["label"]))
    return {lab for lab in labs if len(lab) >= 2 and re.search(r"[A-Za-zÀ-ÿ]", lab) and not YEAR_RE.fullmatch(lab.strip())}


def _mentions(text: str, label: str) -> bool:
    return bool(re.search(rf"(?<![\w]){re.escape(label.lower())}(?![\w])", text.lower()))


def slide_text(slide: dict) -> str:
    parts = [slide.get("purpose"), slide.get("supporting_message"), slide.get("source")]
    for e in slide.get("evidence") or []:
        parts.append(" ".join(str(e.get(k, "")) for k in ("claim", "text", "label", "value")) if isinstance(e, dict) else str(e))
    parts += sorted(slide_labels(slide))
    from ..spec import slide_exhibits

    for ex in slide_exhibits(slide):
        parts += [str(ex.get(k) or "") for k in ("title", "unit")]
        d = ex.get("data") or {}
        for it in d.get("items") or []:
            parts.append(" ".join(str(it.get(k, "")) for k in ("title", "text", "label")) if isinstance(it, dict) else str(it))
        for st in d.get("steps") or []:
            parts.append(" ".join(str(st.get(k, "")) for k in ("label", "title", "text")) if isinstance(st, dict) else str(st))
        for c in ex.get("columns") or []:
            parts.append(str(c.get("label", "")) if isinstance(c, dict) else str(c))
    com = slide.get("commentary") or {}
    parts += [str(x) for x in (com.get("points") or [])] if isinstance(com, dict) else []
    return " ".join(str(p) for p in parts if p)


def periods(text: str) -> set[str]:
    t = text or ""
    out = set(YEAR_RE.findall(t))
    for m in re.finditer(r"\b(?:FY|AF)\s?'?(\d{2})\b", t, re.I):
        out.add("20" + m.group(1))
    for m in re.finditer(r"(?<![\d])((?:19|20)\d\d)\s*[-–/]\s*(\d{2,4})(?![\d])", t):
        a, b = int(m.group(1)), m.group(2)
        bb = int(b) if len(b) == 4 else int(m.group(1)[:2] + b)
        if a < bb <= a + 30:
            out |= {str(y) for y in range(a, bb + 1)}
    for m in QUARTER_RE.finditer(t):
        q = next(g for g in m.groups() if g)
        kind = "Q" if (m.group(1) or m.group(2)) else "H"
        out.add(f"{kind}{q}")
    return out


def _dir_tokens(text: str) -> set[str]:
    toks = re.findall(r"[a-záéíóúñü]+", (text or "").lower())
    found = set()
    for i, t in enumerate(toks):
        d = "up" if t in DIR_UP else "down" if t in DIR_DOWN else None
        if not d:
            continue
        if any(x in NEGATION for x in toks[max(0, i - 2):i]):
            d = "down" if d == "up" else "up"
        found.add(d)
    return found


def _approx_numbers(text: str) -> list[float]:
    out = []
    for m in re.finditer(rf"(?:^|(?<=[\s(]))(?:{APPROX})\s*[€$£]?\s*([-−]?\d[\d.,]*)", text or "", re.I):
        v = numbers_in(m.group(1))
        if v:
            out.append(abs(v[0][0]))
    return out


def _stems(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "in", "on", "to", "and", "or", "for", "by", "with", "is", "are", "was", "be", "as", "at", "from",
            "that", "this", "its", "our", "we", "will", "can", "de", "la", "el", "en", "y", "los", "las", "del", "que", "un", "una",
            "por", "con", "para", "se", "es", "most", "more", "than", "más", "mayor", "parte", "now", "all"}
    return {w[:5] for w in re.findall(r"[a-záéíóúñü]+", (text or "").lower()) if w not in stop and len(w) > 2}


# ── evaluation of one candidate ───────────────────────────────────────────────

def evaluate(text: str, slide: dict, prop: dict | None, ctx: dict) -> dict:
    """All checks on one candidate. Returns issues as (code, 'hard'|'soft'|'info', message)."""
    issues: list[tuple[str, str, str]] = []
    h = (text or "").strip()
    profile = ctx.get("profile") or {}
    prop = prop or {}
    inferred = bool(prop.get("_inferred"))
    if not h:
        return _result(h, [("HEADLINE_MISSING", "hard", "No headline: a substantive slide must state its takeaway")], prop, ctx)
    extra = ctx.get("deck_values") if slide.get("kind") in ("exec_summary", "statement") else None
    _, lint = lint_headline(h, slide if slide.get("kind") != "statement" else {**slide, "visual": None, "exhibits": []}, profile, extra)
    for i in lint:
        code = LINT_MAP.get(i["code"], i["code"])
        cls = "hard" if code in HARD else "soft" if i["level"] in ("warning", "error") else "info"
        if code == "HEADLINE_TITLE_CASE" and ctx.get("capitalization") == "title":
            continue
        issues.append((code, cls, i["message"]))
    lang = ctx.get("lang")
    if analyze(h, lang)["family"] == "action":
        issues = [(c, cls, m) for c, cls, m in issues if c != "HEADLINE_NO_VERB"]
    if any(c == "HEADLINE_TOPIC" for c, _, _ in issues) and has_finite_verb(h, lang) and h.lower().strip(" .") not in TOPIC_LABELS:
        issues = [(c, "info" if c == "HEADLINE_TOPIC" else cls, m) for c, cls, m in issues]
        issues = [(("HEADLINE_NO_VERB_LEXICON" if c == "HEADLINE_TOPIC" else c), cls, m) for c, cls, m in issues]
    codes = {c for c, cls, _ in issues if cls == "hard"}
    low = h.lower().strip(" .")
    first = re.findall(r"[a-záéíóúñü]+", low)[:1]
    purpose = str(slide.get("purpose") or "").strip().lower().strip(" .")
    if "HEADLINE_TOPIC" not in codes and "HEADLINE_PLACEHOLDER" not in codes:
        nwords = len(re.findall(r"[\wÀ-ÿ%€]+", h))
        generic = any(t in GENERIC_NOUNS for t in re.findall(r"[a-záéíóúñü]+", low))
        if low in TOPIC_LABELS or (not has_finite_verb(h, lang) and analyze(h, lang)["family"] in ("noun", "gerund") and (nwords <= 6 or generic)):
            issues.append(("HEADLINE_TOPIC", "hard", f"'{h}' names a topic; state the conclusion the slide proves (subject + verb + so-what)"))
        elif first and first[0] in INSTRUCTION or (purpose and low == purpose):
            issues.append(("HEADLINE_TOPIC", "hard", f"'{h}' is the slide's purpose (an instruction to the author), not its conclusion (spec §103)"))
    if lang and not mixed_language(h):
        hl = language(h)
        if hl and hl != lang and _lang_margin(h) >= 2:
            issues.append(("HEADLINE_LANGUAGE_MISMATCH", "hard", f"Headline is in '{hl}' but the deck is in '{lang}' (spec §67)"))
    if mixed_language(h):
        issues.append(("HEADLINE_LANGUAGE_MISMATCH", "hard", "Headline mixes Spanish and English (spec §67)"))
    if prop and not inferred:
        issues += _fidelity(h, slide, prop, ctx)
    # soft signals (spec §15)
    if WEAK_VERB.search(h):
        issues.append(("HEADLINE_WEAK_VERB", "soft", "The verb describes the slide ('shows', 'presents'), not the finding"))
    if REDUNDANT.search(h):
        issues.append(("HEADLINE_REDUNDANT", "soft", "The headline refers to the slide itself; state the finding"))
    if BUZZ.search(h) and not numbers_in(h):
        issues.append(("HEADLINE_LOW_INFORMATION", "soft", "Consulting-sounding phrase without a supported, specific claim (spec §66)"))
    elif len(_stems(h)) < 3 and "HEADLINE_TOPIC" not in {c for c, _, _ in issues}:
        issues.append(("HEADLINE_LOW_INFORMATION", "info", "Few content words: check the headline carries the finding"))
    if prop.get("implication") and not inferred and not (_stems(h) & _stems(prop["implication"])) and prop.get("role") in ("diagnosis", "insight", "driver"):
        issues.append(("HEADLINE_SO_WHAT_WEAK", "info", f"The proposition's implication ('{prop['implication']}') is not in the headline; add it if it fits"))
    exp, obs = headline_type(prop), observed_type(h)
    if prop and not inferred and obs not in COMPATIBLE_TYPES.get(exp, {exp}):
        issues.append(("HEADLINE_TYPE_MISMATCH", "soft", f"The proposition calls for a {exp} headline; this reads as {obs}"))
    return _result(h, issues, prop, ctx, exp, obs)


def _lang_margin(text: str) -> int:
    from .signatures import EN_FUNC, ES_FUNC

    toks = re.findall(r"[a-záéíóúñü]+", (text or "").lower())
    return abs(sum(t in ES_FUNC for t in toks) - sum(t in EN_FUNC for t in toks))


def _fidelity(h: str, slide: dict, prop: dict, ctx: dict) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    ptext = P.text_of(prop)
    ct, role = prop.get("claim_type"), prop.get("role")
    a = analyze(h, ctx.get("lang"))
    for raw, v in _strictly_unsupported(h, slide, ctx.get("deck_values") if slide.get("kind") in ("exec_summary", "statement") else None):
        out.append(("HEADLINE_NUMBER_UNSUPPORTED", "hard", f"'{raw}' is not in the evidence nor derivable from it at the precision written"))
    # recommendation / decision protection (spec §44, §91)
    reco_form = a["family"] == "action" or bool(RECO.search(h))
    if reco_form and role not in ("recommendation", "decision", "implementation") and ct not in ("recommendation", "decision") and not prop.get("recommended_action"):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"The headline recommends an action but the proposition is a {role or ct}: a finding is not a recommendation (spec §44)"))
    if DECISION.search(h) and role != "decision" and ct != "decision" and not prop.get("decision") and not DECISION.search(ptext):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "The headline asks for or states a decision the proposition does not contain (recommendation ≠ decision)"))
    if DECISION_DONE.search(h) and not DECISION_DONE.search(ptext) and role != "decision" and ct != "decision":
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "The headline states a decision as taken; the proposition only recommends it"))
    if MUST.search(h) and not reco_form and role not in ("recommendation", "decision", "implication", "risk", "implementation") \
            and ct not in ("constraint", "risk", "recommendation", "decision") and not MUST.search(ptext):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "'must / needs to' turns a finding into an obligation the proposition does not state"))
    for part in re.split(r"[;,—–]\s*(?:separately|in addition|additionally|also|unrelated(?:ly)?|por otro lado|adem[aá]s|aparte|por separado)\s*,?\s*", h, flags=re.I)[1:2]:
        left = h[: h.find(part)] if part else ""
        if part and len(part.split()) >= 4 and has_finite_verb(part, ctx.get("lang")) and has_finite_verb(left, ctx.get("lang")):
            out.append(("HEADLINE_TWO_GOVERNING_MESSAGES", "hard", "Two independent claims joined in one title: one slide, one message"))
    # causal strength (spec §43)
    if CAUSAL_C.search(h) and ct not in CAUSAL_OK_C and not CAUSAL_C.search(ptext):
        out.append(("HEADLINE_CAUSALITY_UNSUPPORTED", "hard", f"Causal wording ('{CAUSAL_C.search(h).group(0)}') on a {ct or 'non-causal'} claim: use 'is associated with / coincides with / is concentrated in'"))
    elif CAUSAL_E.search(h) and ct not in CAUSAL_OK_E and not (CAUSAL_E.search(ptext) or CAUSAL_C.search(ptext)):
        out.append(("HEADLINE_CAUSALITY_UNSUPPORTED", "hard", f"'{CAUSAL_E.search(h).group(0)}' attributes the outcome; the proposition is a {ct or 'non-driver'} claim"))
    # comparison / superlative (spec §45)
    sup = SUPERLATIVE.search(re.sub(r"\b(?:behind|ahead of|lag\w*|trail\w*)\s+(?:the\s+)?(?:\w+\s+)?(?:plan|schedule|target|budget|forecast)\b", "", h, flags=re.I))
    if sup and not SUPERLATIVE.search(ptext):
        universe = slide_series(slide)
        n_items = max(len(universe), len(slide_labels(slide)), _evidence_items(slide))
        if ct not in COMPARISON_OK and not prop.get("comparison"):
            out.append(("HEADLINE_COMPARISON_UNSUPPORTED", "hard", f"'{sup.group(0)}' compares, but the proposition is not a comparison"))
        elif n_items < 2:
            out.append(("HEADLINE_COMPARISON_UNSUPPORTED", "hard", f"'{sup.group(0)}' needs the comparison universe on the slide; it shows fewer than two items"))
    out += _order_checks(h, slide, prop)
    # direction (spec §74)
    pdir = P.direction_of(prop.get("direction"))
    if pdir in ("up", "down") and role not in ("recommendation", "decision") and ct not in ("recommendation", "decision"):
        found = _dir_tokens(h)
        opp = "down" if pdir == "up" else "up"
        if opp in found and pdir not in found:
            out.append(("HEADLINE_DIRECTION_MISMATCH", "hard", f"The proposition says {prop.get('direction')}; the headline says the opposite"))
        elif not found and NEUTRAL_CHANGE.search(h) and ct in ("trend", "fact", "impact", "status", None):
            out.append(("HEADLINE_DIRECTION_MISMATCH", "hard", f"The headline states the change but drops its direction ({prop.get('direction')})"))
    # magnitude, approximation
    for m_val, m_unit in numbers_in(str(prop.get("magnitude") or "")):
        same = [v for v, u in numbers_in(h) if u == m_unit]
        if same and not any(abs(abs(v) - abs(m_val)) <= max(0.051 * abs(m_val), 0.051) for v in same):
            out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"The headline's figure differs from the proposition's magnitude ({prop.get('magnitude')})"))
    for v in _approx_numbers(" ".join(str(prop.get(k) or "") for k in ("statement", "magnitude"))):
        for m in re.finditer(r"[-−+]?[\d][\d.,]*", h):
            got = numbers_in(m.group(0))
            if got and abs(abs(got[0][0]) - v) <= 0.1 * v and not re.search(rf"(?:^|[\s(])(?:{APPROX})\s*[€$£]?\s*$", h[max(0, m.start() - 22):m.start()], re.I):
                out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"The proposition gives ~{v:g} as an approximation; the headline states it as exact"))
                break
    # period (spec §74)
    hp = periods(h)
    pp = periods(" ".join(str(prop.get(k) or "") for k in ("timeframe", "statement", "comparison", "scope", "magnitude")))
    ev_p = periods(slide_text(slide))
    if hp:
        extra = hp - pp
        if pp and extra and not (hp & pp and extra <= ev_p):
            out.append(("HEADLINE_TIMEFRAME_MISMATCH", "hard", f"Headline period {sorted(hp)} ≠ proposition period {sorted(pp)}"))
        elif not pp and extra - ev_p:
            out.append(("HEADLINE_TIMEFRAME_MISMATCH", "hard", f"Headline period {sorted(extra - ev_p)} appears nowhere in the proposition or the evidence"))
    # scope (spec §74)
    u = UNIVERSAL.search(h)
    if u and _enumerated_universe(h, u, ptext):
        u = None
    if u and not UNIVERSAL.search(ptext):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"'{u.group(0)}' widens the scope beyond the proposition ({prop.get('scope') or 'not universal'})"))
    scope = str(prop.get("scope") or "")
    if scope:
        st_ = [w for w in re.findall(r"[a-záéíóúñü]{3,}", scope.lower()) if not re.fullmatch(NUMWORD, w) and w not in ("the", "los", "las", "del", "and")]
        present = [w for w in st_ if w[:5] in _stems(h)]
        missing = [w for w in st_ if w[:5] not in _stems(h)]
        if present and missing:
            out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"The proposition's scope is '{scope}'; the headline drops '{' '.join(missing)}' and so widens it"))
    # confidence (spec §74)
    conf = prop.get("confidence")
    if conf == "low" and not HEDGE.search(h):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "The proposition's confidence is low; the headline states it as established (hedge it: 'may', 'suggests', 'podría')"))
    elif conf == "medium" and CERTAIN.search(h) and not CERTAIN.search(ptext):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"'{CERTAIN.search(h).group(0)}' states with certainty a medium-confidence proposition"))
    # entity (spec §74): the proposition's entities replaced by others of the slide, or invented ones
    labels = slide_labels(slide) | _comparison_labels(prop)
    p_ents = {lab for lab in labels if _mentions(ptext, lab)}
    h_ents = {lab for lab in labels if _mentions(h, lab)}
    if p_ents and h_ents and not (p_ents & h_ents) and not any(_mentions(lab, x) or _mentions(x, lab) for lab in h_ents for x in p_ents):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"Entity drift: the proposition is about {sorted(p_ents)}, the headline about {sorted(h_ents)}"))
    hs, ps, es_ = _stems(h), _stems(str(prop.get("statement") or "")), _stems(slide_text(slide))
    new_h = {w for w in hs - _stems(ptext) if w in es_ and not w.isdigit()}
    lost_p = {w for w in ps - hs if w in es_ and not w.isdigit()}
    if new_h and lost_p and _sibling_terms(new_h, lost_p, slide_text(slide)):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"Entity drift: the headline names {sorted(new_h)} where the proposition names {sorted(lost_p)}"))
    if _swapped(str(prop.get("statement") or ""), h):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "The headline swaps the two sides of the proposition's comparison"))
    known = (ptext + " " + slide_text(slide) + " " + ctx.get("deck_text", "")).lower()
    for w in re.findall(r"(?<=\s)([A-ZÁÉÍÓÚÑ][a-záéíóúñü]{2,}(?:[- ][A-ZÁÉÍÓÚÑ][a-záéíóúñü]+)*)", h):
        if w.lower() in MONTHS or w.lower() in known or w.split()[0].lower() in known:
            continue
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"'{w}' appears neither in the proposition nor in the slide's evidence (invented entity?)"))
    if not (_stems(h) & _stems(ptext)):
        out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", "The headline shares no content word with the proposition: it says something else"))
    elif prop.get("subject") and not (_stems(h) & _stems(prop["subject"])):
        out.append(("HEADLINE_SUBJECT_IMPLICIT", "soft", f"The proposition's subject ('{prop['subject']}') is not named in the headline"))
    return out


NUMWORD = r"(?:(?<![\d.,])\d{1,2}(?![\d.,%])|two|three|four|five|six|seven|eight|nine|ten|twelve|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce)"


def _enumerated_universe(h: str, u, ptext: str) -> bool:
    """'all five regions', or 'todas las regiones' when the proposition is about 'las cinco regiones': the
    universal word names the proposition's own enumerated set, it does not widen it."""
    after = h[u.end():u.end() + 40]
    if re.match(rf"\s+(?:the\s+|las\s+|los\s+)?{NUMWORD}\b", after, re.I):
        return True
    m = re.match(r"\s+(?:the\s+|las\s+|los\s+|our\s+)?([A-Za-zÁÉÍÓÚáéíóúñ]{4,})", after)
    if not m:
        return False
    stem = m.group(1).lower()[:5]
    return bool(re.search(rf"\b{NUMWORD}\s+(?:\w+\s+)?{re.escape(stem)}\w*", ptext, re.I))


def _sibling_terms(new: set[str], lost: set[str], evidence: str) -> bool:
    """Two terms are siblings when the evidence lists both as labelled items ('North 9.4%, Central 7.2%, … South 5.1%';
    'enterprise €46k, SMB €20k'): one replacing the other is an entity substitution, not a paraphrase."""
    labels = set()
    for m in re.finditer(r"(?:^|[,;:(]|\band\b|\by\b)\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{1,20}(?:\s[A-Za-zÀ-ÿ\-]{2,20})?)\s*[:=]?\s*[-−+]?[€$£]?\d", evidence):
        labels |= _stems(m.group(1))
    return bool(new & labels) and bool(lost & labels)


CMP_MARK = re.compile(r"\d+(?:[.,]\d+)?\s*(?:×|x\b|times|veces)|\b(?:more than|less than|higher than|lower than|above|below|outperforms?|"
                      r"lags?|trails?|m[aá]s que|menos que|por encima de|por debajo de|supera(?:n)?|mayor(?:es)? que|menor(?:es)? que)\b", re.I)


def _swapped(statement: str, h: str) -> bool:
    ms, mh = CMP_MARK.search(statement), CMP_MARK.search(h)
    if not ms or not mh:
        return False
    ls, rs = _stems(statement[: ms.start()]), _stems(statement[ms.end():])
    lh, rh = _stems(h[: mh.start()]), _stems(h[mh.end():])
    a, b = ls - rs, rs - ls
    pol_s = 1 if not NEG_CMP.search(ms.group(0)) else -1
    pol_h = 1 if not NEG_CMP.search(mh.group(0)) else -1
    return pol_s == pol_h and bool(a & (rh - lh)) and bool(b & (lh - rh))


def _strictly_unsupported(h: str, slide: dict, extra: list | None) -> list[tuple[str, float]]:
    """The lint accepts a headline number within ±0.51 (pp, %) or 5% of anything derivable; a title may not be
    more precise than its proof. Here the tolerance is the precision the number is written with (half a unit
    of its last digit, at least 0.5%), and a hedged number ('~1.4', 'about 40,000') keeps 5%."""
    from ..core.headline import _collect_values, derivable

    vals, texts = _collect_values(slide)
    text_nums = {abs(n) for t in texts for n, _ in numbers_in(t)}
    cands = {abs(x) for x in derivable(vals)} | text_nums | {abs(x) for x in extra or []}
    # any 2-3 of the slide's values together, and their share of the total ("North, East and South: 72% of the gap")
    import itertools

    base = list(dict.fromkeys(abs(v) for v in vals if isinstance(v, (int, float))))[:12]  # evidence and chart repeat the same values
    # a total is the sum of the values, a value that equals the sum of the others, or a number the evidence calls total
    inner = [v for v in base if base and abs(v - (sum(base) - v)) <= 1e-6 * max(1, v)]
    if inner:
        base = [v for v in base if v not in inner]
    totals = {sum(base)} | set(inner)
    for t in texts:
        for m in re.finditer(r"\b(?:total|totales|sum|suma)\b\D{0,12}([\d][\d.,]*)", t, re.I):
            totals |= {abs(n) for n, _ in numbers_in(m.group(1))}
    totals = {t for t in totals if t}
    for k in (2, 3):
        for combo in itertools.combinations(base, k):
            sm = sum(combo)
            cands.add(sm)
            cands |= {sm / t * 100 for t in totals}
    cands |= {c / 1000 for c in cands} | {c * 1000 for c in cands} | {c / 1e6 for c in cands} | {c * 1e6 for c in cands}
    from ..spec import slide_exhibits

    for ex in slide_exhibits(slide):  # a bridge's running totals: the end bar a waterfall computes (857 + 250 − 40 = 1,067)
        run = None
        for st in (ex.get("data") or {}).get("steps") or []:
            if isinstance(st, dict) and isinstance(st.get("value"), (int, float)):
                run = st["value"] if run is None or st.get("type") == "total" else run + st["value"]
                cands.add(abs(run))
    if not cands:
        return []
    from ..ingest.readers import mask_dates

    masked = mask_dates(h)
    out = []
    for m in re.finditer(r"(?<![\w.,])[-−+]?\d[\d.,]*", masked):
        prev_word = (masked[: m.start()].rstrip().split(" ") or [""])[-1]
        got = numbers_in(prev_word + " " + m.group(0) + masked[m.end():m.end() + 12])  # "wave 1", "6 weeks": identifiers and durations
        if not got:
            continue
        v = abs(got[0][0])
        if v == 0 or (1900 <= v <= 2100 and float(v).is_integer()):
            continue
        digits = m.group(0).rstrip(".,")
        dec = re.search(r"[.,](\d{1,2})$", digits)
        step = 10 ** -len(dec.group(1)) if dec and not re.search(r"[.,]\d{3}$", digits) else 1
        tol = max(step / 2 + 1e-9, 0.005 * v)
        if re.search(rf"(?:^|[\s(])(?:{APPROX})\s*[€$£]?\s*$", masked[max(0, m.start() - 22):m.start()], re.I):
            tol = max(tol, 0.05 * v)
        if not any(abs(v - c) <= tol for c in cands):
            out.append((m.group(0), v))
    return out


def _has_magnitude(h: str, prop: dict) -> bool:
    mags = [abs(v) for v, _ in numbers_in(str(prop.get("magnitude") or ""))]
    return any(abs(abs(v) - m) <= max(0.051 * m, 0.051) for v, _ in numbers_in(h) for m in mags)


def _evidence_items(slide: dict) -> int:
    n = 0
    for e in slide.get("evidence") or []:
        if isinstance(e, dict) and isinstance(e.get("values"), list):
            n = max(n, len(e["values"]))
    return max(n, sum(1 for e in slide.get("evidence") or [] if isinstance(e, dict) and isinstance(e.get("value"), (int, float))))


def _comparison_labels(prop: dict) -> set[str]:
    c = str(prop.get("comparison") or "")
    parts = re.split(r"\s+(?:vs\.?|versus|v\.|frente a|compared with|compared to|against|contra|respecto a)\s+", c, flags=re.I)
    return {p.strip(" .") for p in parts if len(parts) > 1 and 2 <= len(p.strip()) <= 40}


def _order_checks(h: str, slide: dict, prop: dict) -> list[tuple[str, str, str]]:
    """Reversed comparisons (spec §91): against the slide's numbers, else against the proposition's own order."""
    series = {k: v for k, v in slide_series(slide).items() if not periods(k) or re.search(r"[A-Za-z]{4,}", re.sub(r"\b(?:FY|Q[1-4]|H[12])\b", "", k))}
    labels = sorted(set(series) | _comparison_labels(prop), key=len, reverse=True)
    pos = []
    for lab in labels:
        m = re.search(rf"(?<![\w]){re.escape(lab.lower())}(?![\w])", h.lower())
        if m and not any(s <= m.start() < e for s, e, _ in pos):
            pos.append((m.start(), m.end(), lab))
    pos.sort()
    out = []
    if len(pos) >= 2:
        (_, e1, a), (s2, _, b) = pos[0], pos[1]
        mid = h[e1:s2]
        pol = 1 if POS_CMP.search(mid) and not NEG_CMP.search(mid) else -1 if NEG_CMP.search(mid) and not POS_CMP.search(mid) else 0
        if pol and a in series and b in series and series[a] != series[b]:
            if (series[a] > series[b]) != (pol > 0):
                out.append(("HEADLINE_COMPARISON_UNSUPPORTED", "hard", f"The data contradict the comparison: {a} {series[a]:g} vs {b} {series[b]:g}"))
        elif pol:
            st = str(prop.get("statement") or "")
            sp = sorted((st.lower().find(lab.lower()), lab) for lab in (a, b) if lab.lower() in st.lower())
            if len(sp) == 2:
                mid2 = st[sp[0][0]:sp[1][0]]
                pol2 = 1 if POS_CMP.search(mid2) and not NEG_CMP.search(mid2) else -1 if NEG_CMP.search(mid2) and not POS_CMP.search(mid2) else 0
                if pol2 and (pol2 > 0) != (pol > 0) if sp[0][1] == a else pol2 and (pol2 > 0) == (pol > 0):
                    out.append(("HEADLINE_PROPOSITION_MISMATCH", "hard", f"The headline reverses the proposition's comparison of {a} and {b}"))
    elif len(pos) == 1 and series and len(series) >= 2:
        lab = pos[0][2]
        if lab in series:
            if MAX_SUP.search(h) and not MIN_SUP.search(h) and series[lab] < max(series.values()):
                out.append(("HEADLINE_COMPARISON_UNSUPPORTED", "hard", f"{lab} ({series[lab]:g}) is not the highest on the slide ({max(series, key=series.get)} {max(series.values()):g})"))
            if MIN_SUP.search(h) and not MAX_SUP.search(h) and series[lab] > min(series.values()):
                out.append(("HEADLINE_COMPARISON_UNSUPPORTED", "hard", f"{lab} ({series[lab]:g}) is not the lowest on the slide ({min(series, key=series.get)} {min(series.values()):g})"))
    return out


# ── diagnostic score (spec §17): never overrides a hard failure ───────────────

def _result(h: str, issues: list, prop: dict, ctx: dict, exp: str | None = None, obs: str | None = None) -> dict:
    codes = {c for c, cls, _ in issues if cls == "hard"}
    soft = {c for c, cls, _ in issues if cls != "hard"}
    a = analyze(h, ctx.get("lang")) if h else {"signature": "NOUN_PHRASE", "family": "noun"}
    fid = 0 if codes & FIDELITY else 25 - 5 * len(soft & {"HEADLINE_SUBJECT_IMPLICIT", "HEADLINE_TYPE_MISMATCH"})
    evid = 0 if "HEADLINE_NUMBER_UNSUPPORTED" in codes else (10 if prop.get("_inferred") or not prop else 25)
    answer = 0 if codes & {"HEADLINE_TOPIC", "HEADLINE_MISSING", "HEADLINE_PLACEHOLDER"} else 7 if "HEADLINE_QUESTION" in soft else 15
    nums = bool(numbers_in(h))
    spec_ = 10 if nums else 3 if "HEADLINE_VAGUE" in soft else 6
    sowhat = 4 if "HEADLINE_SO_WHAT_WEAK" in soft else 10 if (prop.get("role") in ("recommendation", "decision", "implication", "impact") or IMPLICATION.search(h) or re.search(r"\b(?:to|so|making|which|para|lo que)\b", h)) else 7
    struct = 0 if a["family"] in ("noun", "gerund") else 5 - (2 if "HEADLINE_TITLE_CASE" in soft else 0)
    conc = 5 if "HEADLINE_LONG" not in soft else 2
    hyg = 5 - sum(1 for c in ("HEADLINE_LOW_INFORMATION", "HEADLINE_REDUNDANT", "HEADLINE_WEAK_VERB") if c in soft) - (1 if h.endswith(".") else 0)
    dims = {"proposition_fidelity": max(0, fid), "evidence_support": evid, "answer_first": answer, "specificity": spec_, "so_what": sowhat,
            "sentence_structure": max(0, struct), "concision": conc, "wording_hygiene": max(0, hyg)}
    hard_ok = not codes
    rank = (hard_ok, not (codes & FIDELITY), "HEADLINE_NUMBER_UNSUPPORTED" not in codes, "HEADLINE_TYPE_MISMATCH" not in soft,
            "HEADLINE_TWO_GOVERNING_MESSAGES" not in codes, answer, spec_, sowhat, conc, hyg)
    return {"text": h, "passed": hard_ok, "hard": sorted(codes), "issues": issues, "score": sum(dims.values()), "dimensions": dims,
            "signature": a["signature"], "headline_type": exp, "observed_type": obs, "rank": rank}


# ── selection (spec §73) and the safe rewrite (spec §11) ──────────────────────

def candidates_of(slide: dict) -> list[tuple[str, str]]:
    field = title_field(slide)
    seen, out = set(), []
    for origin, t in [("headline", slide.get(field) or "")] + [(f"candidate[{i}]", c) for i, c in enumerate(slide.get("headline_candidates") or [])]:
        t = str(t or "").strip()
        if t and t not in seen:
            seen.add(t)
            out.append((origin, t))
    if not out:
        out = [("headline", "")]
    return out


def select(slide: dict, prop: dict | None, ctx: dict, allow_rewrite: bool = True) -> dict:
    cands = candidates_of(slide)
    evals = [dict(evaluate(t, slide, prop, ctx), origin=o) for o, t in cands]
    order = sorted(range(len(evals)), key=lambda i: (evals[i]["rank"], evals[i]["origin"] == "headline", -i), reverse=True)
    best = evals[order[0]]
    fallback = None
    # the safe rewrite repairs FORM (a label, a placeholder); a headline that contradicts the proposition or the
    # evidence is never papered over: that disagreement belongs upstream (spec §74), so the slide fails closed
    contradicted = any(set(e["hard"]) & (FIDELITY | {"HEADLINE_NUMBER_UNSUPPORTED", "HEADLINE_TWO_GOVERNING_MESSAGES"}) for e in evals)
    if not best["passed"] and allow_rewrite and prop and not prop.get("_inferred") and not contradicted:
        txt, how = deterministic(prop, ctx)
        if txt and txt not in {e["text"] for e in evals}:
            fallback = dict(evaluate(txt, slide, prop, ctx), origin="deterministic", derivation=how)
            evals.append(fallback)
            if fallback["passed"]:
                best = fallback
    if not allow_rewrite:
        best = evals[0]
    return {"selected": best, "candidates": evals, "rewritten": best["text"] != (cands[0][1] if cands else ""), "fallback": fallback}


def deterministic(prop: dict, ctx: dict) -> tuple[str | None, str]:
    """'Revenue declined 8% in 2026' when subject, direction, magnitude and period fully determine it.
    Never adds a cause, a driver or an implication the proposition does not state."""
    subj = str(prop.get("subject") or "").strip()
    d = str(prop.get("direction") or "").strip().lower()
    mag = str(prop.get("magnitude") or "").strip()
    tf = str(prop.get("timeframe") or "").strip()
    nd = P.direction_of(d)
    if prop.get("claim_type") not in ("fact", "trend") or nd not in ("up", "down") or not subj or not mag or not tf or not numbers_in(mag):
        return None, ""
    if re.match(APPROX, mag, re.I) or prop.get("confidence") == "low":
        return None, ""
    year = max((int(y) for y in YEAR_RE.findall(tf)), default=None)
    if year is None or (ctx.get("deck_year") and year > ctx["deck_year"]):
        return None, ""  # a projection's tense is not determined by the proposition
    lang = ctx.get("lang") or "en"
    mag = mag.lstrip("+−-")
    if lang == "es":
        if not re.match(r"(?:el|la|los|las)\s", subj, re.I):
            return None, ""
        plural = subj.split()[0].lower() in ("los", "las")
        verb = {"up": ("creció", "crecieron"), "down": ("cayó", "cayeron")}[nd][plural]
        if d.startswith(("aument", "increase")):
            verb = ("aumentó", "aumentaron")[plural]
        elif d.startswith(("disminu", "decrease", "decline")):
            verb = ("disminuyó", "disminuyeron")[plural]
        txt = f"{subj[:1].upper()}{subj[1:]} {verb} un {mag} en {tf}"
    else:
        verb = {"decline": "declined", "declined": "declined", "decrease": "decreased", "increase": "increased", "growth": "grew",
                "grow": "grew", "grew": "grew", "fall": "fell", "fell": "fell", "rise": "rose", "rose": "rose", "drop": "dropped"}.get(d, "increased" if nd == "up" else "decreased")
        txt = f"{subj[:1].upper()}{subj[1:]} {verb} {mag} in {tf}"
    return txt, f"subject + direction + magnitude + period of the proposition ({subj}; {d}; {mag}; {tf})"
