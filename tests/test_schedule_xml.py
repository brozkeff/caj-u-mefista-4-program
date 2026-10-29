"""Check generated schedules as XML and as usable Pentabarf-style documents."""

import json
import unittest
from datetime import date, time
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ScheduleXmlTests(unittest.TestCase):
    """Check both exported languages independently of the snapshot regression."""

    def test_schedule_document_structure(self) -> None:
        """Require parseable XML, valid dates, unique event IDs and usable fields."""
        program = json.loads((ROOT / 'data/program.json').read_text(encoding='utf-8'))
        streams = json.loads((ROOT / 'data/streams.json').read_text(encoding='utf-8'))
        expected_streams = {event_id: stream['url'] for stream in streams for event_id in stream['events']}
        for lang in ('cz', 'en'):
            with self.subTest(language=lang):
                path = ROOT / 'build' / 'site' / f'schedule-{lang}.xml'
                root = ET.parse(path).getroot()
                self.assertEqual(root.tag, 'schedule')
                conference = root.find('conference')
                self.assertIsNotNone(conference)
                for field in ('title', 'subtitle', 'venue', 'city', 'start', 'end', 'days'):
                    self.assertTrue(conference.findtext(field), field)
                first = date.fromisoformat(conference.findtext('start'))
                last = date.fromisoformat(conference.findtext('end'))
                self.assertLessEqual(first, last)
                days = root.findall('day')
                self.assertEqual(len(days), int(conference.findtext('days')))
                ids, guids = set(), set()
                for index, day in enumerate(days, 1):
                    self.assertEqual(day.get('index'), str(index))
                    self.assertTrue(first <= date.fromisoformat(day.get('date')) <= last)
                    for room in day.findall('room'):
                        self.assertTrue(room.get('name'))
                        for event in room.findall('event'):
                            event_id, guid = event.get('id'), event.get('guid')
                            self.assertTrue(event_id and event_id.isdecimal())
                            self.assertTrue(guid)
                            self.assertNotIn(event_id, ids)
                            self.assertNotIn(guid, guids)
                            ids.add(event_id)
                            guids.add(guid)
                            time.fromisoformat(event.findtext('start'))
                            duration = event.findtext('duration') or ''
                            self.assertRegex(duration, r'^\d{2,}:\d{2}$')
                            hours, minutes = map(int, duration.split(':'))
                            self.assertTrue(minutes < 60 and hours * 60 + minutes > 0)
                            for field in ('room', 'slug', 'title', 'type', 'language'):
                                self.assertTrue(event.findtext(field), field)
                            self.assertEqual(event.findtext('room'), room.get('name'))
                            stream_links = [link.get('href') for link in event.findall('links/link') if 'youtube.com/live/' in link.get('href', '')]
                            expected = expected_streams.get(event.findtext('slug'))
                            self.assertEqual(stream_links, [expected] if expected else [])
                            link = event.find('links/link')
                            self.assertIsNotNone(link)
                            self.assertEqual(link.text, 'Online program' if lang == 'cz' else 'Live programme')
                            self.assertIn(urlparse(link.get('href')).scheme, ('http', 'https'))
                            self.assertTrue(urlparse(link.get('href')).netloc)
                    for event in day.findall('untimed_events/event'):
                        self.assertTrue(event.get('guid') and event.text)
                        self.assertNotIn(event.get('guid'), guids)
                        guids.add(event.get('guid'))
                self.assertEqual(len(ids), sum(e['start'] is not None for e in program['events']))
                self.assertEqual(len(guids), len(program['events']))


if __name__ == '__main__':
    unittest.main()
