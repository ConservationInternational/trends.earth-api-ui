"""Configuration settings for the Trends.Earth API Dashboard."""

import os

# API Configuration
# Default API environment (used when host detection fails)
DEFAULT_API_ENVIRONMENT = "production"

# Environment variable to force a specific API environment (useful for local development)
# Set FORCE_API_ENVIRONMENT=staging to use staging API from localhost
FORCE_API_ENVIRONMENT = os.environ.get("FORCE_API_ENVIRONMENT", "").lower() or None

# API Environment configurations
API_ENVIRONMENTS = {
    "production": {
        "base": "https://api.trends.earth/api/v1",
        "auth": "https://api.trends.earth/auth",
        "display_name": "Production (api.trends.earth)",
        "host_pattern": "api.trends.earth",
    },
    "staging": {
        "base": "https://api-staging.trends.earth/api/v1",
        "auth": "https://api-staging.trends.earth/auth",
        "display_name": "Staging (api-staging.trends.earth)",
        "host_pattern": "api-staging.trends.earth",
    },
}


def detect_api_environment_from_host():
    """
    Detect the API environment based on the request host/subdomain.

    Priority:
    1. FORCE_API_ENVIRONMENT env var (if set to a valid environment)
    2. Host-based detection (api.trends.earth -> production, api-staging.trends.earth -> staging)
    3. DEFAULT_API_ENVIRONMENT fallback

    If the UI is accessed from api.trends.earth, use production.
    If the UI is accessed from api-staging.trends.earth, use staging.
    Falls back to DEFAULT_API_ENVIRONMENT for localhost or unknown hosts.

    Returns:
        str: The detected environment key ('production' or 'staging')
    """
    # Check for forced environment first (useful for local development)
    if FORCE_API_ENVIRONMENT and FORCE_API_ENVIRONMENT in API_ENVIRONMENTS:
        return FORCE_API_ENVIRONMENT

    try:
        from flask import request

        host = request.host.lower() if request.host else ""
        # Remove port if present (e.g., localhost:8050 -> localhost)
        host = host.split(":")[0]

        # Check for staging first (more specific pattern)
        if "api-staging" in host or "staging" in host:
            return "staging"

        # Check for production pattern
        if "api.trends.earth" in host:
            return "production"

        # For localhost or other development hosts, use default
        return DEFAULT_API_ENVIRONMENT

    except Exception:
        # If we can't access the request context, use default
        return DEFAULT_API_ENVIRONMENT


# Legacy constants for backward compatibility (using default environment)
API_BASE = API_ENVIRONMENTS[DEFAULT_API_ENVIRONMENT]["base"]
AUTH_URL = API_ENVIRONMENTS[DEFAULT_API_ENVIRONMENT]["auth"]


def get_api_base(environment=None):
    """Get API base URL for the specified environment."""
    env = environment or DEFAULT_API_ENVIRONMENT
    return API_ENVIRONMENTS.get(env, API_ENVIRONMENTS[DEFAULT_API_ENVIRONMENT])["base"]


def get_auth_url(environment=None):
    """Get authentication URL for the specified environment."""
    env = environment or DEFAULT_API_ENVIRONMENT
    return API_ENVIRONMENTS.get(env, API_ENVIRONMENTS[DEFAULT_API_ENVIRONMENT])["auth"]


def get_current_api_environment():
    """
    Get the current API environment.

    Priority:
    1. Detect from request host (subdomain-based detection)
    2. Fall back to DEFAULT_API_ENVIRONMENT

    Note: Host-based detection takes precedence to ensure users
    always interact with the correct API based on which UI they access.
    """
    return detect_api_environment_from_host()


def get_current_api_base():
    """Get the current API base URL based on current environment."""
    return get_api_base(get_current_api_environment())


def get_current_auth_url():
    """Get the current auth URL based on current environment."""
    return get_auth_url(get_current_api_environment())


# App Configuration
APP_TITLE = "Trends.Earth API Dashboard"
APP_HOST = "127.0.0.1"
APP_PORT = 8050

# Pagination and refresh settings
DEFAULT_PAGE_SIZE = 100
EXECUTIONS_REFRESH_INTERVAL = 30 * 1000  # 30 seconds in milliseconds
LOGS_REFRESH_INTERVAL = 10 * 1000  # 10 seconds in milliseconds
STATUS_REFRESH_INTERVAL = 5 * 60 * 1000  # 5 minutes in milliseconds for status auto-refresh

# UI Constants
LOGO_URL = "/assets/trends_earth_logo_from_CI.png"
LOGO_HEIGHT = "auto"
LOGO_SQUARE_URL = "/assets/trends_earth_logo_square_192x192.png"

# Map Configuration - Tile providers with English labels
MAP_TILE_PROVIDERS = {
    "carto_voyager": {
        "url": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        "subdomains": ["a", "b", "c", "d"],
        "maxZoom": 20,
        "description": "CartoDB Voyager - Clean style with English labels",
    },
    "carto_positron": {
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        "subdomains": ["a", "b", "c", "d"],
        "maxZoom": 20,
        "description": "CartoDB Positron - Light style with English labels",
    },
    "esri_world_imagery": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        "maxZoom": 18,
        "description": "Esri World Imagery - Satellite imagery with English labels",
    },
    "osm_english": {
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        "subdomains": ["a", "b", "c"],
        "maxZoom": 19,
        "description": "OpenStreetMap - Standard style (primarily English internationally)",
    },
}

# Default tile provider for maps
DEFAULT_MAP_TILE_PROVIDER = "carto_voyager"
