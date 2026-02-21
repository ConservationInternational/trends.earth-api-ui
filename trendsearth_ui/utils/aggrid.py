"""Utility helpers for working with AG-Grid server-side data requests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
import copy
from typing import Any, Callable

from ..config import DEFAULT_PAGE_SIZE

FilterModel = Mapping[str, Any]
RequestData = Mapping[str, Any]
FilterHandler = Callable[[Mapping[str, Any]], tuple[str | None, dict[str, Any]]]


def _sanitize_value(value: Any, *, escape_like: bool = False) -> str:
    """Escape single quotes in filter values to minimise SQL injection risk.

    Args:
        value: The value to sanitize.
        escape_like: When True, also escape SQL LIKE wildcard characters
            (``%`` and ``_``) so they are treated as literals.
    """
    text = "" if value is None else str(value)
    text = text.replace("'", "''")
    if escape_like:
        text = text.replace("%", "\\%").replace("_", "\\_")
    return text


def compute_pagination(
    request_data: RequestData | None, *, default_page_size: int = DEFAULT_PAGE_SIZE
) -> tuple[int, int]:
    """Calculate page number and page size from an AG-Grid request payload."""
    request_data = request_data or {}
    try:
        start_row = int(request_data.get("startRow", 0) or 0)
    except (TypeError, ValueError):
        start_row = 0

    try:
        end_row = request_data.get("endRow")
        end_row = int(end_row) if end_row is not None else None
    except (TypeError, ValueError):
        end_row = None

    if end_row is None or end_row <= start_row:
        page_size = max(default_page_size, 1)
    else:
        page_size = max(end_row - start_row, 1)

    page = (start_row // page_size) + 1
    return page, page_size


def build_sort_clause(
    sort_model: Iterable[Mapping[str, Any]] | None,
    *,
    allowed_columns: Iterable[str] | None = None,
) -> str | None:
    """Translate AG-Grid sort model into an API sort string."""
    if not sort_model:
        return None

    allowed = set(allowed_columns) if allowed_columns else None
    clauses = []
    for definition in sort_model:
        column = definition.get("colId")
        if not column:
            continue
        if allowed is not None and column not in allowed:
            continue
        direction = definition.get("sort", "asc").lower()
        direction = "desc" if direction == "desc" else "asc"
        clauses.append(f"{column} {direction}")

    if not clauses:
        return None
    return ",".join(clauses)


def build_filter_clause(
    filter_model: FilterModel | None,
    *,
    allowed_columns: Iterable[str] | None = None,
    joiner: str = ",",
    custom_handlers: Mapping[str, FilterHandler] | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """Translate AG-Grid filters into API-compatible filter strings and params."""
    if not filter_model:
        return None, {}

    allowed = set(allowed_columns) if allowed_columns else None
    handlers = custom_handlers or {}

    clauses = []
    extra_params: dict[str, Any] = {}

    for raw_field, config in filter_model.items():
        if not isinstance(config, Mapping):
            continue
        field = str(raw_field)
        if allowed is not None and field not in allowed:
            continue

        handler = handlers.get(field)
        if handler:
            clause, params = handler(config)
            if clause:
                clauses.append(clause)
            if params:
                extra_params.update(params)
            continue

        filter_type = config.get("filterType")
        if filter_type == "set":
            values = config.get("values") or []
            or_clauses = [
                f"{field}='{_sanitize_value(val)}'" for val in values if val not in (None, "")
            ]
            if or_clauses:
                clauses.append(f"({' OR '.join(or_clauses)})")
        elif filter_type == "text":
            raw_value = config.get("filter", "").strip()
            if not raw_value:
                continue
            condition = config.get("type", "contains")
            if condition == "equals":
                value = _sanitize_value(raw_value)
                clauses.append(f"{field}='{value}'")
            elif condition == "notEquals":
                value = _sanitize_value(raw_value)
                clauses.append(f"{field}!='{value}'")
            elif condition == "startsWith":
                value = _sanitize_value(raw_value, escape_like=True)
                clauses.append(f"{field} like '{value}%'")
            elif condition == "endsWith":
                value = _sanitize_value(raw_value, escape_like=True)
                clauses.append(f"{field} like '%{value}'")
            else:  # contains / default
                value = _sanitize_value(raw_value, escape_like=True)
                clauses.append(f"{field} like '%{value}%'")
        elif filter_type == "number":
            value = config.get("filter")
            if value is None or value == "":
                continue
            try:
                # Preserve numeric formatting when possible
                numeric_value = float(value)
                if numeric_value.is_integer():
                    numeric_str = str(int(numeric_value))
                else:
                    numeric_str = str(numeric_value)
            except (TypeError, ValueError):
                numeric_str = _sanitize_value(value)
            condition = config.get("type", "equals")
            if condition == "equals":
                clauses.append(f"{field}={numeric_str}")
            elif condition == "notEqual":
                clauses.append(f"{field}!={numeric_str}")
            elif condition == "greaterThan":
                clauses.append(f"{field}>{numeric_str}")
            elif condition == "greaterThanOrEqual":
                clauses.append(f"{field}>={numeric_str}")
            elif condition == "lessThan":
                clauses.append(f"{field}<{numeric_str}")
            elif condition == "lessThanOrEqual":
                clauses.append(f"{field}<={numeric_str}")
            # Other numeric conditions (e.g. inRange) are not currently used
        elif filter_type == "date":
            # AG-Grid date column filter — translate to SQL-like comparison clauses
            raw_type = config.get("type", "equals")
            date_from = config.get("dateFrom")
            date_to = config.get("dateTo")

            if raw_type == "equals" and date_from:
                sanitized = _sanitize_value(date_from)
                clauses.append(f"{field}>='{sanitized}'")
                clauses.append(f"{field}<='{sanitized}'")
            elif raw_type in ("greaterThan", "greaterThanOrEqual") and date_from:
                sanitized = _sanitize_value(date_from)
                clauses.append(f"{field}>='{sanitized}'")
            elif raw_type in ("lessThan", "lessThanOrEqual") and date_from:
                sanitized = _sanitize_value(date_from)
                clauses.append(f"{field}<='{sanitized}'")
            elif raw_type == "inRange":
                if date_from:
                    sanitized_from = _sanitize_value(date_from)
                    clauses.append(f"{field}>='{sanitized_from}'")
                if date_to:
                    sanitized_to = _sanitize_value(date_to)
                    clauses.append(f"{field}<='{sanitized_to}'")
            elif raw_type == "notEqual" and date_from:
                sanitized = _sanitize_value(date_from)
                clauses.append(f"{field}!='{sanitized}'")
        # Boolean filter types are not currently supported

    clause_string = joiner.join(clauses) if clauses else None
    return clause_string, extra_params


def build_table_state(
    sort_model: Iterable[Mapping[str, Any]] | None,
    filter_model: FilterModel | None,
    sort_sql: str | None,
    filter_sql: str | None,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture table state needed for refreshing server-side data."""
    state: dict[str, Any] = {
        "sort_model": copy.deepcopy(list(sort_model)) if sort_model else [],
        "filter_model": copy.deepcopy(dict(filter_model)) if filter_model else {},
        "sort_sql": sort_sql,
        "filter_sql": filter_sql,
    }
    if extra_params:
        state["extra_params"] = dict(extra_params)
        state["extra_param_keys"] = sorted(extra_params.keys())
    return state


