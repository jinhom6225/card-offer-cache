"""scripts/build_cards.py end to end, with injected clock and git time (no network)."""

import contextlib
import csv
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

from helpers import FIXTURES, ROOT, make_card, with_value

import build_cards
from cardlib.bonus_log import COLUMNS
from cardlib.schema import load_cards

NOW = "2026-11-09T18:00:00Z"            # 10:00 PST
GIT_TIME = "2026-11-08T21:30:00-08:00"  # = 2026-11-09T05:30:00Z


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.data = self.dir / "cards.yaml"
        self.out = self.dir / "docs" / "cards_v1.json"
        self.warnings = self.dir / "warnings.txt"
        self.log = self.dir / "history" / "bonus_log.csv"

    def write_cards(self, cards):
        self.data.write_text(yaml.safe_dump({"cards": cards}, allow_unicode=True),
                             encoding="utf-8")

    def run_build(self, now=NOW, git_time=GIT_TIME, extra=()):
        argv = ["--data", str(self.data), "--output", str(self.out),
                "--warnings-file", str(self.warnings), "--bonus-log", str(self.log),
                "--now", now, *extra]
        if git_time is not None:
            argv += ["--data-updated-at", git_time]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = build_cards.main(argv)
        return code, out.getvalue()

    def read_json(self):
        return json.loads(self.out.read_text(encoding="utf-8"))

    def stray_files(self):
        return [p.name for p in self.out.parent.iterdir() if p.name != self.out.name]


class SuccessfulBuildTest(BuildTestCase):
    def test_writes_schema_one_json(self):
        self.write_cards([make_card("a"), make_card("b")])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        payload = self.read_json()
        self.assertEqual(list(payload), ["schema", "generated_at", "data_updated_at", "cards"])
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["generated_at"], "2026-11-09T18:00:00Z")
        self.assertEqual(payload["data_updated_at"], "2026-11-09T05:30:00Z")
        self.assertEqual([c["id"] for c in payload["cards"]], ["a", "b"])
        self.assertNotIn("sources", payload["cards"][0])
        self.assertTrue(self.out.read_bytes().endswith(b"}\n"))
        self.assertIn("요약:", output.strip().splitlines()[-1])

    def test_same_input_gives_identical_bytes_in_fresh_builds(self):
        self.write_cards([make_card()])
        self.run_build()
        first = self.out.read_bytes()
        self.out.unlink()
        self.run_build()
        self.assertEqual(self.out.read_bytes(), first)

    def test_rebuild_without_changes_leaves_file_untouched(self):
        self.write_cards([make_card()])
        self.run_build()
        first = self.out.read_bytes()
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0)
        self.assertEqual(self.out.read_bytes(), first)
        self.assertIn("변경 없음", output)
        self.assertEqual(self.stray_files(), [])

    def test_auto_end_rewrites_with_history_and_new_generated_at(self):
        self.write_cards([with_value(make_card(), "elevated.end", "2026-11-09")])
        self.run_build(now="2026-11-10T07:59:59Z")  # 23:59:59 PST on the end date
        self.assertEqual(self.read_json()["cards"][0]["offer"]["status"], "active")
        code, output = self.run_build(now="2026-11-10T08:00:00Z")  # 00:00 PST next day
        self.assertEqual(code, 0, output)
        payload = self.read_json()
        card = payload["cards"][0]
        self.assertEqual((card["offer"]["status"], card["offer"]["ended_auto"]), ("ended", True))
        self.assertEqual([e["type"] for e in card["history"]], ["elevated", "ended"])
        self.assertEqual(card["history"][-1]["date"], "2026-11-10")
        self.assertEqual(payload["generated_at"], "2026-11-10T08:00:00Z")

    def test_d3_warning_is_written_and_build_continues(self):
        self.write_cards([make_card("chase-sp")])
        self.run_build()
        self.write_cards([with_value(make_card("chase-sp"), "bonus.current.parts[0].value",
                                     90000)])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        lines = self.warnings.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("chase-sp", lines[0])
        self.assertIn("[경고]", output)
        self.assertEqual(self.read_json()["cards"][0]["bonus"]["current"]["parts"][0]["value"],
                         90000)

    def test_first_build_says_there_was_no_previous_json(self):
        self.write_cards([make_card()])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        summary = output.strip().splitlines()[-1]
        self.assertIn("이전 JSON 없음(첫 빌드)", summary)
        self.assertIn("경고 1개", summary)
        lines = self.warnings.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("[경고] 이전 JSON 없음(첫 빌드)"))
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertNotIn("첫 빌드", output)
        self.assertEqual(self.warnings.read_text(encoding="utf-8"), "")

    def test_removed_card_warning_is_written(self):
        self.write_cards([make_card("a"), make_card("b")])
        self.run_build()
        self.write_cards([make_card("a")])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        lines = self.warnings.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("[경고] b: 카드가 cards.yaml에서 빠져", lines[0])
        self.assertIn("변동 기록(1건)", lines[0])

    def test_representation_change_in_previous_json_rewrites_it(self):
        self.write_cards([make_card()])
        self.run_build()
        canonical = self.out.read_bytes()
        self.out.write_bytes(canonical.replace(b'"value": 75000', b'"value": 75000.0'))
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.out.read_bytes(), canonical)
        self.assertIn("docs/cards_v1.json 갱신", output.replace(str(self.out), "docs/cards_v1.json"))

    def test_real_cards_yaml_builds_today(self):
        # Live data + real clock (like the Phase 1 data test): no pinned date or card count.
        self.data = ROOT / "data" / "cards.yaml"
        now = datetime.now(timezone.utc).isoformat()
        code, output = self.run_build(now=now)
        self.assertEqual(code, 0, output)
        self.assertEqual(len(self.read_json()["cards"]), len(load_cards(self.data)))

    def test_warnings_file_is_optional(self):
        self.write_cards([make_card()])
        argv = ["--data", str(self.data), "--output", str(self.out), "--now", NOW,
                "--data-updated-at", GIT_TIME, "--bonus-log", str(self.log)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_cards.main(argv), 0)
        self.assertFalse(self.warnings.exists())

    def test_uses_git_commit_time_when_not_overridden(self):
        self.write_cards([make_card()])
        with mock.patch.object(build_cards, "git_commit_time", return_value=GIT_TIME) as git:
            code, output = self.run_build(git_time=None)
        self.assertEqual(code, 0, output)
        git.assert_called_once_with(self.data)
        self.assertEqual(self.read_json()["data_updated_at"], "2026-11-09T05:30:00Z")

    def test_fixture_with_yaml_dates_builds(self):
        shutil.copy(FIXTURES / "valid_cards.yaml", self.data)
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        card = self.read_json()["cards"][0]
        self.assertEqual(card["offer"], {"id": "fixture-travel@2026-10-01", "status": "active",
                                         "start": "2026-10-01", "end": None,
                                         "ended_auto": False})
        self.assertNotIn("note_ko", card["bonus"]["current"])


