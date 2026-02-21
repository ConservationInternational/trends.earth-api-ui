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


# ---------------------------------------------------------------------------
# Rollbar integration – report worker-level errors that never reach Flask
# ---------------------------------------------------------------------------


def _init_rollbar():
    """Initialise Rollbar in the current worker process (if configured)."""
    import os

    token = os.environ.get("ROLLBAR_ACCESS_TOKEN")
    if not token:
        return

    import rollbar

    rollbar.init(
        access_token=token,
        environment=os.environ.get("DEPLOYMENT_ENVIRONMENT", "production"),
        code_version=os.environ.get("GIT_COMMIT", "unknown"),
        branch=os.environ.get("GIT_BRANCH", "unknown"),
        capture_email=False,
        capture_username=False,
        capture_ip=False,
        locals={"enabled": False},
    )


def post_fork(server, worker):  # noqa: ARG001
    """Called after a Gunicorn worker has been forked."""
    _init_rollbar()


def worker_exit(server, worker):  # noqa: ARG001
    """Called when a Gunicorn worker is shutting down."""
    import logging

    logger = logging.getLogger("trendsearth_ui")
    logger.warning("Gunicorn worker %s exiting", worker.pid)


def child_exit(server, worker):  # noqa: ARG001
    """Called in the master when a worker process exits unexpectedly."""
    import logging
    import os

    logger = logging.getLogger("trendsearth_ui")
    logger.error("Gunicorn worker %s died unexpectedly", worker.pid)

    token = os.environ.get("ROLLBAR_ACCESS_TOKEN")
    if token:
        import rollbar

        if not getattr(rollbar, "_initialized", False):
            _init_rollbar()
        rollbar.report_message(
            f"Gunicorn worker {worker.pid} died unexpectedly",
            level="error",
        )
