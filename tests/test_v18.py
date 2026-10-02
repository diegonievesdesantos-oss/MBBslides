"""v1.8 — corporate & real-world generalisation (deterministic parts)."""

from cpe.reasoning.facts import build_fact_model, detect_period
from cpe.reasoning.periods import compare, period_info


def test_period_semantics():
    assert period_info("FY2025") == {"kind": "FY", "months": 12, "year": 2025, "fiscal": True}
    assert period_info("2025-Q3")["months"] == 3 and period_info("LTM")["months"] == 12 and period_info("2025-11")["kind"] == "MONTH"
    assert detect_period("Ventas 2025-11") == {"period": "2025-11", "basis": "actual"}
    assert detect_period("últimos doce meses")["period"] == "LTM" and detect_period("EBITDA auditado 2025")["basis"] == "audited"
    assert compare({"period": "LTM"}, {"period": "2025-Q3"}) and compare({"period": "YTD"}, {"period": "2025"})
    assert compare({"period": "2026", "basis": "budget"}, {"period": "2026", "basis": "actual"})
    assert compare({"period": "RUN-RATE"}, {"period": "2025"}) and compare({"period": "FY2025"}, {"period": "2025"})
    assert compare({"period": "2024"}, {"period": "2025"}) is None


def test_period_mismatch_in_formulas_is_a_warning_unless_acknowledged():
    from cpe.reasoning.checks import check_computed
    facts = {"F0001": {"id": "F0001", "values": [{"value": 100, "unit": "EUR_M", "period": "LTM"}]},
             "F0002": {"id": "F0002", "values": [{"value": 30, "unit": "EUR_M", "period": "2025-Q3"}]}}
    issues, good = check_computed({"facts": [{"id": "C0001", "formula": "F0001 - F0002", "values": [{"value": 70}]}]}, facts)
    assert [(i["code"], i["level"], i["hard"]) for i in issues] == [("PERIOD_MISMATCH", "warning", False)] and "C0001" in good
    ok, _ = check_computed({"facts": [{"id": "C0002", "formula": "F0001 - F0002", "values": [{"value": 70}], "periods_ok": "deliberate"}]}, facts)
    assert ok == []


def test_conflict_types():
    from cpe.reasoning.conflicts import detect_conflicts

    def tx(i, claim, v, basis=None, file="a.md"):
        return {"id": i, "fact_type": "text_statement", "claim": claim, "source": {"file": file},
                "values": [{"value": v, "unit": "EUR_M", "period": "2025", "basis": basis}]}

    c = detect_conflicts([tx("F1", "El EBITDA de gestión 2025 fue 12 M€", 12, "management"), tx("F2", "El EBITDA auditado 2025 fue 10 M€", 10, "audited", "b.pdf")])
    assert [x["type"] for x in c] == ["management_vs_audited"]
    c = detect_conflicts([tx("F1", "El EBITDA del grupo 2025 fue 12 M€", 12), tx("F2", "El EBITDA de la filial España 2025 fue 9 M€", 9, file="b.pdf")])
    assert [x["type"] for x in c] == ["definition_mismatch"]


def test_two_level_headers_scenarios_and_totals(tmp_path):
    (tmp_path / "t.csv").write_text("Línea,2024,,2025,\n,Real,Presupuesto,Real,Presupuesto\nVentas,100,110,120,125\nTotal,40,48,50,54\n", encoding="utf-8")
    fs = [f for f in build_fact_model([tmp_path / "t.csv"])["facts"] if f["fact_type"] == "table_value"]
    got = {(f["values"][0]["label"], f["values"][0]["period"], f["values"][0]["basis"]): f["values"][0]["value"] for f in fs}
    assert got[("Ventas", "2024", "budget")] == 110 and got[("Ventas", "2025", "actual")] == 120
    assert all(f["values"][0].get("row_kind") == "total" for f in fs if f["values"][0]["label"] == "Total")


def test_chart_data_in_excel_and_word_sources(tmp_path):
    import openpyxl
    from openpyxl.chart import BarChart, Reference

    from cpe.ingest.readers import ingest
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Región", "Ventas"])
    for r in (["Norte", 12.5], ["Sur", 9.25], ["Este", 7]):
        ws.append(r)
    ch = BarChart()
    ch.title = "Ventas por región"
    ch.add_data(Reference(ws, min_col=2, min_row=1, max_row=4), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=4))
    ws.add_chart(ch, "D2")
    wb.save(tmp_path / "c.xlsx")
    charts = [t for t in ingest([tmp_path / "c.xlsx"])["tables"] if t["loc"].startswith("chart")]
    assert charts and charts[0]["header"] == ["Ventas por región", "Ventas"] and charts[0]["rows"][1] == ["Sur", 9.25]


