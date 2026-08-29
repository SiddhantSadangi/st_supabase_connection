import unittest
from types import SimpleNamespace
from unittest.mock import patch

import st_supabase_connection as connection_module
from st_supabase_connection import (
    SupabaseConnection,
    __version__,
    _get_or_create_session_client,
    _query_hash,
)


class SessionClientLibraryTests(unittest.TestCase):
    def test_version_is_2_2_0(self):
        self.assertEqual(__version__, "2.2.0")

    def test_session_client_is_reused_only_in_the_same_session(self):
        created = []

        def factory(url, key):
            client = object()
            created.append((url, key, client))
            return client

        first_state = {}
        second_state = {}
        first_client = _get_or_create_session_client(
            first_state,
            connection_name="supabase",
            url="https://demo.supabase.co",
            key="sb_publishable_example",
            client_factory=factory,
        )
        rerun_client = _get_or_create_session_client(
            first_state,
            connection_name="supabase",
            url="https://demo.supabase.co",
            key="sb_publishable_example",
            client_factory=factory,
        )
        second_session_client = _get_or_create_session_client(
            second_state,
            connection_name="supabase",
            url="https://demo.supabase.co",
            key="sb_publishable_example",
            client_factory=factory,
        )

        self.assertIs(first_client, rerun_client)
        self.assertIsNot(first_client, second_session_client)
        self.assertEqual(len(created), 2)
        self.assertNotIn("sb_publishable_example", " ".join(first_state))

    def test_session_client_changes_with_connection_or_credentials(self):
        state = {}
        factory = lambda _url, _key: object()

        first = _get_or_create_session_client(
            state,
            connection_name="first",
            url="https://demo.supabase.co",
            key="key-one",
            client_factory=factory,
        )
        changed_connection = _get_or_create_session_client(
            state,
            connection_name="second",
            url="https://demo.supabase.co",
            key="key-one",
            client_factory=factory,
        )
        changed_credentials = _get_or_create_session_client(
            state,
            connection_name="first",
            url="https://demo.supabase.co",
            key="key-two",
            client_factory=factory,
        )

        self.assertIsNot(first, changed_connection)
        self.assertIsNot(first, changed_credentials)

    def test_public_session_client_uses_streamlit_session_state(self):
        connection = object.__new__(SupabaseConnection)
        connection._connection_name = "supabase"
        connection._url = "https://demo.supabase.co"
        connection._key = "sb_publishable_example"
        state = {}
        created = []

        def factory(url, key):
            client = object()
            created.append((url, key, client))
            return client

        with (
            patch.object(connection_module, "session_state", state),
            patch.object(connection_module, "create_client", side_effect=factory),
        ):
            first = connection.session_client()
            rerun = connection.session_client()

        self.assertIs(first, rerun)
        self.assertEqual(len(created), 1)

    def test_shared_auth_property_is_deprecated(self):
        connection = object.__new__(SupabaseConnection)
        shared_auth = object()
        connection._shared_auth = shared_auth

        with self.assertWarns(DeprecationWarning):
            result = connection.auth

        self.assertIs(result, shared_auth)

    def test_cached_sign_in_is_deprecated_and_not_cached(self):
        calls = []

        class FakeAuth:
            def sign_in_with_password(self, credentials):
                calls.append(credentials)
                return {"call": len(calls)}

        connection = object.__new__(SupabaseConnection)
        connection.session_client = lambda: SimpleNamespace(auth=FakeAuth())

        with self.assertWarns(DeprecationWarning):
            first = connection.cached_sign_in_with_password(
                {"email": "person@example.com", "password": "password"}
            )
        with self.assertWarns(DeprecationWarning):
            second = connection.cached_sign_in_with_password(
                {"email": "person@example.com", "password": "password"}
            )

        self.assertEqual(first, {"call": 1})
        self.assertEqual(second, {"call": 2})

    def test_connect_accepts_publishable_key_secret(self):
        fake_client = SimpleNamespace(
            table=object(),
            auth=object(),
            storage=SimpleNamespace(delete_bucket=object(), empty_bucket=object()),
        )

        class ConnectionWithSecrets(SupabaseConnection):
            @property
            def _secrets(self):
                return {
                    "SUPABASE_URL": "https://demo.supabase.co",
                    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_example",
                }

        connection = object.__new__(ConnectionWithSecrets)
        with patch.object(connection_module, "create_client", return_value=fake_client) as create:
            connection._connect()

        create.assert_called_once_with("https://demo.supabase.co", "sb_publishable_example")
        self.assertEqual(connection._key, "sb_publishable_example")

    def test_connect_prefers_publishable_key_over_legacy_secret_name(self):
        fake_client = SimpleNamespace(
            table=object(),
            auth=object(),
            storage=SimpleNamespace(delete_bucket=object(), empty_bucket=object()),
        )

        class ConnectionWithSecrets(SupabaseConnection):
            @property
            def _secrets(self):
                return {
                    "SUPABASE_URL": "https://demo.supabase.co",
                    "SUPABASE_KEY": "legacy-key",
                    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_example",
                }

        connection = object.__new__(ConnectionWithSecrets)
        with patch.object(connection_module, "create_client", return_value=fake_client) as create:
            connection._connect()

        create.assert_called_once_with("https://demo.supabase.co", "sb_publishable_example")

    def test_query_hash_is_scoped_by_authorization_and_project(self):
        def query(
            authorization,
            base_url="https://demo.supabase.co/rest/v1/",
            headers=None,
        ):
            return SimpleNamespace(
                request=SimpleNamespace(
                    session=SimpleNamespace(base_url=base_url),
                    http_method="GET",
                    path="/countries",
                    params={"select": "*"},
                    json=None,
                    headers={"Authorization": authorization, **(headers or {})},
                )
            )

        first = _query_hash(query("Bearer user-one-token"))
        same = _query_hash(query("Bearer user-one-token"))
        second_user = _query_hash(query("Bearer user-two-token"))
        second_project = _query_hash(
            query(
                "Bearer user-one-token",
                base_url="https://other.supabase.co/rest/v1/",
            )
        )

        self.assertEqual(first, same)
        self.assertNotEqual(first, second_user)
        self.assertNotEqual(first, second_project)
        self.assertNotIn("user-one-token", first)
        self.assertNotIn("demo.supabase.co", first)

    def test_query_hash_includes_count_preference_and_api_key_scope(self):
        def query(headers):
            return SimpleNamespace(
                request=SimpleNamespace(
                    method="GET",
                    url="https://demo.supabase.co/rest/v1/countries",
                    path="/rest/v1/countries",
                    params={"select": "*"},
                    json=None,
                    headers=headers,
                )
            )

        basic = _query_hash(query({"Authorization": "Bearer token", "apikey": "public-one"}))
        counted = _query_hash(
            query(
                {
                    "Authorization": "Bearer token",
                    "apikey": "public-one",
                    "Prefer": "count=exact",
                }
            )
        )
        changed_key = _query_hash(query({"Authorization": "Bearer token", "apikey": "public-two"}))

        self.assertNotEqual(basic, counted)
        self.assertNotEqual(basic, changed_key)
        self.assertNotIn("public-one", basic)


if __name__ == "__main__":
    unittest.main()
