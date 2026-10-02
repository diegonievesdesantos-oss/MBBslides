"""v3.1 Parallel Wording Guarantee (spec §19-28, §57-62, §86, §89)."""
from cpe.editorial import compile_editorial
from cpe.editorial.parallel import check, detect
from cpe.editorial.signatures import analyze


def deck(slides, key_line=None, lang="en"):
    return {"meta": {"title": "T", "language": lang, "editorial_mode": "mbb_strict", "partial": True},
            "storyline": {"governing_thought": "", "key_line": key_line or []}, "slides": slides}


def cards(members, explicit=True, archetype=None, message_type="recommendation"):
    vis = {"type": "text_columns", "data": {"items": [{"title": m} for m in members]}}
    if explicit:
        vis["parallel_group"] = "G"
    s = {"id": "s01", "kind": "content", "headline": "x", "visual": vis}
    if archetype:
        s["archetype"] = archetype
    else:
        s["message_type"] = message_type
    return s


def verdict(spec, lang="en"):
    gs = [check(g, lang) for g in detect(spec)]
    assert gs, "no group detected"
    hard = {f["code"] for g in gs for f in g["findings"] if f["class"] == "hard"}
    soft = {f["code"] for g in gs for f in g["findings"] if f["class"] == "soft"}
    info = {f["code"] for g in gs for f in g["findings"] if f["class"] == "info"}
    return hard, soft, info


def test_signatures_of_the_spec_examples():
    assert analyze("Consolidate procurement to reduce supplier fragmentation")["signature"] == "VERB_OBJECT_OUTCOME"
    assert analyze("Reduce procurement fragmentation by consolidating the supplier base")["signature"] == "VERB_OBJECT_OUTCOME"
    assert analyze("Procurement fragmentation")["signature"] == "NOUN_PHRASE"
    assert analyze("Three regions explain 72% of the gap")["signature"] == "DRIVER_EXPLAINS_OUTCOME"
    assert analyze("Without pricing action, margin will remain below the 2027 target")["signature"] == "CONDITION_IMPLIES_CONSEQUENCE"
    assert analyze("Repricing electronics can recover ~1.4 pp in 2027")["signature"] == "ACTION_TO_OUTCOME"
    assert analyze("Consolidar proveedores para reducir complejidad", "es")["signature"] == "VERB_OBJECT_OUTCOME"
    assert analyze("Repreciar electrónica permitiría recuperar ~1,4 pp de margen", "es")["signature"] == "ACTION_TO_OUTCOME"


def test_three_verb_led_recommendations_pass():
    hard, soft, _ = verdict(deck([cards(["Consolidate suppliers to reduce procurement complexity", "Automate invoice processing to remove manual effort",
                                         "Tighten pricing discipline to protect gross margin"])]))
    assert not hard and not soft


def test_noun_verb_clause_mixture_fails():
    hard, _, _ = verdict(deck([cards(["Procurement fragmentation", "Finance has too many manual activities", "Improving pricing discipline"])]))
    assert "PARALLEL_SIGNATURE_MISMATCH" in hard


def test_same_syntax_different_granularity_flagged():
    hard, soft, _ = verdict(deck([cards(["Reduce supplier fragmentation", "Automate finance", "Increase EBITDA by €12m through pricing"])]))
    assert "PARALLEL_GRANULARITY_MISMATCH" in hard | soft


def test_active_passive_mixture_flagged_in_an_explicit_group():
    hard, soft, _ = verdict(deck([cards(["Suppliers are consolidated by procurement", "Automate invoice processing", "Tighten pricing discipline"])]))
    assert hard | soft & {"PARALLEL_VOICE_MISMATCH", "PARALLEL_SIGNATURE_MISMATCH"}


def test_mixed_tense_in_steps_fails():
    s = {"id": "s01", "kind": "content", "headline": "x", "visual": {"type": "process", "data": {"steps": [
        {"label": "Collected the relevant data"}, {"label": "Diagnose the performance gap"}, {"label": "Define the recommended actions"}]}}}
    hard, _, _ = verdict(deck([s]))
    assert "PARALLEL_TENSE_MISMATCH" in hard


