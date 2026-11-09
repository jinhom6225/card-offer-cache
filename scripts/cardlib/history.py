"""Per-card bonus history, built by comparing with the previous cards_v1.json.

Each build adds at most one event per card (priority elevated > ended > changed):

- ``elevated``: the card now has an active offer whose id was not already active
  (first "높음" mark, a raise with a new ``start``, a reopened offer).
- ``ended``: an active offer disappeared or auto-ended.
- ``changed``: ``bonus.current.parts`` changed otherwise.

Bonus parts compare order-insensitively (see ``parts.parts_key``). Carried-forward
entries keep only ``date``, ``type`` and ``current_parts`` (``value``/``unit``).
Build warnings come from ``offer_warnings``.
"""

from .offer_warnings import card_warnings, removed_card_warnings
from .offers import ACTIVE
from .parts import json_number, parts_key

MAX_HISTORY = 20


def _parts(card):
    return card["bonus"]["current"]["parts"]


def _active_offer_id(card):
    offer = card.get("offer") if card else None
    if offer and offer.get("status") == ACTIVE:
        return offer.get("id")
    return None


def card_event(prev_card, new_card):
    """Event type for this build (``elevated``/``ended``/``changed``) or None."""
    new_active = _active_offer_id(new_card)
    prev_active = _active_offer_id(prev_card)
    if new_active and new_active != prev_active:
        return "elevated"
    if prev_active and not new_active:
        return "ended"
    if prev_card and parts_key(_parts(prev_card)) != parts_key(_parts(new_card)):
        return "changed"
    return None


def _clean_part(part):
    return {key: json_number(part[key]) for key in ("value", "unit") if key in part}


def _clean_entry(entry):
    """A carried-forward history entry with only the published keys."""
    clean = {key: entry[key] for key in ("date", "type") if key in entry}
    parts = entry.get("current_parts")
    if isinstance(parts, list):
        clean["current_parts"] = [_clean_part(p) for p in parts if isinstance(p, dict)]
    return clean


def update_history(prev_card, new_card, today):
    """Previous history plus this build's event (if any), newest ``MAX_HISTORY`` kept."""
    history = [_clean_entry(entry) for entry in (prev_card or {}).get("history", [])]
    event_type = card_event(prev_card, new_card)
    if event_type:
        history = history + [{
            "date": today.isoformat(),
            "type": event_type,
            "current_parts": [{"value": p["value"], "unit": p["unit"]}
                              for p in _parts(new_card)],
        }]
    return history[-MAX_HISTORY:]


def apply_history(previous, new_cards, today):
    """Return ``(cards with history, warnings)``; ``previous`` is the old payload or None."""
    prev_cards = (previous or {}).get("cards", [])
    prev_by_id = {card["id"]: card for card in prev_cards}
    cards, warnings = [], []
    for card in new_cards:
        prev_card = prev_by_id.get(card["id"])
        cards.append({**card, "history": update_history(prev_card, card, today)})
        warnings.extend(card_warnings(prev_card, card))
    return cards, warnings + removed_card_warnings(prev_cards, new_cards)
