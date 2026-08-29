import ast
import math
import unittest

from demo.safe_execution import (
    FilterSpec,
    build_database_query,
    parse_filter_rows,
    parse_json_records,
    parse_string_list,
    render_database_code,
)


class FakeQuery:
    def __init__(self):
        self.calls = []

    def _record(self, method, *args, **kwargs):
        self.calls.append((method, args, kwargs))
        return self

    def select(self, *args, **kwargs):
        return self._record("select", *args, **kwargs)

    def insert(self, *args, **kwargs):
        return self._record("insert", *args, **kwargs)

    def upsert(self, *args, **kwargs):
        return self._record("upsert", *args, **kwargs)

    def update(self, *args, **kwargs):
        return self._record("update", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._record("delete", *args, **kwargs)

    def eq(self, *args, **kwargs):
        return self._record("eq", *args, **kwargs)

    def order(self, *args, **kwargs):
        return self._record("order", *args, **kwargs)

    def limit(self, *args, **kwargs):
        return self._record("limit", *args, **kwargs)


class FakeClient:
    def __init__(self):
        self.query = FakeQuery()

    def table(self, table):
        self.query.calls.append(("table", (table,), {}))
        return self.query


class SafeExecutionTests(unittest.TestCase):
    def test_json_records_reject_python_source(self):
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_json_records("__import__('os').system('echo unsafe')")

    def test_json_records_accept_object_and_array(self):
        self.assertEqual(parse_json_records('{"name": "Wakanda"}'), {"name": "Wakanda"})
        self.assertEqual(
            parse_json_records('[{"name": "Wakanda"}]'),
            [{"name": "Wakanda"}],
        )

    def test_string_list_requires_json_strings(self):
        self.assertEqual(parse_string_list('["a", "b"]', field_name="Paths"), ["a", "b"])
        self.assertIsNone(parse_string_list("[]", field_name="Allowed MIME types", optional=True))
        with self.assertRaisesRegex(ValueError, "JSON array"):
            parse_string_list("['a']", field_name="Paths")

    def test_filter_rows_allowlist_methods_and_treat_source_as_text(self):
        source = "__import__('os').system('echo unsafe')"
        filters = parse_filter_rows([{"Column": "name", "Operator": "Equals", "Value": source}])
        self.assertEqual(filters, [FilterSpec("name", "eq", source)])

    def test_filter_rows_require_explicit_missing_values(self):
        for missing_value in (None, math.nan, ""):
            with (
                self.subTest(missing_value=missing_value),
                self.assertRaisesRegex(ValueError, "needs a value"),
            ):
                parse_filter_rows(
                    [
                        {
                            "Column": "deleted_at",
                            "Operator": "Is",
                            "Value": missing_value,
                        }
                    ]
                )

        filters = parse_filter_rows([{"Column": "deleted_at", "Operator": "Is", "Value": "null"}])
        self.assertEqual(filters, [FilterSpec("deleted_at", "is_", None)])

        code = render_database_code(
            table="countries",
            operation="select",
            ttl=0,
            filters=filters,
        )
        ast.parse(code)
        self.assertIn(".is_('deleted_at', None)", code)

    def test_build_select_query_from_structured_values(self):
        client = FakeClient()
        query = build_database_query(
            client,
            table="countries",
            operation="select",
            columns="name, continent",
            count="exact",
            filters=[FilterSpec("continent", "eq", "Asia")],
            order_column="name",
            order_desc=True,
            limit=5,
        )
        self.assertIs(query, client.query)
        self.assertEqual(
            client.query.calls,
            [
                ("table", ("countries",), {}),
                ("select", ("name, continent",), {"count": "exact"}),
                ("eq", ("continent", "Asia"), {}),
                ("order", ("name",), {"desc": True}),
                ("limit", (5,), {}),
            ],
        )

    def test_update_and_delete_require_a_filter(self):
        for operation in ("update", "delete"):
            with (
                self.subTest(operation=operation),
                self.assertRaisesRegex(ValueError, "requires at least one filter"),
            ):
                build_database_query(
                    FakeClient(),
                    table="countries",
                    operation=operation,
                    payload={"name": "unsafe bulk mutation"} if operation == "update" else None,
                )

    def test_rendered_code_is_copyable_but_not_executed(self):
        source = "__import__('os').system('echo only text')"
        code = render_database_code(
            table="countries",
            operation="select",
            columns="*",
            ttl=None,
            filters=[FilterSpec("name", "eq", source)],
        )
        self.assertIn(".eq('name'", code)
        self.assertIn(source, code)
        self.assertIn("response = execute_query(query, ttl=None)", code)

    def test_rendered_code_can_use_the_session_scoped_client(self):
        code = render_database_code(
            table="private_profiles",
            operation="select",
            ttl=0,
            client_expression="supabase",
        )

        self.assertIn("supabase.table('private_profiles')", code)


if __name__ == "__main__":
    unittest.main()
