"""Read text cells from an XLSX worksheet using Python's standard library.

Handles shared strings, rich strings, inline strings and cached formula results.
This module deliberately does not edit an XLSX or depend on Excel/LibreOffice.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"x": MAIN_NS, "r": OFFICE_REL_NS, "p": PACKAGE_REL_NS}
REF_PATTERN = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")


@dataclass(frozen=True, slots=True)
class Worksheet:
    """Read-only worksheet mapping preserving Excel row indices."""

    name: str
    cells: dict[int, dict[str, str]]

    def get(self, row: int, column: str) -> str:
        """Return text from one cell, or an empty string.

        Args:
            row: One-based worksheet row number.
            column: Excel column letters, such as ``F``.

        Returns:
            Text from the cell, with original line breaks preserved.
        """
        return self.cells.get(row, {}).get(column.upper(), "")


def _read_xml(archive: ZipFile, member: str) -> ET.Element:
    """Load an XML member from an XLSX archive."""
    try:
        return ET.fromstring(archive.read(member))
    except KeyError as exc:
        raise ValueError(f"Missing XLSX part: {member}") from exc


def _shared_strings(archive: ZipFile) -> list[str]:
    """Return the shared-string table, including concatenated rich text runs."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _read_xml(archive, "xl/sharedStrings.xml")
    return [
        "".join(text.text or "" for text in item.findall(".//x:t", NS))
        for item in root.findall("x:si", NS)
    ]


def _resolve_sheet(archive: ZipFile, sheet_name: str) -> str:
    """Resolve sheet names through workbook relations, not sheet order."""
    workbook = _read_xml(archive, "xl/workbook.xml")
    relationships = _read_xml(archive, "xl/_rels/workbook.xml.rels")
    rel_id: str | None = None
    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        if sheet.attrib.get("name") == sheet_name:
            rel_id = sheet.attrib.get(f"{{{OFFICE_REL_NS}}}id")
            break
    if rel_id is None:
        available = ", ".join(
            sheet.attrib.get("name", "")
            for sheet in workbook.findall("x:sheets/x:sheet", NS)
        )
        raise ValueError(f"Worksheet {sheet_name!r} not found; available: {available}")
    for rel in relationships.findall("p:Relationship", NS):
        if rel.attrib.get("Id") != rel_id:
            continue
        target = rel.attrib.get("Target", "")
        if not target or ".." in target.split("/"):
            raise ValueError(f"Unsafe worksheet target: {target!r}")
        member = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join("xl", target))
        )
        if not member.startswith("xl/worksheets/"):
            raise ValueError(f"Unexpected worksheet part: {member}")
        return member
    raise ValueError(f"No XLSX relationship found for worksheet {sheet_name!r}")


def read_worksheet(
    path: Path,
    sheet_name: str,
    *,
    columns: set[str] | None = None,
    max_row: int | None = None,
) -> Worksheet:
    """Read one worksheet while keeping its original row numbers.

    Args:
        path: XLSX file path.
        sheet_name: Exact Excel/Google Sheets worksheet name.
        columns: Optional set of allowed column letters. Other cells are ignored.
        max_row: Optional inclusive maximum row number. Other rows are ignored.

    Returns:
        A worksheet with cell text keyed by the original row and column.

    Raises:
        ValueError: When the workbook is malformed, unsupported, or missing
            a requested worksheet or a cached formula result.
    """
    try:
        with ZipFile(path) as archive:
            shared = _shared_strings(archive)
            root = _read_xml(archive, _resolve_sheet(archive, sheet_name))
            rows: dict[int, dict[str, str]] = {}
            for row in root.findall("x:sheetData/x:row", NS):
                row_number = int(row.attrib["r"])
                if max_row is not None and row_number > max_row:
                    continue
                values: dict[str, str] = {}
                for cell in row.findall("x:c", NS):
                    match = REF_PATTERN.fullmatch(cell.attrib.get("r", ""))
                    if match is None:
                        raise ValueError(f"Invalid cell reference: {cell.attrib!r}")
                    column, actual_row = match.groups()
                    if columns is not None and column not in columns:
                        continue
                    if int(actual_row) != row_number:
                        raise ValueError(f"Inconsistent XLSX cell row: {cell.attrib!r}")
                    kind = cell.attrib.get("t", "n")
                    raw = cell.find("x:v", NS)
                    if kind == "inlineStr":
                        value = "".join(
                            node.text or "" for node in cell.findall("x:is/.//x:t", NS)
                        )
                    elif raw is None:
                        if cell.find("x:f", NS) is not None:
                            raise ValueError(
                                f"Formula in {column}{row_number} has no cached value; "
                                "recalculate/export the workbook before building"
                            )
                        value = ""
                    elif kind == "s":
                        index = int(raw.text or "-1")
                        try:
                            value = shared[index]
                        except IndexError as exc:
                            raise ValueError(
                                f"Invalid shared string index in {column}{row_number}"
                            ) from exc
                    else:
                        value = raw.text or ""
                    values[column] = value.replace("\r\n", "\n").replace("\r", "\n")
                rows[row_number] = values
            return Worksheet(name=sheet_name, cells=rows)
    except (BadZipFile, OSError, ET.ParseError) as exc:
        raise ValueError(f"Cannot read XLSX workbook {path}: {exc}") from exc
