import unittest
from unittest.mock import patch

from demo import ui_helpers


class ActionFingerprintTests(unittest.TestCase):
    def test_auth_changes_discard_user_data_and_confirmations_but_not_auth_feedback(self):
        for next_user in (None, "user-two"):
            with (
                self.subTest(next_user=next_user),
                patch.object(ui_helpers.st, "session_state", {}),
            ):
                ui_helpers.sync_auth_context("user-one")
                private_keys = (
                    "_ux_result_database",
                    "_ux_result_storage",
                    "_ux_result_context_database",
                    "_ux_confirmation",
                    "_ux_confirmed_action",
                    "_ux_confirmation_phrase",
                    "_storage_preserve_result_once",
                    "storage_token_upload_token",
                )
                for key in private_keys:
                    ui_helpers.st.session_state[key] = "old-user-data"
                ui_helpers.st.session_state["_ux_result_auth"] = "latest-auth-feedback"
                ui_helpers.sync_auth_context("user-one")
                self.assertTrue(all(key in ui_helpers.st.session_state for key in private_keys))
                ui_helpers.sync_auth_context(next_user)
                self.assertTrue(all(key not in ui_helpers.st.session_state for key in private_keys))
                self.assertEqual(
                    ui_helpers.st.session_state["_ux_result_auth"], "latest-auth-feedback"
                )

    def test_fingerprint_is_stable_and_bound_to_session_scope_and_values(self):
        values = {"email": "user@example.com", "password": "password123"}
        with patch.object(ui_helpers.st, "session_state", {}):
            first = ui_helpers.action_fingerprint("auth:sign_up", values)
            self.assertEqual(first, ui_helpers.action_fingerprint("auth:sign_up", values))
            self.assertNotEqual(first, ui_helpers.action_fingerprint("auth:sign_in", values))
            self.assertNotEqual(
                first,
                ui_helpers.action_fingerprint("auth:sign_up", {**values, "password": "changed"}),
            )
        with patch.object(ui_helpers.st, "session_state", {}):
            self.assertNotEqual(first, ui_helpers.action_fingerprint("auth:sign_up", values))


if __name__ == "__main__":
    unittest.main()
