# DevDesk Implementation Plan

## Status Overview

**Current Phase:** Phases 1–6 in progress

**Last Updated:** 2026-11-14

## Phase 1 – Foundation ✅

- Project skeleton, core modules, JSON storage, logging, platform abstraction
- System tray + single-instance guard
- Main window, navigation, dashboard cards, themes
- Settings basics

## Phase 2 – Local Productivity ✅

- Working Time Tracker (check-in/out, breaks, summaries, persistence, live UI)
- Quick Access (CRUD, search, favorites, open via platform)
- Developer Tools (apps + projects launcher)
- Global Search dialog (`Ctrl+K`)
- Notification service (history, dedup, quiet hours, tray messages)

## Phase 3 – Integrations ✅

- `integrations/base.py` – httpx client, retries, rate-limit, auth errors
- Jira Cloud client – search, normalize, overdue/stale helpers, test connection
- GitHub client – review-requested + my open PRs via Search API
- Bitbucket client – workspace PRs, normalize model shared with GitHub
- CredentialManager (keyring) for all tokens
- Settings UI with Test Connection for each integration
- Jira / PR pages populated from cache

## Phase 4 – Dashboard & Automation ✅

- `services/sync.py` – QThreadPool workers, QTimer intervals, manual refresh
- Cache write on successful sync
- UI updates via signals (Jira/PR pages + overview cards)
- Notification hooks for overdue issues and PR review requests
- Tray **Refresh All** wired to `sync_all()`

## Phase 5 – Packaging ✅

- `scripts/build_linux.py` / `scripts/build_windows.py` (PyInstaller)
- README with install/run/config instructions
- Build scripts optimized for release output under `dist/`
- PyInstaller dependency added to requirements for reproducible packaging

## Phase 6 – Documentation & Delivery 🟡

- Add `docs/` structure for usage, architecture, design, and build notes
- Add release-oriented package generation flow for Windows and Linux
- Document installation, config, troubleshooting, and deployment boundaries
- Validate the project with automated tests before release

## Tests

Project baseline should be validated with:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest tests/ -v
```

## How to run

```bash
cd devdesk
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=. python main.py
```

## Known limitations

- Visual system-tray verification needs a real desktop session.
- Bitbucket “PRs to review” is approximated via open PRs in configured workspaces.
- PyInstaller cross-builds are best validated on target OS hosts; Windows generation from Linux requires a Windows-targeting toolchain or a Windows build machine.
