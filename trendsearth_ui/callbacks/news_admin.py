"""News admin callbacks for managing news items."""

import logging
import time

from dash import Input, Output, State, dcc, html, no_update

from trendsearth_ui.config import get_api_base
from trendsearth_ui.i18n import gettext as _

logger = logging.getLogger(__name__)


def make_api_request(method, endpoint, token, api_environment=None, json_data=None):
    """Make an API request with authentication."""
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    api_base = get_api_base(api_environment or "production")
    url = f"{api_base}{endpoint}"
    
    logger.info(f"[make_api_request] {method} {url}")

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


def _format_news_rows(news_items):
    """Format news items for AG Grid display."""
    rows = []
    for item in news_items:
        platforms = ", ".join(item.get("target_platforms", [])) or "All"
        created_at = item.get("created_at", "")[:10] if item.get("created_at") else ""
        start_date = item.get("start_date", "")[:10] if item.get("start_date") else ""
        end_date = item.get("end_date", "")[:10] if item.get("end_date") else ""

        rows.append(
            {
                "id": item.get("id"),
                "title": item.get("title", "Untitled"),
                "news_type": item.get("news_type", "announcement"),
                "platforms_display": platforms,
                "priority": item.get("priority", 0),
                "is_active": item.get("is_active", False),
                "created_at": created_at,
                "message": item.get("message", ""),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return rows


def register_callbacks(app):
    """Register news admin callbacks with the app."""
    from dash import callback_context

    @app.callback(
        Output("admin-news-table", "getRowsResponse"),
        Output("admin-news-table-state", "data"),
        Input("admin-news-table", "getRowsRequest"),
        State("token-store", "data"),
        State("role-store", "data"),
        prevent_initial_call=False,
    )
    def load_admin_news_items(_request, token, role):
        """Load news items for AG Grid."""
        # Must have a token and admin role to load news
        if not token or role not in ("ADMIN", "SUPERADMIN"):
            return {"rowData": [], "rowCount": 0}, {}

        try:
            # Fetch all news including inactive
            response = make_api_request("GET", "/admin/news?include_inactive=true", token)

            if response.status_code == 200:
                data = response.json()
                news_items = data.get("data", [])
                rows = _format_news_rows(news_items)
                return {"rowData": rows, "rowCount": len(rows)}, {}
            else:
                return {"rowData": [], "rowCount": 0}, {}

        except Exception:
            return {"rowData": [], "rowCount": 0}, {}

    @app.callback(
        Output("admin-news-table", "getRowsResponse", allow_duplicate=True),
        Output("admin-news-table-state", "data", allow_duplicate=True),
        Input("admin-refresh-news-btn", "n_clicks"),
        Input("news-refresh-trigger", "data"),
        State("token-store", "data"),
        State("role-store", "data"),
        prevent_initial_call=True,
    )
    def refresh_admin_news_items(_refresh_clicks, _trigger, token, role):
        """Refresh news items after actions."""
        if not token or role not in ("ADMIN", "SUPERADMIN"):
            return no_update, no_update

        try:
            response = make_api_request("GET", "/admin/news?include_inactive=true", token)
            if response.status_code == 200:
                data = response.json()
                news_items = data.get("data", [])
                rows = _format_news_rows(news_items)
                return {"rowData": rows, "rowCount": len(rows)}, {}
        except Exception:
            pass

        return no_update, no_update

    @app.callback(
        Output("admin-selected-news-id", "data"),
        Output("admin-edit-news-btn", "disabled"),
        Output("admin-delete-news-btn", "disabled"),
        Input("admin-news-table", "selectedRows"),
        prevent_initial_call=True,
    )
    def handle_news_selection(selected_rows):
        """Handle news item selection from AG Grid."""
        if not selected_rows or len(selected_rows) == 0:
            return None, True, True

        # Get the selected item ID
        selected_id = selected_rows[0].get("id")
        return selected_id, False, False

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
        Output("admin-selected-news-id", "data", allow_duplicate=True),
        Input("admin-create-news-btn", "n_clicks"),
        Input("admin-edit-news-btn", "n_clicks"),
        Input("admin-news-cancel-btn", "n_clicks"),
        Input("admin-news-save-btn", "n_clicks"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_news_modal(
        _create_clicks,
        _edit_clicks,
        _cancel_clicks,
        _save_clicks,
        selected_id,
        token,
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
                "announcement",  # type
                0,  # priority
                "",  # min_version
                "",  # max_version
                None,  # start_date
                None,  # end_date
                True,  # is_active
                None,  # Clear selected_id
            )

        # Open modal for create
        if triggered_id == "admin-create-news-btn":
            return (
                True,  # is_open
                _("Create News Item"),  # title
                "",  # title
                "",  # message
                "",  # link_url
                "",  # link_text
                ["qgis_plugin", "web", "api_ui"],  # platforms
                [],  # roles (empty = all users)
                "announcement",  # type
                0,  # priority
                "",  # min_version
                "",  # max_version
                None,  # start_date
                None,  # end_date
                True,  # is_active
                None,  # Clear selected_id for create
            )

        # Open modal for edit - need to fetch news item data
        if triggered_id == "admin-edit-news-btn" and selected_id and token:
            try:
                response = make_api_request("GET", f"/admin/news/{selected_id}", token)
                if response.status_code == 200:
                    data = response.json()
                    item = data.get("data", data)  # Handle both wrapped and unwrapped
                    logger.info(
                        f"[toggle_news_modal] Loaded item: is_active={item.get('is_active')}"
                    )
                    # Parse dates - API returns publish_at/expires_at as ISO strings
                    start_date = item.get("publish_at")
                    end_date = item.get("expires_at")
                    # Extract just the date part if present (YYYY-MM-DD)
                    if start_date and "T" in start_date:
                        start_date = start_date.split("T")[0]
                    if end_date and "T" in end_date:
                        end_date = end_date.split("T")[0]
                    return (
                        True,  # is_open
                        _("Edit News Item"),  # title
                        item.get("title", ""),
                        item.get("message", ""),
                        item.get("link_url", "") or "",
                        item.get("link_text", "") or "",
                        item.get("target_platforms", ["qgis_plugin", "web", "api_ui"]),
                        item.get("target_roles", []),
                        item.get("news_type", "announcement"),
                        item.get("priority", 0),
                        item.get("min_version", "") or "",
                        item.get("max_version", "") or "",
                        start_date,
                        end_date,
                        item.get("is_active", True),
                        selected_id,  # Keep selected_id for edit
                    )
            except Exception as e:
                logger.error(f"[toggle_news_modal] Error loading item: {e}")
                pass

        return (no_update,) * 16

    @app.callback(
        Output("admin-news-preview", "children"),
        Input("admin-news-message", "value"),
        prevent_initial_call=True,
    )
    def update_markdown_preview(message):
        """Update the Markdown preview."""
        if not message:
            return html.Div(_("Preview will appear here..."), className="text-muted")

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
        Output("news-refresh-trigger", "data"),
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
    ):
        """Save a news item (create or update)."""
        logger.info(
            f"[save_news_item] is_active value received: {is_active} (type: {type(is_active)})"
        )
        if not token:
            return (
                _("Please log in first."),
                "warning",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        # Validate required fields
        if not title or not title.strip():
            return (
                _("Title is required."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if not message or not message.strip():
            return (
                _("Message is required."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if not platforms:
            return (
                _("At least one target platform is required."),
                "danger",
                True,
                no_update,
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
        # API uses publish_at/expires_at, UI uses start_date/end_date
        if start_date:
            data["publish_at"] = start_date
        if end_date:
            data["expires_at"] = end_date

        logger.info(f"[save_news_item] Sending data to API: {data}")
        logger.info(
            f"[save_news_item] modal_title={modal_title!r}, selected_id={selected_id!r}"
        )

        try:
            # Use selected_id to determine create vs update (more reliable than title comparison)
            is_edit = bool(selected_id)
            if is_edit:
                response = make_api_request(
                    "PUT", f"/admin/news/{selected_id}", token, json_data=data
                )
            else:
                response = make_api_request("POST", "/admin/news", token, json_data=data)

            logger.info(
                f"[save_news_item] API response: {response.status_code} - {response.text[:200] if response.text else 'empty'}"
            )

            if response.status_code in (200, 201):
                action = _("updated") if is_edit else _("created")
                return (
                    no_update,
                    no_update,
                    False,
                    _("News item {action} successfully!").format(action=action),
                    "success",
                    True,
                    time.time(),  # Trigger refresh
                )
            elif response.status_code == 401:
                return (
                    _("Session expired. Please log in again."),
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            elif response.status_code == 403:
                return (
                    _("Access denied. Admin privileges required."),
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "message", _("Error: {status}").format(status=response.status_code)
                )
                return (
                    error_msg,
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        except Exception as e:
            return (
                _("Error saving news item: {error}").format(error=str(e)),
                "danger",
                True,
                no_update,
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
        Output("news-refresh-trigger", "data", allow_duplicate=True),
        Input("admin-news-delete-confirm-btn", "n_clicks"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def delete_news_item(_n_clicks, selected_id, token):
        """Delete a news item."""
        if not token:
            return _("Please log in first."), "warning", True, no_update

        if not selected_id:
            return _("No news item selected."), "warning", True, no_update

        try:
            response = make_api_request("DELETE", f"/admin/news/{selected_id}", token)

            if response.status_code in (200, 204):
                return _("News item deleted successfully!"), "success", True, time.time()
            elif response.status_code == 401:
                return _("Session expired. Please log in again."), "warning", True, no_update
            elif response.status_code == 403:
                return _("Access denied. Admin privileges required."), "danger", True, no_update
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get(
                    "message", _("Error: {status}").format(status=response.status_code)
                )
                return error_msg, "danger", True, no_update

        except Exception as e:
            return (
                _("Error deleting news item: {error}").format(error=str(e)),
                "danger",
                True,
                no_update,
            )

    # Translation languages supported
    TRANSLATION_LANGUAGES = ["ar", "es", "fa", "fr", "pt", "ru", "sw", "zh"]

    @app.callback(
        [Output(f"admin-news-trans-title-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [Output(f"admin-news-trans-message-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [Output(f"admin-news-trans-link-text-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [
            Output(f"admin-news-trans-is-machine-{lang}", "value") for lang in TRANSLATION_LANGUAGES
        ],
        Input("admin-news-modal", "is_open"),
        State("admin-news-modal-title", "children"),
        State("admin-selected-news-id", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_translations(is_open, modal_title, selected_id, token):
        """Load existing translations when editing a news item."""
        # Initialize empty values for all fields
        empty_result = [""] * (len(TRANSLATION_LANGUAGES) * 3) + [False] * len(
            TRANSLATION_LANGUAGES
        )

        if not is_open:
            return empty_result

        # Only load translations when editing
        if modal_title != _("Edit News Item") or not selected_id or not token:
            return empty_result

        try:
            response = make_api_request(
                "GET", f"/admin/news/{selected_id}?include_translations=true", token
            )
            if response.status_code == 200:
                item = response.json()
                translations = item.get("translations", {})

                titles = []
                messages = []
                link_texts = []
                is_machine = []

                for lang in TRANSLATION_LANGUAGES:
                    trans = translations.get(lang, {})
                    titles.append(trans.get("title", "") or "")
                    messages.append(trans.get("message", "") or "")
                    link_texts.append(trans.get("link_text", "") or "")
                    is_machine.append(trans.get("is_machine_translated", False))

                return titles + messages + link_texts + is_machine

        except Exception as e:
            logger.error(f"Error loading translations: {e}")

        return empty_result

    @app.callback(
        [
            Output(f"admin-news-trans-title-{lang}", "value", allow_duplicate=True)
            for lang in TRANSLATION_LANGUAGES
        ]
        + [
            Output(f"admin-news-trans-message-{lang}", "value", allow_duplicate=True)
            for lang in TRANSLATION_LANGUAGES
        ]
        + [
            Output(f"admin-news-trans-link-text-{lang}", "value", allow_duplicate=True)
            for lang in TRANSLATION_LANGUAGES
        ]
        + [
            Output(f"admin-news-trans-is-machine-{lang}", "value", allow_duplicate=True)
            for lang in TRANSLATION_LANGUAGES
        ]
        + [
            Output("admin-news-translate-alert", "children"),
            Output("admin-news-translate-alert", "color"),
            Output("admin-news-translate-alert", "is_open"),
        ],
        Input("admin-news-translate-all-btn", "n_clicks"),
        State("admin-news-title", "value"),
        State("admin-news-message", "value"),
        State("admin-news-link-text", "value"),
        prevent_initial_call=True,
    )
    def machine_translate_all(_n_clicks, title, message, link_text):
        """Machine translate English content to all languages."""
        from trendsearth_ui.utils.translation_service import (
            is_translation_available,
            translate_to_all_languages,
        )

        # Check if translation service is available
        if not is_translation_available():
            empty_result = [no_update] * (len(TRANSLATION_LANGUAGES) * 4)
            return empty_result + [
                _(
                    "Translation service not configured. Please set GOOGLE_TRANSLATE_CREDENTIALS environment variable."
                ),
                "warning",
                True,
            ]

        # Check for content to translate
        if not (title or message or link_text):
            empty_result = [no_update] * (len(TRANSLATION_LANGUAGES) * 4)
            return empty_result + [
                _(
                    "No English content to translate. Please add title, message, or link text first."
                ),
                "warning",
                True,
            ]

        try:
            # Translate to all languages
            all_translations = translate_to_all_languages(title, message, link_text)

            titles = []
            messages = []
            link_texts = []
            is_machine = []

            for lang in TRANSLATION_LANGUAGES:
                trans = all_translations.get(lang, {})
                titles.append(trans.get("title", "") or "")
                messages.append(trans.get("message", "") or "")
                link_texts.append(trans.get("link_text", "") or "")
                is_machine.append(True)  # Mark all as machine translated

            return (
                titles
                + messages
                + link_texts
                + is_machine
                + [
                    _("Successfully translated to {count} languages!").format(
                        count=len(TRANSLATION_LANGUAGES)
                    ),
                    "success",
                    True,
                ]
            )

        except Exception as e:
            logger.error(f"Error in machine translation: {e}")
            empty_result = [no_update] * (len(TRANSLATION_LANGUAGES) * 4)
            return empty_result + [
                _("Translation error: {error}").format(error=str(e)),
                "danger",
                True,
            ]

    @app.callback(
        Output("admin-news-translations-store", "data"),
        Input("admin-news-save-btn", "n_clicks"),
        [State(f"admin-news-trans-title-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [State(f"admin-news-trans-message-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [State(f"admin-news-trans-link-text-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [State(f"admin-news-trans-is-machine-{lang}", "value") for lang in TRANSLATION_LANGUAGES]
        + [
            State("admin-selected-news-id", "data"),
            State("token-store", "data"),
            State("admin-news-modal-title", "children"),
        ],
        prevent_initial_call=True,
    )
    def save_translations(
        _n_clicks,
        *args,
    ):
        """Save translations after the news item is saved."""
        # Unpack arguments
        num_langs = len(TRANSLATION_LANGUAGES)
        titles = args[:num_langs]
        messages = args[num_langs : num_langs * 2]
        link_texts = args[num_langs * 2 : num_langs * 3]
        is_machines = args[num_langs * 3 : num_langs * 4]
        selected_id = args[-3]
        token = args[-2]
        modal_title = args[-1]

        if not token or not selected_id:
            return no_update

        # Only save for edit (create needs ID first, handled separately)
        if modal_title != _("Edit News Item"):
            return no_update

        try:
            # Build translations dict
            translations = {}
            for i, lang in enumerate(TRANSLATION_LANGUAGES):
                # Only include if there's content
                if titles[i] or messages[i] or link_texts[i]:
                    translations[lang] = {
                        "title": titles[i] or None,
                        "message": messages[i] or None,
                        "link_text": link_texts[i] or None,
                        "is_machine_translated": bool(is_machines[i]),
                    }

            if translations:
                response = make_api_request(
                    "PUT",
                    f"/admin/news/{selected_id}/translations",
                    token,
                    json_data={"translations": translations},
                )

                if response.status_code not in (200, 201):
                    logger.error(
                        f"Error saving translations: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            logger.error(f"Error saving translations: {e}")

        return no_update
