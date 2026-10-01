#!/usr/bin/env python3
"""Generate the balanced archetype development battery (v1.4): evals/regression/cases/2x_battery_*.json

One deck per archetype, 8–12 slides each, with real internal variation (counts, label length,
density, language, number formats, sources, footnotes). DEVELOPMENT data: visible, rendered and
used to diagnose and fix the engine. It shares no content with evals/holdout/v2.

    python3 scripts/make_archetype_battery.py            # (re)write the case files
    python3 scripts/make_archetype_battery.py --check    # exit 1 if the files are out of date
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "regression" / "cases"
THEMES = ["meridian", "harbor", "graphite"]
SRC = "Battery fixture (synthetic)"
FUENTE = "Batería de pruebas (sintética)"


class Deck:
    def __init__(self, key: str, archetype: str, purpose: str, idx: int):
        self.key, self.archetype, self.purpose, self.idx = key, archetype, purpose, idx
        self.slides: list[dict] = []

    def add(self, s: dict, es: bool = False, source: bool = True, footnotes: list | None = None):
        s = dict(s)
        s.setdefault("id", f"{self.key}{len(self.slides) + 1:02d}")
        if s.get("kind", "content") == "content":
            s.setdefault("section", "K1")
            s.setdefault("purpose", "Battery case")
            if source:
                s.setdefault("source", FUENTE if es else SRC)
        if footnotes:
            s["footnotes"] = footnotes
        self.slides.append(s)
        return self

    def write(self) -> Path:
        spec = {"meta": {"title": f"Battery: {self.archetype}", "deck_type": "strategy_deck", "theme": THEMES[self.idx % 3]},
                "storyline": {"framework": "SCR", "collection": True, "governing_thought": f"Each {self.archetype} slide is judged on what it is trying to be",
                              "key_line": [{"id": "K1", "role": "situation", "message": "Variations of one archetype"},
                                           {"id": "K2", "role": "resolution", "message": "Composition must hold across them"}]},
                "eval": {"purpose": f"Archetype battery ({self.archetype}): {self.purpose}", "battery": self.archetype}, "slides": self.slides}
        p = OUT / f"2{self.idx:02d}_battery_{self.archetype}.json"
        p.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p


def content(headline, visual=None, mt="comparison", **kw):
    s = {"headline": headline, "message_type": mt}
    if visual:
        s["visual"] = visual
    s.update(kw)
    return s


def kpi(value, label, **kw):
    return {"value": value, "label": label, **kw}


def chart(typ, title, unit, cats, series, **kw):
    v = {"type": typ, "title": title, "unit": unit, "data": {"categories": cats, "series": [{"name": n, "values": vals} for n, vals in series]}}
    v.update(kw)
    return v


def table_v(typ, title, cols, rows, **kw):
    return {"type": typ, "title": title, "columns": [c if isinstance(c, dict) else {"label": c} for c in cols], "rows": rows, **kw}


def num(label, **kw):
    return {"label": label, "kind": "number", **kw}


def steps(*items):
    out = []
    for it in items:
        if isinstance(it, str):
            out.append({"title": it})
        elif isinstance(it, tuple):
            d = {"title": it[0]}
            if len(it) > 1 and it[1]:
                d["text" if isinstance(it[1], str) else "points"] = it[1]
            if len(it) > 2 and it[2]:
                d.update(it[2])
            out.append(d)
    return out


def build() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    decks: list[Deck] = []

    # ── statement ───────────────────────────────────────────────────────────
    d = Deck("st", "statement", "short / long / with and without support / Spanish / quote-like", 0)
    d.add({"kind": "statement", "text": "Price is not the problem; availability is"})
    d.add({"kind": "statement", "text": "We should exit the wholesale business by 2027", "support": "It uses 30% of capital and earns 4% of profit."})
    d.add({"kind": "statement", "text": "Three of our five markets will shrink in the next decade, and the two that grow are the ones where we are weakest today",
           "support": "This document explains how we rebalance the portfolio without losing scale."})
    d.add({"kind": "statement", "text": "La decisión es sencilla: invertir ahora o perder la licencia", "support": "El regulador revisa las concesiones en 2027."}, es=True)
    d.add({"kind": "statement", "text": "“Customers do not leave because of price; they leave because nobody calls back”",
           "attribution": "Head of customer service", "style": "quote"})
    d.add({"kind": "statement", "text": "Recomendamos no renovar el contrato con el operador logístico actual"}, es=True)
    d.add({"kind": "statement", "text": "Growth now comes from services", "support": "Services were 12% of revenue in 2020 and are 31% today; hardware shrank every year."})
    d.add({"kind": "statement", "text": "Decision requested", "support": "Approve €14M for the pilot in four regions; results come back to the board in nine months."})
    d.add({"kind": "statement", "text": "El 80% del ahorro depende de una sola palanca: renegociar la energía",
           "support": "El resto de iniciativas suma menos de 6 M€ y puede esperar al segundo año."}, es=True)
    decks.append(d)

    # ── kpi_hero ────────────────────────────────────────────────────────────
    d = Deck("kh", "kpi_hero", "single metric / delta / explanation / positive / negative / % / currency / large integer / Spanish", 1)
    d.add(content("Gross margin reached 41%, the highest in five years", {"type": "kpi", "data": {"items": [kpi("41%", "gross margin, 2025")]}}, mt="single_number"))
    d.add(content("Revenue per store fell 6% as footfall declined", {"type": "kpi", "data": {"items": [kpi("−6%", "revenue per store, like-for-like", delta="−€0.4M", trend="down", good="up")]}}, mt="single_number"))
    d.add(content("The programme has already delivered €48M of savings", {"type": "kpi", "data": {"items": [kpi("€48M", "savings delivered to date", delta="+€12M vs plan", trend="up", good="up",
          note="Procurement and energy contracts signed in Q2")]}}, mt="single_number"))
    d.add(content("The platform processed 1,240,000 orders in November", {"type": "kpi", "data": {"items": [kpi("1,240,000", "orders processed, November")]}}, mt="single_number"))
    d.add(content("La rotación de plantilla bajó al 9,8%", {"type": "kpi", "data": {"items": [kpi("9,8%", "rotación anual de plantilla", delta="−3,1 pp", trend="down", good="down")]}},
          mt="single_number"), es=True)
    d.add(content("Net debt stands at 3.4 times EBITDA, above the 3.0 covenant", {"type": "kpi", "data": {"items": [kpi("3.4x", "net debt / EBITDA, December", delta="+0.6x", trend="up", good="down",
          note="Covenant headroom closes in Q3 without disposals")]}}, mt="single_number"))
    d.add(content("Customers rate the new app 4.7 out of 5", {"type": "kpi", "data": {"items": [kpi("4.7", "app store rating, 18,300 reviews", delta="+0.9", trend="up", good="up")]}}, mt="single_number"))
    d.add(content("El coste por pedido es de 2,35 €, un 18% menos que hace un año", {"type": "kpi", "data": {"items": [kpi("2,35 €", "coste logístico por pedido", delta="−18%", trend="down", good="down",
          note="Rutas optimizadas y entregas agrupadas")]}}, mt="single_number"), es=True)
    d.add(content("Two KPIs carry the story: churn halved while revenue per user rose", {"type": "kpi", "data": {"items": [kpi("2.1%", "monthly churn", delta="−2.2 pts", trend="down", good="down"),
          kpi("$54", "revenue per user", delta="+$7", trend="up", good="up")]}}, mt="single_number"))
    d.add(content("Emissions fell 27% against the 2019 baseline", {"type": "kpi", "data": {"items": [kpi("−27%", "scope 1 and 2 emissions vs 2019")]}}, mt="single_number"),
          footnotes=["Market-based method; excludes acquisitions after 2023."])
    decks.append(d)

    # ── kpi_dashboard ───────────────────────────────────────────────────────
    d = Deck("kd", "kpi_dashboard", "3–6 KPIs / strip and grid / deltas / notes / Spanish", 2)
    def k3(es_=False):
        return [kpi("12%", "crecimiento" if es_ else "revenue growth", delta="+2 pp" if es_ else "+2 pts", trend="up", good="up"),
                kpi("18.5%" if not es_ else "18,5%", "margen EBIT" if es_ else "EBIT margin", delta="+0.4 pts" if not es_ else "+0,4 pp", trend="up", good="up"),
                kpi("€210M", "caja libre" if es_ else "free cash flow", delta="−€15M", trend="down", good="up")]
    d.add(content("Growth and margin beat the plan; cash falls short", {"type": "kpi", "data": {"items": k3()}}, mt="kpi_dashboard"))
    d.add(content("Crecimiento y margen mejoran; la caja empeora por el inventario", {"type": "kpi", "data": {"items": k3(True)}}, mt="kpi_dashboard"), es=True)
    d.add(content("Four operating KPIs improved in the quarter", {"type": "kpi", "data": {"style": "grid", "items": [kpi("96.1%", "on-time delivery", delta="+1.8 pts", trend="up", good="up"),
          kpi("3.2 days", "order lead time", delta="−0.6 days", trend="down", good="down"), kpi("0.8%", "return rate", delta="−0.1 pts", trend="down", good="down"),
          kpi("88", "NPS", delta="+4", trend="up", good="up")]}}, mt="kpi_dashboard"))
    d.add(content("Five metrics track the transformation", {"type": "kpi", "data": {"items": [kpi("€31M", "run-rate savings"), kpi("62%", "processes automated"), kpi("1,450", "staff retrained"),
          kpi("4", "systems retired"), kpi("97%", "milestones on time")]}}, mt="kpi_dashboard"))
    d.add(content("Six KPIs show a business that grows but consumes cash", {"type": "kpi", "data": {"style": "grid", "items": [kpi("+14%", "revenue"), kpi("+9%", "gross profit"),
          kpi("−3 pts", "gross margin", trend="down", good="up"), kpi("€-42M", "operating cash flow", trend="down", good="up"), kpi("71 days", "inventory", trend="up", good="down"),
          kpi("2.9x", "leverage", trend="up", good="down")]}}, mt="kpi_dashboard"))
    d.add(content("Customers grow and complaints fall on every metric", {"type": "kpi", "data": {"items": [kpi("2.4M", "active customers", delta="+310k", trend="up", good="up",
          note="Mostly app sign-ups"), kpi("1.1%", "complaint rate", delta="−0.4 pts", trend="down", good="down", note="Fewer billing errors"),
          kpi("38 s", "average wait time", delta="−12 s", trend="down", good="down", note="Callback service live")]}}, mt="kpi_dashboard"))
    d.add(content("La seguridad laboral alcanza mínimos históricos", {"type": "kpi", "data": {"style": "grid", "items": [kpi("0,9", "índice de frecuencia"),
          kpi("0", "accidentes graves"), kpi("12.400", "horas de formación"), kpi("98%", "auditorías superadas")]}}, mt="kpi_dashboard"), es=True)
    d.add(content("Pipeline, win rate and deal size all moved the right way", {"type": "kpi", "data": {"items": [kpi("$412M", "qualified pipeline", delta="+22%", trend="up", good="up"),
          kpi("27%", "win rate", delta="+3 pts", trend="up", good="up"), kpi("$186k", "average deal", delta="+$21k", trend="up", good="up"),
          kpi("94 days", "sales cycle", delta="−8 days", trend="down", good="down")]}}, mt="kpi_dashboard"))
    decks.append(d)

    # ── executive_summary ───────────────────────────────────────────────────
    d = Deck("es", "executive_summary", "2–6 rows / short and long / SCR / Spanish", 3)
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "Two moves restore growth in 2027",
           "visual": {"type": "statements", "data": {"items": [{"title": "Fix pricing in convenience", "text": "Worth €20M."}, {"title": "Open 30 discount stores", "text": "Worth €45M."}]}}})
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "The insurer can cut its cost ratio by four points in three years by automating claims",
           "visual": {"type": "statements", "data": {"items": [
               {"title": "Claims cost 38% of premiums, eight points above peers", "text": "Manual assessment and slow payments drive both cost and leakage."},
               {"title": "Automated assessment works on 70% of motor claims", "text": "Pilot cut handling time from 23 to 6 days with no rise in leakage."},
               {"title": "The platform pays back in 26 months", "text": "€41M investment, €64M a year of savings from 2028."},
               {"title": "The board is asked to approve phase one", "text": "€18M for photo assessment and triage in 2026."}]}}})
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "La cadena puede volver a crecer si cierra tiendas pequeñas y abre formato de proximidad",
           "visual": {"type": "statements", "data": {"items": [
               {"title": "Las tiendas de menos de 400 m² pierden dinero", "text": "38 tiendas con resultado negativo por tercer año."},
               {"title": "La proximidad crece al 7% anual", "text": "Los clientes compran más a menudo y con cestas más pequeñas."},
               {"title": "El nuevo formato se paga en tres años", "text": "Piloto en 5 tiendas con ventas un 22% superiores."}]}}}, es=True)
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "Exiting two markets frees €120M for the core business",
           "visual": {"type": "statements", "data": {"style": "scr", "items": [
               {"label": "Situation", "title": "Five markets, two of them subscale", "text": "Poland and Romania are 9% of revenue and lose money."},
               {"label": "Complication", "title": "Both need €120M of capex to stay competitive", "text": "Returns stay below the cost of capital even after investment."},
               {"label": "Resolution", "title": "Sell both and reinvest at home", "text": "Two buyers have shown interest at 0.8x revenue."}]}}})
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "Five findings from the operations review",
           "visual": {"type": "statements", "data": {"items": [{"title": t, "text": x} for t, x in [
               ("Capacity is not the constraint", "Plants run at 71% utilisation."), ("Changeovers are", "They take 19% of planned time."),
               ("Quality losses are concentrated", "Two lines cause 64% of scrap."), ("Maintenance is reactive", "78% of hours are unplanned."),
               ("Fixing these adds 9 points of OEE", "Without new equipment.")]]}}})
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "Resumen: tres decisiones para el consejo",
           "visual": {"type": "statements", "data": {"items": [{"title": "Aprobar el plan de eficiencia", "text": "Ahorro de 35 M€."},
                                                              {"title": "Lanzar la marca propia", "text": "Margen +2 pp."},
                                                              {"title": "Vender la filial de transporte", "text": "Ingreso de 60 M€."}]}}}, es=True)
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "The programme is on track, but the second wave needs funding by March to keep the 2027 target",
           "visual": {"type": "statements", "data": {"style": "scr", "items": [
               {"label": "Situation", "title": "Wave one delivered €22M, ahead of plan", "text": "Procurement and energy renegotiations closed early; overtime is down a fifth."},
               {"label": "Complication", "title": "Automation needs €30M of capex with nine-month lead times", "text": "Ordering after March pushes €11M of savings into 2028."},
               {"label": "Resolution", "title": "Release the wave-two budget now", "text": "Keeps the €65M run-rate target for 2027 and pays back in 22 months."}]}}})
    d.add({"kind": "exec_summary", "purpose": "Answer first", "headline": "Six reasons the merger creates value",
           "visual": {"type": "statements", "data": {"items": [{"title": t, "text": x} for t, x in [
               ("Complementary footprints", "Overlap in only 3 of 14 regions."), ("Procurement scale", "€45M of savings on combined spend."),
               ("Shared platforms", "One ERP and one data centre by 2028."), ("Cross-selling", "€30M of revenue synergies."),
               ("Stronger balance sheet", "Leverage falls to 2.1x."), ("Retained talent", "Key managers committed for three years.")]]}}})
    decks.append(d)

    # ── chart ───────────────────────────────────────────────────────────────
    d = Deck("ch", "chart", "column/bar/line/stacked/donut/combo / few and many points / 1–5 series / negatives / Spanish decimals", 4)
    d.add(content("Revenue doubled in four years", chart("column", "Revenue", "€M", ["2021", "2022", "2023", "2024", "2025"], [("Revenue", [210, 260, 315, 370, 425])]), mt="trend",
          commentary={"points": ["Organic growth of **19% a year**", "No acquisitions in the period"]}))
    d.add(content("Two regions explain the whole decline in profit", chart("bar", "Operating profit change by region", "€M", ["North", "South", "East", "West", "Islands"],
          [("Change", [8, 3, -1, -14, -11])], highlight=["West", "Islands"]), mt="ranking"))
    d.add(content("Online overtook stores in 2024 and keeps growing faster", chart("line", "Sales by channel", "€bn", ["2019", "2020", "2021", "2022", "2023", "2024", "2025"],
          [("Online", [1.1, 1.9, 2.3, 2.6, 2.9, 3.4, 3.9]), ("Stores", [3.8, 2.9, 3.2, 3.3, 3.2, 3.1, 3.0])], highlight=["Online"]), mt="trend"))
    d.add(content("La cuota de la marca propia sube en las cinco categorías", chart("stacked_100", "Cuota por tipo de marca", "% de ventas", ["Lácteos", "Bebidas", "Limpieza", "Snacks", "Congelados"],
          [("Marca propia", [42.5, 31.2, 48.9, 27.4, 39.8]), ("Fabricante", [57.5, 68.8, 51.1, 72.6, 60.2])], format={"decimals": 1}), mt="composition"), es=True)
    d.add(content("Three customers account for half of the revenue", chart("donut", "Revenue by customer, 2025", "€M", ["Customer A", "Customer B", "Customer C", "Others"],
          [("Revenue", [96, 71, 58, 230])], highlight=["Customer A", "Customer B", "Customer C"], show_values=True), mt="composition"))
    d.add(content("Volumes grew while price per unit fell every year", chart("combo", "Volume and price", "M units, €", ["2021", "2022", "2023", "2024", "2025"],
          [("Volume", [12.1, 13.4, 14.9, 16.2, 17.8]), ("Price", [9.8, 9.5, 9.1, 8.8, 8.4])], format={"decimals": 1}), mt="trend"))
    d.add(content("Margins vary from −4% to 22% across the twelve product lines", chart("bar", "EBIT margin by product line", "%",
          ["Line A", "Line B", "Line C", "Line D", "Line E", "Line F", "Line G", "Line H", "Line I", "Line J", "Line K", "Line L"],
          [("Margin", [22, 19, 17, 15, 12, 11, 9, 6, 4, 1, -2, -4])], highlight=["Line K", "Line L"]), mt="ranking"))
    d.add(content("Five segments grew at very different rates", chart("stacked_column", "Revenue by segment", "€M", ["2022", "2023", "2024", "2025"],
          [("Retail", [120, 126, 131, 135]), ("SME", [80, 92, 104, 118]), ("Corporate", [140, 138, 141, 139]), ("Public", [40, 44, 47, 52]), ("Online", [20, 31, 45, 63])]), mt="composition"))
    d.add(content("Los costes de energía se triplicaron en 2022 y no han vuelto al nivel previo", chart("line", "Coste de energía por tonelada", "€/t",
          ["2019", "2020", "2021", "2022", "2023", "2024", "2025"], [("Coste", [41.2, 38.7, 52.4, 128.9, 96.3, 84.1, 79.6])], format={"decimals": 1}), mt="trend"), es=True)
    d.add(content("Cash conversion recovered to 92% after two weak years", chart("column", "Cash conversion", "% of EBITDA", ["2021", "2022", "2023", "2024", "2025"],
          [("Conversion", [88, 71, 69, 84, 92])]), mt="trend", footnotes=["Cash conversion = operating cash flow / EBITDA.", "2022 includes a one-off tax payment."]))
    decks.append(d)

    # ── waterfall ───────────────────────────────────────────────────────────
    d = Deck("wf", "waterfall", "3–9 steps / subtotals / negatives / decimals / Spanish / with and without commentary", 5)
    d.add(content("Price increases more than offset inflation in 2025", {"type": "waterfall", "title": "EBITDA 2024 to 2025", "unit": "€M", "data": {"steps": [
        {"label": "2024", "value": 180, "type": "total"}, {"label": "Price", "value": 34}, {"label": "Inflation", "value": -22}, {"label": "2025", "type": "total"}]}}, mt="change_bridge"))
    d.add(content("Volume and mix add €61M; energy and wages take €38M", {"type": "waterfall", "title": "Operating profit bridge", "unit": "€M", "data": {"steps": [
        {"label": "2024", "value": 410, "type": "total"}, {"label": "Volume", "value": 41}, {"label": "Mix", "value": 20}, {"label": "Price", "value": 12},
        {"label": "Energy", "value": -21}, {"label": "Wages", "value": -17}, {"label": "Freight", "value": -6}, {"label": "Other", "value": 3}, {"label": "2025", "type": "total"}]}},
        mt="change_bridge", commentary={"points": ["Volume and mix add **€61M**", "Energy and wages take **€38M**"]}))
    d.add(content("El margen bruto cae 1,8 puntos por mermas y promociones", {"type": "waterfall", "title": "Margen bruto", "unit": "pp", "format": {"decimals": 1}, "data": {"steps": [
        {"label": "2024", "value": 31.4, "type": "total"}, {"label": "Mermas", "value": -0.9}, {"label": "Promociones", "value": -0.7}, {"label": "Mix", "value": -0.4},
        {"label": "Compras", "value": 0.2}, {"label": "2025", "type": "total"}]}}, mt="change_bridge"), es=True)
    d.add(content("Cost savings of €95M build up from five initiatives", {"type": "bridge", "title": "Run-rate savings", "unit": "€M", "data": {"steps": [
        {"label": "Procurement", "value": 32}, {"label": "Footprint", "value": 24}, {"label": "Automation", "value": 18}, {"label": "Subtotal", "type": "subtotal"},
        {"label": "Organisation", "value": 14}, {"label": "Travel", "value": 7}, {"label": "Total", "type": "total"}]}}, mt="change_bridge"))
    d.add(content("Net debt falls from €1.2bn to €0.9bn", {"type": "waterfall", "title": "Net debt", "unit": "€M", "data": {"steps": [
        {"label": "Dec 2024", "value": 1210, "type": "total"}, {"label": "Operating cash", "value": -420}, {"label": "Capex", "value": 180}, {"label": "Dividends", "value": 95},
        {"label": "Disposals", "value": -160}, {"label": "Dec 2025", "type": "total"}]}}, mt="change_bridge",
        commentary={"points": ["Disposals cut debt by **€160M**", "Capex stays at 6% of sales"]}))
    d.add(content("Headcount rises by 140 despite automation", {"type": "waterfall", "title": "FTE", "unit": "FTE", "data": {"steps": [
        {"label": "Start", "value": 2310, "type": "total"}, {"label": "Growth", "value": 260}, {"label": "Automation", "value": -150}, {"label": "Insourcing", "value": 30},
        {"label": "End", "type": "total"}]}}, mt="change_bridge"))
    d.add(content("La caja generada cubre la inversión y el dividendo", {"type": "waterfall", "title": "Flujo de caja 2025", "unit": "M€", "data": {"steps": [
        {"label": "EBITDA", "value": 640, "type": "total"}, {"label": "Circulante", "value": -85}, {"label": "Impuestos", "value": -110}, {"label": "Inversión", "value": -230},
        {"label": "Dividendo", "value": -120}, {"label": "Caja neta", "type": "total"}]}}, mt="change_bridge"), es=True)
    d.add(content("Revenue per customer rose $38 from price and fell $12 from churn mix", {"type": "waterfall", "title": "Revenue per customer", "unit": "$", "data": {"steps": [
        {"label": "2024", "value": 412, "type": "total"}, {"label": "Price", "value": 38}, {"label": "Upsell", "value": 19}, {"label": "Churn mix", "value": -12},
        {"label": "Discounts", "value": -9}, {"label": "2025", "type": "total"}]}}, mt="change_bridge"))
    d.add(content("Gross margin to net profit: where the 42 points go", {"type": "waterfall", "title": "From gross margin to net margin", "unit": "% of revenue", "data": {"steps": [
        {"label": "Gross margin", "value": 42, "type": "total"}, {"label": "Selling", "value": -14}, {"label": "Admin", "value": -8}, {"label": "R&D", "value": -6},
        {"label": "D&A", "value": -4}, {"label": "Interest", "value": -2}, {"label": "Tax", "value": -2}, {"label": "Net margin", "type": "total"}]}}, mt="change_bridge"))
    decks.append(d)

    # ── table ───────────────────────────────────────────────────────────────
    d = Deck("tb", "table", "2–14 rows / 3–7 columns / heatmap, harvey, scorecard / Spanish decimals / commentary", 6)
    d.add(content("Two decisions are needed this quarter", table_v("table", "Decisions", [{"label": "Decision", "width": 4.5}, "Owner", num("Impact (€M)")],
          [["Approve the pricing pilot", "CCO", 12], ["Approve the IT budget", "CIO", 8]])))
    d.add(content("Option B offers the best return for moderate risk", table_v("table", "Options", ["Option", num("NPV (€M)"), num("IRR (%)"), "Risk", "Time to impact"],
          [["A: organic", 85, 14, "Low", "3 years"], ["B: acquisition", 140, 18, "Medium", "1 year"], ["C: partnership", 60, 21, "Low", "2 years"], ["D: do nothing", 0, 0, "High", "—"]])))
    d.add(content("Twelve plants differ mainly on energy intensity", table_v("table", "Plant benchmark", ["Plant", num("Output (kt)"), num("Energy (MWh/t)", format={"decimals": 1}),
          num("Labour (€/t)"), num("Scrap (%)", format={"decimals": 1}), num("OEE (%)")],
          [[f"Plant {c}", o, e, lb, s, oee] for c, o, e, lb, s, oee in [("A", 210, 1.9, 38, 3.1, 74), ("B", 185, 2.4, 41, 3.8, 69), ("C", 164, 2.1, 39, 2.9, 72),
           ("D", 150, 3.0, 40, 4.4, 61), ("E", 142, 2.7, 37, 3.6, 66), ("F", 138, 2.2, 42, 3.0, 70), ("G", 131, 2.9, 36, 4.1, 63), ("H", 125, 2.0, 43, 2.7, 75),
           ("I", 118, 2.6, 39, 3.5, 67), ("J", 104, 3.3, 41, 4.8, 58), ("K", 97, 2.3, 44, 3.2, 71), ("L", 88, 3.1, 38, 4.5, 60)]]),
          commentary={"points": ["Plants D, J and L use **50% more energy** per tonne"]}))
    d.add(content("La rentabilidad por canal varía de −2,1% a 14,8%", table_v("table", "Cuenta de resultados por canal", ["Canal", num("Ventas (M€)", format={"decimals": 1}),
          num("Margen bruto (%)", format={"decimals": 1}), num("Coste servir (%)", format={"decimals": 1}), num("Resultado (%)", format={"decimals": 1})],
          [["Hipermercados", 412.5, 24.1, 9.8, 6.2], ["Supermercados", 386.0, 27.9, 10.4, 8.9], ["Proximidad", 154.2, 31.2, 12.1, 11.4], ["Online", 98.7, 29.5, 22.3, -2.1],
           ["Cash & carry", 77.3, 18.6, 3.9, 14.8]]), mt="comparison"), es=True)
    d.add(content("Margin erosion concentrates in fresh food and the south", table_v("heatmap", "Gross margin change", [{"label": "Category"}, num("North", format={"decimals": 1}),
          num("Centre", format={"decimals": 1}), num("South", format={"decimals": 1}), num("East", format={"decimals": 1}), num("Islands", format={"decimals": 1})],
          [["Fresh", -1.2, -1.9, -3.1, -1.4, -2.2], ["Bakery", -0.6, -0.8, -1.7, -0.4, -1.1], ["Dairy", 0.2, -0.1, -0.9, 0.1, -0.5], ["Grocery", 0.4, 0.3, -0.2, 0.5, 0.1],
           ["Drinks", 0.6, 0.5, 0.2, 0.7, 0.4], ["Household", 0.3, 0.2, 0.0, 0.4, 0.2]], unit="pp"), mt="comparison"))
    d.add(content("Vendor A scores best on four of five criteria", table_v("harvey_table", "Vendor assessment", [{"label": "Vendor", "width": 2.6}, "Functionality", "Cost", "Support",
          "Integration", "References"], [["Vendor A", 4, 3, 4, 4, 4], ["Vendor B", 3, 4, 2, 3, 3], ["Vendor C", 4, 2, 3, 2, 4]], highlight_rows=[0]), mt="comparison"))
    d.add(content("Five of seven initiatives are on track", table_v("scorecard", "Initiative status", [{"label": "Initiative", "width": 2.8}, "Owner", num("Target (€M)"),
          num("Delivered (€M)"), {"label": "Status", "kind": "rag"}, {"label": "Comment", "width": 3.2}],
          [["Procurement", "CPO", 30, 24, "G", "Ahead of plan"], ["Energy", "COO", 12, 10, "G", "Contracts signed"], ["Footprint", "COO", 25, 9, "A", "Two sites delayed"],
           ["Pricing", "CCO", 18, 15, "G", "Pilot extended"], ["Automation", "CIO", 15, 4, "R", "Supplier delay"], ["Travel", "CFO", 4, 4, "G", "Done"],
           ["Organisation", "CHRO", 10, 7, "G", "Consultation closed"]]), mt="status"))
    d.add(content("Three suppliers, three different risk profiles", table_v("table", "Supplier comparison", ["Supplier", num("Share of spend (%)"), num("Lead time (weeks)"), "Region"],
          [["North Metals", 46, 6, "Europe"], ["Pacific Alloys", 31, 14, "Asia"], ["Andes Mining", 23, 10, "LatAm"]]), mt="comparison",
          commentary={"points": ["Pacific Alloys has **the longest lead time**", "No supplier is dual-sourced today"]}))
    d.add(content("Previsión de tesorería por trimestre: el mínimo llega en el tercero", table_v("table", "Tesorería", ["Concepto", num("1T"), num("2T"), num("3T"), num("4T")],
          [["Saldo inicial", 120, 96, 71, 58], ["Cobros", 410, 395, 380, 455], ["Pagos", -434, -420, -393, -401], ["Saldo final", 96, 71, 58, 112]]), mt="trend"), es=True,
          footnotes=["Millones de euros.", "Incluye la línea de crédito no dispuesta de 50 M€."])
    decks.append(d)

    # ── matrix ──────────────────────────────────────────────────────────────
    d = Deck("mx", "matrix", "4–14 items / labels short and long / focus quadrant / portfolio bubbles / Spanish", 7)
    def items(*xs):
        return [{"label": lb, "x": x, "y": y} for lb, x, y in xs]
    d.add(content("Two initiatives are quick wins", {"type": "matrix_2x2", "data": {"x_label": "Ease", "y_label": "Value", "quadrants": ["Big bets", "Quick wins", "Avoid", "Fill-ins"],
          "focus": "TR", "items": items(("Pricing", 0.8, 0.8), ("Sourcing", 0.75, 0.65), ("New DC", 0.2, 0.75), ("Loyalty", 0.3, 0.3))}}, mt="positioning"))
    d.add(content("Eight of fourteen initiatives combine high value and low effort", {"type": "matrix_2x2", "data": {"x_label": "Ease of implementation", "y_label": "Value",
          "quadrants": ["Plan", "Do now", "Drop", "Fill-ins"], "focus": "TR", "items": items(*[(f"Initiative {i + 1}", x, y) for i, (x, y) in enumerate(
              [(0.82, 0.86), (0.71, 0.77), (0.66, 0.91), (0.88, 0.62), (0.59, 0.71), (0.77, 0.55), (0.92, 0.81), (0.55, 0.58), (0.2, 0.8), (0.31, 0.66), (0.15, 0.2),
               (0.4, 0.35), (0.25, 0.42), (0.36, 0.15)])])}}, mt="positioning"))
    d.add(content("Los mercados más atractivos son también los más competidos", {"type": "matrix_2x2", "data": {"x_label": "Intensidad competitiva", "y_label": "Atractivo del mercado",
          "quadrants": ["Defender", "Invertir", "Salir", "Mantener"], "focus": "TL", "items": items(("Madrid", 0.85, 0.9), ("Barcelona", 0.8, 0.85), ("Valencia", 0.55, 0.7),
          ("Sevilla", 0.4, 0.6), ("Bilbao", 0.35, 0.75), ("Zaragoza", 0.25, 0.45), ("Málaga", 0.6, 0.65))}}, mt="positioning"), es=True)
    d.add(content("Our brand is perceived as premium but not differentiated", {"type": "portfolio", "title": "Brand perception", "unit": "index; bubble = revenue",
          "highlight": ["Our brand"], "data": {"x_label": "Price perception", "y_label": "Differentiation", "quadrants": ["Niche", "Premium leaders", "Commodity", "Overpriced"],
          "focus": "BR", "items": [{"label": "Our brand", "x": 0.78, "y": 0.38, "size": 12}, {"label": "Brand A", "x": 0.82, "y": 0.8, "size": 18},
          {"label": "Brand B", "x": 0.3, "y": 0.25, "size": 9}, {"label": "Brand C", "x": 0.45, "y": 0.6, "size": 7}, {"label": "Brand D", "x": 0.2, "y": 0.7, "size": 4}]}}, mt="positioning"))
    d.add(content("Three suppliers are both critical and at risk", {"type": "matrix_2x2", "data": {"x_label": "Supply risk", "y_label": "Spend impact",
          "quadrants": ["Leverage", "Strategic", "Routine", "Bottleneck"], "focus": "TR", "items": items(("Steel coils", 0.82, 0.88), ("Chips", 0.91, 0.72), ("Resins", 0.68, 0.66),
          ("Packaging", 0.25, 0.7), ("Logistics", 0.3, 0.55), ("Office supplies", 0.1, 0.1), ("Paints", 0.7, 0.25), ("Fasteners", 0.2, 0.2))}}, mt="positioning"))
    d.add(content("Products with long names still need clear positions in the portfolio", {"type": "matrix_2x2", "data": {"x_label": "Market growth", "y_label": "Relative market share",
          "quadrants": ["Question marks", "Stars", "Dogs", "Cash cows"], "focus": "TR", "items": items(("Industrial coatings for marine use", 0.78, 0.82),
          ("Residential paints (premium range)", 0.35, 0.8), ("Wood stains and varnishes", 0.2, 0.3), ("Powder coatings for automotive suppliers", 0.85, 0.35),
          ("Adhesives and sealants", 0.55, 0.55))}}, mt="positioning"))
    d.add(content("Talent risk concentrates in four critical roles", {"type": "matrix_2x2", "data": {"x_label": "Flight risk", "y_label": "Impact of loss",
          "quadrants": ["Retain", "Act now", "Monitor", "Develop"], "focus": "TR", "items": items(("Data engineers", 0.85, 0.82), ("Plant managers", 0.66, 0.9),
          ("Key account managers", 0.72, 0.7), ("Pricing analysts", 0.8, 0.6), ("Finance controllers", 0.3, 0.6), ("HR partners", 0.2, 0.3))}}, mt="positioning"))
    d.add(content("Segmentos de clientes según valor y potencial", {"type": "matrix_2x2", "data": {"x_label": "Potencial de crecimiento", "y_label": "Valor actual",
          "quadrants": ["Mantener", "Priorizar", "Servir en digital", "Desarrollar"], "focus": "TR", "items": items(("Grandes cuentas", 0.45, 0.9), ("Pymes industriales", 0.8, 0.65),
          ("Autónomos", 0.7, 0.25), ("Sector público", 0.25, 0.6), ("Distribuidores", 0.55, 0.45))}}, mt="positioning"), es=True)
    decks.append(d)

    # ── comparison ──────────────────────────────────────────────────────────
    d = Deck("cp", "comparison", "2–4 columns / qualitative and quantitative / balanced and asymmetric / short and dense / Spanish", 8)
    def col(title, pts, **kw):
        return {"title": title, "points": pts, **kw}
    d.add(content("Building in-house is slower but keeps control of the data", columns=[col("Build", ["24 months", "€40M", "Full control"]),
          col("Buy", ["6 months", "€65M", "Vendor lock-in"], emphasis=True)]))
    d.add(content("Three options differ on speed, cost and control", columns=[col("Build", ["Full control", "24 months", "€40M"]), col("Buy", ["Fastest: 6 months", "€65M", "Integration risk"], emphasis=True),
          col("Partner", ["Shared control", "12 months", "€25M"])]))
    d.add(content("Leasing beats buying on cash, buying wins on total cost", columns=[col("Lease", ["Upfront cash €0", "Total cost €118M over 10 years", "Flexible exit after 5 years",
          "Maintenance included"], metric="€0", metric_label="upfront"), col("Buy", ["Upfront cash €95M", "Total cost €104M over 10 years", "Asset on the balance sheet",
          "Resale value of about €20M"], metric="€95M", metric_label="upfront", emphasis=True)]))
    d.add(content("La opción local es más cara pero reduce el riesgo de suministro", columns=[col("Proveedor local", ["Precio +12%", "Plazo 1 semana", "Sin aranceles"], emphasis=True),
          col("Proveedor asiático", ["Precio de referencia", "Plazo 9 semanas", "Arancel del 6%", "Riesgo de flete"])]), es=True)
    d.add(content("The new model changes five things for customers", columns=[col("Today", ["Branch visits for most products", "Paper forms", "Approval in 10 days",
          "One adviser per 2,000 clients", "Fees on every transfer"]), col("Target", ["App first, branch for advice", "Digital signature", "Approval in 24 hours",
          "One adviser per 600 premium clients", "Free transfers within the EU"], emphasis=True)]))
    d.add(content("Four sites were assessed; Valencia scores best on cost and labour", columns=[col("Madrid", ["Rent €9.5/m²", "Labour pool 120k", "Port 350 km"]),
          col("Valencia", ["Rent €5.8/m²", "Labour pool 95k", "Port 10 km"], emphasis=True), col("Zaragoza", ["Rent €4.9/m²", "Labour pool 40k", "Port 300 km"]),
          col("Sevilla", ["Rent €5.2/m²", "Labour pool 70k", "Port 120 km"])]))
    d.add(content("Option A is simple; option B needs more explanation but delivers more", columns=[col("Option A", ["Keep the current network"]),
          col("Option B", ["Close 6 depots and open 2 hubs", "Re-route 40% of volume through the hubs", "Saves €22M a year from 2028",
          "Needs €35M of capex and 18 months of dual running", "Union consultation required in three regions"], emphasis=True)]))
    d.add(content("Antes y después del plan: menos niveles, más alcance de control", columns=[col("Antes", ["7 niveles jerárquicos", "Alcance medio de 4", "12 direcciones"]),
          col("Después", ["5 niveles jerárquicos", "Alcance medio de 8", "7 direcciones"], emphasis=True)]), es=True)
    d.add(content("Insourcing and outsourcing differ on every dimension that matters", columns=[col("Insource", ["Cost €14M a year", "Service level under our control",
          "Hiring 120 people takes 9 months", "Fixed cost base"]), col("Outsource", ["Cost €11M a year", "SLA-based, penalties capped at 10%", "Live in 3 months",
          "Variable cost, 2-year minimum term"], emphasis=True), col("Hybrid", ["Cost €12.5M a year", "Core in-house, peaks outsourced", "Live in 6 months", "Two contracts to manage"])]))
    d.add(content("Our proposal versus the competitor's on the five criteria in the tender", columns=[col("Our proposal", ["Price €4.2M", "Go-live in 5 months", "24/7 support",
          "Local team of 12", "3 similar references"], emphasis=True), col("Competitor", ["Price €3.8M", "Go-live in 8 months", "Business-hours support", "Offshore team", "1 reference"])]))
    decks.append(d)

    # ── process ─────────────────────────────────────────────────────────────
    d = Deck("pr", "process", "3–7 steps / short and long labels / metrics per step / bullets / chevrons / Spanish", 9)
    d.add(content("Onboarding takes three steps", {"type": "process", "data": {"steps": steps(("Sign up", "Email"), ("Verify", "ID upload"), ("Order", "First basket"))}, "highlight": [1]}, mt="process"))
    d.add(content("Every claim goes through five steps; assessment takes the longest", {"type": "process", "data": {"steps": steps(("Notify", "Phone or web"), ("Triage", "Rules engine"),
          ("Assess", "Field adjuster, 9 days"), ("Approve", "Two signatures"), ("Pay", "Weekly batch"))}, "highlight": [2]}, mt="process"))
    d.add(content("The order-to-cash process has seven steps and three manual hand-offs", {"type": "process", "data": {"steps": steps(("Quote", "CRM"), ("Order", "EDI or email"),
          ("Credit check", "Manual"), ("Pick", "WMS"), ("Ship", "Carrier"), ("Invoice", "Manual"), ("Collect", "Manual reminders"))}, "highlight": [2, 5, 6]}, mt="process"))
    d.add(content("Each step of the new process has a measurable target", {"type": "process", "data": {"steps": steps(
          ("Capture", "EDI for top customers", {"metric": "0.3%", "metric_label": "order errors"}), ("Allocate", "Automated slotting", {"metric": "2 h", "metric_label": "to allocate"}),
          ("Pick", "Goods-to-person", {"metric": "99.7%", "metric_label": "pick accuracy"}), ("Deliver", "Dynamic routing", {"metric": "96%", "metric_label": "on time"}))}, "highlight": [2]},
          mt="process"))
    d.add(content("El alta de un proveedor tiene cuatro pasos y tarda 21 días", {"type": "process", "data": {"steps": steps(("Solicitud", "Compras"), ("Homologación", "Calidad, 12 días"),
          ("Alta en ERP", "Administración"), ("Primer pedido", "Compras"))}, "highlight": [1]}, mt="process"), es=True)
    d.add(content("Product development follows a gated process with five stages", {"type": "value_chain", "data": {"steps": steps("Discover", "Define", "Develop", "Validate", "Launch")},
          "highlight": [3]}, mt="process"))
    d.add(content("Hiring a nurse takes six steps and 68 days on average", {"type": "process", "data": {"steps": steps(
          ("Request position", ["Ward manager", "5 days"]), ("Approve budget", ["Finance", "11 days"]), ("Advertise and screen", ["HR", "18 days"]),
          ("Interview", ["Panel of 3", "9 days"]), ("Pre-employment checks", ["Occupational health and references", "21 days"]), ("Start", ["Induction", "4 days"]))},
          "highlight": [4]}, mt="process"))
    d.add(content("Three steps turn raw data into a monthly forecast", {"type": "process", "data": {"steps": steps(
          ("Collect and clean sales, inventory and promotion data from 14 country systems", None), ("Run the statistical forecast and flag outliers for review", None),
          ("Agree the consensus forecast in the monthly sales and operations meeting", None))}}, mt="process"))
    d.add(content("La tramitación de una licencia de obra tiene cinco fases", {"type": "process", "data": {"steps": steps(("Solicitud", ["Registro electrónico"]),
          ("Revisión técnica", ["Arquitecto municipal", "45 días"]), ("Informe jurídico", ["15 días"]), ("Resolución", ["Junta de gobierno"]), ("Notificación", ["10 días"]))},
          "highlight": [1]}, mt="process"), es=True)
    d.add(content("A customer complaint is resolved in four steps; escalation is the bottleneck", {"type": "process", "data": {"steps": steps(("Log", "Any channel", {"metric": "2 min"}),
          ("Classify", "Automatic", {"metric": "1 h"}), ("Escalate", "Specialist team", {"metric": "4.5 days"}), ("Resolve", "Call back", {"metric": "1 day"}))}, "highlight": [2]},
          mt="process"))
    decks.append(d)

    # ── roadmap ─────────────────────────────────────────────────────────────
    d = Deck("rm", "roadmap", "3–9 rows / 4–12 periods / today marker / multiple bars per row / Spanish", 10)
    def row(label, *bars):
        return {"label": label, "bars": [{"start": s, "end": e, "label": t, **({"highlight": True} if h else {})} for s, e, t, h in bars]}
    d.add(content("Three workstreams deliver within a year", {"type": "gantt", "data": {"periods": ["Q1", "Q2", "Q3", "Q4"], "rows": [row("Pricing", (0, 2, "Pilot", True)),
          row("Sourcing", (1, 3, "Tender", False)), row("Stores", (2, 4, "Refit", False))]}}, mt="plan"))
    d.add(content("The plan reaches full run-rate in six quarters across five workstreams", {"type": "gantt", "data": {"periods": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"], "today": 0.5,
          "rows": [row("Pricing", (0, 3, "Design and pilot", True)), row("Procurement", (0, 4, "Renegotiation", False)), row("Network", (2, 6, "DC consolidation", False)),
          row("Stores", (1, 5, "Refit waves", False)), row("IT", (0, 6, "ERP upgrade", False))]}}, mt="plan"))
    d.add(content("Nine workstreams over three years, with the ERP on the critical path", {"type": "gantt", "data": {"periods": ["H1 26", "H2 26", "H1 27", "H2 27", "H1 28", "H2 28"],
          "today": 0.3, "rows": [row(f"Workstream {i + 1}", (s, e, t, h)) for i, (s, e, t, h) in enumerate([(0, 2, "Quick wins", False), (0, 3, "Procurement", False),
          (1, 5, "ERP", True), (1, 3, "Pricing", False), (2, 4, "Footprint", False), (2, 6, "Automation", False), (3, 5, "Data", False), (3, 6, "Organisation", False),
          (4, 6, "Close-out", False)])]}}, mt="plan"))
    d.add(content("El plan de transformación se despliega en cuatro fases durante 2026", {"type": "gantt", "data": {"periods": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago",
          "Sep", "Oct", "Nov", "Dic"], "rows": [row("Diagnóstico", (0, 2, "Entrevistas y datos", False)), row("Diseño", (2, 5, "Nuevo modelo", True)),
          row("Piloto", (5, 8, "Dos regiones", False)), row("Despliegue", (8, 12, "Resto de regiones", False))]}}, mt="plan"), es=True)
    d.add(content("Each workstream has two phases: build, then roll out", {"type": "gantt", "data": {"periods": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"], "rows": [
          row("Digital sales", (0, 3, "Build", False), (3, 8, "Roll-out", True)), row("Pricing engine", (1, 4, "Build", False), (4, 7, "Roll-out", False)),
          row("Service hub", (2, 5, "Build", False), (5, 8, "Roll-out", False))]}}, mt="plan"))
    d.add(content("The migration runs product by product over eight quarters", {"type": "roadmap", "data": {"periods": ["2026 Q1", "Q2", "Q3", "Q4", "2027 Q1", "Q2", "Q3", "Q4"], "rows": [
          row("Deposits", (0, 3, "Migrate deposits to the cloud core", True)), row("Loans", (2, 5, "Migrate loans", False)), row("Cards", (4, 7, "Migrate cards", False)),
          row("Mainframe", (7, 8, "Decommission", False))]}}, mt="plan"))
    d.add(content("Hiring and training ramp up before the new plant opens", {"type": "gantt", "data": {"periods": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"],
          "today": 2, "rows": [row("Construction", (0, 7, "Building and utilities", False)), row("Equipment", (4, 8, "Install and commission", False)),
          row("Hiring", (3, 7, "220 operators", False)), row("Training", (5, 9, "Operator certification", True)), row("Start of production", (9, 10, "SOP", True))]}}, mt="plan"))
    d.add(content("Calendario de cierre de oficinas y apertura de centros de asesoramiento", {"type": "gantt", "data": {"periods": ["1T 26", "2T 26", "3T 26", "4T 26", "1T 27", "2T 27"],
          "rows": [row("Cierre de oficinas", (0, 4, "112 oficinas", False)), row("Centros de asesoramiento", (1, 5, "18 centros", True)), row("Gestores remotos", (0, 6, "Contratación", False))]}},
          mt="plan"), es=True)
    decks.append(d)

    # ── timeline ────────────────────────────────────────────────────────────
    d = Deck("tl", "timeline", "3–8 events / details / highlight / Spanish / long labels", 11)
    def ev(*xs):
        return [dict(zip(("date", "text", "detail"), x)) for x in xs]
    d.add(content("Three milestones gate the launch", {"type": "timeline", "data": {"events": ev(("Mar", "Pilot"), ("Jun", "Decision"), ("Oct", "Launch"))}, "highlight": [1]}, mt="sequence"))
    d.add(content("Four regulatory milestones set the pace of the launch", {"type": "timeline", "data": {"events": ev(("Jan 2026", "Consultation closes"), ("Apr 2026", "Draft rules"),
          ("Sep 2026", "Final rules", "Launch window opens"), ("Jan 2027", "Enforcement"))}, "highlight": [2]}, mt="sequence"))
    d.add(content("Eight milestones over two years; the go-live in Q3 2027 is the critical one", {"type": "timeline", "data": {"events": ev(("Q1 26", "Kick-off"), ("Q2 26", "Design signed off"),
          ("Q3 26", "Vendor selected"), ("Q4 26", "Build starts"), ("Q1 27", "Testing"), ("Q2 27", "Training"), ("Q3 27", "Go-live", "All countries"), ("Q4 27", "Hypercare ends"))},
          "highlight": [6]}, mt="sequence"))
    d.add(content("La integración culmina en cinco hitos", {"type": "timeline", "data": {"events": ev(("Ene", "Cierre de la compra"), ("Mar", "Nueva estructura directiva"),
          ("Jun", "Marca única", "Rebranding de 140 tiendas"), ("Sep", "Sistemas integrados"), ("Dic", "Sinergias completas"))}, "highlight": [2]}, mt="sequence"), es=True)
    d.add(content("The company's history explains today's fragmented portfolio", {"type": "timeline", "data": {"events": ev(("1998", "Founded as a regional distributor"),
          ("2006", "First acquisition", "Entry into foodservice"), ("2012", "Expansion into Portugal"), ("2017", "Two private-label factories bought"), ("2021", "Online launch"),
          ("2025", "Six business units, four ERP systems"))}}, mt="sequence"))
    d.add(content("Key dates for the bond refinancing", {"type": "timeline", "data": {"events": ev(("10 Feb", "Rating agency meetings"), ("3 Mar", "Investor roadshow"),
          ("17 Mar", "Pricing", "Target coupon below 5%"), ("24 Mar", "Settlement"))}, "highlight": [2]}, mt="sequence"))
    d.add(content("Hitos del programa con responsables y entregables", {"type": "timeline", "data": {"events": ev(("Oct 2026", "Nuevas condiciones comerciales", "Responsable: dirección comercial"),
          ("Dic 2026", "Licitación de transporte adjudicada", "Responsable: compras"), ("Mar 2027", "Primer almacén automatizado", "Responsable: operaciones"),
          ("Jun 2027", "Nuevo sistema de almacén", "Responsable: sistemas"), ("Dic 2027", "Red de almacenes rediseñada", "Responsable: dirección general"))}, "highlight": [3]},
          mt="sequence"), es=True)
    d.add(content("Six phases of the clinical programme to filing", {"type": "timeline", "data": {"events": ev(("2024", "Phase I complete"), ("2025", "Phase II readout"),
          ("2026", "Phase III start"), ("2027", "Interim analysis"), ("2028", "Primary endpoint", "Filing decision"), ("2029", "Approval expected"))}, "highlight": [4]}, mt="sequence"))
    decks.append(d)

    # ── operating_model ─────────────────────────────────────────────────────
    d = Deck("om", "operating_model", "2–6 layers / 2–6 cells / pillars / emphasis / Spanish", 12)
    def lay(label, items_, **kw):
        return {"label": label, "items": items_, **kw}
    d.add(content("The target model has three layers", {"type": "operating_model", "data": {"layers": [lay("Customers", ["Retail", "Business"]), lay("Operations", ["Stores", "Online"]),
          lay("Support", ["Finance", "HR"])]}}, mt="structure"))
    d.add(content("A central services layer supports four business units", {"type": "operating_model", "data": {"layers": [lay("Business units", ["Retail", "Wholesale", "Online", "Services"],
          emphasis=True), lay("Shared services", ["Finance", "HR", "IT", "Procurement"]), lay("Governance", ["Board", "Risk", "Audit"])], "pillars": [{"label": "Transformation office"}]}},
          mt="structure"))
    d.add(content("The new model separates customer, product and platform teams", {"type": "operating_model", "data": {"layers": [
          lay("Customer", ["Segment leads", "Key accounts", "Digital sales", "Service"]), lay("Product", ["Lending", "Payments", "Savings", "Insurance"], emphasis=True),
          lay("Platform", ["Data", "Core banking", "Cloud", "Security"]), lay("Enablers", ["Finance", "Risk", "People", "Legal"])], "pillars": [{"label": "Compliance"}, {"label": "Change"}]}},
          mt="structure"))
    d.add(content("El modelo operativo de compras tiene cuatro capas", {"type": "operating_model", "data": {"layers": [lay("Estrategia", ["Categorías", "Riesgo de proveedor"]),
          lay("Negociación", ["Compradores de categoría", "Licitaciones"], emphasis=True), lay("Operación", ["Pedidos", "Facturas", "Pagos"]), lay("Datos", ["Gasto", "Contratos"])]}},
          mt="structure"), es=True)
    d.add(content("The operating model runs on six layers, from strategy to infrastructure", {"type": "layers", "data": {"layers": [lay("Strategy", ["Portfolio", "Capital allocation"]),
          lay("Commercial", ["Marketing", "Sales", "Pricing"]), lay("Operations", ["Plants", "Logistics", "Quality"], emphasis=True), lay("Support", ["Finance", "HR", "Legal"]),
          lay("Technology", ["ERP", "MES", "Data"]), lay("Infrastructure", ["Cloud", "Network"])]}}, mt="structure"))
    d.add(content("Each layer lists who does what in the new structure", {"type": "operating_model", "data": {"layers": [
          lay("Front office", ["Relationship managers own the client plan", "Specialists join for complex deals", "Digital desk serves small clients"]),
          lay("Middle office", ["Credit analysts approve within 48 hours", "Pricing desk sets limits"], emphasis=True),
          lay("Back office", ["Operations hub in Lisbon", "Automated reconciliation"])]}}, mt="structure"))
    d.add(content("Two layers is enough for a small organisation", {"type": "operating_model", "data": {"layers": [lay("Delivery", ["Projects", "Support"], emphasis=True), lay("Back office", ["Admin"])]}},
          mt="structure"))
    d.add(content("Funciones centrales y locales en el nuevo modelo de tiendas", {"type": "operating_model", "data": {"layers": [lay("Central", ["Surtido", "Precios", "Marketing", "Compras"]),
          lay("Regional", ["Operaciones", "Personas"], emphasis=True), lay("Tienda", ["Atención al cliente", "Reposición", "Caja"])], "pillars": [{"label": "Datos"}]}},
          mt="structure"), es=True)
    decks.append(d)

    # ── architecture ────────────────────────────────────────────────────────
    d = Deck("ar", "architecture", "3–6 layers / few and many nodes / new and changed / flow left→right / Spanish", 13)
    def item(label, change=None, emph=False):
        x = {"label": label}
        if change:
            x["change"] = change
        if emph:
            x["emphasis"] = True
        return x
    d.add(content("Three layers: channels, services and data", {"type": "architecture", "data": {"layers": [lay("Channels", ["App", "Web"]), lay("Services", ["Orders", "Payments"]),
          lay("Data", ["Warehouse"])]}}, mt="structure"))
    d.add(content("The target architecture adds an API layer between channels and core", {"type": "architecture", "data": {"layers": [lay("Channels", ["Mobile", "Web", "Branch", "Partners"]),
          lay("Integration", [item("API gateway", "new", True), item("Event bus", "new")], emphasis=True), lay("Core", ["Deposits", "Loans", "Cards"]),
          lay("Data", [item("Customer master", "changed"), "Analytics"])]}}, mt="structure"))
    d.add(content("The current landscape has five layers and twenty components", {"type": "architecture", "data": {"layers": [
          lay("Experience", ["Web shop", "App", "Call centre", "Stores", "Marketplace"]), lay("Commerce", ["Catalogue", "Pricing", "Promotions", "Basket"]),
          lay("Fulfilment", ["OMS", "WMS", "TMS", "Returns"]), lay("Enterprise", ["ERP", "HR", "Finance", "Procurement"]), lay("Data", ["Lake", "BI", "ML platform"])]}}, mt="structure"))
    d.add(content("La plataforma de datos tiene cuatro capas", {"type": "architecture", "data": {"layers": [lay("Consumo", ["Cuadros de mando", "Modelos"]),
          lay("Servicio", [item("Catálogo de datos", "new")]), lay("Procesamiento", ["Ingesta", "Calidad", "Transformación"], emphasis=True), lay("Fuentes", ["ERP", "CRM", "Web"])]}},
          mt="structure"), es=True)
    d.add(content("Orders flow from four channels through one order service to fulfilment", {"type": "flow", "data": {"nodes": [
          {"id": "a", "label": "Web", "col": 0, "row": 0}, {"id": "b", "label": "App", "col": 0, "row": 1}, {"id": "c", "label": "Stores", "col": 0, "row": 2},
          {"id": "d", "label": "Marketplace", "col": 0, "row": 3}, {"id": "o", "label": "Order service", "col": 1, "row": 1, "emphasis": True},
          {"id": "w", "label": "Warehouse", "col": 2, "row": 0}, {"id": "s", "label": "Store pick", "col": 2, "row": 2}],
          "edges": [{"from": "a", "to": "o"}, {"from": "b", "to": "o"}, {"from": "c", "to": "o"}, {"from": "d", "to": "o"}, {"from": "o", "to": "w"}, {"from": "o", "to": "s"}]}},
          mt="flow"))
    d.add(content("Data moves left to right from sources to decisions", {"type": "flow", "data": {"nodes": [{"id": "s", "label": "Sources", "col": 0}, {"id": "i", "label": "Ingestion", "col": 1},
          {"id": "m", "label": "Model", "col": 2, "emphasis": True}, {"id": "d", "label": "Decisions", "col": 3}],
          "edges": [{"from": "s", "to": "i"}, {"from": "i", "to": "m"}, {"from": "m", "to": "d"}]}}, mt="flow"))
    d.add(content("Payments run through two parallel paths that meet at the ledger", {"type": "flow", "data": {"nodes": [
          {"id": "c", "label": "Card terminal", "col": 0, "row": 0}, {"id": "a", "label": "Acquirer", "col": 1, "row": 0}, {"id": "s", "label": "Scheme", "col": 2, "row": 0},
          {"id": "w", "label": "Wallet app", "col": 0, "row": 1}, {"id": "p", "label": "Payment gateway", "col": 1, "row": 1, "emphasis": True},
          {"id": "l", "label": "Ledger", "col": 3, "row": 0}], "edges": [{"from": "c", "to": "a"}, {"from": "a", "to": "s"}, {"from": "s", "to": "l"},
          {"from": "w", "to": "p"}, {"from": "p", "to": "l"}]}}, mt="flow"))
    d.add(content("The procurement platform connects four user groups to eleven back-end services", {"type": "architecture", "data": {"layers": [
          lay("Users", ["Requesters", "Buyers", "Approvers", "Suppliers"]), lay("Front end", [item("Guided buying", "new", True), "Supplier portal", "Mobile approvals"], emphasis=True),
          lay("Services", ["Catalogue", "Sourcing", "Contracts", "Invoices", "Payments", "Risk"]), lay("Integration", ["ERP connector", item("Event bus", "changed")]),
          lay("Data", ["Spend cube", "Supplier master"])]}}, mt="structure"))
    d.add(content("Six layers, from devices to the cloud, in the IoT platform", {"type": "architecture", "data": {"layers": [lay("Devices", ["Sensors", "Meters", "Gateways"]),
          lay("Connectivity", ["LoRaWAN", "4G"]), lay("Edge", [item("Edge compute", "new")]), lay("Platform", ["Device registry", item("Stream processing", "new", True), "Storage"],
          emphasis=True), lay("Applications", ["Monitoring", "Billing", "Maintenance"]), lay("Cloud", ["Compute", "Identity"])]}}, mt="structure"))
    d.add(content("El nuevo sistema sustituye tres aplicaciones por una plataforma", {"type": "architecture", "data": {"layers": [lay("Usuarios", ["Ciudadanos", "Funcionarios"]),
          lay("Aplicación", [item("Plataforma de expedientes", "new", True)], emphasis=True), lay("Integración", ["Registro", "Pagos", "Notificaciones"]),
          lay("Infraestructura", ["Nube pública"])]}}, mt="structure"), es=True)
    decks.append(d)

    # ── hierarchy ───────────────────────────────────────────────────────────
    d = Deck("hi", "hierarchy", "org chart / driver tree / issue tree / pyramid / depth 2–3 / 3–8 leaves / Spanish", 14)
    d.add(content("A small team of three reports to the COO", {"type": "org_chart", "data": {"root": {"label": "COO", "children": [{"label": "Operations"}, {"label": "Logistics", "highlight": True},
          {"label": "Quality"}]}}}, mt="hierarchy"))
    d.add(content("The transformation office coordinates eight functions", {"type": "org_chart", "data": {"root": {"label": "CEO", "children": [{"label": "Transformation office",
          "highlight": True, "children": [{"label": f"Function {i}", "sub": "Lead"} for i in range(1, 9)]}]}}}, mt="hierarchy"))
    d.add(content("Network and warehousing explain €31M of the €44M gap", {"type": "driver_tree", "format": {"prefix": "€", "suffix": "M"}, "data": {"root": {"label": "Gap to peers", "value": 44,
          "children": [{"label": "Network", "value": 19, "highlight": True, "children": [{"label": "Depots", "value": 11}, {"label": "Truck fill", "value": 8}]},
          {"label": "Warehousing", "value": 12, "highlight": True, "children": [{"label": "Picking", "value": 9}, {"label": "Overtime", "value": 3}]},
          {"label": "Overheads", "value": 13}]}}}, mt="hierarchy"))
    d.add(content("La caída del margen tiene dos causas principales", {"type": "tree", "data": {"root": {"label": "Margen −2 pp", "children": [
          {"label": "Precio", "children": [{"label": "Promociones"}, {"label": "Mix de canal"}]}, {"label": "Coste", "highlight": True, "children": [{"label": "Energía"}, {"label": "Mermas"}]}]}}},
          mt="hierarchy"), es=True)
    d.add(content("Three tiers of support, most pupils need only the first", {"type": "pyramid", "data": {"levels": [{"label": "Intensive", "text": "8% of pupils"},
          {"label": "Targeted", "text": "22% of pupils"}, {"label": "Universal", "text": "All pupils"}]}}, mt="hierarchy"))
    d.add(content("Revenue growth breaks down into price, volume and mix", {"type": "driver_tree", "format": {"suffix": "%"}, "data": {"root": {"label": "Revenue growth", "value": 9,
          "children": [{"label": "Price", "value": 5, "highlight": True}, {"label": "Volume", "value": 3}, {"label": "Mix", "value": 1}]}}}, mt="hierarchy"))
    d.add(content("The new regional structure has two levels below the country manager", {"type": "org_chart", "data": {"root": {"label": "Country manager", "sub": "Spain", "children": [
          {"label": "North", "sub": "Regional director", "children": [{"label": "Galicia"}, {"label": "Basque Country"}]},
          {"label": "Centre", "sub": "Regional director", "highlight": True, "children": [{"label": "Madrid"}, {"label": "Castilla"}]},
          {"label": "South", "sub": "Regional director", "children": [{"label": "Andalucía"}, {"label": "Murcia"}]}]}}}, mt="hierarchy"))
    d.add(content("Cinco niveles de necesidad del cliente, de lo básico a la lealtad", {"type": "pyramid", "data": {"levels": [{"label": "Recomendación", "text": "El cliente nos recomienda"},
          {"label": "Lealtad", "text": "Repite sin buscar alternativas"}, {"label": "Experiencia", "text": "Compra sin fricciones"}, {"label": "Surtido", "text": "Encuentra lo que busca"},
          {"label": "Precio", "text": "Precio competitivo"}]}}, mt="hierarchy"), es=True)
    d.add(content("Why are deliveries late? Three branches of the issue tree", {"type": "tree", "data": {"root": {"label": "Late deliveries", "children": [
          {"label": "Planning", "children": [{"label": "Forecast error"}, {"label": "Late orders"}]}, {"label": "Warehouse", "highlight": True, "children": [{"label": "Picking errors"},
          {"label": "Staff shortages"}, {"label": "Stock-outs"}]}, {"label": "Transport", "children": [{"label": "Carrier capacity"}, {"label": "Traffic"}]}]}}}, mt="hierarchy"))
    decks.append(d)

    # ── segmentation ────────────────────────────────────────────────────────
    d = Deck("sg", "segmentation", "mekko 2–6 columns / tile map / funnel / Spanish", 15)
    d.add(content("Discount and online are where our share is lowest", {"type": "mekko", "title": "Share by channel", "unit": "% of channel; width = channel size (€bn)", "highlight": ["Us"],
          "data": {"order": ["Us", "Competitor A", "Others"], "columns": [{"label": "Discount", "total": 38, "parts": {"Us": 5, "Competitor A": 41, "Others": 54}},
          {"label": "Supermarkets", "total": 52, "parts": {"Us": 14, "Competitor A": 18, "Others": 68}}, {"label": "Online", "total": 14, "parts": {"Us": 4, "Competitor A": 22, "Others": 74}}]}},
          mt="composition"))
    d.add(content("Two segments make up 70% of the market and we lead in neither", {"type": "mekko", "title": "Market by segment and player", "unit": "% of segment; width = segment size (€M)",
          "highlight": ["Us"], "data": {"order": ["Us", "Leader", "Challenger", "Others"], "columns": [{"label": "Enterprise", "total": 420, "parts": {"Us": 12, "Leader": 38, "Challenger": 21, "Others": 29}},
          {"label": "Mid-market", "total": 310, "parts": {"Us": 18, "Leader": 24, "Challenger": 26, "Others": 32}}, {"label": "SMB", "total": 190, "parts": {"Us": 31, "Leader": 9, "Challenger": 14, "Others": 46}},
          {"label": "Public", "total": 95, "parts": {"Us": 6, "Leader": 44, "Challenger": 10, "Others": 40}}, {"label": "Education", "total": 40, "parts": {"Us": 22, "Leader": 15, "Challenger": 8, "Others": 55}}]}},
          mt="composition"))
    d.add(content("Las ventas por habitante son más altas en el noreste", {"type": "tile_map", "title": "Ventas por habitante, 2025", "unit": "€", "highlight": ["CT", "AR"],
          "data": {"preset": "spain", "values": {"GA": 41, "AS": 38, "CB": 44, "PV": 52, "NA": 55, "CL": 36, "RI": 47, "AR": 61, "CT": 66, "MD": 58, "EX": 29, "CM": 33, "VC": 49,
          "IB": 51, "AN": 34, "MC": 37, "CN": 31}}}, mt="geography"), es=True)
    d.add(content("Most of the market sits in two age groups where our share is below 10%", {"type": "segmentation", "title": "Customers by age group and provider",
          "unit": "% of group; width = customers (M)", "highlight": ["Us"], "data": {"order": ["Us", "Bank A", "Bank B", "Others"], "columns": [
          {"label": "18–29", "total": 4.1, "parts": {"Us": 6, "Bank A": 21, "Bank B": 30, "Others": 43}}, {"label": "30–44", "total": 6.8, "parts": {"Us": 9, "Bank A": 27, "Bank B": 24, "Others": 40}},
          {"label": "45–64", "total": 7.2, "parts": {"Us": 18, "Bank A": 26, "Bank B": 19, "Others": 37}}, {"label": "65+", "total": 5.3, "parts": {"Us": 24, "Bank A": 29, "Bank B": 12, "Others": 35}}]}},
          mt="composition"))
    d.add(content("Premium is a small segment where we already lead", {"type": "mekko", "title": "Share by price tier", "unit": "% of tier; width = tier size (€bn)", "highlight": ["Us"],
          "data": {"order": ["Us", "Brand A", "Private label"], "columns": [{"label": "Premium", "total": 3.1, "parts": {"Us": 34, "Brand A": 41, "Private label": 25}},
          {"label": "Mainstream", "total": 9.4, "parts": {"Us": 11, "Brand A": 29, "Private label": 60}}]}}, mt="composition"))
    d.add(content("La penetración del servicio varía del 12% al 48% entre comunidades", {"type": "tile_map", "title": "Penetración del servicio", "unit": "% de hogares",
          "highlight": ["EX", "CN"], "data": {"preset": "spain", "values": {"GA": 21, "AS": 24, "CB": 28, "PV": 44, "NA": 41, "CL": 19, "RI": 33, "AR": 30, "CT": 46, "MD": 48, "EX": 12,
          "CM": 17, "VC": 35, "IB": 39, "AN": 22, "MC": 25, "CN": 14}}}, mt="geography"), es=True)
    d.add(content("Six customer segments differ by size and profitability", {"type": "mekko", "title": "Revenue by segment and margin band", "unit": "% of segment; width = revenue (€M)",
          "data": {"order": ["High margin", "Medium margin", "Low margin"], "columns": [{"label": s, "total": t, "parts": dict(zip(["High margin", "Medium margin", "Low margin"], p))}
          for s, t, p in [("Grocers", 120, [20, 50, 30]), ("Hotels", 85, [45, 35, 20]), ("Hospitals", 60, [10, 40, 50]), ("Schools", 45, [5, 35, 60]), ("Offices", 70, [40, 40, 20]),
          ("Airlines", 30, [60, 30, 10])]]}}, mt="composition"))
    d.add(content("Three channels, two of them dominated by a single player", {"type": "mekko", "title": "Share by channel", "unit": "% of channel; width = channel size ($bn)",
          "data": {"order": ["Player 1", "Player 2", "Player 3", "Long tail"], "columns": [{"label": "Retail", "total": 2.2, "parts": {"Player 1": 61, "Player 2": 12, "Player 3": 8, "Long tail": 19}},
          {"label": "Wholesale", "total": 1.4, "parts": {"Player 1": 18, "Player 2": 55, "Player 3": 9, "Long tail": 18}},
          {"label": "Direct", "total": 0.6, "parts": {"Player 1": 22, "Player 2": 20, "Player 3": 25, "Long tail": 33}}]}}, mt="composition"))
    decks.append(d)

    # ── text_exhibit ────────────────────────────────────────────────────────
    d = Deck("tx", "text_exhibit", "one argument / three bullets / long paragraph / short narrative / quote-like / Spanish", 16)
    d.add(content("Only one argument is needed: the contract expires in March", {"type": "bullets", "data": {"points": ["The supplier contract expires in March and cannot be extended"]}}, mt="argument"))
    d.add(content("We should act before the summer, for three reasons", {"type": "bullets", "data": {"points": ["Prices rise 8% in July", "Two competitors are already switching", "The tender takes four months"]}},
          mt="argument"))
    d.add(content("The case for change fits in one paragraph", {"type": "bullets", "data": {"points": [
          "Our cost base grew 9% a year for five years while revenue grew 4%, and the gap is now structural: two thirds of the increase comes from overheads that do not scale "
          "with volume, from duplicated regional functions, and from IT systems that were never integrated after the last three acquisitions. Without a reset, operating margin "
          "falls below 5% by 2027, below the level at which we can fund the investment the strategy requires."]}}, mt="argument"))
    d.add(content("Tres condiciones para que el piloto sea un éxito", {"type": "bullets", "data": {"points": ["Un responsable a tiempo completo en cada tienda",
          "Datos de ventas diarios, no semanales", "Libertad para ajustar precios sin aprobación central"]}}, mt="argument"), es=True)
    d.add(content("What customers told us", {"type": "bullets", "data": {"points": ["“I do not mind paying more if it arrives when you say it will.”",
          "“The app is fine; the problem is when something goes wrong.”"]}}, mt="argument"))
    d.add(content("Five risks could delay the plan; each has a mitigation", {"type": "bullets", "data": {"points": ["Supplier delays: dual-source the two critical components",
          "Union opposition: early consultation and a no-redundancy guarantee for 2026", "IT readiness: freeze other projects during the ERP cut-over",
          "Customer churn during migration: dedicated retention team", "Cost overrun: 15% contingency released only by the steering committee"]}}, mt="argument"))
    d.add(content("La historia en breve: crecimos rápido y ahora toca consolidar", {"type": "bullets", "data": {"points": [
          "En cinco años pasamos de 40 a 160 tiendas, abrimos dos países y lanzamos la venta online. Ese crecimiento dejó una organización con procesos distintos en cada país y "
          "márgenes que no han seguido a las ventas."]}}, mt="argument"), es=True)
    d.add(content("Our principles for the new pricing policy", {"type": "bullets", "data": {"points": ["Prices reflect value to the customer, not cost plus margin",
          "One list price per country, discounts only against volume commitments", "Every exception is approved, recorded and reviewed quarterly"]}}, mt="argument"))
    d.add(content("Cuatro cambios en la política de viajes reducen el gasto un 18%", {"type": "bullets", "data": {"points": ["Reserva obligatoria con 14 días de antelación",
          "Clase turista en vuelos de menos de cinco horas", "Tope de 120 € por noche de hotel en ciudades de nivel 2", "Aprobación del director para viajes internacionales"]}},
          mt="argument"), es=True)
    d.add(content("What we heard in twelve interviews with store managers", {"type": "bullets", "data": {"points": [
          "Staffing: rosters arrive too late to plan childcare, so people swap shifts informally",
          "Systems: the ordering tool needs three screens for one product and crashes at peak times",
          "Targets: half of the KPIs on the store dashboard are not under the manager's control",
          "Recognition: good months are never mentioned, bad months are escalated within hours",
          "Training: new starters learn on the job from whoever is on shift",
          "Communication: head-office emails arrive after customers have already asked about promotions"]}}, mt="argument"))
    d.add(content("Two conditions must hold before we sign", {"type": "bullets", "data": {"points": ["Due diligence confirms the €40M of synergies",
          "The regulator clears the deal without remedies"]}}, mt="argument"))
    d.add(content("The pilot shows what works in stores", {"type": "bullets", "data": {"points": ["Stores with a dedicated lead improved twice as fast",
          "Daily data mattered more than the pricing algorithm", "Staff accepted the change once they saw their own results"]}}, mt="argument",
          commentary={"points": ["Roll out with the same three conditions"]}))
    decks.append(d)

    return [dk.write() for dk in decks]


def main() -> int:
    check = "--check" in sys.argv
    if check:
        before = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("2*_battery_*.json")}
    paths = build()
    if check:
        after = {p.name: p.read_text(encoding="utf-8") for p in paths}
        if before != after:
            print("battery cases are out of date: run scripts/make_archetype_battery.py", file=sys.stderr)
            return 1
    print(f"{len(paths)} battery decks, {sum(len(json.loads(p.read_text())['slides']) for p in paths)} slides")
    return 0


if __name__ == "__main__":
    sys.exit(main())
