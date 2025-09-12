"""JSON utilities for rendering and processing."""

import json
from typing import Any, Optional

from dash import html
import dash_bootstrap_components as dbc


def render_json_tree(data, level=0, parent_id="root", enable_interactive=True):
    """Render JSON data as an enhanced interactive tree structure.

    Args:
        data: The JSON data to render
        level: Current nesting level for styling
        parent_id: Parent node ID for generating unique IDs
        enable_interactive: Whether to enable interactive features like search and copy

    Returns:
        Dash component tree representing the JSON data
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return _render_primitive_value(data, level, f"{parent_id}-string")

    # Create container with controls if this is the root level and interactive features are enabled
    if level == 0 and enable_interactive:
        return _render_json_viewer_with_controls(data, parent_id)

    return _render_json_node(data, level, parent_id)


def _render_json_viewer_with_controls(data: Any, parent_id: str = "root") -> html.Div:
    """Render the JSON viewer with search and control features."""
    return html.Div(
        [
            # Control panel
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id=f"{parent_id}-json-search",
                                                placeholder="Search keys or values...",
                                                type="text",
                                                size="sm",
                                                value="",
                                            ),
                                            dbc.Button(
                                                [html.I(className="fas fa-search")],
                                                id=f"{parent_id}-search-btn",
                                                color="outline-secondary",
                                                size="sm",
                                            ),
                                        ],
                                        size="sm",
                                    )
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-expand-arrows-alt"),
                                                    " Expand All",
                                                ],
                                                id=f"{parent_id}-expand-all",
                                                color="outline-primary",
                                                size="sm",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-compress-arrows-alt"),
                                                    " Collapse All",
                                                ],
                                                id=f"{parent_id}-collapse-all",
                                                color="outline-secondary",
                                                size="sm",
                                            ),
                                        ],
                                        size="sm",
                                    )
                                ],
                                width=6,
                                className="d-flex justify-content-end",
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Status message
                    html.Div(
                        id=f"{parent_id}-search-status",
                        className="mb-2 text-muted",
                        style={"fontSize": "12px", "display": "none"},
                    ),
                ],
                className="json-controls mb-3 p-2",
                style={
                    "backgroundColor": "#f8f9fa",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "0.375rem",
                },
            ),
            # JSON tree container
            html.Div(
                [_render_json_node(data, 0, parent_id)],
                id=f"{parent_id}-json-container",
                className="json-tree-container",
                style={
                    "maxHeight": "60vh",
                    "overflowY": "auto",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "0.375rem",
                    "padding": "1rem",
                    "backgroundColor": "#ffffff",
                },
            ),
            # Hidden stores for data
            html.Div(
                [
                    html.Div(id=f"{parent_id}-expand-trigger", style={"display": "none"}),
                    html.Div(id=f"{parent_id}-collapse-trigger", style={"display": "none"}),
                    html.Div(id=f"{parent_id}-search-trigger", style={"display": "none"}),
                ],
                style={"display": "none"},
            ),
        ],
        className="enhanced-json-viewer",
    )


def _render_json_node(data: Any, level: int, parent_id: str) -> html.Div:
    """Render a JSON node (object, array, or primitive)."""
    if isinstance(data, dict):
        return _render_object(data, level, parent_id)
    elif isinstance(data, list):
        return _render_array(data, level, parent_id)
    else:
        return _render_primitive_value(data, level, parent_id)


def _render_object(data: dict[str, Any], level: int, parent_id: str) -> html.Div:
    """Render a JSON object with collapsible key-value pairs."""
    if not data:
        return html.Div(
            [
                html.Span("{}", className="json-empty-object"),
                _render_type_badge("object", len(data)),
            ],
            className="json-node json-object-empty",
            style={"marginLeft": f"{level * 12}px"},
        )

    items = []
    for k, v in data.items():
        node_id = f"{parent_id}-{k}"
        is_complex = isinstance(v, (dict, list))

        if is_complex:
            # Create collapsible item for complex values
            summary_content = [
                html.Span(f'"{k}"', className="json-key"),
                html.Span(": ", className="json-colon"),
                _render_type_badge(_get_type_name(v), _get_size(v)),
            ]

            items.append(
                html.Details(
                    [
                        html.Summary(
                            summary_content,
                            className="json-summary",
                            style={"cursor": "pointer", "marginLeft": f"{level * 12}px"},
                        ),
                        html.Div(
                            _render_json_node(v, level + 1, node_id),
                            className="json-details-content",
                            style={"marginTop": "3px"},
                        ),
                    ],
                    open=(level < 2),
                    className="json-details",
                    id=node_id,
                )
            )
        else:
            # Simple key-value pair
            items.append(_render_simple_property(k, v, level, node_id))

    return html.Div(
        items,
        className="json-object",
    )


def _render_array(data: list[Any], level: int, parent_id: str) -> html.Div:
    """Render a JSON array with collapsible items."""
    if not data:
        return html.Div(
            [
                html.Span("[]", className="json-empty-array"),
                _render_type_badge("array", len(data)),
            ],
            className="json-node json-array-empty",
            style={"marginLeft": f"{level * 12}px"},
        )

    items = []
    for idx, v in enumerate(data):
        node_id = f"{parent_id}-{idx}"
        is_complex = isinstance(v, (dict, list))

        if is_complex:
            # Create collapsible item for complex values
            summary_content = [
                html.Span(f"[{idx}]", className="json-index"),
                html.Span(": ", className="json-colon"),
                _render_type_badge(_get_type_name(v), _get_size(v)),
            ]

            items.append(
                html.Details(
                    [
                        html.Summary(
                            summary_content,
                            className="json-summary",
                            style={"cursor": "pointer", "marginLeft": f"{level * 12}px"},
                        ),
                        html.Div(
                            _render_json_node(v, level + 1, node_id),
                            className="json-details-content",
                            style={"marginTop": "3px"},
                        ),
                    ],
                    open=(level < 2),
                    className="json-details",
                    id=node_id,
                )
            )
        else:
            # Simple array item
            items.append(_render_simple_array_item(idx, v, level, node_id))

    return html.Div(
        items,
        className="json-array",
    )


def _render_simple_property(key: str, value: Any, level: int, node_id: str) -> html.Div:
    """Render a simple key-value property with copy functionality."""
    value_type = _get_type_name(value)
    formatted_value = _format_primitive_value(value)

    return html.Div(
        [
            html.Span(f'"{key}"', className="json-key"),
            html.Span(": ", className="json-colon"),
            html.Span(
                formatted_value,
                className=f"json-value json-value-{value_type}",
            ),
            dbc.Button(
                html.I(className="fas fa-copy"),
                className="json-copy-btn",
                color="outline-secondary",
                size="sm",
                style={"padding": "0.1rem 0.3rem", "fontSize": "0.7rem", "marginLeft": "8px"},
                id={"type": "copy-btn", "index": node_id, "value": str(value)},
                title="Copy value",
            ),
        ],
        className="json-property",
        style={"marginLeft": f"{level * 12}px", "marginBottom": "2px"},
    )


def _render_simple_array_item(index: int, value: Any, level: int, node_id: str) -> html.Div:
    """Render a simple array item with copy functionality."""
    value_type = _get_type_name(value)
    formatted_value = _format_primitive_value(value)

    return html.Div(
        [
            html.Span(f"[{index}]", className="json-index"),
            html.Span(": ", className="json-colon"),
            html.Span(
                formatted_value,
                className=f"json-value json-value-{value_type}",
            ),
            dbc.Button(
                html.I(className="fas fa-copy"),
                className="json-copy-btn",
                color="outline-secondary",
                size="sm",
                style={"padding": "0.1rem 0.3rem", "fontSize": "0.7rem", "marginLeft": "8px"},
                id={"type": "copy-btn", "index": node_id, "value": str(value)},
                title="Copy value",
            ),
        ],
        className="json-array-item",
        style={"marginLeft": f"{level * 12}px", "marginBottom": "2px"},
    )


def _render_primitive_value(value: Any, level: int, node_id: str) -> html.Div:
    """Render a primitive value (string, number, boolean, null)."""
    value_type = _get_type_name(value)
    formatted_value = _format_primitive_value(value)

    return html.Div(
        [
            html.Span(
                formatted_value,
                className=f"json-value json-value-{value_type}",
            ),
            dbc.Button(
                html.I(className="fas fa-copy"),
                className="json-copy-btn",
                color="outline-secondary",
                size="sm",
                style={"padding": "0.1rem 0.3rem", "fontSize": "0.7rem", "marginLeft": "8px"},
                id={"type": "copy-btn", "index": node_id, "value": str(value)},
                title="Copy value",
            ),
        ],
        className="json-primitive",
        style={"marginLeft": f"{level * 12}px"},
    )


def _render_type_badge(type_name: str, size: Optional[int] = None) -> html.Span:
    """Render a small badge showing the type and size of a JSON structure."""
    badge_text = type_name
    if size is not None:
        badge_text += f" ({size})"

    color_map = {
        "object": "primary",
        "array": "success",
        "string": "info",
        "number": "warning",
        "boolean": "secondary",
        "null": "dark",
    }

    return html.Span(
        badge_text,
        className=f"badge bg-{color_map.get(type_name, 'secondary')} ms-2",
        style={"fontSize": "0.65rem"},
    )


def _format_primitive_value(value: Any) -> str:
    """Format a primitive value for display."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return f'"{value}"'
    else:
        return str(value)


def _get_type_name(value: Any) -> str:
    """Get the JSON type name for a value."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, dict):
        return "object"
    elif isinstance(value, list):
        return "array"
    else:
        return "unknown"


def _get_size(value: Any) -> Optional[int]:
    """Get the size of a collection (dict or list)."""
    if isinstance(value, (dict, list)):
        return len(value)
    return None
