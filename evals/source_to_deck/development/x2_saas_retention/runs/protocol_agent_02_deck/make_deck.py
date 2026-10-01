import json
sl = json.load(open('/tmp/s2d_deck/saas/work/storyline.json'))
dp = {s['id']: s for s in json.load(open('/tmp/s2d_deck/saas/work/deck_plan.json'))['slides']}
def ev(*ids): return [{"fact": i, "claim": i} for i in ids]
SRC_ARR = "Source: ARR bridge 2024-25 (arr_bridge.csv); team analysis"
slides = []
slides.append({"id": "S1", "kind": "cover", "title": dp['S1']['headline'],
  "subtitle": "Board discussion: why ARR growth slowed and where the 2026 budget should go"})
slides.append({"id": "S2", "kind": "exec_summary", "tracker": "Executive summary",
  "purpose": dp['S2']['purpose'], "headline": dp['S2']['headline'],
  "evidence": ev("C0003", "C0025", "F0058", "C0007", "C0020", "C0028", "C0029", "F0047", "F0063"),
  "visual": {"type": "statements", "style": "scr", "data": {"style": "numbered", "items": [
    {"title": "Churn, not sales, broke growth", "text": "Net new ARR fell €5.6M to €4.8M; higher churn explains 80.4% while pipeline grew 18.0%."},
    {"title": "The leak is in first-year customers", "text": "First-year churn rose from 12% to 26% after a €0.8M onboarding cut, costing €2.5M of ARR."},
    {"title": "The 30-AE plan does not hold", "text": "With a 9-month ramp, 30 AEs yield at most an estimated €4.5M in 2026, not €9M."},
    {"title": "Retention first closes most of the gap for less", "text": "Onboarding plus 10 AEs: an estimated €2.0M a year for up to €5.3M of the €5.6M; AE wave 2 gated in June."}]}},
  "source": "Source: ARR bridge, CRM export, board pack Q4 2025, customer success notes; team analysis. Estimates rest on assumptions A001-A003"})
slides.append({"id": "S3", "section": "K1", "tracker": "Diagnosis: ARR bridge",
  "purpose": dp['S3']['purpose'], "headline": dp['S3']['headline'], "message_type": "change_bridge",
  "supporting_message": "Churn and expansion broke the bridge; acquisition held",
  "evidence": ev("C0001", "C0002", "C0003", "C0004", "C0005", "C0006", "C0007", "F0002", "F0006", "F0008", "F0012", "F0003", "F0009", "F0004", "F0010", "F0005", "F0011"),
  "visual": {"type": "waterfall", "title": "Net new ARR bridge, 2024 to 2025", "unit": "€M",
    "format": {"decimals": 1}, "highlight": ["Higher churn"], "delta_colors": "neutral",
    "data": {"steps": [
      {"label": "Net new ARR 2024", "value": 10.4, "type": "total"},
      {"label": "More new-logo ARR", "value": 0.2},
      {"label": "Less expansion", "value": -1.3},
      {"label": "Higher churn", "value": -4.5},
      {"label": "Net new ARR 2025", "type": "total"}]}},
  "commentary": {"title": "Churn, not acquisition, broke the bridge", "points": [
    "**Churn (−€4.5M), 80.4% of the fall:** churned ARR more than doubled, from €3.3M to €7.8M",
    "**Expansion (−€1.3M):** fell from €4.3M to €3.0M; cause not yet established",
    "**New logos (+€0.2M):** €9.4M to €9.6M; acquisition held up"]},
  "source": SRC_ARR})
slides.append({"id": "S4", "section": "K1", "tracker": "Diagnosis: sales engine",
  "purpose": dp['S4']['purpose'], "headline": dp['S4']['headline'], "message_type": "comparison",
  "supporting_message": "The CRO's price-competitor diagnosis is not what the funnel and the exit interviews show",
  "evidence": ev("C0012", "C0013", "C0014", "C0015", "C0016", "C0026", "F0015", "F0019", "F0043", "F0064", "C0017", "C0018", "F0054"),
  "kpis": {"items": [
    {"value": "+18.0%", "label": "Pipeline created, €38.9M to €45.9M (2024 to 2025)", "trend": "up", "good": "up"},
    {"value": "175 → 193", "label": "Deals won, 2024 to 2025", "trend": "up", "good": "up"},
    {"value": "23-25%", "label": "Quarterly win rate, stable through 2024-25", "trend": "flat"}]},
  "visual": {"type": "bar", "title": "Reasons given by churned customers, 2025 exit interviews (n=64)", "unit": "% of churned customers",
    "highlight": ["Never fully implemented"], "sort": "desc", "format": {"decimals": 0, "suffix": "%"},
    "data": {"categories": ["Never fully implemented", "Moved to a competitor", "Price"],
             "series": [{"name": "Share", "values": [58, 17, 14]}]}},
  "takeaway": "Price pressure is real but marginal: new ARR per deal slipped from €53.7k to €49.7k; price is 34% of lost deals",
  "source": "Source: CRM export, funnel and lost-deals sheets (crm_export.xlsx); customer success notes (customer_success_notes.md); team analysis"})
