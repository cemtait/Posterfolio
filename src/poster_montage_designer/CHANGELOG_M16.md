# Milestone 16 - IMDb Developer Diagnostics

Files changed:
- src/poster_montage_designer/dialogs/imdb_import_dialog.py
- src/poster_montage_designer/services/imdb_capture.py

Changes:
- Adds a Developer menu to the embedded IMDb import dialog.
- Can dump current page HTML.
- Can dump embedded IMDb JSON / __NEXT_DATA__.
- Can dump all visible links and title-link counts.
- Fixes JavaScript cleanTitle() crash when IMDb supplies object values instead of strings.

Commit message:
Add IMDb import diagnostics
