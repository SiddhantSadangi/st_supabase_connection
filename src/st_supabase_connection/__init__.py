import hashlib
import mimetypes
import os
import warnings
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import IO, Any, Literal, Optional, Tuple, Union, cast

from postgrest import (
    APIResponse,
    SyncFilterRequestBuilder,
    SyncQueryRequestBuilder,
    SyncSelectRequestBuilder,
)
from storage3.types import BaseBucket, UploadResponse
from streamlit import cache_data, session_state
from streamlit.connections import BaseConnection
from supabase import Client, create_client
from supabase_auth.types import AuthResponse, SignInWithPasswordCredentials

__version__ = "2.2.1"

_DEFAULT_MIME_TYPE = "application/octet-stream"
_MAX_CACHE_ENTRIES = 128
_SESSION_CLIENT_STATE_PREFIX = "_st_supabase_connection_session_client"


def _credential_fingerprint(url: str, key: str) -> str:
    return hashlib.sha256(f"{url}\0{key}".encode()).hexdigest()


def _get_or_create_session_client(
    state: MutableMapping[str, Any],
    *,
    connection_name: str,
    url: str,
    key: str,
    client_factory: Optional[Callable[[str, str], Client]] = None,
) -> Client:
    """Return one Supabase client per Streamlit browser session and connection."""
    normalized_url = url.strip()
    normalized_key = key.strip()
    if not normalized_url or not normalized_key:
        raise ValueError("Supabase URL and key are required.")

    fingerprint = _credential_fingerprint(normalized_url, normalized_key)
    state_key = f"{_SESSION_CLIENT_STATE_PREFIX}:{connection_name}:{fingerprint}"
    existing_client = state.get(state_key)
    if existing_client is not None:
        return cast(Client, existing_client)

    factory = client_factory or create_client
    client = factory(normalized_url, normalized_key)
    state[state_key] = client
    return client


def _query_method(query: Any) -> str:
    request = getattr(query, "request", None)
    return str(getattr(request, "method", None) or getattr(request, "http_method", "")).upper()


