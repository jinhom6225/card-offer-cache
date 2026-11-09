"""Bonus parts helpers shared by payload, history, warnings and staleness."""

import unittest

import helpers  # noqa: F401  (puts scripts/ on sys.path)

from cardlib.parts import format_parts, is_raise, json_number, parts_key


def parts(*pairs):
    return [{"value": value, "unit": unit} for value, unit in pairs]


class JsonNumberTest(unittest.TestCase):
    def test_whole_floats_become_ints(self):
        for value, expected in ((3.0, 3), (75000.0, 75000), (95.0, 95), (0.0, 0)):
            with self.subTest(value=value):
                result = json_number(value)
                self.assertEqual(result, expected)
                self.assertIs(type(result), int)

    def test_decimals_ints_and_other_values_are_kept(self):
        for value in (2.7, 1.5, 4000, True, None, "x"):
            with self.subTest(value=value):
                self.assertIs(json_number(value), value)

    def test_non_finite_floats_are_kept_for_serialize_to_reject(self):
        self.assertEqual(json_number(float("inf")), float("inf"))


class PartsKeyTest(unittest.TestCase):
    def test_order_insensitive(self):
        a = parts((80000, "points"), (1, "free_night"))
        b = parts((1, "free_night"), (80000, "points"))
        self.assertEqual(parts_key(a), parts_key(b))

    def test_int_and_whole_float_are_equal(self):
        self.assertEqual(parts_key(parts((75000.0, "points"))), parts_key(parts((75000, "points"))))

    def test_value_or_unit_change_differs(self):
        base = parts_key(parts((75000, "points")))
        self.assertNotEqual(base, parts_key(parts((75001, "points"))))
        self.assertNotEqual(base, parts_key(parts((75000, "miles"))))


class IsRaiseTest(unittest.TestCase):
    def test_higher_value_is_a_raise(self):
        self.assertTrue(is_raise(parts((75000, "points")), parts((90000, "points"))))

    def test_new_unit_is_a_raise(self):
        self.assertTrue(is_raise(parts((75000, "points")),
                                 parts((75000, "points"), (1, "free_night"))))

    def test_one_unit_up_another_down_is_a_raise(self):
        before = parts((75000, "points"), (300, "credit"))
        self.assertTrue(is_raise(before, parts((90000, "points"), (100, "credit"))))

    def test_equal_lower_or_dropped_units_are_not_a_raise(self):
        before = parts((75000, "points"), (1, "free_night"))
        for after in (before, list(reversed(before)), parts((60000, "points")),
                      parts((75000, "points"), (1.0, "free_night"))):
            with self.subTest(after=after):
                self.assertFalse(is_raise(before, after))

    def test_repeated_units_are_summed(self):
        before = parts((50000, "points"), (25000, "points"))
        self.assertFalse(is_raise(before, parts((75000, "points"))))
        self.assertTrue(is_raise(before, parts((80000, "points"))))


class FormatPartsTest(unittest.TestCase):
    def test_formats_numbers_with_commas_and_joins_parts(self):
        self.assertEqual(format_parts(parts((80000, "points"), (1.5, "cash"), (2.0, "free_night"))),
                         "80,000 points + 1.5 cash + 2 free_night")


if __name__ == "__main__":
    unittest.main()
