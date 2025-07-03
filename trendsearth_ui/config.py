"""Configuration settings for the Trends.Earth API Dashboard."""

# API Configuration
API_BASE = "https://api.trends.earth/api/v1"
AUTH_URL = "https://api.trends.earth/auth"

# App Configuration
APP_TITLE = "Trends.Earth API Dashboard"
APP_HOST = "127.0.0.1"
APP_PORT = 8050

# Pagination and refresh settings
DEFAULT_PAGE_SIZE = 50
CACHE_BLOCK_SIZE = 50
MAX_BLOCKS_IN_CACHE = 2
EXECUTIONS_REFRESH_INTERVAL = 30 * 1000  # 30 seconds in milliseconds
LOGS_REFRESH_INTERVAL = 10 * 1000  # 10 seconds in milliseconds
STATUS_REFRESH_INTERVAL = 60 * 1000  # 60 seconds in milliseconds

# UI Constants
LOGO_URL = "/assets/trends_earth_logo.svg"
LOGO_HEIGHT = "60px"

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
