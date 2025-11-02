import mimetypes
import os
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import IO, Callable, Iterable, Literal, Optional, Tuple, Union

from postgrest import (
    APIResponse,
    SyncFilterRequestBuilder,
    SyncQueryRequestBuilder,
    SyncSelectRequestBuilder,
)
from streamlit import cache_data, cache_resource
from streamlit.connections import BaseConnection
from supabase import Client, create_client
from supabase_auth.types import AuthResponse, SignInWithPasswordCredentials

__version__ = "2.1.3"

_DEFAULT_MIME_TYPE = "application/octet-stream"


def _normalize_storage_path(path: str) -> str:
    sanitized_path = path.lstrip("/")
    if not sanitized_path:
        raise ValueError("Object paths must not be empty or point to the bucket root.")
    return sanitized_path


def _normalize_storage_paths(paths: Iterable[str]) -> list[str]:
    return [_normalize_storage_path(item) for item in paths]


def _prepare_upload_payload(
    file: Union[str, Path, BytesIO, bytes, IO[bytes]],
    fallback_name: str,
) -> tuple[Union[bytes, IO[bytes]], str, Optional[Callable[[], None]]]:
    """
    Prepare payload and content-type for uploading to storage.

    Returns
    -------
    payload : bytes | IO[bytes]
        The object that should be sent to storage3.
    content_type : str
        MIME type inferred from the file or fallback name.
    cleanup : Callable | None
        Callable to invoke after upload (used to close opened file handles).
    """
    if isinstance(file, (str, Path)):
        file_path = Path(file)
        file_obj = open(file_path, "rb")
        content_type = mimetypes.guess_type(str(file_path))[0] or _DEFAULT_MIME_TYPE
        return file_obj, content_type, file_obj.close

    # file-like object or raw bytes
    name_hint = getattr(file, "name", fallback_name)
    content_type = (
        getattr(file, "type", None)
        or getattr(file, "content_type", None)
        or mimetypes.guess_type(name_hint)[0]
        or _DEFAULT_MIME_TYPE
    )

    if isinstance(file, bytes):
        return file, content_type, None

    if hasattr(file, "seek"):
        file.seek(0)

    if hasattr(file, "getvalue"):
        payload: Union[bytes, IO[bytes]] = file.getvalue()  # type: ignore[assignment]
    elif hasattr(file, "read"):
        payload = file.read()  # type: ignore[assignment]
    else:
        payload = file  # type: ignore[assignment]

    if isinstance(payload, str):
        payload = payload.encode()

    return payload, content_type, None