def _query_hash(query: Any) -> str:
    """Hash a query without exposing credentials or sharing cached user data."""
    request = query.request
    query_session = getattr(query, "session", None)
    if query_session is None:
        query_session = getattr(request, "session", None)
    base_url = getattr(query_session, "base_url", "")
    normalized_headers = {}
    for headers in (
        getattr(query_session, "headers", {}),
        getattr(request, "headers", {}),
    ):
        try:
            header_items = headers.items()
        except AttributeError:
            header_items = ()
        for name, value in header_items:
            normalized_name = str(name).lower()
            normalized_value = str(value)
            if normalized_name in {"authorization", "apikey"}:
                normalized_value = hashlib.sha256(normalized_value.encode()).hexdigest()
            normalized_headers[normalized_name] = normalized_value
    material = (
        _query_method(query),
        str(base_url),
        str(getattr(request, "url", "")),
        str(getattr(request, "path", "")),
        str(getattr(request, "params", "")),
        str(getattr(request, "json", None) or {}),
        tuple(sorted(normalized_headers.items())),
    )
    return hashlib.sha256(repr(material).encode()).hexdigest()


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
        elif "SUPABASE_PUBLISHABLE_KEY" in self._secrets:
            key = self._secrets["SUPABASE_PUBLISHABLE_KEY"]
        elif "SUPABASE_KEY" in self._secrets:
            key = self._secrets["SUPABASE_KEY"]
        elif "SUPABASE_PUBLISHABLE_KEY" in os.environ:
            key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        elif "SUPABASE_KEY" in os.environ:
            key = os.environ.get("SUPABASE_KEY")
        else:
            raise ConnectionRefusedError(
                "Supabase Key not provided. "
                "You can provide the key by "
                "passing it as the 'key' kwarg while creating the connection, or "
                "setting the 'SUPABASE_KEY' or 'SUPABASE_PUBLISHABLE_KEY' "
                "Streamlit secret or environment variable."
            )

        self._url = url
        self._key = key
        self.client = create_client(self._url, self._key)
        self.table = self.client.table
        self._shared_auth = self.client.auth
        self.delete_bucket = self.client.storage.delete_bucket
        self.empty_bucket = self.client.storage.empty_bucket

    @property
    def auth(self):
        """Return the deprecated process-shared Auth client.

        Use ``session_client().auth`` so login state and tokens are isolated to the
        current Streamlit browser session.
        """
        warnings.warn(
            "`SupabaseConnection.auth` is deprecated because Streamlit connections "
            "are shared across sessions; use `session_client().auth` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._shared_auth

    def session_client(self) -> Client:
        """Return a full Supabase client scoped to the current browser session.

        Use this client for Auth and for database, storage, functions, or realtime
        operations that must carry the signed-in user's JWT.
        """
        return _get_or_create_session_client(
            session_state,
            connection_name=self._connection_name,
            url=self._url,
            key=self._key,
        )

    def cached_sign_in_with_password(
        self,
        credentials: SignInWithPasswordCredentials,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> AuthResponse:
        """Sign in through the session-scoped client without caching credentials.

        .. deprecated:: 2.2.0
            Use ``session_client().auth.sign_in_with_password(credentials)``.
            The ``ttl`` argument is retained for compatibility and ignored.
        """
        _ = ttl
        warnings.warn(
            "`cached_sign_in_with_password()` is deprecated because Auth responses "
            "must not be shared through Streamlit's global cache; use "
            "`session_client().auth.sign_in_with_password()` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.session_client().auth.sign_in_with_password(credentials)

    def _storage_cache_key(self, storage: Any) -> str:
        """Scope cached data to the project, credentials, and current Storage headers.

        Storage3 exposes headers differently across supported versions. Include
        each layer so a token refresh or a caller-supplied header changes the key.
        Only the digest is passed to Streamlit's cache, never the raw credentials.
        """
        header_layers = (
            self.client.options.headers,
            getattr(storage, "headers", {}),
            getattr(storage, "_headers", {}),
            getattr(getattr(storage, "session", None), "headers", {}),
        )
        headers = tuple(
            tuple(sorted((str(name).lower(), str(value)) for name, value in layer.items()))
            for layer in header_layers
            if isinstance(layer, Mapping)
        )
        material = (self._url, self._key, headers)
        return hashlib.sha256(repr(material).encode()).hexdigest()

    def get_bucket(
        self,
        bucket_id: str,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> BaseBucket:
        """Retrieves the details of an existing storage bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket you would like to retrieve.
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (no time-based expiration; at most 128 cached entries).
        """

        @cache_data(ttl=ttl, max_entries=_MAX_CACHE_ENTRIES)
        def _get_bucket(_storage, scope, bucket_id):
            return _storage.get_bucket(bucket_id)

        storage = self.client.storage
        return _get_bucket(storage, self._storage_cache_key(storage), bucket_id)

    def list_buckets(
        self,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> list[BaseBucket]:
        """Retrieves the details of all storage buckets within the project.

        Parameters
        ----------
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (no time-based expiration; at most 128 cached entries).
        """

        @cache_data(ttl=ttl, max_entries=_MAX_CACHE_ENTRIES)
        def _list_buckets(_storage, scope):
            return _storage.list_buckets()

        storage = self.client.storage
        return _list_buckets(storage, self._storage_cache_key(storage))

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
        return self.client.storage.create_bucket(
            id,
            name=name,
            options={
                "public": public,
                "file_size_limit": file_size_limit,
                "allowed_mime_types": allowed_mime_types,
            },
        )

    def upload(
        self,
        bucket_id: str,
        source: Literal["local", "hosted"],
        file: Union[str, Path, BytesIO, bytes, IO[bytes]],
        destination_path: str,
        overwrite: Literal["true", "false"] = "false",
    ) -> UploadResponse:
        """Uploads a file to a Supabase bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        source : str
            "local" to upload file from your local filesystem,
            "hosted" to upload file from the Streamlit hosted filesystem.
        file : str, Path, BytesIO, bytes, IO[bytes]
            File to upload. This can be a path of the file if `source="hosted"`,
            or the `BytesIO` object returned by `st.file_uploader()` if `source="local"`.
            Raw bytes and open binary streams are also accepted.
        destination_path : str
            Path is the bucket where the file will be uploaded to.
            Folders will be created as needed. Defaults to `/filename.fileext`.
        overwrite : str
            Whether to overwrite existing file. Defaults to `false`.
        """
        if source not in {"local", "hosted"}:
            raise ValueError("source must be either 'local' or 'hosted'.")

        if isinstance(file, (str, Path)):
            fallback_name = Path(file).name
        else:
            fallback_name = Path(getattr(file, "name", "upload.bin")).name
        target_path = _normalize_storage_path(destination_path or fallback_name)
        payload, content_type, cleanup = _prepare_upload_payload(file, fallback_name)

        try:
            return self.client.storage.from_(bucket_id).upload(
                path=target_path,
                file=payload,
                file_options={
                    "content-type": content_type,
                    "x-upsert": overwrite,
                },
            )
        finally:
            if cleanup:
                cleanup()

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
            The maximum time to keep an entry in the cache. Defaults to `None` (no time-based expiration; at most 128 cached entries).

        Returns
        -------
        file_name : str
            Name of the file, inferred from the `source_path`
        mime : str
            MIME-type of the object
        data : bytes
            Downloaded bytes object
        """

        @cache_data(ttl=ttl, max_entries=_MAX_CACHE_ENTRIES)
        def _download(_storage, scope, bucket_id, source_path):
            file_name = source_path.split("/")[-1]

            data = _storage.from_(bucket_id).download(source_path)
            mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

            return file_name, mime, data

        storage = self.client.storage
        return _download(storage, self._storage_cache_key(storage), bucket_id, source_path)

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
        return self.client.storage.update_bucket(
            bucket_id,
            options={
                "public": public,
                "file_size_limit": file_size_limit,
                "allowed_mime_types": (
                    [allowed_mime_types]
                    if isinstance(allowed_mime_types, str)
                    else allowed_mime_types
                ),
            },
        )

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
        return self.client.storage.from_(bucket_id).move(from_path, to_path)

    def remove(self, bucket_id: str, paths: list[str]) -> list[dict[str, Any]]:
        """Deletes files within the same bucket

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket where the object is.
        paths : list
            An array or list of files to be deletes, including the path and file name. For example [`folder/image.png`].
        """
        return self.client.storage.from_(bucket_id).remove(paths)

    def list_objects(
        self,
        bucket_id: str,
        path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sortby: Optional[Literal["name", "updated_at", "created_at", "last_accessed_at"]] = "name",
        order: Optional[Literal["asc", "desc"]] = "asc",
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> list[dict[str, Any]]:
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
            The maximum time to keep an entry in the cache. Defaults to `None` (no time-based expiration; at most 128 cached entries).
        """

        @cache_data(ttl=ttl, max_entries=_MAX_CACHE_ENTRIES)
        def _list_objects(_storage, scope, bucket_id, path, limit, offset, sortby, order):
            return _storage.from_(bucket_id).list(
                path,
                dict(
                    limit=limit,
                    offset=offset,
                    sortBy=dict(column=sortby, order=order),
                ),
            )

        storage = self.client.storage
        return _list_objects(
            storage, self._storage_cache_key(storage), bucket_id, path, limit, offset, sortby, order
        )

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
        """Construct a public URL locally, without an HTTP request or result cache.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        filepath : str
            File path to be downloaded, including the current file name.
        ttl : float, timedelta, str, or None
            Retained for compatibility and ignored; URL construction is not cached.
        """

        return self.client.storage.from_(bucket_id).get_public_url(filepath)

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
        """Upload a file with a token generated from `.create_signed_upload_url()`.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        path : str
            The file path, including the file name. This path will be created if it does not exist.
            Leading slashes are stripped; empty values raise an error.
        token : str
            The token generated from `.create_signed_upload_url()` for the specified `path`
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
    """Execute a query, caching only GET/HEAD reads as independent response copies.

    Writes, POST-based RPC calls, and unrecognized request methods always execute
    directly, regardless of ``ttl``. Set ``ttl=0`` to bypass caching for reads too.

    Parameters
    ----------
    query : SyncSelectRequestBuilder, SyncQueryRequestBuilder, SyncFilterRequestBuilder
        The query to execute. Can contain any number of chained filters and operators.
    ttl : float, timedelta, str, or None
        The maximum time to keep an entry in the cache. Defaults to `None` (no time-based expiration; at most 128 cached entries).
    """

    if ttl == 0 or _query_method(query) not in {"GET", "HEAD"}:
        return query.execute()

    @cache_data(ttl=ttl, max_entries=_MAX_CACHE_ENTRIES)
    def _execute(_query, query_key):
        return _query.execute()

    return _execute(query, _query_hash(query))
