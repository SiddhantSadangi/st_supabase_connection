"""State-aware Supabase Auth explorer for the demo app."""

from __future__ import annotations

from typing import Any

import streamlit as st
from session_clients import (
    validate_email_address,
    validate_password_sign_in,
    validate_sign_up,
)
from ui_helpers import (
    action_fingerprint,
    clear_result,
    consume_confirmation,
    open_confirmation,
    render_code_preview,
    render_result,
    store_error,
    store_result,
)

SCOPE = "auth"
SESSION_CLIENT_CODE = "supabase = st_supabase.session_client()"


def render_auth_workspace(
    connection: Any,
    *,
    project: str,
    project_label: str,
) -> None:
    st.header("Authentication", anchor=False)
    st.caption(
        "Auth state is isolated to this browser session. Signed-in Database "
        "requests use the same user JWT."
    )

    auth_api = connection.session_client().auth
    session = _get_session(auth_api)
    user = getattr(session, "user", None) if session else None

    if user:
        _render_signed_in(auth_api, user)
        render_result(SCOPE)
        return

    st.badge("Signed out", color="gray", icon=":material/lock:")
    if project == "demo":
        st.caption(
            "Sign in with an existing account for this demo project. Shared credentials "
            "are not provided; connect your own project to create accounts or use email OTP."
        )
        st.subheader("Sign in", anchor=False)
        mode = "Sign in"
    else:
        mode = st.segmented_control(
            "Authentication task",
            options=["Sign in", "Create account", "Email OTP"],
            default="Sign in",
            key="auth_mode",
        )

    if st.session_state.get("_auth_last_mode") != mode:
        clear_result(SCOPE)
        st.session_state["_auth_last_mode"] = mode

    if mode == "Sign in":
        _render_password_sign_in(auth_api)
    elif mode == "Create account":
        _render_sign_up(auth_api, project_label)
    else:
        _render_otp(auth_api)

    if project == "demo":
        _render_otp_recipe()

    render_result(SCOPE)


def _render_password_sign_in(auth_api: Any) -> None:
    with st.form("auth_password_sign_in"):
        left, right = st.columns(2)
        identifier = left.text_input(
            "Email or phone number",
            key="auth_signin_identifier",
        )
        password = right.text_input(
            "Password",
            type="password",
            key="auth_signin_password",
            autocomplete="current-password",
        )
        validation_error = validate_password_sign_in(identifier, password)
        submitted = st.form_submit_button(
            "Sign in",
            type="primary",
            icon=":material/login:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
        )

    normalized = identifier.strip()
    identifier_field = "email" if "@" in normalized else "phone"
    request = {identifier_field: normalized, "password": password}
    if validation_error is None:
        render_code_preview(
            f"{SESSION_CLIENT_CODE}\n\n"
            f"supabase.auth.sign_in_with_password("
            f"{dict(request, password='***')!r})"
        )

    if submitted:
        clear_result(SCOPE)
        try:
            response = auth_api.sign_in_with_password(request)
            email = getattr(getattr(response, "user", None), "email", None)
            store_result(
                SCOPE,
                title="Signed in",
                message=f"Session established for {email}." if email else None,
            )
        except Exception as exc:
            store_error(SCOPE, exc, context="Sign in")
        st.session_state["_clear_auth_secret_fields"] = True
        st.rerun()


def _render_sign_up(auth_api: Any, project_label: str) -> None:
    with st.form("auth_sign_up"):
        left, right = st.columns(2)
        email = left.text_input(
            "Email",
            key="auth_signup_email",
            autocomplete="email",
        )
        password = right.text_input(
            "Password",
            type="password",
            key="auth_signup_password",
            autocomplete="new-password",
            help="Use at least 6 characters.",
        )
        first_name = left.text_input(
            "First name",
            key="auth_signup_first_name",
            placeholder="Optional",
        )
        attribution = right.text_input(
            "How did you hear about this library?",
            key="auth_signup_attribution",
            placeholder="Optional",
        )
        validation_error = validate_sign_up(email, password)
        submitted = st.form_submit_button(
            "Review account creation",
            type="primary",
            icon=":material/rate_review:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
        )

    request = {
        "email": email.strip(),
        "password": password,
        "options": {
            "data": {
                "fname": first_name.strip(),
                "attribution": attribution.strip(),
            }
        },
    }
    code = f"{SESSION_CLIENT_CODE}\n\n" f"supabase.auth.sign_up({dict(request, password='***')!r})"
    action_id = action_fingerprint(
        f"{SCOPE}:sign_up",
        {
            "email": email.strip(),
            "password": password,
            "first_name": first_name.strip(),
            "attribution": attribution.strip(),
        },
    )

    if validation_error is None:
        render_code_preview(code)
    if submitted:
        open_confirmation(
            scope=SCOPE,
            action_id=action_id,
            operation="Create account",
            project=project_label,
            target=email.strip(),
            code=code,
            phrase="CREATE",
        )
    if consume_confirmation(SCOPE, action_id):
        clear_result(SCOPE)
        try:
            response = auth_api.sign_up(request)
            created_user = getattr(response, "user", None)
            needs_confirmation = getattr(response, "session", None) is None
            store_result(
                SCOPE,
                title="Account creation requested",
                message=(
                    "Check the inbox to confirm the email address."
                    if needs_confirmation
                    else "The new account is signed in."
                ),
                data=_safe_user(created_user),
            )
        except Exception as exc:
            store_error(SCOPE, exc, context="Account creation")
        st.session_state["_clear_auth_secret_fields"] = True
        st.rerun()


