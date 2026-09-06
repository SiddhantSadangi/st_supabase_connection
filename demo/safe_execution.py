"""Safe parsing, query construction, and code rendering for the demo app."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

FILTER_OPERATORS = {
    "Equals": "eq",
    "Does not equal": "neq",
    "Greater than": "gt",
    "Greater than or equal": "gte",
    "Less than": "lt",
    "Less than or equal": "lte",
    "Like": "like",
    "Case-insensitive like": "ilike",
    "Is": "is_",
    "In": "in_",
    "Contains": "contains",
    "Contained by": "contained_by",
    "Overlaps": "overlaps",
}

DATABASE_OPERATIONS = {"select", "insert", "upsert", "update", "delete"}


@dataclass(frozen=True)
class FilterSpec:
    """A validated, allowlisted PostgREST filter."""

    column: str
    method: str
    value: Any


def _reject_non_finite_json_constant(constant: str) -> None:
    raise ValueError(f"JSON values must use finite numbers; {constant} is not supported.")


def parse_json_records(value: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse a database mutation payload without evaluating Python code."""
    try:
        parsed = json.loads(value, parse_constant=_reject_non_finite_json_constant)
    except json.JSONDecodeError as exc:
        raise ValueError("Rows must be valid JSON.") from exc

    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and parsed and all(isinstance(row, dict) for row in parsed):
        return parsed
    raise ValueError("Rows must be a JSON object or a non-empty array of JSON objects.")


def parse_filter_value(value: Any) -> Any:
    """Parse JSON scalars/arrays while treating other input as plain text."""
    if not _as_text(value).strip():
        return ""
    if not isinstance(value, str):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Filter values must use finite numbers.")
        return value

    stripped = value.strip()
    try:
        return json.loads(stripped, parse_constant=_reject_non_finite_json_constant)
    except json.JSONDecodeError:
        return value


def parse_filter_rows(rows: Iterable[Mapping[str, Any]]) -> list[FilterSpec]:
    """Validate filter-editor rows and translate labels to allowlisted methods."""
    filters: list[FilterSpec] = []
    for index, row in enumerate(rows, start=1):
        column = _as_text(row.get("Column")).strip()
        operator_label = _as_text(row.get("Operator")).strip()
        raw_value = row.get("Value", "")
        value_text = _as_text(raw_value).strip()

        if not column and not operator_label and not value_text:
            continue
        if not column:
            raise ValueError(f"Filter {index} needs a column name.")
        if operator_label not in FILTER_OPERATORS:
            raise ValueError(f"Filter {index} has an unsupported operator.")
        if not value_text:
            raise ValueError(
                f'Filter {index} needs a value. Enter null or "" explicitly if intended.'
            )

        method = FILTER_OPERATORS[operator_label]
        parsed_value = parse_filter_value(raw_value)
        if method == "is_":
            # postgrest-py expects lowercase PostgREST literals for `is` filters.
            if parsed_value is None:
                parsed_value = "null"
            elif isinstance(parsed_value, bool):
                parsed_value = str(parsed_value).lower()
        elif method == "in_" and not isinstance(parsed_value, list):
            raise ValueError(f"Filter {index} with In needs a JSON array value.")

        filters.append(FilterSpec(column=column, method=method, value=parsed_value))
    return filters


def _database_query_calls(
    *,
    table: str,
    operation: str,
    payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    columns: str = "*",
    count: str | None = None,
    ignore_duplicates: bool = False,
    on_conflict: str | None = None,
    filters: Iterable[FilterSpec] = (),
    order_column: str | None = None,
    order_desc: bool = False,
    limit: int | None = None,
) -> list[tuple[str, tuple[Any, ...], dict[str, Any]]]:
    """Define the validated SDK calls shared by execution and the code preview."""
    _validate_database_operation(operation)
    filter_specs = list(filters)
    if operation in {"update", "delete"} and not filter_specs:
        raise ValueError(f"{operation.capitalize()} requires at least one filter.")

    calls = [("table", (table,), {})]
    kwargs = {"count": count} if count else {}
    if operation == "select":
        args = (columns or "*",)
    elif operation == "delete":
        args = ()
    else:
        args = (_require_payload(payload),)
    if operation == "upsert":
        kwargs["ignore_duplicates"] = ignore_duplicates
        if on_conflict:
            kwargs["on_conflict"] = on_conflict
    calls.append((operation, args, kwargs))

    for filter_spec in filter_specs:
        if filter_spec.method not in FILTER_OPERATORS.values():
            raise ValueError(f"Unsupported filter method: {filter_spec.method}")
        calls.append((filter_spec.method, (filter_spec.column, filter_spec.value), {}))

    if order_column:
        if operation != "select":
            raise ValueError("Ordering is only available for select queries in this demo.")
        calls.append(("order", (order_column,), {"desc": order_desc}))
    if limit is not None:
        if operation != "select":
            raise ValueError("Limiting is only available for select queries in this demo.")
        if limit < 1:
            raise ValueError("Limit must be at least 1.")
        calls.append(("limit", (limit,), {}))

    return calls


def build_database_query(client: Any, **params: Any) -> Any:
    """Build a query using only validated, allowlisted SDK calls."""
    query = client
    for method, args, kwargs in _database_query_calls(**params):
        query = getattr(query, method)(*args, **kwargs)

    return query


def render_database_code(
    *,
    ttl: str | float | None,
    client_expression: str = "st_supabase",
    **params: Any,
) -> str:
    """Render the same validated calls without executing any generated source."""
    methods = [
        _render_method(method, *args, **kwargs)
        for method, args, kwargs in _database_query_calls(**params)
    ]
    lines = ["query = (", f"    {client_expression}{methods[0]}"]
    lines.extend(f"    {method}" for method in methods[1:])
    lines.extend([")", f"response = execute_query(query, ttl={ttl!r})"])
    return "\n".join(lines)


def _as_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def _render_method(method: str, *args: Any, **kwargs: Any) -> str:
    rendered = [repr(value) for value in args]
    rendered.extend(f"{key}={value!r}" for key, value in kwargs.items())
    return f".{method}({', '.join(rendered)})"


def _require_payload(
    payload: dict[str, Any] | list[dict[str, Any]] | None,
) -> dict[str, Any] | list[dict[str, Any]]:
    if payload is None:
        raise ValueError("This operation requires a JSON payload.")
    return payload


def _validate_database_operation(operation: str) -> None:
    if operation not in DATABASE_OPERATIONS:
        raise ValueError(f"Unsupported database operation: {operation}")
