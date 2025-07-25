import contextlib

import pandas as pd
import streamlit as st
from st_social_media_links import SocialMediaIcons
from streamlit.components.v1 import html as st_html

from st_supabase_connection import execute_query  # noqa: F401
from st_supabase_connection import (
    SupabaseConnection,
    __version__,
)

VERSION = __version__

st.set_page_config(
    page_title="st_supabase_connection",
    page_icon="🔌",
    menu_items={
        "About": f"🔌 Streamlit Supabase Connection v{VERSION}  "
        f"\nContact: [Siddhant Sadangi](mailto:siddhant.sadangi@gmail.com)",
        "Report a Bug": "https://github.com/SiddhantSadangi/st_supabase_connection/issues/new",
        "Get help": None,
    },
)

# ---------- INIT SESSION ----------
upsert = operators = bucket_id = file_size_limit = allowed_mime_types = source = None
public = False

if "client" not in st.session_state:
    st.session_state["client"] = None
else:
    st_supabase = st.session_state["client"]

if "project" not in st.session_state:
    st.session_state["project"] = "demo"

if "initialized" not in st.session_state:
    st.session_state["initialized"] = False

if "storage_disabled" not in st.session_state:
    st.session_state["storage_disabled"] = True

# ---------- SIDEBAR ----------
with open("demo/sidebar.html", "r", encoding="UTF-8") as sidebar_file:
    sidebar_html = sidebar_file.read().replace("{VERSION}", VERSION)

with st.sidebar:
    with st.expander("**How to use**", expanded=True, icon="💡"):
        st.info(
            """
                1. Select a project and initialize client
                2. Select the relevant operation and options
                3. Run the query to get the results 
                4. Copy the constructed code to use in your own app.
                """
        )

    if st.button(
        "Clear cache to fetch latest data🧹",
        use_container_width=True,
    ):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache cleared")

    st_html(sidebar_html, height=325)

    st.html(
        """
        <div style="text-align:center; font-size:14px; color:lightgrey">
            <hr style="margin-bottom: 6%; margin-top: 0%;">
            Share the ❤️ on social media
        </div>"""
    )

    social_media_links = [
        "https://www.facebook.com/sharer/sharer.php?kid_directed_site=0&sdk=joey&u=https%3A%2F%2Fst-supabase-connection.streamlit.app%2F&display=popup&ref=plugin&src=share_button",
        "https://www.linkedin.com/sharing/share-offsite/?url=https%3A%2F%2Fst-supabase-connection.streamlit.app%2F",
        "https://x.com/intent/tweet?original_referer=http%3A%2F%2Flocalhost%3A8501%2F&ref_src=twsrc%5Etfw%7Ctwcamp%5Ebuttonembed%7Ctwterm%5Eshare%7Ctwgr%5E&text=Check%20out%20this%20Streamlit%20Supabase%20connection%20demo%20app%20%F0%9F%8E%88&url=https%3A%2F%2Fst-supabase-connection.streamlit.app%2F",
    ]

    social_media_icons = SocialMediaIcons(
        social_media_links, colors=["lightgray"] * len(social_media_links)
    )

    social_media_icons.render(sidebar=True)

    st.html(
        """
        <div style="text-align:center; font-size:12px; color:lightgrey">
            <hr style="margin-bottom: 6%; margin-top: 6%;">
            <a rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/">
                <img alt="Creative Commons License" style="border-width:0"
                    src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" />
            </a><br><br>
            This work is licensed under a <b>Creative Commons
                Attribution-NonCommercial-ShareAlike 4.0 International License</b>.<br>
            You can modify and build upon this work non-commercially. All derivatives should be
            credited to Siddhant Sadangi and
            be licenced under the same terms.
        </div>
    """
    )
# ---------- MAIN PAGE ----------
st.header("🔌Supabase Connection for Streamlit", divider="violet")

