# XLSX import and reviewed text integrity

Read `data/abstracts_review.xlsx` using `scripts/xlsx_reader.py`. Select sheet `Přednášky tisk` and locate the `Autor`, `Zkrácený abstrakt CZ` and `Short abstract EN` columns by header. Ignore other sheets and fields. Require a one-to-one match between worksheet authors and programme lectures; preserve reviewed text and paragraph breaks. `make sources` regenerates Markdown with source provenance without rendering PDFs.
