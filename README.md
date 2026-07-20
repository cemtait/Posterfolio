# Poster Montage Designer

Day 1 milestone: use a real browser to open an IMDb person page, click/expand the visible filmography sections, and extract title links.

## Setup in VS Code / PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## Test IMDb title extraction

```powershell
python -m poster_montage_designer scrape-imdb "https://www.imdb.com/name/nm0846880/" --out projects/charles_tait_titles.json
```

Then view the resulting JSON in `projects/charles_tait_titles.json`.

## Notes

This version is deliberately focused on one task: proving that a rendered IMDb page can provide the full visible credit/title list. Posters and montage rendering come after this is solid.
