# Posterfolio 1.0 — About Overlay Startup Fix

## Fixed
- Replaced the unsupported `QBitmap.boundingRect()` call used to crop transparent icon padding.
- The Mosaic P icon is now cropped using its alpha channel and remains compatible with PySide6.

## Changed files
- `src/poster_montage_designer/dialogs/about_dialog.py`

## Commit message
`Fix About overlay icon cropping`
