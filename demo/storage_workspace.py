"""Task-focused Storage explorer for the demo app."""

from __future__ import annotations

from typing import Any

import streamlit as st
from session_storage import SessionStorage
from ui_helpers import (
    action_fingerprint,
    clear_result,
    construct_call,
    consume_confirmation,
    literal,
    open_confirmation,
    render_code_preview,
    render_result,
    store_error,
    store_result,
    sync_result_context,
)

SCOPE = "storage"
SESSION_CLIENT_CODE = "supabase = st_supabase.session_client()"
DEMO_OBJECTS = {
    "bucket1": ["awesome_zoom_background.jpg"],
    "bucket2": ["folder1/folder2/lenna.png"],
}

OPERATION_GROUPS = {
    "Read": [
        ("List buckets", "list_buckets"),
        ("Retrieve bucket", "get_bucket"),
        ("List files", "list_objects"),
        ("Download file", "download"),
        ("Get public URL", "get_public_url"),
        ("Create signed download URLs", "create_signed_urls"),
    ],
    "Write": [
        ("Create bucket", "create_bucket"),
        ("Update bucket", "update_bucket"),
        ("Upload file", "upload"),
        ("Move or rename file", "move"),
        ("Create signed upload URL", "create_signed_upload_url"),
        ("Upload with signed URL", "upload_to_signed_url"),
    ],
    "Destructive": [
        ("Empty bucket", "empty_bucket"),
        ("Delete bucket", "delete_bucket"),
        ("Delete files", "remove"),
    ],
}


def render_storage_workspace(connection: Any, *, project: str, project_label: str) -> None:
    st.header("Storage", anchor=False)
    st.caption("Choose one task, configure it, review the generated Python, then run it.")

    if project == "demo":
        st.badge("Read-only demo", color="blue", icon=":material/visibility:")
        st.caption(
            "Write and destructive operations are hidden in the demo. Connect your "
            "own project to review those workflows."
        )
        risk = "Read"
    else:
        risk = st.segmented_control(
            "Operation type",
            options=list(OPERATION_GROUPS),
            default="Read",
            key="storage_risk",
        )

    operations = dict(OPERATION_GROUPS[risk])
    selected_label = st.selectbox(
        "Storage task",
        options=list(operations),
        key=f"storage_operation_{risk.lower()}",
    )
    operation = operations[selected_label]

    if risk == "Write":
        st.warning(
            "This operation can create or change Storage data.",
            icon=":material/edit:",
        )
    elif risk == "Destructive":
        st.error(
            "This operation can permanently remove Storage data.",
            icon=":material/delete_forever:",
        )

    storage = SessionStorage(connection.session_client())
    params, validation_error = _render_inputs(operation, storage, project)
    code = _render_code(operation, params) if validation_error is None else None

    if code:
        render_code_preview(code)
    elif validation_error and _has_meaningful_input(params):
        st.error(validation_error, icon=":material/error:")

    action_values = _fingerprint_values(operation, params)
    action_id = action_fingerprint(f"{SCOPE}:{operation}", action_values)
    sync_result_context(SCOPE, action_id)
    confirmed = consume_confirmation(SCOPE, action_id)

    if risk == "Read":
        clicked = st.button(
            "Run query",
            type="primary",
            icon=":material/play_arrow:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
            key="storage_run_read",
        )
        if clicked:
            _execute(storage, operation, params, selected_label)
    else:
        button_label = "Review destructive action" if risk == "Destructive" else "Review write"
        clicked = st.button(
            button_label,
            type="primary",
            icon=":material/rate_review:",
            width="stretch",
            disabled=validation_error is not None,
            help=validation_error,
            key=f"storage_review_{risk.lower()}",
        )
        if clicked and code:
            phrase = str(params.get("bucket_id") or "DELETE") if risk == "Destructive" else "RUN"
            open_confirmation(
                scope=SCOPE,
                action_id=action_id,
                operation=selected_label,
                project=project_label,
                target=_target(operation, params),
                code=code,
                phrase=phrase,
            )
        if confirmed:
            _execute(storage, operation, params, selected_label)

    render_result(SCOPE)