st.caption(
    "🧑‍🎓 Demo and tutorial for [st_supabase_connection](https://github.com/SiddhantSadangi/st_supabase_connection), an easy-to-use Supabase connector for Streamlit that caches your API calls to make querying fast and cheap."
)

st.subheader("🏗️ Initialize Connection")

with st.expander("**Select project**", expanded=not st.session_state["initialized"]):
    demo_tab, custom_tab = st.tabs(["👶Use demo project", "🫅Use your own project"])

    with demo_tab:
        ttl = st.text_input(
            "Connection cache duration",
            value="",
            placeholder="Optional",
            help="This does not affect results caching. Leave blank to cache indefinitely.",
        )
        ttl = None if ttl == "" else ttl

        if st.button(
            "Initialize client ⚡",
            type="primary",
            use_container_width=True,
        ):
            try:
                st.session_state["client"] = st.connection(
                    name="supabase_connection", type=SupabaseConnection, ttl=ttl
                )
                st.session_state["initialized"] = True
                st.session_state["project"] = "demo"
            except Exception as e:
                st.error(
                    f"""Client initialization failed
                    {e}""",
                    icon="❌",
                )
                st.session_state["initialized"] = False

            st.write("A connection is initialized as")
            st.code(
                f"""
                st_supabase = st.connection(
                    name="supabase_connection", type=SupabaseConnection, {ttl=}
                    )
                """,
                wrap_lines=True,
            )

    with custom_tab:
        with st.form(key="credentials"):
            lcol, rcol = st.columns([2, 1])
            url = lcol.text_input("Enter Supabase URL")
            ttl = rcol.text_input(
                "Connection cache duration",
                value="",
                placeholder="Optional",
                help="This does not affect results caching. Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl
            key = st.text_input("Enter Supabase key", type="password")

            if st.form_submit_button(
                "Initialize client ⚡",
                type="primary",
                use_container_width=True,
            ):
                try:
                    st.session_state["client"] = st.connection(
                        name="supabase_connection",
                        type=SupabaseConnection,
                        ttl=ttl,
                        url=url,
                        key=key,
                    )
                    st.session_state["initialized"] = True
                    st.session_state["project"] = "custom"
                except Exception as e:
                    st.error(
                        f"""Client initialization failed
                        {e}""",
                        icon="❌",
                    )
                    st.session_state["initialized"] = False

                st.write("A connection is initialized as")
                st.code(
                    f"""
                    st_supabase = st.connection(
                        name="supabase_connection", 
                        type=SupabaseConnection, 
                        {ttl=},
                        url=url, 
                        key=key, 
                    )
                    """,
                    wrap_lines=True,
                )

if st.session_state["initialized"]:
    st.success("Client initialized!", icon="✅")

if st.session_state["initialized"]:
    storage, database, auth = st.tabs(
        ["Explore storage 📦", "Explore database 🗄️", "Explore auth 🔐"]
    )

    with storage:
        st.subheader("📦 Run Storage Queries")

        STORAGE_OPERATIONS = [
            "Create a bucket",
            "Update bucket",
            "Delete a bucket",
            "Empty a bucket",
            "Upload a file",
            "Move an existing file",
            "Delete files in a bucket",
            "Create a signed upload URL",
            "Upload to signed URL",
            "Retrieve a bucket",
            "List all buckets",
            "Download a file",
            "List all files in a bucket",
            "Create signed URLs",
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
            "create_signed_upload_url",
            "upload_to_signed_url",
        ]

        STORAGE_OPERATORS = RESTRICTED_STORAGE_OPERATORS + [
            "get_bucket",
            "list_buckets",
            "download",
            "list_objects",
            "create_signed_urls",
            "get_public_url",
        ]

        if st.session_state["project"] == "custom":
            st.warning(
                "You are using your own project. Be careful while running delete, empty, and move requests!",
                icon="ℹ️",
            )
        elif st.session_state["project"] == "demo":
            st.info(
                "You are using the demo project. Some features won't be available.",
                icon="ℹ️",
            )
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
            placeholder="Required" if operation != "list_buckets" else "",
            disabled=operation == "list_buckets",
            help="The unique identifier for the bucket",
        )

        if operation == "get_bucket":
            ttl = st.text_input(
                "Results cache duration",
                value="",
                placeholder="Optional",
                help="Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl
            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}", {ttl=})"""
            st.session_state["storage_disabled"] = bool(not bucket_id)

        elif operation in ["delete_bucket", "empty_bucket"]:
            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}")"""
            st.session_state["storage_disabled"] = bool(not bucket_id)

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
            st.session_state["storage_disabled"] = bool(not bucket_id)

        elif operation == "update_bucket":
            if bucket_id:
                try:
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
                        value=current_props.allowed_mime_types or "",
                        help="Enter as a list. Set `None` to allow all MIME types.",
                    )

                    public = col3.checkbox(
                        "Public",
                        help="Whether the bucket should be publicly accessible?",
                        value=current_props.public,
                    )
                    st.session_state["storage_disabled"] = False
                except Exception as e:
                    if e.__class__.__name__ == "StorageException":
                        st.error(f"Bucket with id **{bucket_id}** not found", icon="❌")
                    else:
                        st.write(e)
                    st.session_state["storage_disabled"] = True

            constructed_storage_query = f"""st_supabase.{operation}('{bucket_id}',{file_size_limit=},allowed_mime_types={allowed_mime_types},{public=})"""

        elif operation == "upload":
            destination_path = None
            lcol, rcol = st.columns([1, 3])
            source = lcol.selectbox(
                label="Source filesystem",
                options=["local", "hosted"],
                help="Filesystem from where the file has to be uploaded",
            )

            if source == "local":
                file = rcol.file_uploader("Choose a file")
                lcol, rcol = st.columns([3, 1])

                destination_path = lcol.text_input(
                    "Destination path in the bucket",
                    value=file.name if file else "",
                )
                overwrite = "true" if rcol.checkbox("Overwrite if exists?") else "false"

                constructed_storage_query = f"""
                st_supabase.{operation}("{bucket_id}", {source=}, file={file}, destination_path="{destination_path}", {overwrite=})
                # `UploadedFile` is the `BytesIO` object returned by `st.file_uploader()`
                """
            else:
                file = rcol.text_input(
                    "Source path",
                    placeholder="path/to/file.txt",
                    help="This is the path of the file on the Streamlit hosted filesystem",
                )
                lcol, rcol = st.columns([3, 1])
                destination_path = lcol.text_input(
                    "Destination path in the bucket",
                    value=file,
                )
                overwrite = "true" if rcol.checkbox("Overwrite if exists?") else "false"
                constructed_storage_query = f"""
                st_supabase.{operation}("{bucket_id}", {source=}, {file=}, destination_path="{destination_path}", {overwrite=})
                """
            st.session_state["storage_disabled"] = bool(not all([bucket_id, file]))
        elif operation == "list_buckets":
            ttl = st.text_input(
                "Results cache duration",
                value="",
                placeholder="Optional",
                help="Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl
            constructed_storage_query = f"""st_supabase.{operation}({ttl=})"""
            st.session_state["storage_disabled"] = False

        elif operation == "download":
            lcol, rcol = st.columns([3, 1])
            source_path = lcol.text_input(
                "Enter source path in the bucket",
                placeholder="/folder/subFolder/file.txt",
            )
            ttl = rcol.text_input(
                "Results cache duration",
                value="",
                placeholder="Optional",
                help="Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl

            constructed_storage_query = (
                f"""st_supabase.{operation}("{bucket_id}", {source_path=}, {ttl=})"""
            )
            st.session_state["storage_disabled"] = bool(not all([bucket_id, source_path]))

        elif operation == "move":
            from_path = st.text_input(
                "Enter source path in the bucket",
                placeholder="/folder/subFolder/file.txt",
            )
            to_path = st.text_input(
                "Enter destination path in the bucket",
                placeholder="/folder/subFolder/file.txt",
                help="Path will be created if it does not exist",
            )
            constructed_storage_query = (
                f"""st_supabase.{operation}("{bucket_id}", {from_path=}, {to_path=})"""
            )

            st.session_state["storage_disabled"] = bool(not all([bucket_id, from_path, to_path]))
        elif operation == "remove":
            paths = st.text_input(
                "Enter the paths of the objects in the bucket to remove",
                placeholder="""["image.png","/folder/subFolder/file.txt"]""",
                help="Enter as a list",
            )
            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}", paths={paths})"""

            st.session_state["storage_disabled"] = bool(not all([bucket_id, paths]))
        elif operation == "list_objects":
            lcol, rcol = st.columns([3, 1])
            path = lcol.text_input(
                "Enter the folder path to list objects from",
                placeholder="/folder/subFolder/",
            )
            ttl = rcol.text_input(
                "Results cache duration",
                value="",
                placeholder="Optional",
                help="Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl

            col1, col2, col3, col4 = st.columns(4)

            limit = col1.number_input(
                "Number of objects to list",
                min_value=1,
                value=100,
            )

            offset = col2.number_input(
                "Offset",
                min_value=0,
                value=0,
            )

            sortby = col3.selectbox(
                "Select the column to sort by",
                options=["name", "updated_at", "created_at", "last_accessed_at"],
                index=0,
            )

            order = col4.radio(
                "Select the sorting order",
                options=["asc", "desc"],
                index=0,
                horizontal=True,
            )

            constructed_storage_query = f"""st_supabase.{operation}("{bucket_id}", {path=}, {limit=}, {offset=}, {sortby=}, {order=}, {ttl=})"""

            st.session_state["storage_disabled"] = not bool(bucket_id)

        elif operation == "get_public_url":
            lcol, rcol = st.columns([3, 1])
            filepath = lcol.text_input(
                "Enter the path to file",
                placeholder="/folder/subFolder/image.jpg",
            )
            ttl = rcol.text_input(
                "Results cache duration",
                value="",
                placeholder="Optional",
                help="Leave blank to cache indefinitely",
            )
            ttl = None if ttl == "" else ttl

            constructed_storage_query = (
                f"""st_supabase.get_public_url("{bucket_id}",{filepath=}, {ttl=})"""
            )
            st.session_state["storage_disabled"] = bool(not all([bucket_id, filepath]))

        elif operation == "create_signed_urls":
            lcol, rcol = st.columns([2, 1])
            paths = lcol.text_input(
                "Enter the list of paths to the files",
                placeholder="['/folder/subFolder/image.jpg','file.txt']",
            )

            expires_in = rcol.number_input(
                "Seconds until the signed URL expires",
                min_value=0,
                value=3600,
            )

            constructed_storage_query = (
                f"""st_supabase.create_signed_urls("{bucket_id}",paths={paths}, {expires_in=})"""
            )
            st.session_state["storage_disabled"] = bool(not all([bucket_id, paths, expires_in]))

        elif operation == "create_signed_upload_url":
            path = st.text_input(
                "Enter the file path",
                placeholder="/folder/subFolder/image.jpg",
            )
            constructed_storage_query = (
                f"""st_supabase.create_signed_upload_url("{bucket_id}",{path=})"""
            )
            st.session_state["storage_disabled"] = bool(not all([bucket_id, path]))

        elif operation == "upload_to_signed_url":
            path = None
            path = st.text_input(
                "Enter destination path in the bucket",
                placeholder="/folder/subFolder/image.jpg",
            )
            token = st.text_input(
                "Enter the token",
                type="password",
                help="This is generated by `.create_signed_url()`",
            )
            lcol, rcol = st.columns([1, 3])
            source = lcol.selectbox(
                label="Source filesystem",
                options=["local", "hosted"],
                help="Filesystem from where the file has to be uploaded",
            )
            overwrite = "false"
            if source == "local":
                file = rcol.file_uploader("Choose a file")

                constructed_storage_query = f"""
                st_supabase.{operation}("{bucket_id}", {source=}, {path=}, token="***", file={file}, {overwrite=})
                # `UploadedFile` is the `BytesIO` object returned by `st.file_uploader()`
                """
            elif source == "hosted":
                file = rcol.text_input(
                    "Source path",
                    placeholder="path/to/file.txt",
                    help="This is the path of the file on the Streamlit hosted filesystem",
                )
                constructed_storage_query = f"""
                st_supabase.{operation}("{bucket_id}", {source=}, {path=}, token="***", {file=}, {overwrite=})
                """
            st.session_state["storage_disabled"] = bool(not all([bucket_id, token, path]))

        st.write("**Constructed code**")
        if operation == "download":
            st.code(
                f"file_name, mime, data = {constructed_storage_query}",
                wrap_lines=True,
            )
        else:
            st.code(constructed_storage_query, wrap_lines=True)

        if st.session_state["project"] == "demo" and operation in RESTRICTED_STORAGE_OPERATORS:
            st.session_state["storage_disabled"] = True

        if st.session_state["project"] == "demo" and operation in RESTRICTED_STORAGE_OPERATORS:
            help = f"'{selected_operation.capitalize()}' not allowed in demo project"
        elif st.session_state["storage_disabled"]:
            help = "A required input is missing"
        else:
            help = None

        if st.button(
            "Run query",
            use_container_width=True,
            type="primary",
            disabled=st.session_state["storage_disabled"],
            help=help,
            key="run_storage_query",
            icon="🚀",
        ):
            try:
                if operation == "upload":
                    response = st_supabase.upload(
                        bucket_id,
                        source,
                        file,
                        destination_path,
                        overwrite,
                    )
                elif operation == "download":
                    file_name, mime, data = eval(constructed_storage_query)
                    st.success(
                        f"File **{file_name}** downloaded from Supabase to Streamlit hosted filesystem"
                    )
                    st.download_button(
                        "Download to local filesystem",
                        data=data,
                        file_name=file_name,
                        mime=mime,
                        use_container_width=True,
                        icon="⏬",
                    )
                elif operation == "upload_to_signed_url":
                    response = st_supabase.upload_to_signed_url(
                        bucket_id,
                        source,
                        path,
                        token,
                        file,
                        overwrite,
                    )
                else:
                    response = eval(constructed_storage_query)
                with contextlib.suppress(TypeError, NameError):
                    if operation == "create_bucket" and response["name"] == bucket_id:
                        st.success(f"Bucket **{bucket_id}** created", icon="✅")
                    elif (
                        operation == "update_bucket"
                        and response["message"] == "Successfully updated"
                    ):
                        st.success(f"Bucket **{bucket_id}** updated", icon="✅")
                    elif (
                        operation == "delete_bucket"
                        and response["message"] == "Successfully deleted"
                    ):
                        st.success(f"Bucket **{bucket_id}** deleted", icon="✅")
                    elif (
                        operation == "empty_bucket"
                        and response["message"] == "Successfully emptied"
                    ):
                        st.success(f"Bucket **{bucket_id}**  emptied", icon="✅")
                    elif operation == "move" and response["message"] == "Successfully moved":
                        st.success(
                            f"Moved **{bucket_id}/{from_path}** to **{bucket_id}/{to_path}**",
                            icon="✅",
                        )
                    elif (
                        operation == "upload"
                        and response.full_path == f"{bucket_id}/{destination_path.lstrip('/')}"
                    ):
                        try:
                            st.success(
                                f"Uploaded **{file.name}** to **{response.full_path}**",
                                icon="✅",
                            )
                        except AttributeError:
                            st.success(
                                f"Uploaded **{file}** to **{response.full_path}**",
                                icon="✅",
                            )
                    elif operation == "remove":
                        st.info(f"Removed **{len(response)}** objects")
                        st.write(response)
                    elif operation == "list_objects":
                        st.info(f"Listing **{len(response)}** objects")
                        _df = pd.DataFrame.from_dict(response)
                        st.dataframe(_df, use_container_width=True)
                    elif operation == "get_public_url":
                        st.success(response, icon="🔗")
                    elif operation == "create_signed_urls":
                        st.warning(
                            f"These URLs are valid only for {expires_in} seconds",
                            icon="⚠️",
                        )
                        for items in response:
                            st.write(f"**File:** {items['path']}")
                            if items["signedURL"]:
                                st.success(items["signedURL"], icon="🔗")
                            else:
                                st.error(items["error"], icon="❌")
                    elif operation == "list_buckets":
                        st.info(f"Listing **{len(response)}** buckets")
                        st.write(response)
                    elif operation == "create_signed_upload_url":
                        st.write("Signed URL")
                        st.info(f"{response['signed_url']}", icon="🔗")
                        st.write("Token")
                        st.code(response["token"], language="text", wrap_lines=True)
                        st.write("Path")
                        st.code(response["path"], wrap_lines=True)
                    elif operation == "upload_to_signed_url":
                        if response["Key"] == f"{bucket_id}/{path.lstrip('/')}":
                            try:
                                st.success(
                                    f"Uploaded **{file.name}** to **{response['Key']}**",
                                    icon="✅",
                                )
                            except AttributeError:
                                st.success(
                                    f"Uploaded **{file}** to **{response['Key']}**",
                                    icon="✅",
                                )
                    else:
                        st.write(response)
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

    with database:
        st.subheader("🗄️ Run Database Queries")

        if st.session_state["project"] == "custom":
            st.warning(
                "You are using your own project. Be careful while running DML queries!",
                icon="ℹ️",
            )
        elif st.session_state["project"] == "demo":
            st.info(
                "You are using the demo project. Some features won't be available.",
                icon="ℹ️",
            )
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

        lcol, mcol, rcol = st.columns([2, 2, 3])
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
            placeholder = value = (
                """[{"name":"Wakanda","iso2":"WK"},{"name":"Wadiya","iso2":"WD"}]"""
            )
            rcol1, rcol2 = rcol_placeholder.columns(2)
            ttl = rcol1.text_input(
                "Cache duration",
                value=0,
                placeholder=0,
                help="Set as `0` to always fetch the latest results (recommended for DML), or leave blank to cache indefinitely.",
            )
            upsert = rcol2.checkbox(
                label="Upsert",
                help="Whether the query should be an upsert",
            )
        elif request_builder == "select":
            request_builder_query_label = "Enter the columns to fetch as comma-separated strings"
            ttl = rcol_placeholder.text_input(
                "Result cache duration",
                value=None,
                placeholder=None,
                help="Set as `0` to always fetch the latest results, or leave blank to cache indefinitely.",
            )
            placeholder = value = "*"
        elif request_builder == "delete":
            request_builder_query_label = "Delete query"
            placeholder = value = "Delete does not take a request builder query"
            ttl = rcol_placeholder.text_input(
                "Results Cache duration",
                value=0,
                placeholder=0,
                help="Set as `0` to always fetch the latest results (recommended for DML), or leave blank to cache indefinitely.",
            )
        elif request_builder == "upsert":
            request_builder_query_label = "Enter the rows to upsert as json (for single row) or array of jsons (for multiple rows)"
            placeholder = value = """{"name":"Wakanda","iso2":"WK", "continent":"Africa"}"""
            rcol1, rcol2 = rcol_placeholder.columns(2)
            ttl = rcol1.text_input(
                "Cache duration",
                value=0,
                placeholder=0,
                help="Set as `0` to always fetch the latest results (recommended for DML), or leave blank to cache indefinitely.",
            )
            ignore_duplicates = rcol2.checkbox(
                label="Ignore duplicates",
                help="Whether duplicate rows should be ignored",
            )
        elif request_builder == "update":
            request_builder_query_label = "Enter the rows to update as json (for single row) or array of jsons (for multiple rows)"
            placeholder = value = """{"iso3":"N/A","continent":"N/A"}"""
            ttl = rcol_placeholder.text_input(
                "Result cache duration",
                value=0,
                placeholder=0,
                help="Set as `0` to always fetch the latest results (recommended for DML), or leave blank to cache indefinitely.",
            )

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

        if request_builder not in ["insert", "update", "upsert"]:
            operators = st.text_input(
                label="Chain any modifiers and filters you want 🔗",
                value=""".eq("continent","Asia").order("name",desc=True).limit(5)""",
                placeholder=""".eq("continent","Asia").order("name",desc=True).limit(5)""",
                help="List of all available [operators](https://postgrest-py.readthedocs.io/en/latest/api/request_builders.html#postgrest.AsyncSelectRequestBuilder) and [filters](https://postgrest-py.readthedocs.io/en/latest/api/filters.html#postgrest.AsyncFilterRequestBuilder)",
            )

            operators = operators.replace(".__init__()", "").replace(".execute()", "")

        ttl = None if ttl == "" else ttl

        if operators:
            constructed_db_query = (
                f"""execute_query(st_supabase.table("{table}").select({request_builder_query}){operators}, {ttl=})"""
                if request_builder == "select"
                else f"""execute_query(st_supabase.table("{table}").{request_builder}({request_builder_query}){operators}, {ttl=})"""
            )
        elif request_builder == "select":
            constructed_db_query = f"""execute_query(st_supabase.table("{table}").select({request_builder_query}), {ttl=})"""
        else:
            constructed_db_query = f"""execute_query(st_supabase.table("{table}").{request_builder}({request_builder_query}), {ttl=})"""
        st.write("**Constructed query**")
        st.code(constructed_db_query, wrap_lines=True)

        lcol, rcol = st.columns([2, 1])
        view = lcol.radio(
            label="View output as",
            options=["Dataframe", "Dict (recommended for joins)"],
            horizontal=True,
        )

        if rcol.button(
            "Execute query",
            use_container_width=True,
            type="primary",
            disabled=st.session_state["project"] == "demo"
            and request_builder in ["insert", "upsert", "update", "delete"],
            help=(
                f"{request_builder.upper()} not allowed in demo project"
                if st.session_state["project"] == "demo"
                and request_builder in ["insert", "upsert", "update", "delete"]
                else None
            ),
            key="run_db_query",
            icon="🚀",
        ):
            try:
                response = eval(constructed_db_query)

                if count_method:
                    st.write(
                        f"**{response.count}** rows {request_builder}ed. `count` does not take `limit` into account."
                    )
                if view == "Dataframe":
                    st.dataframe(response.data, use_container_width=True)
                else:
                    st.write(response.data)
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

    with auth:
        st.subheader("🔐 Run Auth Queries")

        AUTH_OPERATIONS = [
            "Create a new user",
            "Sign in with password",
            "Sign in with OTP",
            "Retrieve session",
            "Retrieve user",
            "Sign out",
        ]

        AUTH_OPERATORS = [
            "sign_up",
            "sign_in_with_password",
            "sign_in_with_otp",
            "get_session",
            "get_user",
            "sign_out",
        ]

        selected_auth_operation = st.selectbox(
            label="Select operation",
            options=AUTH_OPERATIONS,
            help="[Supabase Auth API reference](https://supabase.com/docs/reference/python/auth-signup)",
        )

        auth_operation_query_dict = dict(zip(AUTH_OPERATIONS, AUTH_OPERATORS))
        auth_operation = auth_operation_query_dict.get(selected_auth_operation)

        if auth_operation == "sign_up":
            lcol, rcol = st.columns(2)
            email = lcol.text_input(label="Enter your email ID")
            password = rcol.text_input(
                label="Enter your password",
                placeholder="Min 6 characters",
                type="password",
                help="Password is encrypted",
            )

            fname = lcol.text_input(
                label="First name",
                placeholder="Optional",
            )

            attribution = rcol.text_area(
                label="How did you hear about us?",
                placeholder="Optional",
            )

            constructed_auth_query = f"st_supabase.auth.{auth_operation}(dict({email=}, {password=}, options=dict(data=dict({fname=},{attribution=}))))"

        elif auth_operation == "sign_in_with_password":
            lcol, rcol = st.columns(2)
            identifier = lcol.text_input(label="Enter your email ID or phone number")
            password = rcol.text_input(
                label="Enter your password",
                placeholder="Min 6 characters",
                type="password",
                help="Password is encrypted",
            )

            identifier_field = "email" if "@" in identifier else "phone"
            creds = {identifier_field: identifier, "password": password}
            constructed_auth_query = f"st_supabase.cached_sign_in_with_password({creds})"

        elif auth_operation == "sign_in_with_otp":
            st.info(
                """Interactive demo not available for `sign_in_with_otp()` due to technical constraints.  
                
Follow the below steps to implement in your app:  
1. Setup your Email Templates in your Supabase project: https://supabase.com/dashboard/project/project-id/auth/templates  
(replace "project-id" with your Supabase project ID)  
2. Get user's email ID:  
```
email = st.text_input(label="Enter your email ID")
```
3. Send OTP to email ID: ([`sign_in_with_otp()` documentation](https://supabase.com/docs/reference/python/auth-signinwithotp))  

```
st_supabase.auth.sign_in_with_otp(dict(email=email))
```
4. Enter OTP:  
```
token = st.text_input("Enter OTP", type="password")
```
5. Verify OTP and login: ([verity_otp() documentation](https://supabase.com/docs/reference/python/auth-verifyotp))  
```
st_supabase.auth.verify_otp(dict(type="magiclink", email=email, token=token))
```
                """
            )
            constructed_auth_query = None
        elif auth_operation in ["get_session", "get_user", "sign_out"]:
            constructed_auth_query = f"st_supabase.auth.{auth_operation}()"

        if constructed_auth_query:
            st.write("**Constructed code**")
            st.code(constructed_auth_query, wrap_lines=True)

        if st.button(
            "Execute 🪄",
            use_container_width=True,
            type="primary",
            key="run_auth_query",
            disabled=not constructed_auth_query,
        ):
            try:
                response = eval(constructed_auth_query)

                if auth_operation == "sign_up":
                    auth_success_message = f"User created. Welcome {fname or ''}"
                    auth_success_icon = "🚀"
                elif auth_operation == "sign_in_with_password":
                    name = response.model_dump()["user"]["user_metadata"].get("fname", "")
                    auth_success_message = f"""Logged in. Welcome {name}"""
                    auth_success_icon = "🔓"
                elif auth_operation == "sign_out":
                    auth_success_message = "Signed out"
                    auth_success_icon = "🔒"
                elif auth_operation == "get_user":
                    auth_success_message = f"""{response.dict()["user"]["email"]} is logged in"""
                    auth_success_icon = "🔓"
                elif auth_operation == "get_session":
                    if response:
                        auth_success_message = (
                            (f"""{response.dict()["user"]["email"]} is logged in""")
                            if response
                            else None
                        )
                    else:
                        raise Exception(  # sourcery skip: raise-specific-error
                            "No logged-in user session. Log in or sign up first."
                        )

                if auth_success_message:
                    st.success(auth_success_message, icon=auth_success_icon)

                if response is not None:
                    with st.expander("JSON response"):
                        st.write(response.model_dump())

            except Exception as e:
                if auth_operation == "get_user":
                    st.error("No logged-in user. Log in or sign up first.", icon="❌")
                else:
                    st.error(e, icon="❌")

st.success(
    "[Star the repo](https://github.com/SiddhantSadangi/st_supabase_connection) to show your :heart:",
    icon="⭐",
)
