"""cardlib.schema.load_cards: safe YAML loading and Korean load errors."""

import unittest
from datetime import date

from helpers import FIXTURES, TODAY, errors_of, paths_of

from cardlib import schema


class LoadCardsTest(unittest.TestCase):
    def test_loads_list_of_card_dicts(self):
        cards = schema.load_cards(FIXTURES / "valid_cards.yaml")
        self.assertEqual([c["id"] for c in cards], ["fixture-travel", "fixture-business"])
        self.assertEqual(cards[0]["bonus"]["current"]["parts"][0]["value"], 75000)

    def test_unquoted_and_quoted_dates_both_validate(self):
        cards = schema.load_cards(FIXTURES / "valid_cards.yaml")
        self.assertIsInstance(cards[0]["last_verified"], date)
        self.assertIsInstance(cards[1]["last_verified"], str)
        self.assertEqual(errors_of(schema.validate(cards, today=TODAY)), [])

    def test_accepts_str_path(self):
        cards = schema.load_cards(str(FIXTURES / "valid_cards.yaml"))
        self.assertEqual(len(cards), 2)

    def test_yaml_pitfalls_are_reported_not_silently_accepted(self):
        cards = schema.load_cards(FIXTURES / "yaml_pitfalls.yaml")
        issues = errors_of(schema.validate(cards, today=TODAY))
        self.assertEqual(paths_of(issues), {"name", "bonus.current.min_spend"})

    def test_python_tags_are_rejected_by_safe_load(self):
        with self.assertRaises(schema.CardFileError):
            schema.load_cards(FIXTURES / "python_tag.yaml")


class LoadErrorTest(unittest.TestCase):
    def assert_load_error(self, name, *fragments):
        with self.assertRaises(schema.CardFileError) as ctx:
            schema.load_cards(FIXTURES / name)
        for fragment in fragments:
            self.assertIn(fragment, str(ctx.exception))

    def test_missing_file(self):
        self.assert_load_error("does_not_exist.yaml", "파일")

    def test_syntax_error_reports_line(self):
        self.assert_load_error("syntax_error.yaml", "YAML", "줄")

    def test_impossible_date_reports_line(self):
        self.assert_load_error("bad_date.yaml", "2026-02-30", "5번째 줄")

    def test_other_constructor_value_error_is_wrapped(self):
        self.assert_load_error("bad_value.yaml", "값을 읽지 못했습니다")

    def test_reader_error_is_wrapped(self):
        self.assert_load_error("control_char.yaml", "YAML")

    def test_root_must_be_mapping_with_cards(self):
        self.assert_load_error("root_list.yaml", "cards")
        self.assert_load_error("no_cards_key.yaml", "cards")
        self.assert_load_error("empty.yaml", "cards")


if __name__ == "__main__":
    unittest.main()
