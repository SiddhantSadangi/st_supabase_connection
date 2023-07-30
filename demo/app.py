from typing import Any, Dict, List, Tuple, Union

import streamlit as st

import st_supabase_connection
from st_supabase_connection import SupabaseConnection

VERSION = st_supabase_connection.__version__

st.set_page_config(
    page_title="Streamlit SupabaseConnection Demo app",
    page_icon="🔌",
    menu_items={
        "About": f"🔌 Streamlit Supabase Connection v{VERSION}  "
        f"\nContact: [Siddhant Sadangi](mailto:siddhant.sadangi@gmail.com)",
        "Report a Bug": "https://github.com/SiddhantSadangi/st_supabase_connection/issues/new",
        "Get help": None,
    },
)

# ---------- SESSION STATE ----------
upsert = None

if "client" not in st.session_state:
    st.session_state["client"] = None

if "project" not in st.session_state:
    st.session_state["project"] = "demo"

if "initialized" not in st.session_state:
    st.session_state["initialized"] = False

# ---------- SIDEBAR ----------
with open("demo/sidebar.html", "r", encoding="UTF-8") as sidebar_file:
    sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

with st.sidebar:
    st.info(
        """
        API Reference
        -------------
        - Database operations: [postgrest-py API reference](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html)
        - Storage operations: [Supabase Python client API reference](https://supabase.com/docs/reference/python/storage-createbucket)
        """,
    )
    st.components.v1.html(sidebar_html, height=600)

# ---------- MAIN PAGE ----------
st.header("🔌Streamlit SupabaseConnection Demo")

st.write("📖 Interactive demo for the `st_supabase_connection` Streamlit connection for Supabase.")

st.subheader("🏗️ Initialize Connection")

project = st.radio(
    label="Select Supabase project (demo project recommended for Supabase beginners)",
    options=[
        "Demo project",
        "My own project",
    ],
    horizontal=True,
)

if project == "Demo project":
    st.session_state["project"] = "demo"
    st.warning(
        "DML operations (INSERT, UPSERT, UPDATE, DELETE) not allowed",
        icon="⚠️",
    )
    if st.button(
        "Initialize client ⚡",
        type="primary",
        use_container_width=True,
    ):
        try:
            st.session_state["client"] = st.experimental_connection(
                name="supabase_connection",
                type=SupabaseConnection,
            )
            st.session_state["initialized"] = True
        except Exception as e:
            st.error(
                f"""Client initialization failed
                {e}""",
                icon="❌",
            )
            st.session_state["initialized"] = False

elif project == "My own project":
    st.session_state["project"] = "custom"
    with st.expander(
        label="Supabase credentials",
        expanded=not st.session_state["initialized"],
    ):
        with st.form(key="credentials"):
            url = st.text_input("Enter Supabase URL", type="password")
            key = st.text_input("Enter Supabase key", type="password")

            if st.form_submit_button(
                "Initialize client ⚡",
                type="primary",
                use_container_width=True,
            ):
                try:
                    st.session_state["client"] = st.experimental_connection(
                        name="supabase_connection",
                        type=SupabaseConnection,
                        url=url,
                        key=key,
                    )
                    st.session_state["initialized"] = True
                except Exception as e:
                    st.error(
                        f"""Client initialization failed
                        {e}""",
                        icon="❌",
                    )
                    st.session_state["initialized"] = False

st.write("A connection will be initialized as:")
st.code(
    """
    supabase = st.experimental_connection(
        name="supabase_connection",
        type=SupabaseConnection,
        url=url, # Not required if provided as a Streamlit secret
        key=key, # Not required if provided as a Streamlit secret
    )
    """,
    language="python",
)

