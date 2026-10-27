"""Exercise schedule verification against stale or incomplete programme data."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify import verify_schedule


class ScheduleVerificationTests(unittest.TestCase):
    """Verify changes and duplicates cannot pass as a complete schedule."""

    def setUp(self) -> None:
        """Provide a minimal timed and untimed source and matching output."""
        self.program = {'events': [
            {'id': 'talk', 'start': '10:00', 'kind': 'lecture', 'title_cz': 'Přednáška', 'title_en': 'Lecture'},
            {'id': 'art', 'start': None, 'kind': 'exhibition', 'title_cz': 'Výstava', 'title_en': 'Exhibition'},
        ]}
        self.tree = ET.ElementTree(ET.fromstring('''<schedule><day>
          <untimed_events><event guid="caj-u-mefista-4-art">Výstava</event></untimed_events>
          <room><event guid="caj-u-mefista-4-talk"><start>10:00</start><duration>00:45</duration>
          <title>Přednáška</title><type>lecture</type></event></room>
          </day></schedule>'''))

    def test_matching_schedule_passes(self) -> None:
        """Accept both kinds of source event when their content matches."""
        verify_schedule(self.tree, self.program, 'cz')

    def test_stale_title_fails(self) -> None:
        """Reject a schedule whose title no longer matches its source."""
        self.tree.find('.//room/event/title').text = 'Outdated'
        with self.assertRaises(AssertionError):
            verify_schedule(self.tree, self.program, 'cz')

    def test_duplicate_untimed_event_fails(self) -> None:
        """Reject a duplicate even when its title is otherwise correct."""
        parent = self.tree.find('.//untimed_events')
        parent.append(ET.fromstring('<event guid="caj-u-mefista-4-art">Výstava</event>'))
        with self.assertRaises(AssertionError):
            verify_schedule(self.tree, self.program, 'cz')

    def test_missing_duration_fails(self) -> None:
        """Require a duration for timed events consumed by schedule apps."""
        self.tree.find('.//room/event/duration').text = ''
        with self.assertRaises(AssertionError):
            verify_schedule(self.tree, self.program, 'cz')


if __name__ == '__main__':
    unittest.main()
