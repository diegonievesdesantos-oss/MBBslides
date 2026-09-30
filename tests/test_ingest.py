import zipfile

import openpyxl

from cpe.ingest.readers import extract_facts, ingest


def test_markdown_csv_xlsx_docx(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("# Market\nThe market reached €142bn in 2025, growing 4.1% a year.\n\n| Channel | Sales |\n|---|---|\n| Discount | 38 |\n| Online | 14 |\n")
    csvf = tmp_path / "data.csv"
    csvf.write_text("year,revenue\n2024,13.2\n2025,13.6\n")
    x = tmp_path / "d.xlsx"
    wb = openpyxl.Workbook()
    wb.active.append(["seg", "value"])
    wb.active.append(["A", 10])
    wb.save(x)
    d = tmp_path / "memo.docx"
    with zipfile.ZipFile(d, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>EBITDA fell to €857M, a margin of 6.3%.</w:t></w:r></w:p></w:body></w:document>')
    inv = ingest([md, csvf, x, d])
    assert all(s["status"] == "ok" for s in inv["sources"])
    assert len(inv["tables"]) == 3
    vals = {f["value"] for f in inv["facts"]}
    assert {142.0, 4.1, 857.0, 6.3} <= vals
    assert 2025.0 not in vals  # years are not facts


def test_fact_context_is_kept():
    f = extract_facts("Online grew 14% a year. Hypermarkets shrank.", "x", "l1")
    assert f[0]["value"] == 14 and "Online" in f[0]["context"]