def _render_inputs(
    operation: str,
    storage: SessionStorage,
    project: str,
) -> tuple[dict[str, Any], str | None]:
    params: dict[str, Any] = {}

    if operation != "list_buckets":
        if project == "demo":
            params["bucket_id"] = st.selectbox(
                "Bucket",
                options=list(DEMO_OBJECTS),
                key=f"storage_{operation}_bucket",
            )
        else:
            params["bucket_id"] = st.text_input(
                "Bucket ID",
                key=f"storage_{operation}_bucket",
                placeholder="Required",
            ).strip()

    if operation == "create_bucket":
        left, right = st.columns(2)
        params["name"] = left.text_input(
            "Bucket name",
            key="storage_create_name",
            help="Optional. The bucket ID is used when left blank.",
        ).strip()
        params["file_size_limit"] = right.number_input(
            "File size limit (bytes)",
            min_value=0,
            value=0,
            key="storage_create_size",
            help="0 means no file-size limit.",
        )
        params["allowed_mime_types"] = st.multiselect(
            "Allowed MIME types",
            options=["image/jpeg", "image/png", "application/pdf", "text/plain"],
            default=[],
            accept_new_options=True,
            key="storage_create_mime",
            help="Leave empty to allow all file types.",
        )
        params["public"] = st.checkbox(
            "Make this bucket public",
            key="storage_create_public",
        )

    elif operation == "update_bucket":
        bucket_id = params["bucket_id"]
        if st.button(
            "Load current settings",
            icon=":material/download:",
            disabled=not bucket_id,
            key="storage_load_bucket",
        ):
            try:
                current = storage.get_bucket(bucket_id)
                st.session_state["storage_update_size"] = int(
                    _property(current, "file_size_limit") or 0
                )
                st.session_state["storage_update_mime"] = list(
                    _property(current, "allowed_mime_types") or []
                )
                st.session_state["storage_update_public"] = bool(
                    _property(current, "public") or False
                )
                st.toast("Current bucket settings loaded")
            except Exception as exc:
                store_error(SCOPE, exc, context="Loading bucket settings")

        st.session_state.setdefault("storage_update_size", 0)
        st.session_state.setdefault("storage_update_mime", [])
        st.session_state.setdefault("storage_update_public", False)
        left, right = st.columns(2)
        params["file_size_limit"] = left.number_input(
            "File size limit (bytes)",
            min_value=0,
            key="storage_update_size",
            help="0 means no file-size limit.",
        )
        params["public"] = right.checkbox(
            "Public bucket",
            key="storage_update_public",
        )
        params["allowed_mime_types"] = st.multiselect(
            "Allowed MIME types",
            options=["image/jpeg", "image/png", "application/pdf", "text/plain"],
            accept_new_options=True,
            key="storage_update_mime",
            help="Leave empty to allow all file types.",
        )

    elif operation == "upload":
        uploaded = st.file_uploader(
            "Choose a file",
            key="storage_upload_file",
        )
        params["file"] = uploaded
        params["destination_path"] = st.text_input(
            "Destination path",
            key="storage_upload_destination",
            placeholder=uploaded.name if uploaded else "folder/file.ext",
        ).strip()
        params["overwrite"] = st.checkbox(
            "Overwrite an existing file",
            key="storage_upload_overwrite",
        )

    elif operation == "move":
        left, right = st.columns(2)
        params["from_path"] = left.text_input(
            "Current path",
            key="storage_move_from",
            placeholder="folder/current-name.ext",
        ).strip()
        params["to_path"] = right.text_input(
            "New path",
            key="storage_move_to",
            placeholder="folder/new-name.ext",
        ).strip()

    elif operation == "remove":
        params["paths"] = st.multiselect(
            "Files to delete",
            options=[],
            accept_new_options=True,
            key="storage_remove_paths",
            placeholder="Type a path and press Enter",
        )

    elif operation == "list_objects":
        params["path"] = st.text_input(
            "Folder path",
            key="storage_list_path",
            placeholder="Optional — leave blank for the bucket root",
        ).strip()
        left, right = st.columns(2)
        params["limit"] = left.number_input(
            "Maximum files",
            min_value=1,
            value=100,
            key="storage_list_limit",
        )
        params["offset"] = right.number_input(
            "Offset",
            min_value=0,
            value=0,
            key="storage_list_offset",
        )
        left, right = st.columns(2)
        params["sortby"] = left.selectbox(
            "Sort by",
            options=["name", "updated_at", "created_at", "last_accessed_at"],
            key="storage_list_sort",
        )
        params["order"] = right.segmented_control(
            "Direction",
            options=["Ascending", "Descending"],
            default="Ascending",
            key="storage_list_order",
        )
    elif operation == "download":
        if project == "demo":
            params["source_path"] = st.selectbox(
                "File path",
                options=DEMO_OBJECTS[params["bucket_id"]],
                key="storage_download_path",
            )
        else:
            params["source_path"] = st.text_input(
                "File path",
                key="storage_download_path",
                placeholder="folder/file.ext",
            ).strip()
    elif operation == "get_public_url":
        if project == "demo":
            params["filepath"] = st.selectbox(
                "File path",
                options=DEMO_OBJECTS[params["bucket_id"]],
                key="storage_public_path",
            )
        else:
            params["filepath"] = st.text_input(
                "File path",
                key="storage_public_path",
                placeholder="folder/file.ext",
            ).strip()
        st.caption("Public URLs only provide access when the bucket is public.")
    elif operation == "create_signed_urls":
        demo_paths = DEMO_OBJECTS.get(params["bucket_id"], [])
        selection_key = "storage_signed_paths"
        if (
            project == "demo"
            and st.session_state.get("_storage_signed_paths_bucket") != params["bucket_id"]
        ):
            st.session_state[selection_key] = demo_paths[:1]
            st.session_state["_storage_signed_paths_bucket"] = params["bucket_id"]
        params["paths"] = st.multiselect(
            "Files to sign",
            options=demo_paths if project == "demo" else [],
            accept_new_options=project != "demo",
            key=selection_key,
            placeholder="Type a path and press Enter",
        )
        params["expires_in"] = st.number_input(
            "Expires after (seconds)",
            min_value=1,
            value=3600,
            key="storage_signed_expiry",
        )

    elif operation == "create_signed_upload_url":
        params["path"] = st.text_input(
            "Destination path",
            key="storage_signed_upload_path",
            placeholder="folder/file.ext",
        ).strip()

    elif operation == "upload_to_signed_url":
        left, right = st.columns(2)
        params["path"] = left.text_input(
            "Destination path",
            key="storage_token_upload_path",
            placeholder="folder/file.ext",
        ).strip()
        params["token"] = right.text_input(
            "Signed-upload token",
            type="password",
            key="storage_token_upload_token",
        )
        params["file"] = st.file_uploader(
            "Choose a file",
            key="storage_token_upload_file",
        )

    return params, _validate(operation, params)


