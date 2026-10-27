"""Build release assets from a checked-out tag; optionally upload to GitHub."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, capture: bool = False) -> str:
    result = subprocess.run(command, cwd=ROOT, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', help='Existing release tag, for example v4.0.0')
    parser.add_argument('--upload', action='store_true', help='Upload to an existing GitHub release')
    args = parser.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', args.tag):
        parser.error('tag must be a version such as v4.0.0')
    if run('git', 'status', '--porcelain', '--untracked-files=normal', capture=True):
        raise RuntimeError('working tree must be clean before building release assets')
    commit = run('git', 'rev-parse', 'HEAD', capture=True)
    tagged = run('git', 'rev-parse', '--verify', f'refs/tags/{args.tag}^{{commit}}', capture=True)
    if commit != tagged:
        raise RuntimeError('check out the exact tagged commit before building')
    if args.upload:
        remote = run('git', 'ls-remote', '--exit-code', 'origin', f'refs/tags/{args.tag}',
                     f'refs/tags/{args.tag}^{{}}', capture=True).splitlines()
        refs = dict(line.split('\t', 1)[::-1] for line in remote)
        remote_commit = refs.get(f'refs/tags/{args.tag}^{{}}', refs.get(f'refs/tags/{args.tag}'))
        if remote_commit != commit:
            raise RuntimeError('origin tag does not resolve to the checked-out commit')
    run('make', 'build', f'PYTHON={sys.executable}')
    run('make', 'verify', f'PYTHON={sys.executable}')
    output = ROOT / 'build' / 'release'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'caj-u-mefista-4-{args.tag}.zip'
    files = [*sorted((ROOT / 'build' / 'pdf').glob('*.pdf')),
             *(ROOT / 'build' / 'site' / name for name in
               ('index.html', 'style.css', 'schedule.js', 'logo-cz.jpg', 'schedule-cz.xml', 'schedule-en.xml')),
             *(ROOT / 'assets' / name for name in
               ('logo-cz.jpg', 'logo-en.jpg', 'program-qr-cz.svg', 'program-qr-en.svg', 'stream-qr.svg')),
             ROOT / 'README.md', ROOT / 'LICENSE']
    expected = {'Caj_u_Mefista_4_A5_CZ.pdf', 'Caj_u_Mefista_4_A5_EN.pdf',
                'Caj_u_Mefista_4_A5_tete_beche_reader.pdf', 'Caj_u_Mefista_4_A4_imposed_duplex.pdf'}
    pdfs = {p.name for p in files if p.parent == ROOT / 'build' / 'pdf'}
    if pdfs != expected:
        raise RuntimeError(f'expected exactly the four release PDFs; found {sorted(pdfs)}')
    with ZipFile(archive, 'w', ZIP_DEFLATED) as bundle:
        for path in files:
            if path.parent == ROOT / 'build' / 'pdf':
                name = Path('pdf') / path.name
            elif path.parent == ROOT / 'build' / 'site':
                name = Path('site') / path.name
            else:
                name = path.relative_to(ROOT)
            bundle.write(path, name.as_posix())
        bundle.writestr('SOURCE-COMMIT.txt', f'{args.tag}\n{commit}\n')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = output / f'{archive.name}.sha256'
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(f'Created {archive} and {checksum}', flush=True)
    if args.upload:
        run('gh', 'release', 'upload', args.tag, str(archive), str(checksum))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Release error: {error}', file=sys.stderr)
        sys.exit(1)
