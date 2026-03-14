"""News-related callbacks for fetching and displaying news items."""

import logging

from dash import ALL, Input, Output, State, callback_context, no_update

from ..components.news import create_empty_news_banner, create_news_item_card
from ..config import get_api_base
from ..utils.http_client import get_session

logger = logging.getLogger(__name__)


def fetch_news_items(token, api_environment, platform="api-ui"):
    """Fetch news items from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production or staging)
        platform: Platform filter (api-ui, webapp, app)

    Returns:
        List of news items or empty list on error
    """
    if not token:
        logger.debug("No token provided, skipping news fetch")
        return []

    try:
        api_base = get_api_base(api_environment)
        url = f"{api_base}/news"
        params = {"platform": platform}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        session = get_session()
        response = session.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            news_items = data.get("data", [])
            logger.debug("Fetched %d news items", len(news_items))
            return news_items
        elif response.status_code == 401:
            logger.warning("Unauthorized when fetching news")
            return []
        else:
            logger.warning("Failed to fetch news: %d %s", response.status_code, response.text)
            return []

    except Exception as e:
        logger.error("Error fetching news items: %s", e)
        return []


def dismiss_news_item(token, api_environment, news_id):
    """Dismiss a news item for the current user.

    Args:
        token: JWT authentication token
        api_environment: API environment
        news_id: ID of the news item to dismiss

    Returns:
        True if successful, False otherwise
    """
    if not token or not news_id:
        return False

    try:
        api_base = get_api_base(api_environment)
        url = f"{api_base}/news/{news_id}/dismiss"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        session = get_session()
        response = session.post(url, headers=headers, timeout=10)

        if response.status_code in (200, 201):
            logger.debug("Successfully dismissed news item %s", news_id)
            return True
        else:
            logger.warning(
                "Failed to dismiss news %s: %d %s", news_id, response.status_code, response.text
            )
            return False

    except Exception as e:
        logger.error("Error dismissing news item: %s", e)
        return False


def register_callbacks(app):
    """Register news-related callbacks."""

    @app.callback(
        [
            Output("news-items-store", "data"),
            Output("news-current-index", "data", allow_duplicate=True),
        ],
        [
            Input("token-store", "data"),
            Input("news-refresh-interval", "n_intervals"),
        ],
        [
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def load_news_items(token, _n_intervals, api_environment):
        """Load news items when user logs in or on refresh interval."""
        if not token:
            return [], 0

        news_items = fetch_news_items(token, api_environment, platform="api-ui")
        return news_items, 0

    @app.callback(
        Output("news-banner-container", "children"),
        Output("news-banner-container", "style"),
        [
            Input("news-items-store", "data"),
            Input("news-current-index", "data"),
        ],
        prevent_initial_call=True,
    )
    def render_news_banner(news_items, current_index):
        """Render the news banner based on stored news items."""
        if not news_items:
            return create_empty_news_banner(), {"display": "none"}

        # Ensure current_index is valid
        if current_index is None:
            current_index = 0
        current_index = max(0, min(current_index, len(news_items) - 1))

        current_item = news_items[current_index]
        card = create_news_item_card(current_item, current_index, len(news_items))

        return card, {"display": "block"}

    @app.callback(
        Output("news-current-index", "data", allow_duplicate=True),
        [
            Input("news-prev-btn", "n_clicks"),
            Input("news-next-btn", "n_clicks"),
        ],
        [
            State("news-current-index", "data"),
            State("news-items-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def navigate_news(prev_clicks, next_clicks, current_index, news_items):
        """Handle navigation between news items."""
        if not news_items:
            return 0

        ctx = callback_context
        if not ctx.triggered:
            return no_update

        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if current_index is None:
            current_index = 0

        max_index = len(news_items) - 1

        if triggered_id == "news-prev-btn" and prev_clicks:
            new_index = max(0, current_index - 1)
        elif triggered_id == "news-next-btn" and next_clicks:
            new_index = min(max_index, current_index + 1)
        else:
            return no_update

        return new_index

    @app.callback(
        [
            Output("news-items-store", "data", allow_duplicate=True),
            Output("news-current-index", "data", allow_duplicate=True),
        ],
        [
            Input({"type": "news-dismiss-btn", "index": ALL}, "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("api-environment-store", "data"),
            State("news-items-store", "data"),
            State("news-current-index", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_news_dismiss(n_clicks_list, token, api_environment, news_items, current_index):
        """Handle dismissing a news item."""
        if not n_clicks_list or all(n is None for n in n_clicks_list):
            return no_update, no_update

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update

        # Find which button was clicked
        triggered = ctx.triggered[0]
        if not triggered["value"]:
            return no_update, no_update

        # Extract news_id from the triggered prop_id
        try:
            prop_id = triggered["prop_id"]
            # Format: {"type":"news-dismiss-btn","index":"uuid-here"}.n_clicks
            import json

            id_str = prop_id.rsplit(".", 1)[0]
            id_dict = json.loads(id_str)
            news_id = id_dict.get("index")
        except (json.JSONDecodeError, KeyError, IndexError):
            logger.error("Failed to parse triggered prop_id: %s", triggered)
            return no_update, no_update

        if not news_id:
            return no_update, no_update

        # Dismiss the news item via API
        success = dismiss_news_item(token, api_environment, news_id)

        if success:
            # Remove the dismissed item from the list
            updated_items = [item for item in news_items if item.get("id") != news_id]

            # Adjust current index
            if not updated_items:
                new_index = 0
            elif current_index >= len(updated_items):
                new_index = max(0, len(updated_items) - 1)
            else:
                new_index = current_index

            return updated_items, new_index

        return no_update, no_update
