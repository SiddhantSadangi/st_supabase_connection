import contextlib

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

# ---------- INIT SESSION ----------
upsert = bucket_id = None

STORAGE_OPERATIONS = [
    "Create a bucket",
    "Update bucket",
    "Delete a bucket",
    "Empty a bucket",
    "Upload a file",
    "Move an existing file",
    "Delete files in a bucket",
    "Retrieve a bucket",
    "List all buckets",
    "Download a file",
    "List all files in a bucket",
    "Create a signed URL",
    "Retrieve public URL",
]

RESTRICTED_STORAGE_OPERATORS = [
    "create_bucket",
    "update_bucket",
    "delete_bucket",
    "empty_bucket",
    "upload",
    "move",
    "remove",
]

STORAGE_OPERATORS = RESTRICTED_STORAGE_OPERATORS + [
    "get_bucket",
    "list_buckets",
    "download",
    "list",
    "create_signed_url",
    "get_public_url",
]

if "client" not in st.session_state:
    st.session_state["client"] = None
else:
    st_supabase = st.session_state["client"]

if "project" not in st.session_state:
    st.session_state["project"] = "demo"

if "initialized" not in st.session_state:
    st.session_state["initialized"] = False

# ---------- SIDEBAR ----------
with open("demo/sidebar.html", "r", encoding="UTF-8") as sidebar_file:
    sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

with st.sidebar:
    st.components.v1.html(sidebar_html, height=600)

# ---------- MAIN PAGE ----------
st.header("🔌Streamlit SupabaseConnection Demo")

st.write(
    "📖 Demo for the `st_supabase_connection` Streamlit connection for Supabase Storage and Database."
)

st.subheader("🏗️ Initialize Connection")

project = st.radio(
    label="Select Supabase project",
    options=[
        "Demo project",
        "My own project",
    ],
    horizontal=True,
)

