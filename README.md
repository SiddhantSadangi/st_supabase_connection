# :handshake: st-supabase-connection
[![Downloads](https://static.pepy.tech/personalized-badge/st-supabase-connection?period=total&units=international_system&left_color=black&right_color=brightgreen&left_text=Downloads)](https://pepy.tech/project/st-supabase-connection)

A Streamlit connection component to connect Streamlit to Supabase.

## :computer: Demo app
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://st-supabase-connection.streamlit.app/)

## :construction: Setup

1. Install `st-supabase-connection`
```sh
pip install st-supabase-connection
```
2. Set the `SUPABASE_URL` and `SUPABASE_KEY` Streamlit secrets as described [here](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management)

> [!NOTE]  
> For local development outside Streamlit, you can also set these as your environment variables (recommended), or pass these to the `url` and `key` args of `st.experimental_connection()` (not recommended).

## :pen: Usage

1. Import
  ```python
  import streamlit as st
  from st_supabase_connection import SupabaseConnection
  ```
2. Initialize
  ```python
  supabase = st.experimental_connection(
      name="YOUR_CONNECTION_NAME",
      type=SupabaseConnection,
      url="YOUR_SUPABASE_URL", # not needed if provided as a streamlit secret
      key="YOUR_SUPABASE_KEY", # not needed if provided as a streamlit secret
  )
  ```
  This returns the same Supabase client as Supabase's `create_client()` method.

3. Use the client as you as you would with the Supabase Python API
> [!WARNING]  
> Currently only the Supabase Database and Storage methods are supported.

```python
# Database operations
# -------------------

# Simple query
>>> supabase.table('countries').select("*").execute()
APIResponse(data=[{'id': 1, 'name': 'Afghanistan'},
                  {'id': 2, 'name': 'Albania'},
                  {'id': 3, 'name': 'Algeria'}],
            count=None)

# Query with join
>>> supabase.table('users').select('name, teams(name)').execute()
APIResponse(data=[
                  {'name': 'Kiran', 'teams': [{'name': 'Green'}, {'name': 'Blue'}]},
                  {'name': 'Evan', 'teams': [{'name': 'Blue'}]}
                 ],
            count=None)

# Filter through foreign tables
>>> supabase.table('cities').select('name, countries(*)').eq('countries.name', 'Estonia').execute()
APIResponse(data=[{'name': 'Bali', 'countries': None},
                  {'name': 'Munich', 'countries': None}],
            count=None)

# Storage operations
# ------------------

# Create a bucket
>>> supabase.storage.create_bucket("new_bucket")
{'name': 'new_bucket'}

# Download a file
>>> with open("file.txt", "wb+") as f:
>>>   res = supabase.storage.from_("new_bucket").download("file.txt")
>>>   f.write(res)

# Delete a bucket
>>> supabase.storage.delete_bucket("new_bucket")
```
> [!NOTE]  
> All supported **database** operations and syntax are mentioned in the [`postgrest-py` API reference](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html).  
> All supported **storage** operations and syntax are mentioned in the [Supabase Python client API reference](https://supabase.com/docs/reference/python/storage-createbucket).

## :star: Explore in Streamlit
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://st-supabase-connection.streamlit.app/)

## 🤗 Want to support my work?
<p align="center">
    <a href="https://www.buymeacoffee.com/siddhantsadangi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
    </a>
</p>
