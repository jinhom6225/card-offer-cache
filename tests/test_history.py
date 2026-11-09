"""Per-card bonus history and the D3 warning (same offer id, changed bonus)."""

import copy
import unittest

from helpers import TODAY

from cardlib.history import MAX_HISTORY, apply_history, card_event, update_history


def offer(offer_id="card@2026-10-01", status="active"):
    return {"id": offer_id, "status": status, "start": offer_id.split("@")[1],
            "end": None, "ended_auto": status == "ended"}


def pub(card_id="card", parts=((75000, "points"),), the_offer=None, history=()):
    """A public card as it appears in cards_v1.json (only the fields history reads)."""
    return {
        "id": card_id,
        "name": f"{card_id} name",
        "bonus": {"current": {"parts": [{"value": v, "unit": u} for v, u in parts]}},
        "offer": the_offer,
        "history": list(history),
    }


def event(type_, parts=((75000, "points"),), day="2026-11-01"):
    return {"date": day, "type": type_,
            "current_parts": [{"value": v, "unit": u} for v, u in parts]}


class CardEventTest(unittest.TestCase):
    def test_new_card_with_active_offer_is_elevated(self):
        self.assertEqual(card_event(None, pub(the_offer=offer())), "elevated")

    def test_new_card_without_offer_has_no_event(self):
        self.assertIsNone(card_event(None, pub()))

    def test_offer_appears_is_elevated(self):
        self.assertEqual(card_event(pub(), pub(the_offer=offer())), "elevated")

    def test_raise_with_new_start_is_elevated(self):
        prev = pub(the_offer=offer("card@2026-10-01"))
        new = pub(parts=((90000, "points"),), the_offer=offer("card@2026-11-09"))
        self.assertEqual(card_event(prev, new), "elevated")

    def test_reopen_after_auto_end_is_elevated(self):
        prev = pub(the_offer=offer("card@2026-09-01", "ended"))
        new = pub(the_offer=offer("card@2026-11-05"))
        self.assertEqual(card_event(prev, new), "elevated")

    def test_elevated_block_removed_is_ended(self):
        self.assertEqual(card_event(pub(the_offer=offer()), pub()), "ended")

    def test_auto_end_is_ended(self):
        prev = pub(the_offer=offer())
        self.assertEqual(card_event(prev, pub(the_offer=offer(status="ended"))), "ended")

    def test_lowered_and_ended_is_one_ended_event(self):
        prev = pub(parts=((90000, "points"),), the_offer=offer())
        new = pub(parts=((60000, "points"),))
        self.assertEqual(card_event(prev, new), "ended")

    def test_still_ended_has_no_event(self):
        ended = offer(status="ended")
        self.assertIsNone(card_event(pub(the_offer=ended), pub(the_offer=ended)))

    def test_bonus_change_without_offer_is_changed(self):
        self.assertEqual(card_event(pub(), pub(parts=((50000, "points"),))), "changed")

    def test_bonus_change_with_same_offer_id_is_changed(self):
        prev = pub(the_offer=offer())
        new = pub(parts=((90000, "points"),), the_offer=offer())
        self.assertEqual(card_event(prev, new), "changed")

    def test_nothing_changed_has_no_event(self):
        self.assertIsNone(card_event(pub(the_offer=offer()), pub(the_offer=offer())))

    def test_int_and_float_with_same_value_are_not_a_change(self):
        self.assertIsNone(card_event(pub(parts=((1.5, "cash"),)), pub(parts=((1.5, "cash"),))))
        self.assertIsNone(card_event(pub(parts=((75000.0, "points"),)), pub()))

    def test_unit_change_is_a_change(self):
        self.assertEqual(card_event(pub(), pub(parts=((75000, "miles"),))), "changed")

    def test_reordered_parts_are_not_a_change(self):
        two = ((80000, "points"), (1, "free_night"))
        self.assertIsNone(card_event(pub(parts=two), pub(parts=tuple(reversed(two)))))


