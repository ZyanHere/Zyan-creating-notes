"""Rasterise a PDF to PNG pages. Used for visual review and for the
determinism / golden-image tests, which compare pages rather than bytes:
PDF files carry timestamps and object ordering that differ between identical
renders.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium


def rasterise(pdf: Path, out_dir: Path, scale: float = 2.0) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(pdf)
    written = []
    for i, page in enumerate(doc, start=1):
        img = page.render(scale=scale).to_pil()
        p = out_dir / f"{pdf.stem}-p{i:02d}.png"
        img.save(p)
        written.append(p)
    return written


if __name__ == "__main__":
    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out/pages")
    for p in rasterise(pdf, out):
        print(p)
