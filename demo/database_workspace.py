"""Task-focused Database explorer for the demo app."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from safe_execution import (
    FILTER_OPERATORS,
    build_database_query,
    parse_filter_rows,
    parse_json_records,
    render_database_code,
)
from ui_helpers import (
    action_fingerprint,
    cache_ttl_input,
    clear_result,
    consume_confirmation,
    open_confirmation,
    render_code_preview,
    render_result,
    store_error,
    store_result,
    sync_result_context,
)

from st_supabase_connection import execute_query

SCOPE = "database"
DEMO_TABLES = [
    "cities",
    "countries",
    "messages",
    "teams",
    "users",
    "users_teams",
]
OPERATION_GROUPS = {
    "Read": [("Select rows", "select")],
    "Write": [
        ("Insert rows", "insert"),
        ("Upsert rows", "upsert"),
        ("Update rows", "update"),
    ],
    "Destructive": [("Delete rows", "delete")],
}
COUNT_METHODS = {
    "No count": None,
    "Exact": "exact",
    "Planned": "planned",
    "Estimated": "estimated",
}


def render_database_workspace(
    connection: Any,
    *,
    project: str,
    project_label: str,
) -> None:
    st.header("Database", anchor=False)
    st.caption(
        "Build a structured PostgREST query. Signed-in sessions automatically carry "
        "their user JWT, so Row Level Security still applies."
    )

    if project == "demo":
        st.badge("Read-only demo", color="blue", icon=":material/visibility:")
        st.caption(
            "Database mutations are hidden in the demo. Connect your own project " "to review them."
        )
        risk = "Read"
    else:
        risk = st.segmented_control(
            "Operation type",
            options=list(OPERATION_GROUPS),
            default="Read",
            required=True,
            key="database_risk",
        )

    operations = dict(OPERATION_GROUPS[risk])
    label = st.selectbox(
        "Database task",
        options=list(operations),
        key=f"database_operation_{risk.lower()}",
    )
    operation = operations[label]

    if risk == "Write":
        st.warning(
            "This query can create or change rows. It will require review.",
            icon=":material/edit:",
        )
    elif risk == "Destructive":
        st.error(
            "This query can permanently delete rows. A filter and typed "
            "confirmation are required.",
            icon=":material/delete_forever:",
        )

    params, validation_error = _render_inputs(operation, project)
    code = _render_code(operation, params) if validation_error is None else None

    if code:
        render_code_preview(code)
    elif validation_error and _has_meaningful_input(params):
        st.error(validation_error, icon=":material/error:")

    action_id = action_fingerprint(
        f"{SCOPE}:{operation}",
        {"operation": operation, **params},
    )
    sync_result_context(SCOPE, action_id)
    confirmed = consume_confirmation(SCOPE, action_id)

    if risk == "Read":
        clicked = st.button(
            "Run query",
            type="primary",
            icon=":material/play_arrow:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
            key="database_run_read",
        )
        if clicked:
            _execute(connection, operation, params, label)
    else:
        clicked = st.button(
            "Review destructive action" if risk == "Destructive" else "Review write",
            type="primary",
            icon=":material/rate_review:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
            key=f"database_review_{risk.lower()}",
        )
        if clicked and code:
            open_confirmation(
                scope=SCOPE,
                action_id=action_id,
                operation=label,
                project=project_label,
                target=f"table {params['table']}",
                code=code,
                phrase=params["table"] if risk == "Destructive" else "RUN",
            )
        if confirmed:
            _execute(connection, operation, params, label)

    render_result(SCOPE)


def _render_inputs(operation: str, project: str) -> tuple[dict[str, Any], str | None]:
    params: dict[str, Any] = {}
    if project == "demo":
        params["table"] = st.selectbox(
            "Table",
            options=DEMO_TABLES,
            index=1,
            key="database_demo_table",
        )
    else:
        params["table"] = st.text_input(
            "Table",
            key="database_custom_table",
            placeholder="Required — for example, countries",
        ).strip()

    if operation == "select":
        left, right = st.columns(2)
        params["columns"] = left.text_input(
            "Columns",
            value="*",
            key="database_select_columns",
            help="Use a comma-separated PostgREST selection string.",
        ).strip()
        count_label = right.selectbox(
            "Total count",
            options=list(COUNT_METHODS),
            key="database_count",
            help="Exact is reliable but can be slower on large tables.",
        )
        params["count"] = COUNT_METHODS[count_label]
        params["ttl"] = cache_ttl_input("database_select")

    elif operation in {"insert", "upsert", "update"}:
        examples = {
            "insert": '{"name": "Example"}',
            "upsert": '{"id": 1, "name": "Example"}',
            "update": '{"name": "Updated value"}',
        }
        params["payload_text"] = st.text_area(
            "Rows as JSON",
            value="",
            placeholder=examples[operation],
            key=f"database_{operation}_payload",
            help="Enter one JSON object or a non-empty array of JSON objects.",
        )
        params["ttl"] = 0
        if operation == "upsert":
            left, right = st.columns(2)
            params["on_conflict"] = left.text_input(
                "Conflict columns",
                key="database_upsert_conflict",
                placeholder="Optional — for example, id",
            ).strip()
            params["ignore_duplicates"] = right.checkbox(
                "Ignore duplicates",
                key="database_upsert_ignore",
            )

    else:
        params["ttl"] = 0

    needs_filters = operation in {"update", "delete"}
    optional_filters = operation == "select" and st.toggle(
        "Add filters",
        value=False,
        key="database_select_use_filters",
    )
    params["filters"] = []
    if needs_filters or optional_filters:
        if needs_filters:
            st.caption("At least one filter is required for this operation.")
        editor = st.data_editor(
            pd.DataFrame(columns=["Column", "Operator", "Value"]),
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "Column": st.column_config.TextColumn(
                    "Column",
                    help="Database column to filter",
                    required=True,
                ),
                "Operator": st.column_config.SelectboxColumn(
                    "Operator",
                    options=list(FILTER_OPERATORS),
                    required=True,
                ),
                "Value": st.column_config.TextColumn(
                    "Value",
                    help=(
                        'Plain text or JSON, such as 42, true, null, or ["a", "b"]. '
                        "In requires a JSON array."
                    ),
                ),
            },
            key=f"database_filters_{operation}_{params['table']}",
        )
        params["filter_rows"] = editor.to_dict("records")
    else:
        params["filter_rows"] = []

    if operation == "select":
        params["use_order"] = st.toggle(
            "Configure ordering",
            value=False,
            key="database_use_order",
        )
        if params["use_order"]:
            left, right = st.columns(2)
            params["order_column"] = left.text_input(
                "Order by",
                key="database_order_column",
                placeholder="Column name",
            ).strip()
            direction = right.segmented_control(
                "Direction",
                options=["Ascending", "Descending"],
                default="Ascending",
                required=True,
                key="database_order_direction",
            )
            params["order_desc"] = direction == "Descending"
        else:
            params["order_column"] = ""
            params["order_desc"] = False
        params["limit"] = int(
            st.number_input(
                "Maximum rows",
                min_value=1,
                max_value=1000,
                value=50,
                key="database_limit",
            )
        )
        params["view"] = st.segmented_control(
            "Result format",
            options=["Table", "JSON"],
            default="Table",
            required=True,
            key="database_result_format",
        )
    else:
        params["columns"] = "*"
        params["count"] = None
        params["use_order"] = False
        params["order_column"] = ""
        params["order_desc"] = False
        params["limit"] = None
        params["view"] = "Table"

    validation_error = None
    params["payload"] = None
    try:
        if not params["table"]:
            raise ValueError("Enter a table name.")
        if operation in {"insert", "upsert", "update"}:
            params["payload"] = parse_json_records(params["payload_text"])
        params["filters"] = parse_filter_rows(params["filter_rows"])
        if operation in {"update", "delete"} and not params["filters"]:
            raise ValueError(f"{operation.capitalize()} requires at least one filter.")
        if operation == "select" and not params["columns"]:
            raise ValueError("Enter at least one column or use *.")
        if params["use_order"] and not params["order_column"].strip():
            raise ValueError("Enter a column to order by.")
    except ValueError as exc:
        validation_error = str(exc)

    return params, validation_error


def _render_code(operation: str, params: dict[str, Any]) -> str:
    code = render_database_code(
        table=params["table"],
        operation=operation,
        ttl=params["ttl"],
        payload=params["payload"],
        columns=params["columns"],
        count=params["count"],
        ignore_duplicates=params.get("ignore_duplicates", False),
        on_conflict=params.get("on_conflict") or None,
        filters=params["filters"],
        order_column=params["order_column"] or None,
        order_desc=params["order_desc"],
        limit=params["limit"],
        client_expression="supabase",
    )
    return "supabase = st_supabase.session_client()\n\n" + code


def _execute(
    connection: Any,
    operation: str,
    params: dict[str, Any],
    label: str,
) -> None:
    clear_result(SCOPE)
    try:
        session_client = connection.session_client()
        query = build_database_query(
            session_client,
            table=params["table"],
            operation=operation,
            payload=params["payload"],
            columns=params["columns"],
            count=params["count"],
            ignore_duplicates=params.get("ignore_duplicates", False),
            on_conflict=params.get("on_conflict") or None,
            filters=params["filters"],
            order_column=params["order_column"] or None,
            order_desc=params["order_desc"],
            limit=params["limit"],
        )
        response = execute_query(query, ttl=params["ttl"])
        rows = response.data or []
        row_count = len(rows)

        if operation == "select":
            title = (
                f"Retrieved {row_count} {'row' if row_count == 1 else 'rows'}"
                if row_count
                else "Query completed"
            )
            if params["count"] and response.count is not None:
                message = f"Total matching rows: {response.count}."
            elif params["count"]:
                message = "Supabase did not return a total count for this request."
            elif not row_count:
                message = "No rows matched the current query."
            else:
                message = None
        else:
            title = f"{label} completed"
            affected = response.count if response.count is not None else row_count
            message = f"{affected} {'row' if affected == 1 else 'rows'} returned or affected."

        store_result(
            SCOPE,
            title=title,
            message=message,
            data=rows,
            display="table" if params["view"] == "Table" else "json",
        )
    except Exception as exc:
        store_error(SCOPE, exc, context=label)


def _has_meaningful_input(params: dict[str, Any]) -> bool:
    return bool(params.get("table") or params.get("payload_text") or params.get("filter_rows"))
