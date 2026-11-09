#!/usr/bin/env python3
"""Build docs/cards_v1.json from data/cards.yaml. Exit 1 (old JSON untouched) on any error.

    python scripts/build_cards.py                         # data/cards.yaml -> docs/cards_v1.json
    python scripts/build_cards.py --output /tmp/cards.json --warnings-file /tmp/warn.txt
    python scripts/build_cards.py --now 2026-11-09T18:00:00Z --data-updated-at 2026-11-09T05:30:00Z
    python scripts/build_cards.py --output /tmp/cards.json --bonus-log /tmp/bonus_log.csv

The file is rewritten only when its bytes would change other than ``generated_at``,
so an unchanged build makes no commit and keeps the Pages ETag. Warnings (D3,
reopened offer, new start without a raise, removed card, first build, bonus log
missing while a previous JSON exists) go to
stdout and ``--warnings-file``; the build continues. Any unexpected exception is
printed as one ``[오류]`` line (the workflow sends those to Telegram) and exits 1.

After the JSON step the bonus observation log (``history/bonus_log.csv``, see
``cardlib.bonus_log``) gets one row per new or changed card, even when the JSON
bytes stayed the same. The log is read and checked before anything is written,
so a broken log stops the build with both files untouched.
"""

import argparse
import contextlib
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cardlib.bonus_log import BonusLogError, diff_rows, format_rows, parse_log, row_for
from cardlib.issues import ERROR, error
from cardlib.offers import ACTIVE, pacific_date
from cardlib.payload import (PreviousJsonError, build_payload, iso_utc, normalize_timestamp,
                             parse_previous, same_content, serialize)
from cardlib.schema import CardFileError, load_cards, validate

ROOT = Path(__file__).resolve().parent.parent
FIRST_BUILD = "이전 JSON 없음(첫 빌드)"
FIRST_BUILD_WARNING = (f"[경고] {FIRST_BUILD}: 변동 기록을 처음부터 시작합니다. 첫 빌드가 "
                       "아니라면 docs/cards_v1.json이 지워진 것이니 git에서 되돌리세요.")
DEFAULT_DATA = ROOT / "data" / "cards.yaml"
DEFAULT_OUTPUT = ROOT / "docs" / "cards_v1.json"
DEFAULT_BONUS_LOG = ROOT / "history" / "bonus_log.csv"


class BuildError(Exception):
    """The build must stop and leave the old JSON alone (message is Korean)."""

    json_saved = False


class BonusLogSaveError(BuildError):
    """Appending to the bonus log failed after the JSON step (which may have saved)."""

    def __init__(self, message, json_saved):
        super().__init__(message)
        self.json_saved = json_saved


class GitTimeError(BuildError):
    """The last commit time of cards.yaml could not be read from git."""


def display_path(path):
    """Repo-relative path for logs (the runner's absolute paths are noise)."""
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _aware_datetime(text):
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"ISO 8601 시각이어야 합니다: {text}") from exc
    if moment.tzinfo is None:
        raise argparse.ArgumentTypeError(f"시간대(Z, +00:00 등)가 있어야 합니다: {text}")
    return moment


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="cards.yaml → docs/cards_v1.json 빌더")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="카드 YAML")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="만들 JSON")
    parser.add_argument("--warnings-file", type=Path, default=None,
                        help="빌드 경고를 한 줄씩 적을 파일(workflow가 텔레그램으로 보냄)")
    parser.add_argument("--now", type=_aware_datetime, default=None,
                        help="빌드 시각(테스트용, 기본값: 지금)")
    parser.add_argument("--data-updated-at", default=None,
                        help="data_updated_at 직접 지정(기본값: cards.yaml의 마지막 git 커밋 시각)")
    parser.add_argument("--bonus-log", type=Path, default=DEFAULT_BONUS_LOG,
                        help="보너스 관측 기록 CSV(바뀐 카드만 한 줄씩 덧붙임, 앱 JSON에는 안 나감)")
    return parser.parse_args(argv)


