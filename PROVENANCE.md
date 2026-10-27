# Sources and editorial decisions

The bundled workbook contains only the reviewed author and Czech/English abstract columns in `Přednášky tisk`. Its 45 populated cells were checked against the original export; unrelated organizational sheets were removed. The original workbook's SHA-256 is `6277b931fb6cd75f3c49ddd715df027b9d99d2eeb3e7fb08663aa24346dfd1c5`.

`data/program.json` is the editable timetable, based on the supplied Czech HTML snapshot. The snapshot remains in development Git history but is excluded from the current source tree. English titles use the conference's English programme where available and editorial translations otherwise. Some durations are estimates; `duration_minutes` can override them.

On 27 October 2026, the supplied HTML listed Michal Kindernay's audiovisual performance at 14:45 on Saturday 31 October, while the live programme still listed a Sasha Chaitow lecture. The project follows the supplied HTML; Chaitow remains an exhibition artist. Check the live site before printing because the QR codes point there.

The Czech cover introduction was supplied by the organizer; its English translation was prepared editorially. Organizer contact details are included in the generated booklet.
