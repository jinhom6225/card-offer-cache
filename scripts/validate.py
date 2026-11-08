#!/usr/bin/env python3
"""Validate data/cards.yaml. Exit 1 on errors; warnings are printed but do not fail.

    python scripts/validate.py                    # data/cards.yaml, today in US Pacific
    python scripts/validate.py path/to/cards.yaml --today 2026-11-09
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from cardlib.issues import ERROR, error
from cardlib.schema import CardFileError, load_cards, validate

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "cards.yaml"


def _iso_date(text):
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"YYYY-MM-DD 형식이어야 합니다: {text}") from exc


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="cards.yaml 검증기")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH), help="검증할 YAML 파일")
    parser.add_argument("--today", type=_iso_date, default=None,
                        help="기준 날짜(테스트용, 기본값: 미국 서부 오늘)")
    return parser.parse_args(argv)


def _collect(path, today):
    try:
        cards = load_cards(path)
    except CardFileError as exc:
        return 0, [error("전체", "(파일)", str(exc))]
    return len(cards), validate(cards, today=today)


def main(argv=None):
    args = _parse_args(argv)
    count, issues = _collect(args.path, args.today)
    errors = [issue for issue in issues if issue.level == ERROR]
    print(f"검증 파일: {args.path}")
    for issue in issues:
        print(issue)
    verdict = "실패" if errors else "통과"
    print(f"검증 {verdict}: 카드 {count}장, 오류 {len(errors)}개, "
          f"경고 {len(issues) - len(errors)}개")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
