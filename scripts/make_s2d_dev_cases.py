"""Generate the binary sources (PDF, DOCX) of the source-to-deck development cases.

The cases are synthetic development data written by the developing agent (evals/source_to_deck/README.md).
Run: python scripts/make_s2d_dev_cases.py  (needs pymupdf; DOCX is written as raw OOXML).
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1] / "evals" / "source_to_deck" / "development"

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')


def _p(text: str, heading: bool = False) -> str:
    style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ""
    return f"<w:p>{style}<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def _tbl(rows: list[list[str]]) -> str:
    return "<w:tbl>" + "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{escape(str(c))}</w:t></w:r></w:p></w:tc>" for c in r) + "</w:tr>" for r in rows) + "</w:tbl>"


def write_docx(path: Path, parts: list[str]) -> None:
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
           + "".join(parts) + "</w:body></w:document>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)


def write_pdf(path: Path, paragraphs: list[str]) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    for para in paragraphs:
        rect = pymupdf.Rect(60, y, 535, y + 200)
        h = page.insert_textbox(rect, para, fontsize=10.5, fontname="helv")
        used = 200 - h if h >= 0 else 200
        y += used + 12
        if y > 720:
            page = doc.new_page()
            y = 60
    doc.save(str(path))


def promo() -> None:
    src = ROOT / "promo_effectiveness" / "sources"
    src.mkdir(parents=True, exist_ok=True)
    write_pdf(src / "promo_review_FY2025.pdf", [
        "Promotion review FY2025 - commercial finance.",
        "Promotions represented 38% of sales in FY2025, up from 29% in FY2024.",
        "Promoted volume grew 14% while full-price volume fell 6%; total volume grew 2.1%.",
        "Average promotional depth rose from 18% to 24% of the regular price.",
        "Gross margin fell from 27.4% to 25.1% over the same period.",
        "Sales of promoted items fall 22% in the two weeks after a promotion ends.",
        "Loyalty-card data show that 71% of promoted volume is bought by customers who also buy the same item at full price.",
    ])
    write_docx(src / "promo_by_category.docx", [
        _p("Promotion economics by category", heading=True),
        _p("Incremental margin is the margin gained per 100 EUR of promoted sales after subtracting sales that would have happened anyway."),
        _tbl([["Category", "Promo share FY2024 (%)", "Promo share FY2025 (%)", "Incremental margin per 100 EUR promo (EUR)"],
              ["Snacks", "31", "45", "-2.1"], ["Beverages", "34", "44", "0.8"], ["Household", "22", "30", "-3.4"], ["Fresh", "12", "15", "1.6"]]),
    ])
    (src / "marketing_proposal.md").write_text(
        "# Marketing proposal 2026\n\n"
        "- Marketing: promotions drove our volume growth this year and are our most effective tool.\n"
        "- We propose to raise the promotion budget by 20% in 2026 and extend deep discounts to household.\n", encoding="utf-8")


def plant() -> None:
    src = ROOT / "plant_capacity_es" / "sources"
    src.mkdir(parents=True, exist_ok=True)
    write_pdf(src / "informe_produccion_2025.pdf", [
        "Informe de producción 2025 - planta de envases.",
        "Las tres líneas disponen de 18.000 horas al año; en 2025 se perdieron 6.000 horas por paradas.",
        "El OEE de la planta fue del 61%, frente al 75% de referencia del sector.",
        "El cambio de formato medio dura 95 minutos; las plantas que aplican SMED lo hacen en 30 minutos.",
        "La demanda prevista para 2026 exige un 15% más de horas productivas que en 2025.",
    ])
    write_docx(src / "paradas_por_causa.docx", [
        _p("Horas perdidas por causa, 2025", heading=True),
        _tbl([["Causa", "Horas perdidas 2025", "Porcentaje del tiempo perdido (%)"],
              ["Cambios de formato", "2280", "38"], ["Averías", "1620", "27"], ["Falta de material", "1200", "20"], ["Otros", "900", "15"], ["Total", "6000", "100"]]),
    ])
    (src / "correo_direccion_tecnica.md").write_text(
        "# Correo de la dirección técnica\n\n"
        "- Necesitamos una cuarta línea para crecer: la inversión es de 12 M€ y estaría operativa en 18 meses.\n"
        "- Las líneas actuales están al límite de su capacidad.\n", encoding="utf-8")


if __name__ == "__main__":
    promo()
    plant()
    print("ok")
