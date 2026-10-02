"""Wording signatures: the grammatical shape of a message, in English and Spanish (v3.1).

A signature is a light structural label, not a parse:

    VERB_OBJECT_OUTCOME            Consolidate suppliers to reduce complexity · Consolidar proveedores para reducir complejidad
    VERB_OBJECT                    Minimise upfront cost · Reducir el capex
    ACTION_TO_OUTCOME              Repricing electronics can recover ~1.4 pp · Repreciar electrónica permitiría recuperar 1,4 pp
    SUBJECT_CHANGE_MAGNITUDE       Revenue fell 8% in 2026 · Las ventas cayeron un 8% en 2026
    DRIVER_EXPLAINS_OUTCOME        Three regions explain 72% of the gap · Tres regiones concentran el 72% de la brecha
    CONDITION_IMPLIES_CONSEQUENCE  Without pricing action, margin will stay below target · Sin acción en precios, el margen…
    CLAUSE_SUBJECT_VERB_OUTCOME    any other declarative sentence
    GERUND_PHRASE                  Improving pricing discipline (no finite verb)
    NOUN_PHRASE                    Supplier consolidation · Consolidación de proveedores

Families group the signatures a reader perceives as the same kind of sentence: `action` (an
instruction), `declarative` (a conclusion), `gerund`, `noun`. Spanish is read with its own rules
(infinitive-led recommendations, finite-verb endings), never as translated English.
"""
from __future__ import annotations

import re

from ..core.headline import VERBS, _tokens

FAMILY = {
    "VERB_OBJECT_OUTCOME": "action", "VERB_OBJECT": "action",
    "ACTION_TO_OUTCOME": "declarative", "SUBJECT_CHANGE_MAGNITUDE": "declarative", "DRIVER_EXPLAINS_OUTCOME": "declarative",
    "CONDITION_IMPLIES_CONSEQUENCE": "declarative", "CLAUSE_SUBJECT_VERB_OUTCOME": "declarative",
    "GERUND_PHRASE": "gerund", "NOUN_PHRASE": "noun",
}

ES_FUNC = {"el", "la", "los", "las", "de", "del", "y", "en", "que", "por", "para", "con", "un", "una", "se", "su", "sus", "al",
           "más", "menos", "es", "son", "lo", "como", "sin", "entre", "hasta", "desde", "sobre", "tras", "pero", "este", "esta"}
EN_FUNC = {"the", "of", "and", "in", "to", "for", "with", "a", "an", "is", "are", "by", "its", "their", "than", "from", "on",
           "at", "more", "less", "this", "that", "while", "into", "over", "under", "but", "be", "was", "were", "will", "would"}

