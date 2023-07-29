import streamlit as st

import st_supabase_connection
from st_supabase_connection import SupabaseConnection

VERSION = st_supabase_connection.__version__

# TODO: Let users use their own keys and data sources. Give option of using default keys if they don't have their own
# TODO: Build your query format if using their keys (enter tablename, select operation, etc). Disable table modifying methods (insert, update, delete) if using mine

# ---------- SIDEBAR ----------
with open("assets/sidebar.html", "r", encoding="UTF-8") as sidebar_file:
    sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

with st.sidebar:
    st.components.v1.html(sidebar_html, height=600)

# ---------- MAIN PAGE ----------
st.header("Streamlit SupabaseConnection")

st.write(
    "📖 Interactive tutorial for the `st_supabase_connection` Streamlit connection for Supabase Database."
)

st.subheader("🏗️ Installation")
st.code("pip install st_supabase_connection", language="bash")

st.subheader("🔌 Initializing connection")
st.code(
    """
import streamlit as st
from st_supabase_connection import SupabaseConnection

client = st.experimental_connection(
    name="demo_supabase_connection",
    type=SupabaseConnection,
)
""",
    language="python",
)

client = st.experimental_connection(
    name="demo_supabase_connection",
    type=SupabaseConnection,
)

st.success("✅ Connection initialized!")

st.subheader("🧺 Fetch data")

st.write("🔍 A simple `SELECT * FROM countries`")
st.code(
    """data, count = client.select(table_name="countries", select_query="*", ttl=0)""",
    language="python",
)

data, count = client.select(table_name="countries", select_query="*", ttl=0)

st.dataframe(data, use_container_width=True)

st.write("**🤏 Select only specified columns**")
st.write("**📝 Task:** Select only the `name` and `capital` columns from `countries`")
select_cols_query = st.text_input(
    "Enter the `select_query` string",
    help="Enter column names as comma-separated values",
    key="select_cols",
)
st.write("Constructed query")
st.code(
    f"""
    data, count = client.select(
        table_name="countries",
        select_query="{select_cols_query}",
        ttl=0,
        )
    """,
    language="python",
)
st.write("Results")
if select_cols_query:
    data, count = client.select(table_name="countries", select_query=select_cols_query, ttl=0)
    st.dataframe(data, use_container_width=True)
else:
    st.dataframe()
with st.expander(label="✅ Answer", expanded=False):
    st.code("name,capital")

st.write("**🤏 Filter tables**")
st.write("**📝 Task:** Select countries in Europe")
select_cols_and_filter_string = st.text_input(
    "Enter the `filter_string`",
    help="`filter_string` takes the format `column_name,value to match`",
    key="select_cols_and_filter",
)
st.write("Constructed query")
st.code(
    f"""
    data, count = client.select(
        table_name="countries",
        select_query="*",
        filter_string="{select_cols_and_filter_string}",
        ttl=0,
        )
    """,
    language="python",
)
st.write("Results")
data, count = client.select(
    table_name="countries",
    select_query="*",
    filter_string=select_cols_and_filter_string,
    ttl=0,
)
st.dataframe(data, use_container_width=True)

with st.expander(label="✅ Answer", expanded=False):
    st.code("continent,Europe")

st.write("**🔢 Get the count of rows returned**")
st.write("**📝 Task:** Get the total number of countries in the database")
count_method = st.selectbox(
    "Select the `count_method`",
    options=[None, "exact", "planned", "estimated"],
    help=""" `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the hood.\n
    `"planned"`: Approximated but fast count algorithm. Uses the Postgres statistics under the hood.\n
    `"estimated"`: Uses exact count for low numbers and planned count for high numbers.""",
    key="count_method",
)
st.write("Constructed query")
st.code(
    f"""
    data, count = client.select(
        table_name="countries",
        select_query="*",
        count_method="{count_method}",
        ttl=0,
        )
    """,
    language="python",
)
data, count = client.select(
    table_name="countries", select_query="*", count_method=count_method, ttl=0
)
st.write(f"Result: {count}")

st.info(
    "📖 Read the [Supabase Python API reference](https://supabase.com/docs/reference/python/select) for all available options."
)

st.subheader("➕ Insert data")
st.code(
    """
    client.insert(
        table_name="countries",
        insert_rows={
            "name": "USA",
            "capital":"Washington DC",
            "continent":"North America"
            }
        )
    """,
    language="python",
)


data, count = client.select(table_name="countries", select_query="*")

if count:
    st.text(f"Query returned {count[-1]} rows")
st.dataframe(data, use_container_width=True)
