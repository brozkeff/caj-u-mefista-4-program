"""Package a verified, tagged checkout so release assets identify their source."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from config import A5_PREFIX, DUPLEX_NAME, LANGUAGES, READER_NAME, RELEASE_PREFIX

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, capture: bool = False) -> str:
    """Run a command from the project root, optionally capturing its output.

    Args:
        *command: Program and arguments to execute without a shell.
        capture: Whether to capture standard output.

    Returns:
        Stripped standard output when captured, otherwise an empty string.
    """
    result = subprocess.run(command, cwd=ROOT, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ''


def checked_commit(tag: str, upload: bool) -> str:
    """Verify that release assets come from the clean, exact tagged commit.

    Args:
        tag: Existing release tag.
        upload: Also require the origin tag to resolve to the checked-out commit.

    Returns:
        The checked-out commit ID.

    Raises:
        RuntimeError: If the checkout is dirty or either required tag differs.
    """
    if run('git', 'status', '--porcelain', '--untracked-files=normal', capture=True):
        raise RuntimeError('working tree must be clean before building release assets')
    commit = run('git', 'rev-parse', 'HEAD', capture=True)
    tagged = run('git', 'rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}', capture=True)
    if commit != tagged:
        raise RuntimeError('check out the exact tagged commit before building')
    if upload:
        remote = run('git', 'ls-remote', '--exit-code', 'origin', f'refs/tags/{tag}',
                     f'refs/tags/{tag}^{{}}', capture=True).splitlines()
        refs = dict(line.split('\t', 1)[::-1] for line in remote)
        remote_commit = refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}'))
        if remote_commit != commit:
            raise RuntimeError('origin tag does not resolve to the checked-out commit')
    return commit


def package(tag: str, commit: str) -> tuple[Path, Path]:
    """Create the release archive and its SHA-256 checksum.

    Args:
        tag: Version tag used for the archive name and source identifier.
        commit: Commit ID recorded inside the archive.

    Returns:
        Paths to the ZIP archive and its checksum file.

    Raises:
        RuntimeError: If the expected four PDFs are missing or extra PDFs exist.
        OSError: If a release file cannot be read or written.
    """
    output = ROOT / 'build' / 'release'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'{RELEASE_PREFIX}-{tag}.zip'
    pdf_dir = ROOT / 'build' / 'pdf'
    site_dir = ROOT / 'build' / 'site'
    pdfs = sorted(pdf_dir.glob('*.pdf'))
    expected = {*(f'{A5_PREFIX}_{lang.upper()}.pdf' for lang in LANGUAGES), READER_NAME, DUPLEX_NAME}
    if {p.name for p in pdfs} != expected:
        raise RuntimeError(f'expected exactly the four release PDFs; found {sorted(p.name for p in pdfs)}')
    site_files = ('index.html', 'style.css', 'schedule.js', 'logo-cz.jpg', 'logo-en.jpg',
                  'schedule-cz.xml', 'schedule-en.xml')
    asset_files = ('logo-cz.jpg', 'logo-en.jpg', 'program-qr-cz.svg', 'program-qr-en.svg', 'stream-qr.svg')
    with ZipFile(archive, 'w', ZIP_DEFLATED) as bundle:
        for path in pdfs:
            bundle.write(path, (Path('pdf') / path.name).as_posix())
        for name in site_files:
            bundle.write(site_dir / name, (Path('site') / name).as_posix())
        for name in asset_files:
            bundle.write(ROOT / 'assets' / name, (Path('assets') / name).as_posix())
        for name in ('README.md', 'LICENSE'):
            bundle.write(ROOT / name, name)
        bundle.writestr('SOURCE-COMMIT.txt', f'{tag}\n{commit}\n')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = output / f'{archive.name}.sha256'
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return archive, checksum


def main() -> None:
    """Build, verify and package a tag, uploading when requested on the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag', help='Existing release tag, for example v4.0.0')
    parser.add_argument('--upload', action='store_true', help='Upload to an existing GitHub release')
    args = parser.parse_args()
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', args.tag):
        parser.error('tag must be a version such as v4.0.0')
    commit = checked_commit(args.tag, args.upload)
    run('make', 'build', f'PYTHON={sys.executable}')
    run('make', 'verify', f'PYTHON={sys.executable}')
    run('make', 'test', f'PYTHON={sys.executable}')
    archive, checksum = package(args.tag, commit)
    print(f'Created {archive} and {checksum}', flush=True)
    if args.upload:
        run('gh', 'release', 'upload', args.tag, str(archive), str(checksum))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Release error: {error}', file=sys.stderr)
        sys.exit(1)
