"""Check generated publications against reviewed sources before release.

The programme, reviewed abstracts and stream data are the authorities; comparing
outputs to them catches stale or incomplete builds without freezing old content.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from config import A5_PREFIX, DUPLEX_NAME, EVENT_GUID_PREFIX, LANGUAGES, READER_NAME, SCHEDULE_PREFIX
from generate import ROOT, localized_author, parse_reviewed


def verify_schedule(tree: ET.ElementTree, program: dict, language: str) -> None:
    """Check the XML schedule against every timed and untimed source event.

    Args:
        tree: Parsed schedule XML for one language.
        program: Canonical programme data.
        language: Programme language code, ``cz`` or ``en``.

    Raises:
        AssertionError: An event is missing, duplicated, stale or incomplete.
    """
    source = program['events']
    timed = [event for event in source if event['start'] is not None]
    untimed = [event for event in source if event['start'] is None]
    xml_timed = tree.findall('.//day/room/event')
    xml_untimed = tree.findall('.//day/untimed_events/event')

    def guid(event: dict) -> str:
        """Return the stable XML GUID for a source event.

        Args:
            event: Canonical programme event.

        Returns:
            Published event GUID.
        """
        return f"{EVENT_GUID_PREFIX}{event['id']}"

    assert Counter(event.get('guid') for event in xml_timed) == Counter(guid(event) for event in timed)
    assert Counter(event.get('guid') for event in xml_untimed) == Counter(guid(event) for event in untimed)
    timed_by_guid = {event.get('guid'): event for event in xml_timed}
    untimed_by_guid = {event.get('guid'): event for event in xml_untimed}
    for event in timed:
        published = timed_by_guid[guid(event)]
        assert published.findtext('title') == event[f'title_{language}'], event['id']
        assert published.findtext('start') == event['start'], event['id']
        assert published.findtext('type') == event['kind'], event['id']
        assert published.findtext('duration'), event['id']
    for event in untimed:
        assert untimed_by_guid[guid(event)].text == event[f'title_{language}'], event['id']


def verify() -> None:
    """Check source mapping, schedules, booklets and imposed PDFs.

    Raises:
        AssertionError: A generated output is stale, missing or inconsistent.
        OSError: A source or output cannot be read.
        ValueError: Reviewed workbook data is invalid.
        ET.ParseError: A generated schedule is invalid XML.
    """
    program = json.loads((ROOT / 'data' / 'program.json').read_text(encoding='utf-8'))
    stream = json.loads((ROOT / 'data' / 'stream.json').read_text(encoding='utf-8'))
    booklet = json.loads((ROOT / 'data' / 'booklet.json').read_text(encoding='utf-8'))
    lectures = parse_reviewed(ROOT / 'data' / 'abstracts_review.xlsx', program)
    assert len(lectures) == 14
    assert sum(event['kind'] == 'lecture' for event in program['events']) == 14
    pdfs = {}
    for language in LANGUAGES:
        files = sorted((ROOT / 'content' / language).glob('*.md'))
        assert len(files) == len(lectures), (language, len(files))
        texts = [path.read_text(encoding='utf-8') for path in files]
        for lecture in lectures:
            body = lecture.abstract_cz if language == 'cz' else lecture.abstract_en
            assert sum(body in text for text in texts) == 1, lecture.author
        schedule = ROOT / 'schedule' / f'{SCHEDULE_PREFIX}_{language}.xml'
        assert (ROOT / 'build' / 'site' / f'schedule-{language}.xml').read_bytes() == schedule.read_bytes(), language
        tree = ET.parse(schedule)
        verify_schedule(tree, program, language)
        xml_events = {event.get('guid'): event for event in tree.findall('.//day/room/event')}
        for lecture in lectures:
            body = lecture.abstract_cz if language == 'cz' else lecture.abstract_en
            guid = f"{EVENT_GUID_PREFIX}{lecture.event['id']}"
            assert xml_events[guid].findtext('abstract') == body, (language, lecture.author)

        pdf = PdfReader(ROOT / 'build' / 'pdf' / f'{A5_PREFIX}_{language.upper()}.pdf')
        pdfs[language] = pdf
        text = '\n'.join(page.extract_text() for page in pdf.pages)
        assert booklet['programme']['heading'][language] in pdf.pages[1].extract_text()
        for lecture in lectures:
            assert localized_author(lecture.author, language) in text, (language, lecture.author)
        assert stream[language]['heading'] in pdf.pages[-2].extract_text()
        assert stream['url'] in pdf.pages[-2].extract_text()
        assert booklet['contacts']['heading'][language] in pdf.pages[-1].extract_text()
        assert 'WhatsApp' in pdf.pages[-1].extract_text()
    count = len(pdfs['cz'].pages)
    assert count == len(pdfs['en'].pages) and count % 2 == 0
    both = PdfReader(ROOT / 'build' / 'pdf' / READER_NAME)
    imposed = PdfReader(ROOT / 'build' / 'pdf' / DUPLEX_NAME)
    assert len(both.pages) == 2 * count
    assert len(imposed.pages) == len(both.pages) // 2
    print(f"PASS: {len(lectures)} reviewed abstracts x 2; {len(program['events'])} programme entries")
    print(f'PASS: Pentabarf, {count} A5 pages per language, {len(imposed.pages)} A4 sides')


if __name__ == '__main__':
    try:
        verify()
    except (AssertionError, ValueError, OSError, ET.ParseError) as error:
        print(f'QA FAILED: {error}', file=sys.stderr)
        sys.exit(1)