def _old_deck(path):
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt

    prs = Presentation()
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    tb = s.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
    tb.text_frame.text = "Plan de crecimiento 2025"
    s = prs.slides.add_slide(blank)
    tb = s.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(1))
    tb.text_frame.text = "Las ventas crecieron hasta 120 M€ con un margen del 18%"
    tb.text_frame.paragraphs[0].runs[0].font.size = Pt(24)
    cd = CategoryChartData()
    cd.categories = ["Norte", "Sur"]
    cd.add_series("Ventas", (70, 50))
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(2), Inches(6), Inches(4), cd)
    prs.save(str(path))


def test_existing_deck_ingest_and_update_plan(tmp_path):
    from cpe.reasoning.deck_update import ingest_deck, to_spec, update_plan
    _old_deck(tmp_path / "old.pptx")
    inv = ingest_deck(tmp_path / "old.pptx")
    assert [s["role"] for s in inv["slides"]] == ["title", "content"]
    assert inv["slides"][1]["headline"].startswith("Las ventas crecieron") and inv["slides"][1]["exhibits"][0]["type"] == "column"
    spec = to_spec(inv)
    assert spec["slides"][1]["visual"]["data"]["series"][0]["values"] == [70, 50]
    # v1.9 (U1): a number matches on two words of its own (not one shared word), so the facts say what they are about
    facts = [{"id": "F1", "claim": "Las ventas crecieron hasta 135 M€ en 2026", "values": [{"value": 135, "unit": "EUR_M"}]},
             {"id": "F2", "claim": "Margen bruto 2026 del 18%", "values": [{"value": 18, "unit": "PCT"}]},
             {"id": "F3", "claim": "Ventas Norte 2026: 70", "values": [{"value": 70, "unit": ""}]}]
    plan = update_plan(inv, facts)
    st = {q["raw"]: q["status"] for q in plan["slides"][1]["numbers"]}
    assert st["18%"] == "untraced" and st["70"] == "current" and st["50"] == "untraced"  # v1.9: "margen" alone is one shared word
    outdated = [q for q in plan["slides"][1]["numbers"] if q["status"] == "outdated"]
    assert outdated and outdated[0]["fact"] == "F1" and plan["slides"][1]["action"] == "update"


def test_waterfall_is_rebuilt_from_stacked_columns():
    from cpe.reasoning.deck_update import _waterfall_steps
    ex = {"categories": ["2024", "Precio", "Volumen", "2025"],
          "series": [{"name": "Base", "values": [0, 100, 90, 0]}, {"name": "Total", "values": [100, 0, 0, 110]},
                     {"name": "Increase", "values": [0, 20, 0, 0]}, {"name": "Decrease", "values": [0, 0, 10, 0]}]}
    assert _waterfall_steps(ex) == [{"label": "2024", "value": 100.0, "type": "total"}, {"label": "Precio", "value": 20.0},
                                    {"label": "Volumen", "value": -10.0}, {"label": "2025", "value": 110.0, "type": "total"}]


def test_cell_to_fact_binding():
    from cpe.reasoning.checks import factcheck_deck
    facts = {"F1": {"id": "F1", "claim": "Ventas Norte 2025: 70,4 M€", "values": [{"value": 70.4, "unit": "EUR_M"}]},
             "F2": {"id": "F2", "claim": "Ventas Sur 2025: 50,2 M€", "values": [{"value": 50.2, "unit": "EUR_M"}]}}
    def deck(rows, ev):
        return {"slides": [{"id": "s1", "headline": "Norte vende más que Sur", "evidence": ev,
                            "visual": {"type": "table", "columns": [{"label": "Región"}, {"label": "Ventas (M€)"}], "rows": rows}}]}
    ok = factcheck_deck(deck([["Norte", 70.4], ["Sur", 50.2]], [{"fact": "F1"}, {"fact": "F2"}]), facts)
    assert not [i for i in ok if i["code"] == "CELL_MISBOUND"]
    swapped = factcheck_deck(deck([["Norte", 50.2], ["Sur", 70.4]], [{"fact": "F1"}, {"fact": "F2"}]), facts)
    warn = [i for i in swapped if i["code"] == "CELL_MISBOUND"]
    assert len(warn) == 2 and not any(i["hard"] for i in warn)
    hard = factcheck_deck(deck([["Norte", 50.2], ["Sur", 70.4]], [{"fact": "F1", "at": "visual.rows[0][1]"}, {"fact": "F2", "at": "visual.rows[1][1]"}]), facts)
    assert sum(i["code"] == "CELL_MISBOUND" and i["hard"] for i in hard) == 2
    good = factcheck_deck(deck([["Norte", 70400], ["Sur", 50.2]], [{"fact": "F1", "at": "visual.rows[0][1]"}, {"fact": "F2", "at": ["visual.rows[1][1]"]}]), facts)
    assert not [i for i in good if i["code"] in ("CELL_MISBOUND", "BINDING_PATH_MISSING")]
    missing = factcheck_deck(deck([["Norte", 70.4]], [{"fact": "F1", "at": "visual.rows[3][1]"}]), facts)
    assert [i for i in missing if i["code"] == "BINDING_PATH_MISSING" and i["hard"]]