def build_aggrid_request_params(
    request_data: RequestData | None,
    *,
    base_params: MutableMapping[str, Any] | None = None,
    default_page_size: int = DEFAULT_PAGE_SIZE,
    allowed_sort_columns: Iterable[str] | None = None,
    allow_filters: bool = True,
    allowed_filter_columns: Iterable[str] | None = None,
    filter_model_overrides: Mapping[str, Any] | None = None,
    custom_filter_handlers: Mapping[str, FilterHandler] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build API params and table state from an AG-Grid request payload."""
    page, page_size = compute_pagination(request_data, default_page_size=default_page_size)

    params: dict[str, Any] = {}
    if base_params:
        params.update(base_params)
    params.update({"page": page, "per_page": page_size})

    request_data = request_data or {}
    sort_model = request_data.get("sortModel") or []
    sort_sql = build_sort_clause(sort_model, allowed_columns=allowed_sort_columns)
    if sort_sql:
        params["sort"] = sort_sql

    filter_model: dict[str, Any] = dict(request_data.get("filterModel") or {})
    if filter_model_overrides:
        filter_model.update(filter_model_overrides)

    filter_sql: str | None = None
    extra_params: dict[str, Any] = {}
    if allow_filters and filter_model:
        filter_sql, extra_params = build_filter_clause(
            filter_model,
            allowed_columns=allowed_filter_columns,
            custom_handlers=custom_filter_handlers,
        )
        if filter_sql:
            params["filter"] = filter_sql
        if extra_params:
            params.update(extra_params)

    table_state = build_table_state(
        sort_model,
        filter_model if allow_filters else {},
        sort_sql,
        filter_sql,
        extra_params,
    )
    return params, table_state


def build_refresh_request_params(
    *,
    base_params: MutableMapping[str, Any] | None = None,
    table_state: Mapping[str, Any] | None = None,
    allow_filters: bool = True,
    additional_filters: Mapping[str, Any] | None = None,
    allowed_filter_columns: Iterable[str] | None = None,
    custom_filter_handlers: Mapping[str, FilterHandler] | None = None,
) -> dict[str, Any]:
    """Build params for refresh/auto-refresh scenarios using stored table state."""
    params: dict[str, Any] = {}
    if base_params:
        params.update(base_params)

    filter_model: dict[str, Any] = {}

    if table_state:
        sort_sql = table_state.get("sort_sql")
        if sort_sql:
            params["sort"] = sort_sql
        if allow_filters:
            filter_sql = table_state.get("filter_sql")
            if filter_sql:
                params["filter"] = filter_sql
        extra_param_keys = table_state.get("extra_param_keys", [])
        for key in extra_param_keys:
            params.pop(key, None)
        if allow_filters:
            extra_params = table_state.get("extra_params") or {}
            params.update(extra_params)
            filter_model.update(copy.deepcopy(table_state.get("filter_model") or {}))

    if not allow_filters:
        return params

    if additional_filters:
        filter_model.update(additional_filters)

    if not filter_model:
        params.pop("filter", None)
        return params

    filter_sql, extra_params = build_filter_clause(
        filter_model,
        allowed_columns=allowed_filter_columns,
        custom_handlers=custom_filter_handlers,
    )

    if filter_sql:
        params["filter"] = filter_sql
    else:
        params.pop("filter", None)

    extra_param_keys = table_state.get("extra_param_keys", []) if table_state else []
    for key in extra_param_keys:
        if key not in (extra_params or {}):
            params.pop(key, None)

    if extra_params:
        params.update(extra_params)

    return params


__all__ = [
    "compute_pagination",
    "build_sort_clause",
    "build_filter_clause",
    "build_table_state",
    "build_aggrid_request_params",
    "build_refresh_request_params",
]
