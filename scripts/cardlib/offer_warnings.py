"""Korean build warnings (stdout + ``--warnings-file`` -> Telegram). The build continues.

Per card, at most one of (checked in this order):

- reopened: the previous offer had ended, now the same offer id is active again
  (the app already knows this id, so nobody is notified).
- D3: the offer stayed active under the same id but ``bonus.current.parts`` changed.
- restart: an active offer got a new id (``start`` moved) but the bonus did not go up,
  so users are notified again for nothing.

Plus one warning per card id that was in the previous JSON but is gone now.
"""

from .offers import ACTIVE, ENDED
from .parts import format_parts, is_raise, parts_key


def _parts(card):
    return card["bonus"]["current"]["parts"]


def _offer(card):
    return card.get("offer") if card else None


def _active_id(card):
    offer = _offer(card)
    return offer.get("id") if offer and offer.get("status") == ACTIVE else None


def _is_ended(offer):
    return bool(offer) and (offer.get("status") == ENDED or offer.get("ended_auto") is True)


def reopened_warning(prev_card, new_card):
    """Previous offer ended, now active again with the same id."""
    new_active, prev_offer = _active_id(new_card), _offer(prev_card)
    if not new_active or not _is_ended(prev_offer) or prev_offer.get("id") != new_active:
        return None
    return (f"[경고] {new_card['id']}: 끝났던 오퍼가 같은 start로 다시 열렸습니다. 다시 열린 "
            "것이면 start를 오늘(이미 오늘이면 어제)로 바꾸세요. 종료일 연장이면 무시하세요.")


def d3_warning(prev_card, new_card):
    """Active offer kept its id (and stayed active) but its bonus changed."""
    new_active = _active_id(new_card)
    if not new_active or _active_id(prev_card) != new_active:
        return None
    before, after = _parts(prev_card), _parts(new_card)
    if parts_key(before) == parts_key(after):
        return None
    return (f"[경고] {new_card['id']}: '높음' 오퍼({new_active})의 보너스가 "
            f"{format_parts(before)} → {format_parts(after)}로 바뀌었는데 "
            "elevated.start는 그대로입니다. 보너스가 더 올랐다면 start를 오늘 날짜로"
            "(start가 이미 오늘이면 어제 날짜로) 바꿔야 앱 사용자에게 다시 알림이 갑니다"
            "(오타 정정이면 그대로 두세요).")


def restart_warning(prev_card, new_card):
    """Active offer got a new id (start moved) while the bonus did not go up."""
    new_active, prev_active = _active_id(new_card), _active_id(prev_card)
    if not new_active or not prev_active or new_active == prev_active:
        return None
    if is_raise(_parts(prev_card), _parts(new_card)):
        return None
    return (f"[경고] {new_card['id']}: start가 바뀌어 사용자에게 다시 알림이 갑니다. "
            "보너스가 오르지 않았다면 start를 되돌리세요.")


def card_warnings(prev_card, new_card):
    """The first matching per-card warning as a 0/1-item list."""
    for check in (reopened_warning, d3_warning, restart_warning):
        message = check(prev_card, new_card)
        if message:
            return [message]
    return []


def removed_card_warnings(previous_cards, new_cards):
    """One warning per previous card id that is missing now (removed or renamed)."""
    new_ids = {card["id"] for card in new_cards}
    return [
        f"[경고] {card['id']}: 카드가 cards.yaml에서 빠져 앱에서 사라지고 변동 기록"
        f"({len(card.get('history') or [])}건)도 지워졌습니다. 실수면 cards.yaml을 "
        "되돌리세요(id를 바꾼 경우도 같음)."
        for card in previous_cards if card["id"] not in new_ids]
