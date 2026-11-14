"""DevDesk core package – lazy exports to avoid hard Qt dependency on import."""

from __future__ import annotations

__all__ = [
    "DevDeskApplication",
    "Config",
    "Storage",
    "setup_logging",
    "get_logger",
    "Platform",
    "CredentialManager",
]


def __getattr__(name: str):
    if name == "DevDeskApplication":
        from .application import DevDeskApplication
        return DevDeskApplication
    if name == "Config":
        from .config import Config
        return Config
    if name == "Storage":
        from .storage import Storage
        return Storage
    if name == "setup_logging":
        from .logger import setup_logging
        return setup_logging
    if name == "get_logger":
        from .logger import get_logger
        return get_logger
    if name == "Platform":
        from .platform import Platform
        return Platform
    if name == "CredentialManager":
        from .credential_manager import CredentialManager
        return CredentialManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
