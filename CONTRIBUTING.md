# Contributing

## Scope

This repository is a desktop client for ElevenLabs with a strong focus on accessibility, keyboard control, screen-reader compatibility, and Windows packaging.

## Development Setup

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-release.ps1 -Version 1.0.0
```

## Contribution Rules

- Keep pull requests focused.
- Preserve keyboard navigation and screen-reader semantics.
- Do not commit `.env`, `api key.txt`, generated audio files, or build artifacts.
- Prefer list-based views over complex tables when accessibility would otherwise regress.
- Add or update release notes in `CHANGELOG.md` when the user-facing behavior changes.

## Before Opening a Pull Request

- Run `python -m compileall main.py eleven_gui`
- Verify the changed workflow manually
- Confirm no debug output or placeholder text remains
- Update screenshots or documentation if the UI changed materially
