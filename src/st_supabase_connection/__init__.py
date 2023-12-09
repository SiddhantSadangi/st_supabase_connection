import mimetypes
import os
import urllib
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional, Tuple, Union, types

from postgrest import SyncSelectRequestBuilder, types
from streamlit import cache_data, cache_resource
from streamlit.connections import BaseConnection
from supabase import Client, create_client

__version__ = "1.2.2"


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

    def query(
        self,
        *columns: str,
        table: str,
        count: Optional[types.CountMethod] = None,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ) -> SyncSelectRequestBuilder:
        """Run a SELECT query.

        Parameters
        ----------
        *columns : str
            The names of the columns to fetch.
        table : str
            The table to run the query on.
        count : str
            The method to use to get the count of rows returned. Defaults to `None`.
        ttl : float, timedelta, str, or None
            The maximum time to keep an entry in the cache. Defaults to `None` (cache never expires).
        """

        @cache_resource(ttl=ttl)
        def _query(_self, *columns, table, count):
            return _self.client.table(table).select(*columns, count=count)

        return _query(self, *columns, table=table, count=count)

    def get_bucket(
        self,
        bucket_id: str,
        ttl: Optional[Union[float, timedelta, str]] = None,
    ):
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
    ) -> list:
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
        return response.json()

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

            with open(file_name, "wb+") as f:
                response = _self.client.storage.from_(bucket_id).download(source_path)
                f.write(response)

            mime = mimetypes.guess_type(file_name)[0]
            data = open(file_name, "rb")

            return file_name, mime, data

        return _download(self, bucket_id, source_path)

    def update_bucket(
        self,
        bucket_id: str,
        public: Optional[bool] = False,
        file_size_limit: Optional[bool] = None,
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
            The file MIME types that can be uploaded to the bucket. Set as `None` to allow all types. Defaults to `None`.
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
        column_name : str
            The column name to sort by by. Defaults to "name".
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
            File paths to be downloaded, including the current file name.
        expires_in : int
            Number of seconds until the signed URL expires.
        """
        json = {"paths": paths, "expiresIn": str(expires_in)}

        response = self.client.storage._request(
            "POST",
            f"/object/sign/{bucket_id}",
            json=json,
        )
        data = response.json()
        for item in data:
            if item["signedURL"]:
                item[
                    "signedURL"
                ] = f"{self.client.storage._client.base_url}{item['signedURL'].lstrip('/')}"

        return data

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

        @cache_data(ttl)
        def _get_public_url(_self, bucket_id, filepath):
            return _self.client.storage.from_(bucket_id).get_public_url(filepath)

        return _get_public_url(self, bucket_id, filepath)

    def create_signed_upload_url(self, bucket_id: str, path: str) -> "dict[str, str]":
        """Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        path : str
            The file path, including the file name.
        """
        from storage3.utils import StorageException

        _path = self.client.storage.from_(bucket_id)._get_final_path(path)
        response = self.client.storage.from_(bucket_id)._request(
            "POST", f"/object/upload/sign/{_path}"
        )
        data = response.json()
        full_url: urllib.parse.ParseResult = urllib.parse.urlparse(
            str(self.client.storage._client.base_url) + data["url"]
        )
        query_params = urllib.parse.parse_qs(full_url.query)

        if not query_params.get("token"):
            raise StorageException("No token sent by the API")
        return {
            "signed_url": full_url.geturl(),
            "token": query_params["token"][0],
            "path": path,
        }

    def upload_to_signed_url(
        self,
        bucket_id: str,
        source: Literal["local", "hosted"],
        path: str,
        token: str,
        file: Union[str, Path, BytesIO],
    ) -> "dict[str, str]":
        """Upload a file with a token generated from `.create_signed_url()`

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        source : str
            "local" to upload file from your local filesystem,
            "hosted" to upload file from the Streamlit hosted filesystem.
        path : str
            The file path, including the file name. This path will be created if it does not exist.
        token : str
            The token generated from `.create_signed_url()` for the specified `path`
        file : str, Path, BytesIO
            File to upload. This can be a path of the file if `source="hosted"`,
            or the `BytesIO` object returned by `st.file_uploader()` if `source="local"`.
        """
        _path = self.client.storage.from_(bucket_id)._get_final_path(path)
        _url = urllib.parse.urlparse(f"/object/upload/sign/{_path}")
        query_params = urllib.parse.urlencode({"token": token})
        final_url = f"{_url.geturl()}?{query_params}"

        filename = path.rsplit("/", maxsplit=1)[-1]

        if source == "local":
            _file = {"file": (filename, file, file.type)}
            response = self.client.storage.from_(bucket_id)._request(
                "PUT",
                final_url,
                files=_file,
            )
        elif source == "hosted":
            with open(file, "rb") as f_obj:
                _file = {"file": (filename, f_obj, mimetypes.guess_type(file)[0])}
                response = self.client.storage.from_(bucket_id)._request(
                    "PUT",
                    final_url,
                    files=_file,
                )

        return response.json()
