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


def test_u3_conflicts_read_each_number_with_its_own_words():
    from cpe.reasoning.conflicts import detect_conflicts

    def tx(i, file, claim, value, unit, period=None):
        return {"id": i, "fact_type": "text_statement", "claim": claim, "source": {"file": file, "loc": "line 1"},
                "values": [{"value": value, "unit": unit, "period": period}]}

    def tv(i, file, label, col, value, unit, period=None):
        return {"id": i, "fact_type": "table_value", "claim": f"{label} — {col}", "source": {"file": file, "loc": "sheet A"},
                "values": [{"value": value, "unit": unit, "period": period, "label": label, "column": col}]}

    real = [tx("F1", "informe.md", "La productividad de la zona automatizada ya es 2,1 veces la productividad manual.", 2.1, "X"),
            tx("F2", "oferta.md", "Productividad de preparación en puestos GTP: 2,4 veces la productividad manual de referencia.", 2.4, "X"),
            tx("F3", "ops.md", "El coste de cierre de Valencia (indemnizaciones, penalización del contrato de alquiler y desmantelamiento) asciende a 3,2 millones de euros.", 3.2, "EUR_M"),
            tx("F4", "propuesta.md", "El coste de cierre estimado es de 1,5 M€.", 1.5, "EUR_M")]
    assert len(detect_conflicts(real)) == 2
    noise = [  # a comparison base is not the number's period; phases, zones and mixed manual/automated wording are not one quantity
        tx("F1", "informe.md", "FY2026 cierra con 4,37 millones de líneas preparadas, un 0,5% menos que en FY2025.", 0.5, "PCT", "FY2026"),
        tv("F2", "presupuesto.csv", "Líneas preparadas (miles)", "Comentario: +8% s/ real FY2026", 8.0, "PCT", "FY2026"),
        tv("F3", "modelo.xlsx", "resultado · Ahorro neto anual · k€/año", "fase_2", 643, "EUR_K"),
        tv("F4", "analisis.csv", "Ahorro neto anual de la fase 1 en el business case", "importe (k€)", 732, "EUR_K"),
        tv("F5", "deck.pptx", "Tasa de error manual / automatizada", "Valor: 0,9% / 0,2%", 0.2, "PCT"),
        tv("F6", "wms.csv", "Tasa de error de la zona frío manual (%)", "valor", 0.91, "PCT"),
        tv("F7", "ventas.csv", "Líneas preparadas (miles) · FY2025 · Real", "valor", 4396, ""),
        tv("F8", "wms.csv", "Líneas de la zona frío en FY2026 (miles)", "valor", 1927, "")]
    assert detect_conflicts(noise) == []
