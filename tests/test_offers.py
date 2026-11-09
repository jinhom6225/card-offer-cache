"""Offer ids, active/ended status and the US Pacific date used for auto-ending."""

import unittest
from datetime import date, datetime, timedelta, timezone

from helpers import TODAY

from cardlib.offers import build_offer, offer_id, pacific_date


def elevated(start="2026-10-01", end="2026-12-31"):
    return {"start": start, "end": end}


class OfferIdTest(unittest.TestCase):
    def test_id_is_card_id_at_start_date(self):
        self.assertEqual(offer_id("chase-sapphire", date(2026, 11, 1)),
                         "chase-sapphire@2026-11-01")

    def test_id_accepts_iso_string_start(self):
        self.assertEqual(offer_id("chase-sapphire", "2026-11-01"), "chase-sapphire@2026-11-01")

    def test_offer_carries_the_id(self):
        offer = build_offer("chase-sapphire", elevated(start=date(2026, 10, 1)), TODAY)
        self.assertEqual(offer["id"], "chase-sapphire@2026-10-01")

    def test_raise_with_start_moved_to_today_gives_new_id(self):
        before = build_offer("card", elevated(start="2026-10-01"), TODAY)
        raised = build_offer("card", elevated(start="2026-11-09"), TODAY)
        self.assertNotEqual(before["id"], raised["id"])
        self.assertEqual(raised["status"], "active")

    def test_reopened_offer_gets_new_id(self):
        first = build_offer("card", elevated(start="2026-09-01", end="2026-09-30"), TODAY)
        reopened = build_offer("card", elevated(start="2026-11-05", end=None), TODAY)
        self.assertEqual(first["status"], "ended")
        self.assertEqual(reopened["status"], "active")
        self.assertNotEqual(first["id"], reopened["id"])

    def test_changing_end_keeps_the_same_id(self):
        short = build_offer("card", elevated(end="2026-11-30"), TODAY)
        longer = build_offer("card", elevated(end="2027-01-31"), TODAY)
        self.assertEqual(short["id"], longer["id"])

    def test_no_elevated_block_means_no_offer(self):
        self.assertIsNone(build_offer("card", None, TODAY))


class StatusTest(unittest.TestCase):
    def test_active_offer_shape(self):
        offer = build_offer("card", elevated(start=date(2026, 10, 1), end=date(2026, 12, 31)),
                            TODAY)
        self.assertEqual(offer, {"id": "card@2026-10-01", "status": "active",
                                 "start": "2026-10-01", "end": "2026-12-31",
                                 "ended_auto": False})
        self.assertEqual(list(offer), ["id", "status", "start", "end", "ended_auto"])

    def test_active_on_the_end_date(self):
        offer = build_offer("card", elevated(end="2026-11-09"), TODAY)
        self.assertEqual(offer["status"], "active")
        self.assertFalse(offer["ended_auto"])

    def test_ended_the_day_after_end(self):
        offer = build_offer("card", elevated(end="2026-11-08"), TODAY)
        self.assertEqual(offer["status"], "ended")
        self.assertTrue(offer["ended_auto"])

    def test_end_null_never_auto_ends(self):
        offer = build_offer("card", elevated(end=None), date(2030, 1, 1))
        self.assertEqual(offer["status"], "active")
        self.assertIsNone(offer["end"])
        self.assertFalse(offer["ended_auto"])

    def test_missing_end_key_is_same_as_null(self):
        offer = build_offer("card", {"start": "2026-10-01"}, TODAY)
        self.assertEqual(offer["status"], "active")
        self.assertIsNone(offer["end"])

    def test_does_not_mutate_elevated(self):
        block = elevated(start=date(2026, 10, 1))
        build_offer("card", block, TODAY)
        self.assertEqual(block, {"start": date(2026, 10, 1), "end": "2026-12-31"})


class PacificDateTest(unittest.TestCase):
    """Auto-end flips at midnight in America/Los_Angeles, not at UTC midnight."""

    def test_winter_last_second_of_end_day_in_pacific(self):
        now = datetime(2027, 1, 1, 7, 59, 59, tzinfo=timezone.utc)  # 23:59:59 PST
        self.assertEqual(pacific_date(now), date(2026, 12, 31))

    def test_winter_first_second_of_next_day_in_pacific(self):
        now = datetime(2027, 1, 1, 8, 0, 0, tzinfo=timezone.utc)  # 00:00 PST
        self.assertEqual(pacific_date(now), date(2027, 1, 1))

    def test_summer_uses_daylight_time(self):
        self.assertEqual(pacific_date(datetime(2026, 7, 1, 6, 59, tzinfo=timezone.utc)),
                         date(2026, 6, 30))
        self.assertEqual(pacific_date(datetime(2026, 7, 1, 7, 0, tzinfo=timezone.utc)),
                         date(2026, 7, 1))

    def test_other_offsets_are_converted(self):
        seoul = timezone(timedelta(hours=9))
        self.assertEqual(pacific_date(datetime(2027, 1, 1, 12, 0, tzinfo=seoul)),
                         date(2026, 12, 31))

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(ValueError):
            pacific_date(datetime(2027, 1, 1, 8, 0))

    def test_auto_end_boundary_with_utc_clock(self):
        block = elevated(end="2026-12-31")
        late = build_offer("card", block,
                           pacific_date(datetime(2027, 1, 1, 7, 59, 59, tzinfo=timezone.utc)))
        after = build_offer("card", block,
                            pacific_date(datetime(2027, 1, 1, 8, 0, tzinfo=timezone.utc)))
        self.assertEqual(late["status"], "active")
        self.assertEqual(after["status"], "ended")
        self.assertTrue(after["ended_auto"])


if __name__ == "__main__":
    unittest.main()
