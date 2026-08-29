# Authentication and security

Supabase Auth mutates client state by storing the current session and refreshing its tokens. Because Streamlit connection objects may be shared across browser sessions, Auth must use `session_client()` rather than the process-shared connection client.

## Choose an API key

| Key | Use with this library |
|---|---|
| Publishable (`sb_publishable_...`) | Recommended for user-facing apps. RLS determines what anonymous and signed-in users can access. |
| Legacy `anon` | Supported through the legacy `SUPABASE_KEY` setting, but Supabase recommends migrating to a publishable key. |
| Secret (`sb_secret_...`) | Backend-only administrative work. Bypasses RLS. Do not use for user-scoped app operations. |
| Legacy `service_role` | Legacy equivalent of a secret key. Bypasses RLS and must not be exposed. |

A publishable key identifies the application; it does not make a signed-in user anonymous. After Auth succeeds, the Supabase client sends the user's JWT and Postgres evaluates policies using the `authenticated` role.

Configure a publishable key in `.streamlit/secrets.toml`:

```toml
[connections.supabase_connection]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

See [Supabase's API key documentation](https://supabase.com/docs/guides/getting-started/api-keys) for the current key types and migration guidance.

## Create a session client

Create the shared connection normally, then ask it for the client belonging to the current browser session:

```python
import streamlit as st

from st_supabase_connection import SupabaseConnection

connection = st.connection(
    "supabase_connection",
    type=SupabaseConnection,
)
supabase = connection.session_client()
```

It is safe to execute this on every Streamlit rerun. The same client is reused within that Streamlit browser session.

Do not store `supabase` in:

- a module-level variable;
- `st.cache_resource`;
- another global cache; or
- a global singleton outside Streamlit session state.

## Sign in with a password

Use a form so editing either field does not submit partial credentials on every rerun:

```python
supabase = connection.session_client()

with st.form("sign_in"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Sign in")

if submitted:
    try:
        supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception:
        st.error("Unable to sign in. Check your email and password.")
    else:
        st.success("Signed in")
        st.rerun()
```

The generic error avoids revealing whether a particular email address exists. Applications that need more detailed support diagnostics can log sanitized error details on the server.

## Check the current session

```python
supabase = connection.session_client()
session = supabase.auth.get_session()

if session is None:
    st.info("Sign in to continue")
    st.stop()

st.write(f"Signed in as {session.user.email}")
```

For authorization-sensitive server checks, use `supabase.auth.get_user()` to retrieve a user validated by the Auth server rather than trusting UI state alone.

## Query rows protected by RLS

Use the same session client that performed sign-in:

```python
response = (
    supabase.table("private_profiles")
    .select("id, display_name")
    .execute()
)
st.dataframe(response.data)
```

Using `connection.table(...)` here would build the query from the shared anonymous client and would not carry the current user's JWT.

Authenticated reads can also use `execute_query()` with a finite TTL. Its cache key includes an irreversible authorization fingerprint so users do not share an authenticated cache entry:

```python
from st_supabase_connection import execute_query

response = execute_query(
    supabase.table("private_profiles").select("id, display_name"),
    ttl="1m",
)
```

## Sign out

```python
if st.button("Sign out"):
    supabase.auth.sign_out()
    st.rerun()
```

Continue using `session_client()` after the rerun. Do not replace the session client with the process-shared connection.

## Sign-up and other Auth methods

The library returns the complete Supabase Python client, so the full Auth API remains available:

```python
supabase.auth.sign_up(
    {
        "email": email,
        "password": password,
        "options": {"data": {"display_name": display_name}},
    }
)
```

The project demo is intentionally sign-in-only for existing users. That demo policy does not remove sign-up support from the library.

## Deprecated shared Auth access

The following APIs remain temporarily available for compatibility but should not be used in new code:

```python
connection.auth.sign_in_with_password(credentials)
connection.cached_sign_in_with_password(credentials, ttl="1h")
```

`connection.auth` operates on the shared connection client. `cached_sign_in_with_password()` now delegates to the session client without caching, ignores `ttl`, and emits a deprecation warning.

Use instead:

```python
supabase = connection.session_client()
supabase.auth.sign_in_with_password(credentials)
```

## Security checklist

- Enable RLS on every table in an exposed schema and create policies for the actual access model.
- Treat publishable and legacy `anon` keys as application identifiers, not authorization controls.
- Never expose secret or `service_role` keys; they bypass RLS.
- Do not use user-editable `user_metadata` to make authorization decisions. Put authorization claims in server-controlled `app_metadata`, and account for JWT refresh timing.
- Scope policies to row ownership where appropriate. `TO authenticated` alone confirms authentication but does not restrict one user from another user's rows.
- For update policies, define both which existing rows can be targeted and which resulting values are allowed.
- Do not cache passwords, Auth responses, session clients, or access tokens in process-global caches.

For policy patterns, see [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) and [Securing your data](https://supabase.com/docs/guides/database/secure-data).

## Troubleshooting

### Sign-in succeeds but no rows are returned

Check all three layers:

1. The query was built from `connection.session_client()`, not the anonymous shared connection.
2. The table is exposed through the Data API and the `authenticated` role has the required table grant.
3. An RLS policy permits the current `auth.uid()` to access the requested rows.

Data API grants and RLS are separate: grants make a table reachable, while RLS decides which rows are visible.

### One user appears to inherit another user's session

Search for module-level Supabase clients, `st.cache_resource` around `session_client()`, or direct use of `connection.auth`. Remove those shared locations and create the client with `connection.session_client()` inside the Streamlit script.

## Related guides

- [Database recipes](database.md)
- [Caching](caching.md)

[Back to the guide index](README.md)
