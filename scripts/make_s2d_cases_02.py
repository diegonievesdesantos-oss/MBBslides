"""Generate source-to-deck case set 02: harder cases written AFTER reasoning protocol 1.1 was frozen.

Each case is built to be hard in specific ways:
- a management claim that the data contradicts once the sources are combined;
- a driver buried in a second source or in row-level data;
- two sources that disagree on a number;
- several plausible answers, so options have to be compared on cost;
- a current plan or proposal to challenge;
- noise that is irrelevant to the question.

Synthetic development data written by the developing agent, with no real company. Not used to tune
protocol 1.1; used once, for experiment 02 / round s2. Run: python scripts/make_s2d_cases_02.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_s2d_dev_cases import _p, _tbl, write_docx, write_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "evals" / "source_to_deck" / "development"
AUTHORED = ("developing agent, case set 02 (synthetic, no real company); written after protocol 1.1 was frozen "
            "and not used to tune it — development data, NOT independent evidence")


def _case(name: str, project: dict, reference: dict) -> Path:
    d = ROOT / name
    (d / "sources").mkdir(parents=True, exist_ok=True)
    (d / "project.json").write_text(json.dumps(project, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    reference = {"status": "development", "authored_by": AUTHORED, "set": "02", **reference}
    (d / "reference.json").write_text(json.dumps(reference, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return d / "sources"


def _xlsx(path: Path, sheets: dict[str, list[list]]) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    wb.save(path)


# ── 1. warehouse closure (ES) ───────────────────────────────────────────────────────────────────

def almacen() -> None:
    src = _case("x2_almacen_valencia_es", {
        "project": "Red logística: cierre del almacén de Valencia (caso de desarrollo, set 02)",
        "audience": ["Consejero delegado", "Director financiero", "Director de operaciones"],
        "decision": "Aprobar o rechazar la propuesta de Operaciones de cerrar el almacén de Valencia en 2026",
        "question": "¿Debemos cerrar el almacén de Valencia y servir Levante desde Madrid? Si no, ¿qué hacemos?",
        "horizon": "2026-2027", "scope": ["Red de almacenes España: Madrid, Valencia, Sevilla"], "language": "es",
        "deck_type": "board_presentation", "max_slides": 9}, {
        "critical_facts": [
            {"id": "R1", "description": "Coste total Valencia 2025 (fijo + variable)", "value": 4.1, "unit": "M€"},
            {"id": "R2", "description": "Capacidad libre de Madrid (miles de pedidos)", "value": 300, "unit": ""},
            {"id": "R3", "description": "Transporte adicional a Levante desde Madrid", "value": 1.9, "unit": "M€"},
            {"id": "R4", "description": "Coste de cierre según Finanzas", "value": 3.2, "unit": "M€"}],
        "required_conclusions": [
            {"id": "C1", "description": "Cerrar no ahorra 4,1 M€: el coste variable se traslada a Madrid más caro, hace falta un turno y 1,9 M€ de transporte; el neto es ≈ −0,2 M€/año",
             "any_of": [["transporte", "1,9"], ["ahorro neto"], ["no ahorra"], ["0,2 m€"], ["coste neto"]]},
            {"id": "C2", "description": "Madrid no tiene capacidad: 300 mil pedidos libres frente a 375 mil (397 mil con la previsión 2026)",
             "any_of": [["capacidad", "madrid"], ["300", "375"], ["turno"]]},
            {"id": "C3", "description": "No cerrar; renovar el alquiler con el 25% de descuento (≈0,3 M€/año) y proteger el servicio en Levante",
             "any_of": [["renov"], ["no cerrar"], ["rechazar", "cierre"], ["mantener", "valencia"]]}],
        "traps": [
            {"id": "T1", "description": "Aceptar el ahorro de 4,1 M€ de Operaciones", "forbidden": [["ahorra 4,1"], ["ahorro de 4,1"], ["ahorrar 4,1"]]},
            {"id": "T2", "description": "Aceptar que Madrid tiene capacidad libre suficiente", "forbidden": [["madrid", "capacidad suficiente"], ["madrid", "capacidad libre suficiente"]]},
            {"id": "T3", "description": "Recomendar el cierre", "forbidden": [["aprobar el cierre"], ["cerrar valencia en 2026"], ["recomendamos cerrar"]]}],
        "acceptable_frameworks": ["SCR", "PDS", "DRI", "CII", "MPO"],
        "reference_governing_thought": "Cerrar Valencia no ahorra 4,1 M€ sino que cuesta unos 0,2 M€ al año, más 3,2 M€ de cierre y hasta 2,2 M€ de margen en riesgo, porque Madrid no tiene capacidad y el transporte a Levante sube 1,9 M€; renovar el alquiler con un 25% de descuento ahorra 0,3 M€ sin riesgo.",
        "notes": "Net = 2,6 + 1,5 − 375k×4,8€ (1,8) − turno 0,6 − transporte 1,9 = −0,2 M€/año. Margen en riesgo = 74 M€ × 34% × 40% × 22% ≈ 2,2 M€ (cota superior: 'se plantearía' no es 'cambiará')."})
    (src / "propuesta_operaciones.md").write_text(
        "# Propuesta de Operaciones — red logística 2026\n\n"
        "- Valencia nos costó 4,1 M€ en 2025 (coste fijo más variable). Cerrándolo ahorramos esos 4,1 M€ al año.\n"
        "- Madrid tiene capacidad libre suficiente para absorber los pedidos de Levante.\n"
        "- El coste de cierre estimado es de 1,5 M€.\n"
        "- El servicio al cliente no se verá afectado.\n"
        "- Recordatorio: la auditoría de seguridad de Sevilla se cerró sin incidencias.\n", encoding="utf-8")
    _xlsx(src / "almacenes_2025.xlsx", {
        "Costes": [["Almacén", "Coste fijo 2025 (M€)", "Coste variable 2025 (M€)", "Pedidos 2025 (miles)", "Coste variable por pedido (€)", "Plantilla"],
                   ["Madrid", 5.8, 6.0, 1500, 4.0, 210], ["Valencia", 2.6, 1.5, 375, 4.0, 64], ["Sevilla", 2.1, 1.4, 350, 4.0, 58],
                   ["Total", 10.5, 8.9, 2225, 4.0, 332]],
        "Capacidad": [["Almacén", "Capacidad (miles de pedidos/año)", "Pedidos 2025 (miles)", "Capacidad libre (miles)", "Utilización (%)"],
                      ["Madrid", 1800, 1500, 300, 83], ["Valencia", 450, 375, 75, 83], ["Sevilla", 420, 350, 70, 83]],
        "Notas": [["Nota"],
                  ["Por encima del 85% de utilización Madrid trabaja con horas extra: el coste variable de los pedidos adicionales sube a 4,8 € por pedido."],
                  ["Un turno adicional en Madrid amplía la capacidad en 250 mil pedidos y cuesta 0,6 M€ al año."],
                  ["Servir Levante desde Madrid añade 1,9 M€ al año de transporte."],
                  ["Previsión de pedidos 2026: +6% en toda la red (dato previsto, no real)."]]})
    write_pdf(src / "informe_finanzas_red.pdf", [
        "Informe de Finanzas sobre la red logística - noviembre 2025.",
        "El coste de cierre de Valencia (indemnizaciones, penalización del contrato de alquiler y desmantelamiento) asciende a 3,2 millones de euros. La estimación de 1,5 millones de euros de Operaciones no incluye la penalización del alquiler.",
        "El alquiler de Valencia (1,2 millones de euros al año, incluido en el coste fijo) vence en diciembre de 2026. El propietario ofrece renovar cinco años con un 25% de descuento.",
        "Los clientes de Levante suponen el 18% de los ingresos del grupo: 74 millones de euros de 412 millones de euros en 2025. El margen de contribución medio es del 22%.",
        "Desde Madrid, el 34% de los pedidos de Levante pasaría de entrega en 24 horas a 48 horas.",
        "En la encuesta de clientes de 2025, el 40% de los clientes con entrega a 48 horas declara que se plantearía cambiar de proveedor.",
        "Otros datos: la rotación de la plantilla de almacén fue del 11% en 2025, frente al 9% en 2024.",
    ])


# ── 2. SaaS growth slowdown (EN) ────────────────────────────────────────────────────────────────

def saas() -> None:
    src = _case("x2_saas_retention", {
        "project": "B2B software: growth slowdown and the 2026 investment plan (development case, set 02)",
        "audience": ["CEO", "CFO", "Board"],
        "decision": "Approve the 2026 growth investment (the CRO proposes hiring 30 account executives)",
        "question": "Why did ARR growth slow from 25% to 9%, and where should the 2026 growth budget go?",
        "horizon": "2026", "scope": ["Mid-market SaaS, Europe"], "language": "en", "deck_type": "board_presentation", "max_slides": 9}, {
        "critical_facts": [
            {"id": "R1", "description": "Gross churn 2025 (churned ARR / opening ARR)", "value": 15, "unit": "%"},
            {"id": "R2", "description": "New ARR 2025", "value": 9.6, "unit": "€M"},
            {"id": "R3", "description": "First-year cohort churn 2025", "value": 26, "unit": "%"},
            {"id": "R4", "description": "Median time to first value 2025 (days)", "value": 48, "unit": ""}],
        "required_conclusions": [
            {"id": "C1", "description": "The slowdown is retention, not acquisition: new ARR flat (9.4 → 9.6), win rate stable, churn 8% → 15%",
             "any_of": [["churn", "15%"], ["retention", "not"], ["new arr", "flat"], ["churned arr", "7.8"]]},
            {"id": "C2", "description": "The driver is onboarding: first-year customers churn 26% vs 9%, time to first value 21 → 48 days after the team was cut from 14 to 6",
             "any_of": [["onboarding"], ["time to first value"], ["first-year", "26%"]]},
            {"id": "C3", "description": "Fund onboarding first (≈€0.8M for up to €2.5M retained ARR); phase or cut the AE hiring, whose €9M assumes full productivity from day one",
             "any_of": [["onboarding", "restore"], ["onboarding", "rebuild"], ["onboarding", "rehire"], ["onboarding", "invest"], ["phase", "hiring"], ["fewer", "account executives"]]}],
        "traps": [
            {"id": "T1", "description": "Accepting the CRO's explanation that a competitor caused the slowdown", "forbidden": [["competitor", "caused"], ["competition", "slowed"], ["competitor", "undercutting", "growth"]]},
            {"id": "T2", "description": "Taking the €9M new ARR of the hiring plan as a 2026 result", "forbidden": [["30 account executives", "9m"], ["€9m of new arr in 2026"], ["deliver €9m"], ["add €9m"]]}],
        "acceptable_frameworks": ["SCR", "PDS", "DRI", "CII", "MPO"],
        "reference_governing_thought": "Growth slowed because churn doubled to 15%, driven by first-year customers (26%) after onboarding was cut, not by weaker selling; restoring onboarding (€0.8M) can retain up to €2.5M ARR, more than 30 new AEs (€3.6M) can add in 2026.",
        "notes": "AEs ramp in 9 months: 30 × €300k × 3/12 ≈ €2.25M new ARR in 2026, not €9M. Retained ARR = (26% − 12%) × €18.2M ≈ €2.5M, an upper bound (assumes a full return to the 2024 first-year churn)."})
    write_pdf(src / "board_pack_Q4_2025.pdf", [
        "Board pack Q4 2025 - extract.",
        "CFO: ARR closed 2025 at 56.8 EUR M, up 9.2%, against 25% growth in 2024.",
        "CRO: growth slowed because a new competitor is undercutting us on price. We propose to hire 30 account executives in Q1 2026 (3.6 EUR M per year fully loaded), which will add 9 EUR M of new ARR in 2026.",
        "Marketing: website traffic rose 31% in 2025 and the brand was shortlisted for two industry awards.",
        "HR: engineering headcount grew from 88 to 97.",
    ])
    with (src / "arr_bridge.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "opening_arr_eur_m", "new_arr_eur_m", "expansion_arr_eur_m", "churned_arr_eur_m", "closing_arr_eur_m"])
        w.writerows([[2024, 41.6, 9.4, 4.3, 3.3, 52.0], [2025, 52.0, 9.6, 3.0, 7.8, 56.8]])
    _xlsx(src / "crm_export.xlsx", {
        "Funnel": [["Quarter", "Pipeline created (EUR M)", "Win rate (%)", "Deals won"],
                   ["Q1 2024", 9.1, 24, 41], ["Q2 2024", 9.6, 25, 44], ["Q3 2024", 9.8, 24, 43], ["Q4 2024", 10.4, 24, 47],
                   ["Q1 2025", 10.9, 23, 46], ["Q2 2025", 11.3, 24, 49], ["Q3 2025", 11.6, 23, 48], ["Q4 2025", 12.1, 23, 50]],
        "Cohorts": [["Customer group", "ARR at start of 2025 (EUR M)", "ARR churned in 2025 (EUR M)", "Churn rate 2025 (%)"],
                    ["Onboarded in the previous 12 months", 18.2, 4.7, 26], ["Customers for more than 12 months", 33.8, 3.1, 9], ["Total", 52.0, 7.8, 15]],
        "Lost deals": [["Reason (sales-reported)", "Share of lost deals 2025 (%)"], ["Price", 34], ["No decision", 41], ["Competitor", 25]]})
    (src / "customer_success_notes.md").write_text(
        "# Customer success — notes for the planning cycle\n\n"
        "- The onboarding team was reduced from 14 to 6 people in February 2025 (saving 0.8 EUR M per year).\n"
        "- Median time to first value rose from 21 days in 2024 to 48 days in 2025.\n"
        "- In 2024, first-year customers churned 12%.\n"
        "- Exit interviews 2025 (64 churned customers): 58% say they never fully implemented the product, 17% moved to a competitor, 14% cite price.\n"
        "- New account executives reach full productivity (300 EUR k of new ARR per year) after 9 months.\n"
        "- The support ticket backlog was cleared in November.\n", encoding="utf-8")


# ── 3. loss-making convenience stores (ES) ─────────────────────────────────────────────────────

def tiendas() -> None:
    src = _case("x2_tiendas_proximidad_es", {
        "project": "Tiendas de proximidad en pérdidas (caso de desarrollo, set 02)",
        "audience": ["Consejero delegado", "Directora financiera", "Director de expansión"],
        "decision": "Decidir qué hacer con las 40 tiendas de proximidad en pérdidas (la dirección financiera propone cerrarlas todas en 2026)",
        "question": "¿Qué hacemos con las 40 tiendas de proximidad en pérdidas y cuánto mejora realmente el EBITDA?",
        "horizon": "2026-2027", "scope": ["Formato proximidad, España"], "language": "es", "deck_type": "board_presentation", "max_slides": 9}, {
        "critical_facts": [
            {"id": "R1", "description": "EBITDA 2025 de las 40 tiendas (k€)", "value": -5196, "unit": ""},
            {"id": "R2", "description": "Coste central asignado total (k€)", "value": 3600, "unit": ""},
            {"id": "R3", "description": "Tiendas del grupo A con ruptura de contrato en 2026", "value": 15, "unit": ""},
            {"id": "R4", "description": "Contribución propia del grupo B antes de costes centrales (k€)", "value": 324, "unit": ""}],
        "required_conclusions": [
            {"id": "C1", "description": "Cerrar las 40 mejora el EBITDA unos 1,6 M€, no 5,2: los 3,6 M€ de coste central asignado se quedan",
             "any_of": [["coste central"], ["costes centrales"], ["1,6 m€"], ["1.596"]]},
            {"id": "C2", "description": "El grupo B (aperturas 2023–2024) aporta +324 k€ antes de costes centrales y va camino del equilibrio",
             "any_of": [["grupo b", "positiv"], ["grupo b", "contribu"], ["recientes"], ["jóvenes"], ["324"]]},
            {"id": "C3", "description": "Cierre selectivo: las 15 tiendas con ruptura de contrato (+1,5 M€/año, 1,5 M€ de coste, retorno en un año), renegociar 7, mantener el grupo B con un hito",
             "any_of": [["15 tiendas"], ["selectiv"], ["ruptura", "contrato"]]}],
        "traps": [
            {"id": "T1", "description": "Aceptar que cerrar mejora el EBITDA 5,2 M€", "forbidden": [["mejora", "5,2 m€"], ["ahorr", "5,2 m€"], ["mejorar el ebitda en 5,2"]]},
            {"id": "T2", "description": "Recomendar cerrar las 40 (terms v2: 'cerrar las 40' alone matched storylines that refute it)", "forbidden": [["recomendamos cerrar las 40"], ["proponemos cerrar las 40"], ["aprobar el cierre de las 40"], ["cerrar todas las tiendas en 2026"]]}],
        "acceptable_frameworks": ["SCR", "PDS", "DRI", "CII", "MPO"],
        "reference_governing_thought": "Cerrar las 40 tiendas mejora el EBITDA unos 1,6 M€, no 5,2, porque 3,6 M€ de costes centrales se quedan y las 18 aperturas recientes ya cubren sus costes propios; cerrar solo las 15 con ruptura de contrato en 2026 captura 1,5 M€ al año con un coste recuperado en un año.",
        "notes": "Grupo A con ruptura: 15 × (−190 + 90) = −1.500 k€; resto A: 7 × (−150 + 90) = −420; grupo B: 10 × (−80 + 90) + 8 × (−62 + 90) = +324. Cerrar todas: 1.920 − 324 = 1.596 k€. Coste de cierre: 15 × 100 + 25 × 250 = 7.750 k€ (la DF usa 10 M€). Alquiler/ventas del grupo A: 16% con gastos comunes, 14,5% sin ellos (conflicto de base)."})
    rows = [["Tienda", "Grupo", "Año de apertura", "Ventas 2025 (k€)", "Alquiler / ventas (%)", "EBITDA 2025 (k€)", "Coste central asignado (k€)", "Ruptura de contrato en 2026"]]
    for i in range(15):
        rows.append([f"P{i + 1:02d}", "A", 2014 + i % 6, 1100, 14.5, -190, 90, "sí"])
    for i in range(7):
        rows.append([f"P{i + 16:02d}", "A", 2012 + i % 5, 1150, 14.5, -150, 90, "no"])
    for i in range(10):
        rows.append([f"P{i + 23:02d}", "B", 2023, 900, 9.0, -80, 90, "no"])
    for i in range(8):
        rows.append([f"P{i + 33:02d}", "B", 2024, 820, 9.0, -62, 90, "no"])
    _xlsx(src / "tiendas_proximidad_2025.xlsx", {
        "Tiendas": rows,
        "Resumen": [["Grupo", "Tiendas", "EBITDA 2025 (k€)", "Coste central asignado (k€)"],
                    ["A - alquiler alto", 22, -3900, 1980], ["B - aperturas 2023-2024", 18, -1296, 1620], ["Total", 40, -5196, 3600]],
        "Notas controller": [["Nota"], ["El EBITDA de cada tienda incluye 90 k€ de coste central asignado (sistemas, logística, central de compras)."],
                             ["El coste central no desaparece si se cierra una tienda: se reparte entre el resto de la red."],
                             ["Alquiler / ventas medido sin gastos comunes."]]})
    write_pdf(src / "informe_inmobiliario.pdf", [
        "Informe de la dirección inmobiliaria - tiendas de proximidad.",
        "El alquiler de las tiendas del grupo A supone un 16% de sus ventas (incluidos gastos comunes), frente al 9% de media de la red.",
        "15 contratos del grupo A tienen ventana de ruptura en 2026: cerrarlas cuesta 100.000 euros por tienda. Cerrar una tienda sin ruptura cuesta 250.000 euros (penalización e indemnizaciones).",
        "Los propietarios de 5 de las 7 tiendas restantes del grupo A han aceptado negociar una rebaja de alquiler.",
        "Las tiendas del grupo B abrieron en 2023 y 2024. Sus ventas por metro cuadrado crecen un 11% al año. En nuestra red, una tienda de proximidad alcanza el equilibrio en su cuarto año.",
        "Otros: la reforma de la tienda insignia de Madrid terminó en octubre.",
    ])
    (src / "propuesta_direccion_financiera.md").write_text(
        "# Propuesta de la dirección financiera\n\n"
        "- Las 40 tiendas de proximidad perdieron 5,2 M€ de EBITDA en 2025.\n"
        "- Proponemos cerrarlas todas en 2026: el EBITDA del grupo mejora en 5,2 M€.\n"
        "- Coste de cierre estimado: 250 k€ por tienda, 10 M€ en total.\n", encoding="utf-8")


# ── 4. single-supplier packaging (EN) ──────────────────────────────────────────────────────────

def packaging() -> None:
    src = _case("x2_packaging_supplier", {
        "project": "Packaging supplier consolidation (development case, set 02)",
        "audience": ["COO", "CFO", "Chief procurement officer"],
        "decision": "Approve or reject procurement's proposal to move all packaging spend to Supplier B from 2026",
        "question": "Should we consolidate packaging on a single supplier, and what is the real saving?",
        "horizon": "2026-2028", "scope": ["Packaging for the food division"], "language": "en", "deck_type": "board_presentation", "max_slides": 8}, {
        "critical_facts": [
            {"id": "R1", "description": "Packaging spend 2025", "value": 25, "unit": "€M"},
            {"id": "R2", "description": "Rush freight included in that spend", "value": 1.1, "unit": "€M"},
            {"id": "R3", "description": "Supplier B price reduction at 100% of volume", "value": 12, "unit": "%"},
            {"id": "R4", "description": "Gross margin lost in a 14-day stoppage", "value": 2.4, "unit": "€M"}],
        "required_conclusions": [
            {"id": "C1", "description": "The saving is below €3.0M: the 12% applies to €23.9M (rush freight is not a price), ≈€2.9M, and expected disruption costs ≈€1.3M a year",
             "any_of": [["rush freight"], ["23.9"], ["2.9"], ["disruption", "1.3"]]},
            {"id": "C2", "description": "Single-source risk: Supplier B has one plant and two force-majeure stoppages in three years",
             "any_of": [["single plant"], ["one plant"], ["force majeure"], ["force-majeure"], ["stoppage"]]},
            {"id": "C3", "description": "Dual source 70/30 (≈€1.8M a year with a backup supplier) beats the single supplier (≈€1.5M after expected disruption)",
             "any_of": [["70/30"], ["dual"], ["two suppliers"], ["70%", "30%"]]}],
        "traps": [
            {"id": "T1", "description": "Accepting procurement's €3.0M saving", "forbidden": [["saves €3.0m"], ["saving of €3.0m"], ["€3.0m", "saving per year"]]},
            {"id": "T2", "description": "Recommending the move of 100% of the volume to Supplier B", "forbidden": [["approve", "single supplier"], ["move all", "supplier b"], ["100%", "supplier b", "approve"]]}],
        "acceptable_frameworks": ["SCR", "PDS", "DRI", "CII", "MPO"],
        "reference_governing_thought": "Moving all packaging to Supplier B saves about €1.5M a year, not €3.0M, once rush freight is taken out and the single plant's stoppage risk is priced in; a 70/30 split saves about €1.8M and keeps a second plant as backup.",
        "notes": "Single supplier: 12% × 23.9 = 2.87; expected disruption (1.6 + 2.4) / 3 = 1.33 a year (historical frequency, so an estimate); net ≈ 1.5; one-off €0.8M. 70/30: 9% × 16.73 = 1.51 + 4% × 7.17 = 0.29 = 1.79; one-off €0.5M."})
    write_docx(src / "procurement_proposal.docx", [
        _p("Procurement proposal: packaging 2026-2028", heading=True),
        _p("Packaging spend was 25 EUR M in 2025, with the volume split between the incumbent (70%) and Supplier B (30%)."),
        _p("Supplier B offers a 12% price reduction if it receives 100% of our volume under a three-year commitment. This saves 3.0 EUR M per year."),
        _p("Supplier B volume breaks (price reduction by share of our volume):"),
        _tbl([["Share of our volume with Supplier B", "Price reduction (%)"], ["30%", "0"], ["70%", "9"], ["100%", "12"]]),
        _p("We recommend approving the move to a single supplier from January 2026."),
    ])
    write_pdf(src / "supply_risk_review.pdf", [
        "Supply risk review - packaging.",
        "Supplier B operates a single plant. It declared two force-majeure stoppages in the last three years, of 9 and 14 days.",
        "A 9-day packaging stoppage would cost us 1.6 EUR M of gross margin; a 14-day stoppage 2.4 EUR M.",
        "The incumbent operates two plants and can cover up to 60% of our volume at two weeks' notice.",
        "If kept at 30% of our volume, the incumbent has offered a 4% price reduction on that volume.",
        "Switching costs (tooling and line qualification): 0.8 EUR M one-off for a full move, 0.5 EUR M for a partial move.",
    ])
    months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]
    rush = [0.05, 0.04, 0.12, 0.08, 0.06, 0.15, 0.09, 0.03, 0.14, 0.11, 0.13, 0.10]  # sums to 1.10
    with (src / "invoices_2025.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "supplier", "invoiced_eur_m", "of_which_rush_freight_eur_m", "note"])
        for m, r in zip(months, rush):
            w.writerow([m, "Incumbent", round(16.73 / 12 + r, 3), r, "rush freight passed through: our forecast errors" if r > 0.1 else ""])
            w.writerow([m, "Supplier B", 0.598 if m != "2025-12" else 0.592, 0, ""])
    (src / "finance_note.md").write_text(
        "# Finance note\n\n"
        "- The 25 EUR M packaging spend includes 1.1 EUR M of rush freight invoiced by the incumbent; a unit-price reduction does not apply to it.\n"
        "- Packaging spend excluding rush freight: 23.9 EUR M.\n"
        "- Unrelated: the energy contract for the Zaragoza plant was renewed in September.\n", encoding="utf-8")


if __name__ == "__main__":
    almacen()
    saas()
    tiendas()
    packaging()
    print("ok")
