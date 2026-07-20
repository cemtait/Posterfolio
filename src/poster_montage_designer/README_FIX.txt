Posterfolio 1.0.1 clean interaction fix

Copy the 'src' folder over the existing project 'src' folder.

Fixes:
- Bench hover visual removed at delegate level as well as stylesheet level.
- Delete/Backspace and context-menu deletion resolve Bench selections by IMDb ID.
- Bench grid uses static, uniform positions and performs a clean layout after rebuild.
- Removed delayed layout calls that caused API errors and could preserve stale gaps.
- Existing multi-select, drag-to-promote, drag-to-replace and airiness fixes are retained.
