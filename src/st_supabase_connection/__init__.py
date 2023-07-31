import os
from io import BytesIO
from typing import Optional, Union

from streamlit.connections import ExperimentalBaseConnection
from supabase import Client, create_client

# TODO: Update demo app
# TODO: Update README (highlight benefits 1. same methods as the supabase API 2. built on postgrest-py and storage3, the backend behnd the supaabse API
# 3. less code when using upload and download)
# TODO: Add docstrings and example usage

__version__ = "0.0.2"


class SupabaseConnection(ExperimentalBaseConnection[Client]):
    """Connects a streamlit app to Supabase

    Attributes
    ----------
    client : supabase.Client
        The supabase client initialized with the supabase URL and key
    storage : supabase.SupabaseStorageClient
        The supabase storage client initialized with the supabase URL and key

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
        """Creates a new storage bucket.

        Parameters
        ----------
        id : str
            A unique identifier for the bucket you are creating.
        name : str
            A name for the bucket you are creating. If not passed, the id is used as the name as well.
        public :bool
            Whether the bucket you are creating should be publicly accessible. Defaults to False.
        file_size_limit : int
            The maximum size (in bytes) of files that can be uploaded to this bucket. Pass None to have no limits. Defaults to None.
        allowed_mime_types : list[str]
            The list of file types that can be uploaded to this bucket. Pass none to allow all file types. Defaults to None.
        """
        res = self.client.storage._request(
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
        return res.json()

    def upload(
        self,
        bucket_id: str,
        file: BytesIO,
        destination_path: str,
    ) -> dict[str, str]:
        """Uploads a file to a Supabase bucket.

        Parameters
        ----------
        bucket_id : str
            The unique identifier of the bucket.
        file : BytesIO
            The file to upload. This BytesIO object returned by `st.file_uploader()`.
        destination_path : str
            The path is the bucket where the file will be uploaded to. Folders will be created as needed.
        """
        with open(file.name, "wb") as f:
            f.write(file.getbuffer())
        with open(file.name, "rb") as f:
            res = self.client.storage.from_(bucket_id).upload(
                destination_path,
                f,
                file_options={"content-type": file.type},
            )
        return res.json()

    def download(
        self,
        bucket_id: str,
        source_path: str,
    ) -> Union[str, bytes]:
        """Downloads a file.

        Parameters
        ----------
        bucket_id : str
            The unique identifier of the bucket.
        source_path : str
            The path of the file relative in the bucket, including file name

        Returns
        -------
        file_name : str
            Name of the file, inferred from the `source_path`
        mime : str
            The MIME-type of the object
        data : bytes
            The downloaded bytes object
        """
        import mimetypes

        file_name = source_path.split("/")[-1]

        with open(file_name, "wb+") as f:
            res = self.client.storage.from_(bucket_id).download(source_path)
            f.write(res)

        mime = mimetypes.guess_type(file_name)[0]
        data = open(file_name, "rb")

        return file_name, mime, data

    def update_bucket(
        self, id: str, **options: dict[Union[bool, int, list[str]]]
    ) -> dict[str, str]:
        """Update a storage bucket.

        Parameters
        ----------
        id :
            The unique identifier of the bucket you would like to update.
        options
            The properties you want to update. Valid options are `public (bool)`, `file_size_limit (int)` and
            `allowed_mime_types (str)`.
        """
        json = {"id": id, "name": id, **options}
        res = self.client.storage._request("PUT", f"/bucket/{id}", json=json)
        return res.json()