slides.append({"id": "S5", "section": "K2", "tracker": "Cause: where the leak is",
  "purpose": dp['S5']['purpose'], "headline": dp['S5']['headline'], "message_type": "comparison",
  "evidence": ev("F0047", "F0063", "C0011", "C0010", "F0050", "F0046", "F0052", "F0049"),
  "exhibits": [
    {"type": "column", "title": "Churn rate by customer tenure", "unit": "% of opening ARR",
     "highlight": ["First-year 2025"], "format": {"decimals": 0, "suffix": "%"},
     "data": {"categories": ["First-year 2024", "First-year 2025", "Mature 2025"], "series": [{"name": "Churn rate", "values": [12, 26, 9]}]}},
    {"type": "bar", "title": "Churned ARR by tenure, 2025", "unit": "€M",
     "highlight": ["First-year customers"], "format": {"decimals": 1},
     "data": {"categories": ["First-year customers", "Mature customers"], "series": [{"name": "Churned ARR", "values": [4.7, 3.1]}]}}],
  "takeaway": "First-year customers supplied €4.7M of the €7.8M churned (60.3%): the leak is in onboarding, not in the mature base",
  "source": "Source: CRM export, cohorts sheet (crm_export.xlsx); customer success notes (customer_success_notes.md)",
  "footnotes": ["First-year = onboarded in the previous 12 months; mature = customers for more than 12 months. No 2024 rate is available for mature customers"]})
slides.append({"id": "S6", "section": "K2", "tracker": "Cause: onboarding cut",
  "purpose": dp['S6']['purpose'], "headline": dp['S6']['headline'], "message_type": "sequence",
  "evidence": ev("F0061", "F0062", "F0064", "C0008", "C0009", "F0045", "F0046", "F0063"),
  "visual": {"type": "process", "highlight": [3], "data": {"steps": [
    {"title": "Onboarding team cut", "text": "February 2025, to save €0.8M a year", "metric": "14 → 6", "metric_label": "onboarding staff"},
    {"title": "Customers wait longer", "text": "Median time to first value, 2024 to 2025", "metric": "21 → 48", "metric_label": "days"},
    {"title": "Customers don't go live", "text": "Of 64 churned customers in 2025 exit interviews", "metric": "58%", "metric_label": "never fully implemented"},
    {"title": "First-year churn spikes", "text": "€4.7M churned vs €2.2M at the 2024 rate of 12%", "metric": "€2.5M", "metric_label": "excess ARR lost"}]}},
  "takeaway": "Restoring the team is lever L1; causality is inferred from timing and exit interviews, not a controlled test",
  "source": "Source: customer success notes (customer_success_notes.md); CRM export, cohorts sheet (crm_export.xlsx); team analysis"})
slides.append({"id": "S7", "section": "K3", "tracker": "Current plan test",
  "purpose": dp['S7']['purpose'], "headline": dp['S7']['headline'], "message_type": "comparison",
  "evidence": ev("F0058", "F0065", "C0019", "C0020", "C0021", "C0022", "A001"),
  "visual": {"type": "waterfall", "title": "2026 new ARR from 30 AEs hired in Q1 2026", "unit": "€M",
    "format": {"decimals": 1}, "highlight": ["9-month ramp"], "delta_colors": "neutral",
    "data": {"steps": [
      {"label": "CRO promise (no ramp)", "value": 9.0, "type": "total"},
      {"label": "9-month ramp", "value": -4.5},
      {"label": "Estimate, upper bound", "type": "total"}]}},
  "commentary": {"title": "Why €9M does not hold", "points": [
    "**€9M = 30 AEs × €300k × 12 months:** every AE fully productive from day one",
    "**Ramp:** a Q1 hire gives about 6 productive months in 2026 (our assumption, note 1)",
    "**Cost:** €3.6M a year fully loaded, €0.12M per AE",
    "**Validate:** ramp of the 2025 AE hires before any offer letter"]},
  "source": "Source: board pack Q4 2025 (board_pack_Q4_2025.pdf); customer success notes (customer_success_notes.md); team estimate",
  "footnotes": ["Estimate: A001 assumes a mid-February start and a linear 9-month ramp (6 productive months in 2026); €4.5M is an upper bound"]})