# base-form English verbs that open an instruction ("Consolidate suppliers …")
IMPERATIVE_EN = {
    "accelerate", "add", "adjust", "align", "allocate", "approve", "assign", "automate", "avoid", "build", "buy", "cap", "centralise",
    "centralize", "change", "close", "collect", "combine", "commit", "complete", "consolidate", "continue", "control", "create",
    "cut", "decide", "define", "delay", "deliver", "deploy", "design", "develop", "diagnose", "digitise", "digitize", "divest",
    "double", "drop", "eliminate", "embed", "enable", "enter", "establish", "exit", "expand", "extend", "fix", "focus", "freeze",
    "fund", "grow", "halt", "hire", "implement", "improve", "increase", "integrate", "introduce", "invest", "keep", "launch",
    "lead", "limit", "lock", "lower", "maintain", "make", "map", "maximise", "maximize", "merge", "migrate", "minimise",
    "minimize", "modernise", "modernize", "monitor", "move", "negotiate", "offer", "open", "optimise", "optimize", "outsource",
    "pilot", "pause", "phase", "plan", "postpone", "prioritise", "prioritize", "protect", "prove", "push", "put", "raise",
    "rationalise", "rationalize", "rebalance", "rebuild", "recover", "redeploy", "redesign", "reduce", "refocus", "reinvest",
    "release", "relaunch", "remove", "renegotiate", "reorganise", "reorganize", "replace", "reprice", "reset", "resize",
    "restructure", "retain", "retire", "review", "run", "scale", "secure", "sell", "separate", "set", "shift", "shorten",
    "shrink", "simplify", "standardise", "standardize", "start", "stop", "streamline", "strengthen", "tighten", "track", "train",
    "transfer", "upgrade", "use", "validate", "win", "test", "target", "segment", "reprioritise", "reprioritize", "harmonise",
    "harmonize", "insource", "upskill", "measure", "publish", "share", "agree", "appoint", "ask", "confirm", "defer", "drive",
    "analyse", "analyze", "assess", "select", "prepare", "engage", "mobilise", "mobilize", "onboard", "scope", "frame", "size",
    "sequence", "roll", "renew", "rethink", "reshape", "refresh", "revise", "report", "embed", "anchor", "involve", "empower",
    "accept", "adopt", "apply", "attract", "balance", "benchmark", "brief", "capture", "check", "choose", "clarify", "clean",
    "communicate", "compare", "concentrate", "connect", "convert", "coordinate", "cover", "deepen", "detect", "document",
    "draft", "ensure", "evaluate", "explore", "fill", "finalise", "finalize", "gather", "give", "govern", "guarantee", "help",
    "identify", "inform", "join", "learn", "leverage", "link", "manage", "match", "own", "partner", "prevent", "price",
    "promote", "provide", "quantify", "reach", "redirect", "refine", "reinforce", "rent", "repair", "replicate", "reprioritise",
    "require", "resolve", "respond", "restore", "rethink", "return", "reuse", "save", "schedule", "screen", "seek", "serve",
    "sign", "source", "speed", "split", "staff", "support", "switch", "take", "tie", "trim", "unify", "unlock", "verify",
    "rank", "lift", "restore", "offset", "outweigh", "exceed", "absorb", "erode", "dilute", "fund", "cover", "prefer", "favour", "favor", "produce", "outsell", "outgrow", "outpace", "underperform", "overtake", "spend", "buy",
}
# imperative-looking words that are just as often nouns at the head of a declarative sentence
NOUN_VERB = {"cost", "costs", "price", "prices", "share", "plan", "target", "focus", "review", "shift", "scale", "design", "test",
             "pilot", "launch", "track", "change", "return", "report", "lead", "rate", "value", "need", "use", "offer", "increase",
             "drop", "cut", "set", "run", "fund", "phase", "segment", "map", "measure", "control", "delay", "freeze", "lock",
             "double", "win", "move", "exit", "close", "start", "stop", "add", "drive", "build", "pause", "limit", "cap",
             "decline", "declines", "rise", "rises", "fall", "falls", "gain", "gains", "loss", "growth", "slowdown", "report",
             "reports", "source", "support", "staff", "return", "returns", "save", "savings", "match", "split", "sign", "switch",
             "trim", "speed", "price", "check", "cover", "help", "link", "partner", "screen", "schedule", "balance", "benchmark",
             "capture", "document", "draft", "rent", "repair", "size", "sequence", "frame", "scope", "brief", "promote", "require",
             "increases", "decreases", "drops", "changes", "shifts", "cuts", "costs", "shares", "plans", "targets", "reviews",
             "lower", "clear", "free", "open", "slow", "right", "level", "even", "better", "empty", "complete", "fast"}
NOT_VERB_EN = {"enterprise", "premise", "expertise", "merchandise", "franchise", "corporate", "private", "climate", "state",
               "senate", "candidate", "certificate", "aggregate", "adequate", "accurate", "ultimate", "intimate", "delicate",
               "immediate", "appropriate", "chocolate", "template", "estate", "affiliate", "graduate", "advocate", "associate",
               "electorate", "magistrate", "climate", "moderate", "separate", "approximate", "alternate", "deliberate", "update"}
NOT_INF_ES = {"lugar", "hogar", "bienestar", "poder", "deber", "placer", "taller", "mujer", "alquiler", "militar", "popular",
              "similar", "particular", "regular", "nuclear", "familiar", "celular", "auxiliar", "solar", "dólar", "dolar",
              "azúcar", "azucar", "titular", "pilar", "escolar", "lunar", "polar", "peculiar", "singular", "modular", "secular",
              "par", "mar", "bar", "ámbar", "nectar", "néctar", "cráter", "carácter", "caracter", "líder", "lider", "máster",
              "master", "chárter", "póster", "poster", "súper", "super", "cáncer", "mártir", "elixir", "nadir", "faquir",
              "tutor", "ver"}
