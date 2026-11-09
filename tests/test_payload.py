"""cards.yaml card -> public JSON shape, serialization and the previous-JSON reader."""

import copy
import json
import math
import unittest
from datetime import date, datetime, timedelta, timezone

from helpers import TODAY, make_card, with_value, without

from cardlib.payload import (PUBLIC_CARD_KEYS, PreviousJsonError, build_payload, iso_utc,
                             normalize_timestamp, parse_previous, public_card, same_content,
                             serialize)

GENERATED = "2026-11-09T10:23:00Z"
UPDATED = "2026-11-09T05:30:00Z"


class PublicCardTest(unittest.TestCase):
    def test_key_order_is_fixed(self):
        self.assertEqual(list(public_card(make_card(), TODAY)), list(PUBLIC_CARD_KEYS))
        self.assertEqual(PUBLIC_CARD_KEYS, (
            "id", "name", "issuer", "segment", "official_url", "last_verified", "annual_fee",
            "foreign_tx_fee_pct", "bonus", "offer", "earn", "benefits", "history"))

    def test_sources_are_not_published(self):
        card = with_value(make_card(), "sources", ["https://www.chase.com/review-only-source"])
        public = public_card(card, TODAY)
        self.assertNotIn("sources", public)
        self.assertNotIn("review-only-source", json.dumps(public))

    def test_unknown_keys_are_not_published(self):
        public = public_card(with_value(make_card(), "memo", "internal"), TODAY)
        self.assertNotIn("memo", public)

    def test_full_card_values(self):
        public = public_card(make_card(), TODAY)
        self.assertEqual(public["last_verified"], "2026-11-01")
        self.assertEqual(public["annual_fee"], {"amount": 95, "first_year_waived": False})
        self.assertEqual(public["bonus"]["current"], {
            "parts": [{"value": 75000, "unit": "points"}], "min_spend": 4000,
            "spend_months": 3, "note_en": "Sample note", "note_ko": "샘플 설명"})
        self.assertEqual(public["bonus"]["usual"], {
            "parts": [{"value": 60000, "unit": "points"}],
            "note_en": "Usual note", "note_ko": "평소 설명"})
        self.assertEqual(public["earn"], [
            {"category_en": "Travel", "category_ko": "여행", "rate": 2, "unit": "points"}])
        self.assertEqual(public["benefits"], [{"en": "Trip delay insurance", "ko": "여행 지연 보험"}])
        self.assertEqual(public["offer"]["id"], "sample-travel-card@2026-10-01")
        self.assertEqual(public["history"], [])

    def test_yaml_date_objects_become_iso_strings(self):
        card = with_value(make_card(), "last_verified", date(2026, 11, 2))
        card = with_value(card, "elevated", {"start": date(2026, 10, 3), "end": None})
        public = public_card(card, TODAY)
        self.assertEqual(public["last_verified"], "2026-11-02")
        self.assertEqual(public["offer"]["start"], "2026-10-03")

    def test_empty_ko_keys_are_omitted(self):
        card = make_card()
        for path in ("bonus.current.note_ko", "bonus.usual.note_ko",
                     "earn[0].category_ko", "benefits[0].ko"):
            card = with_value(card, path, "")
        public = public_card(card, TODAY)
        self.assertNotIn("note_ko", public["bonus"]["current"])
        self.assertNotIn("note_ko", public["bonus"]["usual"])
        self.assertNotIn("category_ko", public["earn"][0])
        self.assertNotIn("ko", public["benefits"][0])

    def test_blank_and_missing_optional_text_is_omitted(self):
        card = with_value(make_card(), "bonus.current.note_en", "   ")
        card = without(card, "bonus.usual.note_en")
        card = with_value(card, "earn[0].category_ko", None)
        public = public_card(card, TODAY)
        self.assertNotIn("note_en", public["bonus"]["current"])
        self.assertNotIn("note_en", public["bonus"]["usual"])
        self.assertNotIn("category_ko", public["earn"][0])

    def test_no_elevated_means_null_offer(self):
        self.assertIsNone(public_card(without(make_card(), "elevated"), TODAY)["offer"])
        self.assertIsNone(public_card(with_value(make_card(), "elevated", None), TODAY)["offer"])

    def test_whole_floats_are_published_as_ints(self):
        card = make_card()
        for path, value in (("bonus.current.parts[0].value", 75000.0),
                            ("bonus.usual.parts[0].value", 60000.0),
                            ("bonus.current.min_spend", 4000.0),
                            ("bonus.current.spend_months", 3.0), ("annual_fee.amount", 95.0),
                            ("foreign_tx_fee_pct", 3.0), ("earn[0].rate", 2.0)):
            card = with_value(card, path, value)
        public = public_card(card, TODAY)
        current = public["bonus"]["current"]
        numbers = (current["parts"][0]["value"], public["bonus"]["usual"]["parts"][0]["value"],
                   current["min_spend"], current["spend_months"], public["annual_fee"]["amount"],
                   public["foreign_tx_fee_pct"], public["earn"][0]["rate"])
        self.assertEqual(numbers, (75000, 60000, 4000, 3, 95, 3, 2))
        self.assertEqual({type(n) for n in numbers}, {int})
        self.assertNotIn(".0", json.dumps(public))

    def test_decimals_stay_decimals(self):
        card = with_value(make_card(), "foreign_tx_fee_pct", 2.7)
        card = with_value(card, "earn[0].rate", 1.5)
        public = public_card(card, TODAY)
        self.assertEqual((public["foreign_tx_fee_pct"], public["earn"][0]["rate"]), (2.7, 1.5))

    def test_does_not_mutate_card(self):
        card = make_card()
        snapshot = copy.deepcopy(card)
        public = public_card(card, TODAY)
        public["bonus"]["current"]["parts"][0]["value"] = 1
        public["earn"][0]["rate"] = 99
        self.assertEqual(card, snapshot)