def _validate(operation: str, params: dict[str, Any]) -> str | None:
    bucket_id = params.get("bucket_id")
    if operation != "list_buckets" and not bucket_id:
        return "Enter a bucket ID."

    required = {
        "upload": ("file",),
        "move": ("from_path", "to_path"),
        "remove": ("paths",),
        "download": ("source_path",),
        "get_public_url": ("filepath",),
        "create_signed_urls": ("paths",),
        "create_signed_upload_url": ("path",),
        "upload_to_signed_url": ("path", "token", "file"),
    }
    labels = {
        "file": "Choose a file.",
        "from_path": "Enter the current file path.",
        "to_path": "Enter the new file path.",
        "paths": "Add at least one file path.",
        "source_path": "Enter a file path.",
        "filepath": "Enter a file path.",
        "path": "Enter a destination path.",
        "token": "Enter the signed-upload token.",
    }
    for field in required.get(operation, ()):
        if not params.get(field):
            return labels[field]
    return None


def _render_code(operation: str, params: dict[str, Any]) -> str:
    bucket = params.get("bucket_id")
    bucket_api = f"supabase.storage.from_({bucket!r})"
    if operation == "list_buckets":
        call = construct_call("supabase.storage", operation)
    elif operation == "get_bucket":
        call = construct_call("supabase.storage", operation, bucket)
    elif operation == "create_bucket":
        call = construct_call(
            "supabase.storage",
            operation,
            bucket,
            name=params["name"] or None,
            options={
                "public": params["public"],
                "file_size_limit": int(params["file_size_limit"]) or None,
                "allowed_mime_types": params["allowed_mime_types"] or None,
            },
        )
    elif operation == "update_bucket":
        call = construct_call(
            "supabase.storage",
            operation,
            bucket,
            options={
                "public": params["public"],
                "file_size_limit": int(params["file_size_limit"]) or None,
                "allowed_mime_types": params["allowed_mime_types"] or None,
            },
        )
    elif operation == "upload":
        destination = params["destination_path"] or params["file"].name
        call = (
            construct_call(
                bucket_api,
                operation,
                path=destination.lstrip("/"),
                file=literal("uploaded_file.getvalue()"),
                file_options=literal(
                    '{"content-type": uploaded_file.type or "application/octet-stream", '
                    f'"upsert": {("true" if params["overwrite"] else "false")!r}}}'
                ),
            )
            + "\n# uploaded_file is returned by st.file_uploader()."
        )
    elif operation == "move":
        call = construct_call(
            bucket_api,
            operation,
            params["from_path"],
            params["to_path"],
        )
    elif operation == "remove":
        call = construct_call(bucket_api, operation, params["paths"])
    elif operation == "list_objects":
        call = construct_call(
            bucket_api,
            "list",
            params["path"] or None,
            {
                "limit": int(params["limit"]),
                "offset": int(params["offset"]),
                "sortBy": {
                    "column": params["sortby"],
                    "order": "asc" if params["order"] == "Ascending" else "desc",
                },
            },
        )
    elif operation == "download":
        call = "data = " + construct_call(bucket_api, operation, params["source_path"])
    elif operation == "get_public_url":
        call = construct_call(bucket_api, operation, params["filepath"])
    elif operation == "create_signed_urls":
        call = construct_call(
            bucket_api,
            operation,
            params["paths"],
            int(params["expires_in"]),
        )
    elif operation == "create_signed_upload_url":
        call = construct_call(
            bucket_api,
            operation,
            params["path"],
        )
    elif operation == "upload_to_signed_url":
        call = (
            construct_call(
                bucket_api,
                operation,
                params["path"],
                literal('"***"'),
                literal("uploaded_file.getvalue()"),
                file_options=literal(
                    '{"content-type": uploaded_file.type or "application/octet-stream"}'
                ),
            )
            + "\n# uploaded_file is returned by st.file_uploader()."
        )
    else:
        call = construct_call("supabase.storage", operation, bucket)
    return f"{SESSION_CLIENT_CODE}\n\n{call}"