def test_consistent_process_steps_pass():
    s = {"id": "s01", "kind": "content", "headline": "x", "visual": {"type": "process", "data": {"steps": [
        {"label": "Collect the relevant data"}, {"label": "Diagnose the performance gap"}, {"label": "Define the recommended actions"},
        {"label": "Implement and track delivery"}]}}}
    hard, soft, _ = verdict(deck([s]))
    assert not hard and not soft


def test_bad_process_steps_fail():
    s = {"id": "s01", "kind": "content", "headline": "x", "visual": {"type": "process", "data": {"steps": [
        {"label": "1. Data"}, {"label": "2. Analyse results"}, {"label": "3. Recommendation is developed"}, {"label": "4. Implementation"}]}}}
    hard, _, _ = verdict(deck([s]))
    assert "PARALLEL_SIGNATURE_MISMATCH" in hard


def test_spanish_infinitive_recommendations_pass():
    hard, soft, _ = verdict(deck([cards(["Consolidar proveedores para reducir complejidad", "Automatizar facturación para eliminar trabajo manual",
                                         "Reforzar disciplina de precios para proteger margen"])], lang="es"), "es")
    assert not hard and not soft


def test_english_imperative_options_pass_and_mixed_options_fail():
    def opts(cols):
        return deck([{"id": "s01", "kind": "content", "headline": "x", "visual": {"type": "harvey_table", "columns": ["Criteria"] + cols, "rows": []}}])

    hard, soft, _ = verdict(opts(["Option A — Minimise upfront cost", "Option B — Accelerate implementation", "Option C — Maximise strategic flexibility"]))
    assert not hard and not soft
    hard, _, _ = verdict(opts(["Option A — Lowest cost", "Option B — Faster implementation", "Option C — This option maximises strategic flexibility"]))
    assert "PARALLEL_SIGNATURE_MISMATCH" in hard


def test_different_narrative_roles_are_not_forced_into_one_group():
    slides = []
    for i, (role, ct, h) in enumerate([("diagnosis", "driver", "Electronics mix explains most of the 1.9 pp margin decline"),
                                       ("implication", "impact", "Current growth plans would widen the margin gap further"),
                                       ("recommendation", "recommendation", "Reprice electronics first to recover ~1.4 pp")]):
        slides.append({"id": f"s{i + 2}", "kind": "content", "section": "K1", "headline": h,
                       "proposition": {"statement": h, "role": role, "claim_type": ct, "evidence_ids": ["E"]}})
    assert not [g for g in detect(deck(slides)) if g["context"] == "headlines"]


def test_same_role_consecutive_headlines_form_an_advisory_group():
    slides = [{"id": f"s{i}", "kind": "content", "section": "K1", "headline": h,
               "proposition": {"statement": h, "role": "diagnosis", "claim_type": "driver", "evidence_ids": ["E"]}}
              for i, h in enumerate(["North explains 40% of the gap", "South explains 30% of the gap"])]
    gs = [g for g in detect(deck(slides)) if g["context"] == "headlines"]
    assert len(gs) == 1 and not gs[0]["mandatory"]


def test_repeated_identical_verb_is_advisory_only():
    hard, soft, info = verdict(deck([cards(["Improve pricing to improve margin", "Improve procurement to improve costs",
                                            "Improve operations to improve productivity"])]))
    assert not hard and "PARALLEL_REPEATED_OPENING" in info


def test_punctuation_mismatch_detected():
    _, soft, _ = verdict(deck([cards(["Consolidate suppliers to reduce complexity.", "Automate invoicing to remove manual effort",
                                      "Tighten pricing to protect margin."])]))
    assert "PARALLEL_PUNCTUATION_MISMATCH" in soft


