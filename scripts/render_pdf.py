#!/usr/bin/env python3
"""Render a PDF to traceable page PNG files for Agent visual extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def render_with_pymupdf(pdf_path: Path, output_dir: Path, dpi: int) -> int:
    import fitz  # type: ignore

    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pix.save(output_dir / f"page_{index:03d}.png")
    return len(doc)


def render_with_pypdfium2(pdf_path: Path, output_dir: Path, dpi: int) -> int:
    import pypdfium2 as pdfium  # type: ignore

    pdf = pdfium.PdfDocument(str(pdf_path))
    scale = dpi / 72.0
    for index in range(len(pdf)):
        page = pdf[index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        image.save(output_dir / f"page_{index + 1:03d}.png")
    return len(pdf)


def render_with_pdf2image(pdf_path: Path, output_dir: Path, dpi: int) -> int:
    from pdf2image import convert_from_path  # type: ignore

    images = convert_from_path(str(pdf_path), dpi=dpi)
    for index, image in enumerate(images, start=1):
        image.save(output_dir / f"page_{index:03d}.png")
    return len(images)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Input PDF")
    parser.add_argument("output_dir", help="Directory for page_001.png outputs")
    parser.add_argument("--dpi", type=int, default=220, help="Render DPI, default 220")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output_dir)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    errors = []
    for renderer in (render_with_pymupdf, render_with_pypdfium2, render_with_pdf2image):
        try:
            count = renderer(pdf_path, output_dir, args.dpi)
            print(f"PASS: rendered {count} page(s) to {output_dir}")
            return 0
        except Exception as exc:
            errors.append(f"{renderer.__name__}: {exc}")
    print("ERROR: no PDF renderer succeeded", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
