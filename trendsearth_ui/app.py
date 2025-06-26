import dash
import dash_bootstrap_components as dbc
import flask
from flask import send_from_directory

# Import and register callbacks
from .callbacks import register_all_callbacks

# Import layout components
from .components import create_main_layout

# Import configuration
from .config import APP_TITLE, APP_PORT, APP_HOST

server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = APP_TITLE


@server.route("/health")
def health_check():
    return {"status": "healthy"}, 200


@server.route("/favicon.ico")
def favicon():
    return send_from_directory(server.root_path, "favicon.ico", mimetype="image/vnd.microsoft.icon")


# Create the main layout
app.layout = create_main_layout()

# Register all callbacks
register_all_callbacks(app)


def main():
    """Main entry point for console script."""
    print("Starting Trends.Earth API Dashboard...")
    print(f"Access the app at: http://{APP_HOST}:{APP_PORT}")
    print(f"Debug mode: True")
    app.run(debug=True, host=APP_HOST, port=APP_PORT, use_reloader=False)


if __name__ == "__main__":
    main()