def git_commit_time(path, runner=subprocess.run):
    """``git log -1 --format=%cI -- <cards.yaml>``: when the data was last committed."""
    path = Path(path)
    args = ["git", "log", "-1", "--format=%cI", "--", path.name]
    try:
        result = runner(args, cwd=path.parent, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or exc
        raise GitTimeError(f"{display_path(path)}의 마지막 커밋 시각을 git에서 읽지 못했습니다"
                           f"({str(detail).strip()}).") from exc
    text = result.stdout.strip()
    if not text:
        raise GitTimeError(f"{display_path(path)}의 커밋 기록이 없습니다. 파일을 커밋했는지, "
                           "Actions checkout에 fetch-depth: 0이 있는지 확인하세요.")
    return text


def _load_valid_cards(path, today):
    """Load and validate (Phase 1 rules). Prints every issue; raises BuildError on errors."""
    print(f"검증 파일: {display_path(path)}")
    try:
        cards = load_cards(path)
        issues = validate(cards, today=today)
    except CardFileError as exc:
        cards, issues = [], [error("전체", "(파일)", str(exc))]
    for issue in issues:
        print(issue)
    errors = [issue for issue in issues if issue.level == ERROR]
    if errors:
        raise BuildError(f"검증 실패: 오류 {len(errors)}개. 앱 데이터(JSON)는 바꾸지 않았습니다.")
    return cards


def _data_updated_at(args):
    text = args.data_updated_at or git_commit_time(args.data)
    try:
        return normalize_timestamp(text)
    except ValueError as exc:
        raise BuildError(f"data_updated_at을 정할 수 없습니다: {exc}") from exc


def _read_previous(path):
    """``(doc, exact text)`` of the previous JSON, or ``(None, None)`` when there is none."""
    if not path.exists():
        return None, None
    try:
        text = path.read_bytes().decode("utf-8")  # bytes as is (no newline translation)
        return parse_previous(text), text
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildError(f"{display_path(path)}: 이전 JSON을 읽을 수 없습니다({exc}).") from exc
    except PreviousJsonError as exc:
        raise BuildError(str(exc)) from exc


def write_atomic(path, text):
    """Write via a temp file in the same folder + os.replace (readers never see half a file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def _serialize(payload):
    try:
        return serialize(payload)
    except ValueError as exc:  # NaN/Infinity: validation should have caught it
        raise BuildError(f"JSON으로 만들 수 없는 값이 있습니다({exc}).") from exc


def _save(path, text):
    try:
        write_atomic(path, text)
    except OSError as exc:
        raise BuildError(f"{display_path(path)} 저장 실패({exc}). 이전 파일은 그대로입니다.") from exc


def _write_warnings(path, warnings):
    if path is None:
        return
    try:
        path.write_text("".join(f"{line}\n" for line in warnings), encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"{display_path(path)} 저장 실패({exc}).") from exc


def _read_bonus_log(path):
    """``(existing text, last row per card)``; a missing file is ``("", {})``."""
    if not path.exists():
        return "", {}
    try:
        text = path.read_bytes().decode("utf-8")  # bytes as is: old rows are kept verbatim
        return text, parse_log(text)
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildError(f"{display_path(path)}: 보너스 관측 기록을 읽을 수 없습니다({exc}). "
                         "파일을 git에서 이전 버전으로 되돌려 주세요.") from exc
    except BonusLogError as exc:
        raise BuildError(f"{display_path(path)}: {exc}") from exc


def _log_restart_warning(path):
    return (f"[경고] {display_path(path)} 없음(또는 빈 파일): 보너스 관측 기록을 처음부터 다시 "
            "시작합니다. 첫 배포가 아니라면 git에서 되돌리세요.")


def _append_bonus_log(path, existing, rows, json_saved):
    """Old bytes + new rows (header first when the file is new or empty), written atomically."""
    if not rows:
        return
    try:
        write_atomic(path, existing + format_rows(rows, header=not existing))
    except OSError as exc:
        raise BonusLogSaveError(f"{display_path(path)} 저장 실패({exc}).", json_saved) from exc


def _summary(payload, warnings, changed, output, first_build, logged):
    offers = [card["offer"] for card in payload["cards"] if card["offer"]]
    active = sum(1 for offer in offers if offer["status"] == ACTIVE)
    ended = sum(1 for offer in offers if offer["ended_auto"])
    result = f"{display_path(output)} 갱신" if changed else "JSON 변경 없음"
    first = f" · {FIRST_BUILD}" if first_build else ""
    return (f"요약: 카드 {len(payload['cards'])}장 · 높음 {active}개 · 자동 종료 {ended}개 · "
            f"경고 {len(warnings)}개 · {result} · 기록 {logged}줄 추가{first}")


def build(args, now):
    """Run one build; returns nothing, raises BuildError on any failure."""
    today = pacific_date(now)
    cards = _load_valid_cards(args.data, today)
    data_updated_at = _data_updated_at(args)
    previous, previous_text = _read_previous(args.output)
    payload, card_warnings = build_payload(cards, previous, today, iso_utc(now), data_updated_at)
    log_text, last_rows = _read_bonus_log(args.bonus_log)
    log_rows = diff_rows(last_rows, [row_for(card, today) for card in payload["cards"]], today)
    log_restart = [_log_restart_warning(args.bonus_log)] if previous is not None and not log_text else []
    warnings = ([FIRST_BUILD_WARNING] if previous is None else []) + log_restart + card_warnings
    for warning in warnings:
        print(warning)
    changed = not same_content(payload, previous, previous_text)
    # Warnings before the JSON: if they cannot be written, nothing has changed yet.
    _write_warnings(args.warnings_file, warnings)
    if changed:
        _save(args.output, _serialize(payload))
    _append_bonus_log(args.bonus_log, log_text, log_rows, json_saved=changed)
    print(_summary(payload, warnings, changed, args.output, previous is None, len(log_rows)))


def main(argv=None):
    args = _parse_args(argv)
    json_saved = False
    try:
        build(args, args.now or datetime.now(timezone.utc))
    except BuildError as exc:
        print(f"[오류] {exc}")
        json_saved = exc.json_saved
    except Exception as exc:  # noqa: BLE001 - any crash must still reach Telegram
        print(f"[오류] 예기치 못한 오류: {type(exc).__name__}: {_one_line(exc)}")
    else:
        return 0
    print(_failure_line(args, json_saved))
    return 1


def _failure_line(args, json_saved):
    output = display_path(args.output)
    if json_saved:
        return (f"빌드 실패: {output}는 이 실행 환경에서만 갱신됐지만 "
                f"{display_path(args.bonus_log)}에 기록하지 못했습니다(커밋되지 않음).")
    return f"빌드 실패: {output}는 바꾸지 않았습니다."


def _one_line(exc):
    """Exception text on one line (the workflow only forwards lines starting with [오류])."""
    return " ".join(str(exc).split()) or "(메시지 없음)"


if __name__ == "__main__":
    sys.exit(main())
