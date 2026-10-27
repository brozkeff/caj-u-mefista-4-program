"""Shared publication names keep every generated form factor in sync.

Keep EVENT_GUID_PREFIX stable: changing it would replace published schedule IDs.
"""

PUBLICATION_NAME = 'Caj_u_Mefista_4'
LANGUAGES = ('cz', 'en')
A5_PREFIX = f'{PUBLICATION_NAME}_A5'
SCHEDULE_PREFIX = f'{PUBLICATION_NAME}_pentabarf'
READER_NAME = f'{A5_PREFIX}_tete_beche_reader.pdf'
DUPLEX_NAME = f'{PUBLICATION_NAME}_A4_imposed_duplex.pdf'
EVENT_GUID_PREFIX = 'caj-u-mefista-4-'
RELEASE_PREFIX = 'caj-u-mefista-4'
REVIEWED_SHEET = 'Přednášky tisk'
