import os
from io import BytesIO
from typing import Literal, Optional, Tuple, Union

from streamlit.connections import ExperimentalBaseConnection
from supabase import Client, create_client

# TODO: Update demo app
# TODO: Update README (highlight benefits 1. same methods as the supabase API
# 2. Storage methods are built on storage3, the backend behind the supaabse API. So it supports methods not currently supported by supabase python API (TODO: supprt postgresy-py methods for database (https://github.com/supabase-community/postgrest-py/blob/master/postgrest/_sync/request_builder.py#L177C13-L177C13))
# 3. Unified logging methods as opposed to supabase
# 4. less code when using upload and download)
# TODO: Add docstrings and example usage

__version__ = "0.0.2"


class SupabaseConnection(ExperimentalBaseConnection[Client]):
    """
    Connects a streamlit app to Supabase

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
        # TODO: Use cache_data wherever possible (pass ttl = 0 to disable caching)
        # eg
        # def get_bucket(ttl):
        #   @cache_data(ttl=ttl)
        #   def _get_bucket():
        #       return self.client.storage.get_bucket
        #   return _get_bucket
        # REF : https://discuss.streamlit.io/t/connections-hackathon/47574/24?u=siddhantsadangi
        # REF : https://github.com/streamlit/files-connection/blob/main/st_files_connection/connection.py#L136
        self.table = self.client.table
        self.get_bucket = self.client.storage.get_bucket
        self.list_buckets = self.client.storage.list_buckets
        self.delete_bucket = self.client.storage.delete_bucket
        self.empty_bucket = self.client.storage.empty_bucket

    def create_bucket(
        self,
        id: str,
        name: Optional[str] = None,
        public: Optional[bool] = False,
        file_size_limit: Optional[int] = None,
        allowed_mime_types: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """
        Creates a new storage bucket.

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
        file: BytesIO,
        destination_path: str,
    ) -> dict[str, str]:
        """
        Uploads a file to a Supabase bucket.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        file : BytesIO
            File to upload. This BytesIO object returned by `st.file_uploader()`.
        destination_path : str
            Path is the bucket where the file will be uploaded to. Folders will be created as needed.
        """
        with open(file.name, "wb") as f:
            f.write(file.getbuffer())
        with open(file.name, "rb") as f:
            response = self.client.storage.from_(bucket_id).upload(
                destination_path,
                f,
                file_options={"content-type": file.type},
            )
        return response.json()

    def download(
        self,
        bucket_id: str,
        source_path: str,
    ) -> Tuple[str, str, bytes]:
        """
        Downloads a file.

        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        source_path : str
            Path of the file relative in the bucket, including file name

        Returns
        -------
        file_name : str
            Name of the file, inferred from the `source_path`
        mime : str
            MIME-type of the object
        data : bytes
            Downloaded bytes object
        """
        import mimetypes

        file_name = source_path.split("/")[-1]

        with open(file_name, "wb+") as f:
            response = self.client.storage.from_(bucket_id).download(source_path)
            f.write(response)

        mime = mimetypes.guess_type(file_name)[0]
        data = open(file_name, "rb")

        return file_name, mime, data

    def update_bucket(
        self,
        bucket_id: str,
        public: Optional[bool] = False,
        file_size_limit: Optional[bool] = None,
        allowed_mime_types: Optional[Union[str, list[str]]] = None,
    ) -> dict[str, str]:
        """
        Update a storage bucket.

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

    def move(self, bucket_id: str, from_path: str, to_path: str) -> dict[str, str]:
        """
        Moves an existing file, optionally renaming it at the same time.

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

    def remove(self, bucket_id: str, paths: list) -> dict[str, str]:
        """
        Deletes files within the same bucket

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
    ) -> list[dict[str, str]]:
        """
        Lists all the objects within a bucket.

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
        """
        return self.client.storage.from_(bucket_id).list(
            path,
            dict(
                limit=limit,
                offset=offset,
                sortBy=dict(column=sortby, order=order),
            ),
        )

    def create_signed_urls(
        self,
        bucket_id: str,
        paths: list[str],
        expires_in: int,
    ) -> list[dict[str, str]]:
        """
        Parameters
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
    ) -> str:
        """
        Parameters
        ----------
        bucket_id : str
            Unique identifier of the bucket.
        filepath : str
            File path to be downloaded, including the current file name.
        """

        return self.client.storage.from_(bucket_id).get_public_url(filepath)