# Spanish finite forms the headline lexicon does not list, by ending (future, conditional, preterite)
ES_FINITE_END = re.compile(r"(?:ará|erá|irá|arán|erán|irán|aría|ería|iría|arían|erían|irían|aron|ieron|yeron|ó|aba|aban|ía|ían)$")
ES_FINITE = {"explica", "explican", "concentra", "concentran", "representa", "representan", "supone", "suponen", "impulsa",
             "impulsan", "provoca", "provocan", "causa", "causan", "reduce", "reducen", "aumenta", "aumentan", "mejora", "mejoran",
             "crece", "crecen", "cae", "caen", "baja", "bajan", "sube", "suben", "genera", "generan", "aporta", "aportan", "permite",
             "permiten", "protege", "protegen", "recupera", "recuperan", "ahorra", "ahorran", "cuesta", "cuestan", "pierde",
             "pierden", "gana", "ganan", "lidera", "lideran", "supera", "superan", "duplica", "duplican", "triplica", "alcanza",
             "alcanzan", "mantiene", "mantienen", "requiere", "requieren", "necesita", "necesitan", "pone", "ponen", "coincide",
             "coinciden", "sigue", "siguen", "queda", "quedan", "llega", "llegan", "pasa", "pasan", "cubre", "cubren", "compensa",
             "compensan", "absorbe", "absorben", "retrasa", "retrasan", "acelera", "aceleran", "frena", "frenan", "limita",
             "limitan", "amenaza", "amenazan", "exige", "exigen", "desbloquea", "desbloquean", "libera", "liberan", "asegura",
             "aseguran", "garantiza", "garantizan", "sitúa", "sitúan", "deja", "dejan", "eleva", "elevan", "recorta", "recortan",
             "entrega", "entregan", "ofrece", "ofrecen", "logra", "logran", "consigue", "consiguen", "presenta", "presentan",
             "muestra", "muestran", "refleja", "reflejan", "indica", "indican", "sugiere", "sugieren", "confirma", "confirman",
             "demuestra", "demuestran", "avanza", "avanzan", "va", "van", "está", "están", "es", "son", "fue", "fueron", "ha",
             "han", "había", "será", "serán", "sería", "serían", "podría", "podrían", "puede", "pueden", "debe", "deben",
             "tiene", "tienen", "hay", "disminuye", "disminuyen", "empeora", "empeoran", "retrocede", "retroceden", "desciende",
             "descienden", "contribuye", "contribuyen", "acumula", "acumulan", "duplicó", "obliga", "obligan", "impide", "impiden",
             "evita", "evitan", "conviene", "convienen", "debería", "deberían", "pone", "abre", "abren", "cierra", "cierran",
             "vende", "venden", "compra", "compran", "paga", "pagan", "rinde", "rinden", "devuelve", "devuelven", "resta", "restan",
             "suma", "suman", "equivale", "equivalen", "ocupa", "ocupan", "domina", "dominan", "crecerá", "caerá", "falta",
             "faltan", "aprueba", "aprueban", "protegería", "lleva", "llevan", "conduce", "conducen", "origina", "originan",
             "deriva", "derivan", "eleva", "erosiona", "erosionan", "diluye", "diluyen", "recomendamos", "proponemos",
             "pedimos", "solicitamos", "necesitamos", "estamos", "somos", "tenemos", "vamos"}
ES_PRET_IRREG = {"redujo", "produjo", "condujo", "dijo", "hizo", "tuvo", "pudo", "puso", "quiso", "supo", "vino", "trajo", "dio",
                 "estuvo", "anduvo", "redujeron", "produjeron", "hicieron", "tuvieron", "pusieron", "dieron", "fue", "fueron"}
EN_PAST_IRREG = {"grew", "fell", "rose", "drove", "led", "made", "took", "came", "went", "held", "kept", "won", "lost", "sold",
                 "paid", "brought", "saw", "ran", "spent", "became", "began", "gave", "got", "was", "were", "had", "did", "hit",
                 "shrank", "sank", "slid", "stood", "left", "met", "built", "cut", "fed", "found", "put", "set"}
EN_PARTICIPLE_IRREG = {"made", "done", "built", "driven", "taken", "given", "seen", "shown", "held", "led", "set", "cut", "put",
                       "kept", "sold", "bought", "brought", "paid", "won", "lost", "found", "run", "grown", "known", "met",
                       "spent", "left", "begun", "become", "chosen", "written", "hit", "fallen", "risen"}
