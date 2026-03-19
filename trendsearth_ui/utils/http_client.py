"""HTTP helper utilities for Trends.Earth UI."""

from importlib.util import find_spec
import os
import sys

import requests


def _module_available(module_name: str) -> bool:
    """Check if a module can be imported without actually importing it."""
    return find_spec(module_name) is not None


def get_client_header() -> str:
    """Build the X-TE-Client header value for API requests.

    Returns a semicolon-separated string with client type, version, OS, and commit.
    Example: "type=api_ui; version=0.1.0; os=Linux; commit=abc123"
    """
    parts = ["type=api_ui"]

    # Get version from importlib.metadata (set in pyproject.toml)
    try:
        from importlib.metadata import version as get_version

        ver = get_version("trendsearth-api-ui")
        parts.append(f"version={ver}")
    except Exception:
        parts.append("version=unknown")

    # OS info
    parts.append(f"os={sys.platform}")

    # User's language
    try:
        from trendsearth_ui.i18n import get_locale

        lang = get_locale()
    except Exception:
        lang = "en"
    parts.append(f"lang={lang}")

    # Git commit if available (set by deployment)
    commit = os.environ.get("GIT_COMMIT", "")
    if commit and commit != "unknown":
        parts.append(f"commit={commit[:12]}")

    return "; ".join(parts)


BROTLI_SUPPORTED = _module_available("brotli") or _module_available("brotlicffi")

_DEFAULT_ENCODINGS = ["gzip", "deflate"]
if BROTLI_SUPPORTED:
    _DEFAULT_ENCODINGS.append("br")

DEFAULT_ACCEPT_ENCODING = ", ".join(_DEFAULT_ENCODINGS)

# ---------------------------------------------------------------------------
# Shared requests.Session – reuses TCP connections across HTTP calls,
# avoiding the overhead of a fresh TLS handshake on every request.
# ---------------------------------------------------------------------------
_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Return the module-level shared :class:`requests.Session`.

    The session is created lazily on first call so that import-time side
    effects are kept to a minimum.  It carries the default
    ``Accept-Encoding`` header automatically.
    """
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"Accept-Encoding": DEFAULT_ACCEPT_ENCODING})
    return _session


def apply_default_headers(headers: dict | None = None) -> dict:
    """Ensure outbound API requests advertise support for compressed responses.

    Also adds the X-TE-Client header for client tracking.
    """
    merged_headers = dict(headers or {})
    merged_headers.setdefault("Accept-Encoding", DEFAULT_ACCEPT_ENCODING)
    merged_headers.setdefault("X-TE-Client", get_client_header())
    return merged_headers