class UpdateHistoryTest(unittest.TestCase):
    def test_appends_event_with_date_type_and_current_parts(self):
        prev = pub(history=[event("elevated")])
        new = pub(parts=((50000, "points"),))
        history = update_history(prev, new, TODAY)
        self.assertEqual(history, [
            event("elevated"),
            {"date": "2026-11-09", "type": "changed",
             "current_parts": [{"value": 50000, "unit": "points"}]},
        ])
        self.assertEqual(list(history[-1]), ["date", "type", "current_parts"])

    def test_no_event_keeps_previous_history(self):
        prev = pub(history=[event("elevated")])
        self.assertEqual(update_history(prev, pub(), TODAY), [event("elevated")])

    def test_new_card_starts_empty_or_with_elevated(self):
        self.assertEqual(update_history(None, pub(), TODAY), [])
        self.assertEqual([e["type"] for e in update_history(None, pub(the_offer=offer()), TODAY)],
                         ["elevated"])

    def test_keeps_only_the_newest_twenty(self):
        old = [event("changed", day=f"2026-01-{i:02d}") for i in range(1, 21)]
        history = update_history(pub(history=old), pub(parts=((1, "points"),)), TODAY)
        self.assertEqual(MAX_HISTORY, 20)
        self.assertEqual(len(history), 20)
        self.assertEqual(history[0]["date"], "2026-01-02")
        self.assertEqual(history[-1]["date"], "2026-11-09")

    def test_previous_history_over_cap_is_trimmed(self):
        old = [event("changed", day=f"2026-02-{i:02d}") for i in range(1, 26)]
        self.assertEqual(len(update_history(pub(history=old), pub(), TODAY)), 20)

    def test_carried_history_keeps_only_allowed_keys(self):
        dirty = {"date": "2026-11-01", "type": "changed", "note": "<script>",
                 "current_parts": [{"value": 75000.0, "unit": "points", "url": "x"},
                                   {"unit": "cash"}, "junk"]}
        history = update_history(pub(history=[dirty]), pub(), TODAY)
        self.assertEqual(history, [{"date": "2026-11-01", "type": "changed",
                                    "current_parts": [{"value": 75000, "unit": "points"},
                                                      {"unit": "cash"}]}])
        self.assertIs(type(history[0]["current_parts"][0]["value"]), int)

    def test_carried_history_drops_bad_current_parts_and_missing_keys(self):
        history = update_history(pub(history=[{"type": "ended", "current_parts": "x"}]),
                                 pub(), TODAY)
        self.assertEqual(history, [{"type": "ended"}])

    def test_does_not_mutate_inputs(self):
        prev = pub(history=[event("elevated")])
        new = pub(parts=((50000, "points"),))
        prev_copy, new_copy = copy.deepcopy(prev), copy.deepcopy(new)
        history = update_history(prev, new, TODAY)
        history[-1]["current_parts"][0]["value"] = 1
        self.assertEqual(prev, prev_copy)
        self.assertEqual(new, new_copy)


class ApplyHistoryTest(unittest.TestCase):
    def test_without_previous_json(self):
        cards, warnings = apply_history(None, [pub("a", the_offer=offer("a@2026-10-01")),
                                               pub("b")], TODAY)
        self.assertEqual([len(c["history"]) for c in cards], [1, 0])
        self.assertEqual(warnings, [])

    def test_matches_previous_cards_by_id_and_collects_warnings(self):
        previous = {"cards": [pub("b"), pub("a", the_offer=offer("a@2026-10-01")),
                              pub("gone")]}
        new = [pub("a", parts=((1, "points"),), the_offer=offer("a@2026-10-01")), pub("b")]
        cards, warnings = apply_history(previous, new, TODAY)
        self.assertEqual([c["id"] for c in cards], ["a", "b"])
        self.assertEqual([e["type"] for e in cards[0]["history"]], ["changed"])
        self.assertEqual(cards[1]["history"], [])
        self.assertEqual(len(warnings), 2)
        self.assertTrue(warnings[0].startswith("[경고] a: '높음' 오퍼"))
        self.assertTrue(warnings[1].startswith("[경고] gone: 카드가 cards.yaml에서 빠져"))

    def test_collects_reopen_and_restart_warnings(self):
        previous = {"cards": [pub("r", the_offer=offer("r@2026-10-01", "ended")),
                              pub("s", the_offer=offer("s@2026-10-01"))]}
        new = [pub("r", the_offer=offer("r@2026-10-01")),
               pub("s", the_offer=offer("s@2026-11-09"))]
        _, warnings = apply_history(previous, new, TODAY)
        self.assertEqual([w.split(":")[0] for w in warnings], ["[경고] r", "[경고] s"])
        self.assertIn("다시 열렸습니다", warnings[0])
        self.assertIn("start를 되돌리세요", warnings[1])

    def test_genuine_raise_with_new_start_has_no_warning(self):
        previous = {"cards": [pub("s", the_offer=offer("s@2026-10-01"))]}
        new = [pub("s", parts=((90000, "points"),), the_offer=offer("s@2026-11-09"))]
        cards, warnings = apply_history(previous, new, TODAY)
        self.assertEqual(warnings, [])
        self.assertEqual([e["type"] for e in cards[0]["history"]], ["elevated"])

    def test_keeps_card_key_order_with_history_last(self):
        cards, _ = apply_history(None, [pub("a")], TODAY)
        self.assertEqual(list(cards[0]), ["id", "name", "bonus", "offer", "history"])

    def test_does_not_mutate_new_cards(self):
        new = [pub("a", the_offer=offer("a@2026-10-01"))]
        snapshot = copy.deepcopy(new)
        apply_history(None, new, TODAY)
        self.assertEqual(new, snapshot)


if __name__ == "__main__":
    unittest.main()
