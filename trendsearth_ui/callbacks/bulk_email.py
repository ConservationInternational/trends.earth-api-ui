"""Bulk email manager callbacks.

All endpoints are SUPERADMIN-only on the backend; the UI shows the tab only
when role == "SUPERADMIN" and simply forwards the JWT for every request.
"""

import base64
import logging
import xml.dom.minidom

from dash import ALL, Input, Output, State, callback_context, no_update

from ..config import DEFAULT_PAGE_SIZE
from ..email_templates import (
    _DEFAULT_IMPACT_ITEMS,
    _DEFAULT_NEWS_ITEMS,
    render_engagement,
    render_news,
    render_system_update,
)
from ..utils import make_authenticated_request
from ..utils.aggrid import build_aggrid_request_params

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(token: str, method: str, path: str, **kwargs):
    """Thin wrapper around make_authenticated_request for bulk email endpoints."""
    return make_authenticated_request(path, token, method=method, **kwargs)


_PREVIEW_ALLOWED_SORT_COLUMNS = {
    "email",
    "name",
    "role",
    "email_verified",
    "created_at",
    "last_activity_at",
}


def _ok_rows(resp):
    """Return list of dicts from a paginated or list API response, or []."""
    try:
        body = resp.json()
        if isinstance(body, list):
            return body
        return body.get("data", []) or []
    except Exception:
        return []


def _fetch_preview_page(token, filter_criteria, params):
    """Fetch one page of preview recipients."""
    try:
        resp = _api(
            token,
            "POST",
            "/bulk-email/recipient-list/preview",
            json={"filter_criteria": filter_criteria, **params},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {}) or {}
            return data.get("sample", []) or [], data.get("total", 0)
    except Exception:
        logger.exception("Failed to fetch preview page")
    return [], 0


def _prettify_html(raw: str) -> str:
    """Return a pretty-printed version of *raw* HTML, falling back to raw."""
    try:
        pretty = xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")
        # toprettyxml adds an XML declaration; strip it
        lines = pretty.splitlines()
        if lines and lines[0].startswith("<?xml"):
            lines = lines[1:]
        return "\n".join(lines)
    except Exception:
        return raw


def _build_html_from_fields(
    template: str,
    *,
    news_issue_date: str = "",
    news_intro: str = "",
    news_highlight_title: str = "",
    news_highlight_body: str = "",
    news_highlight_image_url: str = "",
    news_items: list | None = None,
    news_cta_url: str = "",
    news_cta_label: str = "",
    engagement_intro: str = "",
    engagement_topic: str = "",
    engagement_description: str = "",
    engagement_btn_label: str = "",
    engagement_btn_url: str = "",
    sysupdate_date_time: str = "",
    sysupdate_intro: str = "",
    sysupdate_datetime_utc: str = "",
    sysupdate_duration: str = "",
    sysupdate_impact: str = "",
    impact_items: list | None = None,
) -> str:
    """Render the HTML email from structured field values."""
    if template == "news":
        return render_news(
            issue_date=news_issue_date or "[Month Year]",
            intro=news_intro or "",
            highlight_title=news_highlight_title or "Highlight",
            highlight_body=news_highlight_body or "",
            highlight_image_url=news_highlight_image_url or None,
            news_items=news_items or _DEFAULT_NEWS_ITEMS,
            cta_url=news_cta_url or None,
            cta_label=news_cta_label or "Visit Trends.Earth",
        )
    if template == "engagement":
        return render_engagement(
            intro=engagement_intro or "",
            topic=engagement_topic or "[Survey / Feedback Topic]",
            description=engagement_description or "",
            button_label=engagement_btn_label or "[Action Button Label]",
            button_url=engagement_btn_url or "#",
        )
    if template == "system_update":
        return render_system_update(
            date_time=sysupdate_date_time or "[Date & Time]",
            intro=sysupdate_intro or "",
            datetime_utc=sysupdate_datetime_utc or "[YYYY-MM-DD HH:MM UTC]",
            duration=sysupdate_duration or "[Estimated duration]",
            impact=sysupdate_impact or "[Services affected]",
            impact_items=impact_items or _DEFAULT_IMPACT_ITEMS,
        )
    return ""


# Number of static field values returned alongside each call that touches them
_N_NEWS_FIELDS = (
    7  # issue_date, intro, highlight_title, highlight_body, highlight_image_url, cta_url, cta_label
)
_N_ENG_FIELDS = 5  # intro, topic, description, btn_label, btn_url
_N_SYS_FIELDS = 5  # date_time, intro, datetime_utc, duration, impact

# Sentinel values (None means "don't touch")
_NO_UPDATE_NEWS = (no_update,) * _N_NEWS_FIELDS
_NO_UPDATE_ENG = (no_update,) * _N_ENG_FIELDS
_NO_UPDATE_SYS = (no_update,) * _N_SYS_FIELDS