class FailedBuildTest(BuildTestCase):
    ORIGINAL = b'{"previous": "bytes stay"}\n'

    def write_original(self):
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.write_bytes(self.ORIGINAL)

    def assert_untouched(self):
        self.assertEqual(self.out.read_bytes(), self.ORIGINAL)
        self.assertEqual(self.stray_files(), [])

    def test_validation_failure_keeps_existing_json_bytes(self):
        self.write_original()
        self.write_cards([with_value(make_card(), "bonus.current.min_spend", "4,000")])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assert_untouched()
        self.assertIn("[오류] sample-travel-card → bonus.current.min_spend", output)
        self.assertIn("검증 실패", output)

    def test_yaml_load_failure_keeps_existing_json_bytes(self):
        self.write_original()
        shutil.copy(FIXTURES / "syntax_error.yaml", self.data)
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assert_untouched()
        self.assertIn("[오류]", output)

    def test_unreadable_previous_json_stops_the_build(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_bytes(b"{broken")
        self.write_cards([make_card()])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), b"{broken")
        self.assertIn("docs/cards_v1.json", output)

    def test_non_utf8_previous_json_stops_the_build(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_bytes(b"\xff\xfe{")
        self.write_cards([make_card()])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), b"\xff\xfe{")
        self.assertIn("이전 JSON을 읽을 수 없습니다", output)

    def test_previous_json_with_string_offer_stops_with_shape_error(self):
        self.out.parent.mkdir(parents=True)
        bad = json.dumps({"schema": 1, "cards": [{"id": "a", "offer": "oops"}]}).encode()
        self.out.write_bytes(bad)
        self.write_cards([make_card("a")])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), bad)
        self.assertIn("[오류] docs/cards_v1.json: 이전 JSON의 모양이 맞지 않습니다", output)

    def test_unexpected_exception_is_reported_with_its_type(self):
        self.write_cards([make_card()])
        self.run_build()
        before = self.out.read_bytes()
        self.write_cards([with_value(make_card(), "name", "Renamed Card")])
        with mock.patch.object(build_cards, "build_payload", side_effect=TypeError("boom")):
            code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), before)
        self.assertIn("[오류] 예기치 못한 오류: TypeError: boom\n", output)
        self.assertIn("빌드 실패", output)

    def test_git_time_failure_stops_the_build(self):
        self.write_original()
        self.write_cards([make_card()])
        with mock.patch.object(build_cards, "git_commit_time",
                               side_effect=build_cards.GitTimeError("git 오류")):
            code, output = self.run_build(git_time=None)
        self.assertEqual(code, 1)
        self.assert_untouched()
        self.assertIn("git 오류", output)

    def test_bad_data_updated_at_override_stops_the_build(self):
        self.write_cards([make_card()])
        code, output = self.run_build(git_time="yesterday")
        self.assertEqual(code, 1)
        self.assertFalse(self.out.exists())
        self.assertIn("data_updated_at", output)

    def test_write_failure_keeps_old_file_and_removes_temp(self):
        self.write_cards([make_card()])
        self.run_build()
        before = self.out.read_bytes()
        self.write_cards([with_value(make_card(), "name", "Renamed Card")])
        with mock.patch.object(build_cards.os, "replace", side_effect=OSError("disk full")):
            code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), before)
        self.assertEqual(self.stray_files(), [])
        self.assertIn("disk full", output)

    def test_unserializable_value_stops_the_build(self):
        self.write_cards([make_card()])
        with mock.patch.object(build_cards, "serialize", side_effect=ValueError("NaN")):
            code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertFalse(self.out.exists())
        self.assertIn("[오류] JSON으로 만들 수 없는 값이 있습니다(NaN).", output)

    def test_warnings_file_write_failure_is_an_error(self):
        self.write_cards([make_card()])
        self.warnings.mkdir()
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertIn("[오류] ", output)
        self.assertIn("저장 실패", output)
        self.assertFalse(self.out.exists())  # warnings are written before the JSON
        self.assertFalse(self.log.exists())
        self.assertIn("바꾸지 않았습니다", output)

    def test_warnings_file_failure_on_a_change_keeps_the_old_json(self):
        self.write_cards([make_card()])
        self.run_build()
        before, log_before = self.out.read_bytes(), self.log.read_bytes()
        self.write_cards([with_value(make_card(), "name", "Renamed Card")])
        self.warnings.unlink()
        self.warnings.mkdir()
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 1)
        self.assertEqual(self.out.read_bytes(), before)
        self.assertEqual(self.log.read_bytes(), log_before)
        self.assertIn("바꾸지 않았습니다", output)
        self.assertNotIn("갱신됐지만", output)

    def test_bad_now_is_a_usage_error(self):
        self.write_cards([make_card()])
        for bad in ("tomorrow", "2026-11-09T18:00:00"):
            with self.subTest(now=bad), self.assertRaises(SystemExit) as ctx:
                self.run_build(now=bad)
            self.assertEqual(ctx.exception.code, 2)


