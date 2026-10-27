"""Create a reversible (tête-bêche) A5 reader and A4 duplex saddle imposition.

No rasterization: source fonts, vectors and bitmaps are preserved in the PDFs.
The print PDF is already imposed; printers must not apply booklet mode again.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "build" / "pdf"
A4_W = 297.0 * 72.0 / 25.4
A5_W = 148.0 * 72.0 / 25.4
A5_H = 210.0 * 72.0 / 25.4


def impose(pdf_dir: Path = PDF_DIR, *, expected_pages: int = 22) -> None:
    """Combine language editions and produce the A4 duplex printing master.

    Args:
        pdf_dir: Folder containing the two single-language A5 PDFs.
        expected_pages: Pages in each language (default: 22).

    Raises:
        ValueError: On wrong page count, page geometry or invalid booklet size.
    """
    cz = PdfReader(pdf_dir / "Caj_u_Mefista_4_A5_CZ.pdf")
    en = PdfReader(pdf_dir / "Caj_u_Mefista_4_A5_EN.pdf")
    if len(cz.pages) != expected_pages or len(en.pages) != expected_pages:
        raise ValueError(
            f"Unexpected page count CZ={len(cz.pages)}, EN={len(en.pages)}; "
            f"expected {expected_pages} each. Check TeX overflow."
        )
    for edition, source in (("CZ", cz), ("EN", en)):
        for page_num, page in enumerate(source.pages, start=1):
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            if abs(w - A5_W) > 2.0 or abs(h - A5_H) > 2.0:
                raise ValueError(f"{edition} page {page_num}: not portrait A5 ({w:.1f}x{h:.1f} pt)")

    combined = PdfWriter()
    combined.add_metadata(
        {"/Title": "Čaj u Mefista 4 / Tea at Mephisto's 4 — tête-bêche A5"}
    )
    for page in cz.pages:
        combined.add_page(page)
    for page in reversed(en.pages):
        combined.add_page(page)
        combined.pages[-1].rotate(180)
        combined.pages[-1].transfer_rotation_to_content()
    with (pdf_dir / "Caj_u_Mefista_4_A5_tete_beche_reader.pdf").open("wb") as stream:
        combined.write(stream)

    page_total = len(combined.pages)
    if page_total % 4 != 0:
        raise ValueError(f"Saddle stitching requires a multiple of four pages: {page_total}")
    left_margin = (A4_W - 2 * A5_W) / 2
    if left_margin < -0.1:
        raise ValueError("A5 pages are too wide for A4 imposition")
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Čaj u Mefista 4 — A4 short-edge duplex imposition"})
    for sheet_index in range(page_total // 4):
        # Zero-based reader indices. Front: [last, first]; back: [second, penultimate].
        # This ordering is for short-edge duplex of landscape A4 and fold along centre.
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
    with (pdf_dir / "Caj_u_Mefista_4_A4_imposed_duplex.pdf").open("wb") as stream:
        writer.write(stream)


def main() -> None:
    """CLI entry point for imposition independent of the full build."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--expected-pages", type=int, default=22)
    args = parser.parse_args()
    impose(args.pdf_dir, expected_pages=args.expected_pages)
    print("Created A5 tête-bêche reader and A4 2-up duplex master")


if __name__ == "__main__":
    main()
