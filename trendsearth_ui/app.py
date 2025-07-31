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
@server.errorhandler(405)
def method_not_allowed(error):  # noqa: ARG001
    """Handle 405 Method Not Allowed errors."""
    from .utils.logging_config import log_exception

    # Log the request details to help debug
    request_info = f"Path: {flask.request.path}, Method: {flask.request.method}"
    if flask.request.headers.get("Content-Type"):
        request_info += f", Content-Type: {flask.request.headers.get('Content-Type')}"
    if flask.request.headers.get("User-Agent"):
        request_info += f", User-Agent: {flask.request.headers.get('User-Agent')[:100]}"

    # Log available routes for debugging
    route_info = []
    for rule in server.url_map.iter_rules():
        route_info.append(f"{rule.rule} -> {list(rule.methods)}")

    log_exception(logger, f"405 Method Not Allowed: {request_info}")
    log_exception(logger, f"Available routes: {'; '.join(route_info[:10])}")  # Log first 10 routes

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
