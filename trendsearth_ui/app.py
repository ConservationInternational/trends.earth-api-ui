import os

import dash
import dash_bootstrap_components as dbc
import flask
from flask import send_from_directory

# Import and register callbacks
from .callbacks import register_all_callbacks

# Import layout components
from .components import create_main_layout

# Import configuration
from .config import APP_HOST, APP_PORT, APP_TITLE

# Import deployment utilities
from .utils.deployment_info import get_health_response

# Import logging configuration
from .utils.logging_config import setup_logging

# Initialize logging with Rollbar if token is available
rollbar_token = os.environ.get("ROLLBAR_ACCESS_TOKEN")
logger = setup_logging(rollbar_token)

server = flask.Flask(__name__)

# Configure assets directory
assets_dir = os.path.join(os.path.dirname(__file__), "assets")

app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder=assets_dir,
    assets_url_path="/assets/",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "Trends.Earth API Dashboard - Manage scripts, users, and executions",
        },
    ],
)
app.title = APP_TITLE

# Add favicon links to the HTML head
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="/favicon.ico" type="image/x-icon">
        <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon">
        <!-- Suppress noisy React warnings from third-party libraries (dbc, etc.) in dev -->
        <script>
        (function () {
            try {
                var patterns = [
                    "Support for defaultProps will be removed from function components",
                    "componentWillMount has been renamed",
                    "componentWillReceiveProps has been renamed"
                ];
                var origError = window.console && window.console.error ? console.error.bind(console) : function () {};
                var origWarn = window.console && window.console.warn ? console.warn.bind(console) : function () {};

                function shouldFilter(args) {
                    try {
                        var msg = Array.prototype.join.call(args, " ");
                        if (msg.indexOf("Warning:") !== -1) {
                            for (var i = 0; i < patterns.length; i++) {
                                if (msg.indexOf(patterns[i]) !== -1) {
                                    return true;
                                }
                            }
                        }
                    } catch (e) {
                        // no-op
                    }
                    return false;
                }

                console.error = function () {
                    if (shouldFilter(arguments)) { return; }
                    return origError.apply(console, arguments);
                };
                console.warn = function () {
                    if (shouldFilter(arguments)) { return; }
                    return origWarn.apply(console, arguments);
                };
            } catch (e) {
                // Swallow any errors here to avoid impacting app startup
            }
        })();
        </script>
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
    return send_from_directory(assets_dir, filename)


# Create the main layout
app.layout = create_main_layout()


# Add global error handlers
def _is_bot_request(user_agent: str) -> bool:
    """Check if the User-Agent indicates a bot, scanner, or automated tool."""
    if not user_agent:
        return False

    user_agent_lower = user_agent.lower()

    # Known bot/scanner user agents that should not report to Rollbar
    bot_indicators = [
        "libredtail-http",
        "python-requests",
        "curl/",
        "wget/",
        "go-http-client",
        "apache-httpclient",
        "nikto",
        "sqlmap",
        "nuclei",
        "masscan",
        "nmap",
        "scanner",
        "bot",
        "crawl",
        "spider",
        "scraper",
    ]

    return any(indicator in user_agent_lower for indicator in bot_indicators)


@server.errorhandler(400)
def bad_request(error):  # noqa: ARG001
    """Handle 400 Bad Request errors, especially JSON decode errors."""
    from .utils.logging_config import log_exception

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

    log_exception(logger, f"400 Bad Request: {request_info}{request_data_info}")

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
    from .utils.logging_config import log_exception

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
        logger.warning(f"405 Method Not Allowed (bot filtered): {request_info}")
    else:
        # For legitimate requests: log to both local and Rollbar
        log_exception(logger, f"405 Method Not Allowed: {request_info}")

        # Log available routes for debugging (only for legitimate requests to reduce noise)
        route_info = []
        for rule in server.url_map.iter_rules():
            methods = sorted(rule.methods or [])
            route_info.append(f"{rule.rule} -> {methods}")
        log_exception(
            logger, f"Available routes: {'; '.join(route_info[:10])}"
        )  # Log first 10 routes

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
    from .utils.logging_config import log_exception

    log_exception(logger, f"Internal server error: {str(error)}")
    return {"status": "error", "message": "Internal server error"}, 500


@server.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions."""
    from .utils.logging_config import log_exception

    log_exception(logger, f"Uncaught exception: {str(e)}")
    # Return JSON error response for API endpoints or HTML for regular pages
    if flask.request.path.startswith("/api"):
        return {"status": "error", "message": "An unexpected error occurred"}, 500
    else:
        return "An unexpected error occurred", 500


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
