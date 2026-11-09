"""history/bonus_log.csv rows: one snapshot per card, then only changed cards."""

import unittest
from datetime import date

import helpers  # noqa: F401 - puts scripts/ on sys.path

from cardlib.bonus_log import (COLUMNS, BonusLogError, compact_parts, diff_rows, format_rows,
                               parse_log, row_for)

DAY = date(2026, 11, 9)
NEXT = date(2026, 11, 10)


def pub(card_id="card", issuer="Chase", current=((75000, "points"),),
        usual=((60000, "points"),), min_spend=4000, spend_months=3, offer=None,
        last_verified="2026-11-01"):
    """A public card as in cards_v1.json (only the fields the log reads)."""
    def parts(pairs):
        return [{"value": value, "unit": unit} for value, unit in pairs]
    return {
        "id": card_id,
        "issuer": issuer,
        "last_verified": last_verified,
        "bonus": {
            "current": {"parts": parts(current), "min_spend": min_spend,
                        "spend_months": spend_months},
            "usual": {"parts": parts(usual)},
        },
        "offer": offer,
    }


def offer(card_id="card", start="2026-10-01", end="2026-12-31", status="active"):
    return {"id": f"{card_id}@{start}", "status": status, "start": start, "end": end,
            "ended_auto": status == "ended"}


class CompactPartsTest(unittest.TestCase):
    def test_single_part(self):
        self.assertEqual(compact_parts([{"value": 70000, "unit": "miles"}]), "70000 miles")

    def test_parts_are_sorted_so_order_does_not_matter(self):
        a = [{"value": 130000, "unit": "points"}, {"value": 1, "unit": "free_night"}]
        self.assertEqual(compact_parts(a), "1 free_night + 130000 points")
        self.assertEqual(compact_parts(list(reversed(a))), compact_parts(a))

    def test_whole_floats_print_as_ints_and_decimals_stay(self):
        self.assertEqual(compact_parts([{"value": 75000.0, "unit": "points"}]), "75000 points")
        self.assertEqual(compact_parts([{"value": 2.5, "unit": "percent"}]), "2.5 percent")

    def test_no_parts_is_empty_text(self):
        self.assertEqual(compact_parts([]), "")


class RowForTest(unittest.TestCase):
    def test_columns_are_fixed(self):
        self.assertEqual(COLUMNS, ("date", "card_id", "issuer", "current", "min_spend",
                                   "spend_months", "usual", "elevated", "offer_id",
                                   "offer_end", "last_verified", "note"))

    def test_card_with_active_offer(self):
        row = row_for(pub(offer=offer()), DAY)
        self.assertEqual(row, {
            "date": "2026-11-09", "card_id": "card", "issuer": "Chase",
            "current": "75000 points", "min_spend": "4000", "spend_months": "3",
            "usual": "60000 points", "elevated": "yes", "offer_id": "card@2026-10-01",
            "offer_end": "2026-12-31", "last_verified": "2026-11-01", "note": ""})

    def test_card_without_offer(self):
        row = row_for(pub(), DAY)
        self.assertEqual((row["elevated"], row["offer_id"], row["offer_end"]), ("no", "", ""))

    def test_ended_offer_keeps_its_id_but_is_not_elevated(self):
        row = row_for(pub(offer=offer(end="2026-11-08", status="ended")), DAY)
        self.assertEqual((row["elevated"], row["offer_id"], row["offer_end"]),
                         ("no", "card@2026-10-01", "2026-11-08"))

    def test_open_ended_offer_has_empty_end(self):
        self.assertEqual(row_for(pub(offer=offer(end=None)), DAY)["offer_end"], "")

    def test_numbers_are_compact(self):
        row = row_for(pub(min_spend=4000.0, spend_months=3.0), DAY)
        self.assertEqual((row["min_spend"], row["spend_months"]), ("4000", "3"))

    def test_date_may_be_text(self):
        self.assertEqual(row_for(pub(), "2026-11-09")["date"], "2026-11-09")


