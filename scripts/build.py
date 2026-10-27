"""Single entry point for V4 reviewed XLSX → sources → XeLaTeX → PDFs/XML."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from generate import ROOT, generate
from pentabarf import create
from impose import impose
from schedule_site import build_site

PDF_DIR = ROOT / 'build' / 'pdf'


def prepare_qr() -> None:
    """Convert the supplied vector QR assets without modifying the originals."""
    if shutil.which('inkscape') is None:
        raise RuntimeError('inkscape missing; install it to convert the SVG QR codes')
    qr_dir = ROOT / 'build' / 'qr'
    qr_dir.mkdir(parents=True, exist_ok=True)
    for lang in ('cz', 'en'):
        subprocess.run(['inkscape', str(ROOT / 'assets' / f'program-qr-{lang}.svg'),
                        '--export-type=pdf', f'--export-filename={qr_dir / f"program-qr-{lang}.pdf"}'],
                       check=True, capture_output=True, text=True)


def compile_tex(lang:str)->Path:
    """Compile A5 XeLaTeX once; fail on any fatal TeX error.

    Args:
        lang: `cz` or `en`.

    Returns:
        Path to generated A5 PDF.
    """
    if shutil.which('xelatex') is None:
        raise RuntimeError('xelatex missing; install texlive-xetex and fonts-noto-core')
    out=PDF_DIR;out.mkdir(parents=True, exist_ok=True)
    job=f'Caj_u_Mefista_4_A5_{lang.upper()}'
    command=['xelatex','-interaction=nonstopmode','-file-line-error','-halt-on-error',f'-jobname={job}',f'-output-directory={out}',f'generated/{lang}.tex']
    proc=subprocess.run(command,cwd=ROOT/'tex',capture_output=True,text=True,check=False)
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build'/f'{lang}.log').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
    if proc.returncode:
        raise RuntimeError(f'XeLaTeX {lang} failed: '+ '\n'.join(proc.stdout.splitlines()[-28:]))
    for line in proc.stdout.splitlines():
        if 'Overfull \\hbox' in line or 'Overfull \\vbox' in line:
            print('TEX WARNING',lang,line,file=sys.stderr)
    return out/f'{job}.pdf'


def pad_before_contacts() -> int:
    """Match edition lengths while preserving contacts on each final page.

    Returns:
        Equalized number of A5 pages, guaranteed even for reversal/imposition.
    """
    from pypdf import PdfReader,PdfWriter
    paths={x:PDF_DIR/f'Caj_u_Mefista_4_A5_{x.upper()}.pdf' for x in ('cz','en')}
    inputs={x:PdfReader(p) for x,p in paths.items()}
    expected=max(len(r.pages) for r in inputs.values())
    expected += expected % 2
    for lang,reader in inputs.items():
        deficit=expected-len(reader.pages)
        if deficit:
            w=PdfWriter()
            for page in list(reader.pages)[:-1]:w.add_page(page)
            last=reader.pages[-1]
            for _ in range(deficit):w.add_blank_page(width=float(last.mediabox.width),height=float(last.mediabox.height))
            w.add_page(last)
            with paths[lang].open('wb') as target:w.write(target)
    return expected


def main()->int:
    """Validate source data, regenerate editable artifacts, export PDFs and XML."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xlsx',type=Path,default=ROOT/'data'/'abstracts_review.xlsx')
    parser.add_argument('--skip-pdf',action='store_true')
    args=parser.parse_args()
    try:
        (ROOT/'build').mkdir(exist_ok=True)
        (ROOT/'tex'/'generated').mkdir(parents=True, exist_ok=True)
        lectures,program=generate(args.xlsx)
        (ROOT/'schedule').mkdir(exist_ok=True)
        for lang in ('cz','en'):
            (ROOT/'schedule'/f'Caj_u_Mefista_4_pentabarf_{lang}.xml').write_bytes(create(program,lectures,lang))
        build_site()
        print(f'V4: {len(lectures)} manually reviewed lectures, {len(program["events"])} programme events')
        if args.skip_pdf:return 0
        prepare_qr()
        for lang in ('cz','en'):
            path=compile_tex(lang)
            print('Compiled',path.name,flush=True)
        page_count=pad_before_contacts()
        impose(PDF_DIR,expected_pages=page_count)
        print(f'Completed {page_count} A5 pages per edition, {page_count} A4 PDF sides')
        return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.CalledProcessError) as exc:
        print('BUILD ERROR:',exc,file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
