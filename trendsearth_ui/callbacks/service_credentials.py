"""Service credentials management callbacks."""

import logging

from dash import ALL, Input, Output, State, ctx, html, no_update
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

SERVICE_CREDS_ENDPOINT = "/oauth/clients"
_API_TIMEOUT = 15  # seconds for service credentials API calls


def _extract_error_msg(resp, default="An unexpected error occurred."):
    """Extract a human-readable error message from an API response."""
    try:
        error_data = resp.json()
        return error_data.get("detail", error_data.get("msg", default))
    except Exception:
        return default


def _build_credentials_table(clients):
    """Build a Bootstrap table from a list of service client dicts."""
    if not clients:
        return dbc.Alert("No service credentials found. Create one to get started.", color="info")

    rows = []
    for client in clients:
        name = client.get("name", "—")
        client_id = client.get("client_id", "—")
        secret_prefix = client.get("secret_prefix", "")
        scopes = client.get("scopes") or "full access"
        created_at = client.get("created_at", "—")
        last_used_at = client.get("last_used_at") or "Never"
        expires_at = client.get("expires_at") or "Never"
        db_id = str(client.get("id", ""))

        # Trim datetime strings to a readable format
        def _fmt(dt):
            if dt and dt not in ("Never", "—"):
                try:
                    return dt[:19].replace("T", " ")
                except Exception:
                    pass
            return dt

        created_at = _fmt(created_at)
        last_used_at = _fmt(last_used_at)
        expires_at = _fmt(expires_at)

        rows.append(
            html.Tr(
                [
                    html.Td(name),
                    html.Td(
                        html.Code(client_id, style={"fontSize": "11px"}),
                        style={
                            "maxWidth": "220px",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    html.Td(
                        html.Code(f"…{secret_prefix}", style={"fontSize": "11px"})
                        if secret_prefix
                        else "—"
                    ),
                    html.Td(scopes, style={"fontSize": "12px"}),
                    html.Td(created_at, style={"fontSize": "12px", "whiteSpace": "nowrap"}),
                    html.Td(last_used_at, style={"fontSize": "12px", "whiteSpace": "nowrap"}),
                    html.Td(expires_at, style={"fontSize": "12px", "whiteSpace": "nowrap"}),
                    html.Td(
                        dbc.Button(
                            "Revoke",
                            id={"type": "service-creds-revoke-btn", "index": db_id},
                            color="danger",
                            outline=True,
                            size="sm",
                        )
                    ),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Name"),
                        html.Th("Client ID"),
                        html.Th("Secret"),
                        html.Th("Scopes"),
                        html.Th("Created"),
                        html.Th("Last Used"),
                        html.Th("Expires"),
                        html.Th("Action"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mt-2",
    )


def register_callbacks(app):
    """Register service credentials callbacks."""

    @app.callback(
        Output("service-creds-table-container", "children"),
        [
            Input("token-store", "data"),
            Input("service-creds-refresh-btn", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def load_service_credentials(token, _refresh):
        """Load and display service credentials."""
        if not token:
            return html.Div("Please log in to manage service credentials.", className="text-muted")

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(SERVICE_CREDS_ENDPOINT, token)
            if resp.status_code == 200:
                clients = resp.json().get("data", [])
                return _build_credentials_table(clients)
            elif resp.status_code == 404:
                return _build_credentials_table([])
            else:
                logger.error("Service credentials API error: %s", resp.status_code)
                return dbc.Alert("Failed to load service credentials.", color="danger")
        except Exception as e:
            logger.exception("Error loading service credentials: %s", e)
            return dbc.Alert("Error loading service credentials.", color="danger")

    @app.callback(
        Output("service-creds-create-modal", "is_open"),
        [
            Input("service-creds-create-btn", "n_clicks"),
            Input("service-creds-create-cancel-btn", "n_clicks"),
            Input("service-creds-create-confirm-btn", "n_clicks"),
        ],
        State("service-creds-create-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_create_modal(_open, _cancel, _confirm, is_open):
        """Open or close the create credential modal."""
        trigger = ctx.triggered_id
        if trigger == "service-creds-create-btn":
            return True
        if trigger in ("service-creds-create-cancel-btn", "service-creds-create-confirm-btn"):
            return False
        return is_open

    @app.callback(
        [
            Output("service-creds-new-client-id", "value"),
            Output("service-creds-new-secret", "value"),
            Output("service-creds-secret-modal", "is_open"),
            Output("service-creds-create-alert", "children"),
            Output("service-creds-create-alert", "color"),
            Output("service-creds-create-alert", "is_open"),
            Output("service-creds-name-input", "value"),
            Output("service-creds-scopes-input", "value"),
            Output("service-creds-expires-input", "value"),
        ],
        Input("service-creds-create-confirm-btn", "n_clicks"),
        [
            State("service-creds-name-input", "value"),
            State("service-creds-scopes-input", "value"),
            State("service-creds-expires-input", "value"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def create_service_credential(n_clicks, name, scopes, expires_in_days, token):
        """Create a new service credential and show the one-time secret."""
        if not n_clicks or not token:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if not name or not name.strip():
            return (
                no_update,
                no_update,
                no_update,
                "Name is required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        body = {"name": name.strip()}
        if scopes and scopes.strip():
            body["scopes"] = scopes.strip()
        if expires_in_days is not None:
            try:
                days = int(expires_in_days)
                if days < 1:
                    raise ValueError
                body["expires_in_days"] = days
            except (TypeError, ValueError):
                return (
                    no_update,
                    no_update,
                    no_update,
                    "Expires in days must be a positive integer.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                )

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                SERVICE_CREDS_ENDPOINT,
                token,
                method="POST",
                json=body,
                timeout=_API_TIMEOUT,
            )

            if resp.status_code in (200, 201):
                data = resp.json().get("data", {})
                client_id = data.get("client_id", "")
                client_secret = data.get("client_secret", "")
                # Clear form and open secret modal
                return client_id, client_secret, True, no_update, no_update, False, "", "", None
            else:
                error_msg = _extract_error_msg(resp, "Failed to create credential.")
                return (
                    no_update,
                    no_update,
                    no_update,
                    error_msg,
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                )
        except Exception as e:
            logger.exception("Error creating service credential: %s", e)
            return (
                no_update,
                no_update,
                no_update,
                f"Network error: {e}",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        Output("service-creds-secret-modal", "is_open", allow_duplicate=True),
        Input("service-creds-secret-close-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_secret_modal(n_clicks):
        """Close the one-time secret modal."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("service-creds-revoke-modal", "is_open"),
            Output("service-creds-revoke-target", "data"),
            Output("service-creds-revoke-name", "children"),
        ],
        Input({"type": "service-creds-revoke-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_revoke_modal(n_clicks_list):
        """Open revoke confirmation modal for the clicked credential."""
        if not any(n for n in (n_clicks_list or []) if n):
            return no_update, no_update, no_update

        trigger = ctx.triggered_id
        if trigger and isinstance(trigger, dict):
            db_id = trigger.get("index", "")
            return True, db_id, f"Credential ID: {db_id}"
        return no_update, no_update, no_update

    @app.callback(
        Output("service-creds-revoke-modal", "is_open", allow_duplicate=True),
        Input("service-creds-revoke-cancel-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_revoke_modal(n_clicks):
        """Close revoke modal on cancel."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("service-creds-revoke-modal", "is_open", allow_duplicate=True),
            Output("service-creds-alert", "children"),
            Output("service-creds-alert", "color"),
            Output("service-creds-alert", "is_open"),
            Output("service-creds-table-container", "children", allow_duplicate=True),
        ],
        Input("service-creds-revoke-confirm-btn", "n_clicks"),
        [
            State("service-creds-revoke-target", "data"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def revoke_service_credential(n_clicks, db_id, token):
        """Revoke a service credential."""
        if not n_clicks or not db_id or not token:
            return no_update, no_update, no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                f"{SERVICE_CREDS_ENDPOINT}/{db_id}",
                token,
                method="DELETE",
                timeout=_API_TIMEOUT,
            )

            if resp.status_code == 200:
                # Refresh the table after revoking
                refresh_resp = make_authenticated_request(SERVICE_CREDS_ENDPOINT, token)
                if refresh_resp.status_code == 200:
                    clients = refresh_resp.json().get("data", [])
                    table = _build_credentials_table(clients)
                else:
                    table = no_update

                return False, "Credential revoked successfully.", "success", True, table
            else:
                error_msg = _extract_error_msg(resp, "Failed to revoke credential.")
                return False, error_msg, "danger", True, no_update
        except Exception as e:
            logger.exception("Error revoking service credential: %s", e)
            return False, f"Network error: {e}", "danger", True, no_update
