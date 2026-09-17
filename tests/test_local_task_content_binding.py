from __future__ import annotations

import unittest

from lai_gateway.local_task_content_binding import (
    LocalTaskContentBindingError,
    compute_local_task_digest,
    is_valid_local_task_digest,
    parse_local_task_json,
)


class LocalTaskContentBindingTest(unittest.TestCase):
    def test_key_order_and_whitespace_do_not_change_digest(self) -> None:
        first = parse_local_task_json(
            '{"schema_version":"local-task/v1","task_id":"x","value":1}'
        )
        second = parse_local_task_json(
            '{ "value": 1, "task_id": "x", "schema_version": "local-task/v1" }'
        )

        self.assertEqual(
            compute_local_task_digest(first),
            compute_local_task_digest(second),
        )

    def test_integer_and_float_remain_distinct(self) -> None:
        integer = parse_local_task_json('{"value":1}')
        floating = parse_local_task_json('{"value":1.0}')

        self.assertNotEqual(
            compute_local_task_digest(integer),
            compute_local_task_digest(floating),
        )

    def test_positive_and_negative_zero_remain_distinct(self) -> None:
        positive = parse_local_task_json('{"value":0.0}')
        negative = parse_local_task_json('{"value":-0.0}')

        self.assertNotEqual(
            compute_local_task_digest(positive),
            compute_local_task_digest(negative),
        )

    def test_unicode_is_not_normalized(self) -> None:
        composed = parse_local_task_json('{"value":"é"}')
        decomposed = parse_local_task_json('{"value":"e\\u0301"}')

        self.assertNotEqual(
            compute_local_task_digest(composed),
            compute_local_task_digest(decomposed),
        )

    def test_duplicate_object_key_is_rejected(self) -> None:
        with self.assertRaises(LocalTaskContentBindingError):
            parse_local_task_json(
                '{"schema_version":"local-task/v1","task_id":"a","task_id":"b"}'
            )

    def test_nested_duplicate_object_key_is_rejected(self) -> None:
        with self.assertRaises(LocalTaskContentBindingError):
            parse_local_task_json(
                '{"task_id":"a","nested":{"x":1,"x":2}}'
            )

    def test_non_standard_numbers_are_rejected(self) -> None:
        for raw in (
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-Infinity}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(LocalTaskContentBindingError):
                    parse_local_task_json(raw)

    def test_lone_unicode_surrogate_fails_closed(self) -> None:
        task = parse_local_task_json('{"value":"\\ud800"}')

        with self.assertRaises(LocalTaskContentBindingError):
            compute_local_task_digest(task)

    def test_digest_format_validation(self) -> None:
        digest = compute_local_task_digest({"task_id": "x"})

        self.assertTrue(is_valid_local_task_digest(digest))
        self.assertFalse(is_valid_local_task_digest(None))
        self.assertFalse(is_valid_local_task_digest("sha256:ABC"))
        self.assertFalse(is_valid_local_task_digest("0" * 64))


if __name__ == "__main__":
    unittest.main()
