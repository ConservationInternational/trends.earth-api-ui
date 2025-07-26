"""Log refresh and countdown callbacks."""

from dash import Input, Output, State, callback_context, html, no_update

from ..utils import parse_date


def register_callbacks(app):
    """Register log refresh and countdown callbacks."""

    @app.callback(
        Output("json-modal-body", "children", allow_duplicate=True),
        Output("json-modal-data", "data", allow_duplicate=True),
        Output("logs-countdown-interval", "n_intervals", allow_duplicate=True),
        [Input("refresh-logs-btn", "n_clicks"), Input("logs-refresh-interval", "n_intervals")],
        [
            State("current-log-context", "data"),
            State("token-store", "data"),
            State("json-modal", "is_open"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_logs(
        _refresh_clicks,
        _n_intervals,
        log_context,
        token,
        modal_open,
        user_timezone,
        _api_environment,
    ):
        """Refresh logs in the modal."""
        if not modal_open or not log_context or not token:
            return no_update, no_update, no_update

        log_type = log_context.get("type")
        log_id = log_context.get("id")

        if not log_type or not log_id:
            return no_update, no_update, no_update

        from ..utils.helpers import make_authenticated_request

        # Fetch logs based on type
        try:
            if log_type == "execution":
                resp = make_authenticated_request(f"/execution/{log_id}/log", token)
            elif log_type == "script":
                resp = make_authenticated_request(f"/script/{log_id}/log", token)
            else:
                return no_update, no_update, no_update
        except Exception as e:
            return (
                html.Pre(
                    f"Failed to fetch logs: {str(e)}",
                    style={"color": "red", "white-space": "pre-wrap"},
                ),
                {"logs": f"Error: {str(e)}"},
                0,
            )

        if resp.status_code != 200:
            return (
                html.Pre(
                    f"Failed to fetch logs: {resp.text}",
                    style={"whiteSpace": "pre-wrap", "fontSize": "12px", "color": "red"},
                ),
                None,
                no_update,
            )

        logs_data = resp.json().get("data", [])
        if not logs_data:
            return (
                html.Pre("No logs found.", style={"whiteSpace": "pre-wrap", "fontSize": "12px"}),
                None,
                no_update,
            )

        # Parse and format logs for display
        if isinstance(logs_data, list):
            parsed_logs = []
            for log in logs_data:
                if isinstance(log, dict):
                    register_date = log.get("register_date", "")
                    level = log.get("level", "")
                    text = log.get("text", "")

                    # Parse and format the date
                    formatted_date = parse_date(register_date, user_timezone) or register_date

                    # Create formatted log line
                    log_line = f"{formatted_date} - {level} - {text}"
                    parsed_logs.append((register_date, log_line))
                else:
                    # Fallback for non-dict log entries
                    parsed_logs.append(("", str(log)))

            # Sort by register_date in descending order
            parsed_logs.sort(key=lambda x: x[0], reverse=True)
            logs_content = "\n".join([log_line for _, log_line in parsed_logs])
        else:
            logs_content = str(logs_data)

        return (
            html.Pre(logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}),
            logs_data,
            0,
        )

    @app.callback(
        Output("logs-refresh-interval", "disabled", allow_duplicate=True),
        Output("refresh-logs-btn", "style", allow_duplicate=True),
        Output("logs-countdown-interval", "disabled", allow_duplicate=True),
        Output("logs-countdown-label", "style", allow_duplicate=True),
        Output("logs-countdown", "style", allow_duplicate=True),
        Input("json-modal", "is_open"),
        State("current-log-context", "data"),
        prevent_initial_call=True,
    )
    def toggle_refresh_interval(is_open, log_context):
        """Toggle refresh interval based on modal state."""
        if not is_open:
            # Modal is closed, disable interval and hide button/countdown
            return True, {"display": "none"}, True, {"display": "none"}, {"display": "none"}
        elif log_context and log_context.get("type") in ["execution", "script"]:
            # For executions, check if status is finished to disable auto-refresh
            if log_context.get("type") == "execution" and log_context.get("status") in [
                "FINISHED",
                "FAILED",
            ]:
                # Execution is finished, disable auto-refresh but show manual refresh button
                return (
                    True,
                    {"display": "inline-block"},
                    True,
                    {"display": "none"},
                    {"display": "none"},
                )
            else:
                # Modal is open and showing logs for running execution or script, enable interval and show button/countdown
                return (
                    False,
                    {"display": "inline-block"},
                    False,
                    {"display": "inline"},
                    {"display": "inline"},
                )
        else:
            # Modal is open but not showing logs, disable interval and hide button/countdown
            return True, {"display": "none"}, True, {"display": "none"}, {"display": "none"}

    @app.callback(
        Output("logs-countdown", "children"),
        Output("logs-refresh-interval", "n_intervals", allow_duplicate=True),
        [Input("logs-countdown-interval", "n_intervals"), Input("refresh-logs-btn", "n_clicks")],
        [State("json-modal", "is_open"), State("current-log-context", "data")],
        prevent_initial_call=True,
    )
    def update_logs_countdown(countdown_intervals, _refresh_clicks, modal_open, log_context):
        """Update the logs refresh countdown."""
        ctx = callback_context

        # If modal is not open or not showing logs, don't update
        if (
            not modal_open
            or not log_context
            or log_context.get("type") not in ["execution", "script"]
        ):
            return no_update, no_update

        # If execution is finished, don't update countdown (auto-refresh is disabled)
        if log_context.get("type") == "execution" and log_context.get("status") in [
            "FINISHED",
            "FAILED",
        ]:
            return no_update, no_update

        # If refresh button was clicked, reset countdown to 10 and trigger refresh
        if ctx.triggered and ctx.triggered[0]["prop_id"] == "refresh-logs-btn.n_clicks":
            return "10s", 0

        # Calculate remaining seconds (10 second cycle)
        remaining = 10 - (countdown_intervals % 10)
        return f"{remaining}s", no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
