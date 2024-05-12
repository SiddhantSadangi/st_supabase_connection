# :electric_plug: Streamlit Supabase Connector
[![Downloads](https://static.pepy.tech/personalized-badge/st-supabase-connection?period=total&units=international_system&left_color=black&right_color=brightgreen&left_text=Downloads)](https://pepy.tech/project/st-supabase-connection)

A Streamlit connection component to connect Streamlit to Supabase Storage, Database, and Auth.

## :student: Interactive tutorial
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://st-supabase-connection.streamlit.app/)
![Web capture_2-12-2023_124639_st-supabase-connection streamlit app](https://github.com/SiddhantSadangi/st_supabase_connection/assets/41324509/2870b021-48a0-4143-9693-c840880a28be)


## :thinking: Why use this?
- [X] Cache functionality to cache returned results. **Save time and money** on your API requests
- [X] Same method names as the Supabase Python API. **Minimum relearning required**
- [X] **Exposes more storage methods** than currently supported by the Supabase Python API. For example, `update()`, `create_signed_upload_url()`, and `upload_to_signed_url()`
- [X] **Less keystrokes required** when integrating with your Streamlit app.

<details close>
<summary>Examples with and without the connector </summary>
<br>
<table>
<tr>
<td><b>Without connector</b></td><td><b>With connector</b></td>
<tr>
<td colspan="2"> Download file to local system from Supabase storage </td>
<tr>
<td valign="top">

```python
import mimetypes
import streamlit as st
from supabase import create_client

supabase_client = create_client(
    supabase_url="...", supabase_key="..."
)

bucket_id = st.text_input("Enter the bucket_id")
source_path = st.text_input("Enter source path")

file_name = source_path.split("/")[-1]

if st.button("Request download"):
    with open(file_name, "wb+") as f:
        response = supabase_client.storage.from_(
        bucket_id
        ).download(source_path)
        f.write(response)

    mime = mimetypes.guess_type(file_name)[0]
    data = open(file_name, "rb")

    st.download_button(
        "Download file", data=data, 
        file_name=file_name, mime=mime,
    )
```

</td>
<td valign="top">

```python
import streamlit as st
from st_supabase_connection import SupabaseConnection

st_supabase_client = st.connection(
    name="supabase_connection", type=SupabaseConnection
)

bucket_id = st.text_input("Enter the bucket_id")
source_path = st.text_input("Enter source path")

if st.button("Request download"):
    file_name, mime, data = st_supabase_client.download(
        bucket_id, source_path,
    )

    st.download_button(
        "Download file", data=data, 
        file_name=file_name, mime=mime,
    )

```

</td>
<tr>
<td colspan="2"> Upload file from local system to Supabase storage </td>
<tr>
<td valign="top">

```python
import streamlit as st
from supabase import create_client

supabase_client = create_client(
supabase_key="...", supabase_url="..."
)

bucket_id = st.text_input("Enter the bucket_id")
uploaded_file = st.file_uploader("Choose a file")
destination_path = st.text_input("Enter destination path")
overwrite = "true" if st.checkbox("Overwrite?") else "false"  

with open(uploaded_file.name, "wb") as f:
    f.write(uploaded_file.getbuffer())

if st.button("Upload"):
    with open(uploaded_file.name, "rb") as f:
        supabase_client.storage.from_(bucket_id).upload(
            path=destination_path,
            file=f,
            file_options={
            "content-type": uploaded_file.type,
            "x-upsert": overwrite,
            },
        )

``` 

</td>
<td valign="top">

```python
import streamlit as st
from st_supabase_connection import SupabaseConnection

st_supabase_client = st.connection(
    name="supabase_connection", type=SupabaseConnection
)

bucket_id = st.text_input("Enter the bucket_id")
uploaded_file = st.file_uploader("Choose a file"):
destination_path = st.text_input("Enter destination path")
overwrite = "true" if st.checkbox("Overwrite?") else "false" 

if st.button("Upload"):
    st_supabase_client.upload(
        bucket_id, "local", uploaded_file, 
        destination_path, overwrite,
    )
```
<tr>
</table>

</details>

## :hammer_and_wrench: Setup

1. Install `st-supabase-connection`
```sh
pip install st-supabase-connection
```
2. Set the `SUPABASE_URL` and `SUPABASE_KEY` Streamlit secrets as described [here](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management).

> [!NOTE]  
> For local development outside Streamlit, you can also set these as your environment variables (recommended), or pass these to the `url` and `key` args of `st.connection()`.

## :magic_wand: Usage

1. Import
  ```python
  from st_supabase_connection import SupabaseConnection, execute_query
  ```
2. Initialize
  ```python
  st_supabase_client = st.connection(
      name="YOUR_CONNECTION_NAME",
      type=SupabaseConnection,
      ttl=None,
      url="YOUR_SUPABASE_URL", # not needed if provided as a streamlit secret
      key="YOUR_SUPABASE_KEY", # not needed if provided as a streamlit secret
  )
  ```
3. Use in your app to query tables and files, and add authentication. Happy Streamlit-ing! :balloon:

## :ok_hand: Supported methods
<details close>
<summary> Storage </summary>
<ul>
    <li> <code>delete_bucket()</code> </li>
    <li> <code>empty_bucket()</code> </li>
    <li> <code>get_bucket()</code> </li>
    <li> <code>list_buckets()</code> </li>
    <li> <code>create_bucket()</code> </li>
    <li> <code>upload()</code> </li>
    <li> <code>download()</code> </li>
    <li> <code>update_bucket()</code> </li>
    <li> <code>move()</code> </li>
    <li> <code>list_objects()</code> </li>
    <li> <code>create_signed_urls()</code> </li>
    <li> <code>get_public_url()</code> </li>
    <li> <code>create_signed_upload_url()</code> </li>
    <li> <code>upload_to_signed_url()</code> </li>
</ul> 

</details>

<details close>
<summary> Database </summary>
<ul>
    <li> <code>execute_query()</code> - Executes the passed query with caching enabled. </li>
    <li> All methods supported by <a href="https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html">postgrest-py</a>.
</details>

<details>
<summary> Auth </summary>
<ul>
    All methods supported by <a href="https://supabase.com/docs/reference/python/auth-signup">Supabase's Python API </a>.
</details>

## :books: Examples
### :package: Storage operations

#### List existing buckets
```python
>>> st_supabase_client.list_buckets(ttl=None)
[
    SyncBucket(
        id="bucket1",
        name="bucket1",
        owner="",
        public=False,
        created_at=datetime.datetime(2023, 7, 31, 19, 56, 21, 518438, tzinfo=tzutc()),
        updated_at=datetime.datetime(2023, 7, 31, 19, 56, 21, 518438, tzinfo=tzutc()),
        file_size_limit=None,
        allowed_mime_types=None,
    ),
    SyncBucket(
        id="bucket2",
        name="bucket2",
        owner="",
        public=True,
        created_at=datetime.datetime(2023, 7, 31, 19, 56, 28, 203536, tzinfo=tzutc()),
        updated_at=datetime.datetime(2023, 7, 31, 19, 56, 28, 203536, tzinfo=tzutc()),
        file_size_limit=100,
        allowed_mime_types=["image/jpg", "image/png"],
    ),
]
```
#### Create a bucket
```python
>>> st_supabase_client.create_bucket("new_bucket")
{'name': 'new_bucket'}
```

#### Get bucket details
```python
>>> st_supabase_client.get_bucket("new_bucket")
SyncBucket(id='new_bucket', name='new_bucket', owner='', public=True, created_at=datetime.datetime(2023, 8, 2, 19, 41, 44, 810000, tzinfo=tzutc()), updated_at=datetime.datetime(2023, 8, 2, 19, 41, 44, 810000, tzinfo=tzutc()), file_size_limit=None, allowed_mime_types=None)
```
#### Update a bucket
```python
>>> st_supabase_client.update_bucket(
      "new_bucket",
      file_size_limit=100,
      allowed_mime_types=["image/jpg", "image/png"],
      public=True,
    )
{'message': 'Successfully updated'}
```

#### Move files in a bucket
```python
>>> st_supabase_client.move("new_bucket", "test.png", "folder1/new_test.png")
{'message': 'Successfully moved'}
```

#### List objects in a bucket
```python
>>> st_supabase_client.list_objects("new_bucket", path="folder1", ttl=0)
[
    {
        "name": "new_test.png",
        "id": "e506920e-2834-440e-85f1-1d5476927582",
        "updated_at": "2023-08-02T19:53:22.53986+00:00",
        "created_at": "2023-08-02T19:52:20.404391+00:00",
        "last_accessed_at": "2023-08-02T19:53:21.833+00:00",
        "metadata": {
            "eTag": '"814a0034f5549e957ee61360d87457e5"',
            "size": 473831,
            "mimetype": "image/png",
            "cacheControl": "max-age=3600",
            "lastModified": "2023-08-02T19:53:23.000Z",
            "contentLength": 473831,
            "httpStatusCode": 200,
        },
    }
]
```

#### Empty a bucket
```python
>>> st_supabase_client.empty_bucket("new_bucket")
{'message': 'Successfully emptied'}
```
#### Delete a bucket
```python
>>> st_supabase_client.delete_bucket("new_bucket")
{'message': 'Successfully deleted'}
```
### :file_cabinet: Database operations
#### Simple query 
```python
>>> execute_query(st_supabase_client.table("countries").select("*"), ttl=0)
APIResponse(
    data=[
        {"id": 1, "name": "Afghanistan"},
        {"id": 2, "name": "Albania"},
        {"id": 3, "name": "Algeria"},
    ],
    count=None,
)
```
#### Query with join
```python
>>> execute_query(
        st_supabase_client.table("users").select("name, teams(name)", count="exact"), 
        ttl="1h",
    )
    
APIResponse(
    data=[
        {"name": "Kiran", "teams": [{"name": "Green"}, {"name": "Blue"}]},
        {"name": "Evan", "teams": [{"name": "Blue"}]},
    ],
    count=2,
)
```
#### Filter through foreign tables
```python
>>> execute_query(
        st_supabase_client.table("cities").select("name, countries(*)", count="exact").eq("countries.name", "Curaçao"),
        ttl=None,
    )

APIResponse(
    data=[
        {
            "name": "Kralendijk",
            "countries": {
                "id": 2,
                "name": "Curaçao",
                "iso2": "CW",
                "iso3": "CUW",
                "local_name": None,
                "continent": None,
            },
        },
        {"name": "Willemstad", "countries": None},
    ],
    count=2,
)
```

#### Insert rows
```python
>>> execute_query(
        st_supabase_client.table("countries").insert(
            [{"name": "Wakanda", "iso2": "WK"}, {"name": "Wadiya", "iso2": "WD"}], count="None"
        ),
        ttl=0,
    )
    
APIResponse(
    data=[
        {
            "id": 250,
            "name": "Wakanda",
            "iso2": "WK",
            "iso3": None,
            "local_name": None,
            "continent": None,
        },
        {
            "id": 251,
            "name": "Wadiya",
            "iso2": "WD",
            "iso3": None,
            "local_name": None,
            "continent": None,
        },
    ],
    count=None,
)
```

###  :lock: Auth operations

> [!NOTE]  
> If the call is valid, all Supabase Auth methods return the same response structure:
> ```json
> {
>   "user": {
>     "id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>     "app_metadata": {
>       "provider": "email",
>       "providers": [
>         "email"
>       ]
>     },
>     "user_metadata": {
>       "attribution": "I made it :)",
>       "fname": "Siddhant"
>     },
>     "aud": "authenticated",
>     "confirmation_sent_at": null,
>     "recovery_sent_at": null,
>     "email_change_sent_at": null,
>     "new_email": null,
>     "invited_at": null,
>     "action_link": null,
>     "email": "test.user@abc.com",
>     "phone": "",
>     "created_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 365359, tzinfo=datetime.timezone.utc)",
>     "confirmed_at": null,
>     "email_confirmed_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 373966, tzinfo=datetime.timezone.utc)",
>     "phone_confirmed_at": null,
>     "last_sign_in_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 377070, tzinfo=datetime.timezone.utc)",
>     "role": "authenticated",
>     "updated_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 381584, tzinfo=datetime.timezone.utc)",
>     "identities": [
>       {
>         "id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>         "user_id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>         "identity_data": {
>           "email": "siddhant.sadangi@gmail.com",
>           "sub": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544"
>         },
>         "provider": "email",
>         "created_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370040, tzinfo=datetime.timezone.utc)",
>         "last_sign_in_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370002, tzinfo=datetime.timezone.utc)",
>         "updated_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370040, tzinfo=datetime.timezone.utc)"
>       }
>     ],
>     "factors": null
>   },
>   "session": {
>     "provider_token": null,
>     "provider_refresh_token": null,
>     "access_token": "***",
>     "refresh_token": "***",
>     "expires_in": 3600,
>     "expires_at": 1696800390,
>     "token_type": "bearer",
>     "user": {
>       "id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>       "app_metadata": {
>         "provider": "email",
>         "providers": [
>           "email"
>         ]
>       },
>       "user_metadata": {
>         "attribution": "I made it :)",
>         "fname": "Siddhant"
>       },
>       "aud": "authenticated",
>       "confirmation_sent_at": null,
>       "recovery_sent_at": null,
>       "email_change_sent_at": null,
>       "new_email": null,
>       "invited_at": null,
>       "action_link": null,
>       "email": "test.user@abc.com",
>       "phone": "",
>       "created_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 365359, tzinfo=datetime.timezone.utc)",
>       "confirmed_at": null,
>       "email_confirmed_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 373966, tzinfo=datetime.timezone.utc)",
>       "phone_confirmed_at": null,
>       "last_sign_in_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 377070, tzinfo=datetime.timezone.utc)",
>       "role": "authenticated",
>       "updated_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 381584, tzinfo=datetime.timezone.utc)",
>       "identities": [
>         {
>           "id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>           "user_id": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544",
>           "identity_data": {
>             "email": "siddhant.sadangi@gmail.com",
>             "sub": "e1f550fd-9cd1-44e4-bbe4-c04e91cf5544"
>           },
>           "provider": "email",
>           "created_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370040, tzinfo=datetime.timezone.utc)",
>           "last_sign_in_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370002, tzinfo=datetime.timezone.utc)",
>           "updated_at": "datetime.datetime(2023, 10, 8, 20, 26, 30, 370040, tzinfo=datetime.timezone.utc)"
>         }
>       ],
>       "factors": null
>     }
>   }
> }
> ```
> </details>

#### Create new user
```python
>>> st_supabase_client.auth.sign_up(dict(email='test.user@abc.com', password='***', options=dict(data=dict(fname='Siddhant',attribution='I made it :)'))))
```

#### Sign in with password
```python
>>> st_supabase_client.auth.sign_in_with_password(dict(email='test.user@abc.com', password='***'))
```

#### Retrieve session
```python
>>> st_supabase.auth.get_session()
```

#### Retrieve user
```python
>>> st_supabase.auth.get_user()
```

#### Sign out
```python
>>> st_supabase.auth.sign_out()
```

> [!NOTE]  
> Check the [Supabase Python API reference](https://supabase.com/docs/reference/python/select) for more examples.

## :star: Explore all options in a demo app
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://st-supabase-connection.streamlit.app/)

## :bow: Acknowledgements
This connector builds upon the awesome work done by the open-source community in general and the [Supabase Community](https://github.com/supabase-community) in particular. I cannot be more thankful to all the authors whose work I have used either directly or indirectly.

## :hugs: Want to support my work?
<p align="center">
    <a href="https://www.buymeacoffee.com/siddhantsadangi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
    </a>
</p>
