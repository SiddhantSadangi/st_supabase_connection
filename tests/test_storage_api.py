import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from st_supabase_connection import (
    SupabaseConnection,
    _normalize_storage_path,
    _prepare_upload_payload,
)


class UploadedBytes(BytesIO):
    def __init__(self, value: bytes, *, name: str, content_type: str):
        super().__init__(value)
        self.name = name
        self.type = content_type


class StorageApiTests(unittest.TestCase):
    def setUp(self):
        self.bucket = MagicMock()
        self.storage = MagicMock()
        self.storage.from_.return_value = self.bucket
        self.connection = object.__new__(SupabaseConnection)
        self.connection._url = "https://project.example"
        self.connection._key = "test-key"
        self.connection.client = SimpleNamespace(
            storage=self.storage, options=SimpleNamespace(headers={})
        )

    def test_storage_path_normalization_rejects_bucket_root(self):
        self.assertEqual(_normalize_storage_path("/folder/file.txt"), "folder/file.txt")
        for invalid in ("", "/", "///"):
            with (
                self.subTest(path=invalid),
                self.assertRaisesRegex(ValueError, "must not be empty"),
            ):
                _normalize_storage_path(invalid)

    def test_browser_upload_streams_bytes_without_creating_a_server_file(self):
        unique_name = f"upload-{uuid.uuid4().hex}.png"
        uploaded = UploadedBytes(
            b"image-bytes",
            name=unique_name,
            content_type="image/png",
        )
        expected = {"path": "images/photo.png"}
        self.bucket.upload.return_value = expected

        result = self.connection.upload(
            "media",
            "local",
            uploaded,
            "/images/photo.png",
            "true",
        )

        self.assertEqual(result, expected)
        self.storage.from_.assert_called_once_with("media")
        self.assertEqual(
            self.bucket.upload.call_args.kwargs,
            {
                "path": "images/photo.png",
                "file": b"image-bytes",
                "file_options": {
                    "content-type": "image/png",
                    "x-upsert": "true",
                },
            },
        )
        self.assertFalse(Path(unique_name).exists())

    def test_hosted_upload_closes_its_file_handle(self):
        captured = {}

        def upload(**kwargs):
            captured["file"] = kwargs["file"]
            self.assertFalse(kwargs["file"].closed)
            return {"path": kwargs["path"]}

        self.bucket.upload.side_effect = upload
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.pdf"
            source.write_bytes(b"pdf-bytes")
            result = self.connection.upload("documents", "hosted", source, "")

        self.assertEqual(result, {"path": "report.pdf"})
        self.assertTrue(captured["file"].closed)
        self.assertEqual(
            self.bucket.upload.call_args.kwargs["file_options"],
            {"content-type": "application/pdf", "x-upsert": "false"},
        )

    def test_upload_rejects_unknown_source_before_calling_storage(self):
        with self.assertRaisesRegex(ValueError, "source must be"):
            self.connection.upload("media", "remote", BytesIO(b"data"), "file.bin")
        self.storage.from_.assert_not_called()

    def test_signed_url_methods_normalize_paths_and_preserve_response_fields(self):
        self.bucket.create_signed_urls.return_value = [{"signedURL": "https://signed"}]
        self.bucket.create_signed_upload_url.return_value = {
            "signed_url": "https://upload",
            "token": "token",
            "path": "folder/file.png",
        }

        downloads = self.connection.create_signed_urls("media", ["/one.png", "folder/two.png"], 600)
        upload = self.connection.create_signed_upload_url("media", "/folder/file.png")

        self.assertEqual(downloads, [{"signedURL": "https://signed"}])
        self.bucket.create_signed_urls.assert_called_once_with(["one.png", "folder/two.png"], 600)
        self.assertEqual(
            upload,
            {
                "signed_url": "https://upload",
                "token": "token",
                "path": "folder/file.png",
            },
        )
        self.bucket.create_signed_upload_url.assert_called_once_with("folder/file.png")

    def test_upload_to_signed_url_sets_content_type_and_maps_response(self):
        self.bucket.upload_to_signed_url.return_value = SimpleNamespace(
            path="folder/report.pdf",
            full_path="media/folder/report.pdf",
            fullPath="media/folder/report.pdf",
        )

        result = self.connection.upload_to_signed_url(
            "media",
            "/folder/report.pdf",
            "signed-token",
            b"pdf-bytes",
        )

        self.assertEqual(
            result,
            {
                "path": "folder/report.pdf",
                "full_path": "media/folder/report.pdf",
                "fullPath": "media/folder/report.pdf",
            },
        )
        self.assertEqual(
            self.bucket.upload_to_signed_url.call_args.args,
            ("folder/report.pdf", "signed-token", b"pdf-bytes"),
        )
        self.assertEqual(
            self.bucket.upload_to_signed_url.call_args.kwargs,
            {"file_options": {"content-type": "application/pdf"}},
        )

    def test_upload_payload_cleanup_runs_when_signed_upload_fails(self):
        captured = {}

        def fail(_path, _token, payload, **_kwargs):
            captured["payload"] = payload
            raise RuntimeError("upload failed")

        self.bucket.upload_to_signed_url.side_effect = fail
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "data.bin"
            source.write_bytes(b"payload")
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                self.connection.upload_to_signed_url("media", "data.bin", "token", source)

        self.assertTrue(captured["payload"].closed)

    def test_prepare_upload_payload_uses_binary_fallback_content_type(self):
        payload, content_type, cleanup = _prepare_upload_payload(b"data", "unknown.extensionless")

        self.assertEqual(payload, b"data")
        self.assertEqual(content_type, "application/octet-stream")
        self.assertIsNone(cleanup)


if __name__ == "__main__":
    unittest.main()
