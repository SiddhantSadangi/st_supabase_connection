import ast
import math
import unittest

from demo.safe_execution import (
    FilterSpec,
    build_database_query,
    parse_filter_rows,
    parse_json_records,
    render_database_code,
)


class RecordingClient:
    """Record fluent calls without reimplementing the Supabase SDK."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, method):
        def record(*args, **kwargs):
            self.calls.append((method, args, kwargs))
            return self

        return record


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

    def test_database_inputs_reject_non_finite_json_constants(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with (
                self.subTest(payload_constant=constant),
                self.assertRaisesRegex(ValueError, "finite numbers"),
            ):
                parse_json_records(f'{{"value": {constant}}}')

            with (
                self.subTest(filter_constant=constant),
                self.assertRaisesRegex(ValueError, "finite numbers"),
            ):
                parse_filter_rows([{"Column": "value", "Operator": "Equals", "Value": constant}])

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
        self.assertEqual(filters, [FilterSpec("deleted_at", "is_", "null")])

    def test_is_filter_normalizes_boolean_literals(self):
        filters = parse_filter_rows(
            [
                {"Column": "is_active", "Operator": "Is", "Value": "true"},
                {"Column": "is_archived", "Operator": "Is", "Value": "false"},
            ]
        )
        self.assertEqual(
            filters,
            [
                FilterSpec("is_active", "is_", "true"),
                FilterSpec("is_archived", "is_", "false"),
            ],
        )

    def test_in_filter_requires_a_json_array(self):
        for value in ("Asia", '"Asia"', "42", "true", '{"continent": "Asia"}'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "JSON array"):
                parse_filter_rows([{"Column": "continent", "Operator": "In", "Value": value}])

        filters = parse_filter_rows(
            [{"Column": "continent", "Operator": "In", "Value": '["Asia", "Europe"]'}]
        )
        self.assertEqual(filters, [FilterSpec("continent", "in_", ["Asia", "Europe"])])

    def test_build_select_query_from_structured_values(self):
        client = RecordingClient()
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
        self.assertIs(query, client)
        self.assertEqual(
            client.calls,
            [
                ("table", ("countries",), {}),
                ("select", ("name, continent",), {"count": "exact"}),
                ("eq", ("continent", "Asia"), {}),
                ("order", ("name",), {"desc": True}),
                ("limit", (5,), {}),
            ],
        )

    def test_preview_matches_sdk_calls_for_every_database_operation(self):
        source = "__import__('os').system('this must remain text')"
        cases = [
            {
                "operation": "select",
                "columns": "name",
                "count": "exact",
                "filters": parse_filter_rows(
                    [
                        {"Column": "name", "Operator": "Equals", "Value": source},
                        {"Column": "deleted_at", "Operator": "Is", "Value": "null"},
                        {"Column": "active", "Operator": "Is", "Value": "true"},
                        {"Column": "continent", "Operator": "In", "Value": '["Asia", "Europe"]'},
                    ]
                ),
                "order_column": "name",
                "order_desc": True,
                "limit": 5,
            },
            {"operation": "insert", "payload": [{"name": source}], "count": "exact"},
            {
                "operation": "upsert",
                "payload": {"id": 1, "name": source},
                "ignore_duplicates": True,
                "on_conflict": "id",
            },
            {
                "operation": "update",
                "payload": {"name": source},
                "filters": [FilterSpec("id", "eq", 1)],
            },
            {"operation": "delete", "filters": [FilterSpec("id", "eq", 1)]},
        ]
        for params in cases:
            with self.subTest(operation=params["operation"]):
                client = RecordingClient()
                build_database_query(client, table="countries", **params)
                code = render_database_code(
                    table="countries", ttl=0, client_expression="supabase", **params
                )
                node = ast.parse(code).body[0].value
                preview_calls = []
                while isinstance(node, ast.Call):
                    preview_calls.append(
                        (
                            node.func.attr,
                            tuple(ast.literal_eval(arg) for arg in node.args),
                            {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords},
                        )
                    )
                    node = node.func.value
                self.assertEqual(list(reversed(preview_calls)), client.calls)
                self.assertEqual(node.id, "supabase")
                self.assertIn("response = execute_query(query, ttl=0)", code)
                if params["operation"] == "select":
                    self.assertIn(("eq", ("name", source), {}), client.calls)

    def test_preview_and_execution_reject_the_same_invalid_queries(self):
        cases = [
            {"operation": "execute"},
            {"operation": "insert"},
            {"operation": "delete"},
            {"operation": "update", "payload": {"name": "Example"}},
            {"operation": "select", "filters": [FilterSpec("id", "execute", 1)]},
            {"operation": "select", "limit": 0},
            {"operation": "insert", "payload": {"id": 1}, "order_column": "id"},
            {"operation": "insert", "payload": {"id": 1}, "limit": 1},
        ]
        for params in cases:
            with self.subTest(params=params):
                client = RecordingClient()
                with self.assertRaises(ValueError):
                    build_database_query(client, table="countries", **params)
                with self.assertRaises(ValueError):
                    render_database_code(table="countries", ttl=0, **params)
                self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