class SupabaseConnection(BaseConnection[Client]):
    """
    Connects a streamlit app to Supabase Storage and Database

    Attributes
    ----------
    client : supabase.Client
        Supabase client initialized with the supabase URL and key
    storage : supabase.SupabaseStorageClient
        Supabase storage client initialized with the supabase URL and key

    Methods
    -------
    table :
        Perform a table operation
    """

    def _connect(self, **kwargs) -> None:
        if "url" in kwargs:
            url = kwargs.pop("url")
        elif "SUPABASE_URL" in self._secrets:
            url = self._secrets["SUPABASE_URL"]
        elif "SUPABASE_URL" in os.environ:
            url = os.environ.get("SUPABASE_URL")
        else:
            raise ConnectionRefusedError(
                "Supabase URL not provided. "
                "You can provide the url by "
                "passing it as the 'url' kwarg while creating the connection, or "
                "setting the 'SUPABASE_URL' Streamlit secret or environment variable."
            )

        if "key" in kwargs:
            key = kwargs.pop("key")
        elif "SUPABASE_KEY" in self._secrets:
            key = self._secrets["SUPABASE_KEY"]
        elif "SUPABASE_KEY" in os.environ:
            key = os.environ.get("SUPABASE_KEY")
        else:
            raise ConnectionRefusedError(
                "Supabase Key not provided. "
                "You can provide the key by "
                "passing it as the 'key' kwarg while creating the connection, or "
                "setting the 'SUPABASE_KEY' Streamlit secret or environment variable."
            )

        self.client = create_client(url, key)
        self.table = self.client.table
        self.auth = self.client.auth
        self.delete_bucket = self.client.storage.delete_bucket
        self.empty_bucket = self.client.storage.empty_bucket

    def cached_sign_in_with_password(
        self,
        credentials: SignInWithPasswordCredentials,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> AuthResponse:
        """Sign in with email and password or phone number and password, with caching enabled.

        Parameters
        ----------
        credentials : SignInWithPasswordCredentials
            The credentials to sign in with. This can be an email and password, or a phone number and password.
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_resource(ttl=ttl)
        def _sign_in_with_password(_self, credentials):
            return _self.auth.sign_in_with_password(credentials)

        return _sign_in_with_password(self, credentials)

    def get_bucket(
        self,
        bucket_id: str,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> dict[str, str]:
        """Retrieves the details of an existing storage bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket you would like to retrieve.
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_resource(ttl=ttl)
        def _get_bucket(_self, bucket_id):
            return _self.client.storage.get_bucket(bucket_id)

        return _get_bucket(self, bucket_id)

    def list_buckets(
        self,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> list[dict[str, str]]:
        """Retrieves the details of all storage buckets within an existing product.

        Parameters
        ----------
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_resource(ttl=ttl)
        def _list_buckets(_self):
            return _self.client.storage.list_buckets()

        return _list_buckets(self)

    def create_bucket(
        self,
        id: str,
        name: Optional[str] = None,
        public: Optional[bool] = False,
        file_size_limit: Optional[int] = None,
        allowed_mime_types: Optional["list[str]"] = None,
    ) -> "dict[str, str]":
        """Creates a new storage bucket.

        Parameters
        ----------
        id : str
            Unique identifier of the created bucket.
        name : str
            Name of the created bucket. If not passed, the id is used as the name as well.
        public :bool
            Whether the created bucket should be publicly accessible. Defaults to False.
        file_size_limit : int
            Maximum size (in bytes) of files that can be uploaded to this bucket. Pass `None` to have no limits. Defaults to `None`.
        allowed_mime_types : list[str]
            List of file types that can be uploaded to this bucket. Pass `None` to allow all file types. Defaults to `None`.
        """
        response = self.client.storage._request(
            method="POST",
            url="/bucket",
            json={
                "id": id,
                "name": name or id,
                "public": public,
                "file_size_limit": file_size_limit,
                "allowed_mime_types": allowed_mime_types,
            },
        )
        return response.json()

    def upload(
        self,
        bucket_id: str,
        source: Literal["local", "hosted"],
        file: Union[str, Path, BytesIO],
        destination_path: str,
        overwrite: Literal["true", "false"] = "false",
    ) -> "dict[str, str]":
        """Uploads a file to a Supabase bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        source : str
            "local" to upload file from your local filesystem,
            "hosted" to upload file from the Streamlit hosted filesystem.
        file : str, Path, BytesIO
            File to upload. This can be a path of the file if `source="hosted"`,
            or the `BytesIO` object returned by `st.file_uploader()` if `source="local"`.
        destination_path : str
            Path is the bucket where the file will be uploaded to.
            Folders will be created as needed. Defaults to `/filename.fileext`.
        overwrite : str
            Whether to overwrite existing file. Defaults to `false`.
        """

        if source == "local":
            with open(file.name, "wb") as f:
                f.write(file.getbuffer())
            with open(file.name, "rb") as f:
                response = self.client.storage.from_(bucket_id).upload(
                    path=destination_path or f"/{file.name}",
                    file=f,
                    file_options={"content-type": file.type, "x-upsert": overwrite},
                )
        elif source == "hosted":
            with open(file, "rb") as f:
                response = self.client.storage.from_(bucket_id).upload(
                    path=destination_path or f"/{os.path.basename(f.name)}",
                    file=f,
                    file_options={
                        "content-type": mimetypes.guess_type(file)[0],
                        "x-upsert": overwrite,
                    },
                )
        return response

    def download(
        self,
        bucket_id: str,
        source_path: str,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> Tuple[str, str, bytes]:
        """Downloads a file.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        source_path : str
            Path of the file relative in the bucket, including file name
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).

        Returns
        -------
        file_name : str
            Name of the file, inferred from the `source_path`
        mime : str
            MIME-type of the object
        data : bytes
            Downloaded bytes object
        """

        @cache_resource(ttl=ttl)
        def _download(_self, bucket_id, source_path):
            file_name = source_path.split("/")[-1]

            data = _self.client.storage.from_(bucket_id).download(source_path)
            mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

            return file_name, mime, data

        return _download(self, bucket_id, source_path)

    def update_bucket(
        self,
        bucket_id: str,
        public: Optional[bool] = False,
        file_size_limit: Optional[int] = None,
        allowed_mime_types: Optional[Union[str, "list[str]"]] = None,
    ) -> "dict[str, str]":
        """Update a storage bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket you would like to update.
        public : bool
            Whether the bucket will be publicly accessible. Defaults to `False`
        file_size_limit : int
            Size limit of the files that can be uploaded to the bucket. Set as `None` to have no limit. Defaults to `None`.
        allowed_mime_types : str
            The file MIME types that can be uploaded to the bucket. Pass a string or list of strings. Defaults to `None` for no restriction.
        """
        json = {
            "id": bucket_id,
            "name": bucket_id,
            "public": public,
            "file_size_limit": file_size_limit,
            "allowed_mime_types": allowed_mime_types,
        }
        response = self.client.storage._request("PUT", f"/bucket/{bucket_id}", json=json)
        return response.json()

    def move(self, bucket_id: str, from_path: str, to_path: str) -> "dict[str, str]":
        """Moves an existing file, optionally renaming it at the same time.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket where the object is.
        from_path : str
            The original file path, including the current file name.
        to_path : str
            The new file path, including the new file name. Path will be created if it doesn't exist.
        """
        response = self.client.storage._request(
            "POST",
            "/object/move",
            json={
                "bucketId": bucket_id,
                "sourceKey": from_path,
                "destinationKey": to_path,
            },
        )
        return response.json()

    def remove(self, bucket_id: str, paths: list) -> "dict[str, str]":
        """Deletes files within the same bucket

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket where the object is.
        paths : list
            An array or list of files to be deletes, including the path and file name. For example [`folder/image.png`].
        """
        response = self.client.storage._request(
            "DELETE",
            f"/object/{bucket_id}",
            json={"prefixes": paths},
        )
        return response.json()

    def list_objects(
        self,
        bucket_id: str,
        path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sortby: Optional[Literal["name", "updated_at", "created_at", "last_accessed_at"]] = "name",
        order: Optional[Literal["asc", "desc"]] = "asc",
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> "list[dict[str, str]]":
        """Lists all the objects within a bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        path : str
            The folder path.
        limit : int
            The number of objects to list. Defaults to 100.
        offset : int
            The number of initial objects to ignore. Defaults to 0.
        sortby : str
            The column name to sort by. Defaults to "name".
        order : str
            The sorting order. Defaults to "asc".
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_data(ttl=ttl)
        def _list_objects(_self, bucket_id, path, limit, offset, sortby, order):
            return _self.client.storage.from_(bucket_id).list(
                path,
                dict(
                    limit=limit,
                    offset=offset,
                    sortBy=dict(column=sortby, order=order),
                ),
            )

        return _list_objects(self, bucket_id, path, limit, offset, sortby, order)

    def create_signed_urls(
        self,
        bucket_id: str,
        paths: "list[str]",
        expires_in: int,
    ) -> "list[dict[str, str]]":
        """Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        paths : list
            File paths to be downloaded, including the current file name. Leading slashes are stripped; empty values raise an error.
        expires_in : int
            Number of seconds until the signed URL expires.
        """
        normalized_paths = _normalize_storage_paths(paths)
        bucket_client = self.client.storage.from_(bucket_id)
        return bucket_client.create_signed_urls(normalized_paths, expires_in)

    def get_public_url(
        self,
        bucket_id: str,
        filepath: str,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> str:
        """Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        filepath : str
            File path to be downloaded, including the current file name.
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_data(ttl=ttl)
        def _get_public_url(_self, bucket_id, filepath):
            return _self.client.storage.from_(bucket_id).get_public_url(filepath)

        return _get_public_url(self, bucket_id, filepath)

    def create_signed_upload_url(self, bucket_id: str, path: str) -> "dict[str, str]":
        """Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        path : str
            The file path, including the file name. Leading slashes are stripped; empty values raise an error.
        """
        sanitized_path = _normalize_storage_path(path)
        bucket_client = self.client.storage.from_(bucket_id)
        signed_upload = bucket_client.create_signed_upload_url(sanitized_path)
        return {
            "signed_url": signed_upload["signed_url"],
            "token": signed_upload["token"],
            "path": signed_upload["path"],
        }

    def upload_to_signed_url(
        self,
        bucket_id: str,
        path: str,
        token: str,
        file: Union[str, Path, BytesIO, bytes, IO[bytes]],
    ) -> "dict[str, str]":
        """Upload a file with a token generated from `.create_signed_url()`

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        path : str
            The file path, including the file name. This path will be created if it does not exist.
            Leading slashes are stripped; empty values raise an error.
        token : str
            The token generated from `.create_signed_url()` for the specified `path`
        file : str, Path, BytesIO, bytes, IO[bytes]
            File to upload. Accepts:
                * A local path (`str` or `pathlib.Path`)
                * The `BytesIO` object returned by `st.file_uploader()`
                * Raw `bytes`
                * Open file handles (`IO[bytes]`)
        """
        sanitized_path = _normalize_storage_path(path)

        bucket_client = self.client.storage.from_(bucket_id)
        filename = sanitized_path.rsplit("/", maxsplit=1)[-1]
        payload, content_type, cleanup = _prepare_upload_payload(file, filename)

        try:
            upload_response = bucket_client.upload_to_signed_url(
                sanitized_path,
                token,
                payload,
                file_options={"content-type": content_type},
            )
        finally:
            if cleanup:
                cleanup()

        return {
            "path": upload_response.path,
            "full_path": upload_response.full_path,
            "fullPath": upload_response.fullPath,
        }


def execute_query(
    query: Union[SyncSelectRequestBuilder, SyncQueryRequestBuilder, SyncFilterRequestBuilder],
    ttl: Optional[Union[float, timedelta, str]] = None,
) -> APIResponse:
    """Execute the query.
    This function is a wrapper around the `query.execute()` method, with caching enabled.
    This works with all types of queries, but caching may lead to unexpected results when running DML queries.

    It is recommended to set `ttl` to 0 for DML queries (insert, update, upsert, delete) to avoid caching issues.

    Parameters
    ----------
    query : SyncSelectRequestBuilder, SyncQueryRequestBuilder, SyncFilterRequestBuilder
        The query to execute. Can contain any number of chained filters and operators.
    ttl : float, timedelta, str, or None
        The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
    """

    def _hash_func(x):
        return hash(str(x.request.path) + str(x.request.params) + str(x.request.json or {}))

    @cache_resource(
        ttl=ttl,
        hash_funcs={
            SyncSelectRequestBuilder: _hash_func,
            SyncQueryRequestBuilder: _hash_func,
            SyncFilterRequestBuilder: _hash_func,
        },
    )
    def _execute(query):
        return query.execute()

    return _execute(query)
