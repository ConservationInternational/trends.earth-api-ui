"""Configuration settings for the Trends.Earth API Dashboard."""

# API Configuration
# Default API environment (can be overridden by user selection)
DEFAULT_API_ENVIRONMENT = "production"

# API Environment configurations
API_ENVIRONMENTS = {
    "production": {
        "base": "https://api.trends.earth/api/v1",
        "auth": "https://api.trends.earth/auth",
        "display_name": "Production (api.trends.earth)",
    },
    "staging": {
        "base": "https://api-staging.trends.earth/api/v1",
        "auth": "https://api-staging.trends.earth/auth",
        "display_name": "Staging (api-staging.trends.earth)",
    },
}

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
    """Get the current API environment from cookie or default."""
    try:
        import json

        from flask import request

        auth_cookie = request.cookies.get("auth_token")
        if auth_cookie:
            cookie_data = json.loads(auth_cookie)
            if cookie_data and isinstance(cookie_data, dict):
                return cookie_data.get("api_environment", DEFAULT_API_ENVIRONMENT)
    except Exception:
        pass
    return DEFAULT_API_ENVIRONMENT


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
LOGO_URL = "/assets/trends_earth_logo.png"
LOGO_HEIGHT = "60px"
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
