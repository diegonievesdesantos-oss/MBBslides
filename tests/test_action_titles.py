"""v3.1 Action Title Engine (spec §84): the headline states the proposition, or the slide fails closed."""
from cpe.editorial import compile_editorial

REV = {"id": "F1", "claim": "Revenue 2025 €200m, 2026 €224m", "values": [200, 224]}
REV_CHART = {"type": "column", "data": {"categories": ["2025", "2026"], "series": [{"name": "Revenue (€m)", "values": [200, 224]}]}}
GROW = {"statement": "Revenue grew 12% in 2026", "role": "observation", "claim_type": "trend", "subject": "revenue", "direction": "up",
        "magnitude": "12%", "timeframe": "2026", "evidence_ids": ["F1"], "confidence": "high"}


def run(headline, prop=GROW, evidence=(REV,), visual=REV_CHART, kind="content", lang="en", mode="mbb_strict", candidates=None, **extra):
    slide = {"id": "s02", "kind": kind, "section": "K1", "purpose": "Show the revenue trend", "headline": headline,
             "evidence": list(evidence), "source": "Accounts", **extra}
    if visual:
        slide["visual"] = visual
    if prop is not None:
        slide["proposition"] = prop
    if candidates:
        slide["headline_candidates"] = candidates
    spec = {"meta": {"title": "T", "language": lang, "editorial_mode": mode, "partial": True},
            "storyline": {"governing_thought": "", "key_line": [{"id": "K1", "message": "Revenue grows"}]}, "slides": [slide]}
    out, rep = compile_editorial(spec, profile={})
    errs = {f["code"] for f in rep["findings"] if f.get("slide") == "s02" and f["level"] == "error"}
    return errs, out["slides"][0], rep


def test_topic_label_rejected():
    errs, _, _ = run("Revenue evolution", prop={**GROW, "claim_type": "driver", "role": "driver"})
    assert "HEADLINE_TOPIC" in errs and "HEADLINE_UNRESOLVED" in errs


def test_complete_conclusion_accepted():
    errs, s, _ = run("Revenue grew 12% in 2026")
    assert not errs and s["_editorial"]["status"] == "passed"


def test_unsupported_number_rejected():
    errs, _, _ = run("Revenue grew 15% in 2026", prop={**GROW, "magnitude": None})
    assert "HEADLINE_NUMBER_UNSUPPORTED" in errs


def test_derived_supported_number_accepted():
    # 224 / 200 − 1 = 12%; €24m = 224 − 200: derivable, not written in the evidence
    errs, _, _ = run("Revenue grew €24m in 2026", prop={**GROW, "magnitude": "€24m"})
    assert not errs


def test_number_more_precise_than_its_proof_rejected():
    # the old lint tolerates ±0.51 on a percentage; a title may not be more precise than its evidence
    errs, _, _ = run("Revenue grew 12.4% in 2026", prop={**GROW, "magnitude": None})
    assert "HEADLINE_NUMBER_UNSUPPORTED" in errs


def test_unsupported_causal_claim_rejected():
    errs, _, _ = run("A new pricing policy drove 12% revenue growth in 2026")
    assert "HEADLINE_CAUSALITY_UNSUPPORTED" in errs


def test_supported_causal_claim_accepted():
    prop = {**GROW, "role": "driver", "claim_type": "causal", "driver": "the new pricing policy",
            "statement": "The new pricing policy caused the 12% revenue growth of 2026 (randomised test)"}
    errs, _, _ = run("The new pricing policy drove the 12% revenue growth in 2026", prop=prop)
    assert not errs


def test_associative_wording_on_correlation_accepted():
    errs, _, _ = run("Revenue grew 12% in 2026, the year the new pricing policy started", prop={**GROW, "statement": "Revenue grew 12% in 2026 while the pricing policy changed"})
    assert "HEADLINE_CAUSALITY_UNSUPPORTED" not in errs


def test_direction_reversal_rejected():
    errs, _, _ = run("Revenue fell 12% in 2026")
    assert "HEADLINE_DIRECTION_MISMATCH" in errs


def test_timeframe_drift_rejected():
    errs, _, _ = run("Revenue grew 12% in 2025")
    assert "HEADLINE_TIMEFRAME_MISMATCH" in errs


def test_entity_drift_rejected():
    ev = {"id": "F1", "claim": "Churn 2026: North 9.4%, Central 7.2%, South 5.1%", "values": [9.4, 7.2, 5.1]}
    prop = {"statement": "The northern region has the highest churn at 9.4%", "role": "comparison", "claim_type": "comparison",
            "subject": "churn", "magnitude": "9.4%", "timeframe": "2026", "evidence_ids": ["F1"], "confidence": "high"}
    errs, _, _ = run("The southern region has the highest churn at 9.4%", prop=prop, evidence=(ev,), visual=None)
    assert "HEADLINE_PROPOSITION_MISMATCH" in errs


def test_two_governing_messages_rejected():
    errs, _, _ = run("Revenue grew 12% in 2026 and the board should replace the regional sales director")
    assert "HEADLINE_TWO_GOVERNING_MESSAGES" in errs


