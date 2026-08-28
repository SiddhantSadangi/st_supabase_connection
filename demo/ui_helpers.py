"""Shared native-Streamlit UX helpers for the demo application."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any

import pandas as pd
import streamlit as st


class CodeLiteral(str):
    """Marker for a pre-rendered value in generated Python."""


def literal(value: str) -> CodeLiteral:
    return CodeLiteral(value)


def construct_call(receiver: str, operation: str, /, *args: Any, **kwargs: Any) -> str:
    """Render a valid, copyable Python method call from structured values."""
    parts: list[str] = []
    for value in args:
        parts.append(value if isinstance(value, CodeLiteral) else repr(value))
    for key, value in kwargs.items():
        rendered = value if isinstance(value, CodeLiteral) else repr(value)
        parts.append(f"{key}={rendered}")
    if not parts:
        return f"{receiver}.{operation}()"
    return f"{receiver}.{operation}(\n    " + ",\n    ".join(parts) + ",\n)"


def cache_ttl_input(key_prefix: str) -> int | None:
    """Return a typed query TTL. None means until cleared; 0 means no cache."""
    with st.expander("Cache settings", icon=":material/cached:"):
        left, right = st.columns(2, vertical_alignment="bottom")
        always_fresh = left.toggle(
            "Always fetch fresh",
            value=False,
            key=f"{key_prefix}_fresh",
            help="Turn on to skip cached query results.",
        )
        ttl_seconds = right.number_input(
            "Cache TTL (seconds)",
            min_value=0,
            value=0,
            step=60,
            key=f"{key_prefix}_ttl",
            disabled=always_fresh,
            help="0 keeps results until the server cache is cleared.",
        )
    return 0 if always_fresh else (int(ttl_seconds) or None)


def connection_ttl_input(key: str) -> int | None:
    ttl_seconds = st.number_input(
        "Connection cache TTL (seconds)",
        min_value=0,
        value=0,
        step=300,
        key=key,
        help="0 keeps the connection resource until its cache is cleared.",
    )
    return int(ttl_seconds) or None


def action_fingerprint(scope: str, values: Any) -> str:
    """Create a stable, non-plaintext identifier for a reviewed action."""
    material = json.dumps(
        {"scope": scope, "values": _to_plain_data(values)},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def sync_result_context(scope: str, action_id: str) -> None:
    """Clear a stored result when the inputs that produced it have changed."""
    context_key = f"_ux_result_context_{scope}"
    if st.session_state.get(context_key) == action_id:
        return
    clear_result(scope)
    st.session_state[context_key] = action_id


def render_code_preview(code: str) -> None:
    with st.expander(
        "View generated Python",
        expanded=False,
        icon=":material/code:",
    ):
        st.code(code, language="python", wrap_lines=True)


def open_confirmation(
    *,
    scope: str,
    action_id: str,
    operation: str,
    project: str,
    target: str,
    code: str,
    phrase: str,
) -> None:
    st.session_state.pop("_ux_confirmation_phrase", None)
    st.session_state["_ux_confirmation"] = {
        "scope": scope,
        "action_id": action_id,
        "operation": operation,
        "project": project,
        "target": target,
        "code": code,
        "phrase": phrase,
    }
    _confirmation_dialog()


@st.dialog("Review operation", icon=":material/warning:")
def _confirmation_dialog() -> None:
    request = st.session_state.get("_ux_confirmation")
    if not request:
        st.info("This operation is no longer pending.")
        return

    st.warning(
        "This request can change data in your Supabase project. Review every "
        "detail before continuing.",
        icon=":material/warning:",
    )
    st.markdown(f"**Operation:** {request['operation']}")
    st.markdown(f"**Project:** {request['project']}")
    st.markdown(f"**Target:** {request['target']}")
    st.code(request["code"], language="python", wrap_lines=True)

    phrase = request["phrase"]
    confirmation = st.text_input(
        f"Type {phrase} to confirm",
        key="_ux_confirmation_phrase",
        autocomplete="off",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="_ux_cancel_confirmation"):
            st.session_state.pop("_ux_confirmation", None)
            st.session_state.pop("_ux_confirmation_phrase", None)
            st.rerun()
        if st.button(
            "Confirm and run",
            type="primary",
            icon=":material/play_arrow:",
            disabled=confirmation != phrase,
            key="_ux_confirm_operation",
        ):
            st.session_state["_ux_confirmed_action"] = {
                "scope": request["scope"],
                "action_id": request["action_id"],
            }
            st.session_state.pop("_ux_confirmation", None)
            st.session_state.pop("_ux_confirmation_phrase", None)
            st.rerun()


def consume_confirmation(scope: str, action_id: str) -> bool:
    confirmed = st.session_state.get("_ux_confirmed_action")
    if confirmed != {"scope": scope, "action_id": action_id}:
        return False
    st.session_state.pop("_ux_confirmed_action", None)
    return True


def store_result(
    scope: str,
    *,
    title: str,
    message: str | None = None,
    data: Any = None,
    display: str = "json",
    url: str | None = None,
    download: dict[str, Any] | None = None,
) -> None:
    st.session_state[f"_ux_result_{scope}"] = {
        "status": "success",
        "title": title,
        "message": message,
        "data": _to_plain_data(data),
        "display": display,
        "url": url,
        "download": download,
    }


def store_error(scope: str, exc: Exception, *, context: str) -> None:
    st.session_state[f"_ux_result_{scope}"] = {
        "status": "error",
        "title": _friendly_error(exc, context=context),
        "details": str(exc),
    }


def clear_result(scope: str) -> None:
    st.session_state.pop(f"_ux_result_{scope}", None)


def render_result(scope: str) -> None:
    result = st.session_state.get(f"_ux_result_{scope}")
    if not result:
        return

    st.subheader("Result", anchor=False)
    with st.container(border=True):
        if result["status"] == "error":
            st.error(result["title"], icon=":material/error:")
            details = result.get("details")
            if details and details != result["title"]:
                with st.expander("Technical details", icon=":material/bug_report:"):
                    st.code(details, language="text", wrap_lines=True)
            return

        st.success(result["title"], icon=":material/check_circle:")
        if result.get("message"):
            st.caption(result["message"])

        url = result.get("url")
        if url:
            st.link_button(
                "Open URL",
                url,
                icon=":material/open_in_new:",
                width="stretch",
            )

        data = result.get("data")
        display = result.get("display")
        if display == "table":
            frame = pd.DataFrame(data or [])
            if frame.empty:
                st.info("No matching items were returned.", icon=":material/search_off:")
            else:
                st.dataframe(frame, hide_index=True, width="stretch")
        elif data is not None:
            st.json(data)

        download = result.get("download")
        if download:
            st.download_button(
                "Download file",
                data=download["data"],
                file_name=download["file_name"],
                mime=download["mime"],
                icon=":material/download:",
                width="stretch",
            )


def _friendly_error(exc: Exception, *, context: str) -> str:
    message = str(exc).strip()
    lowered = message.lower()
    if "bucket not found" in lowered:
        return "That bucket could not be found."
    if "invalid login credentials" in lowered:
        return "The email or phone number and password did not match."
    if "email rate limit" in lowered or "rate limit" in lowered:
        return "Too many requests were made. Wait a moment and try again."
    if "invalid url" in lowered:
        return "The Supabase project URL is invalid."
    if not message:
        return f"{context} failed. Try again."
    return f"{context} failed."


def _to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if is_dataclass(value):
        return _to_plain_data(asdict(value))
    if hasattr(value, "model_dump"):
        return _to_plain_data(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain_data(item) for item in value]
    if hasattr(value, "__dict__"):
        public = {key: item for key, item in vars(value).items() if not key.startswith("_")}
        if public:
            return _to_plain_data(public)
    return str(value)
