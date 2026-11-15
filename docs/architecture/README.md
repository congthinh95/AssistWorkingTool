# Architecture Overview

## High-level structure

DevDesk follows a layered desktop architecture:

- `main.py` – application entry point
- `core/` – app lifecycle, configuration, storage, logging, platform abstraction
- `services/` – business services and background workers
- `integrations/` – external API adapters
- `ui/` – Qt-based presentation layer

## Core responsibilities

### Core layer

`core/application.py` defines the main `DevDeskApplication`, a `QApplication` subclass with:

- singleton guard
- platform detection
- storage and config bootstrapping
- service initialization
- refresh events and dashboard updates

`core/storage.py` handles JSON persistence with atomic writes and recovery from backup files.

`core/config.py` provides typed configuration access and dotted-path convenience methods.

### Services layer

The services layer handles cross-cutting capabilities:

- sync service for polling integrations
- notifications for tray and desktop messages
- quick access management
- working time tracking
- PR automation support

### Integrations layer

Adapters in `integrations/` wrap GitHub, Bitbucket, and Jira network calls. Each integration is normalized into a common internal model so the UI does not depend on raw provider-specific payloads.

### UI layer

UI components are separated from business logic. Pages and dialogs render information, while service classes update the model and signal changes to the UI.

## Runtime model

1. App starts.
2. Configuration and storage are initialized.
3. Tray icon and main window are created.
4. Sync service starts background tasks.
5. Data cache updates trigger UI refresh events.
6. Notifications and dashboard cards read from local cache.

## Design constraints

- Local-first storage
- OS keyring for secrets
- Qt event loop for UI responsiveness
- Background service workers for API polling and cache sync
