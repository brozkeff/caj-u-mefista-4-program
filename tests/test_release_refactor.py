"""Check release source integrity and archive contents without publishing."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import release


class ReleaseTests(unittest.TestCase):
    """Protect the release against dirty, mismatched or incomplete artifacts."""

    def test_checkout_requires_clean_exact_tag(self) -> None:
        """Reject dirty worktrees and tags which identify another commit."""
        with patch.object(release, 'run', side_effect=['?? untracked']):
            with self.assertRaisesRegex(RuntimeError, 'clean'):
                release.checked_commit('v4.0.4', False)
        with patch.object(release, 'run', side_effect=['', 'head', 'other']):
            with self.assertRaisesRegex(RuntimeError, 'exact tagged'):
                release.checked_commit('v4.0.4', False)

    def test_upload_requires_remote_tag_to_match_peeled_commit(self) -> None:
        """Accept annotated origin tags only when their peeled commit matches."""
        remote = 'tag-object\trefs/tags/v4.0.4\nhead\trefs/tags/v4.0.4^{}'
        with patch.object(release, 'run', side_effect=['', 'head', 'head', remote]):
            self.assertEqual(release.checked_commit('v4.0.4', True), 'head')
        with patch.object(release, 'run', side_effect=['', 'head', 'head', remote.replace('head\t', 'wrong\t')]):
            with self.assertRaisesRegex(RuntimeError, 'origin tag'):
                release.checked_commit('v4.0.4', True)

    def test_archive_has_rendered_assets_and_source_commit(self) -> None:
        """Package all required artifacts and write a verifiable checksum."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_names = ('index.html', 'style.css', 'schedule.js', 'streams.js', 'logo-cz.jpg', 'logo-en.jpg',
                          'schedule-cz.xml', 'schedule-en.xml')
            asset_names = ('logo-cz.jpg', 'logo-en.jpg', 'program-qr-cz.svg', 'program-qr-en.svg', 'stream-qr.svg')
            pdf_names = ('Caj_u_Mefista_4_A5_CZ.pdf', 'Caj_u_Mefista_4_A5_EN.pdf',
                         'Caj_u_Mefista_4_A5_tete_beche_reader.pdf', 'Caj_u_Mefista_4_A4_imposed_duplex.pdf')
            files = [*(Path('build/pdf') / x for x in pdf_names),
                     *(Path('build/site') / x for x in site_names),
                     *(Path('assets') / x for x in asset_names), Path('README.md'), Path('LICENSE')]
            for path in files:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(str(path).encode())
            with patch.object(release, 'ROOT', root):
                archive, checksum = release.package('v4.0.4', 'abcdef')
                with ZipFile(archive) as bundle:
                    self.assertEqual(set(bundle.namelist()),
                                     {*(f'pdf/{x}' for x in pdf_names), *(f'site/{x}' for x in site_names),
                                      *(f'assets/{x}' for x in asset_names), 'README.md', 'LICENSE', 'SOURCE-COMMIT.txt'})
                    self.assertEqual(bundle.read('SOURCE-COMMIT.txt'), b'v4.0.4\nabcdef\n')
                    self.assertEqual(bundle.read('site/logo-en.jpg'), b'build/site/logo-en.jpg')
                self.assertEqual(checksum.read_text(), f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n')
                (root / 'build/pdf/extra.pdf').touch()
                with self.assertRaisesRegex(RuntimeError, 'exactly the four'):
                    release.package('v4.0.4', 'abcdef')


if __name__ == '__main__':
    unittest.main()
