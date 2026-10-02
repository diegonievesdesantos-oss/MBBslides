"""v3.1 proposition fidelity (spec §74, §85, §91): wording may change; numbers, sign, direction, scope, entity,
period, confidence, causal strength and recommendation may not."""
import pytest

from cpe.editorial.action_titles import evaluate

SALES = {"id": "F1", "claim": "Sales 2025 €150m, 2026 €162m; Iberia €60m → €66m, France €90m → €96m", "values": [150, 162, 60, 66, 90, 96]}
BASE = {"statement": "Sales grew 8% in 2026", "role": "observation", "claim_type": "trend", "subject": "sales", "direction": "up",
        "magnitude": "8%", "timeframe": "2026", "evidence_ids": ["F1"], "confidence": "high"}


def hard(headline, **change):
    prop = {**BASE, **change}
    slide = {"id": "s1", "kind": "content", "purpose": "Show sales", "proposition": prop, "evidence": [SALES]}
    return set(evaluate(headline, slide, prop, {"lang": "en"})["hard"])


def test_faithful_paraphrase_passes():
    assert not hard("Sales grew 8% in 2026")
    assert not hard("In 2026 sales rose 8%")


@pytest.mark.parametrize("headline,code", [
    ("Sales fell 8% in 2026", "HEADLINE_DIRECTION_MISMATCH"),                       # sign / direction
    ("Sales changed by 8% in 2026", "HEADLINE_DIRECTION_MISMATCH"),                 # direction dropped in compression
    ("Sales grew 18% in 2026", "HEADLINE_PROPOSITION_MISMATCH"),                    # magnitude
    ("Sales grew 8% in 2025", "HEADLINE_TIMEFRAME_MISMATCH"),                       # time
])
def test_semantic_drift_fails(headline, code):
    assert code in hard(headline)


def test_magnitude_drift_against_the_proposition_even_when_the_number_is_derivable():
    # 10% is derivable (Iberia 60 → 66) but the proposition says 8%: the headline changed the claim
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("Sales grew 10% in 2026")


def test_scope_widened_fails():
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("Sales grew 10% in 2026 in all markets", statement="Iberia sales grew 10% in 2026",
                                                    magnitude="10%", scope="Iberia")
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("Sales grew 10% in 2026", statement="Iberia sales grew 10% in 2026",
                                                    magnitude="10%", scope="Iberia sales")


def test_entity_swapped_fails():
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("France sales grew 10% in 2026", statement="Iberia sales grew 10% in 2026", magnitude="10%")


def test_confidence_overclaimed_fails():
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("Sales grew 8% in 2026", confidence="low")
    assert not hard("Sales may have grown 8% in 2026", confidence="low")


def test_causal_strength_raised_fails():
    assert "HEADLINE_CAUSALITY_UNSUPPORTED" in hard("The loyalty scheme drove the 8% sales growth in 2026",
                                                    statement="Sales grew 8% in 2026, the year the loyalty scheme launched")
    assert not hard("Sales grew 8% in 2026, the year the loyalty scheme launched",
                    statement="Sales grew 8% in 2026, the year the loyalty scheme launched")


def test_observation_turned_into_recommendation_fails():
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("Expand the loyalty scheme to keep sales growing 8% a year")


def test_recommendation_turned_into_decision_fails():
    reco = {"role": "recommendation", "claim_type": "recommendation", "statement": "We recommend expanding the loyalty scheme to Iberia",
            "direction": None, "magnitude": None, "recommended_action": "expand the loyalty scheme"}
    assert not hard("Expand the loyalty scheme to Iberia to sustain sales growth", **reco)
    assert "HEADLINE_PROPOSITION_MISMATCH" in hard("The board has approved the loyalty scheme expansion to Iberia", **reco)


def test_approximation_made_exact_fails():
    prop = {"statement": "The pricing reset would recover about 1.4 pp of margin in 2027", "role": "impact", "claim_type": "impact",
            "subject": "margin", "direction": "up", "magnitude": "~1.4 pp", "timeframe": "2027"}
    ev = {"id": "F1", "claim": "Pricing model: recovery 2027 central 1.4 pp, range 1.2-1.6 pp", "values": [1.2, 1.4, 1.6]}
    slide = {"id": "s1", "kind": "content", "proposition": {**BASE, **prop}, "evidence": [ev]}
    assert "HEADLINE_PROPOSITION_MISMATCH" in evaluate("The pricing reset would recover 1.4 pp of margin in 2027", slide, {**BASE, **prop}, {"lang": "en"})["hard"]
    assert not evaluate("The pricing reset would recover ~1.4 pp of margin in 2027", slide, {**BASE, **prop}, {"lang": "en"})["hard"]


def test_reversed_comparison_fails():
    ev = {"id": "F1", "claim": "Contribution per customer 2026: enterprise €46k, SMB €20k", "values": [46, 20]}
    prop = {"statement": "Enterprise customers generate 2.3 times the contribution of SMB customers", "role": "comparison", "claim_type": "comparison",
            "subject": "contribution per customer", "magnitude": "2.3×", "timeframe": "2026", "evidence_ids": ["F1"], "confidence": "high"}
    slide = {"id": "s1", "kind": "content", "proposition": prop, "evidence": [ev]}
    assert not evaluate("Enterprise customers generate 2.3× the contribution of SMB customers", slide, prop, {"lang": "en"})["hard"]
    assert "HEADLINE_PROPOSITION_MISMATCH" in evaluate("SMB customers generate 2.3× the contribution of enterprise customers", slide, prop, {"lang": "en"})["hard"]


def test_score_never_overrides_a_hard_failure():
    r = evaluate("A new loyalty scheme drove the 8% sales growth in 2026", {"id": "s1", "kind": "content", "evidence": [SALES]}, BASE, {"lang": "en"})
    assert r["score"] >= 50 and not r["passed"]