def test_cause_effect_decisions_timeline_and_na_cells(tmp_path):
    import json

    from pptx import Presentation

    from cpe.charts.numfmt import NA, is_na
    from cpe.core.planner import plan
    from cpe.pptx.builder import build
    from cpe.tables.table import _cell_text, _norm_rows
    spec = {"meta": {"title": "T", "language": "es"}, "slides": [
        {"id": "s1", "purpose": "diagnose", "headline": "El margen cae por tres causas que se refuerzan y obligan a actuar ya",
         "visual": {"type": "cause_effect", "data": {"causes": [{"label": "Coste", "link": "encarece"}, {"label": "Descuentos"}],
                                                     "effect": {"label": "Margen -4 pp"}, "consequences": [{"label": "Caja"}]}}},
        {"id": "s2", "purpose": "decide", "headline": "Tres decisiones hoy desbloquean el plan con hitos entre enero y junio",
         "visual": {"type": "timeline", "data": {"events": [{"date": "Ene", "text": "A"}, {"date": "Mar", "text": "B"}]}},
         "exhibits": [{"type": "table", "columns": ["Decisión", "Impacto"], "rows": [["A", 4.5], ["B", "n/a"]]}]},
        {"id": "s3", "purpose": "inform", "headline": "Ventas por región con el Sur todavía sin reportar",
         "visual": {"type": "column", "data": {"categories": ["N", "S"], "series": [{"name": "V", "values": [70.4, "n/d"]}]}}}]}
    res, _ = plan(json.loads(json.dumps(spec)))
    lay = {s["id"]: s["_plan"]["layout"]["id"] for s in res["slides"]}
    assert lay["s1"].startswith("process") and lay["s2"] == "timeline_decisions"
    build(res, tmp_path / "d.pptx")
    texts = [sh.text_frame.text for sl in Presentation(str(tmp_path / "d.pptx")).slides for sh in sl.shapes if sh.has_text_frame]
    assert sum(t == "n/d" for t in texts) == 1  # the chart's missing point (the table cell is in a table shape)
    rows = _norm_rows({"rows": [["B", "n/a"], ["C", {"value": None, "na": True}]]})
    assert rows[0]["cells"][1] is NA and rows[1]["cells"][1] is NA and is_na("No disponible")
    assert _cell_text(NA, {"kind": "number"}) == "n/a"  # outside a build the locale is English


def test_corporate_usage_and_brand_fidelity(tmp_path):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches

    from conftest import content_slide, mini_spec
    from cpe.brand.fidelity import brand_fidelity, corporate_usage
    from cpe.brand.fixtures import make_multimaster
    from cpe.brand.ingest import ingest
    from cpe.core.planner import plan
    from cpe.design.tokens import theme_for
    from cpe.pptx.builder import build
    ingest(make_multimaster(tmp_path / "mm.pptx"), tmp_path / "brand", name="Synthetic")
    spec = mini_spec([content_slide(id="s1"), {"id": "d1", "kind": "divider", "title": "Where the market is going"}])
    spec["slides"].insert(0, {"id": "c1", "kind": "cover", "title": "Brand test"})
    spec["meta"]["brand"] = str(tmp_path / "brand")
    res, _ = plan(spec)
    man = build(res, tmp_path / "deck.pptx")
    u = corporate_usage(man, res)
    assert {r["slide"]: r["mode"] for r in u["slides"]} == {"c1": "native", "s1": "adaptive", "d1": "native"}
    theme = theme_for(res["meta"])
    f = brand_fidelity(tmp_path / "deck.pptx", theme, man, [], res)
    assert f["structural_slides"]["value"] == 1.0 and f["typography"]["value"] == 1.0 and f["layout_family_appropriateness"]["value"] is None
    # an off-brand font and colour, outside the margins, are reported, each in its own dimension
    prs = Presentation(str(tmp_path / "deck.pptx"))
    tb = prs.slides[1].shapes.add_textbox(Inches(0.02), Inches(3), Inches(3), Inches(1))
    tb.text_frame.text = "Comic text"
    run = tb.text_frame.paragraphs[0].runs[0]
    run.font.name = "Comic Sans MS"
    run.font.color.rgb = RGBColor(0xFF, 0x00, 0xCC)
    prs.save(str(tmp_path / "bad.pptx"))
    g = brand_fidelity(tmp_path / "bad.pptx", theme, man, [{"code": "BRAND_RESERVED_OVERLAP", "slide": "s1", "message": "x"}], res)
    assert g["typography"]["value"] < 1 and "Comic Sans MS" in g["typography"]["misses"][0]
    assert any("FF00CC" in m for m in g["palette"]["misses"]) and g["grid"]["misses"] and g["artwork_protection"]["value"] == 1


