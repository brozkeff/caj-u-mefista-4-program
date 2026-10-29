"""Guard v4.1.1 publication content while allowing implementation refactoring."""

import hashlib
import json
import unittest
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'tests/fixtures/publication-v411.json').read_text())


def digest(data: bytes) -> str:
    """Return a stable digest for published content.

    Args:
        data: Bytes to fingerprint.

    Returns:
        SHA-256 hexadecimal digest.
    """
    return hashlib.sha256(data).hexdigest()


class PublicationRegressionTest(unittest.TestCase):
    """Compare generated schedules and page text with the reviewed release."""

    def test_a5_text_and_page_boundaries(self) -> None:
        """Detect changed text, missing pages and altered lecture flow."""
        for lang, expected in BASELINE['pdf_pages'].items():
            with self.subTest(language=lang):
                pdf = PdfReader(ROOT / 'build/pdf' / f'Caj_u_Mefista_4_A5_{lang}.pdf')
                self.assertEqual([digest(page.extract_text().encode()) for page in pdf.pages], expected)

    def test_pentabarf_output(self) -> None:
        """Detect changes to event IDs, timing, text and XML metadata."""
        for lang, expected in BASELINE['xml'].items():
            with self.subTest(language=lang):
                xml = ROOT / 'schedule' / f'Caj_u_Mefista_4_pentabarf_{lang}.xml'
                self.assertEqual(digest(xml.read_bytes()), expected)


if __name__ == '__main__':
    unittest.main()
