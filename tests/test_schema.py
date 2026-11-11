"""Structure, type, enum, date and count rules of cardlib.schema.validate."""

import copy
import unittest
from datetime import date, datetime, timezone
from types import MappingProxyType
from unittest import mock

from helpers import TODAY, errors_of, make_card, paths_of, warnings_of, with_value, without

from cardlib import schema


def check(*cards, today=TODAY):
    return schema.validate(list(cards), today=today)


class ValidCardTest(unittest.TestCase):
    def test_valid_card_has_no_errors(self):
        self.assertEqual(errors_of(check(make_card())), [])

    def test_validate_does_not_mutate_input(self):
        card = with_value(make_card(), "last_verified", date(2026, 11, 1))
        snapshot = copy.deepcopy(card)
        check(card)
        self.assertEqual(card, snapshot)

    def test_issue_str_contains_level_card_id_and_path(self):
        issues = check(with_value(make_card(), "segment", "family"))
        text = str(errors_of(issues)[0])
        self.assertIn("[오류]", text)
        self.assertIn("sample-travel-card", text)
        self.assertIn("segment", text)


class RequiredFieldTest(unittest.TestCase):
    REQUIRED = [
        "id", "name", "issuer", "segment", "official_url", "last_verified",
        "sources", "annual_fee", "foreign_tx_fee_pct", "bonus", "earn", "benefits",
        "annual_fee.amount", "annual_fee.first_year_waived",
        "bonus.current", "bonus.usual", "bonus.current.parts",
        "bonus.current.min_spend", "bonus.current.spend_months",
        "bonus.usual.parts", "bonus.current.parts[0].value",
        "bonus.current.parts[0].unit", "earn[0].category_en", "earn[0].rate",
        "earn[0].unit", "benefits[0].en", "elevated.start",
    ]

    def test_each_missing_required_field_is_an_error(self):
        for path in self.REQUIRED:
            with self.subTest(path=path):
                issues = errors_of(check(without(make_card(), path)))
                self.assertIn(path, paths_of(issues))
                self.assertTrue(any("필수" in i.message for i in issues))

    def test_blank_required_string_is_an_error(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                issues = errors_of(check(with_value(make_card(), "name", value)))
                self.assertIn("name", paths_of(issues))

    def test_missing_id_message_uses_card_number(self):
        issues = errors_of(check(make_card("a-card"), without(make_card(), "id")))
        self.assertEqual(issues[0].card, "카드 2번")

    def test_card_that_is_not_a_mapping_is_an_error(self):
        issues = errors_of(check("just text"))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].card, "카드 1번")

    def test_cards_that_is_not_a_list_is_an_error(self):
        issues = errors_of(schema.validate({"id": "x"}, today=TODAY))
        self.assertEqual(paths_of(issues), {"cards"})

    def test_empty_lists_where_items_are_required(self):
        for path in ("sources", "bonus.current.parts", "bonus.usual.parts", "earn"):
            with self.subTest(path=path):
                issues = errors_of(check(with_value(make_card(), path, [])))
                self.assertIn(path, paths_of(issues))

    def test_empty_benefits_list_is_allowed(self):
        self.assertEqual(errors_of(check(with_value(make_card(), "benefits", []))), [])

    def test_unknown_top_level_or_earn_key_is_a_warning_not_an_error(self):
        for path in ("elevaetd", "earn[0].memo", "annual_fee.note", "benefits[0].tag"):
            with self.subTest(path=path):
                issues = check(with_value(make_card(), path, "x"))
                self.assertEqual(errors_of(issues), [])
                self.assertIn(path, paths_of(warnings_of(issues)))

    def test_unknown_key_inside_bonus_or_elevated_is_an_error(self):
        for path in ("bonus.curent", "bonus.current.min_spnd", "bonus.usual.note",
                     "bonus.current.parts[0].valu", "bonus.usual.parts[0].extra",
                     "elevated.ends", "elevated.note"):
            with self.subTest(path=path):
                issues = errors_of(check(with_value(make_card(), path, "x")))
                self.assertIn(path, paths_of(issues))
                self.assertTrue(any("알 수 없는 항목" in i.message for i in issues))


