"""
Simple test app to isolate the hanging issue.
This creates a minimal Dash app without the complex callbacks.
"""

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import flask

# Create a simple test app
server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Simple layout without complex callbacks
app.layout = dbc.Container(
    [
        html.H1("Trends.Earth API Dashboard - Test"),
        html.P("If you can see this, the basic app is working!"),
        html.Div(id="test-content"),
        dcc.Store(id="test-store"),
    ]
)


@server.route("/api-ui-health")
def health_check():
    return {"status": "healthy"}, 200


def main():
    """Main entry point for the test app."""
    print("Starting Simple Test App...")
    print("Access the app at: http://127.0.0.1:8051")
    app.run(debug=True, host="127.0.0.1", port=8051)


if __name__ == "__main__":
    main()
