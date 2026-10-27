# Čaj u Mefista 4 — programme and abstracts

Conference website: **[www.caj-u-mefista.cz](https://www.caj-u-mefista.cz/)**. Organized by ČESKO-SLOVENSKÁ VÝZKUMNÁ SPOLEČNOST - SÍŤ, z. s. (IČ 23462833).

This project generates bilingual booklets, Pentabarf schedules and an [interactive programme website](https://brozkeff.github.io/caj-u-mefista-4-program/). See [CHANGELOG.md](CHANGELOG.md) for release history.

## Sources and rights

- `data/abstracts_review.xlsx`: reviewed author and abstract fields in `Přednášky tisk`; preserve the text as supplied.
- `data/program.json`: authoritative timetable, titles, participants and Pentabarf conference metadata. See [PROVENANCE.md](PROVENANCE.md) for sources and a known website discrepancy.
- `data/booklet.json`: bilingual cover, programme headings, column split and contact details.
- `data/stream.json`: bilingual stream text and channel URL.
- `scripts/config.py`: shared output names and language codes. Preserve the event GUID prefix to keep published event IDs stable.
- `assets/`: supplied logos and programme QR codes, plus the stream QR code. If `data/stream.json` changes, regenerate `assets/stream-qr.svg` with `qrencode -t SVG` using the updated URL. Generated outputs are ignored by Git.

Project-authored code, build scripts, website implementation, configuration, tests and documentation are licensed under [EUPL-1.2](LICENSE), unless stated otherwise. Copyright belongs to their respective contributors.

Conference content and third-party materials are **not** licensed under the EUPL by this notice. These include abstracts and translations, programme text and data, participant names, logos, artwork, QR assets and the archived website snapshot. Rights remain with their respective holders; obtain any permission needed for reuse. The organizer named above is not necessarily the owner of every contribution. Third-party software and assets retain their own licenses.

## Build

On Debian or Ubuntu:

```bash
sudo apt install python3 python3-venv nodejs texlive-xetex texlive-latex-extra \
  texlive-lang-czechslovak fonts-noto-core fonts-noto-extra \
  fonts-liberation poppler-utils inkscape zbar-tools
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make build PYTHON=.venv/bin/python
make verify PYTHON=.venv/bin/python
make test PYTHON=.venv/bin/python
```

Alternatively run `uv sync` and use `PYTHON='uv run python'`. Run `make build` before `make test`; the permanent tests check XML well-formedness and schedule structure, while regression checks compare generated publication text and schedules against the reviewed v4.0.4 baseline; update the fixture deliberately when the published content changes. The four PDFs go to `build/pdf/`; the preserved cloud-rendered files in `pdf/` are never overwritten. `make sources` skips PDF rendering; `make xml` regenerates schedules and the website. Before release, follow [QA.md](QA.md); a physical short-edge-duplex proof is optional.

## Update the programme

Edit the timetable in `data/program.json`; change both language titles when appropriate and retain published event IDs. Add a lecture only when the reviewed workbook has a matching author and abstracts. The workbook reader selects columns by header and ignores unrelated fields. Untimed exhibitions appear in an XML extension and on the website; Pentabarf apps may ignore them. Some durations are estimates; set `duration_minutes` to override them.

## Website

The generated static site is in `build/site/`. Upload the entire directory to an HTTPS server, or serve it locally over HTTP; `file:` URLs cannot reliably fetch the XML. The site displays Prague times. Giggity can load the published XML; the Skedz link passes the selected language and `Europe/Prague`. [Skedz](https://github.com/ysorge/skedz) is a third-party web app under GNU AGPL-3.0. The XML host must allow cross-origin requests from `https://app.skedz.org`.

To regenerate the site and preview it locally, run `python3 scripts/preview.py` and open `http://127.0.0.1:8765/`; use `--port` to choose another port. Stop the server with Ctrl+C. The public Skedz import must be tested after deployment because the local server is not a public XML host.

For GitHub Pages, push `production` and select **Settings → Pages → Build and deployment → Source → GitHub Actions**. The workflow builds and deploys the site on pushes to that branch and on manual runs from it. Check both language views and Skedz links after deployment.

Never push `master` or its history. Run `git config --local core.hooksPath .githooks` once per clone to enable the push safeguard. It rejects refs whose history overlaps `master`; Git hooks can be bypassed and are not a remote access control.

## Release assets

Prepare a clean `production` commit and an annotated tag on that exact commit; check out the tag. Run:

```bash
python3 scripts/release.py v4.0.0
```

The helper checks the clean checkout and tag, rebuilds, verifies and runs the regression tests, then creates a ZIP and SHA-256 file in `build/release/`. The ZIP contains the four PDFs, website and XML, logos, programme and stream QR SVGs, README, license and source commit identifier. Inspect them and complete [QA.md](QA.md). Once the tag is pushed and a GitHub release exists, run `python3 scripts/release.py v4.0.0 --upload` to upload both files with `gh`; existing assets are not overwritten.

For a later release, update a clean `production` checkout with the desired snapshot from `master` using `git diff --binary production master | git apply --index`, review the staged changes and make one commit. Tag that production commit; a tag on the development commit does not identify the squashed commit. Review and push deliberately; the helper does not create tags, branches or releases.