AUX_EN = {"is", "are", "was", "were", "be", "been", "being", "gets", "got", "get"}
AUX_ES = {"es", "son", "fue", "fueron", "será", "serán", "sido", "está", "están", "estaba", "estaban", "sería", "serían"}
MODAL_EN = {"will", "would", "could", "can", "may", "might", "should", "must", "shall"}
DET = {"the", "a", "an", "its", "their", "our", "most", "more", "less", "all", "every", "each", "no", "some", "two", "three",
       "el", "la", "los", "las", "un", "una", "su", "sus", "más", "menos", "todo", "toda", "todos", "todas"}
AFTER_VERB = {"at", "as", "into", "than", "by", "to", "from", "above", "below", "in", "over", "under", "up", "down", "back", "out", "off", "on", "ahead",
              "behind", "for", "with", "nearly", "almost", "about", "around", "only", "just", "por", "en", "hasta", "un", "una"}
DRIVER_VERBS = {"explains", "explain", "explained", "accounts", "account", "accounted", "drives", "drive", "drove", "driven",
                "causes", "cause", "caused", "contributes", "contribute", "contributed", "concentrates", "concentrate",
                "explica", "explican", "explicó", "explicaron", "concentra", "concentran", "impulsa", "impulsan", "impulsó",
                "provoca", "provocan", "provocó", "causa", "causan", "causó", "contribuye", "contribuyen", "contribuyó",
                "represent", "represents", "representa", "representan", "supone", "suponen", "makes"}
CHANGE_VERBS = {"grew", "grows", "grow", "fell", "falls", "fall", "rose", "rises", "rise", "declined", "declines", "decline",
                "increased", "increases", "increase", "decreased", "decreases", "decrease", "dropped", "drops", "drop", "doubled",
                "doubles", "halved", "halves", "tripled", "slowed", "slows", "accelerated", "accelerates", "shrank", "shrinks",
                "widened", "widens", "narrowed", "narrows", "improved", "improves", "worsened", "worsens", "recovered",
                "crece", "crecen", "creció", "crecieron", "cae", "caen", "cayó", "cayeron", "sube", "suben", "subió", "subieron",
                "baja", "bajan", "bajó", "bajaron", "aumenta", "aumentan", "aumentó", "aumentaron", "disminuye", "disminuyen",
                "disminuyó", "disminuyeron", "duplica", "duplicó", "mejora", "mejoró", "empeora", "empeoró", "retrocede",
                "retrocedió", "desciende", "descendió", "recupera", "recuperó"}
CONDITION_START = {"if", "unless", "without", "should", "si", "sin", "salvo", "de"}  # "de no actuar…"
OUTCOME_RE = re.compile(r"\b(?:to|in order to|so that|so as to)\s+(?!the\b|a\b|an\b|its\b|their\b|\d)[a-z]+|\bby\s+[a-z]+ing\b|\b(?:para|con el fin de|a fin de|y así|mediante)\b", re.I)
ENUM_RE = re.compile(r"^\s*(?:\d+[.)]|[a-zA-Z][.)]|(?:option|opción|opcion|step|paso|wave|ola|phase|fase|pillar|pilar|workstream|palanca|lever)\s*[\w\d]*\s*[:—–-])\s*", re.I)
LABEL_SPLIT_RE = re.compile(r"^\s*((?:option|opción|opcion|step|paso|wave|ola|phase|fase|pillar|pilar)\s*[\w\d]{0,3})\s*[—–:-]\s+", re.I)


def language(text: str) -> str | None:
    """'es' / 'en' by function words and Spanish orthography, or None when unclear."""
    toks = _tokens(text)
    es = sum(t in ES_FUNC for t in toks) + sum(1 for t in toks if re.search(r"[áéíóúñ¿¡]", t)) + sum(t in ES_FINITE for t in toks)
    en = sum(t in EN_FUNC for t in toks) + sum(1 for t in toks if len(t) > 4 and t.endswith(("ing", "ed", "ly")))
    if es == en:
        return None
    return "es" if es > en else "en"