class IdTest(unittest.TestCase):
    def test_duplicate_id_is_an_error(self):
        issues = errors_of(check(make_card("same-id"), make_card("same-id")))
        self.assertEqual(len(issues), 1)
        self.assertIn("중복", issues[0].message)

    def test_blank_ids_are_not_reported_as_duplicates(self):
        for blank in ("", "   "):
            with self.subTest(blank=repr(blank)):
                issues = errors_of(check(make_card(blank), make_card(blank)))
                self.assertFalse(any("중복" in i.message for i in issues))
                self.assertEqual({i.card for i in issues}, {"카드 1번", "카드 2번"})

    def test_kebab_case_ids_pass(self):
        for card_id in ("chase-sapphire", "amex-gold-2", "a1"):
            with self.subTest(card_id=card_id):
                self.assertEqual(errors_of(check(make_card(card_id))), [])

    def test_non_kebab_ids_fail(self):
        bad = ["Chase-Sapphire", "chase_sapphire", "chase sapphire", "-chase",
               "chase-", "chase--x", "체이스"]
        for card_id in bad:
            with self.subTest(card_id=card_id):
                issues = errors_of(check(make_card(card_id)))
                self.assertIn("id", paths_of(issues))

    def test_non_string_id_fails(self):
        issues = errors_of(check(with_value(make_card(), "id", 123)))
        self.assertIn("id", paths_of(issues))
        self.assertEqual(issues[0].card, "카드 1번")


class EnumTest(unittest.TestCase):
    def test_segment_values(self):
        for value in ("personal", "business"):
            with self.subTest(value=value):
                self.assertEqual(errors_of(check(with_value(make_card(), "segment", value))), [])
        issues = errors_of(check(with_value(make_card(), "segment", "Personal")))
        self.assertIn("segment", paths_of(issues))

    def test_bonus_units(self):
        for unit in ("points", "miles", "cash", "free_night", "credit", "percent_match"):
            with self.subTest(unit=unit):
                card = with_value(make_card(), "bonus.usual.parts[0].unit", unit)
                self.assertEqual(errors_of(check(card)), [])
        card = with_value(make_card(), "bonus.current.parts[0].unit", "dollars")
        self.assertIn("bonus.current.parts[0].unit", paths_of(errors_of(check(card))))

    def test_earn_units(self):
        for unit in ("points", "miles", "cash"):
            with self.subTest(unit=unit):
                card = with_value(make_card(), "earn[0].unit", unit)
                self.assertEqual(errors_of(check(card)), [])
        card = with_value(make_card(), "earn[0].unit", "free_night")
        self.assertIn("earn[0].unit", paths_of(errors_of(check(card))))


