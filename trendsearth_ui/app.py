import base64
import os
import re

import dash
import dash_bootstrap_components as dbc
import flask
from flask import got_request_exception, send_from_directory

# Import and register callbacks
from .callbacks import register_all_callbacks

# Import layout components
from .components import create_main_layout

# Import configuration
from .config import APP_HOST, APP_PORT, APP_TITLE

# Import deployment utilities
from .utils.deployment_info import get_health_response

# Import logging configuration
from .utils.logging_config import is_rollbar_initialized, setup_logging

# Initialize logging with Rollbar if token is available
rollbar_token = os.environ.get("ROLLBAR_ACCESS_TOKEN")
logger = setup_logging(rollbar_token)

server = flask.Flask(__name__)


def _rollbar_report_exception(sender, exception, **_extra):  # noqa: ARG001
    """Report unhandled Flask exceptions to Rollbar via the signal hook."""
    if is_rollbar_initialized():
        import rollbar

        rollbar.report_exc_info()


# Connect the Flask signal so that any exception that bubbles up outside
# of Dash callbacks (e.g. in regular Flask routes) is forwarded to Rollbar.
got_request_exception.connect(_rollbar_report_exception, server)

_SECURE_ENVIRONMENTS = {"production", "staging"}


def _should_enforce_hsts() -> bool:
    """Return True when HSTS should be applied."""
    env = os.environ.get("DEPLOYMENT_ENVIRONMENT", "").lower()
    if env in _SECURE_ENVIRONMENTS:
        return True

    forwarded_proto = flask.request.headers.get("X-Forwarded-Proto", "")
    if "https" in forwarded_proto.lower():
        return True

    return flask.request.is_secure


# Configure assets directory
assets_dir = os.path.join(os.path.dirname(__file__), "assets")

app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder=assets_dir,
    assets_url_path="/assets",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "Trends.Earth API Dashboard - Manage scripts, users, and executions",
        },
    ],
)
app.title = APP_TITLE
# Suppress the default Dash renderer so the custom CSP nonce-aware
# dash_renderer.js in the assets/ folder is used instead.
app.renderer = ""

# Add favicon links to the HTML head
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="/favicon.ico" type="image/x-icon">
        <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def _generate_csp_nonce() -> str:
    """Return a per-request CSP nonce."""
    return base64.b64encode(os.urandom(16)).decode("utf-8")


def _get_csp_nonce() -> str:
    """Fetch or create the nonce stored on flask.g for this request."""
    nonce = getattr(flask.g, "csp_nonce", None)
    if nonce:
        return nonce

    nonce = _generate_csp_nonce()
    flask.g.csp_nonce = nonce
    return nonce


# Pre-compiled patterns used in nonce injection – avoids re-compiling on every request.
_SCRIPT_TAG_PATTERN = re.compile(r"(<script)(?![^>]*nonce=)", flags=re.IGNORECASE)
_BODY_TAG_PATTERN = re.compile(r"(<body)([^>]*)(>)", flags=re.IGNORECASE)


def _inject_nonce_into_scripts(html: str, nonce: str) -> str:
    """Ensure every script tag carries the CSP nonce."""
    return _SCRIPT_TAG_PATTERN.sub(rf'\1 nonce="{nonce}"', html)


def _inject_nonce_metadata(html: str, nonce: str) -> str:
    """Expose the CSP nonce to client-side scripts via head and body attributes."""
    meta_tag = f'<meta name="dash-csp-nonce" content="{nonce}">'
    if "</head>" in html:
        html = html.replace("</head>", f"    {meta_tag}\n    </head>", 1)
    else:
        html = f"{meta_tag}{html}"

    if _BODY_TAG_PATTERN.search(html):
        html = _BODY_TAG_PATTERN.sub(rf'\1\2 data-csp-nonce="{nonce}"\3', html, count=1)
    return html


_original_index = app.index


def _index_with_csp_nonce(**kwargs):
    """Render the Dash index HTML with CSP nonces applied."""
    nonce = _get_csp_nonce()
    html = _original_index(**kwargs)
    html = _inject_nonce_metadata(html, nonce)
    return _inject_nonce_into_scripts(html, nonce)


app.index = _index_with_csp_nonce  # type: ignore[assignment]


def _swap_dash_index_route(route: str) -> None:
    view = server.view_functions.get(route)
    if not view:
        return
    target = getattr(view, "__func__", view)
    original_target = getattr(_original_index, "__func__", _original_index)
    if target is original_target:
        server.view_functions[route] = _index_with_csp_nonce


for _route in ("/", "/<path:path>"):
    _swap_dash_index_route(_route)


