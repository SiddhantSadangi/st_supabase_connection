"""Interactive tutorial and safe API explorer for st_supabase_connection."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import streamlit as st
from auth_workspace import render_auth_workspace
from database_workspace import render_database_workspace
from session_clients import (
    custom_connection_name,
    resolve_connection_credentials,
    validate_project_url,
    validate_public_api_key,
)
from storage_workspace import render_storage_workspace
from streamlit_extras.exception_handler import set_global_exception_handler
from utils import custom_exception_handler

from st_supabase_connection import SupabaseConnection, __version__

VERSION = __version__

st.set_page_config(
    page_title="Supabase for Streamlit",
    page_icon="🔌",
    layout="wide",
    menu_items={
        "About": (
            f"st_supabase_connection v{VERSION}\n\n"
            "An open-source Supabase connection for Streamlit."
        ),
        "Report a Bug": ("https://github.com/SiddhantSadangi/" "st_supabase_connection/issues/new"),
        "Get help": None,
    },
)
set_global_exception_handler(custom_exception_handler)


def _initialize_state() -> None:
    st.session_state.setdefault("client", None)
    st.session_state.setdefault("initialized", False)
    st.session_state.setdefault("project", None)
    st.session_state.setdefault("project_label", None)
    st.session_state.setdefault("project_url", None)
    st.session_state.setdefault("workspace", "Storage")
    if st.session_state["workspace"] == "Authentication":
        st.session_state["workspace"] = "Auth"

    if st.session_state.pop("_clear_connection_form", False):
        st.session_state.pop("connect_custom_key", None)
        st.session_state.pop("connect_custom_url", None)
    if st.session_state.pop("_clear_auth_secret_fields", False):
        for key in (
            "auth_signin_password",
            "auth_signup_password",
            "auth_otp_token",
        ):
            st.session_state.pop(key, None)
    if st.session_state.pop("_clear_storage_secret_fields", False):
        st.session_state.pop("storage_token_upload_token", None)


def _reset_project() -> None:
    for key in list(st.session_state):
        if (
            key
            in {
                "client",
                "initialized",
                "project",
                "project_label",
                "project_url",
                "connection_code",
                "_connection_error",
                "auth_otp_sent_to",
                "_ux_confirmation",
                "_ux_confirmed_action",
            }
            or key.startswith("_ux_result_")
            or key.startswith("_st_supabase_connection_session_client")
            or key.startswith("auth_")
            or key.startswith("_auth_")
            or key.startswith("storage_")
            or key.startswith("_storage_")
            or key.startswith("database_")
            or key.startswith("_database_")
        ):
            st.session_state.pop(key, None)
    st.session_state["client"] = None
    st.session_state["initialized"] = False
    st.session_state["project"] = None
    st.session_state["project_label"] = None
    st.session_state["project_url"] = None


def _connect(
    *,
    url: str,
    key: str,
    ttl: int | None,
    project: str,
) -> None:
    try:
        name = (
            "supabase"
            if project == "demo"
            else custom_connection_name(st.session_state, url=url, key=key)
        )
        connection = st.connection(
            name=name,
            type=SupabaseConnection,
            ttl=ttl,
            url=url,
            key=key,
        )
        connection.session_client()
    except Exception as exc:
        st.session_state["client"] = None
        st.session_state["initialized"] = False
        st.session_state["_connection_error"] = {
            "summary": "The Supabase client could not be initialized.",
            "details": str(exc),
        }
        return

    host = urlparse(url).hostname or url
    st.session_state["client"] = connection
    st.session_state["initialized"] = True
    st.session_state["project"] = project
    st.session_state["project_label"] = "Demo project" if project == "demo" else host
    st.session_state["project_url"] = url
    connection_lines = [
        "st_supabase = st.connection(",
        f"    name={name!r},",
        "    type=SupabaseConnection,",
        f"    ttl={ttl!r},",
    ]
    if project == "custom":
        connection_lines.extend(["    url=url,", "    key=publishable_key,"])
    connection_lines.extend([")", "", "supabase = st_supabase.session_client()"])
    st.session_state["connection_code"] = "\n".join(connection_lines)
    st.session_state.pop("_connection_error", None)
    if project == "custom":
        st.session_state["_clear_connection_form"] = True
    st.toast("Supabase project connected", icon=":material/check_circle:")
    st.rerun()


def _render_sidebar() -> None:
    with st.sidebar:
        with st.expander(
            "How to use",
            expanded=not st.session_state["initialized"],
            icon=":material/lightbulb:",
        ):
            st.markdown(
                """
                1. Connect the demo or your own project.
                2. Choose Storage, Database, or Authentication.
                3. Configure one task and review its Python.
                4. Run reads directly; review writes before confirming.
                """
            )

        if st.session_state["initialized"]:
            with st.container(border=True):
                st.badge(
                    "Connected",
                    color="green",
                    icon=":material/check_circle:",
                )
                st.markdown(f"**{st.session_state['project_label']}**")
                st.caption(
                    "Read-only demo"
                    if st.session_state["project"] == "demo"
                    else "Publishable-key connection"
                )
                st.button(
                    "Change project",
                    icon=":material/swap_horiz:",
                    width="stretch",
                    on_click=_reset_project,
                )

            if st.session_state["project"] == "demo":
                with st.expander(
                    "Demo data",
                    icon=":material/dataset:",
                ):
                    st.markdown(
                        """
                        **Storage**

                        - bucket1/awesome_zoom_background.jpg
                        - bucket2/folder1/folder2/lenna.png

                        **Database tables**

                        cities, countries, messages, teams, users, users_teams
                        """
                    )

        st.link_button(
            "View project on GitHub",
            "https://github.com/SiddhantSadangi/st_supabase_connection",
            icon=":material/star:",
            width="stretch",
        )
        with st.popover(
            "About and links",
            icon=":material/info:",
            width="stretch",
        ):
            st.badge(
                f"Version {VERSION}",
                icon=":material/deployed_code:",
                color="violet",
            )
            st.caption("Built by Siddhant Sadangi · MIT License")
            st.link_button(
                "Report an issue",
                "https://github.com/SiddhantSadangi/" "st_supabase_connection/issues/new",
                icon=":material/bug_report:",
                width="stretch",
            )
            st.link_button(
                "Connect on LinkedIn",
                "https://linkedin.com/in/siddhantsadangi",
                icon=":material/person:",
                width="stretch",
            )
            st.link_button(
                "Sponsor on GitHub",
                "https://github.com/sponsors/SiddhantSadangi",
                icon=":material/favorite:",
                width="stretch",
            )


def _render_connection_error() -> None:
    error = st.session_state.get("_connection_error")
    if not error:
        return
    st.error(error["summary"], icon=":material/error:")
    if error.get("details"):
        with st.expander("Technical details", icon=":material/bug_report:"):
            st.code(error["details"], language="text", wrap_lines=True)


def _render_connect_page() -> None:
    st.header("Connect a project", anchor=False)
    st.caption(
        "Start with the read-only demo, or use a publishable key from your own " "Supabase project."
    )
    source = st.segmented_control(
        "Project source",
        options=["Demo project", "Own project"],
        default="Demo project",
        key="connection_source",
    )
    if st.session_state.get("_connection_source_last") != source:
        st.session_state.pop("_connection_error", None)
        st.session_state["_connection_source_last"] = source

    if source == "Demo project":
        with st.container(border=True):
            st.subheader("Explore safely", anchor=False)
            st.caption(
                "The shared project exposes seeded Storage and Database reads. "
                "Mutations and outbound Auth email are hidden."
            )
            with st.expander("Connection settings", icon=":material/settings:"):
                ttl_seconds = st.number_input(
                    "Connection cache TTL (seconds)",
                    min_value=0,
                    value=0,
                    step=300,
                    key="connect_demo_ttl",
                    help="0 keeps the demo connection until the server restarts.",
                )
            if st.button(
                "Connect demo project",
                type="primary",
                icon=":material/electrical_services:",
                width="stretch",
                key="connect_demo",
            ):
                try:
                    url, key = resolve_connection_credentials(st.secrets, os.environ)
                except Exception as exc:
                    st.session_state["_connection_error"] = {
                        "summary": "Demo credentials are not configured.",
                        "details": str(exc),
                    }
                else:
                    _connect(
                        url=url,
                        key=key,
                        ttl=int(ttl_seconds) or None,
                        project="demo",
                    )
    else:
        st.warning(
            "Use an sb_publishable_ key (legacy anon keys are supported). Never "
            "paste a secret or service-role key into this app.",
            icon=":material/security:",
        )
        with st.form("custom_connection"):
            left, right = st.columns(2)
            url = left.text_input(
                "Supabase project URL",
                key="connect_custom_url",
                placeholder="https://project.supabase.co",
                autocomplete="url",
            )
            key = right.text_input(
                "Publishable key",
                key="connect_custom_key",
                type="password",
                placeholder="sb_publishable_...",
                autocomplete="off",
                help="Legacy anon JWT keys remain supported for compatibility.",
            )
            st.caption(
                "Find the project URL and publishable key in the Supabase "
                "**Connect** dialog or **Settings → API Keys**."
            )
            with st.expander("Connection settings", icon=":material/settings:"):
                ttl_seconds = st.number_input(
                    "Connection cache TTL (seconds)",
                    min_value=60,
                    value=3600,
                    step=300,
                    key="connect_custom_ttl",
                    help="Custom connection resources expire from the server cache.",
                )
            submitted = st.form_submit_button(
                "Connect project",
                type="primary",
                icon=":material/electrical_services:",
                width="stretch",
            )

        if submitted:
            url_error = validate_project_url(url)
            key_error = validate_public_api_key(key)
            if url_error or key_error:
                st.session_state["_connection_error"] = {
                    "summary": url_error or key_error,
                    "details": None,
                }
            else:
                _connect(
                    url=url.strip(),
                    key=key.strip(),
                    ttl=int(ttl_seconds),
                    project="custom",
                )

    _render_connection_error()


def _render_workspace() -> None:
    project_label = st.session_state["project_label"]
    with st.container(border=True):
        st.markdown(f"**Connected to {project_label}**")
        st.caption(
            "Queries use a browser-session client; publishable-key permissions and "
            "Row Level Security remain in force."
        )
        with st.popover(
            "View connection code",
            icon=":material/code:",
            width="content",
        ):
            st.code(
                st.session_state["connection_code"],
                language="python",
                wrap_lines=True,
            )

    workspace = st.segmented_control(
        "Workspace",
        options=["Storage", "Database", "Auth"],
        key="workspace",
        label_visibility="collapsed",
    )
    connection = st.session_state["client"]
    common = {
        "project": st.session_state["project"],
        "project_label": project_label,
    }
    if workspace == "Storage":
        render_storage_workspace(connection, **common)
    elif workspace == "Database":
        render_database_workspace(connection, **common)
    else:
        render_auth_workspace(connection, **common)


_initialize_state()
_render_sidebar()

st.title(":material/electrical_services: Supabase for Streamlit")
st.caption(
    "Connect, explore, and copy safe Python for "
    "[st_supabase_connection]"
    "(https://github.com/SiddhantSadangi/st_supabase_connection)."
)

if st.session_state["initialized"]:
    _render_workspace()
else:
    _render_connect_page()

st.caption("Open source under the MIT License · " f"st_supabase_connection {VERSION}")
