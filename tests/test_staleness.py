"""scripts/staleness.py: the daily Telegram reminder (stale cards, auto-ended offers, D3)."""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from helpers import ROOT, TODAY

import staleness


def parts(*pairs):
    return [{"value": value, "unit": unit} for value, unit in pairs]


def card(card_id, last_verified, offer=None, current=((60000, "points"),),
         usual=((60000, "points"),)):
    return {"id": card_id, "name": f"{card_id.title()} Card",
            "last_verified": last_verified.isoformat(),
            "bonus": {"current": {"parts": parts(*current)}, "usual": {"parts": parts(*usual)}},
            "offer": offer}


def ended_offer(card_id, end="2026-11-01"):
    return {"id": f"{card_id}@2026-10-01", "status": "ended", "start": "2026-10-01",
            "end": end, "ended_auto": True}


def active_offer(card_id):
    return {"id": f"{card_id}@2026-10-01", "status": "active", "start": "2026-10-01",
            "end": None, "ended_auto": False}


def payload(*cards):
    return {"schema": 1, "cards": list(cards)}


class StaleCardsTest(unittest.TestCase):
    def test_seven_days_is_not_stale_eight_is(self):
        data = payload(card("fresh", TODAY), card("seven", TODAY - timedelta(days=7)),
                       card("eight", TODAY - timedelta(days=8)))
        stale = staleness.stale_cards(data, TODAY)
        self.assertEqual([(c["id"], c["days"]) for c in stale], [("eight", 8)])
        self.assertEqual(staleness.STALE_AFTER_DAYS, 7)

    def test_oldest_first(self):
        data = payload(card("a", TODAY - timedelta(days=9)), card("b", TODAY - timedelta(days=30)))
        self.assertEqual([c["id"] for c in staleness.stale_cards(data, TODAY)], ["b", "a"])


class EndedOffersTest(unittest.TestCase):
    def test_lists_only_auto_ended_offers(self):
        data = payload(card("a", TODAY, ended_offer("a")), card("b", TODAY, active_offer("b")),
                       card("c", TODAY))
        self.assertEqual([c["id"] for c in staleness.ended_offers(data)], ["a"])


class UnmarkedHigherBonusTest(unittest.TestCase):
    def test_lists_cards_without_offer_whose_current_differs_from_usual(self):
        data = payload(card("plain", TODAY),
                       card("forgot", TODAY, current=((90000, "points"),)),
                       card("marked", TODAY, active_offer("marked"), current=((90000, "points"),)),
                       card("ended", TODAY, ended_offer("ended"), current=((90000, "points"),)),
                       card("reordered", TODAY, current=((1, "free_night"), (5, "points")),
                            usual=((5.0, "points"), (1, "free_night"))))
        self.assertEqual([c["id"] for c in staleness.unmarked_bonus_cards(data)], ["forgot"])

    def test_daily_report_section(self):
        data = payload(card("forgot", TODAY, current=((90000, "points"),)))
        text = staleness.compose_report(data, TODAY, [], daily=True)
        self.assertIn("평소보다 높은 보너스인데 '높음' 표시가 없습니다 — elevated를 넣거나 "
                      "current를 평소 값으로 되돌리세요", text)
        self.assertIn("- forgot (Forgot Card): 현재 90,000 points · 평소 60,000 points", text)
        self.assertEqual(staleness.compose_report(data, TODAY, [], daily=False), "")


class ComposeReportTest(unittest.TestCase):
    def test_combines_all_sections_into_one_message(self):
        data = payload(card("old-card", TODAY - timedelta(days=10)),
                       card("done-card", TODAY, ended_offer("done-card", end="2026-11-05")))
        text = staleness.compose_report(data, TODAY, ["[경고] d3 문장"], daily=True)
        self.assertIn("2026-11-09", text)
        self.assertIn("[경고] d3 문장", text)
        self.assertIn("old-card", text)
        self.assertIn("2026-10-30", text)
        self.assertIn("10일", text)
        self.assertIn("done-card", text)
        self.assertIn("2026-11-05", text)
        self.assertIn("elevated", text)
        self.assertLess(text.index("d3 문장"), text.index("old-card"))

    def test_nothing_to_report_is_empty(self):
        self.assertEqual(staleness.compose_report(payload(card("a", TODAY)), TODAY, [], True), "")

    def test_not_daily_only_reports_warnings(self):
        data = payload(card("old-card", TODAY - timedelta(days=10)))
        self.assertEqual(staleness.compose_report(data, TODAY, [], daily=False), "")
        text = staleness.compose_report(data, TODAY, ["[경고] x"], daily=False)
        self.assertIn("[경고] x", text)
        self.assertNotIn("old-card", text)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.cards = self.dir / "cards_v1.json"
        self.warnings = self.dir / "warnings.txt"

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = staleness.main(["--cards", str(self.cards), "--today", "2026-11-09", *argv])
        return code, out.getvalue(), err.getvalue()

    def write_cards(self, *cards):
        self.cards.write_text(json.dumps(payload(*cards)), encoding="utf-8")

    def test_prints_report_with_warnings_file(self):
        self.write_cards(card("old-card", date(2026, 10, 1)))
        self.warnings.write_text("[경고] 하나\n\n[경고] 둘\n", encoding="utf-8")
        code, out, _ = self.run_main("--warnings-file", str(self.warnings), "--daily")
        self.assertEqual(code, 0)
        self.assertIn("[경고] 하나", out)
        self.assertIn("[경고] 둘", out)
        self.assertIn("old-card", out)

    def test_prints_nothing_when_all_fresh(self):
        self.write_cards(card("a", TODAY))
        code, out, _ = self.run_main("--daily")
        self.assertEqual((code, out), (0, ""))

    def test_missing_warnings_file_means_no_warnings(self):
        self.write_cards(card("a", TODAY))
        code, out, _ = self.run_main("--warnings-file", str(self.dir / "nope.txt"))
        self.assertEqual((code, out), (0, ""))

    def test_missing_or_broken_cards_json_fails_in_korean_on_stderr(self):
        code, out, err = self.run_main("--daily")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("읽을 수 없습니다", err)
        for text in ("{nope", "[]", '{"cards": 1}'):
            self.cards.write_text(text, encoding="utf-8")
            code, out, err = self.run_main("--daily")
            self.assertEqual((code, out), (1, ""))
            self.assertIn("읽을 수 없습니다", err)

    def test_default_cards_path(self):
        self.assertEqual(staleness.DEFAULT_CARDS, ROOT / "docs" / "cards_v1.json")


if __name__ == "__main__":
    unittest.main()
