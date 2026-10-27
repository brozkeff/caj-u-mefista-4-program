"""Decode QR codes from rendered PDFs to catch broken or stale destinations."""

import json
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / 'build' / 'pdf'


def decode_pages(pdf: Path, pages: list[int]) -> Counter:
    """Rasterize selected PDF pages and decode all QR codes on each page.

    Args:
        pdf: Publication PDF to inspect.
        pages: One-based page numbers to render.

    Returns:
        Counts of decoded QR payloads across the selected pages.

    Raises:
        RuntimeError: If a rendering or barcode tool fails unexpectedly.
    """
    result = Counter()
    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / 'page'
        for page in pages:
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '200',
                            '-singlefile', '-png', str(pdf), str(image)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            scan = subprocess.run(['zbarimg', '--quiet', '--raw', str(image) + '.png'],
                                  capture_output=True, text=True, check=False)
            if scan.returncode not in (0, 4):
                raise RuntimeError(f'zbarimg failed on {pdf.name} page {page}: {scan.stderr}')
            result.update(scan.stdout.splitlines())
    return result


class RenderedQrTests(unittest.TestCase):
    """Verify the codes in both editions and the imposed duplex master."""

    def test_rendered_qr_destinations(self) -> None:
        """Decode programme and stream codes and compare them with source URLs."""
        program = json.loads((ROOT / 'data/program.json').read_text(encoding='utf-8'))
        stream = json.loads((ROOT / 'data/stream.json').read_text(encoding='utf-8'))
        expected_imposed = Counter()
        for lang in ('cz', 'en'):
            pdf = PDF_DIR / f'Caj_u_Mefista_4_A5_{lang.upper()}.pdf'
            pages = len(PdfReader(pdf).pages)
            expected = Counter([program['urls'][lang], stream['url']])
            with self.subTest(edition=lang):
                self.assertEqual(decode_pages(pdf, [2, pages - 1]), expected)
            expected_imposed.update(expected)
        imposed = PDF_DIR / 'Caj_u_Mefista_4_A4_imposed_duplex.pdf'
        self.assertEqual(decode_pages(imposed, list(range(1, len(PdfReader(imposed).pages) + 1))),
                         expected_imposed)


if __name__ == '__main__':
    unittest.main()
