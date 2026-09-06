import ast
import sys
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

DEMO_PATH = Path(__file__).parents[1] / "demo"
sys.path.insert(0, str(DEMO_PATH))

import storage_workspace

from demo.session_storage import SessionStorage


class UploadedFile(BytesIO):
    name = "avatar.png"
    type = "image/png"


class SessionStorageTests(unittest.TestCase):
    def setUp(self):
        self.storage_api = MagicMock()
        self.bucket_api = MagicMock()
        self.storage_api.from_.return_value = self.bucket_api
        self.storage = SessionStorage(SimpleNamespace(storage=self.storage_api))

    def test_bucket_options_are_forwarded_to_session_storage_api(self):
        self.storage.create_bucket(
            "private",
            public=False,
            file_size_limit=None,
            allowed_mime_types=["image/png"],
        )
        self.storage.update_bucket(
            "private",
            public=True,
            file_size_limit=1024,
            allowed_mime_types=None,
        )

        self.storage_api.create_bucket.assert_called_once_with(
            "private",
            options={
                "public": False,
                "file_size_limit": None,
                "allowed_mime_types": ["image/png"],
            },
        )
        self.storage_api.update_bucket.assert_called_once_with(
            "private",
            options={
                "public": True,
                "file_size_limit": 1024,
                "allowed_mime_types": None,
            },
        )

    def test_object_operations_use_bound_bucket_api(self):
        uploaded = UploadedFile(b"image-bytes")
        self.bucket_api.download.return_value = b"downloaded"

        self.storage.upload("private", uploaded, "/folder/avatar.png", overwrite=True)
        self.storage.move("private", "/folder/avatar.png", "/archive/avatar.png")
        self.storage.remove("private", ["/archive/avatar.png"])
        self.storage.list_objects(
            "private",
            path="/archive/",
            limit=25,
            offset=5,
            sortby="updated_at",
            order="desc",
        )
        downloaded = self.storage.download("private", "/archive/avatar.png")
        self.storage.get_public_url("private", "/archive/avatar.png")
        self.storage.create_signed_urls("private", ["/archive/avatar.png"], 300)
        self.storage.create_signed_upload_url("private", "/incoming/avatar.png")
        self.storage.upload_to_signed_url(
            "private",
            "/incoming/avatar.png",
            "signed-token",
            uploaded,
        )

        self.assertTrue(
            all(call.args == ("private",) for call in self.storage_api.from_.call_args_list)
        )
        self.bucket_api.upload.assert_called_once_with(
            path="folder/avatar.png",
            file=b"image-bytes",
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        self.bucket_api.move.assert_called_once_with(
            "folder/avatar.png",
            "archive/avatar.png",
        )
        self.bucket_api.remove.assert_called_once_with(["archive/avatar.png"])
        self.bucket_api.list.assert_called_once_with(
            "archive",
            {
                "limit": 25,
                "offset": 5,
                "sortBy": {"column": "updated_at", "order": "desc"},
            },
        )
        self.assertEqual(downloaded, ("avatar.png", "image/png", b"downloaded"))
        self.bucket_api.get_public_url.assert_called_once_with("archive/avatar.png")
        self.bucket_api.create_signed_urls.assert_called_once_with(["archive/avatar.png"], 300)
        self.bucket_api.create_signed_upload_url.assert_called_once_with("incoming/avatar.png")
        self.bucket_api.upload_to_signed_url.assert_called_once_with(
            "incoming/avatar.png",
            "signed-token",
            b"image-bytes",
            file_options={"content-type": "image/png"},
        )

    def test_paths_must_name_a_file(self):
        with self.assertRaisesRegex(ValueError, "including the file name"):
            self.storage.download("private", "/folder/")

    def test_all_generated_session_storage_examples_are_valid_python(self):
        cases = {
            "list_buckets": {},
            "get_bucket": {"bucket_id": "private"},
            "create_bucket": {
                "bucket_id": "private",
                "file_size_limit": 0,
                "allowed_mime_types": [],
                "public": False,
            },
            "update_bucket": {
                "bucket_id": "private",
                "file_size_limit": 0,
                "allowed_mime_types": [],
                "public": False,
            },
            "upload": {
                "bucket_id": "private",
                "destination_path": "/folder/avatar.png",
                "file": SimpleNamespace(name="avatar.png"),
                "overwrite": True,
            },
            "move": {"bucket_id": "private", "from_path": "a", "to_path": "b"},
            "remove": {"bucket_id": "private", "paths": ["a"]},
            "list_objects": {
                "bucket_id": "private",
                "path": "",
                "limit": 100,
                "offset": 0,
                "sortby": "name",
                "order": "Ascending",
            },
            "download": {"bucket_id": "private", "source_path": "a"},
            "get_public_url": {"bucket_id": "private", "filepath": "a"},
            "create_signed_urls": {
                "bucket_id": "private",
                "paths": ["a"],
                "expires_in": 60,
            },
            "create_signed_upload_url": {"bucket_id": "private", "path": "a"},
            "upload_to_signed_url": {"bucket_id": "private", "path": "a"},
            "empty_bucket": {"bucket_id": "private"},
            "delete_bucket": {"bucket_id": "private"},
        }

        for operation, params in cases.items():
            with self.subTest(operation=operation):
                code = storage_workspace._render_code(operation, params)
                ast.parse(code)
                self.assertIn("st_supabase.session_client()", code)

    def test_signed_upload_requests_secret_cleanup_and_preserves_result_for_one_rerun(self):
        state = {}
        self.storage.upload_to_signed_url = MagicMock(return_value={"path": "avatar.png"})
        params = {
            "bucket_id": "private",
            "path": "avatar.png",
            "token": "signed-token",
            "file": UploadedFile(b"image-bytes"),
        }

        with (
            patch.object(storage_workspace.st, "session_state", state),
            patch.object(storage_workspace.st, "rerun") as rerun,
        ):
            storage_workspace._execute(
                self.storage,
                "upload_to_signed_url",
                params,
                "Upload with signed URL",
            )

        self.assertTrue(state[storage_workspace._PRESERVE_RESULT_ONCE_STATE_KEY])
        self.assertTrue(state["_clear_storage_secret_fields"])
        self.assertEqual(state["_ux_result_storage"]["status"], "success")
        rerun.assert_called_once_with()

        with (
            patch.object(storage_workspace.st, "session_state", state),
            patch.object(storage_workspace, "sync_result_context") as sync_context,
        ):
            storage_workspace._sync_storage_result_context("updated-action")
            sync_context.assert_not_called()
            storage_workspace._sync_storage_result_context("updated-action")
            sync_context.assert_called_once_with("storage", "updated-action")


if __name__ == "__main__":
    unittest.main()
