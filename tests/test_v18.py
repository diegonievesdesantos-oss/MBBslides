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
