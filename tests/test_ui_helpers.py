import hashlib
import json
import unittest
from unittest.mock import patch

from demo import ui_helpers


class ActionFingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_within_a_session_and_keyed(self):
        state = {}
        values = {"email": "user@example.com", "password": "password123"}
        with patch.object(ui_helpers.st, "session_state", state):
            first = ui_helpers.action_fingerprint("auth:sign_up", values)
            second = ui_helpers.action_fingerprint("auth:sign_up", values)

        material = json.dumps(
            {"scope": "auth:sign_up", "values": values},
            sort_keys=True,
            default=str,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, hashlib.sha256(material.encode()).hexdigest())
        self.assertNotIn("password123", first)


if __name__ == "__main__":
    unittest.main()
