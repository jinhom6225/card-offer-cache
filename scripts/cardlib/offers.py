"""Offers: one per ``elevated`` block, identified by ``<card_id>@<elevated.start>``.

Moving ``start`` (a raise, or a reopened offer) makes a new id, so the app
notifies again. Lowering or ending never makes a new id. An offer whose
``end`` has passed in America/Los_Angeles is shown as ended
(``ended_auto: true``); cards.yaml itself is never edited by the bot.
"""

from .fields import parse_date
from .schema import PACIFIC

ACTIVE = "active"
ENDED = "ended"


def pacific_date(now):
    """The America/Los_Angeles calendar date at the aware datetime ``now``."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(PACIFIC).date()


def offer_id(card_id, start):
    """``<card_id>@<YYYY-MM-DD>`` for an elevated offer that began on ``start``."""
    return f"{card_id}@{parse_date(start).isoformat()}"


def build_offer(card_id, elevated, today):
    """Public offer dict for a validated ``elevated`` block, or None when there is none.

    Active while ``end`` is null or ``end >= today`` (``today`` is a Pacific date).
    """
    if not elevated:
        return None
    start = parse_date(elevated["start"])
    end_value = elevated.get("end")
    end = parse_date(end_value) if end_value is not None else None
    ended = end is not None and end < today
    return {
        "id": offer_id(card_id, start),
        "status": ENDED if ended else ACTIVE,
        "start": start.isoformat(),
        "end": end.isoformat() if end else None,
        "ended_auto": ended,
    }
