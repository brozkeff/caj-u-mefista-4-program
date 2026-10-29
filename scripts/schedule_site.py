"""Assemble the website from canonical exports so previews and deployment agree."""
import json
from pathlib import Path
import shutil

from config import LANGUAGES, SCHEDULE_PREFIX

ROOT = Path(__file__).resolve().parents[1]


def build_site() -> None:
    """Copy website assets and the generated schedules into build/site."""
    output = ROOT / 'build' / 'site'
    output.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'style.css', 'schedule.js'):
        shutil.copy2(ROOT / 'website' / name, output / name)
    streams = json.loads((ROOT / 'data' / 'streams.json').read_text(encoding='utf-8'))
    (output / 'streams.js').write_text('const streams = ' + json.dumps(streams, ensure_ascii=False) + ';\n', encoding='utf-8')
    for lang in LANGUAGES:
        shutil.copy2(ROOT / 'assets' / f'logo-{lang}.jpg', output / f'logo-{lang}.jpg')
        shutil.copy2(ROOT / 'schedule' / f'{SCHEDULE_PREFIX}_{lang}.xml',
                     output / f'schedule-{lang}.xml')