slides.append({"id": "S8", "section": "K4", "tracker": "Options",
  "purpose": dp['S8']['purpose'], "headline": dp['S8']['headline'], "message_type": "comparison",
  "evidence": ev("C0025", "C0027", "C0009", "C0005", "C0023", "C0028", "C0029", "C0003", "F0002", "F0006", "F0008", "F0012", "F0004", "F0010", "F0045", "F0046", "F0058", "F0061", "C0024", "C0020", "A001", "A002", "A003"),
  "exhibits": [
    {"type": "table", "title": "Options, costed on the same annual basis",
     "columns": [{"label": "Option", "width": 2.4}, {"label": "€M a year", "align": "right", "width": 1.0},
                 {"label": "2026 ARR effect, €M", "align": "right", "width": 1.4}, {"label": "Fixes leak", "width": 0.9}],
     "rows": [
       ["Keep CRO plan: 30 AEs in Q1", "3.6", "≤4.5, new logos only", "No"],
       {"cells": ["Retention first: onboarding + 10 AEs, wave 2 gated", "2.0 (est.)", "≤5.3", "Yes"], "style": "highlight"},
       ["Onboarding only, no new AEs", "0.8", "≤2.5 + ≤1.3, no new logos", "Yes"]]},
    {"type": "waterfall", "title": "Retention-first levers vs the €5.6M needed", "unit": "€M, upper bounds",
     "format": {"decimals": 1}, "highlight": ["Gap"], "delta_colors": "neutral",
     "data": {"steps": [
       {"label": "Onboarding (L1)", "value": 2.5},
       {"label": "Expansion (L2)", "value": 1.3},
       {"label": "10 AEs (L3)", "value": 1.5},
       {"label": "Identified", "type": "subtotal"},
       {"label": "Gap", "value": 0.3},
       {"label": "Needed", "type": "total"}]}}],
  "takeaway": "Retention first frees an estimated €1.6M a year versus the CRO plan, held as a gated reserve for AE wave 2",
  "source": "Source: board pack Q4 2025 (board_pack_Q4_2025.pdf); ARR bridge (arr_bridge.csv); customer success notes; team estimates",
  "footnotes": ["Upper bounds: L1 assumes a 2026 first-year cohort like 2025's (A002); L3 a linear ramp (A001) and a 10-AE wave (A003). Needed = back to 2024 net new ARR (inferred)"]})
slides.append({"id": "S9", "section": "K4", "tracker": "Decisions",
  "purpose": dp['S9']['purpose'], "headline": dp['S9']['headline'], "message_type": "recommendation",
  "evidence": ev("F0058", "A003", "F0061", "C0027", "F0063", "C0024", "F0062", "F0047", "C0001"),
  "visual": {"type": "table", "title": "Decisions requested today",
     "columns": [{"label": "Decision", "width": 3.4}, {"label": "Owner"}, {"label": "€M a year", "align": "right"}, {"label": "When"}],
     "rows": [
       ["Reject the 30-AE plan as proposed", "Board", "3.6", "Today"],
       ["Approve restoring onboarding to 14 people", "CEO / VP CS", "0.8", "Q1 2026"],
       ["Approve a first wave of 10 AEs (our sizing)", "CRO", "1.2 (est.)", "Q1 2026"],
       ["Hold the rest as reserve for AE wave 2", "CFO", "1.6 (est.)", "June 2026 gate"]]},
  "commentary": {"title": "Gate and KPIs", "points": [
    "**Gate (June 2026 board):** first-year churn ≤12% and time to first value ≤21 days release wave 2",
    "**Monthly:** first-year churn (from 26%), time to first value (from 48 days), new ARR per AE vs ramp",
    "**Quarterly:** net new ARR back to the €10.4M of 2024"]},
  "source": "Source: board pack Q4 2025 (board_pack_Q4_2025.pdf); customer success notes; team sizing (A003)"})
deck = {"meta": {"title": dp['S1']['headline'], "subtitle": "Board discussion", "client": "B2B SaaS company",
                 "date": "Q1 2026", "deck_type": "board_presentation", "theme": "meridian", "confidentiality": "Board confidential"},
        "storyline": {"framework": "SCR", "audience": "CEO, CFO and Board",
                      "decision_sought": "Approve the 2026 growth investment (the CRO proposes hiring 30 account executives)",
                      "governing_thought": sl['governing_thought'],
                      "key_line": [{"id": k['id'], "role": k['role'], "message": k['message']} for k in sl['key_line']]},
        "slides": slides}
json.dump(deck, open('/tmp/s2d_deck/saas/work/deck.json', 'w'), indent=2, ensure_ascii=False)
print("ok")
