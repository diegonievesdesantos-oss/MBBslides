"""Render a .pptx to PDF (LibreOffice headless) and PNGs (PyMuPDF) + contact sheet.

The PDF is not only a preview: render-based QA reads the exact positions of
every rendered text span from it (qa/render_checks.py).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class RenderError(RuntimeError):
    pass


def find_soffice() -> str | None:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/Applications/LibreOffice.app/Contents/MacOS/soffice", "C:/Program Files/LibreOffice/program/soffice.exe"):
        if os.path.exists(p):
            return p
    return None


def to_pdf(pptx: str | Path, out_dir: str | Path, timeout: int = 240) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise RenderError("LibreOffice (soffice) not found. Install libreoffice + libreoffice-impress, or run with --no-render.")
    pptx = Path(pptx).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        cmd = [soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    pdf = out_dir / (pptx.stem + ".pdf")
    if not pdf.exists():
        hint = " (is libreoffice-impress installed?)" if "could not be loaded" in (r.stderr + r.stdout) else ""
        raise RenderError(f"PDF conversion failed{hint}: {r.stderr.strip() or r.stdout.strip()}")
    return pdf


def to_pngs(pdf: str | Path, out_dir: str | Path, dpi: int = 110, prefix: str = "slide") -> list[Path]:
    import pymupdf

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{prefix}-*.png"):
        old.unlink()
    doc = pymupdf.open(str(pdf))
    paths = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        pth = out_dir / f"{prefix}-{i:02d}.png"
        pix.save(str(pth))
        paths.append(pth)
    doc.close()
    return paths


def contact_sheet(pngs: list[Path], out: str | Path, cols: int = 3, thumb_w: int = 520, labels: list[str] | None = None) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    if not pngs:
        raise RenderError("No PNGs to assemble")
    ims = [Image.open(p).convert("RGB") for p in pngs]
    ratio = ims[0].height / ims[0].width
    th = int(thumb_w * ratio)
    pad, lab_h = 16, 22
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (th + pad + lab_h) + pad), "#E9ECEF")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, im in enumerate(ims):
        r, c = divmod(i, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (th + pad + lab_h)
        sheet.paste(im.resize((thumb_w, th)), (x, y + lab_h))
        draw.text((x, y + 2), labels[i] if labels and i < len(labels) else f"{i + 1}", fill="#1E252D", font=font)
    sheet.save(str(out))
    return Path(out)


def render(pptx: str | Path, out_dir: str | Path, dpi: int = 110) -> dict:
    out_dir = Path(out_dir)
    pdf = to_pdf(pptx, out_dir)
    pngs = to_pngs(pdf, out_dir / "renders", dpi=dpi)
    sheet = contact_sheet(pngs, out_dir / "contact_sheet.png")
    return {"pdf": str(pdf), "pngs": [str(p) for p in pngs], "contact_sheet": str(sheet)}