if project == "Demo project":
    st.session_state["project"] = "demo"
    st.warning(
        "Limited data and operations",
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
            url = st.text_input("Enter Supabase URL")
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
                    st.success("Client initialized!", icon="✅")
                    st.session_state["initialized"] = True
                except Exception as e:
                    st.error(
                        f"""Client initialization failed
                        {e}""",
                        icon="❌",
                    )
                    st.session_state["initialized"] = False

st.write("A connection is initialized as")

if st.session_state["project"] == "demo":
    st.code(
        """
        st_supabase = st.experimental_connection(
            name="supabase_connection", type=SupabaseConnection
            )
        """,
        language="python",
    )
elif st.session_state["project"] == "custom":
    st.code(
        """
        st_supabase = st.experimental_connection(
            name="supabase_connection", type=SupabaseConnection, url=url, key=key
            )
        """,
        language="python",
    )

if st.session_state["initialized"]:
    lcol, rcol = st.columns(2)
    storage = lcol.checkbox("Explore storage 🔍📦")
    if database := rcol.checkbox("Explore database 🔍🗄️"):
        st.subheader("🗄️ Run Database Queries")

        if st.session_state["project"] == "custom":
            st.warning(
                "You are using your own project. Be careful while running DML queries!",
                icon="ℹ️",
            )
        elif st.session_state["project"] == "demo":
            st.write("Demo database schema")
            st.markdown(
                """
                | Table | Columns | Size
                |---|---|---
                |`cities`| `id`, `country_id`, `name` | 2
                |`countries`| `id`, `name`, `iso2`, `iso3`, `local_name`, `continent` | 249
                |`messages`| `sender_id`, `receiver_id`, `content` | 2
                |`teams`| `id`, `name` | 2
                |`users`| `id`, `name` | 2
                |`users_teams`| `user_id`, `team_id` | 3
                """
            )
        if st.session_state["project"] == "demo":
            table = st.selectbox(
                "Select the table name",
                options=[
                    "cities",
                    "countries",
                    "messages",
                    "teams",
                    "users",
                    "users_teams",
                ],
                index=1,
            )
        elif st.session_state["project"] == "custom":
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
        request_builder_query = st.text_input(
            label=request_builder_query_label,
            placeholder=placeholder,
            value=value,
            help="[RequestBuilder API reference](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html#postgrest.AsyncRequestBuilder)",
            disabled=request_builder == "delete",
        )

        if request_builder == "upsert" and not ignore_duplicates:
            on_conflict = st.text_input(
                label="Enter the columns to be considered UNIQUE in case of conflicts as comma-separated values",
                placeholder="id",
                value="id",
                help="Specified columns to be made to work with UNIQUE constraint.",
            )

        request_builder_query = (
            f'"{request_builder_query}"' if request_builder == "select" else request_builder_query
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

        operators = operators.replace(".__init__()", "").replace(".execute()", "")

        constructed_db_query = f"""st_supabase.table("{table}").{request_builder}({request_builder_query}){operators}.execute()"""
        st.write("Constructed query")
        st.code(constructed_db_query)

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
            disabled=st.session_state["project"] == "demo"
            and request_builder in ["insert", "upsert", "update", "delete"],
            help=f"{request_builder.upper()} not allowed in demo project"
            if st.session_state["project"] == "demo"
            and request_builder in ["insert", "upsert", "update", "delete"]
            else None,
            key="run_db_query",
        ):
            try:
                data, count = eval(constructed_db_query)

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

    if storage:
        st.subheader("📦 Run Storage Queries")

        if st.session_state["project"] == "custom":
            st.warning(
                "You are using your own project. Be careful while running delete, empty, and move requests!",
                icon="ℹ️",
            )
        elif st.session_state["project"] == "demo":
            st.write("Demo storage schema")
            st.markdown(
                """
                bucket | object
                |---|---
                `bucket1`| `/awesome_zoom_background.jpg`
                `bucket2`| `/folder1/folder2/lenna.png`
                """
            )

        lcol, rcol = st.columns(2)
        selected_operation = lcol.selectbox(
            label="Select operation",
            options=STORAGE_OPERATIONS,
            help="""
            * [Supabase Storage API reference](https://supabase.com/docs/reference/python/storage-createbucket)
            * [storage-py API reference](https://supabase-community.github.io/storage-py/api/index.html)""",
        )

        operation_query_dict = dict(zip(STORAGE_OPERATIONS, STORAGE_OPERATORS))

        operation = operation_query_dict.get(selected_operation)

        bucket_id = rcol.text_input(
            "Enter the bucket id",
            placeholder="my_bucket" if operation != "update_bucket" else "",
            disabled=operation == "list_buckets",
            help="The unique identifier for the bucket",
        )

        if operation in ["delete_bucket", "empty_bucket", "get_bucket"]:
            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}")"""

        elif operation == "create_bucket":
            col1, col2, col3, col4 = st.columns(4)

            name = col1.text_input(
                "Bucket name",
                placeholder=bucket_id,
                help="The name of the bucket. Defaults to bucket id",
            )

            file_size_limit = col2.number_input(
                "Bucket file size limit",
                min_value=0,
                value=0,
                help="Size limit of the files that can be uploaded to the bucket (in bytes). `0` means no limit.",
            )
            file_size_limit = None if file_size_limit == 0 else file_size_limit

            allowed_mime_types = col3.text_area(
                "Allowed MIME types",
                placeholder="['text/plain','image/jpg']",
                help="The MIME types that can be uploaded to the bucket. Enter as a list. Defaults to `None` to allow all file types.",
            )
            allowed_mime_types = None if len(allowed_mime_types) == 0 else allowed_mime_types

            public = col4.checkbox(
                "Public",
                help="Whether the bucket should be publicly accessible?",
                value=False,
            )

            constructed_storage_query = f"""st_supabase.create_bucket('{bucket_id}',{name=},{file_size_limit=},allowed_mime_types={allowed_mime_types},{public=})"""

        elif operation == "update_bucket":
            if bucket_id:
                current_props = st_supabase.get_bucket(bucket_id)
                st.info("Current properties fetched. Update values to update properties.")
                col1, col2, col3 = st.columns(3)

                file_size_limit = col1.number_input(
                    "New file size limit",
                    min_value=0,
                    value=current_props.file_size_limit or 0,
                    help="Set as `0` to have no limit",
                )
                file_size_limit = None if file_size_limit == 0 else file_size_limit

                allowed_mime_types = col2.text_area(
                    "New allowed MIME types",
                    value=""
                    if current_props.allowed_mime_types
                    else current_props.allowed_mime_types,
                    help="Enter as a list. Set `None` to allow all MIME types.",
                )

                public = col3.checkbox(
                    "Public",
                    help="Whether the bucket should be publicly accessible?",
                    value=current_props.public,
                )

                constructed_storage_query = f"""st_supabase.{operation}('{bucket_id}',{file_size_limit=},allowed_mime_types={allowed_mime_types},{public=})"""

        elif operation == "upload":
            uploaded_file = st.file_uploader("Choose a file")
            destination_path = st.text_input(
                "Enter destination path in the bucket",
                placeholder="/parentFolder/subFolder/file.txt",
            )

            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}", file={uploaded_file}, destination_path="{destination_path}")"""

        elif operation == "list_buckets":
            constructed_storage_query = f"""st_supabase.{operation}()"""

        elif operation == "download":
            source_path = st.text_input(
                "Enter source path in the bucket",
                placeholder="/folder/subFolder/file.txt",
            )

            constructed_storage_query = (
                f"""st_supabase.{operation}("{bucket_id}", {source_path=})"""
            )

        # TODO: move, remove, list, create_signed_url, get_public_url
        if operation == "download":
            st.write("Constructed query")
            st.code(
                f"file_name, mime, data = {constructed_storage_query}",
                language="python",
            )
        elif not (operation == "update_bucket" and not bucket_id):
            st.write("Constructed query")
            st.code(constructed_storage_query, language="python")

        if operation == "list_buckets":
            disabled = False
        elif (
            st.session_state["project"] == "demo" and operation in RESTRICTED_STORAGE_OPERATORS
        ) or not bucket_id:
            disabled = True
        else:
            disabled = False

        if st.button(
            "Run query 🏃",
            use_container_width=True,
            type="primary",
            disabled=disabled,
            help=f"'{selected_operation.capitalize()}' not allowed in demo project"
            if st.session_state["project"] == "demo" and operation in RESTRICTED_STORAGE_OPERATORS
            else None,
            key="run_storage_query",
        ):
            try:
                if operation == "upload":
                    res = st_supabase.upload(bucket_id, uploaded_file, destination_path)
                elif operation == "download":
                    file_name, mime, data = eval(constructed_storage_query)
                    st.success("Download ready 🎉🎉🎉")
                    st.download_button(
                        "Download file ⏬",
                        data=data,
                        file_name=file_name,
                        mime=mime,
                        use_container_width=True,
                    )
                else:
                    res = eval(constructed_storage_query)
                with contextlib.suppress(TypeError, NameError):
                    if operation == "create_bucket" and res["name"] == bucket_id:
                        st.success("Bucket created", icon="✅")
                    elif operation == "update_bucket" and res["message"] == "Successfully updated":
                        st.success("Bucket updated", icon="✅")
                    elif operation == "delete_bucket" and res["message"] == "Successfully deleted":
                        st.success("Bucket deleted", icon="✅")
                    elif operation == "empty_bucket" and res["message"] == "Successfully emptied":
                        st.success("Bucket emptied", icon="✅")
                    elif operation == "upload" and res["Key"] == f"{bucket_id}/{destination_path}":
                        st.success(
                            f"__{uploaded_file.name}__ uploaded to __{res['Key']}__",
                            icon="✅",
                        )
                    else:
                        st.write(res)
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
