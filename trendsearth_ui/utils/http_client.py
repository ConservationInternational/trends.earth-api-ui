"""HTTP helper utilities for Trends.Earth UI."""

# Detect brotli support so we only advertise encodings the client can actually decode.
from importlib.util import find_spec

import requests


def _module_available(module_name: str) -> bool:
    """Check if a module can be imported without actually importing it."""
    return find_spec(module_name) is not None


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
    """Ensure outbound API requests advertise support for compressed responses."""
    merged_headers = dict(headers or {})
    merged_headers.setdefault("Accept-Encoding", DEFAULT_ACCEPT_ENCODING)
    return merged_headers
