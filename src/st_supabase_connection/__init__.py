import os

from postgrest import SyncRequestBuilder, SyncSelectRequestBuilder
from streamlit import cache_resource
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
        The supabase storage client initialized with the supabase URL and key.
    """

    def _connect(self, **kwargs) -> None:
        @cache_resource
        def __connect(_self, **kwargs) -> None:
            if "url" in kwargs:
                url = kwargs.pop("url")
            elif "SUPABASE_URL" in _self._secrets:
                url = _self._secrets["SUPABASE_URL"]
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
            elif "SUPABASE_KEY" in _self._secrets:
                key = _self._secrets["SUPABASE_KEY"]
            elif "SUPABASE_KEY" in os.environ:
                key = os.environ.get("SUPABASE_KEY")
            else:
                raise ConnectionRefusedError(
                    "Supabase Key not provided. "
                    "You can provide the key by "
                    "passing it as the 'key' kwarg while creating the connection, or "
                    "setting the 'SUPABASE_KEY' Streamlit secret or environment variable."
                )

            _self.client = create_client(url, key)
            _self.storage = _self.client.storage

        return __connect(self, **kwargs)

    def table(
        self,
        table: str,
    ) -> SyncRequestBuilder:
        """
        The name of the table to query.

        Parameters
        ----------
        table : str
            The table name

        Returns
        -------
        SyncRequestBuilder : class
            A class that can be used to make requests to the table's content.
        """
        return self.client.table(table)
