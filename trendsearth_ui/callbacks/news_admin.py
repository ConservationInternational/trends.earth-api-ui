"""News admin callbacks for managing news items."""

import logging

from dash import ALL, Input, Output, State, dcc, html, no_update
import dash_bootstrap_components as dbc

from trendsearth_ui.config import get_api_base

logger = logging.getLogger(__name__)


def make_api_request(method, endpoint, token, api_environment=None, json_data=None):
    """Make an API request with authentication."""
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    api_base = get_api_base(api_environment or "production")
    url = f"{api_base}{endpoint}"

    if method == "GET":
        response = requests.get(url, headers=headers, timeout=30)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=json_data, timeout=30)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=json_data, timeout=30)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers, timeout=30)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    return response


def create_news_table(news_items):
    """Create a table displaying news items."""
    if not news_items:
        return html.Div(
            "No news items found.",
            className="text-muted text-center py-4",
        )

    # Table header
    header = html.Thead(
        html.Tr(
            [
                html.Th("", style={"width": "40px"}),  # Selection checkbox
                html.Th("Title"),
                html.Th("Type"),
                html.Th("Platforms"),
                html.Th("Roles"),
                html.Th("Priority"),
                html.Th("Active"),
                html.Th("Created"),
            ]
        )
    )

    # Table rows
    rows = []
    for item in news_items:
        platforms = ", ".join(item.get("target_platforms", []))
        roles = ", ".join(item.get("target_roles", [])) or "All"
        is_active = item.get("is_active", False)
        created_at = item.get("created_at", "")[:10] if item.get("created_at") else ""
        news_type = item.get("news_type", "info")

        # Type badge color
        type_colors = {
            "info": "primary",
            "warning": "warning",
            "error": "danger",
            "success": "success",
        }

        row = html.Tr(
            [
                html.Td(
                    dbc.RadioButton(
                        id={"type": "news-select-radio", "index": item["id"]},
                        value=False,
                    )
                ),
                html.Td(item.get("title", "Untitled")),
                html.Td(
                    dbc.Badge(
                        news_type.capitalize(),
                        color=type_colors.get(news_type, "secondary"),
                    )
                ),
                html.Td(platforms or "All"),
                html.Td(roles),
                html.Td(str(item.get("priority", 0))),
                html.Td(
                    dbc.Badge(
                        "Active" if is_active else "Inactive",
                        color="success" if is_active else "secondary",
                    )
                ),
                html.Td(created_at),
            ],
            id={"type": "news-row", "index": item["id"]},
            style={"cursor": "pointer"},
        )
        rows.append(row)

    body = html.Tbody(rows)

    return dbc.Table(
        [header, body],
        striped=True,
        hover=True,
        responsive=True,
        className="mt-3",
    )