@server.route("/api-ui-health")
def health_check():
    """Health check endpoint with deployment information."""
    try:
        return get_health_response(), 200
    except Exception as e:
        from .utils.logging_config import log_exception

        log_exception(logger, f"Health check endpoint error: {str(e)}")
        return {"status": "error", "message": "Health check failed"}, 500


@server.route("/favicon.ico")
def favicon():
    return send_from_directory(assets_dir, "favicon.ico", mimetype="image/x-icon")


@server.route("/assets/<path:filename>")
def serve_assets(filename):
    safe_filename = filename.lstrip("/")
    return send_from_directory(assets_dir, safe_filename)


# Create the main layout
app.layout = create_main_layout()


@server.before_request
def set_csp_nonce() -> None:
    """Guarantee a CSP nonce exists for the current request."""
    _get_csp_nonce()


# Add global error handlers
_CSP_STYLE_SOURCES = [
    "'self'",
    "'unsafe-inline'",
    "https://cdn.jsdelivr.net",
    "https://fonts.googleapis.com",
]

_CSP_FONT_SOURCES = [
    "'self'",
    "data:",
    "https://cdn.jsdelivr.net",
    "https://fonts.gstatic.com",
]

_CSP_IMG_SOURCES = ["'self'", "data:", "https:"]

_CSP_CONNECT_SOURCES = [
    "'self'",
    "https://cdn.jsdelivr.net",
    "https://cdn.plot.ly",
]

_CSP_SCRIPT_SOURCES = [
    "'self'",
    "https://cdn.plot.ly",
    "https://cdn.jsdelivr.net",
]

# Pre-build the static portions of the CSP header so we only format the nonce
# at request time.  Everything except the script-src directive is constant.
_CSP_STATIC_SCRIPT_SOURCES = " ".join(dict.fromkeys(_CSP_SCRIPT_SOURCES))
_CSP_STATIC_SUFFIX = (
    f"style-src {' '.join(_CSP_STYLE_SOURCES)}; "
    f"img-src {' '.join(_CSP_IMG_SOURCES)}; "
    f"font-src {' '.join(_CSP_FONT_SOURCES)}; "
    f"connect-src {' '.join(_CSP_CONNECT_SOURCES)}; "
    "frame-ancestors 'none';"
)


@server.after_request
def add_security_headers(response):
    """Attach standard security headers to every response."""
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

    nonce = getattr(flask.g, "csp_nonce", None)
    if nonce:
        script_src = f"'nonce-{nonce}' {_CSP_STATIC_SCRIPT_SOURCES}"
    else:
        script_src = _CSP_STATIC_SCRIPT_SOURCES

    csp_value = f"default-src 'self'; script-src {script_src}; {_CSP_STATIC_SUFFIX}"

    response.headers.setdefault("Content-Security-Policy", csp_value)

    if _should_enforce_hsts():
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
        )

    return response


_BOT_PATTERN = re.compile(
    r"libredtail-http|python-requests|curl/|wget/|go-http-client|apache-httpclient"
    r"|nikto|sqlmap|nuclei|masscan|nmap|scanner|bot|crawl|spider|scraper",
    re.IGNORECASE,
)


def _is_bot_request(user_agent: str) -> bool:
    """Check if the User-Agent indicates a bot, scanner, or automated tool."""
    if not user_agent:
        return False

    return _BOT_PATTERN.search(user_agent) is not None


@server.errorhandler(400)
def bad_request(error):  # noqa: ARG001
    """Handle 400 Bad Request errors, especially JSON decode errors."""
    from .utils.logging_config import log_warning

    # Log detailed request information for debugging
    request_info = f"Path: {flask.request.path}, Method: {flask.request.method}"
    if flask.request.headers.get("Content-Type"):
        request_info += f", Content-Type: {flask.request.headers.get('Content-Type')}"
    if flask.request.headers.get("Content-Length"):
        request_info += f", Content-Length: {flask.request.headers.get('Content-Length')}"
    if flask.request.headers.get("User-Agent"):
        ua_hdr = flask.request.headers.get("User-Agent")
        request_info += f", User-Agent: {ua_hdr[:100] if ua_hdr else ''}"

    # Try to safely read request data for debugging
    request_data_info = ""
    try:
        # Get raw data without consuming the stream if possible
        if hasattr(flask.request, "get_data"):
            raw_data = flask.request.get_data(as_text=True)
            if raw_data:
                # Log first 200 chars of data for debugging, but don't log sensitive info
                preview = raw_data[:200]
                request_data_info = f", Data preview: {repr(preview)}"
            else:
                request_data_info = ", Data: <empty>"
    except Exception as e:
        request_data_info = f", Data read error: {str(e)}"

    log_warning(logger, f"400 Bad Request: {request_info}{request_data_info}")

    # Return JSON error response for API endpoints and Dash callbacks
    if (
        flask.request.path.startswith("/api")
        or flask.request.path.startswith("/_dash-")
        or flask.request.headers.get("Content-Type", "").startswith("application/json")
    ):
        return {
            "status": "error",
            "message": "Bad request: Invalid or malformed request data",
        }, 400
    else:
        return "Bad request: Invalid or malformed request data", 400