def _execute(
    storage: SessionStorage,
    operation: str,
    params: dict[str, Any],
    label: str,
) -> None:
    clear_result(SCOPE)
    try:
        bucket = params.get("bucket_id")
        if operation == "list_buckets":
            response = storage.list_buckets()
            store_result(
                SCOPE,
                title=(
                    f"Retrieved {len(response)} " f"{'bucket' if len(response) == 1 else 'buckets'}"
                ),
                data=response,
                display="table",
            )
        elif operation == "get_bucket":
            response = storage.get_bucket(bucket)
            store_result(SCOPE, title="Bucket retrieved", data=response)
        elif operation == "create_bucket":
            response = storage.create_bucket(
                bucket,
                name=params["name"] or None,
                file_size_limit=int(params["file_size_limit"]) or None,
                allowed_mime_types=params["allowed_mime_types"] or None,
                public=params["public"],
            )
            store_result(SCOPE, title=f"Bucket {bucket} created", data=response)
        elif operation == "update_bucket":
            response = storage.update_bucket(
                bucket,
                file_size_limit=int(params["file_size_limit"]) or None,
                allowed_mime_types=params["allowed_mime_types"] or None,
                public=params["public"],
            )
            store_result(SCOPE, title=f"Bucket {bucket} updated", data=response)
        elif operation == "delete_bucket":
            response = storage.delete_bucket(bucket)
            store_result(SCOPE, title=f"Bucket {bucket} deleted", data=response)
        elif operation == "empty_bucket":
            response = storage.empty_bucket(bucket)
            store_result(SCOPE, title=f"Bucket {bucket} emptied", data=response)
        elif operation == "upload":
            destination = params["destination_path"] or params["file"].name
            response = storage.upload(
                bucket,
                params["file"],
                destination,
                overwrite=params["overwrite"],
            )
            store_result(
                SCOPE,
                title="File uploaded",
                message=f"Destination: {bucket}/{destination.lstrip('/')}",
                data=response,
            )
        elif operation == "move":
            response = storage.move(
                bucket,
                params["from_path"],
                params["to_path"],
            )
            store_result(
                SCOPE,
                title="File moved",
                message=f"{params['from_path']} → {params['to_path']}",
                data=response,
            )
        elif operation == "remove":
            response = storage.remove(bucket, params["paths"])
            store_result(
                SCOPE,
                title=f"Delete request completed for {len(params['paths'])} files",
                data=response,
            )
        elif operation == "list_objects":
            response = storage.list_objects(
                bucket,
                path=params["path"],
                limit=int(params["limit"]),
                offset=int(params["offset"]),
                sortby=params["sortby"],
                order="asc" if params["order"] == "Ascending" else "desc",
            )
            store_result(
                SCOPE,
                title=(
                    f"Retrieved {len(response)} " f"{'file' if len(response) == 1 else 'files'}"
                ),
                data=response,
                display="table",
            )
        elif operation == "download":
            file_name, mime, data = storage.download(
                bucket,
                params["source_path"],
            )
            store_result(
                SCOPE,
                title="File is ready to download",
                message=f"Source: {bucket}/{params['source_path'].lstrip('/')}",
                download={"data": data, "file_name": file_name, "mime": mime},
            )
        elif operation == "get_public_url":
            response = storage.get_public_url(
                bucket,
                params["filepath"],
            )
            store_result(SCOPE, title="Public URL created", url=response)
        elif operation == "create_signed_urls":
            response = storage.create_signed_urls(
                bucket,
                paths=params["paths"],
                expires_in=int(params["expires_in"]),
            )
            store_result(
                SCOPE,
                title=(
                    f"Created {len(response)} signed " f"{'URL' if len(response) == 1 else 'URLs'}"
                ),
                message=f"Valid for {int(params['expires_in'])} seconds.",
                data=response,
                display="table",
            )
        elif operation == "create_signed_upload_url":
            response = storage.create_signed_upload_url(
                bucket,
                path=params["path"],
            )
            store_result(
                SCOPE,
                title="Signed upload URL created",
                message="Treat the returned token as sensitive.",
                data=response,
            )
        elif operation == "upload_to_signed_url":
            response = storage.upload_to_signed_url(
                bucket,
                params["path"],
                params["token"],
                params["file"],
            )
            store_result(SCOPE, title="File uploaded with signed URL", data=response)
        else:
            raise ValueError(f"Unsupported Storage operation: {operation}")
    except Exception as exc:
        store_error(SCOPE, exc, context=label)
    if operation == "upload_to_signed_url":
        st.session_state["_clear_storage_secret_fields"] = True
        st.rerun()


def _fingerprint_values(operation: str, params: dict[str, Any]) -> dict[str, Any]:
    values = dict(params)
    uploaded = values.get("file")
    if uploaded is not None:
        values["file"] = {
            "name": getattr(uploaded, "name", "uploaded-file"),
            "size": getattr(uploaded, "size", None),
        }
    return {"operation": operation, **values}


def _target(operation: str, params: dict[str, Any]) -> str:
    bucket = params.get("bucket_id", "all buckets")
    paths = params.get("paths")
    if paths:
        return f"{bucket}: {', '.join(paths)}"
    path = (
        params.get("path")
        or params.get("source_path")
        or params.get("filepath")
        or params.get("destination_path")
    )
    return f"{bucket}/{str(path).lstrip('/')}" if path else str(bucket)


def _has_meaningful_input(params: dict[str, Any]) -> bool:
    return any(
        value not in (None, "", [], False, 0)
        for key, value in params.items()
        if key
        not in {
            "ttl",
            "limit",
            "offset",
            "file_size_limit",
            "sortby",
            "order",
            "expires_in",
        }
    )


def _property(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
