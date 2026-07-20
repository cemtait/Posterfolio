# Contributing to Posterfolio

Thank you for your interest in Posterfolio.

## Reporting a bug

Please use the GitHub bug-report template and include:

- the Posterfolio version or commit;
- operating system and version;
- steps that reliably reproduce the problem;
- what you expected to happen;
- what actually happened;
- relevant screenshots or terminal output.

Do not include your TMDb API Read Access Token in an issue, screenshot, log, or project file.

## Suggesting a feature

Use the feature-request template and describe:

- the problem or workflow the feature would improve;
- the proposed behaviour;
- why it would be useful to more than one user;
- any alternative approach you considered.

## Development setup

Posterfolio currently targets Python 3.13.

```powershell
git clone https://github.com/cemtait/Posterfolio.git
cd Posterfolio

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python -m playwright install chromium
python -m poster_montage_designer
```

On macOS, create and activate the virtual environment with `python3.13` and `source .venv/bin/activate`.

## Pull requests

Keep pull requests focused on one change. Before submitting:

1. Confirm that Posterfolio launches.
2. Test the changed workflow manually.
3. Do not commit local settings, cached poster files, exports, projects, build output, or virtual environments.
4. Update the changelog when the change affects users.
5. Explain what changed and how it was tested.

## Code style

- Prefer clear, readable Python over clever shortcuts.
- Preserve the existing PySide6 architecture and naming conventions.
- Keep UI changes visually consistent with the application.
- Add comments only where they explain non-obvious intent.
- Avoid unrelated formatting changes in focused fixes.

## Secrets

`config/settings.json` contains local user settings and may contain a TMDb token. It is ignored by Git and must remain untracked.

Use `config/settings.example.json` for safe example configuration.
