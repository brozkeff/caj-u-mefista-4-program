"""Protect schedule export semantics that mobile clients and readers depend on."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from generate import parse_reviewed  # noqa: E402
from pentabarf import create, duration_minutes  # noqa: E402


class PentabarfRegressionTests(unittest.TestCase):
    """Check representative output against reviewed conference sources."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load canonical sources once for the exported schedule tests."""
        cls.program = json.loads((ROOT / 'data/program.json').read_text(encoding='utf-8'))
        cls.lectures = parse_reviewed(ROOT / 'data/abstracts_review.xlsx', cls.program)

    def test_bilingual_lectures_and_untimed_exhibitions(self) -> None:
        """Keep abstracts intact and untimed art out of the timed event list."""
        for lang in ('cz', 'en'):
            with self.subTest(language=lang):
                root = ET.fromstring(create(self.program, self.lectures, lang))
                timed = root.findall('.//day/room/event')
                exhibitions = root.findall('.//day/untimed_events/event')
                self.assertEqual(35, len(timed))
                self.assertEqual(3, len(exhibitions))
                self.assertEqual(14, sum(e.findtext('type') == 'lecture' for e in timed))
                self.assertEqual('1000', timed[0].attrib['id'])
                self.assertEqual('caj-u-mefista-4-2026-10-29-19:00-brnenske-okultni-pivo-vinoteka-bukov', timed[0].attrib['guid'])
                first_lecture = self.lectures[0]
                exported = next(e for e in timed if e.findtext('slug') == first_lecture.event['id'])
                self.assertEqual(first_lecture.abstract_cz if lang == 'cz' else first_lecture.abstract_en,
                                 exported.findtext('abstract'))
                self.assertTrue(any('Voynich Manuscript' in e.text for e in exhibitions))
                self.assertFalse(any('Chaitow' in (e.text or '') for e in exhibitions))

    def test_metadata_is_read_from_program(self) -> None:
        """Expose metadata edits in XML rather than fixed programme constants."""
        program = dict(self.program)
        program['conference'] = {**program['conference'], 'title_en': 'A & B', 'city': 'Test City'}
        root = ET.fromstring(create(program, self.lectures, 'en'))
        self.assertEqual('A & B', root.findtext('conference/title'))
        self.assertEqual('Test City', root.findtext('conference/city'))

    def test_duration_override_cap_and_next_start(self) -> None:
        """Keep duration override, type cap, and next-event boundaries."""
        event = {'date': '2026-10-30', 'start': '10:00', 'kind': 'lecture'}
        next_event = {'date': '2026-10-30', 'start': '10:20', 'kind': 'lecture'}
        untimed = {'date': '2026-10-30', 'start': None, 'kind': 'exhibition'}
        self.assertEqual(20, duration_minutes(event, [event, next_event, untimed]))
        self.assertEqual(45, duration_minutes(event, [event, untimed]))
        self.assertEqual(90, duration_minutes({**event, 'duration_minutes': 90}, [event, next_event]))


if __name__ == '__main__':
    unittest.main()
