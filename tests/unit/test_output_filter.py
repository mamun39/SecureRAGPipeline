import unittest

from security_output_filter import screen_generated_answer


class OutputFilterTests(unittest.TestCase):
    def test_output_filter_catches_secret_like_pattern(self):
        result = screen_generated_answer("Leaked key: sk-1234567890abcdefghijklmnop")

        self.assertEqual(result.decision, "block")
        self.assertIn("api_key_like_string", result.reasons)
