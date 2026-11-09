"""Bonus observation log (``history/bonus_log.csv``): pure row building, diffing, CSV text.

The app JSON keeps only the last 20 ``history`` events per card and only when
``bonus.current.parts`` moves, which is too little to judge later what a card's
"usual" bonus is. This log keeps every observed change, without limit, and
never goes into the app JSON.

- First build: one row per card (``note`` = ``added``).
- Later builds: one row only for a card whose tracked columns (everything but
  ``date`` and ``note``) changed; a new card (or one that came back) is
  ``added``; a card that disappeared gets one ``removed`` row.
- Bonus parts are written order-insensitively (sorted like ``parts.parts_key``)
  so reordering parts in cards.yaml is not a change.

Rows are built from the *public* cards (``payload["cards"]``): numbers are
already normalized and ``offer`` already says whether the offer is active.
"""

import csv
import io
import re
from datetime import date

from .offers import ACTIVE
from .parts import json_number

COLUMNS = ("date", "card_id", "issuer", "current", "min_spend", "spend_months", "usual",
           "elevated", "offer_id", "offer_end", "last_verified", "note")
TRACKED = tuple(column for column in COLUMNS if column not in ("date", "note"))
ADDED = "added"
REMOVED = "removed"
NOTES = ("", ADDED, REMOVED)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class BonusLogError(Exception):
    """The existing log cannot be read safely (message is Korean)."""


def _number(value):
    value = json_number(value)
    return str(value) if isinstance(value, int) else repr(value)


def compact_parts(parts):
    """``1 free_night + 130000 points``: sorted by (unit, value), no thousands separators."""
    ordered = sorted(parts, key=lambda part: (part["unit"], part["value"]))
    return " + ".join(f"{_number(part['value'])} {part['unit']}" for part in ordered)


def row_for(card, day):
    """Log row (all text) for one public card on the Pacific build date ``day``."""
    current, usual = card["bonus"]["current"], card["bonus"]["usual"]
    offer = card.get("offer") or {}
    return {
        "date": day.isoformat() if isinstance(day, date) else str(day),
        "card_id": card["id"],
        "issuer": card["issuer"],
        "current": compact_parts(current["parts"]),
        "min_spend": _number(current["min_spend"]),
        "spend_months": _number(current["spend_months"]),
        "usual": compact_parts(usual["parts"]),
        "elevated": "yes" if offer.get("status") == ACTIVE else "no",
        "offer_id": offer.get("id") or "",
        "offer_end": offer.get("end") or "",
        "last_verified": card["last_verified"],
        "note": "",
    }


def _tracked(row):
    return tuple(row.get(column, "") for column in TRACKED)


def _removed_row(last, day):
    empty = {column: "" for column in COLUMNS}
    return {**empty, "date": day.isoformat() if isinstance(day, date) else str(day),
            "card_id": last["card_id"], "issuer": last.get("issuer", ""), "note": REMOVED}


def diff_rows(last_rows, new_rows, day):
    """Rows to append: new/returning cards (``added``), changed cards, then removed cards.

    ``last_rows`` maps card id -> its last logged row (``parse_log``); ``new_rows``
    are this build's ``row_for`` rows; ``day`` dates the ``removed`` rows.
    """
    appended = []
    for row in new_rows:
        last = last_rows.get(row["card_id"])
        if last is None or last.get("note") == REMOVED:
            appended.append({**row, "note": ADDED})
        elif _tracked(last) != _tracked(row):
            appended.append({**row, "note": ""})
    present = {row["card_id"] for row in new_rows}
    removed = [_removed_row(last, day) for card_id, last in last_rows.items()
               if card_id not in present and last.get("note") != REMOVED]
    return appended + removed


def format_rows(rows, header):
    """CSV text (RFC 4180 quoting, LF line ends, final newline); ``header`` adds the column row."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    if header:
        writer.writerow(COLUMNS)
    writer.writerows([row.get(column, "") for column in COLUMNS] for row in rows)
    return buffer.getvalue()


def _row_problem(fields):
    if len(fields) != len(COLUMNS):
        return f"칸이 {len(COLUMNS)}개가 아니라 {len(fields)}개입니다"
    row = dict(zip(COLUMNS, fields))
    if not _DATE.fullmatch(row["date"]):
        return f"date가 YYYY-MM-DD가 아닙니다({row['date']!r})"
    if not row["card_id"]:
        return "card_id가 비었습니다"
    if row["note"] not in NOTES:
        return f"note가 {', '.join(repr(n) for n in NOTES)} 중 하나가 아닙니다({row['note']!r})"
    return None


def _malformed(detail):
    return BonusLogError(f"보너스 관측 기록 파일의 모양이 맞지 않습니다({detail}). 기록을 "
                         "지키기 위해 빌드를 멈춥니다. 파일을 git에서 이전 버전으로 되돌려 주세요.")


def parse_log(text):
    """Last row per card id (in first-seen order). Empty text = no rows. Bad files raise."""
    if not text:
        return {}
    if not text.endswith("\n"):
        raise _malformed("마지막 줄이 줄바꿈으로 끝나지 않습니다")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    last = {}
    try:
        header = next(reader)
        if tuple(header) != COLUMNS:
            raise _malformed("첫 줄(머리글)이 다릅니다")
        for fields in reader:
            problem = _row_problem(fields)
            if problem:
                raise _malformed(f"{reader.line_num}번째 줄: {problem}")
            row = dict(zip(COLUMNS, fields))
            last = {**last, row["card_id"]: row}
    except csv.Error as exc:
        raise _malformed(f"{reader.line_num}번째 줄: {exc}") from exc
    return last


__all__ = ["COLUMNS", "TRACKED", "ADDED", "REMOVED", "BonusLogError", "compact_parts",
           "row_for", "diff_rows", "format_rows", "parse_log"]
