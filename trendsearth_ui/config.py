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
LOGO_URL = "https://docs.trends.earth/en/latest/_images/trends_earth_logo_bl_1200.png"
LOGO_HEIGHT = "60px"
