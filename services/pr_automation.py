"""PR automation: auto-approve and remove-as-reviewer with dry-run + audit log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger
from core.storage import Storage
from integrations.base import IntegrationError
from integrations.github import GitHubClient

logger = get_logger("pr_automation")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_allowed(repo: str, allowlist: list[str], blocklist: list[str]) -> bool:
    repo_l = (repo or "").lower()
    if blocklist and any(repo_l == b.lower() or repo_l.startswith(b.lower().rstrip("*")) for b in blocklist):
        # simple exact or prefix*
        for b in blocklist:
            b = b.lower()
            if b.endswith("*") and repo_l.startswith(b[:-1]):
                return False
            if repo_l == b:
                return False
    if not allowlist:
        return True
    for a in allowlist:
        a = a.lower()
        if a.endswith("*") and repo_l.startswith(a[:-1]):
            return True
        if repo_l == a:
            return True
    return False


def _title_blocked(title: str, keywords: list[str]) -> bool:
    t = (title or "").upper()
    return any(k.upper() in t for k in keywords if k)


class PRAutomationService:
    """Evaluate rules and optionally call GitHub APIs."""

    def __init__(
        self,
        storage: Storage,
        config: dict[str, Any],
        github_client: Optional[GitHubClient] = None,
        my_login: str = "",
        notifications=None,
    ) -> None:
        self.storage = storage
        self.config = config or {}
        self.client = github_client
        self.my_login = my_login
        self.notifications = notifications

    def rules(self) -> dict[str, Any]:
        return self.config.get("pr_automation") or {}

    def enabled(self) -> bool:
        return bool(self.rules().get("enabled"))

    def dry_run(self) -> bool:
        return bool(self.rules().get("dry_run", True))

    def _log(self, action: str, pr: dict[str, Any], detail: str, success: bool, dry: bool) -> None:
        entry = {
            "ts": _utcnow_iso(),
            "action": action,
            "dry_run": dry,
            "success": success,
            "repo": pr.get("repository"),
            "number": pr.get("number"),
            "title": pr.get("title"),
            "url": pr.get("html_url"),
            "detail": detail,
        }
        self.storage.append_automation_log(entry)
        logger.info(
            "PR automation %s %s %s#%s – %s",
            "[DRY]" if dry else "",
            action,
            pr.get("repository"),
            pr.get("number"),
            detail,
        )

    def _notify(self, title: str, message: str, url: str = "") -> None:
        if not self.notifications:
            return
        self.notifications.notify(
            title,
            message,
            category="pr_automation",
            source_id=f"auto:{title}:{url}",
            url=url,
        )

    def process_github_prs(self, prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run automation against normalized PR list. Returns action results."""
        if not self.enabled() or not self.client:
            return []
        results: list[dict[str, Any]] = []
        for pr in prs:
            if pr.get("source") and pr.get("source") != "github":
                continue
            r = self._maybe_remove_reviewer(pr)
            if r:
                results.append(r)
            r = self._maybe_approve(pr)
            if r:
                results.append(r)
        return results

    def _maybe_approve(self, pr: dict[str, Any]) -> Optional[dict[str, Any]]:
        rules = self.rules().get("approve") or {}
        if not rules.get("enabled"):
            return None

        repo = pr.get("repository") or ""
        title = pr.get("title") or ""
        if not _repo_allowed(repo, rules.get("repo_allowlist") or [], rules.get("repo_blocklist") or []):
            return None
        if rules.get("skip_draft") and pr.get("draft"):
            return None
        if rules.get("skip_own_prs") and self.my_login and pr.get("user", "").lower() == self.my_login.lower():
            return None
        if _title_blocked(title, rules.get("title_exclude") or []):
            return None

        owner, name = (repo.split("/") + ["", ""])[:2]
        if not owner or not name or not pr.get("number"):
            return None

        # Optional checks
        if rules.get("require_checks_pass"):
            try:
                full = self.client.get_pull_request(owner, name, int(pr["number"]))
                head_sha = (full.get("head") or {}).get("sha")
                if head_sha:
                    status = self.client.get_combined_status(owner, name, head_sha)
                    state = (status or {}).get("state")
                    if state not in ("success", "pending", None, "unknown"):
                        # only block on explicit failure
                        if state == "failure":
                            return None
                    if state == "failure":
                        return None
                    # If require pass strictly:
                    if state and state != "success" and state != "pending":
                        pass
                    if rules.get("require_checks_pass") and state not in ("success", None, "unknown"):
                        # pending: skip approve for safety
                        if state != "success":
                            return None
            except IntegrationError as exc:
                logger.debug("Could not verify checks for %s#%s: %s", repo, pr.get("number"), exc)
                return None

        dry = self.dry_run()
        detail = "Matched approve rules"
        if dry:
            self._log("approve", pr, detail + " (dry-run, no API call)", True, True)
            self._notify(
                "DevDesk dry-run: would approve",
                f"{repo}#{pr.get('number')}: {title}",
                pr.get("html_url") or "",
            )
            return {"action": "approve", "dry_run": True, "pr": pr}

        try:
            self.client.approve_pull_request(owner, name, int(pr["number"]))
            self._log("approve", pr, detail, True, False)
            self._notify(
                "DevDesk approved PR",
                f"{repo}#{pr.get('number')}: {title}",
                pr.get("html_url") or "",
            )
            return {"action": "approve", "dry_run": False, "pr": pr}
        except IntegrationError as exc:
            self._log("approve", pr, f"Failed: {exc}", False, False)
            return {"action": "approve", "error": str(exc), "pr": pr}

    def _maybe_remove_reviewer(self, pr: dict[str, Any]) -> Optional[dict[str, Any]]:
        rules = self.rules().get("remove_reviewer") or {}
        if not rules.get("enabled"):
            return None
        if not self.my_login:
            return None

        repo = pr.get("repository") or ""
        title = pr.get("title") or ""
        if not _repo_allowed(repo, rules.get("repo_allowlist") or [], rules.get("repo_blocklist") or []):
            return None

        should = False
        reasons: list[str] = []
        if rules.get("on_draft") and pr.get("draft"):
            should = True
            reasons.append("draft")
        if rules.get("on_title_keywords") and _title_blocked(title, rules.get("on_title_keywords") or []):
            should = True
            reasons.append("title keyword")
        # on_new_commits_after_review needs richer review history – best-effort via cache flag
        if rules.get("on_new_commits_after_review") and pr.get("new_commits_since_review"):
            should = True
            reasons.append("new commits since review")

        if not should:
            return None

        owner, name = (repo.split("/") + ["", ""])[:2]
        if not owner or not name or not pr.get("number"):
            return None

        dry = self.dry_run()
        detail = "Remove me as reviewer: " + ", ".join(reasons)
        if dry:
            self._log("remove_reviewer", pr, detail + " (dry-run)", True, True)
            self._notify(
                "DevDesk dry-run: would remove reviewer",
                f"{repo}#{pr.get('number')}: {title} ({detail})",
                pr.get("html_url") or "",
            )
            return {"action": "remove_reviewer", "dry_run": True, "pr": pr}

        try:
            self.client.remove_requested_reviewers(owner, name, int(pr["number"]), [self.my_login])
            self._log("remove_reviewer", pr, detail, True, False)
            self._notify(
                "DevDesk removed you as reviewer",
                f"{repo}#{pr.get('number')}: {title}",
                pr.get("html_url") or "",
            )
            return {"action": "remove_reviewer", "dry_run": False, "pr": pr}
        except IntegrationError as exc:
            self._log("remove_reviewer", pr, f"Failed: {exc}", False, False)
            return {"action": "remove_reviewer", "error": str(exc), "pr": pr}
