"""Export the reviewed programme as Pentabarf XML for schedule applications.

The canonical JSON and workbook are read locally so publishing never silently
changes the timetable from a live website. Untimed events use an extension
because the Pentabarf event format requires a start and duration.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from config import EVENT_GUID_PREFIX, LANGUAGES, SCHEDULE_PREFIX
from generate import ROOT, Lecture, parse_reviewed
from schedule_site import build_site


def duration_minutes(event: dict, same_day: list[dict]) -> int:
    """Calculate a timed event's duration without crossing the next start.

    Args:
        event: Programme event with a start and optional duration override.
        same_day: All events on the same day, including untimed events.

    Returns:
        Duration in minutes. Without an override, use the next start capped by
        the default for the event type, or the default if no later start exists.
    """
    if 'duration_minutes' in event:
        return int(event['duration_minutes'])
    defaults = {'lecture': 45, 'panel': 60, 'performance': 30, 'ceremony': 30,
                'break': 45, 'activity': 45, 'social': 60}
    limit = defaults.get(event['kind'], 45)
    current = datetime.fromisoformat(event['date'] + 'T' + event['start'])
    later = [datetime.fromisoformat(item['date'] + 'T' + item['start'])
             for item in same_day if item['start'] and item['start'] > event['start']]
    return max(5, min(limit, int((min(later) - current).total_seconds() / 60))) if later else limit


def create(program: dict, lectures: list[Lecture], lang: str) -> bytes:
    """Serialize the canonical programme to a localized Pentabarf document.

    Args:
        program: Programme metadata and timed and untimed events.
        lectures: Reviewed workbook texts associated with lecture events.
        lang: Output language, either ``cz`` or ``en``.

    Returns:
        UTF-8 XML bytes, including reviewed abstracts and stable published IDs.
    """
    streams = json.loads((ROOT / 'data' / 'streams.json').read_text(encoding='utf-8'))
    stream_by_event = {event_id: stream['url'] for stream in streams for event_id in stream['events']}
    lecture_by_id = {lecture.event['id']: lecture for lecture in lectures}
    root = ET.Element('schedule')
    conference = ET.SubElement(root, 'conference')
    source = program['conference']
    metadata = {'title': source[f'title_{lang}'], 'subtitle': source[f'subtitle_{lang}'],
                **{key: str(source[key]) for key in
                   ('venue', 'city', 'start', 'end', 'days', 'day_change', 'timeslot_duration')}}
    for key, value in metadata.items():
        ET.SubElement(conference, key).text = value

    days = defaultdict(list)
    for item in program['events']:
        days[item['date']].append(item)
    for index, day in enumerate(sorted(days), 1):
        day_element = ET.SubElement(root, 'day', {'index': str(index), 'date': day})
        untimed = ET.SubElement(day_element, 'untimed_events')
        for item in (item for item in days[day] if not item['start']):
            ET.SubElement(untimed, 'event', {'guid': f"{EVENT_GUID_PREFIX}{item['id']}"}).text = item[f'title_{lang}']
        timed = [item for item in days[day] if item['start']]
        for room_name in sorted({item['room'] for item in timed}):
            room = ET.SubElement(day_element, 'room', {'name': room_name})
            room_events = sorted((item for item in timed if item['room'] == room_name),
                                 key=lambda item: item['start'])
            for item in room_events:
                event_index = program['events'].index(item)
                event = ET.SubElement(room, 'event', {'id': str(1000 + event_index),
                                                      'guid': f"{EVENT_GUID_PREFIX}{item['id']}"})
                minutes = duration_minutes(item, days[day])
                lecture = lecture_by_id.get(item['id'])
                abstract = (lecture.abstract_cz if lang == 'cz' else lecture.abstract_en) if lecture else item.get('notes', '')
                elements = {'start': item['start'], 'duration': f'{minutes // 60:02d}:{minutes % 60:02d}',
                            'room': room_name, 'slug': item['id'], 'title': item[f'title_{lang}'],
                            'subtitle': '', 'track': item['kind'].capitalize(), 'type': item['kind'],
                            'language': ', '.join(item.get('spoken_languages', [])) or 'und',
                            'abstract': abstract, 'description': ''}
                for key, value in elements.items():
                    ET.SubElement(event, key).text = value
                links = ET.SubElement(event, 'links')
                ET.SubElement(links, 'link', {'href': program['urls'][lang]}).text = (
                    'Online program' if lang == 'cz' else 'Live programme'
                )
                if item['id'] in stream_by_event:
                    ET.SubElement(links, 'link', {'href': stream_by_event[item['id']]}).text = (
                        'Online stream' if lang == 'en' else 'Online přenos'
                    )
                people = ET.SubElement(event, 'persons')
                for person_index, person in enumerate(item['persons'], 1):
                    ET.SubElement(people, 'person', {'id': str(100000 + event_index * 10 + person_index)}).text = person
                if item.get('moderator'):
                    ET.SubElement(people, 'person', {'id': str(100000 + event_index * 10 + 9)}).text = item['moderator']
    return minidom.parseString(ET.tostring(root, encoding='utf-8')).toprettyxml(indent='  ', encoding='utf-8')


def main() -> None:
    """Regenerate both XML schedules and the website from the local sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xlsx', type=Path, default=ROOT / 'data' / 'abstracts_review.xlsx')
    args = parser.parse_args()
    program = json.loads((ROOT / 'data' / 'program.json').read_text(encoding='utf-8'))
    lectures = parse_reviewed(args.xlsx, program)
    (ROOT / 'schedule').mkdir(exist_ok=True)
    for lang in LANGUAGES:
        path = ROOT / 'schedule' / f'{SCHEDULE_PREFIX}_{lang}.xml'
        path.write_bytes(create(program, lectures, lang))
        print(f'{path}: {len(program["events"])} source events')
    build_site()


if __name__ == '__main__':
    main()
