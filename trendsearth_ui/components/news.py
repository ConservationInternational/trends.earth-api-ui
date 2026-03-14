"""News banner component for displaying announcements in the dashboard."""

from dash import dcc, html
import dash_bootstrap_components as dbc

# News type colors and configurations
NEWS_TYPE_STYLES = {
    "info": {
        "color": "info",
        "icon": "fas fa-info-circle",
        "bg_class": "bg-info bg-opacity-10",
    },
    "warning": {
        "color": "warning",
        "icon": "fas fa-exclamation-triangle",
        "bg_class": "bg-warning bg-opacity-10",
    },
    "success": {
        "color": "success",
        "icon": "fas fa-check-circle",
        "bg_class": "bg-success bg-opacity-10",
    },
    "danger": {
        "color": "danger",
        "icon": "fas fa-exclamation-circle",
        "bg_class": "bg-danger bg-opacity-10",
    },
    "announcement": {
        "color": "primary",
        "icon": "fas fa-bullhorn",
        "bg_class": "bg-primary bg-opacity-10",
    },
    "update": {
        "color": "secondary",
        "icon": "fas fa-sync-alt",
        "bg_class": "bg-secondary bg-opacity-10",
    },
}


def create_news_banner():
    """Create the news banner container that will be populated by callbacks.

    Returns:
        A Dash component containing the news banner structure and stores.
    """
    return html.Div(
        [
            # Store for news items
            dcc.Store(id="news-items-store", data=[]),
            # Store for current news index
            dcc.Store(id="news-current-index", data=0),
            # Store for dismissed news IDs (local tracking)
            dcc.Store(id="news-dismissed-ids", data=[]),
            # Loading state
            dcc.Loading(
                id="news-loading",
                type="circle",
                children=[
                    # News container - will be populated by callback
                    html.Div(
                        id="news-banner-container",
                        style={"display": "none"},  # Hidden until news is loaded
                    ),
                ],
                style={"minHeight": "0"},
            ),
            # Interval for refreshing news (every 5 minutes)
            dcc.Interval(
                id="news-refresh-interval",
                interval=5 * 60 * 1000,  # 5 minutes
                n_intervals=0,
            ),
        ],
        id="news-wrapper",
        className="mb-3",
    )


def create_news_item_card(news_item, current_index, total_count):
    """Create a card for displaying a single news item.

    Args:
        news_item: Dictionary containing news item data
        current_index: Current index in the news list (0-based)
        total_count: Total number of news items

    Returns:
        A dbc.Card component displaying the news item
    """
    if not news_item:
        return None

    news_type = news_item.get("news_type", "info")
    style_config = NEWS_TYPE_STYLES.get(news_type, NEWS_TYPE_STYLES["info"])

    title = news_item.get("title", "")
    message = news_item.get("message", "")
    link_url = news_item.get("link_url")
    news_id = news_item.get("id")

    # Build message content
    message_content = [html.P(message, className="mb-0 small")]

    # Add link if present
    if link_url:
        message_content.append(
            html.A(
                [html.I(className="fas fa-external-link-alt me-1"), "Learn more"],
                href=link_url,
                target="_blank",
                rel="noopener noreferrer",
                className="small ms-2",
            )
        )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            # Icon column
                            dbc.Col(
                                html.I(
                                    className=f"{style_config['icon']} fa-lg",
                                    style={"opacity": "0.8"},
                                ),
                                width="auto",
                                className="d-flex align-items-center pe-2",
                            ),
                            # Content column
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Strong(title, className="me-2"),
                                            *message_content,
                                        ],
                                        className="d-flex flex-wrap align-items-center",
                                    ),
                                ],
                                className="flex-grow-1",
                            ),
                            # Navigation and dismiss column
                            dbc.Col(
                                html.Div(
                                    [
                                        # Navigation buttons (only if multiple items)
                                        html.Div(
                                            [
                                                dbc.Button(
                                                    html.I(className="fas fa-chevron-left"),
                                                    id="news-prev-btn",
                                                    color="link",
                                                    size="sm",
                                                    className="p-1",
                                                    disabled=current_index == 0,
                                                ),
                                                html.Span(
                                                    f"{current_index + 1}/{total_count}",
                                                    className="mx-2 small text-muted",
                                                ),
                                                dbc.Button(
                                                    html.I(className="fas fa-chevron-right"),
                                                    id="news-next-btn",
                                                    color="link",
                                                    size="sm",
                                                    className="p-1",
                                                    disabled=current_index >= total_count - 1,
                                                ),
                                            ],
                                            className="d-flex align-items-center me-3",
                                            style={
                                                "display": "flex" if total_count > 1 else "none"
                                            },
                                        ),
                                        # Dismiss button
                                        dbc.Button(
                                            html.I(className="fas fa-times"),
                                            id={"type": "news-dismiss-btn", "index": news_id},
                                            color="link",
                                            size="sm",
                                            className="p-1 text-muted",
                                            title="Dismiss this news item",
                                        ),
                                    ],
                                    className="d-flex align-items-center",
                                ),
                                width="auto",
                                className="d-flex align-items-center",
                            ),
                        ],
                        className="align-items-center g-0",
                    ),
                ],
                className="py-2 px-3",
            ),
        ],
        color=style_config["color"],
        outline=True,
        className=f"border-{style_config['color']} {style_config['bg_class']}",
    )


def create_empty_news_banner():
    """Create an empty/hidden news banner placeholder."""
    return html.Div(style={"display": "none"})
