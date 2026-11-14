"""Integration client tests with mocked HTTP."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from integrations.jira import JiraClient
from integrations.github import GitHubClient
from integrations.bitbucket import BitbucketClient
from integrations.base import IntegrationError, AuthError


def test_jira_normalize_issue() -> None:
    raw = {
        "key": "PROJ-1",
        "id": "10001",
        "fields": {
            "summary": "Fix bug",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assignee": {"displayName": "Alice"},
            "project": {"key": "PROJ"},
            "issuetype": {"name": "Bug"},
            "duedate": "2020-01-01",
            "updated": "2026-11-01T10:00:00.000+0000",
        },
    }
    norm = JiraClient.normalize_issue(raw)
    assert norm["key"] == "PROJ-1"
    assert norm["summary"] == "Fix bug"
    assert norm["status"] == "In Progress"
    assert JiraClient.is_overdue(norm) is True


def test_github_normalize_pr() -> None:
    raw = {
        "number": 42,
        "title": "Add feature",
        "state": "open",
        "user": {"login": "bob"},
        "html_url": "https://github.com/org/repo/pull/42",
        "repository_url": "https://api.github.com/repos/org/repo",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "labels": [],
    }
    norm = GitHubClient.normalize_pr(raw)
    assert norm["number"] == 42
    assert norm["repository"] == "org/repo"
    assert norm["source"] == "github"


def test_bitbucket_normalize_pr() -> None:
    raw = {
        "id": 7,
        "title": "BB PR",
        "state": "OPEN",
        "author": {"display_name": "Carol"},
        "destination": {"repository": {"full_name": "ws/repo"}},
        "links": {"html": {"href": "https://bitbucket.org/ws/repo/pull-requests/7"}},
        "created_on": "2026-01-01T00:00:00Z",
        "updated_on": "2026-01-02T00:00:00Z",
    }
    norm = BitbucketClient.normalize_pr(raw)
    assert norm["number"] == 7
    assert norm["repository"] == "ws/repo"
    assert norm["source"] == "bitbucket"


@patch("integrations.base.httpx.Client")
def test_jira_test_connection_auth_error(mock_client_cls) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_client = MagicMock()
    mock_client.request.return_value = mock_resp
    mock_client.is_closed = False
    mock_client_cls.return_value = mock_client

    client = JiraClient("https://example.atlassian.net", "a@b.com", "bad-token")
    with pytest.raises(AuthError):
        client.test_connection()
    client.close()


def test_stale_detection() -> None:
    issue = {"updated": "2020-01-01T00:00:00+00:00"}
    assert JiraClient.is_stale(issue, days=7) is True
    issue2 = {"updated": "2099-01-01T00:00:00+00:00"}
    assert JiraClient.is_stale(issue2, days=7) is False
