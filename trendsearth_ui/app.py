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

server = flask.Flask(__name__)

# Configure assets directory
assets_dir = os.path.join(os.path.dirname(__file__), "assets")

app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    assets_folder=assets_dir,
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
        {%favicon%}
        <link rel="icon" type="image/png" sizes="200x200" href="/assets/trends_earth_logo_square_200x200.png">
        <link rel="shortcut icon" type="image/png" sizes="200x200" href="/assets/trends_earth_logo_square_200x200.png">
        <link rel="apple-touch-icon" type="image/png" sizes="200x200" href="/assets/trends_earth_logo_square_200x200.png">
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
    return {"status": "healthy"}, 200


@server.route("/favicon.ico")
def favicon():
    return send_from_directory(
        assets_dir, "trends_earth_logo_square_200x200.png", mimetype="image/png"
    )


@server.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(assets_dir, filename)


# Create the main layout
app.layout = create_main_layout()

# Register all callbacks
register_all_callbacks(app)


def main():
    """Main entry point for console script."""
    print("Starting Trends.Earth API Dashboard...")
    print(f"Access the app at: http://{APP_HOST}:{APP_PORT}")
    print("Debug mode: True")
    app.run(debug=True, host=APP_HOST, port=APP_PORT, use_reloader=False)


if __name__ == "__main__":
    main()
