"""Build warnings sent to Telegram: D3, reopened same id, new start without raise, removed card."""

import copy
import unittest

import helpers  # noqa: F401  (puts scripts/ on sys.path)

from cardlib.offer_warnings import (card_warnings, d3_warning, removed_card_warnings,
                                    reopened_warning, restart_warning)


def offer(offer_id="card@2026-10-01", status="active"):
    return {"id": offer_id, "status": status, "start": offer_id.split("@")[1],
            "end": None, "ended_auto": status == "ended"}


def pub(card_id="card", parts=((75000, "points"),), the_offer=None, history=()):
    return {"id": card_id, "name": f"{card_id} name",
            "bonus": {"current": {"parts": [{"value": v, "unit": u} for v, u in parts]}},
            "offer": the_offer, "history": list(history)}


class D3WarningTest(unittest.TestCase):
    def test_same_offer_id_with_changed_parts_warns(self):
        prev = pub(card_id="chase-sp", the_offer=offer("chase-sp@2026-10-01"))
        new = pub(card_id="chase-sp", parts=((90000, "points"), (1, "free_night")),
                  the_offer=offer("chase-sp@2026-10-01"))
        message = d3_warning(prev, new)
        self.assertTrue(message.startswith("[경고] chase-sp: "))
        self.assertIn("75,000 points", message)
        self.assertIn("90,000 points + 1 free_night", message)
        self.assertIn("start가 이미 오늘이면 어제 날짜로", message)

    def test_unchanged_or_reordered_parts_do_not_warn(self):
        two = ((80000, "points"), (1, "free_night"))
        self.assertIsNone(d3_warning(pub(the_offer=offer()), pub(the_offer=offer())))
        self.assertIsNone(d3_warning(pub(parts=two, the_offer=offer()),
                                     pub(parts=tuple(reversed(two)), the_offer=offer())))

    def test_new_start_does_not_warn(self):
        prev = pub(the_offer=offer("card@2026-10-01"))
        new = pub(parts=((90000, "points"),), the_offer=offer("card@2026-11-09"))
        self.assertIsNone(d3_warning(prev, new))

    def test_no_offer_new_card_or_auto_ended_does_not_warn(self):
        self.assertIsNone(d3_warning(pub(), pub(parts=((1, "points"),))))
        self.assertIsNone(d3_warning(None, pub(the_offer=offer())))
        prev = pub(the_offer=offer(status="ended"))
        self.assertIsNone(d3_warning(prev, pub(parts=((6, "points"),),
                                               the_offer=offer(status="ended"))))

    def test_previously_ended_same_id_is_left_to_the_reopen_warning(self):
        prev = pub(the_offer=offer(status="ended"))
        new = pub(parts=((90000, "points"),), the_offer=offer())
        self.assertIsNone(d3_warning(prev, new))
        self.assertEqual(len(card_warnings(prev, new)), 1)


class ReopenedWarningTest(unittest.TestCase):
    def test_ended_then_active_with_same_id_warns(self):
        prev = pub("amex-gold", the_offer=offer("amex-gold@2026-10-01", "ended"))
        new = pub("amex-gold", the_offer=offer("amex-gold@2026-10-01"))
        self.assertEqual(reopened_warning(prev, new), (
            "[경고] amex-gold: 끝났던 오퍼가 같은 start로 다시 열렸습니다. 다시 열린 것이면 "
            "start를 오늘(이미 오늘이면 어제)로 바꾸세요. 종료일 연장이면 무시하세요."))

    def test_ended_auto_flag_alone_counts_as_ended(self):
        ended = {**offer(), "ended_auto": True}
        self.assertIsNotNone(reopened_warning(pub(the_offer=ended), pub(the_offer=offer())))

    def test_new_id_still_active_or_still_ended_does_not_warn(self):
        ended = pub(the_offer=offer("card@2026-09-01", "ended"))
        self.assertIsNone(reopened_warning(ended, pub(the_offer=offer("card@2026-11-05"))))
        self.assertIsNone(reopened_warning(pub(the_offer=offer()), pub(the_offer=offer())))
        self.assertIsNone(reopened_warning(ended, ended))
        self.assertIsNone(reopened_warning(None, pub(the_offer=offer())))


class RestartWarningTest(unittest.TestCase):
    def assert_warns(self, before, after):
        prev = pub("citi-p", parts=before, the_offer=offer("citi-p@2026-10-01"))
        new = pub("citi-p", parts=after, the_offer=offer("citi-p@2026-11-09"))
        return restart_warning(prev, new)

    def test_new_start_with_same_or_lower_bonus_warns(self):
        for after in (((75000, "points"),), ((60000, "points"),)):
            with self.subTest(after=after):
                self.assertEqual(self.assert_warns(((75000, "points"),), after), (
                    "[경고] citi-p: start가 바뀌어 사용자에게 다시 알림이 갑니다. "
                    "보너스가 오르지 않았다면 start를 되돌리세요."))

    def test_genuine_raise_or_new_unit_does_not_warn(self):
        self.assertIsNone(self.assert_warns(((75000, "points"),), ((90000, "points"),)))
        self.assertIsNone(self.assert_warns(((75000, "points"),),
                                            ((75000, "points"), (1, "free_night"))))

    def test_only_when_previous_offer_was_active(self):
        prev = pub(the_offer=offer("card@2026-09-01", "ended"))
        self.assertIsNone(restart_warning(prev, pub(the_offer=offer("card@2026-11-09"))))
        self.assertIsNone(restart_warning(pub(), pub(the_offer=offer("card@2026-11-09"))))
        self.assertIsNone(restart_warning(pub(the_offer=offer()), pub()))


class RemovedCardWarningsTest(unittest.TestCase):
    def test_removed_card_warns_with_history_count(self):
        previous = [pub("a"), pub("gone", history=[{"date": "2026-11-01"}] * 3)]
        warnings = removed_card_warnings(previous, [pub("a")])
        self.assertEqual(warnings, [
            "[경고] gone: 카드가 cards.yaml에서 빠져 앱에서 사라지고 변동 기록(3건)도 "
            "지워졌습니다. 실수면 cards.yaml을 되돌리세요(id를 바꾼 경우도 같음)."])

    def test_renamed_id_warns_for_the_old_id(self):
        warnings = removed_card_warnings([pub("old-id")], [pub("new-id")])
        self.assertEqual(len(warnings), 1)
        self.assertIn("old-id", warnings[0])
        self.assertIn("0건", warnings[0])

    def test_nothing_removed_or_no_previous(self):
        self.assertEqual(removed_card_warnings([pub("a")], [pub("a"), pub("b")]), [])
        self.assertEqual(removed_card_warnings([], [pub("a")]), [])

    def test_does_not_mutate_inputs(self):
        previous, new = [pub("gone")], [pub("a")]
        snapshot = copy.deepcopy((previous, new))
        removed_card_warnings(previous, new)
        self.assertEqual((previous, new), snapshot)


if __name__ == "__main__":
    unittest.main()
