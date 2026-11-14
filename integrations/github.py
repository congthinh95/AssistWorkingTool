"""GitHub REST API client."""

from __future__ import annotations

from typing import Any, Optional

from core.logger import get_logger
from integrations.base import BaseClient, IntegrationError

logger = get_logger("integrations.github")


class GitHubClient(BaseClient):
    """GitHub REST API v3 client."""

    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        super().__init__(
            base_url=base_url,
            token=token,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def _auth_header(self) -> str:
        return f"Bearer {self.token}"

    def test_connection(self) -> dict[str, Any]:
        data = self.get("/user")
        return {
            "login": data.get("login"),
            "name": data.get("name"),
            "id": data.get("id"),
        }

    def get_notifications_prs(self) -> list[dict[str, Any]]:
        """Search PRs where the user is requested as reviewer."""
        # Search issues/PRs involving the authenticated user that need review
        q = "is:pr is:open review-requested:@me"
        data = self.get("/search/issues", params={"q": q, "per_page": 50, "sort": "updated"})
        return data.get("items", []) if isinstance(data, dict) else []

    def get_my_open_prs(self) -> list[dict[str, Any]]:
        q = "is:pr is:open author:@me"
        data = self.get("/search/issues", params={"q": q, "per_page": 50, "sort": "updated"})
        return data.get("items", []) if isinstance(data, dict) else []

    def get_pull_request(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        return self.get(f"/repos/{owner}/{repo}/pulls/{number}")

    def get_pr_reviews(self, owner: str, repo: str, number: int) -> list[dict[str, Any]]:
        data = self.get(f"/repos/{owner}/{repo}/pulls/{number}/reviews")
        return data if isinstance(data, list) else []

    def get_pr_checks(self, owner: str, repo: str, ref: str) -> dict[str, Any]:
        try:
            return self.get(f"/repos/{owner}/{repo}/commits/{ref}/status")
        except IntegrationError:
            return {}

    @staticmethod
    def normalize_pr(raw: dict[str, Any]) -> dict[str, Any]:
        # Search API returns issue-like objects; full PR has more fields
        repo_url = raw.get("repository_url") or ""
        repo_name = ""
        if repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                repo_name = f"{parts[-2]}/{parts[-1]}"
        pull = raw.get("pull_request") or {}
        return {
            "number": raw.get("number"),
            "title": raw.get("title", ""),
            "state": raw.get("state", ""),
            "user": (raw.get("user") or {}).get("login", ""),
            "repository": repo_name or raw.get("repository", {}).get("full_name", ""),
            "html_url": raw.get("html_url") or pull.get("html_url", ""),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at"),
            "draft": raw.get("draft", False),
            "labels": [l.get("name") for l in raw.get("labels", []) if isinstance(l, dict)],
            "source": "github",
            "raw": raw,
        }

    def approve_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
        body: str = "Approved via DevDesk automation",
    ) -> dict[str, Any]:
        """Submit an APPROVE review."""
        return self.request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json={"event": "APPROVE", "body": body},
        )

    def dismiss_review(
        self,
        owner: str,
        repo: str,
        number: int,
        review_id: int,
        message: str = "Dismissed via DevDesk",
    ) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews/{review_id}/dismissals",
            json={"message": message, "event": "DISMISS"},
        )

    def remove_requested_reviewers(
        self,
        owner: str,
        repo: str,
        number: int,
        reviewers: list[str],
    ) -> dict[str, Any]:
        """Remove users from the requested reviewers list."""
        return self.request(
            "DELETE",
            f"/repos/{owner}/{repo}/pulls/{number}/requested_reviewers",
            json={"reviewers": reviewers},
        )

    def get_combined_status(self, owner: str, repo: str, ref: str) -> dict[str, Any]:
        try:
            return self.get(f"/repos/{owner}/{repo}/commits/{ref}/status")
        except IntegrationError:
            return {"state": "unknown"}

    def parse_repo(self, full_name: str) -> tuple[str, str]:
        parts = (full_name or "").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        return "", ""
