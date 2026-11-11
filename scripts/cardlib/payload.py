"""Turn validated cards.yaml cards into the public ``docs/cards_v1.json`` (schema 1).

Only listed keys are published, in a fixed order, so the same content always
serializes to the same bytes (stable Pages ETag). ``sources`` and unknown keys
are dropped; empty optional texts (``note_en`` and the ``ko``/``ja``/``es``
translations, plan A7) are omitted so the app falls back to English. Whole floats (``75000.0``) are published as ints;
decimals (``2.7``) stay decimals, so the app must read numbers as ``num``.
"""

import json
from datetime import datetime, timezone

from .fields import parse_date
from .history import apply_history
from .offers import build_offer
from .parts import json_number

SCHEMA_VERSION = 1
PREVIOUS_NAME = "docs/cards_v1.json"
PUBLIC_CARD_KEYS = (
    "id", "name", "issuer", "segment", "official_url", "last_verified", "annual_fee",
    "foreign_tx_fee_pct", "bonus", "offer", "earn", "benefits", "history")


NOTE_KEYS = ("note_en", "note_ko", "note_ja", "note_es")
CATEGORY_TRANSLATION_KEYS = ("category_ko", "category_ja", "category_es")
BENEFIT_TRANSLATION_KEYS = ("ko", "ja", "es")


class PreviousJsonError(Exception):
    """The previous cards_v1.json could not be used (message is Korean)."""


def _with_optional_text(base, source, keys):
    """``base`` plus each ``source[key]`` that is non-blank text, in ``keys`` order."""
    extra = {key: source[key] for key in keys
             if isinstance(source.get(key), str) and source[key].strip()}
    return {**base, **extra}


def _parts(parts):
    return [{"value": json_number(part["value"]), "unit": part["unit"]} for part in parts]


def _bonus(bonus):
    current, usual = bonus["current"], bonus["usual"]
    return {
        "current": _with_optional_text({
            "parts": _parts(current["parts"]),
            "min_spend": json_number(current["min_spend"]),
            "spend_months": json_number(current["spend_months"]),
        }, current, NOTE_KEYS),
        "usual": _with_optional_text({"parts": _parts(usual["parts"])}, usual, NOTE_KEYS),
    }


def _earn(item):
    base = {"category_en": item["category_en"]}
    with_text = _with_optional_text(base, item, CATEGORY_TRANSLATION_KEYS)
    return {**with_text, "rate": json_number(item["rate"]), "unit": item["unit"]}


def public_card(card, today):
    """Public dict for one validated card (``history`` empty; filled by apply_history)."""
    fee = card["annual_fee"]
    return {
        "id": card["id"],
        "name": card["name"],
        "issuer": card["issuer"],
        "segment": card["segment"],
        "official_url": card["official_url"],
        "last_verified": parse_date(card["last_verified"]).isoformat(),
        "annual_fee": {"amount": json_number(fee["amount"]),
                       "first_year_waived": fee["first_year_waived"]},
        "foreign_tx_fee_pct": json_number(card["foreign_tx_fee_pct"]),
        "bonus": _bonus(card["bonus"]),
        "offer": build_offer(card["id"], card.get("elevated"), today),
        "earn": [_earn(item) for item in card["earn"]],
        "benefits": [_with_optional_text({"en": b["en"]}, b, BENEFIT_TRANSLATION_KEYS)
                     for b in card["benefits"]],
        "history": [],
    }


def build_payload(cards, previous, today, generated_at, data_updated_at):
    """Return ``(payload, warnings)``. ``previous`` is the old payload or None."""
    public = [public_card(card, today) for card in cards]
    with_history, warnings = apply_history(previous, public, today)
    payload = {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "data_updated_at": data_updated_at,
        "cards": with_history,
    }
    return payload, warnings


def serialize(payload):
    """Deterministic JSON text (insertion order, UTF-8 text, trailing newline). NaN raises."""
    return json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def same_content(new, previous, previous_text):
    """True when the old file's bytes equal ``new`` serialized with the old ``generated_at``.

    Compares text, not dicts, so a representation change (``75000.0`` -> ``75000``,
    indentation, line endings) rewrites the file. ``previous`` None = no old file.
    """
    if previous is None or previous_text is None:
        return False
    return serialize({**new, "generated_at": previous.get("generated_at")}) == previous_text


def iso_utc(moment):
    """``YYYY-MM-DDTHH:MM:SSZ`` for an aware datetime (seconds precision)."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_timestamp(text):
    """An ISO 8601 time with offset (e.g. ``git log --format=%cI``) as UTC ``...Z``."""
    try:
        moment = datetime.fromisoformat(text.strip())
    except ValueError as exc:
        raise ValueError(f"ISO 8601 시각이 아닙니다: {text!r}") from exc
    if moment.tzinfo is None:
        raise ValueError(f"시간대(+00:00 등)가 없는 시각입니다: {text!r}")
    return iso_utc(moment)


def _reject_constant(name):
    raise ValueError(f"허용되지 않는 숫자 {name}")


def _is_part(part):
    value = part.get("value") if isinstance(part, dict) else None
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isinstance(part.get("unit"), str))


def _card_problem(card):
    """What is wrong with one previous card (only the fields the build reads), or None."""
    if not isinstance(card, dict) or not isinstance(card.get("id"), str):
        return "id가 없는 카드가 있습니다."
    label = card["id"]
    if not (card.get("offer") is None or isinstance(card["offer"], dict)):
        return f"{label}: offer가 객체나 null이 아닙니다."
    bonus = card.get("bonus")
    current = bonus.get("current") if isinstance(bonus, dict) else None
    parts = current.get("parts") if isinstance(current, dict) else None
    if not isinstance(parts, list) or not all(_is_part(part) for part in parts):
        return f"{label}: bonus.current.parts 모양이 다릅니다."
    history = card.get("history", [])
    if not isinstance(history, list) or not all(isinstance(e, dict) for e in history):
        return f"{label}: history가 객체 목록이 아닙니다."
    return None


def _check_previous_shape(doc):
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_VERSION:
        return f"schema {SCHEMA_VERSION} 형식이 아닙니다."
    cards = doc.get("cards")
    if not isinstance(cards, list):
        return "cards 목록이 없습니다."
    return next((problem for problem in map(_card_problem, cards) if problem), None)


def parse_previous(text):
    """Parse the previous cards_v1.json. Broken files raise PreviousJsonError, never ignored."""
    try:
        doc = json.loads(text, parse_constant=_reject_constant)
    except ValueError as exc:
        raise PreviousJsonError(
            f"{PREVIOUS_NAME}: 이전 JSON을 읽을 수 없습니다({exc}). 변동 기록을 지키기 위해 "
            "빌드를 멈춥니다. 파일을 git에서 이전 버전으로 되돌려 주세요.") from exc
    problem = _check_previous_shape(doc)
    if problem:
        raise PreviousJsonError(
            f"{PREVIOUS_NAME}: 이전 JSON의 모양이 맞지 않습니다({problem}). 변동 기록을 "
            "지키기 위해 빌드를 멈춥니다. 파일을 git에서 이전 버전으로 되돌려 주세요.")
    return doc


__all__ = ["SCHEMA_VERSION", "PUBLIC_CARD_KEYS", "PreviousJsonError", "public_card",
           "build_payload", "serialize", "same_content", "iso_utc", "normalize_timestamp",
           "parse_previous"]