def test_exec_summary_needs_declarative_conclusions_not_identical_syntax():
    def es(items):
        return deck([{"id": "s02", "kind": "exec_summary", "headline": "x", "visual": {"type": "statements", "data": {"items": [{"title": t} for t in items]}}}])

    hard, soft, _ = verdict(es(["Electronics mix drove most of the 1.9 pp margin decline", "Current growth plans would widen the margin gap further",
                                "Repricing electronics can recover ~1.4 pp in 2027"]))
    assert not hard and not soft  # spec §57: past, conditional and modal conclusions are one family
    hard, _, _ = verdict(es(["Margins fell sharply", "Electronics is the main issue", "Need to take pricing action"]))
    hard2, _, _ = verdict(es(["Market", "Financial performance", "Electronics is the main issue"]))
    assert "PARALLEL_SIGNATURE_MISMATCH" in hard | hard2


def test_exec_summary_agenda_is_a_hard_editorial_error():
    spec = deck([{"id": "s02", "kind": "exec_summary", "headline": "Alvora can restore EBITDA by repositioning", "proposition":
                  {"statement": "Alvora can restore EBITDA by repositioning", "role": "implication", "claim_type": "impact", "evidence_ids": ["K1"]},
                  "visual": {"type": "statements", "data": {"items": [{"title": t} for t in ["Market", "Financial performance", "Recommendation"]]}}}],
                 key_line=[{"id": "K1", "message": "Alvora can restore EBITDA by repositioning"}])
    _, rep = compile_editorial(spec, profile={})
    assert any(f["code"] == "EXEC_SUMMARY_AGENDA" and f["level"] == "error" for f in rep["findings"])


def test_key_line_labels_and_parallelism():
    kl = [{"id": "K1", "message": "Margin decline"}, {"id": "K2", "message": "Electronics has become a problem"}, {"id": "K3", "message": "We recommend repricing"}]
    _, rep = compile_editorial(deck([], key_line=kl), profile={})
    assert any(f["code"] == "KEYLINE_TOPIC" and f["level"] == "error" for f in rep["findings"])
    good = [{"id": "K1", "message": "Electronics mix explains most of the margin decline"}, {"id": "K2", "message": "Current growth plans would deepen the margin gap"},
            {"id": "K3", "message": "Repricing electronics can recover most of the lost margin"}]
    hard, soft, _ = verdict(deck([], key_line=good))
    assert not hard and not soft


def test_roadmap_workstreams_and_design_principles():
    gantt = {"id": "s01", "kind": "content", "headline": "x", "visual": {"type": "gantt", "data": {"rows": [
        {"label": "Pricing & promo reset"}, {"label": "Fresh margins"}, {"label": "Cost programme"}]}}}
    hard, soft, _ = verdict(deck([gantt]))
    assert not hard and not soft
    bad = cards(["Customer focused", "Make decisions locally", "Simple", "Scalable organisation"], explicit=False, archetype="design_principles")
    hard, _, _ = verdict(deck([bad]))
    assert "PARALLEL_SIGNATURE_MISMATCH" in hard
    good = cards(["Put customer outcomes at the centre of decisions", "Push accountability to the lowest effective level",
                  "Keep governance simple and explicit", "Scale capabilities without duplicating roles"], explicit=False, archetype="design_principles")
    hard, soft, _ = verdict(deck([good]))
    assert not hard and not soft


def test_scr_executive_summary_is_not_a_sibling_group():
    s = {"id": "s02", "kind": "exec_summary", "headline": "x", "visual": {"type": "statements", "data": {"style": "scr", "items": [
        {"label": "Situation", "title": "Cost-to-serve is 18% above peers"}, {"label": "Complication", "title": "Automation needs capex now"},
        {"label": "Resolution", "title": "Release €22M for wave 2 today"}]}}}
    assert not detect(deck([s]))


def test_meaning_outranks_symmetry_no_member_is_rewritten():
    spec = deck([cards(["Procurement fragmentation", "Automate invoicing to remove manual effort", "Tighten pricing to protect margin"])])
    out, _ = compile_editorial(spec, profile={})
    assert [i["title"] for i in out["slides"][0]["visual"]["data"]["items"]] == [i["title"] for i in spec["slides"][0]["visual"]["data"]["items"]]
