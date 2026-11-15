# User Guide

## Overview

DevDesk is a desktop productivity assistant for software developers. It launches from the system tray and keeps the main workflow lightweight and local-first.

## Features

### 1. Dashboard overview

The dashboard shows a quick snapshot of:

- Jira issue status
- overdue work
- pull requests requiring review
- personal PRs and tasks

### 2. Jira integration

Configure Jira in Settings:

- base URL
- email / account
- JQL query
- sync frequency

Once enabled, the app can show assigned tasks, stale items, and overdue issues.

### 3. Pull request monitoring

Support for GitHub and Bitbucket allows the app to show:

- PRs awaiting review
- my open PRs
- review requests and stale activity

### 4. Working time tracker

Use the working time page to:

- check in / check out
- take breaks
- track active sessions
- compare with the daily target

### 5. Quick access shortcuts

You can add predefined links, project folders, and tools to make frequent actions faster.

## Typical usage flow

1. Start DevDesk from `run.sh` or `run.bat`.
2. Open Settings and add integration credentials.
3. Trigger a manual refresh or let the sync loop run.
4. Check dashboard cards and notifications.
5. Use Quick Access and Developer Tools for daily tasks.

## Shortcuts

- `Ctrl+K` – global search
- `Ctrl+,` – settings
- `Ctrl+1` ... `Ctrl+5` – main app pages

## Operational notes

- App tokens are managed in OS keyring, not JSON.
- Configuration is stored under OS-specific directories.
- The app minimizes to tray by default.
