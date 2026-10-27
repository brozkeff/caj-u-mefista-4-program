"""Assemble the static schedule website from the current XML exports."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def build_site() -> None:
    """Copy website assets and the generated schedules into build/site."""
    output = ROOT / 'build' / 'site'
    output.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'style.css', 'schedule.js'):
        shutil.copy2(ROOT / 'website' / name, output / name)
    shutil.copy2(ROOT / 'assets' / 'logo-cz.jpg', output / 'logo-cz.jpg')
    for lang in ('cz', 'en'):
        shutil.copy2(ROOT / 'schedule' / f'Caj_u_Mefista_4_pentabarf_{lang}.xml',
                     output / f'schedule-{lang}.xml')
