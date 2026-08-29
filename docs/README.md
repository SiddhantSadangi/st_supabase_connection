# Streamlit Supabase Connection guides

These guides expand on the project [README](../README.md) without making the package landing page an exhaustive API reference.

## Start here

| Goal | Guide |
|---|---|
| Understand connection and result caching | [Caching](caching.md) |
| Upload, download, or manage Storage objects | [Storage recipes](storage.md) |
| Read or write Database rows | [Database recipes](database.md) |
| Sign users in and apply their RLS policies | [Authentication and security](authentication.md) |
| Upgrade an existing app | [Changelog](../CHANGELOG.md) |
| Explore the UI | [Interactive demo](https://st-supabase-connection.streamlit.app/) |

## Shared setup

The examples use this connection:

```python
import streamlit as st

from st_supabase_connection import SupabaseConnection

connection = st.connection(
    "supabase_connection",
    type=SupabaseConnection,
)
```

Configure it in `.streamlit/secrets.toml`:

```toml
[connections.supabase_connection]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

The examples consistently use:

- `connection` for the process-shared `SupabaseConnection` returned by `st.connection()`.
- `supabase` for the browser-session-scoped client returned by `connection.session_client()`.

Use `connection` for anonymous cached reads. Use `supabase` for Auth and any operation that must carry a signed-in user's JWT.

## External references

- [Streamlit connections](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data)
- [Supabase Python reference](https://supabase.com/docs/reference/python/introduction)
- [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)

[Back to the project README](../README.md)
