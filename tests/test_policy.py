"""Policy safety rules on the repo side (policy.md "안전 설계 규칙", plan Phase 9).

Checks the committed files, not only the validator: data/*.yaml (raw text,
comments included) and everything under docs/ (the public Pages output).
Runs in CI before the build step, so it needs no network.

- rule 9: credit-decision phrases (EN + KO) are caught and absent.
- community sources: domains and names never in data or the public JSON.
- official_url: https on the card issuer's own domain (fixed allowlist).
- the public JSON never carries ``sources`` (review-only) or unknown keys.
"""

import json
import re
import unittest

# helpers must be imported before cardlib: it puts scripts/ on sys.path.
from helpers import ROOT, TODAY, errors_of, make_card, with_value

from cardlib import schema
from cardlib.payload import PUBLIC_CARD_KEYS, build_payload
from cardlib.phrases import (FORBIDDEN_PATTERNS, find_community_marker, find_forbidden_phrase,
                             find_shortener)
from cardlib.rules import iter_strings
from cardlib.urls import ISSUER_DOMAINS, is_issuer_url

CARDS_YAML = ROOT / "data" / "cards.yaml"
PUBLIC_JSON = ROOT / "docs" / "cards_v1.json"


def data_files():
    return sorted((ROOT / "data").glob("*.yaml"))


# Text files under docs/ (the public Pages output); .nojekyll is an empty marker.
DOCS_TEXT_SUFFIXES = (".json", ".html", ".txt", ".md")


def docs_files():
    return sorted(p for p in (ROOT / "docs").rglob("*")
                  if p.is_file() and p.suffix.lower() in DOCS_TEXT_SUFFIXES)


def committed_text_files(test):
    """data/*.yaml and the docs/ text files; fails if either set is empty."""
    data, docs = data_files(), docs_files()
    test.assertTrue(data, "no data/*.yaml found")
    test.assertTrue(docs, "no text files under docs/")
    return data + docs


def public_doc():
    return json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))


