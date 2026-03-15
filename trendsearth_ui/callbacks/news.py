"""News-related callbacks for fetching and displaying news items."""

import logging
import time

from dash import ALL, Input, Output, State, callback_context, no_update

from ..components.news import create_empty_news_banner, create_news_item_card
from ..config import get_api_base
from ..utils.http_client import get_session

logger = logging.getLogger(__name__)

# Minimum time between automatic fetches (24 hours in seconds)
MIN_FETCH_INTERVAL = 24 * 60 * 60


def fetch_news_items(api_environment, platform="api-ui"):
    """Fetch news items from the API.

    Args:
        api_environment: API environment (production or staging)
        platform: Platform filter (api-ui, webapp, app)

    Returns:
        List of news items or empty list on error
    """
    try:
        api_base = get_api_base(api_environment)
        url = f"{api_base}/news"
        params = {"platform": platform}

        headers = {
            "Content-Type": "application/json",
        }

        session = get_session()
        response = session.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            news_items = data.get("data", [])
            logger.debug("Fetched %d news items", len(news_items))
            return news_items
        else:
            logger.warning("Failed to fetch news: %d %s", response.status_code, response.text)
            return []

    except Exception as e:
        logger.error("Error fetching news items: %s", e)
        return []


def filter_dismissed_items(news_items, dismissed_ids):
    """Filter out dismissed news items.

    Args:
        news_items: List of news item dictionaries
        dismissed_ids: List of dismissed news item IDs

    Returns:
        Filtered list of news items
    """
    if not dismissed_ids:
        return news_items
    dismissed_set = set(dismissed_ids)
    return [item for item in news_items if item.get("id") not in dismissed_set]


def should_fetch_news(last_fetch_timestamp):
    """Check if enough time has passed to fetch news again.

    Args:
        last_fetch_timestamp: Unix timestamp of last fetch, or None

    Returns:
        True if should fetch, False otherwise
    """
    if last_fetch_timestamp is None:
        return True
    current_time = time.time()
    return (current_time - last_fetch_timestamp) >= MIN_FETCH_INTERVAL


def register_callbacks(app):
    """Register news-related callbacks."""

    @app.callback(
        [
            Output("news-items-store", "data"),
            Output("news-current-index", "data", allow_duplicate=True),
            Output("news-last-fetch", "data", allow_duplicate=True),
        ],
        [
            Input("token-store", "data"),
            Input("news-refresh-interval", "n_intervals"),
            Input("news-refresh-btn", "n_clicks"),
        ],
        [
            State("api-environment-store", "data"),
            State("news-last-fetch", "data"),
            State("news-dismissed-ids", "data"),
        ],
        prevent_initial_call=True,
    )
    def load_news_items(
        _token, _n_intervals, refresh_clicks, api_environment, last_fetch, dismissed_ids
    ):
        """Load news items when user logs in, on refresh interval, or manual refresh."""
        ctx = callback_context
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Manual refresh - always fetch
        is_manual_refresh = triggered_id == "news-refresh-btn" and refresh_clicks

        # Check if we should fetch (either manual or enough time has passed)
        if not is_manual_refresh and not should_fetch_news(last_fetch):
            logger.debug("Skipping news fetch - last fetch was recent")
            return no_update, no_update, no_update

        # Fetch news items (no auth required anymore)
        news_items = fetch_news_items(api_environment, platform="api-ui")

        # Filter out dismissed items
        filtered_items = filter_dismissed_items(news_items, dismissed_ids or [])

        # Update last fetch timestamp
        current_time = time.time()

        return filtered_items, 0, current_time

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
            Output("news-dismissed-ids", "data"),
        ],
        [
            Input({"type": "news-dismiss-btn", "index": ALL}, "n_clicks"),
        ],
        [
            State("news-items-store", "data"),
            State("news-current-index", "data"),
            State("news-dismissed-ids", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_news_dismiss(n_clicks_list, news_items, current_index, dismissed_ids):
        """Handle dismissing a news item (local storage only)."""
        if not n_clicks_list or all(n is None for n in n_clicks_list):
            return no_update, no_update, no_update

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update

        # Find which button was clicked
        triggered = ctx.triggered[0]
        if not triggered["value"]:
            return no_update, no_update, no_update

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
            return no_update, no_update, no_update

        if not news_id:
            return no_update, no_update, no_update

        # Add to dismissed IDs (local storage)
        updated_dismissed = list(dismissed_ids or [])
        if news_id not in updated_dismissed:
            updated_dismissed.append(news_id)
            logger.debug("Dismissed news item %s locally", news_id)

        # Remove the dismissed item from the current list
        updated_items = [item for item in news_items if item.get("id") != news_id]

        # Adjust current index
        if not updated_items:
            new_index = 0
        elif current_index >= len(updated_items):
            new_index = max(0, len(updated_items) - 1)
        else:
            new_index = current_index

        return updated_items, new_index, updated_dismissed
