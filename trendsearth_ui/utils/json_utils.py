"""JSON utilities for rendering and processing."""

import json

from dash import html


def render_json_tree(data, level=0, parent_id="root"):
    """Render JSON data as an interactive tree structure."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return html.Code(repr(data))
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            node_id = f"{parent_id}-{k}"
            if isinstance(v, (dict, list)):
                items.append(
                    html.Details(
                        [html.Summary(str(k)), render_json_tree(v, level + 1, node_id)],
                        open=(level < 1),
                    )
                )
            else:
                items.append(
                    html.Div(
                        [html.Span(f"{k}: "), html.Code(repr(v))],
                        style={"marginLeft": f"{level * 20}px"},
                    )
                )
        return html.Div(items)
    elif isinstance(data, list):
        items = []
        for idx, v in enumerate(data):
            node_id = f"{parent_id}-{idx}"
            if isinstance(v, (dict, list)):
                items.append(
                    html.Details(
                        [html.Summary(f"[{idx}]"), render_json_tree(v, level + 1, node_id)],
                        open=(level < 1),
                    )
                )
            else:
                items.append(
                    html.Div(
                        [html.Span(f"[{idx}]: "), html.Code(repr(v))],
                        style={"marginLeft": f"{level * 20}px"},
                    )
                )
        return html.Div(items)
    else:
        return html.Code(repr(data))
