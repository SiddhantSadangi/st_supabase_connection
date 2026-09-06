# Changelog

All notable changes to `st-supabase-connection` are documented here. This project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.1] - 2026-09-06

### Changed

- Library read caches now retain at most 128 entries per operation; TTL semantics are unchanged.
- The demo defaults to fresh reads, with a 60-second TTL when caching is enabled.
- Pinned the Python 3.12 demo runtime independently of library dependency ranges, with CI verification.
- Added a minimal `pyproject.toml` for the build backend and formatter settings.
- Cached library reads now return independent data copies instead of shared mutable resources.
- Bucket creation/update and object move/remove delegate to the public Storage SDK methods.
- Removed public-URL result caching; the existing `ttl` argument remains accepted and is ignored.
- Corrected Storage return annotations and the signed-upload token documentation.
- Simplified the demo to use Streamlit's default exception reporting; removed the
  SMTP traceback hook and the `streamlit-extras` dependency.
- Database query execution and the generated Python preview now share the same
  validated call sequence.
- Removed unused demo helpers, redundant connection state, and optional profile
  and attribution fields from the custom-project sign-up example.

### Fixed

- Workspace navigation has an explicit initial selection, and single-choice controls cannot be cleared accidentally.
- The demo clears Database/Storage results and pending confirmations when the authenticated user changes or signs out.
- Workspace rendering stops if the Auth session cannot be checked, hiding previously displayed results.
- Isolated Storage result caches by project, credentials, and current headers, including authorization changes.
- `execute_query()` no longer caches writes, POST-based RPC calls, or unrecognized request methods, even when a TTL is supplied.
- Preserved the documented single-string MIME type input to `update_bucket()` by converting it to an SDK-compatible list.
- Auth forms validate on submission so users can submit newly entered sign-in,
  sign-up, and OTP fields without an unrelated app rerun.

### Tests

- Added real-cache regression tests with mocked HTTP transports for project/auth isolation, repeated writes, response mutation, and Storage SDK request compatibility.
- Added a CI case for the minimum supported Supabase version alongside the existing Python/Streamlit matrix.

## [2.2.0] - 2026-08-25

### Added

- Added `SupabaseConnection.session_client()`, which returns one complete Supabase client
  per Streamlit browser session and connection. Use it for Auth and for Database, Storage,
  Functions, or Realtime calls that must carry a signed-in user's JWT.
- Added first-class `SUPABASE_PUBLISHABLE_KEY` support for Streamlit secrets and environment
  variables. It takes precedence over the legacy `SUPABASE_KEY` name when both are present.
- Added automated coverage for Python 3.10 through 3.14, the minimum and latest supported
  Streamlit versions, the demo, the library, and built package installation.

### Changed

- Raised the minimum Streamlit version from 1.50 to 1.62.0. Python 3.10 and
  `supabase>=2.22.0` remain the other minimum runtime requirements.
- Browser uploads are now handled in memory instead of being written to the Streamlit
  server's working directory. Hosted file handles are closed deterministically.
- Storage upload destinations are normalized consistently, and an invalid `source` now
  raises `ValueError` before any Storage request is made.
- `execute_query()` cache keys now include the request method, project URL, path, parameters,
  payload, and irreversible fingerprints of authorization headers. This isolates cached
  results across projects and signed-in users without storing raw credentials in the key.

### Deprecated

- `SupabaseConnection.auth` is deprecated because a Streamlit connection is shared across
  browser sessions. Replace it with `connection.session_client().auth`.
- `cached_sign_in_with_password()` is deprecated. It now delegates to the session-scoped
  client without caching the Auth response; its `ttl` argument is retained for compatibility
  but ignored.

### Security

- Auth flows using `session_client()` keep sessions and tokens in the current Streamlit
  browser session instead of the process-shared connection.
- `cached_sign_in_with_password()` no longer puts Auth responses in Streamlit's global
  resource cache.
- The demo accepts only publishable or legacy anonymous credentials and does not accept
  Supabase secret or `service_role` keys.
- Generated demo code is displayed for review and copying; it is not executed with `eval()`.

### Demo and release tooling

- Reworked the demo into focused Storage, Database, and Auth workspaces with safer structured
  inputs, stale-result handling, and explicit review for write or destructive operations.
- Demo Auth is sign-in-only for existing users. Account creation remains available to library
  users through the session-scoped Supabase Auth client.
- Added Trusted Publishing workflows for manual TestPyPI rehearsals and approval-gated PyPI
  releases without long-lived registry credentials.

### Migrating from 2.1.x

No public method has been removed. Apps that only use public or anonymous Storage and Database
operations generally need no source changes after satisfying the new Streamlit requirement.

Auth and user-scoped operations should migrate from the shared connection client:

```python
# 2.1.x: shared across Streamlit sessions
st_supabase.auth.sign_in_with_password(credentials)
response = st_supabase.table("private_profiles").select("*").execute()
```

to the session-scoped client:

```python
# 2.2.0: isolated to the current browser session
supabase = st_supabase.session_client()
supabase.auth.sign_in_with_password(credentials)
response = supabase.table("private_profiles").select("*").execute()
```

For user-facing apps, prefer `SUPABASE_PUBLISHABLE_KEY`. The legacy `SUPABASE_KEY` name remains
supported, so renaming it is recommended but not required for 2.2.0.

[Unreleased]: https://github.com/SiddhantSadangi/st_supabase_connection/compare/v2.2.1...HEAD
[2.2.1]: https://github.com/SiddhantSadangi/st_supabase_connection/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/SiddhantSadangi/st_supabase_connection/compare/v2.1.3...v2.2.0
