"""Community-source, URL-shortener and forbidden-phrase rules (URL rules: test_urls.py)."""

import unittest

from helpers import TODAY, errors_of, make_card, paths_of, with_value

from cardlib import rules, schema

TEXT_PATHS = ("name", "bonus.current.note_en", "benefits[0].ko", "earn[0].category_en")


def check(card):
    return errors_of(schema.validate([card], today=TODAY))


def assert_flagged(test, path, text, word):
    with test.subTest(path=path, text=text):
        issues = check(with_value(make_card(), path, text))
        test.assertIn(path, paths_of(issues))
        test.assertTrue(any(word in i.message for i in issues), issues)


class CommunityDomainTest(unittest.TestCase):
    MARKERS = ["https://www.milemoa.com/bbs/1", "https://www.doctorofcredit.com/x",
               "https://frequentmiler.com/x", "https://www.reddit.com/r/churning",
               "https://thepointsguy.com/x", "see MileMoa thread", "마일모아 글 참고",
               "r/churning", "from r/CreditCards thread", "(r/amex)", "레딧에서 봄",
               "닥터오브크레딧", "닥터 오브 크레딧 글", "더 포인츠 가이", "프리퀀트 마일러",
               "Doctor of Credit", "The Points Guy", "https://www.%72eddit.com/x",
               "https://www.reddit%2Ecom/x", "https://www.%252572eddit.com/x",
               "ｒｅｄｄｉｔ", "red\u200bdit"]

    def test_community_marker_in_any_field_fails(self):
        paths = ["sources[0]", "name", "bonus.current.note_en", "bonus.usual.note_ko",
                 "earn[0].category_ko", "benefits[0].en"]
        for path in paths:
            for marker in self.MARKERS:
                assert_flagged(self, path, marker, "커뮤니티")

    def test_community_marker_in_unknown_key_value_also_fails(self):
        card = with_value(make_card(), "memo", ["https://www.reddit.com/r/churning"])
        self.assertIn("memo[0]", paths_of(check(card)))

    def test_community_marker_in_key_name_fails(self):
        card = with_value(make_card(), "reddit_url", "see notes")
        self.assertIn("reddit_url", paths_of(check(card)))

    def test_r_slash_inside_an_issuer_url_path_passes(self):
        card = with_value(make_card(), "official_url", "https://creditcards.chase.com/r/abc")
        self.assertEqual(check(card), [])


class ShortenerTest(unittest.TestCase):
    SHORT = ["https://bit.ly/abc", "https://tinyurl.com/x", "https://t.co/x",
             "https://goo.gl/x", "https://ow.ly/x", "https://is.gd/x", "https://buff.ly/x",
             "https://rebrand.ly/x", "https://lnkd.in/x", "https://BIT.LY/x", "see bit.ly/x"]

    def test_shortener_in_any_url_or_text_field_fails(self):
        for path in ("official_url", "sources[0]", "bonus.current.note_en"):
            for url in self.SHORT:
                assert_flagged(self, path, url, "단축")

    def test_similar_real_domains_pass(self):
        for url in ("https://www.att.com/x", "https://t.com/x", "https://credit.co/x",
                    "https://thisgd.example.com/x", "https://bit.lyrics.com/x"):
            with self.subTest(url=url):
                self.assertEqual(check(with_value(make_card(), "sources[0]", url)), [])


class IterStringsTest(unittest.TestCase):
    def test_walks_keys_tuples_and_sets(self):
        node = {"a": ("x", {"k": "v"}), "b": {"s1", "s2"}, 3: "n"}
        found = list(rules.iter_strings(node))
        self.assertEqual(found, [("a", "a"), ("a[0]", "x"), ("a[1].k", "k"),
                                 ("a[1].k", "v"), ("b", "b"), ("b[0]", "s1"),
                                 ("b[1]", "s2"), ("3", "n")])


class ForbiddenPhraseTest(unittest.TestCase):
    PHRASES = ["You are pre-approved!", "Preapproved offer", "pre approved", "PRE–APPROVED",
               "Guaranteed approval", "Approval guaranteed", "approval is guaranteed",
               "guaranteed to be approved", "Guaranteed acceptance",
               "Check your APPROVAL ODDS", "No credit check needed",
               "Apply without a credit check", "without credit check",
               "Get pre-qualified", "prequalified offers", "Instant approval",
               "The best card for you", "best  card  for you", "best cards for you",
               "the best card for your needs",
               "ＰＲＥ－ＡＰＰＲＯＶＥＤ", "pre\u200bapproved",
               "사전 승인 대상", "사전승인", "승인 보장", "승인을 보장합니다", "무조건 승인",
               "신용조회 없음", "신용 조회 없음", "신용조회 없이 발급", "신용조회 불필요",
               "승인 가능성 확인", "승인될 가능성이 높음", "승인가능성"]

    def test_forbidden_phrase_in_any_text_fails(self):
        for path in TEXT_PATHS:
            for phrase in self.PHRASES:
                assert_flagged(self, path, phrase, "금지 문구")

    def test_ordinary_text_passes(self):
        texts = ["Earn 75,000 bonus points", "Approval is up to the issuer",
                 "No foreign transaction fees", "승인 여부는 카드사가 결정합니다",
                 "Best for dining", "Guaranteed 4PM late checkout", "guaranteed",
                 "Room upgrade guaranteed at check-in", "the best card for young adults",
                 "Credit check required", "Approved by the issuer",
                 "연 300달러 여행 크레딧", "Sapphire Reserve r2 lounge"]
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(check(with_value(make_card(), "bonus.current.note_en", text)), [])

    def test_find_forbidden_phrase_helper(self):
        self.assertEqual(rules.find_forbidden_phrase("Pre-Approved"), "pre-approved")
        self.assertEqual(rules.find_forbidden_phrase("approval guaranteed"),
                         "guaranteed approval")
        self.assertIsNone(rules.find_forbidden_phrase("approved by issuer"))


if __name__ == "__main__":
    unittest.main()


class ForbiddenPhrasePerformanceTest(unittest.TestCase):
    """Regression for quadratic backtracking on long whitespace runs (ReDoS)."""

    def test_long_whitespace_after_seunggin_is_fast(self):
        import time

        from cardlib import phrases

        text = "승인" + " " * 64000 + "x"
        started = time.perf_counter()
        self.assertIsNone(phrases.find_forbidden_phrase(text))
        self.assertLess(time.perf_counter() - started, 1.0)

    def test_korean_approval_phrases_still_match(self):
        from cardlib import phrases

        for text in ("승인 가능성", "승인될 가능성", "승인이 될 확률", "승인을 보장",
                     "승인보장", "승인 받을 확률"):
            with self.subTest(text=text):
                self.assertIsNotNone(phrases.find_forbidden_phrase(text))
