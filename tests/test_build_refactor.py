"""Protect build sequencing and booklet padding during refactoring.

These checks use temporary PDFs so they exercise page ordering without modifying
actual publication artifacts.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build


class BuildTests(unittest.TestCase):
    """Check externally visible results of the build orchestration."""

    def test_padding_keeps_last_sections_adjacent_and_edition_lengths_even(self) -> None:
        """Insert blanks before the final two pages, preserving their order."""
        with tempfile.TemporaryDirectory() as directory:
            pdf_dir = Path(directory)
            for lang, widths in (('CZ', [101, 102, 103]), ('EN', [201, 202, 203, 204, 205])):
                writer = PdfWriter()
                for width in widths:
                    writer.add_blank_page(width=width, height=300)
                with (pdf_dir / f'Caj_u_Mefista_4_A5_{lang}.pdf').open('wb') as out:
                    writer.write(out)
            with patch.object(build, 'PDF_DIR', pdf_dir):
                self.assertEqual(build.pad_before_contacts(), 6)
            cz = PdfReader(pdf_dir / 'Caj_u_Mefista_4_A5_CZ.pdf')
            en = PdfReader(pdf_dir / 'Caj_u_Mefista_4_A5_EN.pdf')
            self.assertEqual([float(p.mediabox.width) for p in cz.pages], [101, 103, 103, 103, 102, 103])
            self.assertEqual([float(p.mediabox.width) for p in en.pages], [201, 202, 203, 205, 204, 205])

    def test_skip_pdf_generates_both_schedules_and_website(self) -> None:
        """The source-only build still publishes both language schedules."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = {'events': [1, 2]}
            lectures = [object()]
            with (
                patch.object(build, 'ROOT', root),
                patch.object(build, 'generate', return_value=(lectures, program)) as generate,
                patch.object(build, 'create', side_effect=lambda _p, _l, lang: lang.encode()),
                patch.object(build, 'build_site') as site,
                patch.object(build, 'prepare_qr') as qr,
                patch.object(sys, 'argv', ['build.py', '--xlsx', 'reviewed.xlsx', '--skip-pdf']),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(build.main(), 0)
            generate.assert_called_once_with(Path('reviewed.xlsx'))
            site.assert_called_once_with()
            qr.assert_not_called()
            for lang in ('cz', 'en'):
                self.assertEqual((root / 'schedule' / f'Caj_u_Mefista_4_pentabarf_{lang}.xml').read_bytes(), lang.encode())

    def test_missing_xelatex_fails_with_actionable_message(self) -> None:
        """Missing external tools are reported before invoking a subprocess."""
        with patch.object(build.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'xelatex missing'):
                build.compile_tex('cz')


if __name__ == '__main__':
    unittest.main()
