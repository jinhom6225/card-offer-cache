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


JA_ES_PATHS = ("bonus.current.note_ja", "bonus.usual.note_es", "earn[0].category_ja",
               "earn[0].category_es", "benefits[0].ja", "benefits[0].es")


class JapaneseSpanishForbiddenPhraseTest(unittest.TestCase):
    """Plan A7: credit-decision phrases in Japanese and Spanish fail like EN/KO ones."""

    LABELED = {
        "事前承認": ("事前承認済みです", "事前 承認", "事前・承認"),
        "承認保証": ("承認保証", "承認を保証します", "承認が保証されます", "保証された承認",
                 "必ず承認されます"),
        "必ず審査に通る": ("必ず審査に通る", "必ず審査に通ります", "審査に必ず通る"),
        "与信審査不要": ("与信審査不要", "与信審査なし", "与信チェックなしで発行", "信用調査不要"),
        "審査なし": ("審査なし", "審査無しで発行", "審査不要のカード"),
        "承認の可能性": ("承認の可能性", "承認される可能性を確認", "承認率", "承認の確率"),
        "preaprobado": ("Estás preaprobado", "Oferta pre-aprobada", "PRE APROBADOS",
                        "preaprobación"),
        "precalificado": ("Precalificado hoy", "pre-calificada", "precalificación"),
        "aprobación garantizada": ("Aprobación garantizada", "aprobacion garantizada",
                                   "La aprobación está garantizada", "garantizamos la aprobación",
                                   "garantía de aprobación"),
        "sin verificación de crédito": ("Sin verificación de crédito", "sin verificacion de credito",
                                        "sin consulta de crédito", "sin chequeo de crédito"),
        "sin revisión de crédito": ("Sin revisión de crédito", "sin revision del credito"),
        "probabilidad de aprobación": ("Probabilidad de aprobación", "probabilidades de aprobacion",
                                       "posibilidades de ser aprobado"),
    }

    def test_each_phrase_has_its_label(self):
        for label, samples in self.LABELED.items():
            for sample in samples:
                with self.subTest(sample=sample):
                    self.assertEqual(rules.find_forbidden_phrase(sample), label)

    def test_fullwidth_and_invisible_variants_are_caught(self):
        for sample, label in (("事前\u200b承認", "事前承認"), ("審査\u3000なし", "審査なし"),
                              ("ＰＲＥＡＰＲＯＢＡＤＯ", "preaprobado"),
                              ("pre\u200baprobado", "preaprobado"),
                              ("APROBACIÓN GARANTIZADA", "aprobación garantizada")):
            with self.subTest(sample=sample):
                self.assertEqual(rules.find_forbidden_phrase(sample), label)

    def test_phrase_in_any_ja_or_es_field_fails_validation(self):
        for path in JA_ES_PATHS:
            for sample in ("事前承認", "審査なし", "Aprobación garantizada",
                           "Sin verificación de crédito"):
                assert_flagged(self, path, sample, "금지 문구")

    def test_ordinary_ja_and_es_text_passes(self):
        texts = ["延長保証", "購入保護と延長保証", "年間$300の旅行クレジット", "承認はカード会社が判断します",
                 "審査はカード会社が行います", "ポイントの有効期限なし", "年会費無料",
                 "Garantía extendida", "La aprobación depende del emisor",
                 "Salida tardía garantizada", "Crédito anual de $300 para viajes",
                 "Sin cargos por transacciones en el extranjero", "Sin cuota anual",
                 "Se requiere verificación de crédito", "Sin límite de reembolso en efectivo"]
        for path in ("bonus.current.note_ja", "benefits[0].es"):
            for text in texts:
                with self.subTest(path=path, text=text):
                    self.assertEqual(check(with_value(make_card(), path, text)), [])

    def test_long_whitespace_runs_stay_fast(self):
        import time

        from cardlib import phrases

        for head in ("承認", "事前", "与信審査", "審査", "審査に", "必ず", "必ず審査", "保証",
                     "保証された", "aprobación", "sin", "sin verificación de", "probabilidad de",
                     "garantizamos", "pre"):
            text = head + " " * 64000 + "x"
            with self.subTest(head=head):
                started = time.perf_counter()
                self.assertIsNone(phrases.find_forbidden_phrase(text))
                self.assertLess(time.perf_counter() - started, 1.0)
        for head in ("マイル", "ドクター", "ドクター オブ", "フリークエント", "ポインツ", "ザ", "ザ ポイント"):
            text = head + " " * 64000 + "x"
            with self.subTest(community_head=head):
                started = time.perf_counter()
                self.assertIsNone(phrases.find_community_marker(text))
                self.assertLess(time.perf_counter() - started, 1.0)


class JapaneseCommunityNameTest(unittest.TestCase):
    """Community sources written in katakana fail too (Spanish uses the Latin names)."""

    MARKERS = ("マイルモア", "マイル・モア", "ドクターオブクレジット", "ドクター・オブ・クレジット",
               "フリークエントマイラー", "フリークエント・マイラー", "レディット", "ﾚﾃﾞｨｯﾄ",
               "ザ・ポイント・ガイ", "ポインツガイ", "ザ・ポインツ・ガイ")

    def test_katakana_names_are_caught(self):
        for marker in self.MARKERS:
            with self.subTest(marker=marker):
                self.assertIsNotNone(rules.find_community_marker(marker))
        for path in JA_ES_PATHS:
            assert_flagged(self, path, "レディットで見た", "커뮤니티")

    def test_ordinary_katakana_passes(self):
        for text in ("年間$300の旅行クレジット", "クレディット", "ポイントガイド", "ポイント",
                     "マイル", "ドクター"):
            with self.subTest(text=text):
                self.assertIsNone(rules.find_community_marker(text))