class TypeTest(unittest.TestCase):
    """YAML pitfalls: `no` becomes False, `4,000` stays a string, and so on."""

    def test_boolean_where_string_expected_fails_with_quote_hint(self):
        for path in ("name", "issuer", "benefits[0].en", "benefits[0].ko",
                     "bonus.current.note_ko", "earn[0].category_ko"):
            with self.subTest(path=path):
                issues = errors_of(check(with_value(make_card(), path, False)))
                self.assertIn(path, paths_of(issues))
                self.assertTrue(any("따옴표" in i.message for i in issues))

    def test_number_where_string_expected_fails(self):
        issues = errors_of(check(with_value(make_card(), "name", 2026)))
        self.assertIn("name", paths_of(issues))

    def test_boolean_where_number_expected_fails(self):
        for path in ("annual_fee.amount", "foreign_tx_fee_pct", "bonus.current.min_spend",
                     "bonus.current.spend_months", "bonus.current.parts[0].value",
                     "earn[0].rate"):
            with self.subTest(path=path):
                issues = errors_of(check(with_value(make_card(), path, False)))
                self.assertIn(path, paths_of(issues))

    def test_text_number_with_comma_fails(self):
        issues = errors_of(check(with_value(make_card(), "bonus.current.min_spend", "4,000")))
        self.assertIn("bonus.current.min_spend", paths_of(issues))
        self.assertTrue(any("쉼표" in i.message for i in issues))

    def test_number_ranges(self):
        cases = [("annual_fee.amount", -1), ("foreign_tx_fee_pct", -0.5),
                 ("foreign_tx_fee_pct", 101), ("bonus.current.min_spend", -1),
                 ("bonus.current.spend_months", 0), ("bonus.current.spend_months", 2.5),
                 ("bonus.current.parts[0].value", 0), ("earn[0].rate", 0)]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                issues = errors_of(check(with_value(make_card(), path, value)))
                self.assertIn(path, paths_of(issues))

    def test_nan_and_infinity_fail(self):
        for path in ("annual_fee.amount", "foreign_tx_fee_pct", "bonus.current.min_spend",
                     "bonus.current.spend_months", "bonus.current.parts[0].value",
                     "earn[0].rate"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(path=path, value=value):
                    issues = errors_of(check(with_value(make_card(), path, value)))
                    self.assertIn(path, paths_of(issues))
                    self.assertTrue(any("nan" in i.message for i in issues))

    def test_huge_integer_is_range_checked_not_a_crash(self):
        issues = errors_of(check(with_value(make_card(), "bonus.current.spend_months", 10**400)))
        self.assertEqual(issues, [])
        issues = errors_of(check(with_value(make_card(), "foreign_tx_fee_pct", 10**400)))
        self.assertIn("foreign_tx_fee_pct", paths_of(issues))

    def test_valid_number_edges_pass(self):
        card = with_value(make_card(), "annual_fee.amount", 0)
        card = with_value(card, "foreign_tx_fee_pct", 2.7)
        card = with_value(card, "bonus.current.min_spend", 0)
        self.assertEqual(errors_of(check(card)), [])

    def test_first_year_waived_must_be_boolean(self):
        for value in ("no", 0, None):
            with self.subTest(value=value):
                card = with_value(make_card(), "annual_fee.first_year_waived", value)
                self.assertIn("annual_fee.first_year_waived", paths_of(errors_of(check(card))))
        card = with_value(make_card(), "annual_fee.first_year_waived", True)
        self.assertEqual(errors_of(check(card)), [])

    def test_wrong_container_types_fail(self):
        cases = [("sources", "https://creditcards.chase.com/x"), ("annual_fee", 95),
                 ("bonus", "75k"), ("bonus.current.parts", {"value": 1}),
                 ("bonus.current.parts[0]", 75000), ("earn", {"x": 1}),
                 ("earn[0]", "travel"), ("benefits", "lounge"), ("benefits[0]", "lounge"),
                 ("elevated", "yes")]
        for path, value in cases:
            with self.subTest(path=path):
                self.assertIn(path, paths_of(errors_of(check(with_value(make_card(), path, value)))))


class KoreanOptionalTest(unittest.TestCase):
    KO_PATHS = ("bonus.current.note_ko", "bonus.usual.note_ko", "earn[0].category_ko",
                "benefits[0].ko")

    def test_ko_missing_empty_or_null_passes(self):
        for path in self.KO_PATHS:
            for variant in ("missing", "", None):
                with self.subTest(path=path, variant=variant):
                    if variant == "missing":
                        card = without(make_card(), path)
                    else:
                        card = with_value(make_card(), path, variant)
                    self.assertEqual(errors_of(check(card)), [])

    def test_note_en_is_optional(self):
        card = without(make_card(), "bonus.current.note_en")
        self.assertEqual(errors_of(check(card)), [])


def card_issues(card):
    """Issues of one card, without the whole-file 'not 30 cards' warning."""
    return [issue for issue in check(card) if issue.path != "cards"]


class JapaneseSpanishOptionalTest(unittest.TestCase):
    """Plan A7: optional ja/es texts, same rules as the _ko texts."""

    TEXTS = {
        "bonus.current.note_ja": "サンプル説明", "bonus.current.note_es": "Nota de ejemplo",
        "bonus.usual.note_ja": "通常の説明", "bonus.usual.note_es": "Nota habitual",
        "earn[0].category_ja": "旅行", "earn[0].category_es": "Viajes",
        "benefits[0].ja": "旅行遅延保険", "benefits[0].es": "Seguro por retraso de viaje",
    }

    def full_card(self):
        card = make_card()
        for path, text in self.TEXTS.items():
            card = with_value(card, path, text)
        return card

    def test_sample_card_alone_has_no_card_issues(self):
        self.assertEqual(card_issues(make_card()), [])

    def test_ja_and_es_texts_pass_without_errors_or_warnings(self):
        self.assertEqual(card_issues(self.full_card()), [])

    def test_ja_and_es_missing_empty_blank_or_null_pass(self):
        for path in self.TEXTS:
            for value in ("", "   ", None):
                with self.subTest(path=path, value=value):
                    self.assertEqual(card_issues(with_value(self.full_card(), path, value)), [])
            with self.subTest(path=path, value="missing"):
                self.assertEqual(card_issues(without(self.full_card(), path)), [])

    def test_non_text_ja_or_es_fails_with_quote_hint(self):
        for path in self.TEXTS:
            for value in (False, 2026, ["x"]):
                with self.subTest(path=path, value=value):
                    issues = errors_of(card_issues(with_value(self.full_card(), path, value)))
                    self.assertEqual(paths_of(issues), {path})
                    self.assertTrue(any("따옴표" in i.message for i in issues))

    def test_unknown_language_keys_keep_the_old_rules(self):
        for path in ("bonus.current.note_jp", "bonus.usual.note_sp"):
            with self.subTest(path=path):
                issues = card_issues(with_value(make_card(), path, "x"))
                self.assertIn(path, paths_of(errors_of(issues)))
        for path in ("earn[0].category_jp", "benefits[0].sp"):
            with self.subTest(path=path):
                issues = card_issues(with_value(make_card(), path, "x"))
                self.assertEqual(errors_of(issues), [])
                self.assertIn(path, paths_of(warnings_of(issues)))


class DateTest(unittest.TestCase):
    def test_last_verified_accepts_date_object_and_iso_string(self):
        for value in (date(2026, 11, 1), "2026-11-01", TODAY):
            with self.subTest(value=value):
                card = with_value(make_card(), "last_verified", value)
                self.assertEqual(errors_of(check(card)), [])

    def test_last_verified_in_future_fails(self):
        for value in (date(2026, 11, 10), "2027-01-01"):
            with self.subTest(value=value):
                card = with_value(make_card(), "last_verified", value)
                issues = errors_of(check(card))
                self.assertIn("last_verified", paths_of(issues))
                self.assertTrue(any("미래" in i.message for i in issues))

    def test_bad_dates_fail(self):
        for value in ("2026/11/01", "11-01-2026", "2026-02-30", "yesterday", 20261101,
                      datetime(2026, 11, 1, 10, 0), True):
            with self.subTest(value=value):
                card = with_value(make_card(), "last_verified", value)
                self.assertIn("last_verified", paths_of(errors_of(check(card))))

    def test_today_defaults_to_pacific_date(self):
        class FrozenClock(datetime):
            """2026-11-10 03:00 UTC is still 2026-11-09 19:00 in Los Angeles."""

            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 11, 10, 3, 0, tzinfo=timezone.utc).astimezone(tz)

        with mock.patch.object(schema, "datetime", FrozenClock):
            self.assertEqual(schema.today_pt(), date(2026, 11, 9))
            today_ok = with_value(make_card(), "last_verified", "2026-11-09")
            utc_today = with_value(make_card(), "last_verified", "2026-11-10")
            self.assertEqual(errors_of(schema.validate([today_ok])), [])
            self.assertIn("last_verified", paths_of(errors_of(schema.validate([utc_today]))))

    def test_parse_date_normalizes(self):
        self.assertEqual(schema.parse_date("2026-11-01"), date(2026, 11, 1))
        self.assertEqual(schema.parse_date(date(2026, 11, 1)), date(2026, 11, 1))
        with self.assertRaises(ValueError):
            schema.parse_date(datetime(2026, 11, 1, 1, 0))


