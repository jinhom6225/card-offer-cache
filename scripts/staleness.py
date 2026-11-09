#!/usr/bin/env python3
"""Print one Korean report for Telegram (plain text, sent without parse_mode).

    python scripts/staleness.py --daily --warnings-file "$RUNNER_TEMP/build_warnings.txt"

Sections (empty sections are skipped; nothing to report prints nothing):
  1. warnings written by build_cards.py (always)
  2. with --daily: cards whose last_verified is more than 7 days old
  3. with --daily: offers that auto-ended (reminder to clean elevated in cards.yaml)
  4. with --daily: cards with no elevated block whose bonus.current differs from usual

Reads the built docs/cards_v1.json (already validated), not cards.yaml.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from cardlib.fields import parse_date
from cardlib.parts import format_parts, parts_key
from cardlib.schema import today_pt

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CARDS = ROOT / "docs" / "cards_v1.json"
STALE_AFTER_DAYS = 7


def stale_cards(payload, today):
    """Cards last verified more than STALE_AFTER_DAYS days ago, oldest first."""
    stale = []
    for card in payload["cards"]:
        verified = parse_date(card["last_verified"])
        days = (today - verified).days
        if days > STALE_AFTER_DAYS:
            stale.append({"id": card["id"], "name": card["name"],
                          "last_verified": verified.isoformat(), "days": days})
    return sorted(stale, key=lambda item: -item["days"])


def ended_offers(payload):
    """Cards whose offer ended automatically (end date passed, YAML not cleaned yet)."""
    return [{"id": card["id"], "name": card["name"], "end": card["offer"]["end"]}
            for card in payload["cards"]
            if card.get("offer") and card["offer"].get("ended_auto")]


def unmarked_bonus_cards(payload):
    """Cards with no offer (no elevated) whose bonus.current parts differ from usual."""
    result = []
    for card in payload["cards"]:
        current, usual = card["bonus"]["current"]["parts"], card["bonus"]["usual"]["parts"]
        if card.get("offer") is None and parts_key(current) != parts_key(usual):
            result.append({"id": card["id"], "name": card["name"],
                           "current": format_parts(current), "usual": format_parts(usual)})
    return result


def _stale_section(payload, today):
    stale = stale_cards(payload, today)
    if not stale:
        return []
    return [f"마지막 확인이 {STALE_AFTER_DAYS}일 넘은 카드 {len(stale)}장 "
            "(공식 페이지 확인 후 last_verified를 오늘로):"] + [
        f"- {c['id']} ({c['name']}): 마지막 확인 {c['last_verified']}, {c['days']}일 전"
        for c in stale]


def _ended_section(payload):
    ended = ended_offers(payload)
    if not ended:
        return []
    return [f"종료일이 지나 자동 종료된 오퍼 {len(ended)}개 "
            "(cards.yaml에서 elevated를 지우고 bonus.current를 평소 값으로):"] + [
        f"- {c['id']} ({c['name']}): 종료일 {c['end']}" for c in ended]


def _unmarked_section(payload):
    unmarked = unmarked_bonus_cards(payload)
    if not unmarked:
        return []
    return ["평소보다 높은 보너스인데 '높음' 표시가 없습니다 — elevated를 넣거나 current를 "
            f"평소 값으로 되돌리세요({len(unmarked)}장):"] + [
        f"- {c['id']} ({c['name']}): 현재 {c['current']} · 평소 {c['usual']}" for c in unmarked]


def compose_report(payload, today, warnings, daily):
    """The whole message, or "" when there is nothing to report."""
    sections = [list(warnings)] if warnings else []
    if daily:
        daily_sections = (_stale_section(payload, today), _ended_section(payload),
                          _unmarked_section(payload))
        sections += [section for section in daily_sections if section]
    if not sections:
        return ""
    header = f"card-offer-cache 확인 필요 ({today.isoformat()}, 미국 서부 기준)"
    return "\n\n".join([header] + ["\n".join(section) for section in sections])


def read_warnings(path):
    """Non-blank lines of the build's warnings file (missing file = no warnings)."""
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip()]


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="빌드 경고·확인 공백·자동 종료·높음 표시 누락 보고")
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARDS, help="빌드된 JSON")
    parser.add_argument("--warnings-file", type=Path, default=None, help="build_cards.py 경고")
    parser.add_argument("--today", type=date.fromisoformat, default=None,
                        help="기준 날짜(테스트용, 기본값: 미국 서부 오늘)")
    parser.add_argument("--daily", action="store_true",
                        help="7일 확인 공백·자동 종료·높음 표시 누락 목록도 포함(매일·수동 실행)")
    return parser.parse_args(argv)


def _load_payload(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path.name}을 읽을 수 없습니다({exc}).") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("cards"), list):
        raise ValueError(f"{path.name}을 읽을 수 없습니다(cards 목록이 없음).")
    return payload


def main(argv=None):
    args = _parse_args(argv)
    try:
        payload = _load_payload(args.cards)
        warnings = read_warnings(args.warnings_file)
        report = compose_report(payload, args.today or today_pt(), warnings, args.daily)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"[오류] 확인 보고를 만들지 못했습니다: {exc}", file=sys.stderr)
        return 1
    if report:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