def test_protocol_15_rules():
    from cpe.reasoning import PROTOCOL_VERSION
    from cpe.reasoning.rules15 import check_assumptions_in_summary, check_decision_15, check_discarded, check_partner_checklist, check_rejected_revived
    assert PROTOCOL_VERSION == "1.5"
    # R1 + R2: no contingency, a gate without margin and too short, no renegotiate / defer option
    sl = {"decision": {"options": [{"id": "O1", "statement": "Aprobar hoy al precio de la oferta", "cost_components": {"inversion": 2616}},
                                   {"id": "O2", "statement": "Aprobar con prueba", "cost_components": {"inversion": 2616}}],
                       "gates": [{"statement": "Prueba", "criterion": "2,1x", "threshold": 2.1, "break_even": 2.09, "period_weeks": 4}]}}
    codes = {i["code"] for i in check_decision_15(sl)}
    assert {"CONTINGENCY_MISSING", "GATE_NO_MARGIN", "GATE_SHORT_TEST", "OPTION_RENEGOTIATE_MISSING", "OPTION_DEFER_MISSING"} <= codes
    good = {"decision": {"options": [{"id": "O1", "kind": "approve", "cost_components": {"inversion": 2616, "contingencia": 262}},
                                     {"id": "O2", "kind": "renegotiate", "cost_components": {"inversion": 2182, "contingencia": 218}},
                                     {"id": "O3", "kind": "defer", "cost_components": {"inversion": 2616, "contingencia": 262}}],
                         "gates": [{"statement": "Decisión", "threshold": 2.2, "break_even": 2.0, "period_weeks": 8}]}}
    assert not check_decision_15(good)
    # R3: a fact set aside as unrepresentative may not support a later claim
    ins = {"insights": [{"id": "I1", "facts": ["F1", "F2"], "discards": ["F2"]}, {"id": "I6", "facts": ["F3", "F2"]}]}
    deck = {"slides": [{"id": "s04", "evidence": [{"fact": "F2", "as_discarded": True}]}, {"id": "s08", "evidence": [{"fact": "F2"}]}]}
    refs = {i["ref"] for i in check_discarded(ins, deck)}
    assert refs == {"I6", "s08"}
    # R4: an assumption-only number in the summary; a rejected hypothesis revived as a risk
    facts = {"F1": {"id": "F1", "claim": "Precio", "values": [{"value": 2396, "unit": "EUR_K"}]},
             "C1": {"id": "C1", "claim": "Coste de aplazar", "values": [{"value": 237, "unit": "EUR_K"}], "fact_type": "computed", "rests_on_assumptions": ["A001"]}}
    deck = {"slides": [{"id": "s02", "kind": "exec_summary", "headline": "Aplazar costaría 237 k€", "evidence": [{"fact": "C1"}, {"fact": "F1"}]}]}
    assert [i["code"] for i in check_assumptions_in_summary(deck, facts)] == ["ASSUMPTION_IN_SUMMARY"]
    sl = {"decision": {"options": [{"id": "O3", "risks_from": ["H7"]}]}}
    assert check_rejected_revived(sl, {"H7": {"status": "rejected"}})[0]["code"] == "REJECTED_HYPOTHESIS_REVIVED"
    # R5: partner checklist
    cr = {"findings": [{"critic": "PARTNER REVIEW", "finding": "Contingencia del 10% y coste hundido de 48 k€"}]}
    msg = check_partner_checklist(cr)[0]["message"]
    assert "capacity" in msg and "external_deadline" in msg and "contingency" not in msg.split("address:")[1]


def test_computed_fact_declares_assumption():
    from cpe.reasoning.checks import check_computed
    facts = {"F1": {"id": "F1", "values": [{"value": 2396, "unit": "EUR_K"}]}}
    _, good = check_computed({"facts": [{"id": "C1", "formula": "F1 * 0.099", "values": [{"value": 237.2}], "rests_on_assumptions": ["A001"]}]}, facts)
    assert good["C1"]["rests_on_assumptions"] == ["A001"]
