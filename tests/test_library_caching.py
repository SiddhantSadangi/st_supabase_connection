"""Exercise real Streamlit caches and real SDK builders with no network access."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from postgrest import SyncPostgrestClient
from streamlit import cache_data
from supabase import ClientOptions, create_client

import st_supabase_connection as connection_module
from st_supabase_connection import SupabaseConnection, execute_query


class LibraryCachingTests(unittest.TestCase):
    def setUp(self):
        cache_data.clear()
        self.addCleanup(cache_data.clear)

    def test_caches_evict_old_entries_without_changing_ttl_semantics(self):
        with patch.object(connection_module, "_MAX_CACHE_ENTRIES", 2):
            db, requests = self.database()
            for record_id in range(3):
                execute_query(db.table("records").select("*").eq("id", record_id))
            execute_query(db.table("records").select("*").eq("id", 2))
            self.assertEqual(len(requests), 3)
            execute_query(db.table("records").select("*").eq("id", 0))
            self.assertEqual(len(requests), 4)

            first, first_requests = self.storage_connection()
            self.storage_reads(first)
            for project in ("second", "third"):
                connection, _ = self.storage_connection(project)
                self.storage_reads(connection)
            self.storage_reads(connection)
            self.assertEqual(len(first_requests), 4)
            self.storage_reads(first)
            self.assertEqual(len(first_requests), 8)

    def storage_connection(self, project="first", key="sb_publishable_first"):
        requests = []

        def respond(request):
            requests.append(request)
            marker = (
                f"{project}:{request.headers.get('authorization')}:{request.headers.get('apikey')}"
            )
            bucket = {
                "id": "documents",
                "name": marker,
                "owner": "owner",
                "public": False,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "file_size_limit": None,
                "allowed_mime_types": None,
            }
            if request.method == "GET" and request.url.path.endswith("/bucket"):
                return httpx.Response(200, json=[bucket])
            if request.method == "GET" and "/bucket/" in request.url.path:
                return httpx.Response(200, json=bucket)
            if request.method == "GET":
                return httpx.Response(200, content=marker.encode())
            if "/object/list/" in request.url.path:
                return httpx.Response(200, json=[{"name": marker}])
            if request.method == "DELETE":
                return httpx.Response(200, json=[{"name": "file.txt"}])
            return httpx.Response(200, json={"message": "ok"})

        http = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(http.close)
        connection = object.__new__(SupabaseConnection)
        connection._url = f"https://{project}.example"
        connection._key = key
        connection.client = create_client(
            connection._url, key, options=ClientOptions(httpx_client=http)
        )
        return connection, requests

    def storage_reads(self, connection, ttl=None):
        return (
            connection.list_buckets(ttl=ttl),
            connection.get_bucket("documents", ttl=ttl),
            connection.download("documents", "file.txt", ttl=ttl),
            connection.list_objects(
                "documents",
                path="folder",
                limit=25,
                offset=5,
                sortby="updated_at",
                order="desc",
                ttl=ttl,
            ),
        )

    def test_storage_caches_reuse_reads_but_isolate_projects_and_keys(self):
        first, requests = self.storage_connection()
        original = self.storage_reads(first)
        self.assertEqual(self.storage_reads(first), original)
        self.assertEqual(len(requests), 4)

        self.assertEqual(original[2][:2], ("file.txt", "text/plain"))
        self.assertEqual(
            json.loads(requests[-1].content),
            {
                "prefix": "folder",
                "limit": 25,
                "offset": 5,
                "sortBy": {"column": "updated_at", "order": "desc"},
            },
        )

        for project, key in (
            ("second", "sb_publishable_first"),
            ("first", "sb_publishable_second"),
        ):
            with self.subTest(project=project, key=key):
                other, other_requests = self.storage_connection(project, key)
                results = self.storage_reads(other)
                self.assertEqual(len(other_requests), 4)
                for before, after in zip(original, results):
                    self.assertNotEqual(before, after)

    def test_storage_cache_tracks_sign_in_token_refresh_and_sign_out(self):
        connection, requests = self.storage_connection()
        anonymous = self.storage_reads(connection)
        previous = anonymous
        for event, token in (
            ("SIGNED_IN", "user-one"),
            ("TOKEN_REFRESHED", "user-one-refreshed"),
            ("SIGNED_IN", "user-two"),
        ):
            with self.subTest(event=event, token=token):
                # Simulate the SDK's auth notification without contacting Auth.
                connection.client._listen_to_auth_events(event, SimpleNamespace(access_token=token))
                before_count = len(requests)
                current = self.storage_reads(connection)
                self.assertEqual(len(requests), before_count + 4)
                for before, after in zip(previous, current):
                    self.assertNotEqual(before, after)
                previous = current
        connection.client._listen_to_auth_events("SIGNED_OUT", None)
        self.assertEqual(self.storage_reads(connection), anonymous)

    def test_storage_cache_returns_independent_models_and_lists(self):
        connection, requests = self.storage_connection()
        buckets, bucket, _, objects = self.storage_reads(connection)
        buckets[0].name = "modified"
        bucket.name = "modified"
        objects[0]["name"] = "modified"
        fresh_buckets, fresh_bucket, _, fresh_objects = self.storage_reads(connection)
        self.assertNotEqual(fresh_buckets[0].name, "modified")
        self.assertNotEqual(fresh_bucket.name, "modified")
        self.assertNotEqual(fresh_objects[0]["name"], "modified")
        self.assertEqual(len(requests), 4)

    def test_storage_cache_tracks_headers_changed_on_the_storage_client(self):
        connection, requests = self.storage_connection()
        original = self.storage_reads(connection)
        storage = connection.client.storage
        headers = getattr(storage, "_headers", None)
        if headers is None:
            headers = storage.headers
        headers["Authorization"] = "Bearer changed-storage-token"
        changed = self.storage_reads(connection)
        self.assertEqual(len(requests), 8)
        for before, after in zip(original, changed):
            self.assertNotEqual(before, after)

    def test_storage_zero_ttl_fetches_each_time(self):
        connection, requests = self.storage_connection()
        self.storage_reads(connection, ttl=0)
        self.storage_reads(connection, ttl=0)
        self.assertEqual(len(requests), 8)

    def test_public_urls_are_project_specific_and_accept_legacy_ttl(self):
        for project in ("first", "second"):
            connection, requests = self.storage_connection(project)
            url = connection.get_public_url("documents", "file.txt", ttl=60)
            self.assertEqual(
                url, f"https://{project}.example/storage/v1/object/public/documents/file.txt"
            )
            self.assertEqual(requests, [])

    def test_public_storage_mutations_preserve_http_payloads_and_responses(self):
        connection, requests = self.storage_connection()
        self.assertEqual(
            connection.create_bucket(
                "documents",
                name="Reports",
                public=True,
                file_size_limit=1024,
                allowed_mime_types=["image/png"],
            ),
            {"message": "ok"},
        )
        self.assertEqual(
            connection.update_bucket(
                "documents", file_size_limit=2048, allowed_mime_types="text/plain"
            ),
            {"message": "ok"},
        )
        self.assertEqual(
            connection.move("documents", "file.txt", "archive/file.txt"), {"message": "ok"}
        )
        self.assertEqual(connection.remove("documents", ["file.txt"]), [{"name": "file.txt"}])
        self.assertEqual(
            [(r.method, r.url.path, json.loads(r.content)) for r in requests],
            [
                (
                    "POST",
                    "/storage/v1/bucket",
                    {
                        "id": "documents",
                        "name": "Reports",
                        "public": True,
                        "file_size_limit": 1024,
                        "allowed_mime_types": ["image/png"],
                    },
                ),
                (
                    "PUT",
                    "/storage/v1/bucket/documents",
                    {
                        "id": "documents",
                        "name": "documents",
                        "public": False,
                        "file_size_limit": 2048,
                        "allowed_mime_types": ["text/plain"],
                    },
                ),
                (
                    "POST",
                    "/storage/v1/object/move",
                    {
                        "bucketId": "documents",
                        "sourceKey": "file.txt",
                        "destinationKey": "archive/file.txt",
                    },
                ),
                ("DELETE", "/storage/v1/object/documents", {"prefixes": ["file.txt"]}),
            ],
        )

    def database(self, project="first", token="first-user", key="public-key", schema="public"):
        requests = []

        def respond(request):
            requests.append(request)
            row = {
                "call": len(requests),
                "project": project,
                "token": request.headers.get("authorization"),
            }
            data = (
                row
                if request.headers.get("accept") == "application/vnd.pgrst.object+json"
                else [row]
            )
            return httpx.Response(200, json=data, headers={"content-range": "0-0/1"})

        http = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(http.close)
        db = SyncPostgrestClient(
            f"https://{project}.example/rest/v1/",
            http_client=http,
            schema=schema,
            headers={"Authorization": f"Bearer {token}", "apikey": key},
        )
        return db, requests

    def test_every_write_and_post_rpc_executes_even_with_a_cache_ttl(self):
        db, requests = self.database()
        builders = (
            lambda: db.table("records").insert({"name": "same"}),
            lambda: db.table("records").upsert({"id": 1}),
            lambda: db.table("records").update({"name": "changed"}).eq("id", 1),
            lambda: db.table("records").delete().eq("id", 1),
            lambda: db.rpc("increment_counter", {}),
        )
        for index, build in enumerate(builders):
            for ttl in (None, 60):
                with self.subTest(operation=index, ttl=ttl):
                    before = len(requests)
                    first = execute_query(build(), ttl=ttl)
                    second = execute_query(build(), ttl=ttl)
                    self.assertEqual(len(requests), before + 2)
                    self.assertNotEqual(first.data, second.data)

    def test_cached_reads_return_independent_response_copies(self):
        db, requests = self.database()
        first = execute_query(db.table("records").select("*"))
        first.data[0]["call"] = "modified"
        second = execute_query(db.table("records").select("*"))
        self.assertEqual(second.data[0]["call"], 1)
        self.assertIsNot(first, second)
        self.assertEqual(len(requests), 1)

    def test_database_cache_isolates_project_auth_key_and_schema(self):
        db, requests = self.database()
        execute_query(db.table("records").select("*"))
        execute_query(db.table("records").select("*"))
        self.assertEqual(len(requests), 1)
        for options in (
            {"project": "second"},
            {"token": "second-user"},
            {"key": "different-key"},
            {"schema": "private"},
        ):
            with self.subTest(options=options):
                other, other_requests = self.database(**options)
                execute_query(other.table("records").select("*"))
                self.assertEqual(len(other_requests), 1)

    def test_database_cache_distinguishes_filters_count_and_head(self):
        db, requests = self.database()
        builders = (
            lambda: db.table("records").select("*"),
            lambda: db.table("records").select("id"),
            lambda: db.table("records").select("*", count="exact"),
            lambda: db.table("records").select("*", count="exact", head=True),
            lambda: db.table("records").select("*").eq("id", 1),
            lambda: db.table("records").select("*").eq("id", 2),
        )
        for index, build in enumerate(builders, start=1):
            with self.subTest(query=index):
                execute_query(build())
                execute_query(build())
                self.assertEqual(len(requests), index)

    def test_single_and_read_only_rpc_results_can_be_cached(self):
        db, requests = self.database()
        single = execute_query(db.table("records").select("*").single())
        self.assertEqual(execute_query(db.table("records").select("*").single()), single)
        rpc = execute_query(db.rpc("read_records", {}, get=True))
        self.assertEqual(execute_query(db.rpc("read_records", {}, get=True)), rpc)
        self.assertEqual(len(requests), 2)

    def test_zero_ttl_and_unknown_methods_bypass_database_cache(self):
        db, requests = self.database()
        execute_query(db.table("records").select("*"), ttl=0)
        execute_query(db.table("records").select("*"), ttl=0)
        self.assertEqual(len(requests), 2)
        calls = []
        unknown = SimpleNamespace(execute=lambda: calls.append("called"))
        execute_query(unknown)
        execute_query(unknown)
        self.assertEqual(calls, ["called", "called"])


if __name__ == "__main__":
    unittest.main()
