import unittest
from unittest.mock import MagicMock, patch

import st_supabase_connection as connection_module
from st_supabase_connection import SupabaseConnection


class SessionClientLibraryTests(unittest.TestCase):
    def test_session_client_reuse_is_scoped_to_session_connection_and_credentials(self):
        connection = object.__new__(SupabaseConnection)
        connection._connection_name = "supabase"
        connection._url = "https://demo.supabase.co"
        connection._key = "sb_publishable_example"
        state = {}

        with (
            patch.object(connection_module, "session_state", state),
            patch.object(
                connection_module, "create_client", side_effect=lambda *_: object()
            ) as create,
        ):
            first = connection.session_client()
            self.assertIs(connection.session_client(), first)
            create.assert_called_once_with(connection._url, connection._key)

            for attribute, value in (
                ("_connection_name", "other"),
                ("_url", "https://other.supabase.co"),
                ("_key", "sb_publishable_other"),
            ):
                with self.subTest(attribute=attribute), patch.object(connection, attribute, value):
                    changed = connection.session_client()
                    self.assertIsNot(changed, first)
                    self.assertIs(connection.session_client(), changed)

            with patch.object(connection_module, "session_state", {}):
                self.assertIsNot(connection.session_client(), first)
            self.assertIs(connection.session_client(), first)
            self.assertEqual(create.call_count, 5)

    def test_shared_auth_property_is_deprecated(self):
        connection = object.__new__(SupabaseConnection)
        connection._shared_auth = object()
        with self.assertWarns(DeprecationWarning):
            self.assertIs(connection.auth, connection._shared_auth)

    def test_cached_sign_in_is_deprecated_and_not_cached(self):
        connection = object.__new__(SupabaseConnection)
        client = MagicMock()
        client.auth.sign_in_with_password.side_effect = [{"call": 1}, {"call": 2}]
        connection.session_client = lambda: client
        credentials = {"email": "person@example.com", "password": "password"}

        for call in (1, 2):
            with self.assertWarns(DeprecationWarning):
                self.assertEqual(
                    connection.cached_sign_in_with_password(credentials, ttl=60), {"call": call}
                )
        self.assertEqual(client.auth.sign_in_with_password.call_count, 2)
        client.auth.sign_in_with_password.assert_called_with(credentials)

    def test_connect_prefers_publishable_secret_with_or_without_legacy_key(self):
        for legacy in ({}, {"SUPABASE_KEY": "legacy-key"}):
            secrets = {
                "SUPABASE_URL": "https://demo.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_example",
                **legacy,
            }
            with (
                self.subTest(legacy=bool(legacy)),
                patch.object(SupabaseConnection, "_secrets", secrets),
                patch.object(connection_module, "create_client") as create,
            ):
                connection = object.__new__(SupabaseConnection)
                connection._connect()
                create.assert_called_once_with("https://demo.supabase.co", "sb_publishable_example")


if __name__ == "__main__":
    unittest.main()