def register_callbacks(app):
    """Register all bulk email callbacks."""

    # -----------------------------------------------------------------------
    # Load bulk email config (threshold info) when the tab becomes active
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-threshold-info", "children"),
        Input("bulk-email-tab-rendered", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_bulk_email_config(_rendered, token):
        if not token:
            return no_update
        try:
            resp = _api(token, "GET", "/bulk-email/config")
            if resp.status_code == 200:
                cfg = resp.json()
                max_r = cfg.get("max_recipients", "?")
                from_email = cfg.get("from_email", "")
                return (
                    f"Bulk emails with more than {max_r} recipients require a verification code. "
                    f"Emails sent from: {from_email}"
                )
        except Exception:
            logger.exception("Failed to load bulk email config")
        return ""

    # -----------------------------------------------------------------------
    # Preview button — store filter criteria and load first page
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-preview-grid", "getRowsResponse"),
            Output("bulk-email-preview-count", "children"),
            Output("bulk-email-preview-filter-store", "data"),
            Output("bulk-email-preview-source-label", "children"),
        ],
        Input("bulk-email-preview-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-rlist-roles", "value"),
            State("bulk-email-rlist-verified", "value"),
            State("bulk-email-rlist-min-created", "value"),
            State("bulk-email-rlist-max-created", "value"),
            State("bulk-email-rlist-min-activity", "value"),
            State("bulk-email-rlist-max-activity", "value"),
        ],
        prevent_initial_call=True,
    )
    def preview_recipient_group(
        _n, token, roles, verified, min_created, max_created, min_activity, max_activity
    ):
        if not token:
            return {"rowData": [], "rowCount": 0}, "", {}, ""
        filter_criteria = _build_filter_criteria(
            roles, verified, min_created, max_created, min_activity, max_activity
        )
        rows, total = _fetch_preview_page(
            token, filter_criteria, {"page": 1, "per_page": DEFAULT_PAGE_SIZE}
        )
        return {"rowData": rows, "rowCount": total}, f"{total} recipients", filter_criteria, ""

    # -----------------------------------------------------------------------
    # Load saved recipient groups into dropdown on tab open
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-load-rlist-select", "options"),
            Output("bulk-email-send-rlist-select", "options"),
        ],
        Input("bulk-email-tab-rendered", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_recipient_lists(_rendered, token):
        if not token:
            return no_update, no_update
        rows = _load_recipient_lists(token)
        options = [{"label": _rlist_label(r), "value": r["id"]} for r in rows if "id" in r]
        return options, options

    # -----------------------------------------------------------------------
    # Load a saved group into the filter editor + auto-preview
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-name", "value"),
            Output("bulk-email-rlist-desc", "value"),
            Output("bulk-email-rlist-roles", "value"),
            Output("bulk-email-rlist-verified", "value"),
            Output("bulk-email-rlist-min-created", "value"),
            Output("bulk-email-rlist-max-created", "value"),
            Output("bulk-email-rlist-min-activity", "value"),
            Output("bulk-email-rlist-max-activity", "value"),
            Output("bulk-email-loaded-rlist-id", "data"),
            Output("bulk-email-rlist-mode-label", "children"),
            Output("bulk-email-preview-grid", "getRowsResponse", allow_duplicate=True),
            Output("bulk-email-preview-count", "children", allow_duplicate=True),
            Output("bulk-email-preview-filter-store", "data", allow_duplicate=True),
            Output("bulk-email-preview-source-label", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-load-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def load_rlist_into_editor(_n, token, rlist_id):
        _empty = (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
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
        if not token or not rlist_id:
            return _empty + ("Select a group to load.", True, "warning")
        rows = _load_recipient_lists(token)
        row = next((r for r in rows if str(r.get("id")) == str(rlist_id)), None)
        if not row:
            return _empty + ("Group not found.", True, "danger")
        fc = row.get("filter_criteria") or {}
        roles = fc.get("roles") or ["USER"]
        verified_val = (
            "true"
            if fc.get("email_verified") is True
            else "false"
            if fc.get("email_verified") is False
            else "any"
        )
        preview_rows, total = _fetch_preview_page(
            token, fc, {"page": 1, "per_page": DEFAULT_PAGE_SIZE}
        )
        label = f"Editing: {row.get('name', '')}"
        source_label = f"\u2014 Saved group: {row.get('name', '')}"
        return (
            row.get("name", ""),
            row.get("description", ""),
            roles,
            verified_val,
            fc.get("min_created_at", ""),
            fc.get("max_created_at", ""),
            fc.get("min_last_activity_at", ""),
            fc.get("max_last_activity_at", ""),
            rlist_id,
            label,
            {"rowData": preview_rows, "rowCount": total},
            f"{total} recipients",
            fc,
            source_label,
            "",
            False,
            "success",
        )

    # -----------------------------------------------------------------------
    # Copy a saved group (create new group based on selected one)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-name", "value", allow_duplicate=True),
            Output("bulk-email-rlist-desc", "value", allow_duplicate=True),
            Output("bulk-email-rlist-roles", "value", allow_duplicate=True),
            Output("bulk-email-rlist-verified", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-activity", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-activity", "value", allow_duplicate=True),
            Output("bulk-email-loaded-rlist-id", "data", allow_duplicate=True),
            Output("bulk-email-rlist-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "color", allow_duplicate=True),
            Output("bulk-email-load-rlist-select", "options", allow_duplicate=True),
            Output("bulk-email-send-rlist-select", "options", allow_duplicate=True),
        ],
        Input("bulk-email-copy-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def copy_recipient_list(_n, token, rlist_id):
        _no = (
            no_update,
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
        if not token or not rlist_id:
            return _no + ("Select a group to copy.", True, "warning", no_update, no_update)
        rows = _load_recipient_lists(token)
        row = next((r for r in rows if str(r.get("id")) == str(rlist_id)), None)
        if not row:
            return _no + ("Group not found.", True, "danger", no_update, no_update)
        copy_name = f"Copy of {row.get('name', 'Group')}"
        fc = row.get("filter_criteria") or {}
        try:
            resp = _api(
                token,
                "POST",
                "/bulk-email/recipient-list",
                json={
                    "name": copy_name,
                    "description": row.get("description", ""),
                    "filter_criteria": fc,
                },
            )
            if resp.status_code not in (200, 201):
                msg = _extract_error(resp)
                return _no + (f"Error: {msg}", True, "danger", no_update, no_update)
            new_id = resp.json().get("data", {}).get("id")
            new_rows = _load_recipient_lists(token)
            options = [{"label": _rlist_label(r), "value": r["id"]} for r in new_rows if "id" in r]
            roles = fc.get("roles") or ["USER"]
            verified_val = (
                "true"
                if fc.get("email_verified") is True
                else "false"
                if fc.get("email_verified") is False
                else "any"
            )
            return (
                copy_name,
                row.get("description", ""),
                roles,
                verified_val,
                fc.get("min_created_at", ""),
                fc.get("max_created_at", ""),
                fc.get("min_last_activity_at", ""),
                fc.get("max_last_activity_at", ""),
                new_id,
                f"Editing: {copy_name}",
                f"Created copy '{copy_name}'.",
                True,
                "success",
                options,
                options,
            )
        except Exception:
            logger.exception("Failed to copy recipient list")
            return _no + ("An unexpected error occurred.", True, "danger", no_update, no_update)

    # -----------------------------------------------------------------------
    # Clear the group editor (new group)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-name", "value", allow_duplicate=True),
            Output("bulk-email-rlist-desc", "value", allow_duplicate=True),
            Output("bulk-email-rlist-roles", "value", allow_duplicate=True),
            Output("bulk-email-rlist-verified", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-activity", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-activity", "value", allow_duplicate=True),
            Output("bulk-email-loaded-rlist-id", "data", allow_duplicate=True),
            Output("bulk-email-rlist-mode-label", "children", allow_duplicate=True),
        ],
        Input("bulk-email-clear-rlist-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_group_editor(_n):
        return "", "", ["USER"], "any", "", "", "", "", None, ""

    # -----------------------------------------------------------------------
    # Delete saved recipient group (dropdown-based)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-alert", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "color", allow_duplicate=True),
            Output("bulk-email-rlist-name", "value", allow_duplicate=True),
            Output("bulk-email-rlist-desc", "value", allow_duplicate=True),
            Output("bulk-email-rlist-roles", "value", allow_duplicate=True),
            Output("bulk-email-rlist-verified", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-created", "value", allow_duplicate=True),
            Output("bulk-email-rlist-min-activity", "value", allow_duplicate=True),
            Output("bulk-email-rlist-max-activity", "value", allow_duplicate=True),
            Output("bulk-email-loaded-rlist-id", "data", allow_duplicate=True),
            Output("bulk-email-rlist-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-load-rlist-select", "options", allow_duplicate=True),
            Output("bulk-email-load-rlist-select", "value", allow_duplicate=True),
            Output("bulk-email-send-rlist-select", "options", allow_duplicate=True),
        ],
        Input("bulk-email-delete-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-rlist-select", "value"),
            State("bulk-email-loaded-rlist-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def delete_recipient_list(_n, token, selected_id, loaded_id):
        rlist_id = selected_id or loaded_id
        _no_change = (
            no_update,
            no_update,
            no_update,
            no_update,
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
        if not token or not rlist_id:
            return ("Select a group to delete.", True, "warning") + _no_change
        try:
            rows = _load_recipient_lists(token)
            row = next((r for r in rows if str(r.get("id")) == str(rlist_id)), None)
            name = row.get("name", rlist_id) if row else rlist_id
            resp = _api(token, "DELETE", f"/bulk-email/recipient-list/{rlist_id}")
            if resp.status_code in (200, 204):
                new_rows = _load_recipient_lists(token)
                options = [
                    {"label": _rlist_label(r), "value": r["id"]} for r in new_rows if "id" in r
                ]
                return (
                    f"Group '{name}' deleted.",
                    True,
                    "success",
                    "",
                    "",
                    ["USER"],
                    "any",
                    "",
                    "",
                    "",
                    "",
                    None,
                    "",
                    options,
                    None,
                    options,
                )
            msg = _extract_error(resp)
            return (f"Error: {msg}", True, "danger") + _no_change
        except Exception:
            logger.exception("Failed to delete recipient list")
            return ("An unexpected error occurred.", True, "danger") + _no_change

    # -----------------------------------------------------------------------
    # Infinite scroll — subsequent pages requested by AG Grid
    # Uses build_aggrid_request_params to handle pagination and column sorting.
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-preview-grid", "getRowsResponse", allow_duplicate=True),
        Input("bulk-email-preview-grid", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("bulk-email-preview-filter-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def get_preview_rows(request, token, filter_criteria):
        if not request or filter_criteria is None or not token:
            return no_update
        params, _ = build_aggrid_request_params(
            request,
            allow_filters=False,
            allowed_sort_columns=_PREVIEW_ALLOWED_SORT_COLUMNS,
        )
        rows, total = _fetch_preview_page(token, filter_criteria, params)
        return {"rowData": rows, "rowCount": total}

    # -----------------------------------------------------------------------
    # Save recipient group
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-alert", "children"),
            Output("bulk-email-rlist-alert", "is_open"),
            Output("bulk-email-rlist-alert", "color"),
            Output("bulk-email-loaded-rlist-id", "data", allow_duplicate=True),
            Output("bulk-email-rlist-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-load-rlist-select", "options", allow_duplicate=True),
            Output("bulk-email-send-rlist-select", "options", allow_duplicate=True),
        ],
        Input("bulk-email-save-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-rlist-name", "value"),
            State("bulk-email-rlist-desc", "value"),
            State("bulk-email-rlist-roles", "value"),
            State("bulk-email-rlist-verified", "value"),
            State("bulk-email-rlist-min-created", "value"),
            State("bulk-email-rlist-max-created", "value"),
            State("bulk-email-rlist-min-activity", "value"),
            State("bulk-email-rlist-max-activity", "value"),
            State("bulk-email-loaded-rlist-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_recipient_list(
        _n,
        token,
        name,
        desc,
        roles,
        verified,
        min_created,
        max_created,
        min_activity,
        max_activity,
        loaded_rlist_id,
    ):
        _no = (no_update, no_update, no_update, no_update)
        if not token or not name:
            return ("Please enter a group name.", True, "warning") + _no
        filter_criteria = _build_filter_criteria(
            roles, verified, min_created, max_created, min_activity, max_activity
        )
        try:
            if loaded_rlist_id:
                resp = _api(
                    token,
                    "PATCH",
                    f"/bulk-email/recipient-list/{loaded_rlist_id}",
                    json={
                        "name": name,
                        "description": desc or "",
                        "filter_criteria": filter_criteria,
                    },
                )
                action = "updated"
            else:
                resp = _api(
                    token,
                    "POST",
                    "/bulk-email/recipient-list",
                    json={
                        "name": name,
                        "description": desc or "",
                        "filter_criteria": filter_criteria,
                    },
                )
                action = "saved"
            if resp.status_code in (200, 201):
                saved_id = resp.json().get("data", {}).get("id") or loaded_rlist_id
                rows = _load_recipient_lists(token)
                options = [{"label": _rlist_label(r), "value": r["id"]} for r in rows if "id" in r]
                return (
                    f"Group '{name}' {action}.",
                    True,
                    "success",
                    saved_id,
                    f"Editing: {name}",
                    options,
                    options,
                )
            msg = _extract_error(resp)
            return (f"Error: {msg}", True, "danger") + _no
        except Exception:
            logger.exception("Failed to save recipient list")
            return ("An unexpected error occurred.", True, "danger") + _no

    # -----------------------------------------------------------------------
    # Load a template into the composer
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-subject", "value", allow_duplicate=True),
            Output("bulk-email-html-source", "value", allow_duplicate=True),
            Output("bulk-email-category-select", "value", allow_duplicate=True),
            Output("bulk-email-preview-html", "data", allow_duplicate=True),
            Output("bulk-email-preview-frame", "srcDoc", allow_duplicate=True),
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
            Output("bulk-email-editor-tabs", "value", allow_duplicate=True),
            Output("bulk-email-active-template", "data", allow_duplicate=True),
            # News fields
            Output("bulk-email-field-news-issue-date", "value", allow_duplicate=True),
            Output("bulk-email-field-news-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-title", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-body", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-image-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-label", "value", allow_duplicate=True),
            # Engagement fields
            Output("bulk-email-field-engagement-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-topic", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-description", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-label", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-url", "value", allow_duplicate=True),
            # System update fields
            Output("bulk-email-field-sysupdate-date-time", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-datetime-utc", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-duration", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-impact", "value", allow_duplicate=True),
            # Dynamic stores
            Output("bulk-email-news-items-store", "data", allow_duplicate=True),
            Output("bulk-email-impact-items-store", "data", allow_duplicate=True),
        ],
        Input("bulk-email-load-template-btn", "n_clicks"),
        State("bulk-email-template-select", "value"),
        prevent_initial_call=True,
    )
    def load_template_into_composer(_n, template_key):
        from ..email_templates import TEMPLATES

        # 29 outputs total; early return fills all 29 explicitly:
        #  5 no_update + 3 alert values + 21 no_updates for items 9-29
        _nu21 = (no_update,) * 21

        if not template_key or template_key not in TEMPLATES:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Select a template first.",
                True,
                "warning",
                *_nu21,
            )
        tmpl = TEMPLATES[template_key]
        raw_html = tmpl["html"]
        subject = tmpl["subject"]

        # Default field values per template.
        # news_f = 7 items  (matches 7 news outputs)
        # eng_f  = 5 items  (matches 5 engagement outputs)
        # sys_f  = 5 items  (matches 5 sysupdate outputs)
        news_f = ("",) * 7
        eng_f = ("",) * 5
        sys_f = ("",) * 5
        news_items = _DEFAULT_NEWS_ITEMS
        impact_items = _DEFAULT_IMPACT_ITEMS

        if template_key == "news":
            from datetime import date

            month_year = date.today().strftime("%B %Y")  # e.g. "May 2026"
            subject = subject.replace("[Month Year]", month_year)
            news_f = (
                month_year,
                "Here is the latest news from the Trends.Earth community.",
                "Highlight",
                "[Add your main highlight here.]",
                "",  # highlight_image_url — blank by default
                "",
                "Visit Trends.Earth",
            )
        elif template_key == "engagement":
            eng_f = (
                (
                    "As a valued member of the Trends.Earth community, your feedback "
                    "helps us improve the tools and resources we provide."
                ),
                "[Survey / Feedback Topic]",
                "[Describe what you want users to do or share.]",
                "[Action Button Label]",
                "#",
            )
            news_items = []
            impact_items = []
        elif template_key == "system_update":
            sys_f = (
                "[Date & Time]",
                "We want to let you know about an upcoming change to the Trends.Earth platform.",
                "[YYYY-MM-DD HH:MM UTC]",
                "[Estimated duration]",
                "[Services affected]",
            )
            news_items = []

        return (
            subject,
            raw_html,
            tmpl.get("subscription_type", ""),
            raw_html,
            raw_html,
            f"Template '{tmpl['label']}' loaded.",
            True,
            "success",
            "fields",
            template_key,
            *news_f,
            *eng_f,
            *sys_f,
            news_items,
            impact_items,
        )

    # Save draft bulk email
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-composer-alert", "children"),
            Output("bulk-email-composer-alert", "is_open"),
            Output("bulk-email-composer-alert", "color"),
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-preview-html", "data", allow_duplicate=True),
            Output("bulk-email-preview-frame", "srcDoc", allow_duplicate=True),
        ],
        Input("bulk-email-save-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-name", "value"),
            State("bulk-email-subject", "value"),
            State("bulk-email-html-source", "value"),
            State("bulk-email-loaded-draft-id", "data"),
            State("bulk-email-category-select", "value"),
            State("bulk-email-editor-tabs", "value"),
            State("bulk-email-active-template", "data"),
            # News fields
            State("bulk-email-field-news-issue-date", "value"),
            State("bulk-email-field-news-intro", "value"),
            State("bulk-email-field-news-highlight-title", "value"),
            State("bulk-email-field-news-highlight-body", "value"),
            State("bulk-email-field-news-highlight-image-url", "value"),
            State("bulk-email-field-news-cta-url", "value"),
            State("bulk-email-field-news-cta-label", "value"),
            # Engagement fields
            State("bulk-email-field-engagement-intro", "value"),
            State("bulk-email-field-engagement-topic", "value"),
            State("bulk-email-field-engagement-description", "value"),
            State("bulk-email-field-engagement-btn-label", "value"),
            State("bulk-email-field-engagement-btn-url", "value"),
            # System update fields
            State("bulk-email-field-sysupdate-date-time", "value"),
            State("bulk-email-field-sysupdate-intro", "value"),
            State("bulk-email-field-sysupdate-datetime-utc", "value"),
            State("bulk-email-field-sysupdate-duration", "value"),
            State("bulk-email-field-sysupdate-impact", "value"),
            # Dynamic stores
            State("bulk-email-news-items-store", "data"),
            State("bulk-email-impact-items-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_draft_bulk_email(
        _n,
        token,
        name,
        subject,
        raw_html,
        loaded_draft_id,
        subscription_type,
        active_tab,
        active_template,
        news_issue_date,
        news_intro,
        news_highlight_title,
        news_highlight_body,
        news_highlight_image_url,
        news_cta_url,
        news_cta_label,
        engagement_intro,
        engagement_topic,
        engagement_description,
        engagement_btn_label,
        engagement_btn_url,
        sysupdate_date_time,
        sysupdate_intro,
        sysupdate_datetime_utc,
        sysupdate_duration,
        sysupdate_impact,
        news_items,
        impact_items,
    ):
        _nu9 = (no_update,) * 6  # 6 outputs after the first 3 (alert)

        if not token or not name or not subject:
            return (
                "Name and subject are required.",
                True,
                "warning",
                *_nu9,
            )

        # Determine content based on active tab
        fields_data = None
        if active_tab == "fields" and active_template:
            html_content = _build_html_from_fields(
                active_template,
                news_issue_date=news_issue_date or "",
                news_intro=news_intro or "",
                news_highlight_title=news_highlight_title or "",
                news_highlight_body=news_highlight_body or "",
                news_highlight_image_url=news_highlight_image_url or "",
                news_items=news_items or [],
                news_cta_url=news_cta_url or "",
                news_cta_label=news_cta_label or "",
                engagement_intro=engagement_intro or "",
                engagement_topic=engagement_topic or "",
                engagement_description=engagement_description or "",
                engagement_btn_label=engagement_btn_label or "",
                engagement_btn_url=engagement_btn_url or "",
                sysupdate_date_time=sysupdate_date_time or "",
                sysupdate_intro=sysupdate_intro or "",
                sysupdate_datetime_utc=sysupdate_datetime_utc or "",
                sysupdate_duration=sysupdate_duration or "",
                sysupdate_impact=sysupdate_impact or "",
                impact_items=impact_items or [],
            )
            fields_data = {
                "template": active_template,
                "news_issue_date": news_issue_date,
                "news_intro": news_intro,
                "news_highlight_title": news_highlight_title,
                "news_highlight_body": news_highlight_body,
                "news_highlight_image_url": news_highlight_image_url,
                "news_cta_url": news_cta_url,
                "news_cta_label": news_cta_label,
                "engagement_intro": engagement_intro,
                "engagement_topic": engagement_topic,
                "engagement_description": engagement_description,
                "engagement_btn_label": engagement_btn_label,
                "engagement_btn_url": engagement_btn_url,
                "sysupdate_date_time": sysupdate_date_time,
                "sysupdate_intro": sysupdate_intro,
                "sysupdate_datetime_utc": sysupdate_datetime_utc,
                "sysupdate_duration": sysupdate_duration,
                "sysupdate_impact": sysupdate_impact,
                "news_items": news_items or [],
                "impact_items": impact_items or [],
            }
        else:
            html_content = raw_html or ""

        payload = {
            "name": name,
            "subject": subject,
            "html_content": html_content,
            "subscription_type": subscription_type or None,
            "fields_data": fields_data,
        }
        try:
            if loaded_draft_id:
                resp = _api(token, "PATCH", f"/bulk-email/{loaded_draft_id}", json=payload)
                action = "updated"
            else:
                resp = _api(token, "POST", "/bulk-email", json=payload)
                action = "saved"
            if resp.status_code in (200, 201):
                saved_id = resp.json().get("data", {}).get("id") or loaded_draft_id
                options = _load_draft_options(token)
                label = f"Editing: {name}"
                preview = html_content or ""
                return (
                    f"Draft '{name}' {action}.",
                    True,
                    "success",
                    options,
                    options,
                    saved_id,
                    label,
                    preview,
                    preview,
                )
            msg = _extract_error(resp)
            return (f"Error: {msg}", True, "danger", *_nu9)
        except Exception:
            logger.exception("Failed to save draft bulk email")
            return ("An unexpected error occurred.", True, "danger", *_nu9)

    # -----------------------------------------------------------------------
    # Load draft bulk emails on tab open
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-select", "options"),
            Output("bulk-email-load-draft-select", "options"),
            Output("bulk-email-history-grid", "rowData"),
        ],
        [
            Input("bulk-email-tab-rendered", "data"),
            Input("bulk-email-history-refresh-btn", "n_clicks"),
        ],
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_bulk_emails(_rendered, _refresh, token):
        if not token:
            return no_update, no_update, no_update
        try:
            resp = _api(token, "GET", "/bulk-email")
            bulk_emails = _ok_rows(resp)
        except Exception:
            logger.exception("Failed to load bulk emails")
            bulk_emails = []
        draft_options = [
            {"label": c["name"], "value": c["id"]}
            for c in bulk_emails
            if c.get("status") == "DRAFT"
        ]
        return draft_options, draft_options, bulk_emails

    # -----------------------------------------------------------------------
    # Load a draft into the composer
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-name", "value"),
            Output("bulk-email-subject", "value"),
            Output("bulk-email-html-source", "value"),
            Output("bulk-email-loaded-draft-id", "data"),
            Output("bulk-email-draft-mode-label", "children"),
            Output("bulk-email-category-select", "value"),
            Output("bulk-email-preview-html", "data"),
            Output("bulk-email-preview-frame", "srcDoc"),
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
            Output("bulk-email-editor-tabs", "value"),
            Output("bulk-email-active-template", "data"),
            # News fields
            Output("bulk-email-field-news-issue-date", "value"),
            Output("bulk-email-field-news-intro", "value"),
            Output("bulk-email-field-news-highlight-title", "value"),
            Output("bulk-email-field-news-highlight-body", "value"),
            Output("bulk-email-field-news-highlight-image-url", "value"),
            Output("bulk-email-field-news-cta-url", "value"),
            Output("bulk-email-field-news-cta-label", "value"),
            # Engagement fields
            Output("bulk-email-field-engagement-intro", "value"),
            Output("bulk-email-field-engagement-topic", "value"),
            Output("bulk-email-field-engagement-description", "value"),
            Output("bulk-email-field-engagement-btn-label", "value"),
            Output("bulk-email-field-engagement-btn-url", "value"),
            # System update fields
            Output("bulk-email-field-sysupdate-date-time", "value"),
            Output("bulk-email-field-sysupdate-intro", "value"),
            Output("bulk-email-field-sysupdate-datetime-utc", "value"),
            Output("bulk-email-field-sysupdate-duration", "value"),
            Output("bulk-email-field-sysupdate-impact", "value"),
            # Dynamic stores
            Output("bulk-email-news-items-store", "data"),
            Output("bulk-email-impact-items-store", "data"),
            Output("bulk-email-in-html-mode", "data", allow_duplicate=True),
        ],
        Input("bulk-email-load-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-draft-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def load_draft_into_composer(_n, token, draft_id):
        _nu_fields = ("",) * 17  # 17 field outputs
        _nu_stores = ([], [])  # 2 store outputs

        def _error(msg):
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                msg,
                True,
                "danger",
                no_update,
                no_update,
                *_nu_fields,
                *_nu_stores,
                no_update,  # in-html-mode
            )

        if not token or not draft_id:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Select a draft to load.",
                True,
                "warning",
                no_update,
                no_update,
                *_nu_fields,
                *_nu_stores,
                no_update,  # in-html-mode
            )
        try:
            resp = _api(token, "GET", f"/bulk-email/{draft_id}")
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                name = data.get("name", "")
                subject = data.get("subject", "")
                html_content = data.get("html_content", "")
                subscription_type = data.get("subscription_type") or ""
                label = f"Editing: {name}"
                fields_data = data.get("fields_data")

                if isinstance(fields_data, dict):
                    template = fields_data.get("template", "")
                    news_items = fields_data.get("news_items") or _DEFAULT_NEWS_ITEMS
                    impact_items = fields_data.get("impact_items") or _DEFAULT_IMPACT_ITEMS
                    return (
                        name,
                        subject,
                        html_content,
                        draft_id,
                        label,
                        subscription_type,
                        html_content,
                        html_content,
                        "",
                        False,
                        "success",
                        "fields",
                        template,
                        fields_data.get("news_issue_date", ""),
                        fields_data.get("news_intro", ""),
                        fields_data.get("news_highlight_title", ""),
                        fields_data.get("news_highlight_body", ""),
                        fields_data.get("news_highlight_image_url", ""),
                        fields_data.get("news_cta_url", ""),
                        fields_data.get("news_cta_label", ""),
                        fields_data.get("engagement_intro", ""),
                        fields_data.get("engagement_topic", ""),
                        fields_data.get("engagement_description", ""),
                        fields_data.get("engagement_btn_label", ""),
                        fields_data.get("engagement_btn_url", ""),
                        fields_data.get("sysupdate_date_time", ""),
                        fields_data.get("sysupdate_intro", ""),
                        fields_data.get("sysupdate_datetime_utc", ""),
                        fields_data.get("sysupdate_duration", ""),
                        fields_data.get("sysupdate_impact", ""),
                        news_items,
                        impact_items,
                        False,  # in-html-mode: reset for templated drafts
                    )
                else:
                    # Raw HTML draft — show in raw tab, lock fields
                    pretty = _prettify_html(html_content)
                    return (
                        name,
                        subject,
                        pretty,
                        draft_id,
                        label,
                        subscription_type,
                        html_content,
                        html_content,
                        "",
                        False,
                        "success",
                        "raw",
                        "",
                        *_nu_fields,
                        *_nu_stores,
                        True,  # in-html-mode: lock fields for raw HTML drafts
                    )
            msg = _extract_error(resp)
            return _error(f"Error loading draft: {msg}")
        except Exception:
            logger.exception("Failed to load draft")
            return _error("An unexpected error occurred.")

    # -----------------------------------------------------------------------
    # Copy a draft (create new draft based on selected one)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-name", "value", allow_duplicate=True),
            Output("bulk-email-subject", "value", allow_duplicate=True),
            Output("bulk-email-html-source", "value", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-category-select", "value", allow_duplicate=True),
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
        ],
        Input("bulk-email-copy-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-draft-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def copy_draft(_n, token, draft_id):
        _nu11 = (no_update,) * 11

        if not token or not draft_id:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Select a draft to copy.",
                True,
                "warning",
                no_update,
                no_update,
            )
        try:
            resp = _api(token, "GET", f"/bulk-email/{draft_id}")
            if resp.status_code != 200:
                msg = _extract_error(resp)
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    f"Error loading draft: {msg}",
                    True,
                    "danger",
                    no_update,
                    no_update,
                )
            data = resp.json().get("data", {})
            copy_name = f"Copy of {data.get('name', 'Draft')}"
            copy_subject = data.get("subject", "")
            copy_html = data.get("html_content", "")
            copy_subscription_type = data.get("subscription_type") or None
            copy_fields_data = data.get("fields_data")
            create_resp = _api(
                token,
                "POST",
                "/bulk-email",
                json={
                    "name": copy_name,
                    "subject": copy_subject,
                    "html_content": copy_html,
                    "subscription_type": copy_subscription_type,
                    "fields_data": copy_fields_data,
                },
            )
            if create_resp.status_code not in (200, 201):
                msg = _extract_error(create_resp)
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    f"Error creating copy: {msg}",
                    True,
                    "danger",
                    no_update,
                    no_update,
                )
            new_id = create_resp.json().get("data", {}).get("id")
            options = _load_draft_options(token)
            label = f"Editing: {copy_name}"
            return (
                copy_name,
                copy_subject,
                copy_html,
                new_id,
                label,
                copy_subscription_type or "",
                f"Created copy '{copy_name}'.",
                True,
                "success",
                options,
                options,
            )
        except Exception:
            logger.exception("Failed to copy draft")
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "An unexpected error occurred.",
                True,
                "danger",
                no_update,
                no_update,
            )

    # -----------------------------------------------------------------------
    # Clear the composer (new draft)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-name", "value", allow_duplicate=True),
            Output("bulk-email-subject", "value", allow_duplicate=True),
            Output("bulk-email-html-source", "value", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-category-select", "value", allow_duplicate=True),
            Output("bulk-email-template-select", "value", allow_duplicate=True),
            Output("bulk-email-active-template", "data", allow_duplicate=True),
            Output("bulk-email-news-items-store", "data", allow_duplicate=True),
            Output("bulk-email-impact-items-store", "data", allow_duplicate=True),
            Output("bulk-email-editor-tabs", "value", allow_duplicate=True),
            Output("bulk-email-in-html-mode", "data", allow_duplicate=True),
            # News fields
            Output("bulk-email-field-news-issue-date", "value", allow_duplicate=True),
            Output("bulk-email-field-news-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-title", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-body", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-image-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-label", "value", allow_duplicate=True),
            # Engagement fields
            Output("bulk-email-field-engagement-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-topic", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-description", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-label", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-url", "value", allow_duplicate=True),
            # System update fields
            Output("bulk-email-field-sysupdate-date-time", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-datetime-utc", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-duration", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-impact", "value", allow_duplicate=True),
        ],
        Input("bulk-email-clear-draft-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_composer(_n):
        return (
            "",
            "",
            "",
            None,
            "",
            "",
            "",  # name, subject, html, loaded_id, label, cat, tmpl-sel
            "",  # active-template
            [],  # news-items-store
            [],  # impact-items-store
            "fields",  # editor-tabs
            False,  # in-html-mode: reset on clear
            *("",) * 17,  # all 17 field values
        )

    # -----------------------------------------------------------------------
    # Delete draft bulk email
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
            Output("bulk-email-name", "value", allow_duplicate=True),
            Output("bulk-email-subject", "value", allow_duplicate=True),
            Output("bulk-email-html-source", "value", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-category-select", "value", allow_duplicate=True),
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "value", allow_duplicate=True),
            Output("bulk-email-active-template", "data", allow_duplicate=True),
            Output("bulk-email-news-items-store", "data", allow_duplicate=True),
            Output("bulk-email-impact-items-store", "data", allow_duplicate=True),
            Output("bulk-email-editor-tabs", "value", allow_duplicate=True),
            Output("bulk-email-in-html-mode", "data", allow_duplicate=True),
            # News fields
            Output("bulk-email-field-news-issue-date", "value", allow_duplicate=True),
            Output("bulk-email-field-news-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-title", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-body", "value", allow_duplicate=True),
            Output("bulk-email-field-news-highlight-image-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-url", "value", allow_duplicate=True),
            Output("bulk-email-field-news-cta-label", "value", allow_duplicate=True),
            # Engagement fields
            Output("bulk-email-field-engagement-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-topic", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-description", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-label", "value", allow_duplicate=True),
            Output("bulk-email-field-engagement-btn-url", "value", allow_duplicate=True),
            # System update fields
            Output("bulk-email-field-sysupdate-date-time", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-intro", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-datetime-utc", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-duration", "value", allow_duplicate=True),
            Output("bulk-email-field-sysupdate-impact", "value", allow_duplicate=True),
        ],
        Input("bulk-email-delete-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-draft-select", "value"),
            State("bulk-email-loaded-draft-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def delete_draft(_n, token, selected_id, loaded_id):
        _nu_post_alert = (no_update,) * 31  # all outputs after the 3 alert ones

        draft_id = selected_id or loaded_id
        if not token or not draft_id:
            return ("Select a draft to delete.", True, "warning", *_nu_post_alert)
        try:
            resp = _api(token, "DELETE", f"/bulk-email/{draft_id}")
            if resp.status_code in (200, 204):
                options = _load_draft_options(token)
                return (
                    "Draft deleted.",
                    True,
                    "success",
                    "",
                    "",
                    "",
                    None,
                    "",
                    "",  # name, subject, html, loaded_id, label, cat
                    options,
                    options,
                    None,  # send-select, load-draft-select, load-draft-value
                    "",  # active-template
                    [],  # news-items-store
                    [],  # impact-items-store
                    "fields",  # editor-tabs
                    False,  # in-html-mode: reset on delete
                    *("",) * 17,  # all 17 field values
                )
            msg = _extract_error(resp)
            return (f"Error deleting draft: {msg}", True, "danger", *_nu_post_alert)
        except Exception:
            logger.exception("Failed to delete draft")
            return ("An unexpected error occurred.", True, "danger", *_nu_post_alert)

    # -----------------------------------------------------------------------
    # Initiate send — opens verify modal on 428, shows success/error otherwise
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-alert", "children"),
            Output("bulk-email-send-alert", "is_open"),
            Output("bulk-email-send-alert", "color"),
            Output("bulk-email-verify-modal", "is_open"),
            Output("bulk-email-verify-modal-title", "children"),
            Output("bulk-email-verify-modal-body", "children"),
            Output("bulk-email-pending-id", "data"),
        ],
        Input("bulk-email-send-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-send-select", "value"),
            State("bulk-email-send-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def initiate_send(_n, token, bulk_email_id, recipient_list_id):
        if not token:
            return "Not authenticated.", True, "danger", False, "", "", None
        if not bulk_email_id:
            return "Select a bulk email.", True, "warning", False, "", "", None
        payload = {}
        if recipient_list_id:
            payload["recipient_list_id"] = recipient_list_id
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send", json=payload)
            if resp.status_code in (200, 202):
                return (
                    "Bulk email queued for sending! It will be delivered shortly.",
                    True,
                    "success",
                    False,
                    "",
                    "",
                    None,
                )
            if resp.status_code == 428:
                body = resp.json()
                count = body.get("recipient_count", "?")
                title = "Verification Required"
                msg = (
                    f"This bulk email targets {count} recipients, which exceeds the threshold. "
                    "A verification code will be sent to your email. "
                    "Click 'Request Code' to receive it, then enter it below and click 'Confirm Send'."
                )
                return no_update, False, no_update, True, title, msg, bulk_email_id
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger", False, "", "", None
        except Exception:
            logger.exception("Failed to initiate bulk email send")
            return "An unexpected error occurred.", True, "danger", False, "", "", None

    # -----------------------------------------------------------------------
    # Request verification code
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-verify-modal-alert", "children"),
            Output("bulk-email-verify-modal-alert", "is_open"),
            Output("bulk-email-verify-modal-alert", "color"),
        ],
        Input("bulk-email-request-code-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-pending-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def request_verification_code(_n, token, bulk_email_id):
        if not token or not bulk_email_id:
            return "No bulk email selected.", True, "warning"
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send-verification")
            if resp.status_code == 200:
                return "Verification code sent to your email address.", True, "success"
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to request verification code")
            return "An unexpected error occurred.", True, "danger"

    # -----------------------------------------------------------------------
    # Confirm send with OTP
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-verify-modal", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "children", allow_duplicate=True),
            Output("bulk-email-send-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "color", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "children", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-verify-submit", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-pending-id", "data"),
            State("bulk-email-verify-code", "value"),
            State("bulk-email-send-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def confirm_send(_n, token, bulk_email_id, code, recipient_list_id):
        if not token or not bulk_email_id:
            return True, no_update, False, no_update, "No bulk email selected.", True, "warning"
        if not code or len(code.strip()) != 6:
            return True, no_update, False, no_update, "Enter a valid 6-digit code.", True, "warning"
        payload = {"code": code.strip()}
        if recipient_list_id:
            payload["recipient_list_id"] = recipient_list_id
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send", json=payload)
            if resp.status_code in (200, 202):
                return (
                    False,
                    "Bulk email queued for sending! It will be delivered shortly.",
                    True,
                    "success",
                    "",
                    False,
                    "success",
                )
            msg = _extract_error(resp)
            return True, no_update, False, no_update, f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to confirm bulk email send")
            return (
                True,
                no_update,
                False,
                no_update,
                "An unexpected error occurred.",
                True,
                "danger",
            )

    # -----------------------------------------------------------------------
    # Cancel verify modal
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-verify-modal", "is_open", allow_duplicate=True),
        Input("bulk-email-verify-cancel", "n_clicks"),
        prevent_initial_call=True,
    )
    def cancel_verify_modal(_n):
        return False

    # -----------------------------------------------------------------------
    # Send test to self
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-alert", "children", allow_duplicate=True),
            Output("bulk-email-send-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-send-test-self-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-send-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def send_test_to_self(_n, token, bulk_email_id):
        if not token:
            return "Not authenticated.", True, "danger"
        if not bulk_email_id:
            return "Select a bulk email first.", True, "warning"
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send-test-self")
            if resp.status_code == 200:
                sent_to = resp.json().get("data", {}).get("sent_to", "you")
                return f"Test email sent to {sent_to}.", True, "success"
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to send test bulk email to self")
            return "An unexpected error occurred.", True, "danger"

    # -----------------------------------------------------------------------
    # Send test to superadmins
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-alert", "children", allow_duplicate=True),
            Output("bulk-email-send-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-send-test-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-send-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def send_test_bulk_email(_n, token, bulk_email_id):
        if not token:
            return "Not authenticated.", True, "danger"
        if not bulk_email_id:
            return "Select a bulk email first.", True, "warning"
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send-test")
            if resp.status_code == 200:
                return "Test email sent to all superadmins.", True, "success"
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to send test bulk email")
            return "An unexpected error occurred.", True, "danger"

    # -----------------------------------------------------------------------
    # Toggle template field panels
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-no-template-panel", "is_open"),
            Output("bulk-email-news-fields-panel", "is_open"),
            Output("bulk-email-engagement-fields-panel", "is_open"),
            Output("bulk-email-sysupdate-fields-panel", "is_open"),
        ],
        Input("bulk-email-active-template", "data"),
    )
    def toggle_field_panels(active_template):
        t = active_template or ""
        return (
            t == "",
            t == "news",
            t == "engagement",
            t == "system_update",
        )

    # -----------------------------------------------------------------------
    # Render news items container from store
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-news-items-container", "children"),
        Input("bulk-email-news-items-store", "data"),
    )
    def render_news_items_container(news_items):
        from ..components.bulk_email import _news_item_row

        items = news_items or []
        children = []
        for i, item in enumerate(items):
            row = _news_item_row(i, item=item)
            children.append(row)
        return children

    # -----------------------------------------------------------------------
    # Manage news items store (add / delete / field edits)
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-news-items-store", "data", allow_duplicate=True),
        [
            Input("bulk-email-add-news-item-btn", "n_clicks"),
            Input({"type": "news-item-delete", "index": ALL}, "n_clicks"),
            Input({"type": "news-title", "index": ALL}, "value"),
            Input({"type": "news-summary", "index": ALL}, "value"),
            Input({"type": "news-url", "index": ALL}, "value"),
            Input({"type": "news-image-url", "index": ALL}, "value"),
            Input({"type": "news-image-alt", "index": ALL}, "value"),
        ],
        State("bulk-email-news-items-store", "data"),
        prevent_initial_call=True,
    )
    def manage_news_items_store(
        _add,
        _delete_clicks,
        titles,
        summaries,
        urls,
        image_urls,
        image_alts,
        current_store,
    ):
        items = list(current_store or [])
        triggered = callback_context.triggered_id

        if triggered == "bulk-email-add-news-item-btn":
            from ..email_templates import _DEFAULT_NEWS_ITEMS

            template_item = _DEFAULT_NEWS_ITEMS[0] if _DEFAULT_NEWS_ITEMS else {}
            items.append(dict(template_item))
            return items

        if isinstance(triggered, dict) and triggered.get("type") == "news-item-delete":
            idx = triggered["index"]
            if 0 <= idx < len(items):
                items.pop(idx)
            return items

        # Field edits — sync store with current field values
        n = len(titles)
        if n == 0:
            return no_update
        new_items = []
        for i in range(n):
            new_items.append(
                {
                    "title": (titles[i] or "") if i < len(titles) else "",
                    "summary": (summaries[i] or "") if i < len(summaries) else "",
                    "url": (urls[i] or "") if i < len(urls) else "",
                    "image_url": (image_urls[i] or "") if i < len(image_urls) else "",
                    "image_alt": (image_alts[i] or "") if i < len(image_alts) else "",
                }
            )
        if new_items == items:
            return no_update
        return new_items

    # -----------------------------------------------------------------------
    # Upload news item image to S3
    # -----------------------------------------------------------------------
    @app.callback(
        Output({"type": "news-image-url", "index": ALL}, "value", allow_duplicate=True),
        Input({"type": "news-image-upload", "index": ALL}, "contents"),
        [
            State({"type": "news-image-upload", "index": ALL}, "filename"),
            State("token-store", "data"),
            State("bulk-email-news-items-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def upload_news_images(contents_list, filenames_list, _token, current_store):
        from ..utils.s3_upload import upload_image_to_s3

        items = list(current_store or [])
        n = max(len(contents_list), len(items))
        result_urls = [items[i].get("image_url", "") if i < len(items) else "" for i in range(n)]

        for i, (contents, filename) in enumerate(zip(contents_list or [], filenames_list or [])):
            if not contents:
                continue
            try:
                content_type_prefix, b64data = contents.split(",", 1)
                content_type = content_type_prefix.split(":")[1].split(";")[0]
                file_bytes = base64.b64decode(b64data)
                url = upload_image_to_s3(file_bytes, filename, content_type)
                if i < len(result_urls):
                    result_urls[i] = url
                else:
                    result_urls.append(url)
            except Exception:
                logger.exception("Failed to upload news image %s", filename)

        return result_urls

    # -----------------------------------------------------------------------
    # Upload single highlight image for the News template
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-field-news-highlight-image-url", "value", allow_duplicate=True),
        Input("bulk-email-highlight-image-upload", "contents"),
        State("bulk-email-highlight-image-upload", "filename"),
        prevent_initial_call=True,
    )
    def upload_highlight_image(contents, filename):
        from ..utils.s3_upload import upload_image_to_s3

        if not contents:
            return no_update
        try:
            content_type_prefix, b64data = contents.split(",", 1)
            content_type = content_type_prefix.split(":")[1].split(";")[0]
            file_bytes = base64.b64decode(b64data)
            return upload_image_to_s3(file_bytes, filename, content_type)
        except Exception:
            logger.exception("Failed to upload highlight image %s", filename)
            return no_update

    # -----------------------------------------------------------------------
    # Render impact items container from store
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-impact-items-container", "children"),
        Input("bulk-email-impact-items-store", "data"),
    )
    def render_impact_items_container(impact_items):
        from ..components.bulk_email import _impact_item_row

        items = impact_items or []
        return [_impact_item_row(i, text=item) for i, item in enumerate(items)]

    # -----------------------------------------------------------------------
    # Manage impact items store (add / delete / field edits)
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-impact-items-store", "data", allow_duplicate=True),
        [
            Input("bulk-email-add-impact-item-btn", "n_clicks"),
            Input({"type": "impact-item-delete", "index": ALL}, "n_clicks"),
            Input({"type": "impact-item", "index": ALL}, "value"),
        ],
        State("bulk-email-impact-items-store", "data"),
        prevent_initial_call=True,
    )
    def manage_impact_items_store(_add, _delete_clicks, values, current_store):
        items = list(current_store or [])
        triggered = callback_context.triggered_id

        if triggered == "bulk-email-add-impact-item-btn":
            items.append("[New impact item]")
            return items

        if isinstance(triggered, dict) and triggered.get("type") == "impact-item-delete":
            idx = triggered["index"]
            if 0 <= idx < len(items):
                items.pop(idx)
            return items

        # Field edits
        if not values:
            return no_update
        new_items = [v or "" for v in values]
        if new_items == items:
            return no_update
        return new_items

    # -----------------------------------------------------------------------
    # Live preview from fields tab
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-preview-frame", "srcDoc", allow_duplicate=True),
            Output("bulk-email-preview-html", "data", allow_duplicate=True),
            Output("bulk-email-html-source", "value", allow_duplicate=True),
        ],
        [
            Input("bulk-email-active-template", "data"),
            Input("bulk-email-news-items-store", "data"),
            Input("bulk-email-impact-items-store", "data"),
            # News fields
            Input("bulk-email-field-news-issue-date", "value"),
            Input("bulk-email-field-news-intro", "value"),
            Input("bulk-email-field-news-highlight-title", "value"),
            Input("bulk-email-field-news-highlight-body", "value"),
            Input("bulk-email-field-news-highlight-image-url", "value"),
            Input("bulk-email-field-news-cta-url", "value"),
            Input("bulk-email-field-news-cta-label", "value"),
            # Engagement fields
            Input("bulk-email-field-engagement-intro", "value"),
            Input("bulk-email-field-engagement-topic", "value"),
            Input("bulk-email-field-engagement-description", "value"),
            Input("bulk-email-field-engagement-btn-label", "value"),
            Input("bulk-email-field-engagement-btn-url", "value"),
            # System update fields
            Input("bulk-email-field-sysupdate-date-time", "value"),
            Input("bulk-email-field-sysupdate-intro", "value"),
            Input("bulk-email-field-sysupdate-datetime-utc", "value"),
            Input("bulk-email-field-sysupdate-duration", "value"),
            Input("bulk-email-field-sysupdate-impact", "value"),
            # Tab selector
            Input("bulk-email-editor-tabs", "value"),
        ],
        prevent_initial_call=True,
    )
    def live_preview_from_fields(
        active_template,
        news_items,
        impact_items,
        news_issue_date,
        news_intro,
        news_highlight_title,
        news_highlight_body,
        news_highlight_image_url,
        news_cta_url,
        news_cta_label,
        engagement_intro,
        engagement_topic,
        engagement_description,
        engagement_btn_label,
        engagement_btn_url,
        sysupdate_date_time,
        sysupdate_intro,
        sysupdate_datetime_utc,
        sysupdate_duration,
        sysupdate_impact,
        editor_tab,
    ):
        if editor_tab == "raw":
            # Switching to the raw tab: render fields → HTML so Monaco has content.
            if not active_template:
                return no_update, no_update, no_update
            html_content = _build_html_from_fields(
                active_template,
                news_issue_date=news_issue_date or "",
                news_intro=news_intro or "",
                news_highlight_title=news_highlight_title or "",
                news_highlight_body=news_highlight_body or "",
                news_highlight_image_url=news_highlight_image_url or "",
                news_items=news_items or [],
                news_cta_url=news_cta_url or "",
                news_cta_label=news_cta_label or "",
                engagement_intro=engagement_intro or "",
                engagement_topic=engagement_topic or "",
                engagement_description=engagement_description or "",
                engagement_btn_label=engagement_btn_label or "",
                engagement_btn_url=engagement_btn_url or "",
                sysupdate_date_time=sysupdate_date_time or "",
                sysupdate_intro=sysupdate_intro or "",
                sysupdate_datetime_utc=sysupdate_datetime_utc or "",
                sysupdate_duration=sysupdate_duration or "",
                sysupdate_impact=sysupdate_impact or "",
                impact_items=impact_items or [],
            )
            return html_content, html_content, html_content

        if editor_tab != "fields" or not active_template:
            return no_update, no_update, no_update

        html_content = _build_html_from_fields(
            active_template,
            news_issue_date=news_issue_date or "",
            news_intro=news_intro or "",
            news_highlight_title=news_highlight_title or "",
            news_highlight_body=news_highlight_body or "",
            news_highlight_image_url=news_highlight_image_url or "",
            news_items=news_items or [],
            news_cta_url=news_cta_url or "",
            news_cta_label=news_cta_label or "",
            engagement_intro=engagement_intro or "",
            engagement_topic=engagement_topic or "",
            engagement_description=engagement_description or "",
            engagement_btn_label=engagement_btn_label or "",
            engagement_btn_url=engagement_btn_url or "",
            sysupdate_date_time=sysupdate_date_time or "",
            sysupdate_intro=sysupdate_intro or "",
            sysupdate_datetime_utc=sysupdate_datetime_utc or "",
            sysupdate_duration=sysupdate_duration or "",
            sysupdate_impact=sysupdate_impact or "",
            impact_items=impact_items or [],
        )
        return html_content, html_content, no_update

    # -----------------------------------------------------------------------
    # "Enable HTML Editing…" button in the raw panel → open confirmation modal.
    # The banner is hidden once HTML mode is active (handled by
    # update_html_mode_banner below).
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-switch-html-modal", "is_open", allow_duplicate=True),
        Input("bulk-email-enable-html-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def open_html_mode_modal(_n):
        return True

    # -----------------------------------------------------------------------
    # Hide the warning banner once HTML mode is active; show it otherwise
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-html-mode-banner", "is_open"),
        Input("bulk-email-in-html-mode", "data"),
    )
    def update_html_mode_banner(in_html_mode):
        return not bool(in_html_mode)

    # -----------------------------------------------------------------------
    # Confirm switch to HTML mode — save both drafts, lock Fields tab
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-switch-html-modal", "is_open", allow_duplicate=True),
            Output("bulk-email-editor-tabs", "value", allow_duplicate=True),
            Output("bulk-email-in-html-mode", "data", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-name", "value", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
            Output("bulk-email-switch-modal-alert", "children", allow_duplicate=True),
            Output("bulk-email-switch-modal-alert", "is_open", allow_duplicate=True),
        ],
        Input("bulk-email-confirm-html-mode-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-name", "value"),
            State("bulk-email-subject", "value"),
            State("bulk-email-category-select", "value"),
            State("bulk-email-active-template", "data"),
            State("bulk-email-html-source", "value"),
            # News fields
            State("bulk-email-field-news-issue-date", "value"),
            State("bulk-email-field-news-intro", "value"),
            State("bulk-email-field-news-highlight-title", "value"),
            State("bulk-email-field-news-highlight-body", "value"),
            State("bulk-email-field-news-highlight-image-url", "value"),
            State("bulk-email-field-news-cta-url", "value"),
            State("bulk-email-field-news-cta-label", "value"),
            # Engagement fields
            State("bulk-email-field-engagement-intro", "value"),
            State("bulk-email-field-engagement-topic", "value"),
            State("bulk-email-field-engagement-description", "value"),
            State("bulk-email-field-engagement-btn-label", "value"),
            State("bulk-email-field-engagement-btn-url", "value"),
            # System update fields
            State("bulk-email-field-sysupdate-date-time", "value"),
            State("bulk-email-field-sysupdate-intro", "value"),
            State("bulk-email-field-sysupdate-datetime-utc", "value"),
            State("bulk-email-field-sysupdate-duration", "value"),
            State("bulk-email-field-sysupdate-impact", "value"),
            # Dynamic stores
            State("bulk-email-news-items-store", "data"),
            State("bulk-email-impact-items-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def confirm_switch_to_html_mode(
        _n,
        token,
        name,
        subject,
        subscription_type,
        active_template,
        raw_html,
        news_issue_date,
        news_intro,
        news_highlight_title,
        news_highlight_body,
        news_highlight_image_url,
        news_cta_url,
        news_cta_label,
        engagement_intro,
        engagement_topic,
        engagement_description,
        engagement_btn_label,
        engagement_btn_url,
        sysupdate_date_time,
        sysupdate_intro,
        sysupdate_datetime_utc,
        sysupdate_duration,
        sysupdate_impact,
        news_items,
        impact_items,
    ):
        import re

        def _modal_error(msg):
            """Keep modal open, surface the error in the modal's own alert."""
            return (
                True,  # modal stays open
                no_update,  # editor-tabs
                no_update,  # in-html-mode
                no_update,  # loaded-draft-id
                no_update,  # name
                no_update,  # draft-mode-label
                no_update,  # send-select options
                no_update,  # load-draft-select options
                no_update,  # composer-alert children
                False,  # composer-alert is_open (hide so modal is readable)
                no_update,  # composer-alert color
                msg,  # modal-alert children
                True,  # modal-alert is_open
            )

        if not _n:
            return (no_update,) * 13

        if not token:
            return _modal_error("Not authenticated.")
        if not name:
            return _modal_error("A draft name is required before switching. Enter a name above.")
        if not subject:
            return _modal_error(
                "A subject line is required before switching. Enter a subject above."
            )

        base_name = (
            re.sub(
                r"\s*\((?:templated|html)\)\s*$",
                "",
                (name or "Draft").strip(),
                flags=re.IGNORECASE,
            ).strip()
            or "Draft"
        )
        html_draft_name = f"{base_name} (html)"
        templated_draft_name = f"{base_name} (templated)"

        try:
            html_content = ""
            saved_templated = False

            if active_template:
                html_content = _build_html_from_fields(
                    active_template,
                    news_issue_date=news_issue_date or "",
                    news_intro=news_intro or "",
                    news_highlight_title=news_highlight_title or "",
                    news_highlight_body=news_highlight_body or "",
                    news_highlight_image_url=news_highlight_image_url or "",
                    news_items=news_items or [],
                    news_cta_url=news_cta_url or "",
                    news_cta_label=news_cta_label or "",
                    engagement_intro=engagement_intro or "",
                    engagement_topic=engagement_topic or "",
                    engagement_description=engagement_description or "",
                    engagement_btn_label=engagement_btn_label or "",
                    engagement_btn_url=engagement_btn_url or "",
                    sysupdate_date_time=sysupdate_date_time or "",
                    sysupdate_intro=sysupdate_intro or "",
                    sysupdate_datetime_utc=sysupdate_datetime_utc or "",
                    sysupdate_duration=sysupdate_duration or "",
                    sysupdate_impact=sysupdate_impact or "",
                    impact_items=impact_items or [],
                )
                fields_data = {
                    "template": active_template,
                    "news_issue_date": news_issue_date,
                    "news_intro": news_intro,
                    "news_highlight_title": news_highlight_title,
                    "news_highlight_body": news_highlight_body,
                    "news_highlight_image_url": news_highlight_image_url,
                    "news_cta_url": news_cta_url,
                    "news_cta_label": news_cta_label,
                    "engagement_intro": engagement_intro,
                    "engagement_topic": engagement_topic,
                    "engagement_description": engagement_description,
                    "engagement_btn_label": engagement_btn_label,
                    "engagement_btn_url": engagement_btn_url,
                    "sysupdate_date_time": sysupdate_date_time,
                    "sysupdate_intro": sysupdate_intro,
                    "sysupdate_datetime_utc": sysupdate_datetime_utc,
                    "sysupdate_duration": sysupdate_duration,
                    "sysupdate_impact": sysupdate_impact,
                    "news_items": news_items or [],
                    "impact_items": impact_items or [],
                }
                _api(
                    token,
                    "POST",
                    "/bulk-email",
                    json={
                        "name": templated_draft_name,
                        "subject": subject,
                        "html_content": html_content,
                        "subscription_type": subscription_type or None,
                        "fields_data": fields_data,
                    },
                )
                saved_templated = True
            else:
                html_content = raw_html or ""

            # Save the (html) draft — no fields_data
            html_resp = _api(
                token,
                "POST",
                "/bulk-email",
                json={
                    "name": html_draft_name,
                    "subject": subject,
                    "html_content": html_content,
                    "subscription_type": subscription_type or None,
                    "fields_data": None,
                },
            )
            if html_resp.status_code not in (200, 201):
                return _modal_error(f"Error saving HTML draft: {_extract_error(html_resp)}")

            html_draft_id = html_resp.json().get("data", {}).get("id")
            options = _load_draft_options(token)
            if saved_templated:
                saved_msg = (
                    f"Saved '{templated_draft_name}' and '{html_draft_name}'. "
                    "Now editing the (html) version."
                )
            else:
                saved_msg = f"Saved '{html_draft_name}'."

            return (
                False,  # close modal
                "raw",  # switch to raw tab
                True,  # set in-html-mode = True
                html_draft_id,  # now editing the (html) draft
                html_draft_name,  # update name field
                f"Editing: {html_draft_name}",  # draft-mode-label
                options,  # send-select options
                options,  # load-draft-select options
                saved_msg,  # composer-alert
                True,
                "success",
                "",  # clear modal-alert
                False,
            )
        except Exception:
            logger.exception("Failed to save drafts during HTML mode switch")
            return _modal_error("An unexpected error occurred.")

    # -----------------------------------------------------------------------
    # Cancel HTML-mode switch — close the modal
    # -----------------------------------------------------------------------
    app.clientside_callback(
        "function(n) { return false; }",
        Output("bulk-email-switch-html-modal", "is_open", allow_duplicate=True),
        Input("bulk-email-cancel-html-mode-btn", "n_clicks"),
        prevent_initial_call=True,
    )

    # -----------------------------------------------------------------------
    # Disable the Template Fields tab once in HTML mode
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-fields-tab", "disabled"),
        Input("bulk-email-in-html-mode", "data"),
    )
    def update_fields_tab_disabled(in_html_mode):
        return bool(in_html_mode)

    # -----------------------------------------------------------------------
    # Dash → Monaco: push value into the editor when Python sets it
    # (fires whenever a server callback writes to bulk-email-html-source.value)
    # -----------------------------------------------------------------------
    app.clientside_callback(
        """
        function(value) {
            var editor = window._bulkEmailEditor;
            if (editor && value !== undefined && editor.getValue() !== (value || '')) {
                editor.setValue(value || '');
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("bulk-email-cm-sync-trigger", "data"),
        Input("bulk-email-html-source", "value"),
        prevent_initial_call=True,
    )

    # -----------------------------------------------------------------------
    # Format HTML button — triggers Monaco's built-in HTML formatter
    # -----------------------------------------------------------------------
    app.clientside_callback(
        """
        function(n_clicks) {
            var editor = window._bulkEmailEditor;
            if (n_clicks && editor) {
                var action = editor.getAction('editor.action.formatDocument');
                if (action) { action.run(); }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("bulk-email-cm-sync-trigger", "data", allow_duplicate=True),
        Input("bulk-email-format-html-btn", "n_clicks"),
        prevent_initial_call=True,
    )


# ---------------------------------------------------------------------------
# Private helpers (module-level to keep callbacks concise)
# ---------------------------------------------------------------------------


def _build_filter_criteria(roles, verified, min_created, max_created, min_activity, max_activity):
    criteria = {}
    if roles:
        criteria["roles"] = roles
    if verified and verified not in ("", "any"):
        criteria["email_verified"] = verified == "true"
    if min_created:
        criteria["min_created_at"] = min_created
    if max_created:
        criteria["max_created_at"] = max_created
    if min_activity:
        criteria["min_last_activity_at"] = min_activity
    if max_activity:
        criteria["max_last_activity_at"] = max_activity
    return criteria


def _rlist_label(r):
    desc = (r.get("description") or "").strip()
    return f"{r['name']} — {desc}" if desc else r["name"]


def _load_recipient_lists(token):
    try:
        resp = make_authenticated_request("/bulk-email/recipient-list", token)
        return _ok_rows(resp)
    except Exception:
        logger.exception("Failed to load recipient lists")
        return []


def _draft_label(c):
    subject = (c.get("subject") or "").strip()
    return f"{c['name']} — {subject}" if subject else c["name"]


def _load_draft_options(token):
    try:
        resp = make_authenticated_request("/bulk-email", token)
        bulk_emails = _ok_rows(resp)
        return [
            {"label": _draft_label(c), "value": c["id"]}
            for c in bulk_emails
            if c.get("status") == "DRAFT"
        ]
    except Exception:
        logger.exception("Failed to load draft options")
        return []


def _extract_error(resp):
    try:
        body = resp.json()
        return body.get("message") or body.get("error") or resp.text
    except Exception:
        return resp.text or "Unknown error"
