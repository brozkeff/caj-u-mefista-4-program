"""Protect reviewed text and editable booklet copy during generator changes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate


class GeneratorRegressionTests(unittest.TestCase):
    """Verify the workbook contract and generated TeX boundaries."""

    def test_reviewed_workbook_matches_programme_in_order(self):
        """Every reviewed abstract maps to one programme lecture in order."""
        program = json.loads((ROOT / "data/program.json").read_text(encoding="utf-8"))
        lectures = generate.parse_reviewed(ROOT / "data/abstracts_review.xlsx", program)
        self.assertEqual(len(lectures), 14)
        self.assertEqual(
            [x.event["id"] for x in lectures],
            [e["id"] for e in program["events"] if e["kind"] == "lecture"],
        )
        self.assertTrue(all(x.abstract_cz and x.abstract_en for x in lectures))
        self.assertEqual(len({x.row for x in lectures}), 14)

    def test_paragraphs_and_tex_metacharacters(self):
        """Paragraph boundaries and TeX escaping survive rendering."""
        self.assertEqual(
            generate.paragraphs("První % řádek\nčást\n\nDruhý & třetí", "cz"),
            "První \\% řádek část\n\nDruhý \\& třetí",
        )
        self.assertEqual(generate.typeset("v lese a na poli", "cz"), "v~lese a~na~poli")
        self.assertEqual(
            generate.paragraphs("One\nline\n\nNext #2", "en"), "One line\n\nNext \\#2"
        )

    def test_booklet_copy_is_read_from_data_and_escaped(self):
        """Cover and contact changes come from data and remain TeX-safe."""
        data = generate.booklet_data()
        data["cover"]["venue"] = "Venue & place"
        data["contacts"]["people"][0]["name"] = "First & Last"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data/booklet.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            with patch.object(generate, "ROOT", root):
                self.assertIn(r"Venue \& place", generate.cover("cz"))
                self.assertIn(r"First \& Last", generate.contacts("cz"))
                self.assertIn("First", generate.contacts("en"))

    def test_mismatched_author_rejected(self):
        """A workbook author outside the canonical programme is rejected."""
        program = json.loads((ROOT / "data/program.json").read_text(encoding="utf-8"))
        lecture = next(e for e in program["events"] if e["kind"] == "lecture")
        lecture["persons"][0] = "Nobody of This Name"
        with self.assertRaisesRegex(ValueError, "unmatched author"):
            generate.parse_reviewed(ROOT / "data/abstracts_review.xlsx", program)


if __name__ == "__main__":
    unittest.main()
