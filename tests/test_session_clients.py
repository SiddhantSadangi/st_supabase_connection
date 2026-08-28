import base64
import json
import unittest

from demo.session_clients import (
    custom_connection_name,
    resolve_connection_credentials,
    validate_email_address,
    validate_password_sign_in,
    validate_project_url,
    validate_public_api_key,
    validate_sign_up,
)


class SessionClientTests(unittest.TestCase):
    def test_resolves_nested_connection_secrets_with_publishable_alias(self):
        secrets = {
            "connections": {
                "supabase": {
                    "SUPABASE_URL": " https://demo.supabase.co ",
                    "SUPABASE_PUBLISHABLE_KEY": " sb_publishable_example ",
                }
            }
        }

        self.assertEqual(
            resolve_connection_credentials(secrets, {}),
            ("https://demo.supabase.co", "sb_publishable_example"),
        )

    def test_resolves_environment_credentials(self):
        environ = {
            "SUPABASE_URL": "https://environment.supabase.co",
            "SUPABASE_KEY": "environment-key",
        }

        self.assertEqual(
            resolve_connection_credentials({}, environ),
            ("https://environment.supabase.co", "environment-key"),
        )

    def test_publishable_alias_takes_precedence_over_legacy_key_name(self):
        secrets = {
            "connections": {
                "supabase": {
                    "SUPABASE_URL": "https://demo.supabase.co",
                    "SUPABASE_KEY": "legacy-key",
                    "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_example",
                }
            }
        }

        self.assertEqual(
            resolve_connection_credentials(secrets, {}),
            ("https://demo.supabase.co", "sb_publishable_example"),
        )

    def test_missing_credentials_raise_without_exposing_values(self):
        with self.assertRaisesRegex(ConnectionRefusedError, "Supabase URL and key not provided"):
            resolve_connection_credentials({}, {})

    def test_custom_connection_names_are_stable_and_session_specific(self):
        first_state = {}
        second_state = {}

        first_name = custom_connection_name(
            first_state, url="https://demo.supabase.co", key="key-one"
        )
        same_name = custom_connection_name(
            first_state, url="https://demo.supabase.co", key="key-one"
        )
        second_session_name = custom_connection_name(
            second_state, url="https://demo.supabase.co", key="key-one"
        )
        changed_config_name = custom_connection_name(
            first_state, url="https://demo.supabase.co", key="key-two"
        )

        self.assertEqual(first_name, same_name)
        self.assertNotEqual(first_name, second_session_name)
        self.assertNotEqual(first_name, changed_config_name)
        self.assertNotIn("key-one", first_name)

    def test_auth_form_validation(self):
        self.assertEqual(validate_email_address(""), "Enter an email address.")
        self.assertEqual(
            validate_email_address("not-an-email"),
            "Enter a valid email address.",
        )
        self.assertIsNone(validate_email_address("person@example.com"))

        self.assertEqual(validate_sign_up("", "123456"), "Enter an email address.")
        self.assertEqual(
            validate_sign_up("not-an-email", "123456"),
            "Enter a valid email address.",
        )
        self.assertEqual(
            validate_sign_up("person@example.com", "short"),
            "Password must contain at least 6 characters.",
        )
        self.assertIsNone(validate_sign_up("person@example.com", "123456"))

        self.assertEqual(
            validate_password_sign_in("", "123456"),
            "Enter an email address or phone number.",
        )
        self.assertEqual(
            validate_password_sign_in("invalid@", "123456"),
            "Enter a valid email address.",
        )
        self.assertIsNone(validate_password_sign_in("+353871234567", "123456"))

    def test_project_url_validation_requires_https_except_for_local_hosts(self):
        self.assertEqual(validate_project_url(""), "Enter your Supabase project URL.")
        self.assertIsNone(validate_project_url("https://demo.supabase.co"))
        self.assertIsNone(validate_project_url("http://127.0.0.1:54321"))
        self.assertEqual(
            validate_project_url("http://demo.supabase.co"),
            "Hosted Supabase projects must use HTTPS.",
        )

    def test_public_key_validation_accepts_only_public_credentials(self):
        self.assertIsNone(validate_public_api_key("sb_publishable_example"))
        self.assertEqual(
            validate_public_api_key("sb_secret_example"),
            "Secret keys are not accepted. Use an sb_publishable_ key instead.",
        )
        self.assertIsNone(validate_public_api_key(self._legacy_key("anon")))
        self.assertEqual(
            validate_public_api_key(self._legacy_key("service_role")),
            "Service-role keys are not accepted. Use a publishable key instead.",
        )

    @staticmethod
    def _legacy_key(role):
        payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
        return f"header.{payload}.signature"


if __name__ == "__main__":
    unittest.main()
