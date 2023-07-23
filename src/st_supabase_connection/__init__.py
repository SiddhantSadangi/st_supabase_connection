import os
from datetime import timedelta
from typing import Tuple, Union

import pandas as pd
import streamlit as st
from streamlit import cache_data
from streamlit.connections import ExperimentalBaseConnection
from supabase import Client, PostgrestAPIError, create_client


class SupabaseConnection(ExperimentalBaseConnection[Client]):
    """Connects a Streamlit app to Supabase"""

    def _connect(self, **kwargs) -> None:
        if "url" in kwargs:
            url = kwargs.pop("url")
        elif "SUPABASE_URL" in self._secrets:
            url = self._secrets["SUPABASE_URL"]
        elif "SUPABASE_URL" in os.environ:
            url = os.environ.get("SUPABASE_URL")
        else:
            raise ValueError(
                """Supabase URL not provided.
You can provide the URL by:
- Passing it as the "url" kwarg while creating the connection
- Setting the "SUPABASE_URL" environment variable or Streamlit secret
"""
            )

        if "key" in kwargs:
            key = kwargs.pop("key")
        elif "SUPABASE_KEY" in self._secrets:
            key = self._secrets["SUPABASE_KEY"]
        elif "SUPABASE_KEY" in os.environ:
            key = os.environ.get("SUPABASE_KEY")
        else:
            raise ValueError(
                """Supabase Key not provided.
You can provide the key by:
- Passing it as the "key" kwarg while creating the connection
- Setting the "SUPABASE_KEY" environment variable or Streamlit secret
"""
            )
        self.client = create_client(url, key)

    def select(
        self,
        table_name: str,
        select_query: str,
        count_method: str = None,
        filter_string: str = None,
        ttl: Union[float, timedelta, str, None] = None,
    ) -> Tuple[pd.DataFrame, int]:
        """
        Select data from a table. This is a wrapper around the supabase.table().select().execute() method.
        Read more about the accepted `select` and `eq` strings in the [Supabase Python API reference](https://supabase.com/docs/reference/python/select)

        Args:
            table_name: Table to fetch data from
            select_query: Select clause for the query
            count_method (optional): Method used to get the number of rows
            filter_string (optional): Filtering condition for the query
            ttl (optional): The maximum time to keep an entry in the cache.

        Returns:
            data [list[dict|None]]: Rows returned by the query
            count [int|None]: Count of the rows returned
            >>> data, count = supabase.table(table_name).select(select_query, count=count_method).eq(filter_string).execute()
        """

        @cache_data(ttl=ttl)
        def _select(
            _self,
            table_name: str,
            select_query: str,
            count_method: str = None,
            filter_string: str = None,
        ) -> Tuple[pd.DataFrame, int]:
            if filter_string:
                data, count = (
                    _self.client.table(table_name)
                    .select(select_query, count=count_method)
                    .eq(filter_string)
                    .execute()
                )
            else:
                data, count = (
                    _self.client.table(table_name)
                    .select(select_query, count=count_method)
                    .execute()
                )

            # TODO: Handle joins
            return pd.DataFrame.from_dict(data[-1], orient="columns"), count[-1]

        return _select(self, table_name, select_query, count_method, filter_string)

    def insert(
        self, table_name: str, insert_rows: Union[dict, list[dict]]
    ) -> Tuple[list[Union[dict, None]], int]:
        """
        Insert data into a table. This is a wrapper around the supabase.table().insert().execute() method.
        Read more about the accepted `insert` string in the [Supabase Python API reference](https://supabase.com/docs/reference/python/insert)

        Args:
            table_name: Table to insert data to
            insert_rows: Values to insert. Pass an object to insert a single row or an array to insert multiple rows.

        Returns:
            APIResponse with the result of the query
            >>> supabase.table(table_name).insert(insert_rows).execute()
        """
        try:
            return self.client.table(table_name).insert(insert_rows).execute()
        except PostgrestAPIError as e:
            st.error(e.details, icon="❌")
