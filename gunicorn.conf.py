# Gunicorn configuration file for Trends.Earth UI

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
# NOTE: Dash applications require a single worker due to in-memory state and callback routing
# Multiple workers cause 405 Method Not Allowed errors for Dash internal routes
workers = 1  # Use single worker to avoid Dash callback issues
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, with up to 50% jitter
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "trendsearth_ui"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure if needed)
# keyfile = None
# certfile = None

# Application
module = "trendsearth_ui.app:server"
