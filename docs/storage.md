# Storage recipes

The connection provides Streamlit-friendly wrappers around common Supabase Storage operations. Read methods accept cache TTLs, uploaded files can remain in memory, and object paths are normalized before selected signed-URL operations.

## List buckets

```python
buckets = connection.list_buckets(ttl="30m")

for bucket in buckets:
    st.write(bucket.name)
```

Use a finite TTL when bucket configuration may change while the app is running.

Bucket reads return SDK bucket models (for example, `bucket.name`), not dictionaries. In 2.2.1, cached models and lists are returned as independent copies and are isolated by project and credentials. See [Caching](caching.md) for details.

## Get one bucket

```python
bucket = connection.get_bucket("documents", ttl="30m")
st.write(bucket)
```

## Create a bucket

```python
connection.create_bucket(
    id="documents",
    public=False,
    file_size_limit=10 * 1024 * 1024,
    allowed_mime_types=["application/pdf", "text/csv"],
)
```

`file_size_limit` is expressed in bytes. Use private buckets unless every object in the bucket is intentionally public.

## Update a bucket

```python
connection.update_bucket(
    bucket_id="documents",
    public=False,
    file_size_limit=20 * 1024 * 1024,
    allowed_mime_types=["application/pdf", "text/csv"],
)
```

## Upload from `st.file_uploader`

`st.file_uploader()` returns an in-memory uploaded file. Pass it directly instead of first writing it to the app server:

```python
uploaded_file = st.file_uploader(
    "Choose a document",
    type=["pdf", "csv"],
)

if uploaded_file is not None and st.button("Upload"):
    response = connection.upload(
        bucket_id="documents",
        source="local",
        file=uploaded_file,
        destination_path=f"incoming/{uploaded_file.name}",
        overwrite="false",
    )
    st.success("Upload complete")
    st.write(response)
```

The wrapper resets file-like objects before reading and infers the content type from the upload metadata or file name.

`overwrite` uses the strings `"true"` and `"false"` for compatibility with the Supabase Storage API.

## Upload a server-side file

When the file already exists on the app server, pass its path:

```python
from pathlib import Path

connection.upload(
    bucket_id="documents",
    source="hosted",
    file=Path("generated/monthly-report.pdf"),
    destination_path="reports/monthly-report.pdf",
    overwrite="true",
)
```

Only use paths controlled by the application. Do not turn arbitrary user input into server filesystem paths.

## Download a file

The wrapper returns the inferred filename, MIME type, and downloaded bytes:

```python
file_name, mime_type, data = connection.download(
    bucket_id="documents",
    source_path="reports/monthly-report.pdf",
    ttl="10m",
)

st.download_button(
    "Download report",
    data=data,
    file_name=file_name,
    mime=mime_type,
)
```

The bytes remain in memory; the wrapper does not create a temporary download file.

## List objects

```python
objects = connection.list_objects(
    bucket_id="documents",
    path="reports",
    limit=50,
    offset=0,
    sortby="updated_at",
    order="desc",
    ttl="5m",
)

st.dataframe(objects)
```

## Move or rename an object

```python
connection.move(
    bucket_id="documents",
    from_path="incoming/report.pdf",
    to_path="reports/report.pdf",
)
```

## Remove objects

```python
connection.remove(
    bucket_id="documents",
    paths=[
        "reports/old-report.pdf",
        "reports/old-export.csv",
    ],
)
```

Supabase recommends deleting Storage objects through the Storage API rather than deleting rows directly from `storage.objects`.

## Public URLs

For an object in a public bucket:

```python
public_url = connection.get_public_url(
    bucket_id="public-assets",
    filepath="images/logo.png",
)
st.link_button("Open image", public_url)
```

Generating a public URL does not make a private bucket public and does not verify that the object exists.

This operation only constructs a URL locally; it is not cached. The legacy `ttl` argument is still accepted but ignored.

## Signed download URLs

For time-limited access to private objects:

```python
signed = connection.create_signed_urls(
    bucket_id="documents",
    paths=[
        "reports/report.pdf",
        "exports/data.csv",
    ],
    expires_in=600,
)
st.write(signed)
```

Leading slashes are removed from paths. Empty paths are rejected.

Signed URLs are credentials for the referenced objects until they expire. Avoid logging them or storing them longer than needed.

## Signed uploads

Create a signed upload URL on a trusted path, then upload using its token:

```python
destination_path = f"incoming/{uploaded_file.name}"

signed_upload = connection.create_signed_upload_url(
    bucket_id="documents",
    path=destination_path,
)

result = connection.upload_to_signed_url(
    bucket_id="documents",
    path=signed_upload["path"],
    token=signed_upload["token"],
    file=uploaded_file,
)
```

The path supplied to `upload_to_signed_url()` must match the path used to create the token. The wrapper accepts uploaded files, raw bytes, open binary files, and server-side paths.

## Empty or delete a bucket

Empty a bucket before deleting it:

```python
connection.empty_bucket("temporary-exports")
connection.delete_bucket("temporary-exports")
```

Both operations are destructive. Confirm the exact bucket and apply an authorization check in the application before exposing either action to users.

## Authenticated Storage operations

The convenience wrappers use the shared connection client. When a Storage policy depends on the signed-in user's JWT, use the session client's Storage API:

```python
supabase = connection.session_client()

response = (
    supabase.storage.from_("avatars")
    .upload(
        path=f"{user_id}/avatar.png",
        file=uploaded_file.getvalue(),
        file_options={"content-type": uploaded_file.type},
    )
)
```

Use the same `supabase` client that performed sign-in so Storage receives the user's current JWT.

## Storage policy requirements

Storage authorization is enforced through RLS policies on the `storage.objects` table. The exact privileges depend on the action:

- A new upload requires `INSERT`.
- An upsert requires `INSERT`, `SELECT`, and `UPDATE`.
- A download or listing requires `SELECT`.
- A move requires `SELECT` and `UPDATE`.
- A delete requires `SELECT` and `DELETE`.

See [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control) and the relevant [Python Storage reference](https://supabase.com/docs/reference/python/storage-from-upload) before writing policies.

## Troubleshooting

### Upload returns a policy error

- Confirm the query uses the session client's Storage API when the policy depends on `auth.uid()`.
- Check that the destination path matches the path expression in the policy.
- For overwrite/upsert, add the required select and update permissions in addition to insert.
- Confirm the bucket's allowed MIME types and file-size limit accept the file.

### The downloaded file has a generic MIME type

The wrapper falls back to `application/octet-stream` when the filename has no recognized extension. Supply meaningful object filenames and preserve their extensions.

### Object listings look stale

Use a finite `ttl` or temporarily call `list_objects(..., ttl=0)` after a write. Storage writes do not automatically invalidate previously cached listings.

## Related guides

- [Authentication and security](authentication.md)
- [Caching](caching.md)

[Back to the guide index](README.md)
