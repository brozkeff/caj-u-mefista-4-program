"""V4 release QA: source mapping, editable artifacts, programme, PDF and XML."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from generate import ROOT, localized_author, parse_reviewed


def verify() -> None:
    """Assert that the built outputs match the current reviewed source.

    Raises:
        AssertionError: If a source or generated artifact is stale, missing or invalid.
    """
    meta = json.loads((ROOT / "data" / "program.json").read_text(encoding="utf-8"))
    lectures = parse_reviewed(ROOT / "data" / "abstracts_review.xlsx", meta)
    assert len(lectures) == 14
    assert len(meta["events"]) == 38
    assert sum(e["kind"] == "lecture" for e in meta["events"]) == 14
    assert sum(e["kind"] == "panel" for e in meta["events"]) == 4
    assert not any("Chaitow" in name for e in meta["events"] if e["kind"] == "lecture" for name in e["persons"])
    assert any("Kindernay" in e["title_cz"] for e in meta["events"] if e["kind"] == "performance")
    for language in ("cz", "en"):
        files = sorted((ROOT / "content" / language).glob("*.md"))
        assert len(files) == 14, (language, len(files))
        for lecture in lectures:
            body = lecture.abstract_cz if language == "cz" else lecture.abstract_en
            assert sum(body in p.read_text(encoding="utf-8") for p in files) == 1, lecture.author
        tree = ET.parse(ROOT / "schedule" / f"Caj_u_Mefista_4_pentabarf_{language}.xml")
        assert (ROOT / "build" / "site" / f"schedule-{language}.xml").read_bytes() == (ROOT / "schedule" / f"Caj_u_Mefista_4_pentabarf_{language}.xml").read_bytes(), language
        untimed = tree.findall(".//day/untimed_events/event")
        expected_untimed = [e for e in meta["events"] if e["start"] is None]
        assert {e.text for e in untimed} == {e[f"title_{language}"] for e in expected_untimed}
        events = tree.findall(".//day/room/event")
        assert len(events) == sum(e["start"] is not None for e in meta["events"]), len(events)
        assert len([e for e in events if e.findtext("type") == "lecture"]) == 14
        assert len([e for e in events if e.findtext("type") == "panel"]) == 4
        for e in events:
            assert e.findtext("duration") and e.findtext("title") and e.findtext("start")
    c = PdfReader(ROOT / "build" / "pdf" / "Caj_u_Mefista_4_A5_CZ.pdf")
    e = PdfReader(ROOT / "build" / "pdf" / "Caj_u_Mefista_4_A5_EN.pdf")
    assert len(c.pages) == len(e.pages) and len(c.pages) % 2 == 0
    assert "Program" in c.pages[1].extract_text() and "Synkretizmus" in c.pages[1].extract_text()
    assert "Programme" in e.pages[1].extract_text() and "Syncretism" in e.pages[1].extract_text()
    assert "Jan Ševčík" in c.pages[2].extract_text()
    assert "Jewish Magic" in e.pages[2].extract_text()
    for lang, pdf in (("cz", c), ("en", e)):
        text = "\n".join(page.extract_text() for page in pdf.pages)
        if lang == "cz":
            normalized = re.sub(r"\s+", " ", text)
            assert "„mix and match“ sekvenci" in normalized
            assert "„rituály“ napříč" in normalized
        for lecture in lectures:
            assert localized_author(lecture.author, lang) in text, (lang, lecture.author)
        assert "ČESKÉ VYDÁNÍ" not in text and "ENGLISH EDITION" not in text
        assert "O TÉTO EDICI" not in text and "Pro anglické znění otočte" not in text
        assert "Důležité kontakty" in text if lang == "cz" else "Key contacts" in text
        assert "WhatsApp" in text
        stream = json.loads((ROOT / "data" / "stream.json").read_text(encoding="utf-8"))
        assert stream[lang]["heading"] in pdf.pages[-2].extract_text()
        assert stream["url"] in pdf.pages[-2].extract_text()
        assert ("Důležité kontakty" if lang == "cz" else "Key contacts") in pdf.pages[-1].extract_text()
    both = PdfReader(ROOT / "build" / "pdf" / "Caj_u_Mefista_4_A5_tete_beche_reader.pdf")
    imposed = PdfReader(ROOT / "build" / "pdf" / "Caj_u_Mefista_4_A4_imposed_duplex.pdf")
    assert len(both.pages) == 2 * len(c.pages)
    assert len(imposed.pages) == len(both.pages) // 2
    print(f"PASS: {len(lectures)} reviewed abstracts x 2; 38 programme entries; 4 panels")
    print(f"PASS: Pentabarf, {len(c.pages)} A5 pages per language, {len(imposed.pages)} A4 sides")


if __name__ == "__main__":
    try:
        verify()
    except (AssertionError, ValueError, OSError, ET.ParseError) as error:
        print(f"QA FAILED: {error}", file=sys.stderr)
        sys.exit(1)
