"""Tests for PR automation rules (no real API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.storage import Storage
from services.pr_automation import PRAutomationService, _repo_allowed, _title_blocked


def test_repo_allowlist() -> None:
    assert _repo_allowed("org/a", [], []) is True
    assert _repo_allowed("org/a", ["org/a"], []) is True
    assert _repo_allowed("org/b", ["org/a"], []) is False
    assert _repo_allowed("org/api-service", ["org/api-*"], []) is True
    assert _repo_allowed("org/a", [], ["org/a"]) is False


def test_title_blocked() -> None:
    assert _title_blocked("WIP: stuff", ["WIP"]) is True
    assert _title_blocked("Ready", ["WIP"]) is False


def test_dry_run_approve(tmp_path: Path) -> None:
    storage = Storage(base_dir=tmp_path)
    client = MagicMock()
    client.get_pull_request.return_value = {"head": {"sha": "abc"}}
    client.get_combined_status.return_value = {"state": "success"}

    cfg = {
        "pr_automation": {
            "enabled": True,
            "dry_run": True,
            "approve": {
                "enabled": True,
                "require_checks_pass": True,
                "skip_draft": True,
                "skip_own_prs": True,
                "title_exclude": ["WIP"],
                "repo_allowlist": [],
                "repo_blocklist": [],
            },
            "remove_reviewer": {"enabled": False},
        }
    }
    svc = PRAutomationService(storage, cfg, github_client=client, my_login="me")
    pr = {
        "source": "github",
        "repository": "org/repo",
        "number": 1,
        "title": "Fix bug",
        "user": "alice",
        "draft": False,
        "html_url": "https://github.com/org/repo/pull/1",
    }
    results = svc.process_github_prs([pr])
    assert len(results) == 1
    assert results[0]["dry_run"] is True
    client.approve_pull_request.assert_not_called()
    log = storage.load_automation_log()
    assert log["entries"]
    assert log["entries"][-1]["action"] == "approve"
    assert log["entries"][-1]["dry_run"] is True


def test_skip_wip_title(tmp_path: Path) -> None:
    storage = Storage(base_dir=tmp_path)
    client = MagicMock()
    cfg = {
        "pr_automation": {
            "enabled": True,
            "dry_run": False,
            "approve": {
                "enabled": True,
                "require_checks_pass": False,
                "skip_draft": True,
                "skip_own_prs": True,
                "title_exclude": ["WIP"],
                "repo_allowlist": [],
                "repo_blocklist": [],
            },
            "remove_reviewer": {"enabled": False},
        }
    }
    svc = PRAutomationService(storage, cfg, github_client=client, my_login="me")
    pr = {
        "source": "github",
        "repository": "org/repo",
        "number": 2,
        "title": "WIP: not ready",
        "user": "alice",
        "draft": False,
    }
    assert svc.process_github_prs([pr]) == []
    client.approve_pull_request.assert_not_called()


def test_remove_reviewer_draft_dry_run(tmp_path: Path) -> None:
    storage = Storage(base_dir=tmp_path)
    client = MagicMock()
    cfg = {
        "pr_automation": {
            "enabled": True,
            "dry_run": True,
            "approve": {"enabled": False},
            "remove_reviewer": {
                "enabled": True,
                "on_draft": True,
                "on_new_commits_after_review": False,
                "on_title_keywords": [],
                "repo_allowlist": [],
                "repo_blocklist": [],
            },
        }
    }
    svc = PRAutomationService(storage, cfg, github_client=client, my_login="me")
    pr = {
        "source": "github",
        "repository": "org/repo",
        "number": 3,
        "title": "Draft work",
        "draft": True,
        "html_url": "https://example.com",
    }
    results = svc.process_github_prs([pr])
    assert results and results[0]["action"] == "remove_reviewer"
    client.remove_requested_reviewers.assert_not_called()
