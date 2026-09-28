"""Tests for per-application access display and management helpers."""

import pytest

from trendsearth_ui.callbacks.app_access import _render_grants
from trendsearth_ui.callbacks.users import _format_app_access, _format_user_rows

pytestmark = pytest.mark.unit


class TestFormatAppAccess:
    def test_no_grants(self):
        assert _format_app_access(None) == "—"
        assert _format_app_access([]) == "—"

    def test_active_grant_includes_role(self):
        grants = [{"app_key": "avoided_emissions", "status": "active", "role": "admin"}]
        assert _format_app_access(grants) == "Avoided Emissions (admin)"

    def test_active_grants_listed_before_other_statuses(self):
        grants = [
            {"app_key": "rio_coherence", "status": "pending", "role": None},
            {"app_key": "avoided_emissions", "status": "active", "role": "member"},
        ]
        assert _format_app_access(grants) == ("Avoided Emissions (member), Rio Coherence (pending)")

    def test_unknown_app_key_is_humanized(self):
        grants = [{"app_key": "some_new_app", "status": "active", "role": None}]
        assert _format_app_access(grants) == "Some New App"


class TestFormatUserRows:
    def test_app_access_flattened_into_display_column(self):
        users = [
            {
                "id": "u1",
                "role": "USER",
                "app_access": [
                    {"app_key": "avoided_emissions", "status": "active", "role": "member"}
                ],
            }
        ]
        rows = _format_user_rows(users, "SUPERADMIN", "UTC")
        assert rows[0]["app_access_display"] == "Avoided Emissions (member)"
        assert "app_access" not in rows[0]

    def test_missing_app_access_renders_placeholder(self):
        rows = _format_user_rows([{"id": "u1", "role": "USER"}], "ADMIN", "UTC")
        assert rows[0]["app_access_display"] == "—"


class TestRenderGrants:
    def test_shows_every_registered_app_even_without_a_grant(self):
        apps = [
            {"app_key": "avoided_emissions", "label": "Avoided Emissions", "roles": ["member"]},
            {"app_key": "rio_coherence", "label": "Rio Coherence", "roles": ["member"]},
        ]
        grants = [{"app_key": "avoided_emissions", "status": "active", "role": "member"}]
        rendered = str(_render_grants(apps, grants))
        assert "Avoided Emissions" in rendered
        assert "Rio Coherence" in rendered
        assert "no access" in rendered

    def test_empty_registry(self):
        rendered = str(_render_grants([], []))
        assert "No gated applications" in rendered
