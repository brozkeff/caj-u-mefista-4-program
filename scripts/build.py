"""Build the bilingual publications from reviewed sources.

A single entry point keeps the generated TeX, schedules, website and print PDFs
consistent, while allowing PDF rendering to be skipped for quick updates.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from config import A5_PREFIX, LANGUAGES, SCHEDULE_PREFIX
from generate import ROOT, generate
from pentabarf import create
from impose import impose
from schedule_site import build_site

PDF_DIR = ROOT / 'build' / 'pdf'


def prepare_qr() -> None:
    """Convert supplied vector QR assets to PDFs for XeLaTeX.

    Raises:
        RuntimeError: If Inkscape is unavailable.
        subprocess.CalledProcessError: If a conversion fails.
    """
    if shutil.which('inkscape') is None:
        raise RuntimeError('inkscape missing; install it to convert the SVG QR codes')
    qr_dir = ROOT / 'build' / 'qr'
    qr_dir.mkdir(parents=True, exist_ok=True)
    for name in ('program-qr-cz', 'program-qr-en', 'stream-qr'):
        subprocess.run(
            ['inkscape', str(ROOT / 'assets' / f'{name}.svg'), '--export-type=pdf',
             f'--export-filename={qr_dir / f"{name}.pdf"}'],
            check=True, capture_output=True, text=True,
        )


def compile_tex(lang: str) -> Path:
    """Compile one A5 edition and retain its log for inspection.

    Args:
        lang: Edition language, either ``cz`` or ``en``.

    Returns:
        Path to the generated A5 PDF.

    Raises:
        RuntimeError: If XeLaTeX is unavailable or compilation fails.
    """
    if shutil.which('xelatex') is None:
        raise RuntimeError('xelatex missing; install texlive-xetex and fonts-noto-core')
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    job = f'{A5_PREFIX}_{lang.upper()}'
    command = [
        'xelatex', '-interaction=nonstopmode', '-file-line-error', '-halt-on-error',
        f'-jobname={job}', f'-output-directory={PDF_DIR}', f'generated/{lang}.tex',
    ]
    proc = subprocess.run(command, cwd=ROOT / 'tex', capture_output=True, text=True, check=False)
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build' / f'{lang}.log').write_text(proc.stdout + '\n' + proc.stderr, encoding='utf-8')
    if proc.returncode:
        raise RuntimeError(f'XeLaTeX {lang} failed: ' + '\n'.join(proc.stdout.splitlines()[-28:]))
    for line in proc.stdout.splitlines():
        if 'Overfull \\hbox' in line or 'Overfull \\vbox' in line:
            print('TEX WARNING', lang, line, file=sys.stderr)
    return PDF_DIR / f'{job}.pdf'


def pad_before_contacts() -> int:
    """Equalize edition lengths for booklet imposition.

    Padding goes before the stream and contacts pages so those sections remain
    adjacent and at the end of each edition.

    Returns:
        The even number of A5 pages in each resulting edition.
    """
    from pypdf import PdfReader, PdfWriter

    paths = {lang: PDF_DIR / f'{A5_PREFIX}_{lang.upper()}.pdf' for lang in LANGUAGES}
    inputs = {lang: PdfReader(path) for lang, path in paths.items()}
    expected = max(len(reader.pages) for reader in inputs.values())
    expected += expected % 2
    for lang, reader in inputs.items():
        deficit = expected - len(reader.pages)
        if not deficit:
            continue
        writer = PdfWriter()
        for page in reader.pages[:-2]:
            writer.add_page(page)
        last = reader.pages[-1]
        for _ in range(deficit):
            writer.add_blank_page(width=float(last.mediabox.width), height=float(last.mediabox.height))
        for page in reader.pages[-2:]:
            writer.add_page(page)
        with paths[lang].open('wb') as target:
            writer.write(target)
    return expected


def main() -> int:
    """Generate sources, schedules and optionally all print PDFs.

    Returns:
        Zero on success, or one if input validation or a build step fails.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xlsx', type=Path, default=ROOT / 'data' / 'abstracts_review.xlsx')
    parser.add_argument('--skip-pdf', action='store_true')
    args = parser.parse_args()
    try:
        (ROOT / 'build').mkdir(exist_ok=True)
        (ROOT / 'tex' / 'generated').mkdir(parents=True, exist_ok=True)
        lectures, program = generate(args.xlsx)
        (ROOT / 'schedule').mkdir(exist_ok=True)
        for lang in LANGUAGES:
            (ROOT / 'schedule' / f'{SCHEDULE_PREFIX}_{lang}.xml').write_bytes(
                create(program, lectures, lang)
            )
        build_site()
        print(f'V4: {len(lectures)} manually reviewed lectures, {len(program["events"])} programme events')
        if args.skip_pdf:
            return 0
        prepare_qr()
        for lang in LANGUAGES:
            path = compile_tex(lang)
            print('Compiled', path.name, flush=True)
        page_count = pad_before_contacts()
        impose(PDF_DIR, expected_pages=page_count)
        print(f'Completed {page_count} A5 pages per edition, {page_count} A4 PDF sides')
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print('BUILD ERROR:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
