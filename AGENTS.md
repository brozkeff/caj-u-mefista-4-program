# Project instructions

- Develop on `master`; promote reviewed changes to `production` as a squash. Never push `master` or its history to any remote. Install the local push safeguard with `git config --local core.hooksPath .githooks`.
- When changing the Node.js runtime used by GitHub Actions, bump the project version and update `CHANGELOG.md` in the same commit.
- Use `data/abstracts_review.xlsx`, sheet `Přednášky tisk`, and the three named author/Czech/English abstract columns as the only source of abstract text. Preserve text and paragraph boundaries; do not shorten or translate it automatically.
- `data/program.json` is the authoritative timetable. Do not silently sync the website; see `PROVENANCE.md` for the known 31 October discrepancy. Only authors in the reviewed sheet can have lecture abstracts. Keep 14 lectures unless both sources deliberately change.
- Generate `content/`, `tex/generated/` and `schedule/` with `make build`; edit `scripts/generate.py` or `tex/layout.tex`, not generated files. Propagate programme changes to all outputs and keep published Pentabarf IDs stable.
- Preserve Unicode, the one-page A5 programme and QR for each language. Escape user text in TeX, keep headings with their opening text, and do not force page breaks between lectures. Keep contact URLs visible.
- Run `make build`, `make verify` and `make test` before release; automated checks cover page layout regressions, imposition and decoding of the rendered QR codes. See `QA.md`. A physical print proof is optional.
- Project guidance for workbook import, typesetting and Pentabarf is in `skills/`.