class BonusLogBuildTest(BuildTestCase):
    """history/bonus_log.csv: first snapshot, then only cards whose values changed."""

    def log_rows(self):
        with self.log.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def summary(self, output):
        return output.strip().splitlines()[-1]

    def test_first_build_writes_header_and_one_added_row_per_card(self):
        self.write_cards([make_card("a"), make_card("b")])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        text = self.log.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(",".join(COLUMNS) + "\n"))
        self.assertTrue(text.endswith("\n"))
        rows = self.log_rows()
        self.assertEqual([(r["card_id"], r["note"], r["date"]) for r in rows],
                         [("a", "added", "2026-11-09"), ("b", "added", "2026-11-09")])
        self.assertEqual((rows[0]["current"], rows[0]["usual"], rows[0]["elevated"],
                          rows[0]["offer_id"], rows[0]["offer_end"]),
                         ("75000 points", "60000 points", "yes", "a@2026-10-01", "2026-12-31"))
        self.assertIn("기록 2줄 추가", self.summary(output))

    def test_unchanged_rerun_appends_nothing_and_keeps_bytes(self):
        self.write_cards([make_card("a"), make_card("b")])
        self.run_build()
        before = self.log.read_bytes()
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.log.read_bytes(), before)
        self.assertIn("기록 0줄 추가", self.summary(output))

    def test_changes_append_one_row_for_that_card_only(self):
        changes = {
            "current": ("bonus.current.parts[0].value", 90000),
            "usual": ("bonus.usual.parts[0].value", 50000),
            "min_spend": ("bonus.current.min_spend", 5000),
            "last_verified": ("last_verified", "2026-11-08"),
            "offer_end": ("elevated.end", "2027-01-31"),
            "elevated": ("elevated", None),
        }
        for field, (path, value) in changes.items():
            with self.subTest(field=field):
                self.log.unlink(missing_ok=True)
                self.out.unlink(missing_ok=True)
                self.write_cards([make_card("a"), make_card("b")])
                self.run_build()
                before = self.log.read_bytes()
                self.write_cards([with_value(make_card("a"), path, value), make_card("b")])
                code, output = self.run_build(now="2026-11-10T18:00:00Z")
                self.assertEqual(code, 0, output)
                self.assertTrue(self.log.read_bytes().startswith(before))  # append-only
                rows = self.log_rows()
                self.assertEqual(len(rows), 3)
                self.assertEqual((rows[-1]["card_id"], rows[-1]["note"], rows[-1]["date"]),
                                 ("a", "", "2026-11-10"))
                self.assertNotEqual(rows[-1][field], rows[0][field])
                self.assertIn("기록 1줄 추가", self.summary(output))

    def test_part_order_change_only_appends_nothing(self):
        two = [{"value": 130000, "unit": "points"}, {"value": 1, "unit": "free_night"}]
        card = with_value(with_value(make_card("a"), "bonus.current.parts", two),
                          "bonus.usual.parts", two)
        self.write_cards([card])
        self.run_build()
        self.assertEqual(self.log_rows()[0]["current"], "1 free_night + 130000 points")
        swapped = list(reversed(two))
        self.write_cards([with_value(with_value(card, "bonus.current.parts", swapped),
                                     "bonus.usual.parts", swapped)])
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        self.assertEqual(len(self.log_rows()), 1)

    def test_removed_and_new_cards(self):
        self.write_cards([make_card("a"), make_card("b")])
        self.run_build()
        self.write_cards([make_card("a"), make_card("c")])
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        rows = self.log_rows()[2:]
        self.assertEqual([(r["card_id"], r["note"]) for r in rows],
                         [("c", "added"), ("b", "removed")])
        self.assertEqual((rows[1]["issuer"], rows[1]["current"]), ("Chase", ""))
        code, _ = self.run_build(now="2026-11-11T18:00:00Z")
        self.assertEqual(len(self.log_rows()), 4)  # "removed" is written once

    def test_date_is_the_pacific_build_date(self):
        self.write_cards([with_value(make_card(), "elevated.end", "2026-11-09")])
        self.run_build(now="2026-11-10T07:59:59Z")  # 23:59:59 PST on 2026-11-09
        self.run_build(now="2026-11-10T08:00:00Z")  # 00:00 PST 2026-11-10: offer auto-ends
        rows = self.log_rows()
        self.assertEqual([(r["date"], r["elevated"]) for r in rows],
                         [("2026-11-09", "yes"), ("2026-11-10", "no")])

    def test_header_is_written_once(self):
        self.write_cards([make_card("a")])
        self.run_build()
        self.write_cards([with_value(make_card("a"), "bonus.current.min_spend", 5000)])
        self.run_build(now="2026-11-10T18:00:00Z")
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(text.count("date,card_id"), 1)

    def test_log_is_started_even_when_the_json_is_unchanged(self):
        self.write_cards([make_card("a")])
        self.run_build()
        json_before = self.out.read_bytes()
        self.log.unlink()
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.out.read_bytes(), json_before)
        self.assertEqual([r["note"] for r in self.log_rows()], ["added"])
        self.assertIn("JSON 변경 없음", output)

    def test_empty_log_file_gets_a_header(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_bytes(b"")
        self.write_cards([make_card("a")])
        code, output = self.run_build()
        self.assertEqual(code, 0, output)
        self.assertEqual(len(self.log_rows()), 1)

    def test_validation_failure_leaves_the_log_alone(self):
        self.write_cards([make_card("a")])
        self.run_build()
        before = self.log.read_bytes()
        self.write_cards([with_value(make_card("a"), "bonus.current.min_spend", "4,000")])
        code, _ = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 1)
        self.assertEqual(self.log.read_bytes(), before)

    def test_malformed_log_stops_the_build_and_nothing_is_written(self):
        self.write_cards([make_card("a")])
        self.run_build()
        json_before = self.out.read_bytes()
        broken = b"date,card\n2026-11-09,a\n"
        self.log.write_bytes(broken)
        self.write_cards([with_value(make_card("a"), "name", "Renamed Card")])
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 1)
        self.assertEqual(self.log.read_bytes(), broken)
        self.assertEqual(self.out.read_bytes(), json_before)
        self.assertIn("[오류] ", output)
        self.assertIn("보너스 관측 기록", output)
        self.assertIn("바꾸지 않았습니다", output)

    def test_non_utf8_log_stops_the_build(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_bytes(b"\xff\xfe")
        self.write_cards([make_card("a")])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertEqual(self.log.read_bytes(), b"\xff\xfe")
        self.assertFalse(self.out.exists())
        self.assertIn("[오류] ", output)

    def test_log_save_failure_after_json_saved_says_so(self):
        blocker = self.dir / "blocker"
        blocker.write_text("not a folder", encoding="utf-8")
        self.log = blocker / "bonus_log.csv"
        self.write_cards([make_card("a")])
        code, output = self.run_build()
        self.assertEqual(code, 1)
        self.assertTrue(self.out.exists())
        self.assertIn("[오류] ", output)
        self.assertIn("저장 실패", output)
        self.assertNotIn("바꾸지 않았습니다", output)
        self.assertIn("이 실행 환경에서만 갱신됐지만", output)

    def test_missing_log_with_previous_json_is_warned(self):
        self.write_cards([make_card("a")])
        self.run_build()
        self.log.unlink()
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        lines = self.warnings.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("[경고] "), lines[0])
        self.assertIn("bonus_log.csv", lines[0])
        self.assertIn("보너스 관측 기록을 처음부터 다시 시작합니다", lines[0])
        self.assertIn("git에서 되돌리세요", lines[0])
        self.assertIn("경고 1개", self.summary(output))
        self.assertEqual([r["note"] for r in self.log_rows()], ["added"])

    def test_empty_log_with_previous_json_is_warned_too(self):
        self.write_cards([make_card("a")])
        self.run_build()
        self.log.write_bytes(b"")
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(code, 0, output)
        self.assertIn("처음부터 다시 시작합니다", self.warnings.read_text(encoding="utf-8"))

    def test_first_build_without_json_does_not_warn_about_the_log(self):
        self.write_cards([make_card("a")])
        self.run_build()
        text = self.warnings.read_text(encoding="utf-8")
        self.assertNotIn("보너스 관측 기록", text)
        code, output = self.run_build(now="2026-11-10T18:00:00Z")
        self.assertEqual(self.warnings.read_text(encoding="utf-8"), "")


