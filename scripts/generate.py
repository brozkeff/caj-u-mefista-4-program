"""Generate V4 reviewed Markdown, bilingual XeLaTeX and a programme QA report.

The reviewed worksheet is the sole source of abstract text. Programme and
booklet JSON keep editorial content separate from the rendering rules.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from config import LANGUAGES, REVIEWED_SHEET
from xlsx_reader import read_worksheet

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("Autor", "Zkrácený abstrakt CZ", "Short abstract EN")
TEX_ESCAPE = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "%": r"\%",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
}


def booklet_data() -> dict:
    """Load booklet copy and presentation settings without caching edits.

    Returns:
        The localized cover, programme and contact settings.
    """
    return json.loads((ROOT / "data" / "booklet.json").read_text(encoding="utf-8"))


def norm(value: str) -> str:
    """Normalize an author name for matching across sources.

    Args:
        value: Author name, possibly with worksheet annotations.

    Returns:
        Accent- and case-insensitive matching key.
    """
    value = re.sub(r"\([^)]*\)", "", value)  # affiliation flags in 'Autor'
    value = re.sub(r"[\"„“’]", "", value).replace(",", " ")
    value = " ".join(value.split())
    if value.startswith("Szönyi György"):
        value = "György Szönyi"
    value = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in value if not unicodedata.combining(char))


def author_clean(value: str) -> str:
    """Remove worksheet annotations while preserving the author's name.

    Args:
        value: Original worksheet author field.

    Returns:
        Editorially normalized author name.
    """
    value = re.sub(r"\([^)]*\)", "", value)
    value = " ".join(value.split()).strip()
    if value.startswith("Szönyi, György"):
        return "György Szönyi"
    return value.replace('"Jelena"', "„Jelena“")


def slug(text: str) -> str:
    """Generate an ASCII filename token.

    Args:
        text: Original author or lecture title.

    Returns:
        Lowercase, hyphenated token of at most 64 characters.
    """
    t = unicodedata.normalize("NFKD", text.casefold())
    t = "".join(x for x in t if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:64].rstrip("-")


def tex(value: str) -> str:
    """Escape user text as literal TeX content.

    Args:
        value: Unescaped text.

    Returns:
        Text with TeX metacharacters escaped.
    """
    return "".join(TEX_ESCAPE.get(c, c) for c in value)


def typeset(value: str, language: str) -> str:
    """Escape text and bind Czech short words to the following word.

    Args:
        value: Unescaped text.
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX-safe text with nonbreaking Czech short-word spaces.
    """
    if language != "cz":
        return tex(value)
    parts = re.split(
        r"(?i)(?<!\w)([vkszouai]|ve|ke|ze|se|do|na|po|od|za|ku) +(?=\S)", value
    )
    return "".join(
        tex(part) + ("~" if index % 2 else "") for index, part in enumerate(parts)
    )


def localized_author(author: str, language: str) -> str:
    """Use the edition's quotation marks in the editorial author name.

    Args:
        author: Cleaned author name.
        language: Edition code, ``cz`` or ``en``.

    Returns:
        Author name with edition-appropriate quotation marks.
    """
    return re.sub(r"„([^“]*)“", r"“\1”", author) if language == "en" else author


def paragraphs(value: str, language: str) -> str:
    """Preserve paragraph divisions and join wrapped source lines.

    Args:
        value: Reviewed workbook abstract.
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX-safe paragraphs separated by blank lines.
    """
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if language == "cz":
        # These reviewed ASCII quote pairs otherwise trigger Babel shorthand and
        # consume the following spaces; keep the workbook and Markdown intact.
        value = value.replace('"mix and match"', "„mix and match“")
        value = value.replace('"rituály"', "„rituály“")
    return "\n\n".join(
        typeset(" ".join(x.split()), language)
        for x in re.split(r"\n\s*\n", value)
        if x.strip()
    )


def yaml_quote(value: str) -> str:
    """Quote a string as a YAML-compatible JSON scalar.

    Args:
        value: Metadata value.

    Returns:
        Unicode-preserving quoted scalar.
    """
    return json.dumps(value, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class Lecture:
    row: int
    author: str
    author_original: str
    event: dict
    abstract_cz: str
    abstract_en: str


def parse_reviewed(xlsx: Path, program: dict) -> list[Lecture]:
    """Read selected columns by their names; reject missing or duplicate authors.

    Args:
        xlsx: The current, manually reviewed conference spreadsheet export.
        program: Canonical programme metadata mapping talks by author.

    Returns:
        Lecture records in programme order, each with its original XLSX row.
    """
    sheet = read_worksheet(xlsx, REVIEWED_SHEET, max_row=250)
    header = {
        re.sub(r"\s+", " ", v).strip().casefold(): k
        for k, v in sheet.cells.get(1, {}).items()
        if v
    }
    mapping = {}
    for label in REQUIRED:
        name = label.casefold()
        if name not in header:
            raise ValueError(
                f"Required sheet column missing: {label!r}; found {header}"
            )
        mapping[label] = header[name]
    lecture_events = {
        norm(e["persons"][0]): e for e in program["events"] if e["kind"] == "lecture"
    }
    if len(lecture_events) != sum(e["kind"] == "lecture" for e in program["events"]):
        raise ValueError("Duplicate lecture author in programme JSON")
    seen = set()
    found = []
    for row in sorted(sheet.cells):
        if row == 1:
            continue
        raw_author = sheet.get(row, mapping["Autor"])
        if not raw_author.strip():
            continue
        key = norm(raw_author)
        if key not in lecture_events:
            raise ValueError(
                f"XLSX row {row}: unmatched author {raw_author!r}; update data/program.json explicitly"
            )
        if key in seen:
            raise ValueError(f"Duplicated speaker {raw_author!r} (row {row})")
        cz = sheet.get(row, mapping[REQUIRED[1]]).strip()
        en = sheet.get(row, mapping[REQUIRED[2]]).strip()
        if not cz or not en:
            raise ValueError(
                f"Missing reviewed abstract CZ/EN in row {row}: {raw_author!r}"
            )
        seen.add(key)
        found.append(
            Lecture(
                row, author_clean(raw_author), raw_author, lecture_events[key], cz, en
            )
        )
    if seen != lecture_events.keys():
        missing = sorted(lecture_events.keys() - seen)
        raise ValueError(
            f"Programme and reviewed XLSX lecture mismatch. Missing: {missing}"
        )
    return sorted(found, key=lambda lec: (lec.event["date"], lec.event["start"]))


def write_markdown(lectures: list[Lecture], xlsx: Path) -> None:
    """Recreate source-traceable Markdown files for both editions.

    Args:
        lectures: Reviewed lectures in programme order.
        xlsx: Source workbook path for metadata.
    """
    for lang in LANGUAGES:
        folder = ROOT / "content" / lang
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.md"):
            old.unlink()
        for lec in lectures:
            e = lec.event
            title = e[f"title_{lang}"]
            body = lec.abstract_cz if lang == "cz" else lec.abstract_en
            family = lec.author.split()[-1]
            base = f"{slug(family)}_{slug(' '.join(lec.author.split()[:-1]))}-{slug(title)}-{lang}.md"
            author = localized_author(lec.author, lang)
            front = {
                "title": title,
                "author": author,
                "date": e["date"],
                "time": e["start"],
                "event_id": e["id"],
                "language": lang,
                "source_file": xlsx.name,
                "sheet": REVIEWED_SHEET,
                "source_row": lec.row,
                "source_columns": {
                    "author": "Autor",
                    "abstract_cz": "Zkrácený abstrakt CZ",
                    "abstract_en": "Short abstract EN",
                },
                "status": "reviewed worksheet source; copied verbatim",
                "edition": "V4",
            }
            metadata = "\n".join(
                f"{k}: {yaml_quote(v) if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}"
                for k, v in front.items()
            )
            (folder / base).write_text(
                f"---\n{metadata}\n---\n\n# {title}\n\n**{author}**\n\n{body}\n",
                encoding="utf-8",
            )


def days_and_events(program: dict, language: str) -> str:
    """Render the two-column programme page and language-specific QR.

    Args:
        program: Canonical programme and schedule URLs.
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX source for the programme page.
    """
    group_a = []
    group_b = []
    settings = booklet_data()["programme"]
    day_labels = settings["day_labels"]
    split = settings["column_break"]
    for e in program["events"]:
        # Balanced across the two independent columns; no programme overflow into a second page.
        target = (
            group_a
            if (
                e["date"] < split["date"]
                or (
                    e["date"] == split["date"]
                    and (e["start"] or "00:00") <= split["after"]
                )
            )
            else group_b
        )
        target.append(e)

    def one_col(items: list[dict]) -> str:
        """Render a programme column with day headings and panel guests.

        Args:
            items: Ordered events assigned to this column.

        Returns:
            TeX source for the column contents.
        """
        lines = []
        prev = None
        for e in items:
            if e["date"] != prev:
                lines.append(r"\daytitle{" + tex(day_labels[language][e["date"]]) + "}")
            prev = e["date"]
            title = e[f"title_{language}"]
            lines.append(
                r"\progentry{"
                + (e["start"] or "—")
                + "}{"
                + typeset(title, language)
                + "}{}"
            )
            if e["kind"] == "panel":
                lead = settings["guests"][language]
                mod = settings["chair"][language]
                notes = (
                    lead
                    + ", ".join(e["persons"])
                    + (mod + e["moderator"] if e.get("moderator") else "")
                )
                lines.append(
                    r"{\RaggedRight\color{muted}\fontsize{6.3}{7.3}\selectfont "
                    + typeset(notes, language)
                    + r"\par}\vspace{1pt}"
                )
        return "\n".join(lines)

    htmlink = program["urls"][language]
    return "\n".join(
        [
            r"\clearpage\thispagestyle{fancy}",
            r"\noindent{\displayfont\fontsize{14}{15}\selectfont\bfseries "
            + tex(settings["heading"][language])
            + r"}\hfill\href{"
            + htmlink
            + r"}{\includegraphics[width=18mm,height=18mm,keepaspectratio]{program-qr-"
            + language
            + r"}}\par",
            r"\vspace{3mm}{\sffamily\fontsize{6.7}{8}\selectfont\color{muted}\url{"
            + htmlink
            + r"}\par}\vspace{1mm}",
            r"\noindent\begin{minipage}[t]{0.475\linewidth}\vspace{0pt}",
            one_col(group_a),
            r"\end{minipage}\hfill\begin{minipage}[t]{0.49\linewidth}\vspace{0pt}",
            one_col(group_b),
            r"\end{minipage}\par\clearpage",
        ]
    )


def cover(language: str) -> str:
    """Render the A5 cover with logo, title, date and venue.

    Args:
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX source for the cover.
    """
    data = booklet_data()["cover"]
    return "\n".join(
        [
            r"\thispagestyle{empty}\begin{center}\vspace*{5mm}",
            r"\makebox[\textwidth][c]{\includegraphics[width=130mm]{logo-"
            + language
            + r"}}\par",
            r"\vspace{4mm}{\displayfont\fontsize{16}{18}\selectfont\bfseries "
            + tex(data["title"][language])
            + r"\par}",
            r"\vspace{1mm}{\sffamily\fontsize{9.2}{11}\selectfont "
            + tex(data["date"])
            + r"\par}",
            r"{\sffamily\fontsize{9.1}{11}\selectfont " + tex(data["venue"]) + r"\par}",
            r"\end{center}\clearpage",
        ]
    )


def stream(language: str) -> str:
    """Render the editable stream information on its own page.

    Args:
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX source with the stream description, URL and QR code.
    """
    data = json.loads((ROOT / "data" / "stream.json").read_text(encoding="utf-8"))
    url = data["url"]
    return "\n".join(
        [
            r"\clearpage\thispagestyle{fancy}\vspace*{5mm}",
            r"{\displayfont\fontsize{17}{19}\selectfont\bfseries "
            + typeset(data[language]["heading"], language)
            + r"\par}\divider\vspace{3mm}",
            r"{\fontsize{10}{13}\selectfont "
            + typeset(data[language]["text"], language)
            + r"\par}\vspace{8mm}",
            r"\begin{center}\href{"
            + url
            + r"}{\includegraphics[width=45mm]{stream-qr}}\par\vspace{5mm}",
            r"{\sffamily\fontsize{9}{11}\selectfont\url{" + url + r"}\par}\end{center}",
        ]
    )


def contacts(language: str) -> str:
    """Render organizer contacts in the appropriate language order.

    Args:
        language: Edition code, ``cz`` or ``en``.

    Returns:
        TeX source for the final contacts page.
    """
    data = booklet_data()["contacts"]
    heading = tex(data["heading"][language])
    people = [data["people"][index] for index in data["order"][language]]
    out = [
        r"\clearpage\thispagestyle{fancy}\vspace*{5mm}",
        r"{\displayfont\fontsize{17}{19}\selectfont\bfseries "
        + heading
        + r"\par}\divider\vspace{3mm}",
    ]
    for person in people:
        name, role, phone, fb = (
            person["name"],
            person["role"][language],
            person["phone"],
            person["facebook"],
        )
        facebook = r"Facebook / Messenger: \url{" + fb + "}"
        out.append(
            r"\contact{"
            + typeset(name, language)
            + "}{"
            + typeset(role, language)
            + "}{"
            + tex(phone)
            + "}{"
            + facebook
            + "}"
        )
    url = data["url"][language]
    out.append(
        r"\vfill{\sffamily\fontsize{7.2}{9}\selectfont\color{muted}\url{"
        + url
        + r"}\par}\clearpage"
    )
    return "\n".join(out)


def write_tex(lectures: list[Lecture], program: dict) -> None:
    """Write XeLaTeX sources with continuously flowing abstracts.

    Args:
        lectures: Reviewed lectures in programme order.
        program: Canonical programme and schedule URLs.
    """
    for language in LANGUAGES:
        parts = [
            r"\input{layout.tex}",
            r"\begin{document}",
            r"\selectlanguage{" + ("czech" if language == "cz" else "english") + "}",
            cover(language),
            days_and_events(program, language),
        ]
        parts.append(
            r"\vspace*{2mm}{\displayfont\fontsize{16}{18}\selectfont\bfseries "
            + tex(booklet_data()["cover"]["title"][language])
            + r"\par}\divider"
        )
        for lecture in lectures:
            e = lecture.event
            day = date.fromisoformat(e["date"])
            stamp = (
                f"{day.day}. {day.month}. · {e['start']}"
                if language == "cz"
                else f"{day.day} {day.strftime('%b')} · {e['start']}"
            )
            abstract = lecture.abstract_cz if language == "cz" else lecture.abstract_en
            parts.append(
                "\\talk{"
                + tex(stamp)
                + "}{"
                + typeset(e[f"title_{language}"], language)
                + "}{"
                + typeset(localized_author(lecture.author, language), language)
                + "}{"
                + paragraphs(abstract, language)
                + "}"
            )
        parts.append(stream(language))
        parts.append(contacts(language))
        parts.append(r"\end{document}")
        (ROOT / "tex" / "generated" / f"{language}.tex").write_text(
            "\n".join(parts) + "\n", encoding="utf-8"
        )


def generate(xlsx: Path) -> tuple[list[Lecture], dict]:
    """Validate inputs and generate all reproducible source artifacts.

    Args:
        xlsx: Reviewed workbook path.

    Returns:
        Lectures and canonical programme information.
    """
    program = json.loads((ROOT / "data" / "program.json").read_text(encoding="utf-8"))
    lectures = parse_reviewed(xlsx, program)
    write_markdown(lectures, xlsx)
    write_tex(lectures, program)
    sha = hashlib.sha256(xlsx.read_bytes()).hexdigest()
    summary = {
        "version": program["version"],
        "xlsx_sha256": sha,
        "sheet": REVIEWED_SHEET,
        "column_names": list(REQUIRED),
        "abstracts": len(lectures),
        "events": len(program["events"]),
        "event_lectures": sum(e["kind"] == "lecture" for e in program["events"]),
        "source_rows": {l.author: l.row for l in lectures},
        "source": "user provided reviewed XLSX and HTML, not V2/V3",
    }
    (ROOT / "build" / "qa_source.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return lectures, program
