# Caching

Streamlit Supabase Connection uses Streamlit caching for the connection object and for selected read results. Those caches have different scopes and should be configured separately.

## Cache types

| Cache | Configuration | Purpose |
|---|---|---|
| Connection object | `st.connection(..., ttl=...)` | Controls how long the underlying `SupabaseConnection` object is retained |
| Storage result | A wrapper such as `list_objects(..., ttl=...)` | Controls how long that returned Storage result is retained |
| Database result | `execute_query(..., ttl=...)` | Controls how long the query response is retained |
| Auth | Not cached | Keeps credentials and tokens out of process-shared result caches |

## Connection lifetime

`st.connection()` internally caches connection objects as resources. For a long-lived, stateless Supabase connection, the default is normally appropriate:

```python
connection = st.connection(
    "supabase_connection",
    type=SupabaseConnection,
)
```

Set `ttl` on `st.connection()` only when the connection object itself should be periodically reconstructed:

```python
connection = st.connection(
    "supabase_connection",
    type=SupabaseConnection,
    ttl="12h",
)
```

This does not set the lifetime of results returned by `execute_query()` or the Storage wrappers.

## Storage result caching

Read wrappers accept a Streamlit-compatible `ttl`:

```python
buckets = connection.list_buckets(ttl="30m")
objects = connection.list_objects("documents", ttl="5m")
file_name, mime_type, data = connection.download(
    "documents",
    "reports/latest.csv",
    ttl="10m",
)
```

`ttl=None` retains a result without time-based expiration. Prefer a finite value for content that can change.

## Database result caching

Use `execute_query()` for reads that benefit from caching:

```python
from st_supabase_connection import execute_query

response = execute_query(
    connection.table("countries").select("id, name").order("name"),
    ttl="10m",
)
```

Practical starting points:

| Data | Suggested starting TTL |
|---|---|
| Frequently changing UI data | `"30s"` to `"2m"` |
| Reports and common lists | `"5m"` to `"15m"` |
| Reference data | `"1h"` or longer |
| Immutable content | `None` |

Choose a value based on acceptable staleness and API traffic rather than treating these ranges as requirements.

## User-specific reads

For rows protected by a signed-in user's RLS policies, build the query from the session client:

```python
supabase = connection.session_client()

response = execute_query(
    supabase.table("private_profiles").select("*"),
    ttl="1m",
)
```

`execute_query()` includes an irreversible fingerprint of the authorization headers in its cache key. Authenticated users therefore do not share the same cached entry. The raw token is not placed in the key.

Use the same `supabase` client for sign-in and for the query so its current JWT is attached.

## Writes and immediate consistency

Do not cache inserts, updates, upserts, or deletes. Call `.execute()` directly:

```python
response = (
    connection.table("countries")
    .insert({"name": "Wakanda", "iso2": "WK"})
    .execute()
)
```

For compatibility, a write can be passed through `execute_query(..., ttl=0)`, but direct execution communicates the intent more clearly.

Writing data does not automatically invalidate earlier cached reads. When the UI must show a write immediately, fetch the next read directly with `.execute()` or use `ttl=0`. Otherwise, let the read's finite TTL expire.

## Auth must not be cached

Create the session client through `session_client()` and call Auth directly:

```python
supabase = connection.session_client()
supabase.auth.sign_in_with_password(credentials)
```

Do not put the session client or Auth response in `st.cache_resource`, a module-level variable, or another process-global cache. Streamlit connection resources may be shared across browser sessions; Auth state must not be.

`cached_sign_in_with_password()` is deprecated. Despite its legacy name, version 2.2.0 no longer caches its result and ignores its `ttl` argument.

## Cache growth

Parameterized reads can create many cache entries. Use finite TTLs for high-cardinality queries, especially user-specific or search-driven requests. Avoid caching a new result for every keystroke; submit search inputs through a form or otherwise limit the number of distinct queries.

`connection.reset()` reconstructs a stale connection object. It is not a replacement for setting appropriate result TTLs.

## Related guides

- [Database recipes](database.md)
- [Authentication and security](authentication.md)
- [Storage recipes](storage.md)

[Back to the guide index](README.md)
