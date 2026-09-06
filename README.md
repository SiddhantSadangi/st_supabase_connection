# Streamlit Supabase Connection

<div align="center">
  <a href="https://github.com/SiddhantSadangi/st_supabase_connection/actions/workflows/ci.yml">
    <img src="https://github.com/SiddhantSadangi/st_supabase_connection/actions/workflows/ci.yml/badge.svg" alt="CI status">
  </a>
  <a href="https://pypi.org/project/st-supabase-connection/">
    <img src="https://img.shields.io/pypi/v/st-supabase-connection" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/st-supabase-connection/">
    <img src="https://img.shields.io/pypi/pyversions/st-supabase-connection" alt="Supported Python versions">
  </a>
  <a href="https://pepy.tech/project/st-supabase-connection">
    <img src="https://static.pepy.tech/personalized-badge/st-supabase-connection?period=total&units=international_system&left_color=black&right_color=brightgreen&left_text=Downloads" alt="Downloads">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT license">
  </a>
</div>

Use Supabase Storage, Database, and Auth from Streamlit with Streamlit-aware caching and browser-session-safe authentication.

[Open the interactive demo](https://st-supabase-connection.streamlit.app/) ·
[Read the guides](https://github.com/SiddhantSadangi/st_supabase_connection/tree/main/docs) ·
[View the changelog](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/CHANGELOG.md)

## Why use it?

- Use `st.connection()` and Streamlit secrets for Supabase configuration.
- Cache Storage and Database reads with familiar `ttl` values such as `"10m"`.
- Keep Supabase Auth tokens isolated to the current Streamlit browser session.
- Upload `st.file_uploader()` results without first writing them to the app server.
- Normalize Storage paths and infer common MIME types automatically.

## Requirements

| Component | Supported version |
|---|---|
| Python | 3.10 or newer |
| Streamlit | 1.62.0 or newer |
| Supabase Python | 2.22.0 or newer |

## Quickstart

Install the package:

```bash
pip install st-supabase-connection
```

Add your project URL and publishable key to `.streamlit/secrets.toml`:

```toml
[connections.supabase_connection]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

Create the connection and make a cached read:

```python
import streamlit as st

from st_supabase_connection import SupabaseConnection

connection = st.connection(
    "supabase_connection",
    type=SupabaseConnection,
)

buckets = connection.list_buckets(ttl="10m")
st.write(buckets)
```

The legacy `SUPABASE_KEY` setting is still supported. New user-facing apps should use a Supabase publishable key. Never use a secret or `service_role` key for user-scoped operations because those keys bypass Row Level Security.

You can also supply `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` as environment variables, or pass `url=` and `key=` to `st.connection()`.

## Choose the right client

Streamlit connection objects are cached resources and may be shared between browser sessions. Choose the client based on whether the operation depends on a signed-in user.

| Use case | Recommended API |
|---|---|
| Public or anonymous cached reads | The shared `connection` and its cached helpers |
| Supabase Auth | `connection.session_client().auth` |
| Reads or writes protected by the signed-in user's RLS policies | The same `connection.session_client()` used for sign-in |
| Privileged administrative work | A separate, secured backend using a secret key—not a user-facing app flow |

Create the session-scoped client inside the Streamlit script:

```python
supabase = connection.session_client()
```

Reuse that client for Auth and user-specific operations. Do not put it in a module-level variable, `st.cache_resource`, or another global cache.

## Caching behavior

There are two different kinds of `ttl`:

| Where `ttl` is set | What it controls |
|---|---|
| `st.connection(..., ttl=...)` | How long Streamlit keeps the connection object |
| `connection.list_buckets(ttl=...)`, `connection.download(ttl=...)`, or `execute_query(..., ttl=...)` | How long the returned result is cached |

In most apps, omit `ttl` from `st.connection()` and set a finite `ttl` on reads that can change:

```python
from st_supabase_connection import execute_query

countries = execute_query(
    connection.table("countries").select("id, name").order("name"),
    ttl="10m",
)
st.dataframe(countries.data)
```

Do not cache Auth calls. Starting in 2.2.1, `execute_query()` automatically bypasses caching for inserts, updates, upserts, deletes, and POST-based RPC calls. Direct `.execute()` calls also remain supported; `ttl=0` fetches fresh data for reads.

See the [caching guide](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/docs/caching.md) for cache scope, user-specific queries, and invalidation considerations.

## Common workflows

### Upload from `st.file_uploader`

The uploaded file is handled in memory; it does not need to be copied to the app server first.

```python
uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None and st.button("Upload"):
    connection.upload(
        bucket_id="documents",
        source="local",
        file=uploaded_file,
        destination_path=f"uploads/{uploaded_file.name}",
        overwrite="false",
    )
    st.success("Upload complete")
```

### Query the database

Use the shared connection for anonymous reads:

```python
from st_supabase_connection import execute_query

response = execute_query(
    connection.table("countries").select("id, name").limit(20),
    ttl="5m",
)
st.dataframe(response.data)
```

Use the session client for rows protected by a signed-in user's RLS policies:

```python
supabase = connection.session_client()
response = supabase.table("private_profiles").select("*").execute()
st.dataframe(response.data)
```

### Sign in an existing user

```python
supabase = connection.session_client()

email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Sign in"):
    supabase.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    st.success("Signed in")
```

After sign-in, use the same `supabase` client for all operations that must carry the user's JWT.

## Guides and recipes

- [Storage recipes](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/docs/storage.md): buckets, uploads, downloads, object management, and signed URLs
- [Database recipes](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/docs/database.md): cached reads, joins, filters, writes, RLS, and Data API access
- [Authentication and security](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/docs/authentication.md): keys, sign-in, session isolation, sign-out, and user-scoped queries
- [Caching](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/docs/caching.md): connection lifetime, result lifetime, and cache-safe writes
- [Upgrade notes](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/CHANGELOG.md): behavioral changes and migration guidance

## Supported functionality

The connection includes Streamlit-friendly wrappers for commonly used Storage operations:

- Bucket management: `list_buckets()`, `get_bucket()`, `create_bucket()`, `update_bucket()`, `empty_bucket()`, and `delete_bucket()`
- Objects: `upload()`, `download()`, `list_objects()`, `move()`, and `remove()`
- URLs: `get_public_url()`, `create_signed_urls()`, `create_signed_upload_url()`, and `upload_to_signed_url()`
- Database: `table()` and the cached `execute_query()` helper
- Auth and other user-scoped Supabase APIs: `session_client()`

Because `session_client()` returns the complete Supabase Python client, it can also be used for Functions, Realtime, and other SDK features that must carry the current user's session.

## Upgrading

### 2.2.1

This patch fixes Storage cache isolation between projects and credentials, prevents `execute_query()` from caching writes, and returns independent copies of cached read responses. No public methods are removed and dependency minimums are unchanged.

`get_public_url()` now constructs URLs without caching; existing `ttl` arguments remain accepted but are ignored. Apps that manually clear cached results should use `st.cache_data.clear()`, not only `st.cache_resource.clear()`.

### From 2.1.x to 2.2.x

Version 2.2.0 requires Python 3.10+, Streamlit 1.62.0+, and Supabase Python 2.22.0+.

Apps using Auth should replace process-shared access:

```python
# Deprecated
connection.auth.sign_in_with_password(credentials)
```

with a session-scoped client:

```python
supabase = connection.session_client()
supabase.auth.sign_in_with_password(credentials)
```

`connection.auth` and `cached_sign_in_with_password()` remain available for compatibility but are deprecated. The latter no longer caches its result and ignores `ttl`.

See the [2.2.0 changelog](https://github.com/SiddhantSadangi/st_supabase_connection/blob/main/CHANGELOG.md) for the complete migration notes.

## Development

Install the project, then run the library and demo tests:

```bash
python -m pip install --editable .
python -m unittest discover --start-directory tests --verbose
```

The CI workflow tests Python 3.10–3.14 against the minimum and latest supported Streamlit releases.

For the reproducible demo runtime, use **Python 3.12** and run from the repository root:

```bash
python -m pip install -r demo/requirements.txt
python -m pip check
python -m streamlit run demo/app.py
```

`demo/requirements.txt` pins the demo environment, including transitive dependencies;
the published library keeps flexible dependency ranges. CI also tests this pinned set.
Refresh the pins in a clean Python 3.12 environment when upgrading the demo, and run
the suite plus the browser smoke checklist in [RELEASING.md](RELEASING.md).

Black and isort use the repository's `pyproject.toml` settings.

Issues and pull requests are welcome in the [GitHub repository](https://github.com/SiddhantSadangi/st_supabase_connection).

## Acknowledgements

This connector builds on [Streamlit](https://streamlit.io/), [Supabase Python](https://github.com/supabase/supabase-py), and the work of the Supabase open-source community.

If the project helps you, you can [sponsor it on GitHub](https://github.com/sponsors/SiddhantSadangi) or [buy me a coffee](https://www.buymeacoffee.com/siddhantsadangi).