def _render_otp(auth_api: Any) -> None:
    st.info(
        "Email OTP requires a template containing the {{ .Token }} variable. "
        "New Free projects also need custom SMTP to customize that template.",
        icon=":material/mail:",
    )

    sent_to = st.session_state.get("auth_otp_sent_to")
    with st.form("auth_send_otp"):
        email = st.text_input(
            "Email",
            key="auth_otp_email",
            autocomplete="email",
        )
        email_error = validate_email_address(email)
        sent = st.form_submit_button(
            "Send one-time code",
            type="primary",
            icon=":material/send:",
            width="stretch",
            disabled=email_error is not None,
            help=email_error,
        )

    send_request = {
        "email": email.strip(),
        "options": {"should_create_user": False},
    }
    if email_error is None:
        render_code_preview(
            f"{SESSION_CLIENT_CODE}\n\n" f"supabase.auth.sign_in_with_otp({send_request!r})"
        )

    if sent:
        clear_result(SCOPE)
        try:
            auth_api.sign_in_with_otp(send_request)
            st.session_state["auth_otp_sent_to"] = email.strip()
            store_result(
                SCOPE,
                title="One-time code sent",
                message=f"Check {email.strip()} and enter the six-digit code below.",
            )
            st.rerun()
        except Exception as exc:
            store_error(SCOPE, exc, context="Sending the one-time code")

    sent_to = st.session_state.get("auth_otp_sent_to")
    if not sent_to:
        return

    with st.form("auth_verify_otp"):
        token = st.text_input(
            "Six-digit code",
            type="password",
            max_chars=6,
            key="auth_otp_token",
            autocomplete="one-time-code",
        )
        token_error = (
            None
            if token.isdigit() and len(token) == 6
            else "Enter the six-digit code from the email."
        )
        verified = st.form_submit_button(
            "Verify and sign in",
            type="primary",
            icon=":material/verified_user:",
            width="stretch",
            disabled=token_error is not None,
            help=token_error,
        )

    if token_error is None:
        render_code_preview(
            f"{SESSION_CLIENT_CODE}\n\n"
            "supabase.auth.verify_otp({"
            f"'email': {sent_to!r}, 'token': '***', 'type': 'email'"
            "})"
        )
    if verified:
        clear_result(SCOPE)
        try:
            auth_api.verify_otp({"email": sent_to, "token": token, "type": "email"})
            st.session_state.pop("auth_otp_sent_to", None)
            store_result(SCOPE, title="Email verified and signed in")
        except Exception as exc:
            store_error(SCOPE, exc, context="OTP verification")
        st.session_state["_clear_auth_secret_fields"] = True
        st.rerun()


def _render_signed_in(auth_api: Any, user: Any) -> None:
    email = getattr(user, "email", None) or "Authenticated user"
    with st.container(border=True):
        st.badge("Signed in", color="green", icon=":material/verified_user:")
        st.subheader(email, anchor=False)
        st.caption("Database queries in this browser session now run with this user's JWT.")
        if st.button(
            "Sign out",
            icon=":material/logout:",
            width="stretch",
            key="auth_sign_out",
        ):
            try:
                auth_api.sign_out()
                st.session_state.pop("auth_otp_sent_to", None)
                store_result(SCOPE, title="Signed out")
                st.rerun()
            except Exception as exc:
                store_error(SCOPE, exc, context="Sign out")

    with st.expander("Account details", icon=":material/account_circle:"):
        st.json(_safe_user(user))


def _render_otp_recipe() -> None:
    with st.expander(
        "Email OTP implementation recipe",
        icon=":material/menu_book:",
    ):
        st.caption("Interactive email delivery is disabled for the shared demo project.")
        st.code(
            f"""{SESSION_CLIENT_CODE}

supabase.auth.sign_in_with_otp({{
    "email": email,
    "options": {{"should_create_user": False}},
}})

supabase.auth.verify_otp({{
    "email": email,
    "token": token,
    "type": "email",
}})""",
            language="python",
        )
        st.link_button(
            "Supabase passwordless email guide",
            "https://supabase.com/docs/guides/auth/auth-email-passwordless",
            icon=":material/open_in_new:",
        )


def _get_session(auth_api: Any) -> Any:
    try:
        return auth_api.get_session()
    except Exception:
        return None


def _safe_user(user: Any) -> dict[str, Any] | None:
    if user is None:
        return None
    if hasattr(user, "model_dump"):
        data = user.model_dump()
    elif isinstance(user, dict):
        data = dict(user)
    else:
        return {"email": getattr(user, "email", None), "id": getattr(user, "id", None)}
    for sensitive in ("access_token", "refresh_token", "token"):
        data.pop(sensitive, None)
    return data
