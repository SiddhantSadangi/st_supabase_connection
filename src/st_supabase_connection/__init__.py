import os

from streamlit.connections import ExperimentalBaseConnection
from supabase import Client, create_client

__version__ = "0.0.0"


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
        self.storage = self.client.storage
        self.table = self.client.table