class DiffRowsTest(unittest.TestCase):
    def last(self, *cards, day=DAY):
        return {card["id"]: row_for(card, day) for card in cards}

    def test_first_snapshot_writes_every_card_as_added(self):
        rows = diff_rows({}, [row_for(pub("a"), DAY), row_for(pub("b"), DAY)], DAY)
        self.assertEqual([(r["card_id"], r["note"]) for r in rows], [("a", "added"),
                                                                     ("b", "added")])

    def test_unchanged_cards_add_nothing_even_on_a_new_date(self):
        last = self.last(pub("a"), pub("b"))
        self.assertEqual(diff_rows(last, [row_for(pub("a"), NEXT), row_for(pub("b"), NEXT)],
                                   NEXT), [])

    def test_each_tracked_change_adds_exactly_one_row_for_that_card(self):
        changes = {
            "current": {"current": ((90000, "points"),)},
            "usual": {"usual": ((50000, "points"),)},
            "min_spend": {"min_spend": 5000},
            "spend_months": {"spend_months": 6},
            "elevated": {"offer": offer("a", status="ended")},
            "offer_id": {"offer": offer("a", start="2026-11-05")},
            "offer_end": {"offer": offer("a", end="2027-01-31")},
            "last_verified": {"last_verified": "2026-11-09"},
            "issuer": {"issuer": "American Express"},
        }
        last = self.last(pub("a", offer=offer("a")), pub("b"))
        for field, change in changes.items():
            card = pub("a", **{"offer": offer("a"), **change})
            with self.subTest(field=field):
                rows = diff_rows(last, [row_for(card, NEXT), row_for(pub("b"), NEXT)], NEXT)
                self.assertEqual(len(rows), 1)
                self.assertEqual((rows[0]["card_id"], rows[0]["note"], rows[0]["date"]),
                                 ("a", "", "2026-11-10"))
                self.assertNotEqual(rows[0][field], last["a"][field])

    def test_auto_end_is_a_change(self):
        last = self.last(pub(offer=offer()))
        rows = diff_rows(last, [row_for(pub(offer=offer(status="ended")), NEXT)], NEXT)
        self.assertEqual([(r["elevated"], r["offer_id"]) for r in rows],
                         [("no", "card@2026-10-01")])

    def test_part_order_change_only_adds_nothing(self):
        two = ((130000, "points"), (1, "free_night"))
        last = self.last(pub(current=two, usual=two))
        swapped = tuple(reversed(two))
        self.assertEqual(diff_rows(last, [row_for(pub(current=swapped, usual=swapped), NEXT)],
                                   NEXT), [])

    def test_removed_card_adds_one_removed_row(self):
        last = self.last(pub("a"), pub("b", issuer="Citi"))
        rows = diff_rows(last, [row_for(pub("a"), NEXT)], NEXT)
        self.assertEqual(rows, [{**{column: "" for column in COLUMNS}, "date": "2026-11-10",
                                 "card_id": "b", "issuer": "Citi", "note": "removed"}])

    def test_already_removed_card_is_not_repeated(self):
        last = {**self.last(pub("a")),
                "b": {**{c: "" for c in COLUMNS}, "date": "2026-11-09", "card_id": "b",
                      "issuer": "Citi", "note": "removed"}}
        self.assertEqual(diff_rows(last, [row_for(pub("a"), NEXT)], NEXT), [])

    def test_card_coming_back_after_removal_is_added_again(self):
        last = {"a": {**{c: "" for c in COLUMNS}, "date": "2026-11-09", "card_id": "a",
                      "issuer": "Chase", "note": "removed"}}
        rows = diff_rows(last, [row_for(pub("a"), NEXT)], NEXT)
        self.assertEqual([(r["card_id"], r["note"]) for r in rows], [("a", "added")])

    def test_new_card_is_added_and_others_stay_quiet(self):
        last = self.last(pub("a"))
        rows = diff_rows(last, [row_for(pub("a"), NEXT), row_for(pub("new"), NEXT)], NEXT)
        self.assertEqual([(r["card_id"], r["note"]) for r in rows], [("new", "added")])

    def test_new_rows_come_before_removed_rows(self):
        last = self.last(pub("old"))
        rows = diff_rows(last, [row_for(pub("new"), NEXT)], NEXT)
        self.assertEqual([(r["card_id"], r["note"]) for r in rows],
                         [("new", "added"), ("old", "removed")])

    def test_inputs_are_not_mutated(self):
        last = self.last(pub("a"))
        new = [row_for(pub("a", min_spend=1), NEXT)]
        before = (repr(last), repr(new))
        diff_rows(last, new, NEXT)
        self.assertEqual((repr(last), repr(new)), before)


class FormatAndParseTest(unittest.TestCase):
    def rows(self):
        return [row_for(pub("a", offer=offer("a")), DAY), row_for(pub("b"), DAY)]

    def test_header_then_rows_with_lf_and_trailing_newline(self):
        text = format_rows(self.rows(), header=True)
        lines = text.split("\n")
        self.assertEqual(lines[0], ",".join(COLUMNS))
        self.assertEqual(len(lines), 4)  # header, 2 rows, "" after the final newline
        self.assertTrue(text.endswith("\n"))
        self.assertNotIn("\r", text)

    def test_without_header(self):
        text = format_rows(self.rows(), header=False)
        self.assertFalse(text.startswith("date,"))

    def test_no_rows_is_empty_text(self):
        self.assertEqual(format_rows([], header=False), "")

    def test_commas_and_quotes_are_quoted_and_round_trip(self):
        tricky = {**row_for(pub("a"), DAY), "issuer": 'Bank, "N.A."'}
        text = format_rows([tricky], header=True)
        self.assertIn('"Bank, ""N.A."""', text)
        self.assertEqual(parse_log(text)["a"]["issuer"], 'Bank, "N.A."')

    def test_parse_returns_the_last_row_per_card_in_first_seen_order(self):
        later = {**row_for(pub("a", min_spend=5000), NEXT)}
        text = format_rows(self.rows(), header=True) + format_rows([later], header=False)
        last = parse_log(text)
        self.assertEqual(list(last), ["a", "b"])
        self.assertEqual((last["a"]["min_spend"], last["a"]["date"]), ("5000", "2026-11-10"))

    def test_empty_text_has_no_rows(self):
        self.assertEqual(parse_log(""), {})

    def test_crlf_file_is_still_read(self):
        text = format_rows(self.rows(), header=True).replace("\n", "\r\n")
        self.assertEqual(list(parse_log(text)), ["a", "b"])

    def test_malformed_files_are_rejected(self):
        header = ",".join(COLUMNS) + "\n"
        good = format_rows([row_for(pub("a"), DAY)], header=False)
        cases = {
            "wrong header": "date,card\n" + good,
            "header only missing": good,
            "too few columns": header + "2026-11-09,a,Chase\n",
            "too many columns": header + good.rstrip("\n") + ",extra\n",
            "blank line": header + "\n" + good,
            "no final newline": header + good.rstrip("\n"),
            "bad quoting": header + good.replace("Chase", '"Ch"ase"'),
            "empty card id": header + good.replace(",a,", ",,", 1),
            "bad date": header + good.replace("2026-11-09", "11/09/2026", 1),
            "unknown note": header + good.rstrip("\n") + "moved\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name), self.assertRaises(BonusLogError) as ctx:
                parse_log(text)
            self.assertTrue(str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
