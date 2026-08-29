"""Session-scoped Supabase client helpers for the demo app."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Mapping, MutableMapping
from typing import Any
from urllib.parse import urlparse

from streamlit.errors import StreamlitSecretNotFoundError

_CUSTOM_CONNECTION_TOKEN_STATE_KEY = "_supabase_custom_connection_token"


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Any:
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except (AttributeError, TypeError, StreamlitSecretNotFoundError):
        return None


def _credential_value(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def resolve_connection_credentials(
    secrets: Mapping[str, Any] | None,
    environ: Mapping[str, str] | None,
    *,
    connection_name: str = "supabase",
) -> tuple[str, str]:
    """Resolve demo credentials without returning or logging partial secrets."""
    connections = _mapping_value(secrets, "connections")
    connection_secrets = _mapping_value(connections, connection_name)
    if not isinstance(connection_secrets, Mapping):
        connection_secrets = None

    url = _credential_value(
        _mapping_value(connection_secrets, "SUPABASE_URL"),
        _mapping_value(secrets, "SUPABASE_URL"),
        _mapping_value(environ, "SUPABASE_URL"),
    )
    key = _credential_value(
        _mapping_value(connection_secrets, "SUPABASE_PUBLISHABLE_KEY"),
        _mapping_value(connection_secrets, "SUPABASE_KEY"),
        _mapping_value(secrets, "SUPABASE_PUBLISHABLE_KEY"),
        _mapping_value(secrets, "SUPABASE_KEY"),
        _mapping_value(environ, "SUPABASE_PUBLISHABLE_KEY"),
        _mapping_value(environ, "SUPABASE_KEY"),
    )

    missing = [name for name, value in (("URL", url), ("key", key)) if value is None]
    if missing:
        raise ConnectionRefusedError(
            "Supabase "
            + " and ".join(missing)
            + " not provided in the connection secrets or environment."
        )

    return url, key


def _credential_fingerprint(url: str, key: str) -> str:
    return hashlib.sha256(f"{url}\0{key}".encode()).hexdigest()


def custom_connection_name(state: MutableMapping[str, Any], *, url: str, key: str) -> str:
    """Build a stable, non-secret connection name unique to a browser session."""
    session_token = state.setdefault(_CUSTOM_CONNECTION_TOKEN_STATE_KEY, uuid.uuid4().hex)
    fingerprint = _credential_fingerprint(url.strip(), key.strip())[:12]
    return f"supabase_custom_{session_token}_{fingerprint}"


def validate_project_url(url: str) -> str | None:
    """Validate a hosted or local Supabase project URL."""
    normalized = url.strip()
    if not normalized:
        return "Enter your Supabase project URL."

    try:
        parsed = urlparse(normalized)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return "Enter a complete URL, such as https://project.supabase.co."

    if parsed.scheme not in {"http", "https"} or not hostname:
        return "Enter a complete URL, such as https://project.supabase.co."

    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and hostname not in local_hosts:
        return "Hosted Supabase projects must use HTTPS."
    return None


def _legacy_key_role(key: str) -> str | None:
    """Read the role from a legacy JWT key without verifying or logging it."""
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode()).decode()
        value = json.loads(decoded)
    except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, Mapping):
        return None
    role = value.get("role")
    return role if isinstance(role, str) else None


def validate_public_api_key(key: str) -> str | None:
    """Allow publishable or legacy anon keys and reject privileged credentials."""
    normalized = key.strip()
    if not normalized:
        return "Enter a publishable key."
    if normalized.startswith("sb_publishable_"):
        return None
    if normalized.startswith("sb_secret_"):
        return "Secret keys are not accepted. Use an sb_publishable_ key instead."

    role = _legacy_key_role(normalized)
    if role == "anon":
        return None
    if role == "service_role":
        return "Service-role keys are not accepted. Use a publishable key instead."

    return "Enter an sb_publishable_ key or a legacy anon key."


def validate_sign_up(email: str, password: str) -> str | None:
    """Validate the fields required by the demo's email sign-up form."""
    email_error = validate_email_address(email)
    if email_error:
        return email_error
    if len(password) < 6:
        return "Password must contain at least 6 characters."
    return None


def validate_email_address(email: str) -> str | None:
    """Validate an email address without coupling it to password rules."""
    normalized = email.strip()
    if not normalized:
        return "Enter an email address."
    if not _is_valid_email(normalized):
        return "Enter a valid email address."
    return None


def validate_password_sign_in(identifier: str, password: str) -> str | None:
    """Validate the demo's email-or-phone password sign-in form."""
    normalized_identifier = identifier.strip()
    if not normalized_identifier:
        return "Enter an email address or phone number."
    if "@" in normalized_identifier and not _is_valid_email(normalized_identifier):
        return "Enter a valid email address."
    if len(password) < 6:
        return "Password must contain at least 6 characters."
    return None


def _is_valid_email(value: str) -> bool:
    """Perform bounded, linear-time validation suitable for a sign-in hint."""
    if len(value) > 320 or value.count("@") != 1 or any(char.isspace() for char in value):
        return False
    local_part, domain = value.split("@", maxsplit=1)
    if not local_part or len(local_part) > 64 or not domain or len(domain) > 255:
        return False
    labels = domain.split(".")
    return len(labels) >= 2 and all(labels)
