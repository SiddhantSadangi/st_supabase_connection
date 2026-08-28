# Database recipes

The connection exposes Supabase Python's PostgREST query builder through `connection.table()`. Use `execute_query()` for cached reads and the query builder's `.execute()` method for writes.

## Anonymous cached reads

Use the shared connection for public data or rows available to the Supabase `anon` role:

```python
from st_supabase_connection import execute_query

response = execute_query(
    connection.table("countries")
    .select("id, name, iso2")
    .order("name")
    .limit(50),
    ttl="10m",
)

st.dataframe(response.data)
```

The result is a Supabase `APIResponse`. Rows are available through `response.data`; when requested, the total is available through `response.count`.

## Filters

Compose filters with the standard Supabase Python query builder:

```python
response = execute_query(
    connection.table("cities")
    .select("id, name, population")
    .gte("population", 100_000)
    .order("population", desc=True),
    ttl="5m",
)
```

See the [Supabase Python filter reference](https://supabase.com/docs/reference/python/using-filters) for the full set of operators.

## Joins and counts

```python
response = execute_query(
    connection.table("users").select(
        "name, teams(name)",
        count="exact",
    ),
    ttl="10m",
)

st.write(f"Rows: {response.count}")
st.dataframe(response.data)
```

Foreign-table filtering uses the same PostgREST syntax:

```python
response = execute_query(
    connection.table("cities")
    .select("name, countries(name, iso2)")
    .eq("countries.name", "Curaçao"),
    ttl="10m",
)
```

## Inserts

Writes should execute directly so their responses are not cached:

```python
response = (
    connection.table("countries")
    .insert(
        [
            {"name": "Wakanda", "iso2": "WK"},
            {"name": "Wadiya", "iso2": "WD"},
        ]
    )
    .execute()
)
```

Use the session client instead when the insert must be evaluated as the signed-in user:

```python
supabase = connection.session_client()

response = (
    supabase.table("notes")
    .insert({"owner_id": user_id, "body": note_body})
    .execute()
)
```

The database should derive or validate ownership where possible; do not rely solely on a user-supplied `owner_id`.

## Updates

Always filter updates to the intended rows:

```python
response = (
    supabase.table("notes")
    .update({"body": revised_body})
    .eq("id", note_id)
    .execute()
)
```

Under RLS, an update also needs a policy that allows the row to be selected. A missing select policy can produce an empty result rather than an obvious authorization error. Update policies should restrict both the existing row and the values permitted after the change.

## Deletes

```python
response = (
    supabase.table("notes")
    .delete()
    .eq("id", note_id)
    .execute()
)
```

Use narrow filters and enforce ownership in RLS. UI filters are not a security boundary.

## User-scoped reads

After sign-in, build protected queries from the same session client:

```python
supabase = connection.session_client()

response = (
    supabase.table("private_profiles")
    .select("id, display_name")
    .execute()
)
```

To cache an authenticated read, pass that session client's query to `execute_query()`:

```python
response = execute_query(
    supabase.table("private_profiles").select("id, display_name"),
    ttl="1m",
)
```

The authorization headers contribute an irreversible fingerprint to the cache key, isolating authenticated entries. Use a finite TTL for user-specific data.

## Data API exposure and RLS

Supabase is changing its defaults so newly created tables may not be automatically exposed through the Data API. If a valid query returns a schema or permission error, confirm that:

1. the schema is exposed in the project's Data API settings;
2. the `anon` or `authenticated` role has the required table privileges; and
3. RLS is enabled with a policy that permits the requested rows.

Exposure and grants determine whether a table can be reached. RLS determines which rows a reachable role can access. Enabling one does not replace the other.

Follow Supabase's [Data API security guide](https://supabase.com/docs/guides/api/securing-your-api) before granting access to an exposed table.

## Cache-safe writes

`execute_query()` accepts all common query builders, but writes should normally use `.execute()` directly. If existing code passes writes through `execute_query()`, set `ttl=0`:

```python
response = execute_query(
    connection.table("countries").insert({"name": "Wakanda"}),
    ttl=0,
)
```

A write does not invalidate an earlier cached select. For an immediately consistent UI, run the next select directly or with `ttl=0`; otherwise, use a suitably short finite TTL.

## Troubleshooting

### The response contains no rows

- Read `response.data`, not the response object as if it were a list.
- Confirm the table's Data API exposure and role grants.
- Check RLS using the same role and user represented by the query.
- For signed-in data, build the query from `connection.session_client()`.
- For updates, confirm an applicable select policy also exists.

### The UI shows old data after a write

The prior select is probably cached. Fetch once with `.execute()` or `execute_query(..., ttl=0)`, then choose a finite TTL suitable for subsequent reads.

### A count is always `None`

Request it explicitly with `select(..., count="exact")` or another supported count strategy.

## Related guides

- [Authentication and security](authentication.md)
- [Caching](caching.md)

[Back to the guide index](README.md)