def register_callbacks(app):
    """Register news admin callbacks with the app."""
    from dash import callback_context

    @app.callback(
        Output("admin-news-table", "children"),
        Output("admin-news-alert", "children", allow_duplicate=True),
        Output("admin-news-alert", "color", allow_duplicate=True),
        Output("admin-news-alert", "is_open", allow_duplicate=True),
        Input("admin-news-load-interval", "n_intervals"),
        Input("admin-refresh-news-btn", "n_clicks"),
        Input("admin-news-save-btn", "n_clicks"),
        Input("admin-news-delete-confirm-btn", "n_clicks"),
        Input("token-store", "data"),
        State("api-environment-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def load_admin_news_items(
        _n_intervals, _refresh_clicks, _save_clicks, _delete_clicks, token, api_environment
    ):
        """Load news items for admin management."""
        logger.info(
            f"load_admin_news_items called: intervals={_n_intervals}, "
            f"refresh={_refresh_clicks}, save={_save_clicks}, delete={_delete_clicks}, "
            f"token_exists={bool(token)}, api_env={api_environment}"
        )
        # Must have a token to load news
        if not token:
            logger.warning("No token provided to load_admin_news_items")
            return "Please log in to manage news.", "", "warning", True

        try:
            # Fetch all news including inactive
            logger.info(f"Fetching admin news from API (env={api_environment})...")
            response = make_api_request(
                "GET", "/admin/news?include_inactive=true", token, api_environment=api_environment
            )
            logger.info(f"Admin news API response: status={response.status_code}")

            if response.status_code == 200:
                data = response.json()
                news_items = data.get("data", [])
                logger.info(f"Successfully loaded {len(news_items)} news items")
                table = create_news_table(news_items)
                return table, no_update, no_update, no_update
            elif response.status_code == 401:
                return (
                    "Session expired. Please log in again.",
                    "Session expired. Please log in again.",
                    "warning",
                    True,
                )
            elif response.status_code == 403:
                return (
                    "Access denied. Admin privileges required.",
                    "Access denied. Admin privileges required.",
                    "danger",
                    True,
                )
            else:
                error_msg = f"Failed to load news: {response.status_code}"
                return error_msg, error_msg, "danger", True

        except Exception as e:
            logger.exception(f"Exception in load_admin_news_items: {e}")
            error_msg = f"Error loading news: {str(e)}"
            return error_msg, error_msg, "danger", True

    @app.callback(
        Output("admin-selected-news-id", "data"),
        Output("admin-edit-news-btn", "disabled"),
        Output("admin-delete-news-btn", "disabled"),
        Input({"type": "news-select-radio", "index": ALL}, "value"),
        State({"type": "news-select-radio", "index": ALL}, "id"),
    )
    def handle_news_selection(values, ids):
        """Handle news item selection."""
        if not values or not ids:
            return None, True, True

        # Find the selected item
        for i, value in enumerate(values):
            if value:
                return ids[i]["index"], False, False

        return None, True, True

    @app.callback(
        Output("admin-news-modal", "is_open"),
        Output("admin-news-modal-title", "children"),
        Output("admin-news-title", "value"),
        Output("admin-news-message", "value"),
        Output("admin-news-link-url", "value"),
        Output("admin-news-link-text", "value"),
        Output("admin-news-platforms", "value"),
        Output("admin-news-roles", "value"),
        Output("admin-news-type", "value"),
        Output("admin-news-priority", "value"),
        Output("admin-news-min-version", "value"),
        Output("admin-news-max-version", "value"),
        Output("admin-news-start-date", "date"),
        Output("admin-news-end-date", "date"),
        Output("admin-news-is-active", "value"),
        Input("admin-create-news-btn", "n_clicks"),
        Input("admin-edit-news-btn", "n_clicks"),
        Input("admin-news-cancel-btn", "n_clicks"),
        Input("admin-news-save-btn", "n_clicks"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        State("api-environment-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_news_modal(  # noqa: ARG001
        _create_clicks,
        _edit_clicks,
        _cancel_clicks,
        _save_clicks,
        selected_id,
        token,
        api_environment,  # noqa: ARG001 - used conditionally in edit branch
    ):
        """Toggle the news create/edit modal."""
        ctx = callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Close modal on cancel or successful save
        if triggered_id in ("admin-news-cancel-btn", "admin-news-save-btn"):
            return (
                False,  # is_open
                no_update,
                "",  # title
                "",  # message
                "",  # link_url
                "",  # link_text
                ["qgis_plugin", "web", "api_ui"],  # platforms
                [],  # roles (empty = all users)
                "info",  # type
                0,  # priority
                "",  # min_version
                "",  # max_version
                None,  # start_date
                None,  # end_date
                True,  # is_active
            )

        # Open modal for create
        if triggered_id == "admin-create-news-btn":
            return (
                True,  # is_open
                "Create News Item",  # title
                "",  # title
                "",  # message
                "",  # link_url
                "",  # link_text
                ["qgis_plugin", "web", "api_ui"],  # platforms
                [],  # roles (empty = all users)
                "info",  # type
                0,  # priority
                "",  # min_version
                "",  # max_version
                None,  # start_date
                None,  # end_date
                True,  # is_active
            )

        # Open modal for edit - need to fetch news item data
        if triggered_id == "admin-edit-news-btn" and selected_id and token:
            try:
                response = make_api_request(
                    "GET",
                    f"/admin/news/{selected_id}",
                    token,
                    api_environment=api_environment,
                )
                if response.status_code == 200:
                    item = response.json()
                    return (
                        True,  # is_open
                        "Edit News Item",  # title
                        item.get("title", ""),
                        item.get("message", ""),
                        item.get("link_url", "") or "",
                        item.get("link_text", "") or "",
                        item.get("target_platforms", ["qgis_plugin", "web", "api_ui"]),
                        item.get("target_roles", []),
                        item.get("news_type", "info"),
                        item.get("priority", 0),
                        item.get("min_version", "") or "",
                        item.get("max_version", "") or "",
                        item.get("publish_at"),  # API returns publish_at
                        item.get("expires_at"),  # API returns expires_at
                        item.get("is_active", True),
                    )
            except Exception:
                pass

        return (no_update,) * 15

    @app.callback(
        Output("admin-news-preview", "children"),
        Input("admin-news-message", "value"),
        prevent_initial_call=True,
    )
    def update_markdown_preview(message):
        """Update the Markdown preview."""
        if not message:
            return html.Div("Preview will appear here...", className="text-muted")

        try:
            # Use dcc.Markdown for rendering - it has built-in markdown support
            return dcc.Markdown(
                message,
                style={"lineHeight": "1.5"},
            )
        except Exception:
            return html.Div(message, style={"whiteSpace": "pre-wrap"})

    @app.callback(
        Output("admin-news-modal-alert", "children"),
        Output("admin-news-modal-alert", "color"),
        Output("admin-news-modal-alert", "is_open"),
        Output("admin-news-alert", "children"),
        Output("admin-news-alert", "color"),
        Output("admin-news-alert", "is_open"),
        Input("admin-news-save-btn", "n_clicks"),
        State("admin-news-modal-title", "children"),
        State("admin-news-title", "value"),
        State("admin-news-message", "value"),
        State("admin-news-link-url", "value"),
        State("admin-news-link-text", "value"),
        State("admin-news-platforms", "value"),
        State("admin-news-roles", "value"),
        State("admin-news-type", "value"),
        State("admin-news-priority", "value"),
        State("admin-news-min-version", "value"),
        State("admin-news-max-version", "value"),
        State("admin-news-start-date", "date"),
        State("admin-news-end-date", "date"),
        State("admin-news-is-active", "value"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        State("api-environment-store", "data"),
        prevent_initial_call=True,
    )
    def save_news_item(
        _n_clicks,
        modal_title,
        title,
        message,
        link_url,
        link_text,
        platforms,
        roles,
        news_type,
        priority,
        min_version,
        max_version,
        start_date,
        end_date,
        is_active,
        selected_id,
        token,
        api_environment,
    ):
        """Save a news item (create or update)."""
        if not token:
            return (
                "Please log in first.",
                "warning",
                True,
                no_update,
                no_update,
                no_update,
            )

        # Validate required fields
        if not title or not title.strip():
            return (
                "Title is required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not message or not message.strip():
            return (
                "Message is required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not platforms:
            return (
                "At least one target platform is required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        # Build request data - store raw markdown, clients will render it
        data = {
            "title": title.strip(),
            "message": message,  # Keep as markdown, clients render it
            "target_platforms": ",".join(platforms) if platforms else "qgis_plugin,web,api_ui",
            "target_roles": ",".join(roles) if roles else None,
            "news_type": news_type,
            "priority": int(priority) if priority else 0,
            "is_active": bool(is_active),
        }

        # Add optional fields
        if link_url:
            data["link_url"] = link_url.strip()
        if link_text:
            data["link_text"] = link_text.strip()
        if min_version:
            data["min_version"] = min_version.strip()
        if max_version:
            data["max_version"] = max_version.strip()
        if start_date:
            data["publish_at"] = start_date
        if end_date:
            data["expires_at"] = end_date

        try:
            is_edit = modal_title == "Edit News Item"
            if is_edit and selected_id:
                response = make_api_request(
                    "PUT",
                    f"/admin/news/{selected_id}",
                    token,
                    api_environment=api_environment,
                    json_data=data,
                )
            else:
                response = make_api_request(
                    "POST",
                    "/admin/news",
                    token,
                    api_environment=api_environment,
                    json_data=data,
                )

            if response.status_code in (200, 201):
                action = "updated" if is_edit else "created"
                return (
                    no_update,
                    no_update,
                    False,
                    f"News item {action} successfully!",
                    "success",
                    True,
                )
            elif response.status_code == 401:
                return (
                    "Session expired. Please log in again.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                )
            elif response.status_code == 403:
                return (
                    "Access denied. Admin privileges required.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                )
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", f"Error: {response.status_code}")
                return (
                    error_msg,
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                )

        except Exception as e:
            return (
                f"Error saving news item: {str(e)}",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        Output("admin-news-delete-modal", "is_open"),
        Input("admin-delete-news-btn", "n_clicks"),
        Input("admin-news-delete-cancel-btn", "n_clicks"),
        Input("admin-news-delete-confirm-btn", "n_clicks"),
        State("admin-selected-news-id", "data"),
        prevent_initial_call=True,
    )
    def toggle_delete_modal(_delete_clicks, _cancel_clicks, _confirm_clicks, selected_id):
        """Toggle the delete confirmation modal."""
        ctx = callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        return triggered_id == "admin-delete-news-btn" and selected_id is not None

    @app.callback(
        Output("admin-news-alert", "children", allow_duplicate=True),
        Output("admin-news-alert", "color", allow_duplicate=True),
        Output("admin-news-alert", "is_open", allow_duplicate=True),
        Input("admin-news-delete-confirm-btn", "n_clicks"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        State("api-environment-store", "data"),
        prevent_initial_call=True,
    )
    def delete_news_item(_n_clicks, selected_id, token, api_environment):
        """Delete a news item."""
        if not token:
            return "Please log in first.", "warning", True

        if not selected_id:
            return "No news item selected.", "warning", True

        try:
            response = make_api_request(
                "DELETE",
                f"/admin/news/{selected_id}",
                token,
                api_environment=api_environment,
            )

            if response.status_code in (200, 204):
                return "News item deleted successfully!", "success", True
            elif response.status_code == 401:
                return "Session expired. Please log in again.", "warning", True
            elif response.status_code == 403:
                return "Access denied. Admin privileges required.", "danger", True
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", f"Error: {response.status_code}")
                return error_msg, "danger", True

        except Exception as e:
            return f"Error deleting news item: {str(e)}", "danger", True
