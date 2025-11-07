"""Tests covering CSP header hardening and script nonce injection."""

import flask


def _trigger_before_request(app_module):
    app_module.server.preprocess_request()
    app_module._get_csp_nonce()


def test_csp_header_uses_nonce_and_excludes_unsafe():
    from trendsearth_ui import app as app_module

    with app_module.server.test_request_context("/"):
        _trigger_before_request(app_module)
        response = flask.make_response("ok", 200)
        secured_response = app_module.add_security_headers(response)

        nonce = flask.g.csp_nonce
        csp_header = secured_response.headers["Content-Security-Policy"]
        script_directive = next(
            (
                part.strip()
                for part in csp_header.split(";")
                if part.strip().startswith("script-src")
            ),
            "",
        )

        assert f"'nonce-{nonce}'" in script_directive
        assert "'strict-dynamic'" in script_directive
        assert "'unsafe-inline'" not in script_directive
        assert "'unsafe-eval'" not in script_directive


def test_dash_index_scripts_receive_nonce():
    from trendsearth_ui import app as app_module

    with app_module.server.test_request_context("/"):
        _trigger_before_request(app_module)
        html = app_module.app.index()
        nonce = flask.g.csp_nonce

        assert f'nonce="{nonce}"' in html
        assert html.count('nonce="') >= 1


if __name__ == "__main__":  # pragma: no cover - manual debug hook
    import pytest

    pytest.main([__file__, "-v"])
