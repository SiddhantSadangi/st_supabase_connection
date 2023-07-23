import streamlit as st

from st_supabase_connection import SupabaseConnection

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

st.subheader("🧺 Fetch data from Supabase DB")
st.write("🔍 A simple `SELECT * FROM countries`")
st.code(
    """data, count = client.select(table_name="countries", select_query="*", ttl=0)""",
    language="python",
)

data, count = client.select(table_name="countries", select_query="*", ttl=0)

st.dataframe(data, use_container_width=True)

st.write("**🤏 Select only specified columns**")
st.write("**📝 Task:** Select only the `name` and `capital` columns from `countries`")
select_query = st.text_input(
    "Enter the `select_query` string",
    help="Enter column names as comma-separated values",
)
st.write("Constructed query")
st.code(
    f"""
    data, count = client.select(table_name="countries",
                                select_query="{select_query}",
                                ttl=0)
    """,
    language="python",
)

if select_query:
    data, count = client.select(table_name="countries", select_query=select_query, ttl=0)
    st.dataframe(data, use_container_width=True)

with st.expander(label="✅ Answer", expanded=False):
    st.code("name,capital")

# TODO: Handle joins
# st.write("**🤏 Query foreign tables**")
# st.write("We have a `cities` table containing `id`, `country_id`, and `name` columns. `cities.country_id` references `country.id` as a foreign key")
# st.write("**📝 Task:** Select `name` from the `countries` and `cities` tables")
# select_query = st.text_input(
#     "Enter the `select_query` string",
#     help="Foreign table columns can be queries using the format `table_name(column_name)`",)
# st.write("Constructed query")
# st.code(
#     f"""
#     data, count = client.select(table_name="countries",
#                                 select_query="{select_query}",
#                                 ttl=0)
#     """,
#     language="python"
# )

# if select_query:
#     data, count = client.select(table_name="countries", select_query=select_query, ttl=0)
#     st.dataframe(data, use_container_width=True)

# with st.expander(label="✅ Answer", expanded=False):
#     st.code("name,cities(name)")

if count:
    st.text(f"Query returned {count[-1]} rows")

st.info(
    "📖 Read the [Supabase Python API reference](https://supabase.com/docs/reference/python/select) for all available options."
)


client.insert(table_name="countries", insert_rows={"name": "India"})

data, count = client.select(table_name="countries", select_query="*")

if count:
    st.text(f"Query returned {count[-1]} rows")
st.dataframe(data, use_container_width=True)