def mixed_language(text: str) -> bool:
    """'Repricing electrónica unlocks 1.4 pp de margen': both languages carry the sentence."""
    toks = _tokens(text)
    es = sum(t in ES_FUNC for t in toks) + sum(1 for t in toks if re.search(r"[áéíóúñ]", t))
    en_words = [t for t in toks if t in EN_FUNC or (len(t) > 4 and t.endswith(("ing", "ed"))) or (t in VERBS and t not in ES_FINITE and re.fullmatch(r"[a-z]+", t) and t.endswith("s") and t not in ES_FUNC)]
    en = len(en_words)
    return es >= 2 and en >= 2 and min(es, en) >= 0.3 * max(es, en)


def strip_enum(text: str) -> tuple[str, bool]:
    """'2. Diagnose the gap' → ('Diagnose the gap', True); 'Option A — Minimise cost' → ('Minimise cost', True)."""
    t = text or ""
    m = LABEL_SPLIT_RE.match(t)
    if m:
        return t[m.end():].strip(), True
    m = ENUM_RE.match(t)
    if m and m.end() < len(t):
        return t[m.end():].strip(), True
    return t.strip(), False


def _is_inf_es(t: str) -> bool:
    t = t.lower()
    if t in NOT_INF_ES or len(t) <= 3:
        return False
    return bool(re.fullmatch(r"[a-záéíóúñü]+(?:ar|er|ir)(?:se|lo|la|los|las|le|les)?", t))


def _is_gerund(t: str, lang: str | None) -> bool:
    t = t.lower()
    if lang == "es" or re.search(r"(?:ando|iendo|yendo)$", t):
        return bool(re.fullmatch(r"[a-záéíóúñ]{4,}(?:ando|iendo|yendo)", t))
    return len(t) > 4 and t.endswith("ing") and t not in {"thing", "things", "string", "ceiling", "spring", "during", "morning", "evening", "pudding"}


def _is_base_verb_en(t: str) -> bool:
    t = t.lower()
    if t in IMPERATIVE_EN:
        return True
    return len(t) > 5 and t.isalpha() and t.endswith(("ise", "ize", "ate", "ify")) and t not in NOT_VERB_EN


def _past_lead(t: str, lang: str | None) -> bool:
    t = t.lower()
    if lang == "es":
        return bool(re.search(r"(?:ó|aron|ieron|amos|imos)$", t)) and len(t) > 3 and not _is_inf_es(t)
    return t in EN_PAST_IRREG or (len(t) > 4 and t.endswith("ed"))


