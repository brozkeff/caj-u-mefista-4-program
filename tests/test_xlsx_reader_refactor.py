"""Exercise workbook import without depending on an Excel installation."""

from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from xlsx_reader import read_worksheet

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_workbook(path: Path, cells: str, target: str = "worksheets/sheet2.xml") -> None:
    """Create a minimal XLSX with a non-first reviewed worksheet.

    Args:
        path: Destination archive path.
        cells: XML to place inside sheetData.
        target: Reviewed worksheet relationship target.
    """
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", f'''<workbook xmlns="{MAIN}" xmlns:r="{OFFICE}">
          <sheets><sheet name="Other" r:id="rId1"/><sheet name="Přednášky tisk" r:id="rId2"/></sheets></workbook>''')
        archive.writestr("xl/_rels/workbook.xml.rels", f'''<Relationships xmlns="{PACKAGE}">
          <Relationship Id="rId2" Target="{target}"/></Relationships>''')
        archive.writestr("xl/sharedStrings.xml", f'''<sst xmlns="{MAIN}">
          <si><r><t>Čaj </t></r><r><t>u Mefista</t></r></si></sst>''')
        archive.writestr("xl/worksheets/sheet2.xml", f'<worksheet xmlns="{MAIN}"><sheetData>{cells}</sheetData></worksheet>')


class WorksheetRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        """Create a temporary workbook path for each test."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.xlsx"

    def test_text_types_formulas_rows_and_filters(self) -> None:
        """Preserve worksheet text, cached values, row numbers, and filters."""
        make_workbook(self.path, '''<row r="1">
          <c r="A1" t="s"><v>0</v></c>
          <c r="C1" t="inlineStr"><is><r><t>first\n\n</t></r><r><t>second</t></r></is></c>
          <c r="AA1"><f>1+1</f><v>2</v></c></row>
          <row r="9"><c r="A9" t="str"><v>last</v></c></row>''')
        sheet = read_worksheet(self.path, "Přednášky tisk")
        self.assertEqual(sheet.cells, {1: {"A": "Čaj u Mefista", "C": "first\n\nsecond", "AA": "2"}, 9: {"A": "last"}})
        self.assertEqual(sheet.get(1, "aa"), "2")
        self.assertEqual(sheet.get(20, "A"), "")
        self.assertEqual(read_worksheet(self.path, "Přednášky tisk", columns={"C"}, max_row=1).cells,
                         {1: {"C": "first\n\nsecond"}})

    def test_invalid_inputs_fail_clearly(self) -> None:
        """Reject missing cached values, bad rows, and unsafe relations."""
        make_workbook(self.path, '<row r="1"><c r="A1"><f>1+1</f></c></row>')
        with self.assertRaisesRegex(ValueError, "no cached value"):
            read_worksheet(self.path, "Přednášky tisk")
        with self.assertRaisesRegex(ValueError, "not found"):
            read_worksheet(self.path, "Missing")
        make_workbook(self.path, '<row r="1"><c r="A2"><v>1</v></c></row>')
        with self.assertRaisesRegex(ValueError, "Inconsistent XLSX cell row"):
            read_worksheet(self.path, "Přednášky tisk")
        make_workbook(self.path, '', target='../unsafe.xml')
        with self.assertRaisesRegex(ValueError, "Unsafe worksheet target"):
            read_worksheet(self.path, "Přednášky tisk")

    def test_reviewed_workbook_uses_headers_and_exact_text(self) -> None:
        """Read the reviewed source using its expected headers and text."""
        root = Path(__file__).resolve().parents[1]
        sheet = read_worksheet(root / "data/abstracts_review.xlsx", "Přednášky tisk")
        self.assertEqual(sheet.get(1, "A"), "Autor")
        self.assertEqual(sheet.get(1, "C"), "Zkrácený abstrakt CZ")
        self.assertEqual(sheet.get(1, "D"), "Short abstract EN")
        self.assertEqual(sheet.get(2, "A"), "Jan Ševčík")
        self.assertTrue(sheet.get(2, "C").startswith("Přednáška stručně představí"))


if __name__ == "__main__":
    unittest.main()
