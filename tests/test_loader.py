"""CardLoader: duplicate keys, YAML 1.1 number traps, aliases, encoding and date lines."""

import tempfile
import unittest
from pathlib import Path

import yaml

from helpers import FIXTURES

from cardlib import schema


def load_error(path):
    try:
        schema.load_cards(path)
    except schema.CardFileError as exc:
        return str(exc)
    raise AssertionError(f"{path} loaded without CardFileError")


class DuplicateKeyTest(unittest.TestCase):
    def test_nested_duplicate_key_names_line_and_key(self):
        message = load_error(FIXTURES / "duplicate_nested_key.yaml")
        self.assertIn("6번째 줄: 'start' 항목이 두 번 있습니다", message)

    def test_duplicate_top_level_cards_key(self):
        message = load_error(FIXTURES / "duplicate_cards_key.yaml")
        self.assertIn("3번째 줄: 'cards' 항목이 두 번 있습니다", message)

    def test_duplicate_card_field(self):
        message = load_error(FIXTURES / "duplicate_card_field.yaml")
        self.assertIn("5번째 줄: 'name' 항목이 두 번 있습니다", message)

    def test_message_starts_with_file_path(self):
        path = FIXTURES / "duplicate_card_field.yaml"
        self.assertTrue(load_error(path).startswith(str(path)))

    def test_unhashable_key_is_a_yaml_error_not_a_crash(self):
        self.assertIn("YAML", load_error(FIXTURES / "unhashable_key.yaml"))

    def test_merge_key_override_is_not_a_duplicate(self):
        cards = schema.load_cards(FIXTURES / "merge_override.yaml")
        self.assertEqual(cards[0]["name"], "Child")
        self.assertEqual(cards[0]["id"], "merge-base")


class NumberTrapTest(unittest.TestCase):
    def test_non_decimal_integers_are_rejected_with_line(self):
        cases = [("octal_number.yaml", "4번째 줄", "0500"),
                 ("sexagesimal_number.yaml", "5번째 줄", "1:30"),
                 ("sexagesimal_float.yaml", "3번째 줄", "1:30.5"),
                 ("hex_number.yaml", "3번째 줄", "0x1f")]
        for name, line, value in cases:
            with self.subTest(name=name):
                message = load_error(FIXTURES / name)
                self.assertIn(line, message)
                self.assertIn(value, message)
                self.assertIn("숫자만", message)

    def test_decimal_numbers_still_load(self):
        cards = schema.load_cards(FIXTURES / "valid_cards.yaml")
        self.assertEqual(cards[0]["bonus"]["current"]["parts"][0]["value"], 75000)
        self.assertEqual(cards[1]["foreign_tx_fee_pct"], 2.7)

    def test_nan_and_inf_load_so_fields_can_report_them(self):
        loaded = yaml.load("a: .nan\nb: -.inf\nc: 0\nd: -12\n", Loader=schema.CardLoader)
        self.assertNotEqual(loaded["a"], loaded["a"])
        self.assertEqual((loaded["b"], loaded["c"], loaded["d"]), (float("-inf"), 0, -12))

    def test_global_safe_loader_is_untouched(self):
        self.assertEqual(yaml.safe_load("0500"), 320)
        self.assertEqual(yaml.safe_load("a: 1\na: 2"), {"a": 2})


class SafetyTest(unittest.TestCase):
    def test_python_tags_still_rejected(self):
        self.assertIn("YAML", load_error(FIXTURES / "python_tag.yaml"))

    def test_aliases_are_rejected(self):
        message = load_error(FIXTURES / "recursive_alias.yaml")
        self.assertIn("4번째 줄", message)
        self.assertIn("별칭", message)

    def test_deep_nesting_is_a_korean_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deep.yaml"
            path.write_text("cards: " + "[" * 5000 + "]" * 5000 + "\n", encoding="utf-8")
            self.assertIn("너무 깊", load_error(path))

    def test_non_utf8_file_is_a_korean_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "latin1.yaml"
            path.write_bytes(b"cards:\n  - id: caf\xe9\n")
            self.assertIn("UTF-8", load_error(path))


class BadDateLineTest(unittest.TestCase):
    def test_line_comes_from_the_value_not_a_comment(self):
        message = load_error(FIXTURES / "bad_date_after_comment.yaml")
        self.assertIn("6번째 줄", message)
        self.assertIn("2026-04-31", message)

    def test_other_constructor_errors_use_generic_message(self):
        self.assertIn("값을 읽지 못했습니다", load_error(FIXTURES / "bad_value.yaml"))


if __name__ == "__main__":
    unittest.main()
