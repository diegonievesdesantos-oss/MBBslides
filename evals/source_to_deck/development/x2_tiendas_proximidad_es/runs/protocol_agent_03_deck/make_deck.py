import json

K = {"decimals": 0, "thousands": False}
XLS = "tiendas_proximidad_2025.xlsx"
PDF = "informe_inmobiliario.pdf"
MD = "propuesta_direccion_financiera.md"


def ev(*pairs):
    return [{"fact": f, "claim": c} for f, c in pairs]


deck = {
    "meta": {
        "title": "Tiendas de proximidad: cerrar 15, no 40",
        "subtitle": "Decisión sobre las 40 tiendas en pérdidas y su efecto real en el EBITDA 2026-2027",
        "client": "Consejo de administración",
        "date": "Octubre 2026",
        "deck_type": "board_presentation",
        "theme": "meridian",
        "confidentiality": "Confidencial",
    },
    "storyline": {
        "framework": "SCR",
        "audience": "Consejero delegado, directora financiera y director de expansión",
        "decision_sought": "Rechazar el cierre de las 40 tiendas y aprobar el cierre selectivo de las 15 tiendas A con ruptura en 2026",
        "governing_thought": "No cerremos las 40 tiendas: la mejora real de EBITDA es de 1596 k€, no 5,2 M€; cerremos en 2026 las 15 tiendas A con ruptura, negociemos las 7 restantes y mantengamos las 18 B",
        "key_line": [
            {"id": "K1", "role": "problem", "message": "La propuesta sobrevalora el ahorro y el coste de cierre"},
            {"id": "K2", "role": "diagnosis", "message": "La pérdida evitable está solo en el grupo A; el grupo B aporta y está en rampa"},
            {"id": "K3", "role": "solution", "message": "Cerrar las 15 tiendas A con ruptura es la opción más barata en la misma base"},
            {"id": "K4", "role": "next_steps", "message": "Negociar antes de cerrar las 7 tiendas A sin ruptura"},
        ],
    },
    "slides": [
        {"id": "S0", "kind": "cover", "title": "Tiendas de proximidad: cerrar 15, no 40",
         "subtitle": "Decisión sobre las 40 tiendas en pérdidas y su efecto real en el EBITDA"},
        {
            "id": "S1", "kind": "exec_summary", "tracker": "Resumen ejecutivo",
            "purpose": "Respuesta completa en una página: rechazar el cierre total y aprobar el cierre selectivo",
            "headline": "Cerrar 15 tiendas A con ruptura, no las 40: la mejora real es 1596 k€, no 5,2 M€",
            "evidence": ev(("C0032", "Mejora real de cerrar las 40: 1596 k€"), ("F0215", "La propuesta promete 5,2 M€"),
                           ("F0208", "Pérdida 2025 de las 40: 5196 k€"), ("F0209", "Coste central asignado: 3600 k€"),
                           ("F0207", "40 tiendas"), ("F0201", "22 tiendas A"), ("F0204", "18 tiendas B"),
                           ("C0002", "A pierde 1920 k€ antes de coste central"), ("C0003", "B aporta 324 k€"),
                           ("F0210", "Alquiler 16% frente a 9%"), ("F0211", "15 contratos con ruptura en 2026"),
                           ("C0031", "Mejora anual 1500 k€"), ("C0008", "Coste de cierre 1500 k€"),
                           ("C0025", "Coste 2026-2027 opción selectiva 9540 k€"), ("C0024", "Coste 2026-2027 cierre total 15598 k€"),
                           ("C0009", "Cerrar las 7 A sin ruptura: 1750 k€"), ("C0007", "Pérdida de las 7: 420 k€ al año")),
            "visual": {"type": "statements", "data": {"style": "scr", "items": [
                {"label": "Problema", "title": "La mejora de 5,2 M€ no existe",
                 "text": "3600 k€ son coste central que no desaparece: la mejora real es 1596 k€."},
                {"label": "Diagnóstico", "title": "La pérdida evitable está en las 22 A",
                 "text": "Pierden 1920 k€ por un alquiler del 16% (red: 9%); B aporta 324 k€."},
                {"label": "Solución", "title": "Cerrar las 15 A con ruptura es lo más barato",
                 "text": "1500 k€ de mejora anual por 1500 k€ de cierre; 9540 k€ en 2026-2027 frente a 15598 k€."},
                {"label": "Siguiente paso", "title": "Negociar las 7 A sin ruptura antes de cerrar",
                 "text": "Cerrarlas costaría 1750 k€ para evitar 420 k€ al año; revisión en junio."},
            ]}},
            "source": f"{XLS}; {PDF}; {MD}",
        },
        {
            "id": "S2", "section": "K1", "tracker": "La propuesta sobrevalora el ahorro",
            "purpose": "Desmontar la cifra de 5,2 M€: el coste central asignado no desaparece al cerrar",
            "headline": "Cerrar las 40 mejora el EBITDA 1596 k€, no 5196 k€: 3600 k€ son coste central que permanece",
            "supporting_message": "El coste central asignado se reparte entre el resto de la red si se cierra una tienda",
            "message_type": "change_bridge",
            "evidence": ev(("F0208", "Pérdida de EBITDA 2025 de las 40 tiendas: −5196 k€"),
                           ("F0215", "La propuesta promete +5,2 M€"),
                           ("F0209", "Coste central asignado a las 40: 3600 k€"),
                           ("F0217", "90 k€ de coste central por tienda"),
                           ("C0032", "Mejora real: 1596 k€"),
                           ("C0002", "Grupo A antes de coste central: −1920 k€"),
                           ("C0003", "Grupo B antes de coste central: +324 k€"),
                           ("C0017", "69,3% de la pérdida es coste central"), ("F0207", "40 tiendas")),
            "visual": {
                "type": "waterfall", "title": "Mejora anual de EBITDA al cerrar las 40 tiendas", "unit": "k€",
                "format": K, "proof_label": False, "delta_colors": "muted", "highlight": ["Coste central que permanece"],
                "data": {"steps": [
                    {"label": "Mejora prometida (pérdida 2025)", "value": 5196, "type": "total"},
                    {"label": "Coste central que permanece", "value": -3600, "type": "delta"},
                    {"label": "Mejora real", "type": "total"},
                ]},
            },
            "commentary": {"title": "El 69% de la pérdida no se ahorra", "points": [
                "**Coste central:** 90 k€ por tienda (sistemas, logística, compras) que se reparte entre el resto de la red",
                "**1596 k€ reales:** el grupo A pierde 1920 k€ antes de coste central y el grupo B aporta 324 k€",
            ]},
            "source": f"{XLS} (Resumen, Notas controller); {MD}",
        },
        {
            "id": "S3", "section": "K1", "tracker": "La propuesta sobrevalora el coste",
            "purpose": "Corregir el coste de cierre de la propuesta",
            "headline": "Cerrar las 40 cuesta 7750 k€, no 10 M€: 15 contratos A rompen en 2026 a 100 k€",
            "supporting_message": "La propuesta aplica 250 k€ a todas las tiendas; el informe inmobiliario fija 100 k€ para las 15 con ruptura",
            "message_type": "composition",
            "evidence": ev(("F0216", "Propuesta: 250 k€ por tienda, 10 M€ en total"),
                           ("C0034", "40 × 250 k€ = 10000 k€"),
                           ("F0207", "40 tiendas"),
                           ("F0211", "15 contratos con ruptura en 2026 a 100.000 € por tienda"),
                           ("A001", "Supuesto: 100 k€ por tienda con ruptura, a confirmar por contrato"),
                           ("F0204", "18 tiendas B"),
                           ("C0008", "15 × 100 k€ = 1500 k€"),
                           ("C0009", "7 × 250 k€ = 1750 k€"),
                           ("C0010", "18 × 250 k€ = 4500 k€"),
                           ("C0011", "Coste real de cerrar las 40: 7750 k€")),
            "visual": {
                "type": "table", "title": "Coste de cerrar las 40 tiendas", "unit": "k€",
                "columns": [
                    {"label": "Grupo de tiendas", "kind": "text", "width": 4.2},
                    {"label": "Tiendas", "kind": "number", "format": K},
                    {"label": "Coste por tienda", "kind": "number", "format": K},
                    {"label": "Coste de cierre", "kind": "number", "format": K},
                ],
                "rows": [
                    ["A con ruptura en 2026", 15, {"value": 100, "bound": "estimate"}, {"value": 1500, "bound": "estimate"}],
                    ["A sin ruptura", 7, 250, 1750],
                    ["B (aperturas 2023-2024)", 18, 250, 4500],
                    {"cells": ["Coste real de cerrar las 40", 40, None, {"value": 7750, "bound": "estimate"}], "style": "total"},
                    {"cells": ["Según la propuesta financiera", 40, 250, 10000], "style": "highlight"},
                ],
            },
            "takeaway": "La propuesta sobrestima el cierre total en 2250 k€ al aplicar 250 k€ también a las 15 tiendas con ruptura",
            "footnotes": ["~ Supuesto: 100 k€ por tienda con ruptura (informe inmobiliario), a confirmar contrato a contrato antes de notificar"],
            "source": f"{PDF}; {MD}; {XLS}",
        },
        {
            "id": "S4", "section": "K2", "tracker": "La pérdida evitable está en el grupo A",
            "purpose": "Localizar la pérdida evitable: separar el problema estructural (A) de la rampa (B)",
            "headline": "Sin coste central, A pierde 1920 k€ por su alquiler del 16%, mientras B aporta 324 k€",
            "supporting_message": "El problema es el contrato de alquiler del grupo A, no el formato de proximidad",
            "message_type": "comparison",
            "evidence": ev(("F0201", "22 tiendas A"), ("F0204", "18 tiendas B"), ("F0207", "40 tiendas"),
                           ("F0202", "EBITDA 2025 grupo A: −3900 k€"), ("F0203", "Coste central grupo A: 1980 k€"),
                           ("F0205", "EBITDA 2025 grupo B: −1296 k€"), ("F0206", "Coste central grupo B: 1620 k€"),
                           ("F0208", "EBITDA 2025 total: −5196 k€"), ("F0209", "Coste central total: 3600 k€"),
                           ("C0002", "A antes de coste central: −1920 k€"), ("C0003", "B antes de coste central: +324 k€"),
                           ("C0001", "Total antes de coste central: −1596 k€"),
                           ("F0210", "Alquiler del grupo A: 16% de las ventas frente al 9% de la red"),
                           ("C0018", "7 pp por encima de la red")),
            "visual": {
                "type": "table", "title": "EBITDA 2025 por grupo, con y sin coste central asignado", "unit": "k€",
                "columns": [
                    {"label": "Grupo", "kind": "text", "width": 3.4},
                    {"label": "Tiendas", "kind": "number", "format": K},
                    {"label": "EBITDA 2025", "kind": "number", "format": K},
                    {"label": "Coste central asignado", "kind": "number", "format": K},
                    {"label": "Antes de coste central", "kind": "delta", "format": K, "good": "up"},
                ],
                "rows": [
                    ["A: alquiler alto", 22, -3900, 1980, -1920],
                    ["B: aperturas 2023-2024", 18, -1296, 1620, 324],
                    {"cells": ["Total", 40, -5196, 3600, -1596], "style": "total"},
                ],
                "highlight_columns": [4],
            },
            "commentary": {"title": "El alquiler explica la pérdida de A", "points": [
                "**Alquiler de A:** 16% de las ventas frente al 9% de media de la red, 7 pp más",
                "**Grupo B:** positivo antes de coste central; su pérdida contable es coste asignado",
            ]},
            "footnotes": ["Alquiler con gastos comunes, según el informe inmobiliario; el excel lo mide sin ellos"],
            "source": f"{XLS} (Resumen); {PDF}",
        },
        {
            "id": "S5", "section": "K2", "tracker": "El grupo B está en rampa",
            "purpose": "Mostrar que el grupo B ya aporta y está en rampa: responde a 'B también pierde dinero'",
            "headline": "Antes de coste central, cada tienda B ya aporta 10 k€ (aperturas 2023) o 28 k€ (2024)",
            "supporting_message": "Sus ventas por m2 crecen un 11% al año; cerrarlas costaría 4500 k€ y restaría su contribución",
            "message_type": "single_number",
            "evidence": ev(("C0015", "Tienda B abierta en 2023: +10 k€ antes de coste central"),
                           ("C0016", "Tienda B abierta en 2024: +28 k€ antes de coste central"),
                           ("F0213", "Ventas por m2 +11% al año"),
                           ("C0003", "Grupo B: +324 k€"),
                           ("F0204", "18 tiendas B"),
                           ("C0010", "Cerrar las 18 B: 4500 k€"), ("F0205", "EBITDA 2025 grupo B: −1296 k€"), ("F0206", "Coste central grupo B: 1620 k€")),
            "kpis": {"items": [
                {"value": "+10 k€", "label": "Por tienda abierta en 2023, antes de coste central"},
                {"value": "+28 k€", "label": "Por tienda abierta en 2024, antes de coste central"},
                {"value": "+11%", "label": "Crecimiento anual de las ventas por m2", "trend": "up", "good": "up"},
            ]},
            "visual": {
                "type": "waterfall", "title": "EBITDA 2025 de las 18 tiendas B", "unit": "k€",
                "format": K, "delta_colors": "muted", "highlight": ["Contribución antes de coste central"],
                "data": {"steps": [
                    {"label": "EBITDA contable", "value": -1296, "type": "total"},
                    {"label": "Coste central asignado", "value": 1620, "type": "delta"},
                    {"label": "Contribución antes de coste central", "type": "total"},
                ]},
            },
            "takeaway": "Cerrar las 18 tiendas B costaría 4500 k€ y restaría 324 k€ al año; la red alcanza el equilibrio en el cuarto año",
            "source": f"{XLS} (Tiendas); {PDF}",
        },
        {
            "id": "S6", "section": "K3", "tracker": "Opciones en la misma base",
            "purpose": "Comparar las cuatro opciones en la misma base 2026-2027",
            "headline": "En 2026-2027, cerrar las 15 A con ruptura cuesta 9540 k€, frente a 15598 k€ del cierre total",
            "supporting_message": "Las cuatro opciones cargan los mismos componentes; el coste central permanece en todas",
            "message_type": "comparison",
            "evidence": ev(("C0023", "Mantener las 40: 11040 k€"), ("C0024", "Cerrar las 40: 15598 k€"),
                           ("C0025", "Cerrar 15 A con ruptura: 9540 k€"), ("C0026", "Cerrar las 22 A: 10450 k€"),
                           ("C0022", "Coste central que permanece 2026-2027: 7200 k€"),
                           ("C0032", "Mejora anual cierre total: 1596 k€"), ("C0031", "Mejora anual cierre selectivo: 1500 k€"),
                           ("C0033", "Mejora anual cerrar las 22 A: 1920 k€"),
                           ("C0011", "Cierre de las 40: 7750 k€"), ("C0008", "Cierre de las 15: 1500 k€"),
                           ("C0012", "Cierre de las 22 A: 3250 k€"),
                           ("C0019", "Pérdida directa de A mantenida 2 años: 3840 k€"),
                           ("C0020", "Pérdida de las 7 A sin ruptura 2 años: 840 k€"),
                           ("C0021", "Contribución de B perdida 2 años: 648 k€"),
                           ("C0028", "Cerrar las 40 da 96 k€ más al año"), ("C0029", "a cambio de 6250 k€ más de cierre"),
                           ("F0211", "15 contratos con ruptura en 2026"), ("F0207", "40 tiendas"), ("F0201", "22 tiendas A"),
                           ("A001", "Supuesto: 100 k€ por tienda con ruptura"), ("A002", "Supuesto: horizonte de dos años, cierres a inicio de 2026")),
            "visual": {
                "type": "table", "title": "Coste acumulado 2026-2027 por opción", "unit": "k€",
                "columns": [
                    {"label": "Opción", "kind": "text", "width": 3.3},
                    {"label": "Mejora EBITDA anual", "kind": "number", "format": K},
                    {"label": "Coste de cierre", "kind": "number", "format": K},
                    {"label": "Pérdida directa mantenida", "kind": "number", "format": K},
                    {"label": "Contribución de B perdida", "kind": "number", "format": K},
                    {"label": "Coste total (incluye 7200 de coste central)", "kind": "number", "format": K},
                ],
                "rows": [
                    ["Mantener las 40", 0, 0, 3840, 0, 11040],
                    ["Cerrar las 40 (propuesta)", 1596, {"value": 7750, "bound": "estimate"}, 0, 648, {"value": 15598, "bound": "estimate"}],
                    {"cells": ["Cerrar 15 A con ruptura (recomendada)", 1500, {"value": 1500, "bound": "estimate"}, {"value": 840, "bound": "upper"}, 0, {"value": 9540, "bound": "estimate"}], "style": "highlight"},
                    ["Cerrar las 22 A", 1920, {"value": 3250, "bound": "estimate"}, 0, 0, {"value": 10450, "bound": "estimate"}],
                ],
                "highlight_columns": [5],
            },
            "takeaway": "Cerrar las 40 da solo 96 k€ más de EBITDA al año, a cambio de 6250 k€ más de cierre y de renunciar a B",
            "footnotes": ["~ Supuesto: cierres a inicio de 2026 y 100 k€ por tienda con ruptura. ≤ Cota superior: pérdida de las 7 A sin ruptura si la negociación fracasa"],
            "source": f"{XLS}; {PDF}; {MD}",
        },
        {
            "id": "S7", "section": "K4", "tracker": "Negociar antes de cerrar",
            "purpose": "Plan para las 7 tiendas A sin ruptura: negociar antes de cerrar, con criterio y fecha",
            "headline": "En las 7 A sin ruptura, negociar primero: cerrarlas costaría 1750 k€ para evitar 420 k€ al año",
            "supporting_message": "Cinco de los siete propietarios ya aceptan negociar una rebaja de alquiler",
            "message_type": "sequence",
            "evidence": ev(("C0009", "Cerrar las 7 A sin ruptura: 1750 k€"), ("C0007", "Pérdida de las 7: 420 k€ al año"),
                           ("C0014", "4,2 años de recuperación"), ("C0013", "1 año de recuperación para las 15 con ruptura"),
                           ("F0212", "Cerrar sin ruptura: 250.000 € por tienda"), ("F0211", "15 contratos con ruptura en 2026")),
            "commentary": {"title": "Cerrar hoy no compensa", "points": [
                "**1750 k€:** coste de cerrarlas hoy, sin ventana de ruptura",
                "**420 k€ al año:** su pérdida antes de coste central",
                "**4,2 años de recuperación,** frente a 1 año en las 15 tiendas con ruptura",
            ]},
            "visual": {"type": "process", "title": "Plan para las 7 tiendas A sin ruptura", "highlight": [0], "numbered": True,
                       "data": {"steps": [
                           {"title": "Negociar la rebaja", "text": "5 de los 7 propietarios ya aceptan negociar el alquiler", "owner": "Dirección inmobiliaria"},
                           {"title": "Revisar en junio de 2026", "text": "Umbral: contribución directa positiva tras la rebaja", "owner": "Directora financiera"},
                           {"title": "Cerrar si no hay acuerdo", "text": "En su próxima ventana de ruptura, sin pagar 250 k€ por tienda", "owner": "Consejero delegado"},
                       ]}},
            "source": f"{PDF}; {XLS}",
        },
        {
            "id": "S8", "section": "K4", "tracker": "Decisiones para hoy",
            "purpose": "Decisiones, umbrales y seguimiento que el consejo aprueba hoy",
            "headline": "Aprobar hoy cerrar 15 tiendas (1500 k€) y negociar las 7 A restantes; revisión en junio de 2026",
            "message_type": "recommendation",
            "evidence": ev(("C0008", "Coste de cierre de las 15: 1500 k€"), ("C0031", "Mejora anual: 1500 k€"),
                           ("F0211", "15 contratos con ruptura en 2026"), ("F0207", "40 tiendas"), ("F0204", "18 tiendas B"),
                           ("C0015", "10 k€ por tienda B de 2023"), ("C0016", "28 k€ por tienda B de 2024")),
            "visual": {
                "type": "table", "title": "Decisiones que se piden al consejo",
                "columns": [
                    {"label": "Decisión", "kind": "text", "width": 4.3},
                    {"label": "Responsable", "kind": "text", "width": 2.5},
                    {"label": "Umbral o KPI", "kind": "text", "width": 4.3},
                    {"label": "Cuándo", "kind": "text"},
                ],
                "rows": [
                    ["Rechazar el cierre de las 40 tiendas", "Consejero delegado", "–", "Hoy"],
                    {"cells": ["Aprobar el cierre de las 15 tiendas A con ruptura", "Directora financiera", "Coste real no superior a 1500 k€; mejora de EBITDA de 1500 k€ al año", "T1 2026"], "style": "highlight"},
                    ["Mandato de negociación en las 7 A sin ruptura", "Dirección inmobiliaria", "Contribución directa positiva o cierre en su ventana", "Junio 2026"],
                    ["Mantener las 18 tiendas B", "Director de expansión", "Por tienda, no menos de 10 k€ (2023) y 28 k€ (2024)", "Cierre 2026"],
                ],
            },
            "source": f"{XLS}; {PDF}",
        },
    ],
}
import re
def nb(x, key=None):
    if isinstance(x, dict):
        return {k: (v if k in ("source", "evidence", "storyline") else nb(v, k)) for k, v in x.items()}
    if isinstance(x, list):
        return [nb(v, key) for v in x]
    if isinstance(x, str):
        return re.sub(r"(\d)\s(k€|M€|años|pp)", "\\1\u00a0\\2", x)
    return x
deck = nb(deck)
json.dump(deck, open("/tmp/s2d_deck/tiendas/work/deck.json", "w"), ensure_ascii=False, indent=1)
print("ok")
