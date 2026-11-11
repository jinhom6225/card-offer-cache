"""Load data/cards.yaml and validate it. Messages are Korean for the human editor."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .fields import Bool, Date, ListOf, Mapping, Number, Text, Url, parse_date
from .issues import error, warning
from .loader import CardFileError, CardLoader, parse_yaml
from .rules import check_text_content
from .urls import ISSUER_DOMAINS, is_issuer_url

__all__ = ["CardFileError", "CardLoader", "load_cards", "validate", "parse_date",
           "today_pt", "CARD_SPEC", "TRANSLATION_LANGS"]

PACIFIC = ZoneInfo("America/Los_Angeles")
EXPECTED_CARD_COUNT = 30
SEGMENTS = ("personal", "business")
BONUS_UNITS = ("points", "miles", "cash", "free_night", "credit", "percent_match")
EARN_UNITS = ("points", "miles", "cash")
ID_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ID_HINT = "소문자·숫자와 '-'만 쓰세요(예: chase-sapphire-preferred)."
WHOLE_FILE = "전체"


# Optional translations (plan A7). Blank = the app shows the English text.
TRANSLATION_LANGS = ("ko", "ja", "es")


def _optional_text():
    return Text(required=False)


def _translations(prefix):
    """``{prefix}ko``, ``{prefix}ja``, ``{prefix}es`` as optional texts (e.g. ``note_ko``)."""
    return {f"{prefix}{lang}": _optional_text() for lang in TRANSLATION_LANGS}


def _strict(fields, required=True):
    """Bonus/elevated blocks: a typo there silently changes an offer, so unknown keys fail."""
    return Mapping(fields, required=required, strict=True)


def _parts():
    return ListOf(_strict({"value": Number(above_minimum=True), "unit": Text(choices=BONUS_UNITS)}))


_BONUS = _strict({
    "current": _strict({
        "parts": _parts(),
        "min_spend": Number(),
        "spend_months": Number(minimum=1, integer=True),
        "note_en": _optional_text(),
        **_translations("note_"),
    }),
    "usual": _strict({
        "parts": _parts(),
        "note_en": _optional_text(),
        **_translations("note_"),
    }),
})

CARD_SPEC = Mapping({
    "id": Text(pattern=ID_PATTERN, pattern_hint=ID_HINT),
    "name": Text(),
    "issuer": Text(choices=tuple(ISSUER_DOMAINS)),
    "segment": Text(choices=SEGMENTS),
    "official_url": Url(issuer_only=True),
    "last_verified": Date(),
    "sources": ListOf(Url()),
    "annual_fee": Mapping({"amount": Number(), "first_year_waived": Bool()}),
    "foreign_tx_fee_pct": Number(maximum=100),
    "bonus": _BONUS,
    "elevated": _strict({"start": Date(), "end": Date(required=False)}, required=False),
    "earn": ListOf(Mapping({
        "category_en": Text(),
        **_translations("category_"),
        "rate": Number(above_minimum=True),
        "unit": Text(choices=EARN_UNITS),
    })),
    "benefits": ListOf(Mapping({"en": Text(), **_translations("")}), min_items=0),
})


def today_pt():
    """Today's date in America/Los_Angeles (the offers' home time zone)."""
    return datetime.now(PACIFIC).date()


def _try_date(value):
    try:
        return parse_date(value)
    except ValueError:
        return None


def _card_label(card, index):
    card_id = card.get("id") if isinstance(card, dict) else None
    if isinstance(card_id, str) and card_id.strip():
        return card_id
    return f"카드 {index + 1}번"


def _future_error(label, path, value, today):
    if value and value > today:
        return [error(label, path, (
            f"미래 날짜입니다({value.isoformat()}). "
            f"오늘(미국 서부 기준 {today.isoformat()}) 이전이어야 합니다."))]
    return []


def _check_dates(card, label, today):
    issues = _future_error(label, "last_verified", _try_date(card.get("last_verified")), today)
    elevated = card.get("elevated")
    if isinstance(elevated, dict):
        start, end = _try_date(elevated.get("start")), _try_date(elevated.get("end"))
        issues += _future_error(label, "elevated.start", start, today)
        if start and end and end < start:
            issues.append(error(label, "elevated.end", (
                f"종료일({end.isoformat()})이 시작일({start.isoformat()})보다 앞섭니다.")))
    return issues


def _check_issuer_domain(card, label):
    """official_url must be on the card's own issuer domain (other issuers' domains fail)."""
    issuer, url = card.get("issuer"), card.get("official_url")
    if not isinstance(issuer, str) or issuer not in ISSUER_DOMAINS:
        return []
    if not is_issuer_url(url) or is_issuer_url(url, issuer):
        return []
    return [error(label, "official_url", (
        f"{issuer} 카드의 official_url은 {ISSUER_DOMAINS[issuer]}(또는 하위 도메인) "
        "주소여야 합니다."))]


def _check_card(card, label, today):
    if not isinstance(card, dict):
        return [error(label, "(카드)", "카드는 '- id: ...'로 시작하는 항목 묶음이어야 합니다.")]
    return (CARD_SPEC.check(card, "", label)
            + _check_dates(card, label, today)
            + _check_issuer_domain(card, label)
            + check_text_content(card, label))


def _check_duplicate_ids(cards):
    first_seen = {}
    issues = []
    for index, card in enumerate(cards):
        card_id = card.get("id") if isinstance(card, dict) else None
        if not isinstance(card_id, str) or not card_id.strip():
            continue  # missing/blank ids are already reported as required-field errors
        if card_id in first_seen:
            issues.append(error(card_id, "id", (
                f"id가 중복됩니다(카드 {first_seen[card_id] + 1}번과 같음). "
                "카드마다 다른 id를 쓰세요.")))
        else:
            first_seen[card_id] = index
    return issues


def _check_count(cards):
    if not cards:
        return [error(WHOLE_FILE, "cards", "카드가 한 장도 없습니다.")]
    if len(cards) != EXPECTED_CARD_COUNT:
        return [warning(WHOLE_FILE, "cards", (
            f"카드가 {len(cards)}장입니다(출시 기준 {EXPECTED_CARD_COUNT}장). "
            "배포는 막지 않습니다."))]
    return []


def validate(cards, today=None):
    """Return every Issue in ``cards`` (errors and warnings). Never mutates ``cards``.

    ``today`` defaults to today's Pacific date; tests pass a fixed date.
    """
    if not isinstance(cards, list):
        return [error(WHOLE_FILE, "cards", "cards는 카드 목록이어야 합니다.")]
    today = today or today_pt()
    per_card = [issue for index, card in enumerate(cards)
                for issue in _check_card(card, _card_label(card, index), today)]
    return per_card + _check_duplicate_ids(cards) + _check_count(cards)


def load_cards(path):
    """Read cards.yaml with the strict SafeLoader-based CardLoader; return ``cards``."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CardFileError(f"{path}: 파일을 열 수 없습니다({exc.strerror}).") from exc
    except UnicodeDecodeError as exc:
        raise CardFileError(f"{path}: UTF-8 글자로 저장된 파일이 아닙니다. "
                            "UTF-8로 다시 저장해 주세요.") from exc
    data = parse_yaml(text, path)
    if not isinstance(data, dict) or not isinstance(data.get("cards"), list):
        raise CardFileError(f"{path}: 파일 맨 위에 'cards:' 목록이 있어야 합니다.")
    return data["cards"]
