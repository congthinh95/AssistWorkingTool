# DevDesk

Lightweight cross-platform desktop productivity assistant for software developers.

DevDesk runs in the system tray and helps track:

- Jira issues and overdue work
- GitHub and Bitbucket pull requests
- Working time / daily focus sessions
- Quick-access folders, projects, URLs, and apps
- Global search and dashboard insights

## Project principles

- Native desktop only (PySide6 / Qt Widgets)
- Local-first, no web UI or embedded browser
- Credentials stored in OS keyring only
- Single Python codebase for Windows 10/11 and Linux

## Repository structure

- `core/` – config, storage, logger, platform abstraction, app bootstrap
- `services/` – sync, notifications, quick access, working time, PR automation
- `integrations/` – GitHub, Bitbucket, Jira clients
- `ui/` – tray, windows, pages, dialogs, styling
- `scripts/` – build and packaging automation
- `docs/` – usage guide, architecture, design docs, packaging notes
- `tests/` – regression and feature tests

## Requirements

- Python 3.11+
- System tray support on desktop OS
- Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run locally

### Linux / macOS

```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
python main.py
```

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
set PYTHONPATH=%CD%
python main.py
```

Or use the repo launcher:

```bash
./run.sh
```

```bat
run.bat
```

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Global search |
| `Ctrl+1` … `Ctrl+5` | Dashboard / Jira / PRs / Working Time / Quick Access |
| `Ctrl+,` | Settings |

## Configuration

- Windows config directory: `%APPDATA%/DevDesk/`
- Linux config directory: `~/.config/devdesk/`

Files stored locally include:

- `config.json`
- `working_time.json`
- `quick_access.json`
- `notifications.json`
- `cache/`
- `logs/`

API tokens are never stored in JSON; they are managed via the system keyring.

## Integrations

1. Open Settings.
2. Enable Jira, GitHub, and/or Bitbucket.
3. Enter URLs, account information, and access tokens.
4. Click Test Connection and Save All.
5. Trigger Refresh All from the tray or UI.

## Development

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

## Packaging and distribution

Build the app package for the current OS:

```bash
python scripts/build_linux.py
```

```powershell
python scripts\build_windows.py
```

The build scripts generate distributable PyInstaller bundles under the project `dist/` folder. These scripts are the basis for release packaging and can be expanded with signing, installer generation, or artifact publishing.

## Documentation

The repo now includes a dedicated docs structure:

- `docs/user-guide/` – feature usage and daily operations
- `docs/architecture/` – service and module architecture
- `docs/design/` – UI and data design notes
- `docs/build/` – packaging and release guidance

See `docs/README.md` for the index.

## Project status

See `IMPLEMENTATION_PLAN.md` for the current phase tracker and delivery roadmap.

## License

Proprietary / internal use unless otherwise stated.
