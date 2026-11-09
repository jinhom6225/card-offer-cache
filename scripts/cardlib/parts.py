"""Helpers for bonus ``parts`` (``[{"value": 80000, "unit": "points"}, ...]``).

Shared by the JSON builder, history, build warnings and the staleness report so
that every comparison treats parts the same way: order does not matter and a
whole float (``75000.0``) equals the int (``75000``).
"""

import math


def json_number(value):
    """``75000.0`` -> ``75000`` so Dart's ``as int`` keeps working; others unchanged."""
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def parts_key(parts):
    """Order-insensitive comparison key: sorted ``(unit, value)`` pairs."""
    return sorted((part["unit"], part["value"]) for part in parts)


def _by_unit(parts):
    totals = {}
    for part in parts:
        totals = {**totals, part["unit"]: totals.get(part["unit"], 0) + part["value"]}
    return totals


def is_raise(before, after):
    """True when ``after`` adds a unit or has a higher total for any unit than ``before``."""
    old, new = _by_unit(before), _by_unit(after)
    return any(unit not in old or total > old[unit] for unit, total in new.items())


def format_parts(parts):
    """``80,000 points + 1 free_night`` (whole floats print without ``.0``)."""
    def number(value):
        if isinstance(value, float) and not value.is_integer():
            return f"{value:,}"
        return f"{int(value):,}"
    return " + ".join(f"{number(part['value'])} {part['unit']}" for part in parts)