class BuildPayloadTest(unittest.TestCase):
    def test_top_level_shape(self):
        payload, warnings = build_payload([make_card("a"), make_card("b")], None, TODAY,
                                          GENERATED, UPDATED)
        self.assertEqual(list(payload), ["schema", "generated_at", "data_updated_at", "cards"])
        self.assertEqual(payload["schema"], 1)
        self.assertEqual([c["id"] for c in payload["cards"]], ["a", "b"])
        self.assertEqual(warnings, [])

    def test_history_and_warnings_come_from_previous(self):
        first, _ = build_payload([make_card("a")], None, TODAY, GENERATED, UPDATED)
        raised = with_value(make_card("a"), "bonus.current.parts[0].value", 90000)
        payload, warnings = build_payload([raised], first, TODAY, GENERATED, UPDATED)
        self.assertEqual([e["type"] for e in payload["cards"][0]["history"]],
                         ["elevated", "changed"])
        self.assertEqual(len(warnings), 1)


class SerializeTest(unittest.TestCase):
    def payload(self):
        return build_payload([make_card()], None, TODAY, GENERATED, UPDATED)[0]

    def test_same_input_gives_same_text(self):
        self.assertEqual(serialize(self.payload()), serialize(self.payload()))

    def test_ends_with_one_newline_and_keeps_korean(self):
        text = serialize(self.payload())
        self.assertTrue(text.endswith("}\n"))
        self.assertIn("샘플 설명", text)

    def test_keeps_insertion_order_not_sorted(self):
        text = serialize(self.payload())
        self.assertLess(text.index('"schema"'), text.index('"generated_at"'))
        self.assertLess(text.index('"name"'), text.index('"issuer"'))

    def test_nan_and_infinity_are_rejected(self):
        for bad in (math.nan, math.inf):
            payload = with_value(self.payload(), "cards[0].foreign_tx_fee_pct", bad)
            with self.subTest(value=bad), self.assertRaises(ValueError):
                serialize(payload)

    def test_round_trips(self):
        payload = self.payload()
        self.assertEqual(json.loads(serialize(payload)), payload)


