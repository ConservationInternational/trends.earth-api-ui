"""Tests for HTTP helper utilities."""

from trendsearth_ui.utils.http_client import (
    BROTLI_SUPPORTED,
    DEFAULT_ACCEPT_ENCODING,
    apply_default_headers,
)


def test_apply_default_headers_adds_accept_encoding():
    """Accept-Encoding header is added when missing."""
    headers = apply_default_headers()
    encodings = {value.strip() for value in headers["Accept-Encoding"].split(",")}

    # Core encodings should always be present
    assert {"gzip", "deflate"}.issubset(encodings)

    if BROTLI_SUPPORTED:
        assert "br" in encodings
    else:
        assert "br" not in encodings

    # Ensure DEFAULT_ACCEPT_ENCODING matches helper output exactly
    assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING


def test_apply_default_headers_preserves_existing_accept_encoding():
    """Existing Accept-Encoding header is not overwritten."""
    custom_headers = {"Accept-Encoding": "gzip"}
    headers = apply_default_headers(custom_headers)
    assert headers["Accept-Encoding"] == "gzip"
    # Original dict should remain unchanged
    assert custom_headers["Accept-Encoding"] == "gzip"
