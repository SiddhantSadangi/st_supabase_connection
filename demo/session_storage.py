"""Session-scoped Supabase Storage operations used by the demo workspace."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any


def _normalize_path(path: str) -> str:
    normalized = str(path).strip().lstrip("/")
    if not normalized or normalized.endswith("/"):
        raise ValueError("Enter a file path, including the file name.")
    return normalized


def _file_bytes(file: Any) -> bytes:
    if isinstance(file, bytes):
        return file
    if isinstance(file, (str, Path)):
        return Path(file).read_bytes()
    if hasattr(file, "getvalue"):
        return bytes(file.getvalue())
    if hasattr(file, "read"):
        position = file.tell() if hasattr(file, "tell") else None
        data = file.read()
        if position is not None and hasattr(file, "seek"):
            file.seek(position)
        return bytes(data)
    raise TypeError("The uploaded file must provide bytes or a readable binary stream.")


def _content_type(file: Any, filename: str) -> str:
    declared_type = getattr(file, "type", None)
    if isinstance(declared_type, str) and declared_type:
        return declared_type
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


class SessionStorage:
    """Use the Storage API carried by one browser session's Supabase client."""

    def __init__(self, supabase_client: Any) -> None:
        self._storage = supabase_client.storage

    def list_buckets(self) -> Any:
        return self._storage.list_buckets()

    def get_bucket(self, bucket_id: str) -> Any:
        return self._storage.get_bucket(bucket_id)

    def create_bucket(
        self,
        bucket_id: str,
        *,
        public: bool,
        file_size_limit: int | None,
        allowed_mime_types: list[str] | None,
    ) -> Any:
        return self._storage.create_bucket(
            bucket_id,
            options={
                "public": public,
                "file_size_limit": file_size_limit,
                "allowed_mime_types": allowed_mime_types,
            },
        )

    def update_bucket(
        self,
        bucket_id: str,
        *,
        public: bool,
        file_size_limit: int | None,
        allowed_mime_types: list[str] | None,
    ) -> Any:
        return self._storage.update_bucket(
            bucket_id,
            options={
                "public": public,
                "file_size_limit": file_size_limit,
                "allowed_mime_types": allowed_mime_types,
            },
        )

    def delete_bucket(self, bucket_id: str) -> Any:
        return self._storage.delete_bucket(bucket_id)

    def empty_bucket(self, bucket_id: str) -> Any:
        return self._storage.empty_bucket(bucket_id)

    def upload(
        self,
        bucket_id: str,
        file: Any,
        destination_path: str,
        *,
        overwrite: bool,
    ) -> Any:
        fallback_name = Path(getattr(file, "name", "upload.bin")).name
        target_path = _normalize_path(destination_path or fallback_name)
        return self._storage.from_(bucket_id).upload(
            path=target_path,
            file=_file_bytes(file),
            file_options={
                "content-type": _content_type(file, fallback_name),
                "upsert": "true" if overwrite else "false",
            },
        )

    def move(self, bucket_id: str, from_path: str, to_path: str) -> Any:
        return self._storage.from_(bucket_id).move(
            _normalize_path(from_path),
            _normalize_path(to_path),
        )

    def remove(self, bucket_id: str, paths: list[str]) -> Any:
        return self._storage.from_(bucket_id).remove([_normalize_path(path) for path in paths])

    def list_objects(
        self,
        bucket_id: str,
        *,
        path: str,
        limit: int,
        offset: int,
        sortby: str,
        order: str,
    ) -> Any:
        return self._storage.from_(bucket_id).list(
            path.strip().strip("/") or None,
            {
                "limit": limit,
                "offset": offset,
                "sortBy": {"column": sortby, "order": order},
            },
        )

    def download(self, bucket_id: str, source_path: str) -> tuple[str, str, bytes]:
        normalized_path = _normalize_path(source_path)
        file_name = normalized_path.rsplit("/", maxsplit=1)[-1]
        data = self._storage.from_(bucket_id).download(normalized_path)
        return file_name, _content_type(None, file_name), data

    def get_public_url(self, bucket_id: str, filepath: str) -> str:
        return self._storage.from_(bucket_id).get_public_url(_normalize_path(filepath))

    def create_signed_urls(self, bucket_id: str, paths: list[str], expires_in: int) -> Any:
        normalized_paths = [_normalize_path(path) for path in paths]
        return self._storage.from_(bucket_id).create_signed_urls(normalized_paths, expires_in)

    def create_signed_upload_url(self, bucket_id: str, path: str) -> Any:
        return self._storage.from_(bucket_id).create_signed_upload_url(_normalize_path(path))

    def upload_to_signed_url(
        self,
        bucket_id: str,
        path: str,
        token: str,
        file: Any,
    ) -> Any:
        normalized_path = _normalize_path(path)
        filename = normalized_path.rsplit("/", maxsplit=1)[-1]
        return self._storage.from_(bucket_id).upload_to_signed_url(
            normalized_path,
            token,
            _file_bytes(file),
            file_options={"content-type": _content_type(file, filename)},
        )
