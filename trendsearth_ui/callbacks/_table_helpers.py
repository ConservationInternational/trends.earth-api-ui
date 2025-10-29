"""Shared helpers for resolving table rows inside Dash callbacks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..utils.helpers import make_authenticated_request


@dataclass(slots=True)
class RowResolutionError(RuntimeError):
    """Raised when a table row cannot be resolved for a callback."""

    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial string override
        return self.message


def resolve_row_data(
    cell: Mapping[str, Any] | None,
    token: str | None,
    table_state: Mapping[str, Any] | None,
    endpoint: str,
    *,
    include: str | None = None,
    exclude: str | None = None,
    extra_params: Mapping[str, Any] | None = None,
    page_size: int = 50,
    id_field: str = "id",
) -> Mapping[str, Any]:
    """Return row data for a clicked AG Grid cell.

    The grid sometimes omits ``data`` when virtualization or pagination kicks in. In that
    situation we replicate the table request made by the frontend to retrieve the specific
    record for the provided ``rowIndex``.

    Args:
        cell: Dash cell payload with ``data`` and ``rowIndex`` keys.
        token: Current access token used for authenticated requests.
        table_state: Cached sort/filter state emitted by the grid.
        endpoint: API endpoint to call when data needs to be fetched.
        include: Optional ``include`` query parameter to append.
        exclude: Optional ``exclude`` query parameter to append.
        extra_params: Additional query parameters to merge into the request.
        page_size: Size of the pages requested from the API. Defaults to 50 which matches
            the UI configuration.
        id_field: Name of the identifier field expected in the row payload.

    Returns:
        Mapping containing the resolved row data (never ``None``).

    Raises:
        RowResolutionError: When the row cannot be determined.
    """

    if not cell:
        raise RowResolutionError("Cell payload is missing.")

    row_data = cell.get("data") if isinstance(cell, Mapping) else None
    if isinstance(row_data, Mapping) and row_data.get(id_field) is not None:
        return row_data

    if token is None:
        raise RowResolutionError("Authentication token is required to resolve row data.")

    row_index = cell.get("rowIndex") if isinstance(cell, Mapping) else None
    if row_index is None:
        raise RowResolutionError("Row index not provided in cell payload.")

    if row_index < 0:
        raise RowResolutionError(f"Invalid row index: {row_index}.")

    page = (row_index // page_size) + 1
    row_in_page = row_index % page_size

    params: dict[str, Any] = {"page": page, "per_page": page_size}
    if include:
        params["include"] = include
    if exclude:
        params["exclude"] = exclude
    if extra_params:
        params.update(extra_params)

    if isinstance(table_state, Mapping):
        sort_sql = table_state.get("sort_sql")
        filter_sql = table_state.get("filter_sql")
        if sort_sql:
            params["sort"] = sort_sql
        if filter_sql:
            params["filter"] = filter_sql

    response = make_authenticated_request(endpoint, token, params=params)
    if response.status_code != 200:
        raise RowResolutionError(
            f"Failed to fetch data ({response.status_code}): {response.text[:200]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        raise RowResolutionError(f"Invalid JSON payload: {exc}") from exc

    records = payload.get("data", []) if isinstance(payload, Mapping) else []
    if row_in_page >= len(records):
        raise RowResolutionError(
            f"Row index {row_in_page} out of range for page {page} (found {len(records)} records)."
        )

    record = records[row_in_page]
    if not isinstance(record, Mapping) or record.get(id_field) is None:
        raise RowResolutionError("Resolved record is missing required identifier field.")

    return record