@server.errorhandler(405)
def method_not_allowed(error):  # noqa: ARG001
    """Handle 405 Method Not Allowed errors."""
    from .utils.logging_config import log_warning

    # Log the request details to help debug
    request_info = f"Path: {flask.request.path}, Method: {flask.request.method}"
    if flask.request.headers.get("Content-Type"):
        request_info += f", Content-Type: {flask.request.headers.get('Content-Type')}"
    if flask.request.headers.get("User-Agent"):
        ua_hdr = flask.request.headers.get("User-Agent")
        request_info += f", User-Agent: {ua_hdr[:100] if ua_hdr else ''}"

    # Check if this is a bot/scanner request
    user_agent = flask.request.headers.get("User-Agent", "")
    is_bot = _is_bot_request(user_agent)

    if is_bot:
        # For bot requests: log locally for debugging but don't report to Rollbar
        logger.info("405 Method Not Allowed (bot filtered): %s", request_info)
    else:
        # For legitimate requests: log to Rollbar as a warning
        route_info = []
        for rule in server.url_map.iter_rules():
            methods = sorted(rule.methods or [])
            route_info.append(f"{rule.rule} -> {methods}")
        extra = {"available_routes": "; ".join(route_info[:10])}
        log_warning(logger, f"405 Method Not Allowed: {request_info}", extra_data=extra)

    # Return JSON error response for API endpoints or HTML for regular pages
    if flask.request.path.startswith("/api") or flask.request.headers.get(
        "Content-Type", ""
    ).startswith("application/json"):
        return {
            "status": "error",
            "message": f"Method {flask.request.method} not allowed for {flask.request.path}",
        }, 405
    else:
        return f"Method {flask.request.method} not allowed for {flask.request.path}", 405


@server.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    from .utils.logging_config import log_error

    log_error(logger, f"Internal server error: {error}")
    return {"status": "error", "message": "Internal server error"}, 500


@server.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    logger.exception("Uncaught exception: %s", e)
    # Return JSON error response for API endpoints or HTML for regular pages
    if flask.request.path.startswith("/api"):
        return {"status": "error", "message": "An unexpected error occurred"}, 500
    else:
        return "An unexpected error occurred", 500


@server.errorhandler(404)
def not_found(_error):
    """Handle 404 errors with logging.

    Asset requests and bot traffic are logged at DEBUG level to avoid noise.
    All other 404s are logged at WARNING level so they reach Rollbar.
    """
    path = flask.request.path
    user_agent = flask.request.headers.get("User-Agent", "")

    # Determine whether this 404 warrants a Rollbar notification
    is_asset = path.startswith(("/assets/", "/favicon", "/_dash-"))
    is_bot = _is_bot_request(user_agent)

    if is_asset or is_bot:
        logger.debug("404 Not Found: %s (filtered)", path)
    else:
        logger.warning("404 Not Found: Path=%s, Method=%s", path, flask.request.method)

    # For API-style requests return JSON; for others return lightweight HTML
    if flask.request.path.startswith("/api") or flask.request.headers.get(
        "Content-Type", ""
    ).startswith("application/json"):
        return {"status": "error", "message": "Not Found"}, 404
    # Plain text/HTML response for unknown routes; Dash will render root on load
    return flask.Response(
        '<div data-testid="not-found-page">404 Not Found</div>',
        mimetype="text/html",
        status=404,
    )


# Register all callbacks
register_all_callbacks(app)


def main():
    """Main entry point for console script."""
    logger.info("Starting Trends.Earth API Dashboard...")
    logger.info(f"Access the app at: http://{APP_HOST}:{APP_PORT}")
    logger.info("Debug mode: True")

    # Log deployment information
    deployment_info = get_health_response()["deployment"]
    logger.info(f"Deployment info: {deployment_info}")

    if rollbar_token:
        logger.info("Rollbar error tracking is enabled")
    else:
        logger.warning("Rollbar error tracking is disabled (no ROLLBAR_ACCESS_TOKEN provided)")

    app.run(debug=True, host=APP_HOST, port=APP_PORT, use_reloader=False)


if __name__ == "__main__":
    main()
