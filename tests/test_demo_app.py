import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "demo" / "app.py"
DEMO_REQUIREMENTS_PATH = APP_PATH.with_name("requirements.txt")


class FakeAuth:
    def __init__(self):
        self.session = None
        self.password_requests = []

    def get_session(self):
        return self.session

    def sign_in_with_password(self, request):
        self.password_requests.append(request)
        user = SimpleNamespace(id="user-1", email=request.get("email"))
        self.session = SimpleNamespace(user=user)
        return SimpleNamespace(user=user, session=self.session)

    def sign_out(self):
        self.session = None


class FakeQuery:
    def select(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self


class FakeSessionClient:
    def __init__(self):
        self.auth = FakeAuth()
        self.storage = FakeStorage()

    def table(self, _table):
        return FakeQuery()


class FakeStorage:
    def __init__(self):
        self.list_buckets_calls = 0
        self.bucket_settings = {
            "bucket-a": {
                "file_size_limit": 1024,
                "allowed_mime_types": ["image/png"],
                "public": True,
            }
        }

    def list_buckets(self):
        self.list_buckets_calls += 1
        return [{"id": "bucket1", "name": "bucket1", "public": True}]

    def get_bucket(self, bucket_id):
        return self.bucket_settings[bucket_id]


class FakeConnection:
    def __init__(self):
        self.session = FakeSessionClient()

    def session_client(self):
        return self.session

    def list_buckets(self, ttl=None):
        raise AssertionError("Storage must use the session-scoped client")


class DemoAppTests(unittest.TestCase):
    def test_demo_installs_the_checked_out_library(self):
        requirements = {
            line.strip()
            for line in DEMO_REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertIn("-e .", requirements)
        self.assertFalse(
            any(
                line.startswith(("st_supabase_connection", "st-supabase-connection"))
                for line in requirements
            )
        )

    def assert_no_exceptions(self, app):
        self.assertEqual([str(item.value) for item in app.exception], [])

    def connected_app(self, *, project="demo", workspace="Storage"):
        connection = FakeConnection()
        app = AppTest.from_file(str(APP_PATH), default_timeout=15)
        initial_state = {
            "client": connection,
            "initialized": True,
            "project": project,
            "project_label": ("Demo project" if project == "demo" else "test-project.supabase.co"),
            "project_url": "https://test-project.supabase.co",
            "connection_code": "st_supabase = st.connection(...)\n",
            "workspace": workspace,
        }
        for key, value in initial_state.items():
            app.session_state[key] = value
        app.run()
        self.assert_no_exceptions(app)
        return app, connection

    def test_landing_page_and_secret_key_rejection(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=15)
        app.run()

        self.assert_no_exceptions(app)
        self.assertEqual(app.header[0].value, "Connect a project")
        self.assertFalse(app.button(key="connect_demo").disabled)
        self.assertFalse(any(button.label == "Clear cached results" for button in app.button))

        app.segmented_control(key="connection_source").set_value("Own project").run()
        app.text_input(key="connect_custom_url").set_value("https://test-project.supabase.co")
        app.text_input(key="connect_custom_key").set_value("sb_secret_example")
        next(button for button in app.button if button.label == "Connect project").click().run()

        self.assert_no_exceptions(app)
        self.assertEqual(
            [item.value for item in app.error],
            ["Secret keys are not accepted. Use an sb_publishable_ key instead."],
        )

        app.segmented_control(key="connection_source").set_value("Demo project").run()
        self.assertEqual([item.value for item in app.error], [])

    def test_demo_storage_read_renders_normalized_result(self):
        app, connection = self.connected_app()

        app.button(key="storage_run_read").click().run()

        self.assert_no_exceptions(app)
        self.assertEqual([item.value for item in app.success], ["Retrieved 1 bucket"])
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(app.dataframe[0].value.shape, (1, 3))
        self.assertEqual(connection.session.storage.list_buckets_calls, 1)

    def test_demo_storage_tasks_use_seeded_choices_without_initial_errors(self):
        app, _connection = self.connected_app()

        for task in (
            "Retrieve bucket",
            "List files",
            "Download file",
            "Get public URL",
            "Create signed download URLs",
        ):
            app.selectbox(key="storage_operation_read").set_value(task).run()

            self.assert_no_exceptions(app)
            self.assertEqual([item.value for item in app.error], [])
            self.assertFalse(app.button(key="storage_run_read").disabled)

        app.selectbox(key="storage_create_signed_urls_bucket").set_value("bucket2").run()
        self.assertEqual(
            app.multiselect(key="storage_signed_paths").value,
            ["folder1/folder2/lenna.png"],
        )

    def test_database_read_supports_counted_table_and_json_results(self):
        app, _connection = self.connected_app(workspace="Database")
        response = SimpleNamespace(
            data=[{"name": "Ireland"}, {"name": "Japan"}],
            count=2,
        )

        app.selectbox(key="database_count").set_value("Exact").run()
        with patch.object(
            sys.modules["database_workspace"],
            "execute_query",
            return_value=response,
        ):
            app.button(key="database_run_read").click().run()

        self.assert_no_exceptions(app)
        self.assertEqual([item.value for item in app.success], ["Retrieved 2 rows"])
        self.assertIn(
            "Total matching rows: 2.",
            [item.value for item in app.caption],
        )
        self.assertEqual(app.dataframe[0].value.shape, (2, 1))

        app.segmented_control(key="database_result_format").set_value("JSON").run()
        with patch.object(
            sys.modules["database_workspace"],
            "execute_query",
            return_value=response,
        ):
            app.button(key="database_run_read").click().run()

        self.assert_no_exceptions(app)
        self.assertEqual(len(app.json), 1)
        self.assertEqual(len(app.dataframe), 0)

    def test_database_result_is_cleared_when_query_inputs_change(self):
        app, _connection = self.connected_app(workspace="Database")
        response = SimpleNamespace(data=[{"name": "Ireland"}], count=1)

        with patch.object(
            sys.modules["database_workspace"],
            "execute_query",
            return_value=response,
        ):
            app.button(key="database_run_read").click().run()

        self.assertEqual([item.value for item in app.success], ["Retrieved 1 row"])
        app.selectbox(key="database_demo_table").set_value("cities").run()
        self.assertEqual([item.value for item in app.success], [])
        self.assertEqual(len(app.dataframe), 0)

    def test_database_ordering_requires_a_column_when_enabled(self):
        app, _connection = self.connected_app(workspace="Database")

        app.toggle(key="database_use_order").set_value(True).run()

        self.assert_no_exceptions(app)
        self.assertTrue(app.button(key="database_run_read").disabled)
        self.assertIn(
            "Enter a column to order by.",
            [item.value for item in app.error],
        )

    def test_demo_auth_is_sign_in_only_and_uses_the_session_client(self):
        app, connection = self.connected_app(workspace="Authentication")

        self.assertFalse(any(control.key == "auth_mode" for control in app.segmented_control))
        self.assertIn("Sign in", [item.value for item in app.subheader])
        self.assertFalse(any(button.label == "Review account creation" for button in app.button))
        self.assertFalse(any(button.label == "Send one-time code" for button in app.button))

        app.text_input(key="auth_signin_identifier").set_value("user@example.com")
        app.text_input(key="auth_signin_password").set_value("password123")
        app.run()
        sign_in = next(button for button in app.button if button.label == "Sign in")
        self.assertFalse(sign_in.disabled)
        sign_in.click().run()

        self.assert_no_exceptions(app)
        self.assertTrue(any(button.label == "Sign out" for button in app.button))
        self.assertEqual(
            connection.session.auth.password_requests,
            [{"email": "user@example.com", "password": "password123"}],
        )
        self.assertNotIn("auth_signin_password", app.session_state)

    def test_custom_storage_write_requires_review_and_typed_confirmation(self):
        app, _connection = self.connected_app(project="custom")

        app.segmented_control(key="storage_risk").set_value("Write").run()
        app.selectbox(key="storage_operation_write").set_value("Create bucket").run()
        self.assertTrue(app.button(key="storage_review_write").disabled)

        app.text_input(key="storage_create_bucket_bucket").set_value("preview-bucket").run()
        self.assertFalse(app.button(key="storage_review_write").disabled)
        app.button(key="storage_review_write").click().run()

        self.assert_no_exceptions(app)
        self.assertEqual(
            app.text_input(key="_ux_confirmation_phrase").label,
            "Type RUN to confirm",
        )
        self.assertTrue(app.button(key="_ux_confirm_operation").disabled)

    def test_storage_update_settings_reset_when_bucket_changes(self):
        app, _connection = self.connected_app(project="custom")

        app.segmented_control(key="storage_risk").set_value("Write").run()
        app.selectbox(key="storage_operation_write").set_value("Update bucket").run()
        app.text_input(key="storage_update_bucket_bucket").set_value("bucket-a").run()
        app.button(key="storage_load_bucket").click().run()

        self.assertEqual(app.number_input(key="storage_update_size").value, 1024)
        self.assertTrue(app.checkbox(key="storage_update_public").value)
        self.assertEqual(app.multiselect(key="storage_update_mime").value, ["image/png"])

        app.text_input(key="storage_update_bucket_bucket").set_value("bucket-b").run()

        self.assert_no_exceptions(app)
        self.assertEqual(app.number_input(key="storage_update_size").value, 0)
        self.assertFalse(app.checkbox(key="storage_update_public").value)
        self.assertEqual(app.multiselect(key="storage_update_mime").value, [])

    def test_custom_database_delete_requires_a_filter(self):
        app, _connection = self.connected_app(project="custom", workspace="Database")

        app.segmented_control(key="database_risk").set_value("Destructive").run()
        app.text_input(key="database_custom_table").set_value("countries").run()

        self.assert_no_exceptions(app)
        self.assertTrue(app.button(key="database_review_destructive").disabled)
        self.assertIn(
            "At least one filter is required for this operation.",
            [item.value for item in app.caption],
        )

    def test_custom_auth_actions_start_disabled(self):
        app, _connection = self.connected_app(project="custom", workspace="Authentication")

        app.segmented_control(key="auth_mode").set_value("Create account").run()
        create = next(button for button in app.button if button.label == "Review account creation")
        self.assertTrue(create.disabled)

        app.segmented_control(key="auth_mode").set_value("Email OTP").run()
        send = next(button for button in app.button if button.label == "Send one-time code")
        self.assertTrue(send.disabled)
        self.assertFalse(any(button.label == "Clear cached results" for button in app.button))


if __name__ == "__main__":
    unittest.main()