def finite_index(toks: list[str], lang: str | None, start: int = 1, instruction: bool = False) -> int | None:
    """Index of the first finite verb at or after `start` (an infinitive after 'to'/'para' is not finite)."""
    for i in range(max(0, start), len(toks)):
        t = toks[i]
        prev = toks[i - 1] if i else ""
        if prev in ("to", "para", "de", "a", "por", "sin", "al"):
            continue
        if t in MODAL_EN or t in AUX_EN or t in ("has", "have", "had"):
            return i
        if lang != "en" and (t in ES_FINITE or t in ES_PRET_IRREG or (prev in ("se", "no", "ya", "nunca", "también", "solo", "sólo") and len(t) > 2 and t not in ES_FUNC) or (len(t) > 3 and ES_FINITE_END.search(t) and not _is_inf_es(t) and t not in ES_FUNC)):
            return i
        if lang != "es":
            if t in EN_PAST_IRREG or (len(t) > 4 and t.endswith("ed") and prev not in DET):
                return i
            nxt0 = toks[i + 1] if i + 1 < len(toks) else ""
            open_third = (t.endswith("es") or (t.endswith("s") and not t.endswith(("ss", "us", "is")))) and len(t) > 4 and i > 0 and prev not in DET \
                and not re.search(r"(?:tion|ment|ness|ity|ance|ence|ship|ism|ics|ers|ors|ists|ings)$", t) \
                and (nxt0 in DET or (nxt0 in AFTER_VERB and nxt0 not in ("to", "for", "and", "of", "in", "on", "with")) or re.match(r"[-−+~≈]?[\d€$£]", nxt0 or "x"))
            nxt1 = toks[i + 1] if i + 1 < len(toks) else ""
            nxt2 = toks[i + 1] if i + 1 < len(toks) else ""
            if not instruction and i >= 2 and _is_base_verb_en(t) and (t not in NOUN_VERB or nxt2 in DET or nxt2 in AFTER_VERB) and prev not in DET and prev not in ("to", "and", "or", "&", "will", "can") \
                    and nxt1 and nxt1 not in ("of", "and", "&", "for", "or") and not re.fullmatch(r"[a-z]+ing|[a-z]+ed", prev):
                return i  # compound or plural subject + present verb: "a pricing reset and a cost programme restore EBITDA"
            if i == 1 and toks[0].endswith("s") and len(toks[0]) > 3 and _is_base_verb_en(t) and t not in NOUN_VERB:
                return i  # plural subject + base verb: "Customers rank …"
            if open_third and t not in ES_FUNC and not instruction:  # after an imperative, "outcomes at …" is its object
                return i
            third = t.endswith("s") and len(t) > 4 and (_is_base_verb_en(t[:-1]) or (t.endswith("es") and _is_base_verb_en(t[:-2])) or (t.endswith("ies") and _is_base_verb_en(t[:-3] + "y")))
            if (t in VERBS or third) and re.fullmatch(r"[a-z]+", t) and t not in ES_FUNC and t not in ES_FINITE:
                if t in NOUN_VERB or t.rstrip("s") in NOUN_VERB:
                    nxt = toks[i + 1] if i + 1 < len(toks) else ""
                    if prev in DET or i == 0 or not nxt or not (nxt in DET or nxt in AFTER_VERB or re.match(r"[-−+~≈]?[\d€$£]", nxt)):
                        continue  # "cost analysis", "market share", "revenue decline": nouns
                return i
        if lang != "en" and i > 1 and len(t) > 3 and re.search(r"(?:a|e|an|en)$", t) and prev not in ES_FUNC and prev not in DET \
                and not re.search(r"(?:ción|sión|dad|tad|aje|umbre|ente|ante|ista|ia|ía|ica|ura|ora|era|ena|ana|ina|ona|ma)$", t) \
                and (toks[i + 1] if i + 1 < len(toks) else "") in ("el", "la", "los", "las", "un", "una", "su", "sus", "al", "más", "menos", "casi", "hasta"):
            return i  # "esta opción maximiza la …": a present-tense verb before its object
        if lang != "en" and t in VERBS and t not in ES_FUNC and re.search(r"[a-záéíóúñ]", t) and not _is_inf_es(t):
            return i
    return None


def has_finite_verb(text: str, lang: str | None = None) -> bool:
    toks = _tokens(strip_enum(text)[0])
    lang = lang or language(text)
    return finite_index(toks, lang, 0) is not None


