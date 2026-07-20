# Posterfolio Milestone 15 — IMDb Page Import

## Files changed

- `src/poster_montage_designer/windows/main_window.py`

## New files

- `src/poster_montage_designer/dialogs/imdb_import_dialog.py`
- `src/poster_montage_designer/services/imdb_capture.py`

## Changes

- Adds **File → Import from IMDb Page...**
- Opens an embedded IMDb browser at imdb.com.
- Enables **Import Credits** only on IMDb person pages.
- Captures credits directly from the loaded IMDb page using bookmarklet-style DOM extraction.
- Starts a fresh montage from the captured credits and loads posters automatically.
- Keeps **Import from IMDb File...** as the fallback/offline workflow.

## Commit message

Add embedded IMDb page import