class SameContentTest(unittest.TestCase):
    def build(self, generated=GENERATED, updated=UPDATED, card=None):
        return build_payload([card or make_card()], None, TODAY, generated, updated)[0]

    def test_ignores_generated_at_only(self):
        old = self.build()
        old_text = serialize(old)
        self.assertTrue(same_content(self.build("2026-11-10T10:23:00Z"), old, old_text))
        changed = self.build(updated="2026-11-10T00:00:00Z")
        self.assertFalse(same_content(changed, old, old_text))
        self.assertFalse(same_content(old, None, None))

    def test_representation_change_is_a_change(self):
        new = self.build()
        float_text = serialize(new).replace('"value": 75000', '"value": 75000.0')
        self.assertEqual(json.loads(float_text), new)  # equal as dicts ...
        for old_text in (float_text, json.dumps(new, ensure_ascii=False, indent=4) + "\n",
                         serialize(new).replace("\n", "\r\n")):
            with self.subTest(old_text=old_text[:40]):
                self.assertFalse(same_content(new, json.loads(old_text), old_text))  # ... not bytes


class TimestampTest(unittest.TestCase):
    def test_iso_utc(self):
        self.assertEqual(iso_utc(datetime(2026, 11, 9, 10, 23, 5, 999, tzinfo=timezone.utc)),
                         "2026-11-09T10:23:05Z")
        pst = timezone(timedelta(hours=-8))
        self.assertEqual(iso_utc(datetime(2026, 11, 8, 21, 30, tzinfo=pst)),
                         "2026-11-09T05:30:00Z")

    def test_iso_utc_rejects_naive(self):
        with self.assertRaises(ValueError):
            iso_utc(datetime(2026, 11, 9, 10, 23))

    def test_normalize_git_commit_time(self):
        self.assertEqual(normalize_timestamp("2026-11-08T21:30:00-08:00"), "2026-11-09T05:30:00Z")
        self.assertEqual(normalize_timestamp("2026-11-09T05:30:00Z"), "2026-11-09T05:30:00Z")

    def test_normalize_rejects_garbage_and_naive(self):
        for bad in ("", "yesterday", "2026-11-09T05:30:00"):
            with self.subTest(text=bad), self.assertRaises(ValueError):
                normalize_timestamp(bad)


class ParsePreviousTest(unittest.TestCase):
    def test_valid_previous(self):
        payload, _ = build_payload([make_card()], None, TODAY, GENERATED, UPDATED)
        self.assertEqual(parse_previous(serialize(payload)), payload)

    def test_wrong_card_field_types_are_an_error(self):
        good = build_payload([make_card()], None, TODAY, GENERATED, UPDATED)[0]["cards"][0]
        bad_cards = [{**good, "offer": "x"}, {**good, "bonus": []},
                     {**good, "bonus": {"current": {"parts": "x"}}},
                     {**good, "bonus": {"current": {"parts": [{"value": "1", "unit": "points"}]}}},
                     {**good, "bonus": {"current": {"parts": [{"value": 1}]}}},
                     {**good, "history": {}}, {**good, "history": ["x"]}]
        for card in bad_cards:
            text = json.dumps({"schema": 1, "cards": [card]})
            with self.subTest(card=text[-80:]), self.assertRaises(PreviousJsonError) as ctx:
                parse_previous(text)
            self.assertIn("모양이 맞지 않습니다", str(ctx.exception))

    def test_null_offer_and_missing_history_are_fine(self):
        good = build_payload([without(make_card(), "elevated")], None, TODAY, GENERATED,
                             UPDATED)[0]["cards"][0]
        no_history = {key: value for key, value in good.items() if key != "history"}
        parse_previous(json.dumps({"schema": 1, "cards": [good, {**no_history, "id": "b"}]}))

    def test_broken_or_wrong_shape_is_an_error(self):
        bad_texts = ("{not json", "[]", '{"schema": 2, "cards": []}', '{"schema": 1}',
                     '{"schema": 1, "cards": [1]}', '{"schema": 1, "cards": [{"name": "x"}]}',
                     '{"schema": 1, "cards": [], "x": NaN}')
        for text in bad_texts:
            with self.subTest(text=text), self.assertRaises(PreviousJsonError) as ctx:
                parse_previous(text)
            self.assertIn("docs/cards_v1.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