def test_vague_unquantified_claim_flagged():
    _, _, rep = run("Revenue grew significantly in 2026", prop={**GROW, "magnitude": None})
    assert any(f["code"] == "HEADLINE_VAGUE" and f["level"] == "warning" for f in rep["findings"])


def test_question_headline_flagged():
    _, s, rep = run("Did revenue grow 12% in 2026?")
    assert any(f["code"] == "HEADLINE_QUESTION" for f in rep["findings"]) and s["_editorial"]["headline_score"] < 100


def test_recommendation_without_recommendation_proposition_rejected():
    ev = {"id": "F1", "claim": "NPV: A €42m, B €38m, C €21m", "values": [42, 38, 21]}
    prop = {"statement": "Option A has the highest NPV of the three options at €42m", "role": "comparison", "claim_type": "comparison",
            "subject": "NPV", "magnitude": "€42m", "evidence_ids": ["F1"], "confidence": "high"}
    errs, _, _ = run("Choose Option A, which has the highest NPV at €42m", prop=prop, evidence=(ev,), visual=None)
    assert "HEADLINE_PROPOSITION_MISMATCH" in errs


def test_comparison_without_comparison_evidence_rejected():
    ev = {"id": "F1", "claim": "Revenue 2026 €224m", "value": 224}
    prop = {**GROW, "magnitude": None, "statement": "Revenue reached €224m in 2026", "claim_type": "comparison"}
    errs, _, _ = run("Revenue reached €224m in 2026, the highest in the sector", prop=prop, evidence=(ev,), visual=None)
    assert "HEADLINE_COMPARISON_UNSUPPORTED" in errs


def test_spanish_topic_label_rejected():
    prop = {**GROW, "statement": "Las ventas crecieron un 12% en 2026", "subject": "ventas", "role": "driver", "claim_type": "driver"}
    errs, _, _ = run("Evolución de ventas", prop=prop, lang="es")
    assert "HEADLINE_TOPIC" in errs


def test_spanish_conclusion_accepted():
    prop = {**GROW, "statement": "Las ventas crecieron un 12% en 2026", "subject": "ventas"}
    errs, _, _ = run("Las ventas crecieron un 12% en 2026", prop=prop, lang="es")
    assert not errs


def test_english_conclusion_accepted():
    errs, _, _ = run("Revenue grew 12% in 2026 to €224m")
    assert not errs


def test_mixed_language_rejected():
    errs, _, _ = run("Repricing electrónica unlocks 12% de crecimiento en 2026", lang="es")
    assert "HEADLINE_LANGUAGE_MISMATCH" in errs


def test_cover_exempt():
    errs, s, _ = run("Market overview", kind="cover", prop=None)
    assert not errs and s["_editorial"]["exempt"]


def test_divider_exempt():
    errs, s, _ = run("Financial performance", kind="divider", prop=None)
    assert not errs and s["_editorial"]["status"] == "exempt"


def test_strict_slide_without_proposition_fails_and_standard_infers():
    errs, _, _ = run("Revenue grew 12% in 2026", prop=None)
    assert "PROPOSITION_MISSING" in errs
    errs, s, rep = run("Revenue grew 12% in 2026", prop=None, mode="standard")
    assert not errs and s["_editorial"]["proposition"] == "inferred"
    assert any(f["code"] == "PROPOSITION_INFERRED" and f["level"] == "info" for f in rep["findings"])


def test_candidate_selection_prefers_the_faithful_candidate():
    errs, s, _ = run("Revenue evolution", candidates=["Revenue grew 15% in 2026", "Revenue grew 12% in 2026"],
                     prop={**GROW, "role": "driver", "claim_type": "driver"})
    assert not errs and s["headline"] == "Revenue grew 12% in 2026" and s["_editorial"]["selected_origin"] == "candidate[1]"


def test_deterministic_rewrite_only_when_the_proposition_fixes_it():
    errs, s, rep = run("Revenue decline", prop={**GROW, "statement": "Revenue declined 12% in 2026", "direction": "decline", "magnitude": "12%"},
                       evidence=({"id": "F1", "claim": "Revenue 2025 €224m, 2026 €197m", "values": [224, 197]},), visual=None)
    assert not errs and s["headline"] == "Revenue declined 12% in 2026"
    assert any(f["code"] == "HEADLINE_SELECTED" for f in rep["findings"])
    # never invents a cause, and never papers over a contradiction
    errs, s, _ = run("Revenue fell 12% in 2026")
    assert "HEADLINE_DIRECTION_MISMATCH" in errs and s["headline"] == "Revenue fell 12% in 2026"


def test_purpose_is_not_a_headline():
    errs, _, _ = run("Explain the causes of the revenue growth")
    assert "HEADLINE_TOPIC" in errs


def test_kpi_label_rejected():
    errs, _, _ = run("2026 Revenue", prop={**GROW, "role": "driver", "claim_type": "driver"})
    assert "HEADLINE_TOPIC" in errs
