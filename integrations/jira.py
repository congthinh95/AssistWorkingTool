"""Jira Cloud REST API client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger
from integrations.base import AuthError, BaseClient, IntegrationError

logger = get_logger("integrations.jira")


class JiraClient(BaseClient):
    """Jira Cloud API v3 client."""

    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        # Basic auth: email:token
        import base64

        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        super().__init__(
            base_url=base_url.rstrip("/"),
            token=None,
            headers={
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        self.email = email

    def _auth_header(self) -> str:
        return self._default_headers.get("Authorization", "")

    def test_connection(self) -> dict[str, Any]:
        """Verify credentials by fetching current user."""
        data = self.get("/rest/api/3/myself")
        return {
            "account_id": data.get("accountId"),
            "display_name": data.get("displayName"),
            "email": data.get("emailAddress"),
        }

    def search_issues(
        self,
        jql: str,
        fields: Optional[list[str]] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        fields = fields or [
            "summary",
            "status",
            "priority",
            "assignee",
            "issuetype",
            "project",
            "duedate",
            "updated",
            "created",
        ]
        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "maxResults": max_results,
            "startAt": start_at,
        }
        return self.get("/rest/api/3/search", params=params)

    def search_all_issues(self, jql: str, max_total: int = 200) -> list[dict[str, Any]]:
        """Paginate through search results."""
        issues: list[dict[str, Any]] = []
        start = 0
        page_size = 50
        while start < max_total:
            data = self.search_issues(jql, max_results=page_size, start_at=start)
            batch = data.get("issues", [])
            issues.extend(batch)
            total = data.get("total", 0)
            start += len(batch)
            if start >= total or not batch:
                break
        return issues[:max_total]

    def get_my_issues(self, jql: Optional[str] = None) -> list[dict[str, Any]]:
        jql = jql or "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
        return self.search_all_issues(jql)

    @staticmethod
    def normalize_issue(raw: dict[str, Any]) -> dict[str, Any]:
        fields = raw.get("fields") or {}
        status = (fields.get("status") or {}).get("name", "")
        priority = (fields.get("priority") or {}).get("name", "")
        assignee = fields.get("assignee") or {}
        project = fields.get("project") or {}
        issuetype = fields.get("issuetype") or {}
        due = fields.get("duedate")
        updated = fields.get("updated")
        return {
            "key": raw.get("key", ""),
            "id": raw.get("id", ""),
            "summary": fields.get("summary", ""),
            "status": status,
            "priority": priority,
            "assignee": assignee.get("displayName") or assignee.get("emailAddress") or "",
            "project": project.get("key") or project.get("name") or "",
            "issuetype": issuetype.get("name", ""),
            "due_date": due,
            "updated": updated,
            "url": None,  # filled by caller with base_url
            "raw": raw,
        }

    @staticmethod
    def is_overdue(issue: dict[str, Any]) -> bool:
        due = issue.get("due_date")
        if not due:
            return False
        try:
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            return due_dt.date() < datetime.now(timezone.utc).date()
        except Exception:
            return False

    @staticmethod
    def is_stale(issue: dict[str, Any], days: int = 7) -> bool:
        updated = issue.get("updated")
        if not updated:
            return False
        try:
            upd = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if upd.tzinfo is None:
                upd = upd.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - upd).days >= days
        except Exception:
            return False