if st.session_state["initialized"]:
    st.success("Client initialized!", icon="✅")

    st.subheader("🗄️ Run Database Queries")
    with st.expander(label="🗄️ Database Section", expanded=True):
        # if st.session_state["project"] == "custom":
        st.warning(
            "You are using your own project. Be careful while running DML queries!",
            icon="ℹ️",
        )
        table = st.text_input(
            "Enter the table name",
            value="countries",
            placeholder="countries",
        )

        lcol, mcol, rcol = st.columns(3)
        request_builder = lcol.selectbox(
            "Select the query type",
            options=["select", "insert", "upsert", "update", "delete"],
        )
        count_method = mcol.selectbox(
            "Enter the count method",
            options=[None, "exact", "planned", "estimated"],
            help=f"""
            Count algorithm to use to count {request_builder}ed rows.  
            `None`: Does not return a count.  
            `"exact"`: Exact but slow count algorithm. Performs a `COUNT(*)` under the hood.  
            `"planned"`: Approximated but fast count algorithm. Uses the Postgres statistics under the hood.  
            `"estimated"`: Uses exact count for low numbers and planned count for high numbers.  
            """,
        )
        rcol_placeholder = rcol.empty()

        if request_builder == "insert":
            request_builder_query_label = "Enter the rows to insert as json (for single row) or array of jsons (for multiple rows)"
            placeholder = (
                value
            ) = """[{"name":"Wakanda","iso2":"WK"},{"name":"Wadiya","iso2":"WD"}]"""
            upsert = rcol_placeholder.checkbox(
                label="Upsert",
                help="Whether the query should be an upsert",
            )
        elif request_builder == "select":
            request_builder_query_label = "Enter the columns to fetch as comma-separated strings"
            placeholder = value = "*"
        elif request_builder == "delete":
            request_builder_query_label = "Delete query"
            placeholder = value = "Delete does not take a request builder query"
        elif request_builder == "upsert":
            request_builder_query_label = "Enter the rows to upsert as json (for single row) or array of jsons (for multiple rows)"
            placeholder = value = """{"name":"Wakanda","iso2":"WK", "continent":"Africa"}"""
            ignore_duplicates = rcol_placeholder.checkbox(
                label="Ignore duplicates",
                help="Whether duplicate rows should be ignored",
            )
        elif request_builder == "update":
            request_builder_query_label = "Enter the rows to update as json (for single row) or array of jsons (for multiple rows)"
            placeholder = value = """{"iso3":"N/A","continent":"N/A"}"""
            pass

        request_builder_query = st.text_input(
            label=request_builder_query_label,
            placeholder=placeholder,
            value=value,
            help="[RequestBuilder API reference](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html#postgrest.AsyncRequestBuilder)",
            disabled=True if request_builder == "delete" else False,
        )

        if request_builder == "upsert" and not ignore_duplicates:
            on_conflict = st.text_input(
                label="Enter the columns to be considered UNIQUE in case of conflicts as comma-separated values",
                placeholder="id",
                value="id",
                help="Specified columns to be made to work with UNIQUE constraint.",
            )

        request_builder_query = (
            '"' + request_builder_query + '"'
            if request_builder == "select"
            else request_builder_query
        )
        request_builder_query = (
            f'count="{count_method}"'
            if request_builder == "delete"
            else f'{request_builder_query}, count="{count_method}"'
        )
        if upsert:
            request_builder_query = f'{request_builder_query}, upsert="{upsert}"'

        operators = st.text_input(
            label="Chain any operators and filters you want 🔗",
            value=""".eq("continent","Asia").order("name",desc=True).limit(5)""",
            placeholder=""".eq("continent","Asia").order("name",desc=True).limit(5)""",
            help="List of all available [operators](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html#postgrest.AsyncSelectRequestBuilder) and [filters](https://postgrest-py.readthedocs.io/en/latest/api/filters.html#postgrest.AsyncFilterRequestBuilder)",
        )

        constructed_query = f"""supabase.table("{table}").{request_builder}({request_builder_query}){operators}.execute()"""
        st.write("Constructed query:")
        st.code(constructed_query)

        lcol, rcol = st.columns([2, 1])
        view = lcol.radio(
            label="View output as",
            options=["Dataframe", "Dict (recommended for joins)"],
            horizontal=True,
        )

        if rcol.button(
            "Run query 🏃",
            use_container_width=True,
            type="primary",
            disabled=True
            if st.session_state["project"] == "demo"
            and request_builder in ["insert", "upsert", "update", "delete"]
            else False,
            help=f"{request_builder.upper()} not allowed in demo project"
            if st.session_state["project"] == "demo"
            and request_builder in ["insert", "upsert", "update", "delete"]
            else None,
        ):
            supabase = st.session_state["client"]
            try:

                @st.cache_data
                def run_query(query: str) -> Tuple[List[Dict[str, Any]], Union[int, None]]:
                    return eval(query)

                data, count = run_query(constructed_query)

                if count_method:
                    st.write(f"{count[-1]} rows {request_builder}ed")
                if view == "Dataframe":
                    st.dataframe(data[-1], use_container_width=True)
                else:
                    st.write(data[-1])
            except ValueError:
                if count_method == "planned":
                    st.error(
                        "Operation too small for `planned` count method. Please change count method."
                    )
            except Exception as e:
                if e.__class__.__name__ == "ConnectError":
                    st.error(
                        "Could not connect. Please check the Supabase URL provided",
                        icon="❌",
                    )
                else:
                    st.error(
                        e,
                        icon="❌",
                    )

    st.subheader("📦 Run Storage Queries")
    with st.expander("📦 Storage section"):
        # TODO: Add storage queries
        pass
