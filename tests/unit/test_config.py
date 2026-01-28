"""Unit tests for configuration module."""

from trendsearth_ui.config import (
    API_BASE,
    APP_TITLE,
    AUTH_URL,
    DEFAULT_PAGE_SIZE,
    EXECUTIONS_REFRESH_INTERVAL,
    LOGO_HEIGHT,
    LOGO_URL,
    LOGS_REFRESH_INTERVAL,
    STATUS_REFRESH_INTERVAL,
)


class TestConfigurationConstants:
    """Test configuration constants."""

    def test_api_urls_are_strings(self):
        """Test that API URLs are properly formatted strings."""
        assert isinstance(API_BASE, str)
        assert isinstance(AUTH_URL, str)

        # Should be valid URLs
        assert API_BASE.startswith("http")
        assert AUTH_URL.startswith("http")

        # Should not end with slash for consistency
        assert not API_BASE.endswith("/")
        assert not AUTH_URL.endswith("/")

    def test_app_branding(self):
        """Test app branding constants."""
        assert isinstance(APP_TITLE, str)
        assert len(APP_TITLE) > 0
        assert "Trends.Earth" in APP_TITLE

        assert isinstance(LOGO_URL, str)
        # Logo URL can be either external (http) or local assets path
        assert LOGO_URL.startswith(("http", "/assets/"))

        assert isinstance(LOGO_HEIGHT, str)
        # Logo height can be CSS units or 'auto'
        valid_values = ["px", "em", "rem", "%", "vh", "vw", "auto"]
        assert any(val in LOGO_HEIGHT for val in valid_values)

    def test_pagination_settings(self):
        """Test pagination and refresh settings."""
        assert isinstance(DEFAULT_PAGE_SIZE, int)
        assert DEFAULT_PAGE_SIZE > 0
        assert DEFAULT_PAGE_SIZE <= 200  # Reasonable limit

    def test_refresh_intervals(self):
        """Test refresh interval settings."""
        assert isinstance(EXECUTIONS_REFRESH_INTERVAL, int)
        assert isinstance(LOGS_REFRESH_INTERVAL, int)
        assert isinstance(STATUS_REFRESH_INTERVAL, int)

        # Should be reasonable intervals (in milliseconds)
        assert EXECUTIONS_REFRESH_INTERVAL >= 1000  # At least 1 second
        assert LOGS_REFRESH_INTERVAL >= 1000
        assert STATUS_REFRESH_INTERVAL >= 1000

        # Should not be too frequent
        assert EXECUTIONS_REFRESH_INTERVAL <= 300000  # No more than 5 minutes
        assert LOGS_REFRESH_INTERVAL <= 60000  # No more than 1 minute
        assert STATUS_REFRESH_INTERVAL <= 300000  # No more than 5 minutes

    def test_config_values_not_none(self):
        """Test that no configuration values are None."""
        config_values = [
            API_BASE,
            AUTH_URL,
            APP_TITLE,
            LOGO_URL,
            LOGO_HEIGHT,
            DEFAULT_PAGE_SIZE,
            EXECUTIONS_REFRESH_INTERVAL,
            LOGS_REFRESH_INTERVAL,
            STATUS_REFRESH_INTERVAL,
        ]

        for value in config_values:
            assert value is not None

    def test_api_endpoints_different(self):
        """Test that API and Auth URLs are different endpoints."""
        # They should be different endpoints
        assert API_BASE != AUTH_URL

    def test_intervals_in_milliseconds(self):
        """Test that intervals are specified in milliseconds for Dash."""
        # Dash intervals should be in milliseconds
        # So values should be >= 1000 for reasonable refresh rates
        assert EXECUTIONS_REFRESH_INTERVAL >= 1000
        assert LOGS_REFRESH_INTERVAL >= 1000
        assert STATUS_REFRESH_INTERVAL >= 1000


class TestConfigurationConsistency:
    """Test configuration consistency and relationships."""

    def test_log_refresh_faster_than_executions(self):
        """Test that log refresh is faster than executions refresh."""
        # Logs should refresh more frequently than executions
        assert LOGS_REFRESH_INTERVAL <= EXECUTIONS_REFRESH_INTERVAL

    def test_reasonable_page_size(self):
        """Test that page size is reasonable for web display."""
        # Page size should be reasonable for web tables
        assert DEFAULT_PAGE_SIZE >= 10  # Not too small
        assert DEFAULT_PAGE_SIZE <= 200  # Not too large

    def test_logo_dimensions_format(self):
        """Test that logo height is in valid CSS format."""
        assert isinstance(LOGO_HEIGHT, str)
        # Should be in CSS units (px, em, rem, %, etc.) or 'auto'
        valid_values = ["px", "em", "rem", "%", "vh", "vw", "auto"]
        assert any(val in LOGO_HEIGHT for val in valid_values)

    def test_url_consistency(self):
        """Test URL format consistency."""
        # API and AUTH URLs should be external URLs
        external_urls = [API_BASE, AUTH_URL]

        for url in external_urls:
            assert isinstance(url, str)
            assert url.startswith(("http://", "https://"))
            # Should not have trailing whitespace
            assert url == url.strip()

        # Logo URL can be external or local asset path
        assert isinstance(LOGO_URL, str)
        assert LOGO_URL.startswith(("http://", "https://", "/assets/"))
        assert LOGO_URL == LOGO_URL.strip()


class TestConfigurationImport:
    """Test that configuration can be imported properly."""

    def test_all_constants_importable(self):
        """Test that all constants can be imported."""
        # This test passes if all imports in the module work
        from trendsearth_ui.config import (
            API_BASE,
            APP_TITLE,
            AUTH_URL,
            DEFAULT_PAGE_SIZE,
            EXECUTIONS_REFRESH_INTERVAL,
            LOGO_HEIGHT,
            LOGO_URL,
            LOGS_REFRESH_INTERVAL,
            STATUS_REFRESH_INTERVAL,
        )

        # All should be defined
        assert API_BASE is not None
        assert AUTH_URL is not None
        assert APP_TITLE is not None
        assert LOGO_URL is not None
        assert LOGO_HEIGHT is not None
        assert DEFAULT_PAGE_SIZE is not None
        assert EXECUTIONS_REFRESH_INTERVAL is not None
        assert LOGS_REFRESH_INTERVAL is not None
        assert STATUS_REFRESH_INTERVAL is not None

    def test_config_module_structure(self):
        """Test that config module has expected structure."""
        import trendsearth_ui.config as config

        # Should have all expected attributes
        expected_attrs = [
            "API_BASE",
            "AUTH_URL",
            "APP_TITLE",
            "LOGO_URL",
            "LOGO_HEIGHT",
            "DEFAULT_PAGE_SIZE",
            "EXECUTIONS_REFRESH_INTERVAL",
            "LOGS_REFRESH_INTERVAL",
            "STATUS_REFRESH_INTERVAL",
        ]

        for attr in expected_attrs:
            assert hasattr(config, attr), f"Config missing {attr}"
