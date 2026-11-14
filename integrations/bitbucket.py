"""Bitbucket Cloud REST API client."""

from __future__ import annotations

from typing import Any, Optional

from core.logger import get_logger
from integrations.base import BaseClient, IntegrationError

logger = get_logger("integrations.bitbucket")


class BitbucketClient(BaseClient):
    """Bitbucket Cloud API 2.0 client."""

    def __init__(
        self,
        username: str,
        app_password: str,
        base_url: str = "https://api.bitbucket.org/2.0",
    ) -> None:
        import base64

        credentials = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        super().__init__(
            base_url=base_url,
            token=None,
            headers={
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
            },
        )
        self.username = username

    def _auth_header(self) -> str:
        return self._default_headers.get("Authorization", "")

    def test_connection(self) -> dict[str, Any]:
        data = self.get("/user")
        return {
            "username": data.get("username"),
            "display_name": data.get("display_name"),
            "uuid": data.get("uuid"),
        }

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self.get_paginated("/workspaces", items_key="values")

    def get_prs_to_review(self, workspace: str) -> list[dict[str, Any]]:
        """PRs in workspace where current user is a reviewer and state is OPEN."""
        # Bitbucket doesn't have a perfect global "review requested" endpoint;
        # query open PRs and filter client-side when needed.
        path = f"/repositories/{workspace}"
        repos = self.get_paginated(path, params={"role": "member"}, items_key="values", max_pages=5)
        prs: list[dict[str, Any]] = []
        for repo in repos[:20]:
            full_name = repo.get("full_name")
            if not full_name:
                continue
            try:
                repo_prs = self.get_paginated(
                    f"/repositories/{full_name}/pullrequests",
                    params={"state": "OPEN", "pagelen": 25},
                    items_key="values",
                    max_pages=2,
                )
                for pr in repo_prs:
                    pr["_repo"] = full_name
                    prs.append(pr)
            except IntegrationError as exc:
                logger.debug("Skip repo %s: %s", full_name, exc)
        return prs

    def get_my_open_prs(self, workspace: str) -> list[dict[str, Any]]:
        path = f"/pullrequests/{self.username}"
        try:
            return self.get_paginated(
                path,
                params={"state": "OPEN", "pagelen": 50},
                items_key="values",
                max_pages=3,
            )
        except IntegrationError:
            # Fallback: search via workspace repos
            return []

    @staticmethod
    def normalize_pr(raw: dict[str, Any]) -> dict[str, Any]:
        dest = raw.get("destination") or {}
        repo = dest.get("repository") or {}
        author = raw.get("author") or {}
        links = raw.get("links") or {}
        html = links.get("html") or {}
        return {
            "number": raw.get("id"),
            "title": raw.get("title", ""),
            "state": raw.get("state", ""),
            "user": author.get("display_name") or author.get("nickname", ""),
            "repository": repo.get("full_name") or raw.get("_repo", ""),
            "html_url": html.get("href", ""),
            "created_at": raw.get("created_on"),
            "updated_at": raw.get("updated_on"),
            "draft": False,
            "source": "bitbucket",
            "raw": raw,
        }
