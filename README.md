# DevDesk

Lightweight cross-platform desktop productivity assistant for software developers.

Runs in the system tray and provides:

- **Jira** task monitoring (assigned / overdue / stale)
- **GitHub** & **Bitbucket** Pull Request monitoring
- **Working Time** tracker (check-in, breaks, daily target)
- **Quick Access** shortcuts for folders, files, projects, URLs
- **Developer Tools** launcher (apps + projects)
- Local notifications and a daily overview dashboard
- Global search (`Ctrl+K`) over cached data

## Principles

- Native desktop only (PySide6 / Qt Widgets)
- Local-first – no web UI, no embedded browser, no SQL
- Credentials in the system **keyring** only
- Single Python codebase for Windows 10/11 and Linux

## Requirements

- Python 3.11+
- System tray support
- Packages: `PySide6`, `httpx`, `keyring`, `pytest` (dev)

## Quick start

```bash
cd devdesk
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. python main.py
```

Starts minimized to the tray by default. Double-click the tray icon or use the context menu.

### Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Global search |
| `Ctrl+1` … `Ctrl+5` | Dashboard / Jira / PRs / Working Time / Quick Access |
| `Ctrl+,` | Settings |

## Configuration

- **Windows:** `%APPDATA%/DevDesk/`
- **Linux:** `~/.config/devdesk/`

Files: `config.json`, `working_time.json`, `quick_access.json`, `notifications.json`, `cache/`.

API tokens are **never** stored in JSON – only in the OS keyring.

### Integrations

1. Open **Settings**
2. Enable Jira / GitHub / Bitbucket
3. Enter URL / email / token (or PAT / app password)
4. Click **Test Connection**, then **Save All**
5. Use **Refresh All** from the tray or the page buttons

## Development

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

Packaging (requires PyInstaller):

```bash
python scripts/build_linux.py
python scripts/build_windows.py
```

## Project status

See `IMPLEMENTATION_PLAN.md` for phase completion details.

Phases 1–4 are implemented. Phase 5 packaging scripts are present; full installer testing should be done on target desktops.

## License

Proprietary / internal use unless otherwise stated.