def all_keys(node):
    """Every dict key at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from all_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_keys(value)


class Rule9ForbiddenPhraseTest(unittest.TestCase):
    """Rule 9: no wording that hints at a credit decision."""

    SAMPLES = {
        "pre-approved": "You are pre-approved",
        "pre-qualified": "See if you are pre-qualified",
        "guaranteed approval": "Guaranteed approval for everyone",
        "instant approval": "Instant approval today",
        "no credit check": "No credit check needed",
        "approval odds": "Check your approval odds",
        "best card for you": "The best card for you",
        "사전 승인": "사전 승인 대상입니다",
        "승인 보장": "승인 보장 카드",
        "무조건 승인": "무조건 승인",
        "신용조회 없음": "신용조회 없이 발급",
        "승인 가능성": "승인 가능성 높음",
    }

    def test_every_pattern_label_has_a_sample_that_it_catches(self):
        labels = {label for label, _ in FORBIDDEN_PATTERNS}
        self.assertEqual(labels, set(self.SAMPLES))
        for label, sample in self.SAMPLES.items():
            with self.subTest(label=label):
                self.assertEqual(find_forbidden_phrase(sample), label)

    def test_korean_variants_are_caught(self):
        for sample in ("신용 조회 불필요", "승인 확률", "승인이 보장", "사전승인"):
            with self.subTest(sample=sample):
                self.assertIsNotNone(find_forbidden_phrase(sample))

    def test_the_validator_rejects_a_card_with_such_a_phrase(self):
        card = with_value(make_card(), "bonus.current.note_ko", "승인 보장 카드")
        errors = errors_of(schema.validate([card], today=TODAY))
        self.assertTrue(any("금지 문구" in issue.message for issue in errors), errors)

    def test_no_forbidden_phrase_in_committed_data_or_docs(self):
        for path in committed_text_files(self):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(file=path.name, line=number):
                    self.assertIsNone(find_forbidden_phrase(line), line)


class CommunitySourceTest(unittest.TestCase):
    """Community posts are internal signals only; they never reach data or the app."""

    MARKERS = ("https://www.milemoa.com/bbs/1", "마일모아", "https://www.doctorofcredit.com/x",
               "Doctor of Credit", "닥터오브크레딧", "https://frequentmiler.com/x",
               "프리퀀트 마일러", "https://www.reddit.com/r/churning", "redd.it/x", "레딧",
               "https://thepointsguy.com/x", "The Points Guy", "더 포인츠 가이")

    def test_every_community_domain_and_name_is_caught(self):
        for marker in self.MARKERS:
            with self.subTest(marker=marker):
                self.assertIsNotNone(find_community_marker(marker))

    def test_credit_is_not_mistaken_for_reddit(self):
        self.assertIsNone(find_community_marker("연간 여행 크레딧 $300"))

    def test_no_community_marker_or_shortener_in_committed_data_or_docs(self):
        for path in committed_text_files(self):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                with self.subTest(file=path.name, line=number):
                    self.assertIsNone(find_community_marker(line), line)
                    self.assertIsNone(find_shortener(line), line)

    def test_no_community_marker_in_any_parsed_string(self):
        cards = schema.load_cards(CARDS_YAML)
        for source in (cards, public_doc()):
            for path, text in iter_strings(source):
                with self.subTest(path=path):
                    self.assertIsNone(find_community_marker(text), text)


class OfficialUrlAllowlistTest(unittest.TestCase):
    """official_url is https on the card's own issuer domain (or a subdomain)."""

    def test_the_issuer_allowlist_is_fixed(self):
        self.assertEqual(dict(ISSUER_DOMAINS), {
            "Chase": "chase.com",
            "American Express": "americanexpress.com",
            "Citi": "citi.com",
            "Capital One": "capitalone.com",
            "Discover": "discover.com",
            "Wells Fargo": "wellsfargo.com",
            "Bank of America": "bankofamerica.com",
        })

    def test_lookalike_and_cross_issuer_urls_fail(self):
        for url, issuer in (("http://www.chase.com/x", "Chase"),
                            ("https://chase.com.evil.example/x", "Chase"),
                            ("https://notchase.com/x", "Chase"),
                            ("https://www.americanexpress.com/x", "Chase"),
                            ("https://www.chase.com/x", "Unknown Bank")):
            with self.subTest(url=url, issuer=issuer):
                self.assertFalse(is_issuer_url(url, issuer))

    def test_every_card_in_data_and_docs_uses_its_issuer_domain(self):
        for name, cards in (("cards.yaml", schema.load_cards(CARDS_YAML)),
                            ("cards_v1.json", public_doc()["cards"])):
            self.assertTrue(cards, name)
            for card in cards:
                with self.subTest(file=name, card=card.get("id")):
                    self.assertTrue(is_issuer_url(card["official_url"], card["issuer"]),
                                    card["official_url"])

    def test_official_url_is_the_only_url_in_the_public_json(self):
        for path, text in iter_strings(public_doc()):
            if "://" in text or "www." in text:
                with self.subTest(path=path):
                    self.assertTrue(path.endswith(".official_url"), path)


class PublicJsonShapeTest(unittest.TestCase):
    """The public JSON never carries review-only ``sources`` or unknown card keys."""

    def test_public_keys_exclude_sources(self):
        self.assertNotIn("sources", PUBLIC_CARD_KEYS)

    def test_a_build_drops_sources(self):
        card = with_value(make_card(), "sources", ["https://www.chase.com/review-only"])
        payload, _ = build_payload([card], None, TODAY, "2026-11-09T00:00:00Z",
                                   "2026-11-09T00:00:00Z")
        self.assertNotIn("sources", set(all_keys(payload)))
        self.assertNotIn("review-only", json.dumps(payload))

    def test_committed_json_has_no_sources_key_anywhere(self):
        self.assertNotIn("sources", set(all_keys(public_doc())))

    def test_committed_json_cards_have_only_public_keys(self):
        for card in public_doc()["cards"]:
            with self.subTest(card=card.get("id")):
                self.assertEqual(tuple(card), PUBLIC_CARD_KEYS)

    def test_no_image_or_logo_keys_in_the_public_json(self):
        # A word of a snake_case or camelCase key: image, card_art, cardImage,
        # issuerLogoUrl, icons (not "start" or "partner").
        def is_picture_key(key):
            parts = re.split(r"_|(?<=[a-z0-9])(?=[A-Z])", key)
            return any(re.fullmatch(r"(?:image|img|logo|art|icon|picture)s?", part, re.IGNORECASE)
                       for part in parts)

        for key, expected in (("card_art", True), ("cardImage", True), ("issuerLogoUrl", True),
                              ("Icons", True), ("start", False), ("partner", False),
                              ("artist", False)):
            with self.subTest(key=key):
                self.assertEqual(is_picture_key(key), expected)
        self.assertFalse({k for k in all_keys(public_doc()) if is_picture_key(k)})


if __name__ == "__main__":
    unittest.main()