class GitCommitTimeTest(unittest.TestCase):
    def fake_runner(self, stdout="", error=None):
        calls = []

        def runner(args, **kwargs):
            calls.append((args, kwargs))
            if error:
                raise error
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")
        return runner, calls

    def test_reads_last_commit_time_of_the_file(self):
        runner, calls = self.fake_runner(stdout=GIT_TIME + "\n")
        path = Path("/repo/data/cards.yaml")
        self.assertEqual(build_cards.git_commit_time(path, runner=runner), GIT_TIME)
        args, kwargs = calls[0]
        self.assertEqual(args, ["git", "log", "-1", "--format=%cI", "--", "cards.yaml"])
        self.assertEqual(kwargs["cwd"], path.parent)

    def test_uncommitted_file_is_an_error(self):
        runner, _ = self.fake_runner(stdout="\n")
        with self.assertRaises(build_cards.GitTimeError) as ctx:
            build_cards.git_commit_time(Path("/repo/data/cards.yaml"), runner=runner)
        self.assertIn("fetch-depth", str(ctx.exception))

    def test_git_errors_become_git_time_error(self):
        for error in (subprocess.CalledProcessError(128, ["git"], stderr="not a repo"),
                      FileNotFoundError("git")):
            runner, _ = self.fake_runner(error=error)
            with self.subTest(error=error), self.assertRaises(build_cards.GitTimeError):
                build_cards.git_commit_time(Path("/repo/data/cards.yaml"), runner=runner)


class OneLineTest(unittest.TestCase):
    def test_multiline_and_empty_messages(self):
        self.assertEqual(build_cards._one_line(ValueError("a\n  b")), "a b")
        self.assertEqual(build_cards._one_line(KeyError()), "(메시지 없음)")


class DisplayPathTest(unittest.TestCase):
    def test_paths_inside_the_repo_are_relative(self):
        self.assertEqual(build_cards.display_path(ROOT / "docs" / "cards_v1.json"),
                         "docs/cards_v1.json")

    def test_paths_outside_the_repo_are_kept(self):
        outside = Path(tempfile.gettempdir()) / "x.json"
        self.assertEqual(build_cards.display_path(outside), str(outside))

    def test_defaults_point_into_the_repo(self):
        self.assertEqual(build_cards.DEFAULT_DATA, ROOT / "data" / "cards.yaml")
        self.assertEqual(build_cards.DEFAULT_OUTPUT, ROOT / "docs" / "cards_v1.json")
        self.assertEqual(build_cards.DEFAULT_BONUS_LOG, ROOT / "history" / "bonus_log.csv")


if __name__ == "__main__":
    unittest.main()
