"""Check booklet ordering and PDF validation using small synthetic editions."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from impose import A4_W, A5_H, A5_W, impose  # noqa: E402


def make_edition(directory: Path, language: str, count: int, width: float = A5_W) -> None:
    """Write labeled pages so their position survives PDF imposition.

    Args:
        directory: Directory to receive the edition.
        language: Edition code used in its filename and page labels.
        count: Number of pages to generate.
        width: Page width in PDF points.
    """
    writer = PdfWriter()
    for index in range(count):
        page = writer.add_blank_page(width=width, height=A5_H)
        content = DecodedStreamObject()
        content.set_data(f"/{language}-{index + 1} BMC\nEMC\n".encode())
        page[NameObject("/Contents")] = writer._add_object(content)
    writer.write(directory / f"Caj_u_Mefista_4_A5_{language}.pdf")


class ImpositionTest(unittest.TestCase):
    """Verify the reversible reader and duplex order, including rejection cases."""

    def test_reader_and_folded_sheet_order(self) -> None:
        """Place Czech pages first and English pages reversed, then impose pairs."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_edition(directory, "CZ", 4)
            make_edition(directory, "EN", 4)
            impose(directory, expected_pages=4)
            reader = PdfReader(directory / "Caj_u_Mefista_4_A5_tete_beche_reader.pdf")
            labels = ("CZ-1", "CZ-2", "CZ-3", "CZ-4", "EN-4", "EN-3", "EN-2", "EN-1")
            self.assertEqual(len(reader.pages), len(labels))
            for page, label in zip(reader.pages, labels):
                content = page.get_contents().get_data()
                self.assertIn(label.encode(), content)
                if label.startswith("EN"):
                    self.assertIn(b"-1", content)  # 180-degree rotation is in the content
            master = PdfReader(directory / "Caj_u_Mefista_4_A4_imposed_duplex.pdf")
            pairs = (("EN-1", "CZ-1"), ("CZ-2", "EN-2"), ("EN-3", "CZ-3"), ("CZ-4", "EN-4"))
            self.assertEqual(len(master.pages), len(pairs))
            for page, (left, right) in zip(master.pages, pairs):
                content = page.get_contents().get_data()
                self.assertLess(content.index(left.encode()), content.index(right.encode()))
                self.assertAlmostEqual(float(page.mediabox.width), A4_W, places=2)
                self.assertAlmostEqual(float(page.mediabox.height), A5_H, places=2)

    def test_rejects_count_and_geometry_mismatch(self) -> None:
        """Reject missing pages and non-A5 source dimensions before imposition."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_edition(directory, "CZ", 4)
            make_edition(directory, "EN", 2)
            with self.assertRaisesRegex(ValueError, "Unexpected page count"):
                impose(directory, expected_pages=4)
            make_edition(directory, "EN", 4, width=100)
            with self.assertRaisesRegex(ValueError, "EN page 1: not portrait A5"):
                impose(directory, expected_pages=4)

    def test_rejects_unfoldable_page_count(self) -> None:
        """Reject an odd number of pages per language for saddle stitching."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_edition(directory, "CZ", 3)
            make_edition(directory, "EN", 3)
            with self.assertRaisesRegex(ValueError, "multiple of four"):
                impose(directory, expected_pages=3)


if __name__ == "__main__":
    unittest.main()
