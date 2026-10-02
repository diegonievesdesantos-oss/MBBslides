"""v1.9 — DEBT_V18 fixes (tool findings from the real-project run), on synthetic data."""


def test_u4_u5_week_and_date_references_are_periods():
    from cpe.core.headline import numbers_in
    from cpe.ingest.readers import mask_dates
    assert numbers_in("En régimen (semanas 31 a 40) rinde 1,89x; la mejor semana (S37) 85,7") == [(1.89, "x"), (85.7, "")]
    assert numbers_in("Decidir la firma el 27 de noviembre") == []
    assert "12" not in mask_dates("weeks 12-15 and W40, KW 12")
    assert numbers_in("durante 8 semanas por encima de 2,2x") == [(2.2, "x")]  # a duration before the word is not masked, and is exempt


def test_u6_unit_comes_from_header_or_stated_label_not_quoted_figures():
    from cpe.reasoning.facts import _label_unit_text, detect_unit
    assert detect_unit(_label_unit_text("Real + mermas de 120 k€ (sin fuente)")) == ""
    assert detect_unit(_label_unit_text("FY2027 orgánico (+3,5% sin Marea)")) == ""
    assert detect_unit(_label_unit_text("Ventas netas (M€)")) == "EUR_M"
    assert detect_unit(_label_unit_text("Margen (%)")) == "PCT"


def test_u8_statement_text_is_fact_checked():
    from cpe.reasoning.checks import factcheck_deck
    facts = {"F1": {"id": "F1", "claim": "Ventas 2025: 1.460 M€", "values": [{"value": 1460, "unit": "EUR_M"}]}}
    deck = {"slides": [{"id": "s02", "kind": "exec_summary", "headline": "Las ventas crecen pero el margen cae", "evidence": [{"fact": "F1"}],
                        "visual": {"type": "statements", "data": {"items": [{"title": "Volumen", "text": "Las ventas llegan a 1.460 M€ y el margen a 23%"}]}}}]}
    bad = [i for i in factcheck_deck(deck, facts) if i["code"] == "UNSUPPORTED_NUMBER"]
    assert len(bad) == 1 and "23%" in bad[0]["message"] and "items[0].text" in bad[0]["ref"]


def test_u9_scaled_numbers_ground_against_unscaled_facts():
    from cpe.reasoning.grounding import ground_numbers
    f = [{"id": "F1", "claim": "Líneas FY2027 (miles)", "values": [{"value": 4588, "unit": ""}]},
         {"id": "F2", "claim": "Capacidad (millones de líneas)", "values": [{"value": 4.6, "unit": ""}]}]
    st = {g["number"]: g["status"] for g in ground_numbers("4,59 M de líneas frente a 4,6 M de capacidad", f)}
    assert st == {"4,59 M": "grounded", "4,6 M": "grounded"}
    assert ground_numbers("unos 7,3 M de líneas", f)[0]["status"] == "unsupported"


def test_u2_banner_line_and_repeated_two_level_header(tmp_path):
    import json
    import subprocess
    import sys
    src = tmp_path / "src"
    src.mkdir()
    (src / "presupuesto.csv").write_text(
        "Presupuesto almacén · versión 2 (borrador 25/09/2026);;;;;\n"
        "Concepto;FY2025;FY2026;FY2026;FY2027;Comentario\n"
        ";Real;Presupuesto;Real;Presupuesto;\n"
        "Volumen;;;;;\n"
        "Líneas preparadas (miles);4.396;4.660;4.373;4.723;+8% s/ real FY2026\n"
        "Ventas netas (M€);94,5;100,1;94,0;101,6;\n"
        "Mantenimiento;n/d;75;33;133;Contrato\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "cpe", "reason", "facts", str(src), "-o", str(tmp_path / "w")], check=True, capture_output=True)
    fs = json.loads((tmp_path / "w" / "facts.json").read_text(encoding="utf-8"))["facts"]
    by = {(f["values"][0]["label"].split(" · ")[0], f["values"][0]["period"], f["values"][0]["basis"]): f["values"][0] for f in fs if f.get("fact_type") == "table_value"}
    assert by[("Líneas preparadas (miles)", "FY2025", "actual")]["value"] == 4396 and by[("Líneas preparadas (miles)", "FY2025", "actual")]["unit"] == ""
    assert by[("Líneas preparadas (miles)", "FY2027", "budget")]["value"] == 4723
    assert by[("Ventas netas (M€)", "FY2025", "actual")] == {**by[("Ventas netas (M€)", "FY2025", "actual")], "value": 94.5, "unit": "EUR_M"}
    assert by[("Mantenimiento", "FY2026", "actual")]["value"] == 33
