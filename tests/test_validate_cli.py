"""scripts/validate.py CLI and the real data/ files."""

import contextlib
import io
import subprocess
import sys
import unittest
from unittest import mock

import yaml

from helpers import FIXTURES, ROOT, errors_of

import validate
from cardlib import schema

DATA = ROOT / "data"


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = validate.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_valid_file_exits_zero_and_prints_warning(self):
        code, out, _ = run_cli(str(FIXTURES / "valid_cards.yaml"), "--today", "2026-11-09")
        self.assertEqual(code, 0)
        self.assertIn("[경고]", out)
        self.assertIn("통과", out)

    def test_invalid_file_exits_one_with_korean_errors(self):
        code, out, _ = run_cli(str(FIXTURES / "yaml_pitfalls.yaml"), "--today", "2026-11-09")
        self.assertEqual(code, 1)
        self.assertIn("[오류] pitfall-card → name", out)
        self.assertIn("실패", out)
        self.assertIn("오류 2개", out)

    def test_load_error_exits_one(self):
        code, out, _ = run_cli(str(FIXTURES / "syntax_error.yaml"))
        self.assertEqual(code, 1)
        self.assertIn("[오류]", out)

    def test_unsafe_yaml_files_exit_one_with_korean_error(self):
        for name in ("recursive_alias.yaml", "duplicate_nested_key.yaml", "octal_number.yaml"):
            with self.subTest(name=name):
                code, out, _ = run_cli(str(FIXTURES / name), "--today", "2026-11-09")
                self.assertEqual(code, 1)
                self.assertIn("[오류] 전체 → (파일)", out)
                self.assertIn("번째 줄", out)

    def test_bad_today_argument_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(str(FIXTURES / "valid_cards.yaml"), "--today", "tomorrow")
        self.assertEqual(ctx.exception.code, 2)

    def test_default_path_points_at_data_cards_yaml(self):
        self.assertEqual(validate.DEFAULT_PATH, DATA / "cards.yaml")

    def test_no_path_argument_uses_default_path(self):
        fixture = FIXTURES / "valid_cards.yaml"
        with mock.patch.object(validate, "DEFAULT_PATH", fixture):
            code, out, _ = run_cli("--today", "2026-11-09")
        self.assertEqual(code, 0)
        self.assertIn(f"검증 파일: {fixture}", out)

    def test_runs_as_a_script(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate.py"),
             str(FIXTURES / "yaml_pitfalls.yaml"), "--today", "2026-11-09"],
            capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("[오류]", result.stdout)


class DataFilesTest(unittest.TestCase):
    def test_real_cards_yaml_has_no_errors_today(self):
        cards = schema.load_cards(DATA / "cards.yaml")
        issues = schema.validate(cards, today=schema.today_pt())
        self.assertEqual(errors_of(issues), [])

    def test_card_aliases_placeholder_structure(self):
        with open(DATA / "card_aliases.yaml", encoding="utf-8") as handle:
            aliases = yaml.safe_load(handle)
        self.assertEqual(set(aliases), {"cards", "issuers", "signal_words", "terminal_prefixes"})

    def test_pages_folder_has_nojekyll(self):
        self.assertTrue((ROOT / "docs" / ".nojekyll").is_file())


if __name__ == "__main__":
    unittest.main()
