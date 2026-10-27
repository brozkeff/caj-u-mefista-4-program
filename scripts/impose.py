"""Create reversible A5 and imposed A4 PDFs for reliable duplex printing.

Keeping pages as PDF vectors preserves their fonts and artwork; the A4 master
already contains booklet ordering and must be printed without booklet mode.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from config import A5_PREFIX, DUPLEX_NAME, READER_NAME
from pypdf import PageObject, PdfReader, PdfWriter, Transformation

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "build" / "pdf"
A4_W = 297.0 * 72.0 / 25.4
A5_W = 148.0 * 72.0 / 25.4
A5_H = 210.0 * 72.0 / 25.4


def _validate_editions(cz: PdfReader, en: PdfReader, expected_pages: int) -> None:
    """Check both editions have the requested size and portrait A5 geometry.

    Args:
        cz: Czech edition.
        en: English edition.
        expected_pages: Required page count for each edition.

    Raises:
        ValueError: If page counts or geometry do not match.
    """
    if len(cz.pages) != expected_pages or len(en.pages) != expected_pages:
        raise ValueError(
            f"Unexpected page count CZ={len(cz.pages)}, EN={len(en.pages)}; "
            f"expected {expected_pages} each. Check TeX overflow."
        )
    for edition, source in (("CZ", cz), ("EN", en)):
        for page_num, page in enumerate(source.pages, start=1):
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            if abs(width - A5_W) > 2.0 or abs(height - A5_H) > 2.0:
                raise ValueError(
                    f"{edition} page {page_num}: not portrait A5 ({width:.1f}x{height:.1f} pt)"
                )


def _reader(cz: PdfReader, en: PdfReader) -> PdfWriter:
    """Combine Czech pages with reversed, rotated English pages.

    Args:
        cz: Czech edition.
        en: English edition.

    Returns:
        A writer containing the reversible A5 reader.
    """
    combined = PdfWriter()
    combined.add_metadata({"/Title": "Čaj u Mefista 4 / Tea at Mephisto's 4 — tête-bêche A5"})
    for page in cz.pages:
        combined.add_page(page)
    for page in reversed(en.pages):
        combined.add_page(page)
        combined.pages[-1].rotate(180)
        combined.pages[-1].transfer_rotation_to_content()
    return combined


def _print_master(combined: PdfWriter) -> PdfWriter:
    """Place reader pages in folded short-edge-duplex sheet order.

    Args:
        combined: The reversible reader with portrait A5 pages.

    Returns:
        A writer containing landscape A4 sides ready for printing.

    Raises:
        ValueError: If the reader cannot be imposed on A4 saddle sheets.
    """
    page_total = len(combined.pages)
    if page_total % 4 != 0:
        raise ValueError(f"Saddle stitching requires a multiple of four pages: {page_total}")
    left_margin = (A4_W - 2 * A5_W) / 2
    if left_margin < -0.1:
        raise ValueError("A5 pages are too wide for A4 imposition")
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Čaj u Mefista 4 — A4 short-edge duplex imposition"})
    for sheet_index in range(page_total // 4):
        # Front [last, first], back [second, penultimate], then work inward.
        pairs = (
            (page_total - 1 - 2 * sheet_index, 2 * sheet_index),
            (2 * sheet_index + 1, page_total - 2 - 2 * sheet_index),
        )
        for left_index, right_index in pairs:
            page = PageObject.create_blank_page(None, width=A4_W, height=A5_H)
            page.merge_transformed_page(
                combined.pages[left_index], Transformation().translate(left_margin, 0)
            )
            page.merge_transformed_page(
                combined.pages[right_index], Transformation().translate(left_margin + A5_W, 0)
            )
            writer.add_page(page)
    return writer


def impose(pdf_dir: Path = PDF_DIR, *, expected_pages: int = 22) -> None:
    """Combine both language editions and produce the A4 printing master.

    Args:
        pdf_dir: Folder containing the two single-language A5 PDFs.
        expected_pages: Required page count in each language.

    Raises:
        ValueError: If page counts, geometry or booklet size are invalid.
    """
    cz = PdfReader(pdf_dir / f"{A5_PREFIX}_CZ.pdf")
    en = PdfReader(pdf_dir / f"{A5_PREFIX}_EN.pdf")
    _validate_editions(cz, en, expected_pages)
    combined = _reader(cz, en)
    with (pdf_dir / READER_NAME).open("wb") as stream:
        combined.write(stream)
    writer = _print_master(combined)
    with (pdf_dir / DUPLEX_NAME).open("wb") as stream:
        writer.write(stream)


def main() -> None:
    """Impose existing edition PDFs from command-line paths and page count."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--expected-pages", type=int, default=22)
    args = parser.parse_args()
    impose(args.pdf_dir, expected_pages=args.expected_pages)
    print("Created A5 tête-bêche reader and A4 2-up duplex master")


if __name__ == "__main__":
    main()
