"""Secure credential storage using the system keyring."""

from __future__ import annotations

from typing import Optional

from .logger import get_logger

logger = get_logger("credentials")

SERVICE_NAME = "DevDesk"

# Well-known keys
JIRA_TOKEN = "jira_api_token"
GITHUB_TOKEN_PREFIX = "github_pat_"
BITBUCKET_TOKEN = "bitbucket_token"


class CredentialManager:
    """Thin wrapper around keyring. Never falls back to plaintext storage."""

    def __init__(self) -> None:
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import keyring

                # Probe the backend
                keyring.get_keyring()
                self._available = True
            except Exception as exc:
                logger.warning("keyring is unavailable: %s", exc)
                self._available = False
        return self._available

    def set(self, key: str, value: str) -> bool:
        """Store a secret. Returns True on success."""
        if not self.available:
            logger.error("Cannot store credential – keyring unavailable")
            return False
        try:
            import keyring

            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except Exception as exc:
            logger.error("Failed to store credential %s: %s", key, exc)
            return False

    def get(self, key: str) -> Optional[str]:
        """Retrieve a secret. Returns None if missing or keyring unavailable."""
        if not self.available:
            return None
        try:
            import keyring

            return keyring.get_password(SERVICE_NAME, key)
        except Exception as exc:
            logger.error("Failed to read credential %s: %s", key, exc)
            return None

    def delete(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            import keyring

            keyring.delete_password(SERVICE_NAME, key)
            return True
        except Exception as exc:
            # keyring raises PasswordDeleteError when the key does not exist
            logger.debug("Delete credential %s: %s", key, exc)
            return False

    # Convenience helpers -------------------------------------------------

    def set_jira_token(self, token: str) -> bool:
        return self.set(JIRA_TOKEN, token)

    def get_jira_token(self) -> Optional[str]:
        return self.get(JIRA_TOKEN)

    def set_github_token(self, account: str, token: str) -> bool:
        return self.set(f"{GITHUB_TOKEN_PREFIX}{account}", token)

    def get_github_token(self, account: str) -> Optional[str]:
        return self.get(f"{GITHUB_TOKEN_PREFIX}{account}")

    def set_bitbucket_token(self, token: str) -> bool:
        return self.set(BITBUCKET_TOKEN, token)

    def get_bitbucket_token(self) -> Optional[str]:
        return self.get(BITBUCKET_TOKEN)