class ElevatedTest(unittest.TestCase):
    def test_absent_or_null_elevated_is_usual(self):
        self.assertEqual(errors_of(check(without(make_card(), "elevated"))), [])
        self.assertEqual(errors_of(check(with_value(make_card(), "elevated", None))), [])

    def test_end_may_be_null_or_missing(self):
        self.assertEqual(errors_of(check(with_value(make_card(), "elevated.end", None))), [])
        self.assertEqual(errors_of(check(without(make_card(), "elevated.end"))), [])

    def test_start_in_future_fails(self):
        card = with_value(make_card(), "elevated", {"start": "2026-11-10", "end": None})
        issues = errors_of(check(card))
        self.assertEqual(paths_of(issues), {"elevated.start"})
        self.assertIn("미래", issues[0].message)

    def test_start_today_passes(self):
        card = with_value(make_card(), "elevated.start", TODAY)
        self.assertEqual(errors_of(check(card)), [])

    def test_end_before_start_fails(self):
        card = with_value(make_card(), "elevated", {"start": "2026-10-10", "end": "2026-10-09"})
        issues = errors_of(check(card))
        self.assertIn("elevated.end", paths_of(issues))

    def test_end_equal_to_start_passes(self):
        card = with_value(make_card(), "elevated", {"start": "2026-10-10", "end": "2026-10-10"})
        self.assertEqual(errors_of(check(card)), [])

    def test_bad_start_or_end_date_fails(self):
        for path in ("elevated.start", "elevated.end"):
            with self.subTest(path=path):
                card = with_value(make_card(), path, "soon")
                self.assertIn(path, paths_of(errors_of(check(card))))


class FrozenSpecTest(unittest.TestCase):
    def test_spec_field_tables_are_read_only(self):
        nested = schema.CARD_SPEC.fields["bonus"].fields["current"]
        for spec in (schema.CARD_SPEC, schema.CARD_SPEC.fields["annual_fee"], nested):
            with self.subTest(spec=type(spec).__name__):
                # Checked without writing: a successful write would corrupt the shared spec.
                self.assertIsInstance(spec.fields, MappingProxyType)


class CardCountTest(unittest.TestCase):
    def test_not_thirty_cards_is_only_a_warning(self):
        issues = check(make_card("one"), make_card("two"))
        self.assertEqual(errors_of(issues), [])
        self.assertEqual(paths_of(warnings_of(issues)), {"cards"})
        self.assertIn("30", warnings_of(issues)[0].message)

    def test_zero_cards_is_an_error(self):
        issues = schema.validate([], today=TODAY)
        self.assertEqual(paths_of(errors_of(issues)), {"cards"})

    def test_thirty_cards_have_no_warning(self):
        cards = [make_card(f"card-{n}") for n in range(30)]
        self.assertEqual(check(*cards), [])


if __name__ == "__main__":
    unittest.main()