def analyze(text: str, lang: str | None = None) -> dict:
    """Signature and the features the parallel checks compare."""
    raw = (text or "").strip()
    body, numbered = strip_enum(raw)
    lang = lang or language(body) or "en"
    toks = _tokens(body)
    words = [t for t in toks if re.search(r"[a-záéíóúñü0-9]", t)]
    lead = toks[0] if toks else ""
    fin = finite_index(toks, lang, 1)
    head_toks = _tokens(re.split(r",|;|\s[—–-]\s|\b(?:which|that|who|where|que|lo que|donde)\b", body, maxsplit=1)[0])
    fin_head = finite_index(head_toks, lang, 1, instruction=True)
    lead_kind = "noun"
    if not toks:
        lead_kind = "empty"
    elif lang == "es" and _is_inf_es(lead):
        lead_kind = "infinitive"
    elif lang != "es" and _is_base_verb_en(lead) and not (lead in NOUN_VERB and (fin is not None or len(toks) == 1)):
        lead_kind = "imperative"
        fin = fin_head
    elif _is_gerund(lead, lang):
        lead_kind = "gerund"
    elif _past_lead(lead, lang) and fin is None and len(toks) > 1 and (toks[1] in DET or (len(toks) >= 3 and not toks[1].endswith("ing"))):
        lead_kind = "past_lead"
    es_lead_verb = lang == "es" and (lead in ES_FINITE or re.fullmatch(r"[a-záéíóúñ]{4,}(?:amos|emos|imos)", lead or "") is not None)  # "Proponemos …"
    finite = fin if lead_kind in ("infinitive", "imperative", "gerund", "past_lead") else finite_index(toks, lang, 0 if lead in MODAL_EN | AUX_EN or es_lead_verb else 1)
    outcome = bool(OUTCOME_RE.search(body))
    if lead_kind in ("imperative", "infinitive", "past_lead") and (finite is None or lead_kind == "past_lead"):
        sig = "VERB_OBJECT_OUTCOME" if outcome else "VERB_OBJECT"
    elif lead_kind in ("gerund", "infinitive") and finite is not None:
        sig = "ACTION_TO_OUTCOME"
    elif lead_kind == "gerund":
        sig = "GERUND_PHRASE"
    elif finite is None:
        sig = "NOUN_PHRASE"
    else:
        fv = toks[finite]
        if lead in CONDITION_START or re.search(r"\b(?:unless|a menos que|salvo que)\b", body, re.I) or (re.search(r"^(?:if|without|si|sin)\b", body, re.I)):
            sig = "CONDITION_IMPLIES_CONSEQUENCE"
        elif any(t in DRIVER_VERBS for t in toks[finite:finite + 3]):
            sig = "DRIVER_EXPLAINS_OUTCOME"
        elif any(t in CHANGE_VERBS for t in toks[finite:finite + 3]) and re.search(r"\d", body):
            sig = "SUBJECT_CHANGE_MAGNITUDE"
        else:
            sig = "CLAUSE_SUBJECT_VERB_OUTCOME"
        del fv
    return {
        "text": raw, "body": body, "numbered": numbered, "lang": lang, "signature": sig, "family": FAMILY[sig],
        "lead": lead, "lead_kind": lead_kind, "voice": voice(toks, lang), "tense": tense(toks, lang, lead_kind, finite),
        "words": len(words), "has_number": bool(re.search(r"\d", body)), "terminal": _terminal(raw), "case": case_style(body),
        "outcome": outcome,
    }


def voice(toks: list[str], lang: str | None) -> str:
    for i, t in enumerate(toks[:-1]):
        nxt = toks[i + 1:i + 3]
        if lang != "es" and t in AUX_EN and any((len(n) > 4 and n.endswith("ed")) or n in EN_PARTICIPLE_IRREG for n in nxt[:1]):
            return "passive"
        if lang != "en" and t in AUX_ES and any(re.fullmatch(r"[a-záéíóúñ]+(?:ado|ada|ados|adas|ido|ida|idos|idas)", n) for n in nxt[:1]):
            return "passive"
    return "active"


def tense(toks: list[str], lang: str | None, lead_kind: str, finite: int | None) -> str:
    if lead_kind in ("imperative", "infinitive"):
        return "imperative" if lead_kind == "imperative" else "infinitive"
    if lead_kind == "gerund" and finite is None:
        return "gerund"
    if lead_kind == "past_lead":
        return "past"
    if finite is None:
        return "none"
    t = toks[finite]
    if t in ("will", "would", "could", "can", "may", "might", "shall", "should", "must") or (lang != "en" and re.search(r"(?:rá|rán|ría|rían)$", t)):
        return "modal"
    if t in EN_PAST_IRREG or (lang != "es" and t.endswith("ed")) or (lang != "en" and re.search(r"(?:ó|aron|ieron)$", t)) or t in ("fue", "fueron", "was", "were", "had"):
        return "past"
    if t in ("has", "have", "ha", "han"):
        return "perfect"
    return "present"


def _terminal(text: str) -> str:
    t = (text or "").rstrip()
    if t.endswith("."):
        return "period"
    if t.endswith(("!", "?")):
        return t[-1]
    return "none"


def case_style(text: str) -> str:
    ws = [w for w in (text or "").split() if re.match(r"[A-Za-zÀ-ÿ]", w)]  # words that start with a letter ('€48M' says nothing about case)
    if not ws:
        return "none"
    if not re.match(r"[A-Za-zÀ-ÿ]", (text or "").strip()):
        return "sentence"  # '€48M run-rate savings…': a figure opens the sentence, its case says nothing
    if all(w.isupper() for w in ws if len(w) > 1) and len(ws) > 1:
        return "upper"
    caps = sum(1 for w in ws[1:] if w[:1].isupper())
    if len(ws) >= 3 and caps / (len(ws) - 1) > 0.6:
        return "title"
    return "sentence" if ws[0][:1].isupper() else "lower"
