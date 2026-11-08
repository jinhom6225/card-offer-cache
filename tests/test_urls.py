"""Strict https URL rule, issuer enum and issuer -> official domain table."""

import unittest

from helpers import TODAY, errors_of, make_card, paths_of, with_value

from cardlib import rules, schema

URL_FIELDS = ("official_url", "sources[0]")

ISSUER_URLS = {
    "Chase": ["https://chase.com/", "https://creditcards.chase.com/a?b=c",
              "https://WWW.CHASE.COM/x", "https://creditcards.chase.com:443/x"],
    "American Express": ["https://www.americanexpress.com/us/credit-cards/"],
    "Citi": ["https://www.citi.com/credit-cards"],
    "Capital One": ["https://www.capitalone.com/x"],
    "Discover": ["https://www.discover.com/credit-cards/"],
    "Wells Fargo": ["https://www.wellsfargo.com/x"],
    "Bank of America": ["https://www.bankofamerica.com/credit-cards/"],
}


def check(card):
    return errors_of(schema.validate([card], today=TODAY))


def card_for(issuer, url):
    return with_value(with_value(make_card(), "issuer", issuer), "official_url", url)


class HttpsTest(unittest.TestCase):
    def assert_rejected(self, urls):
        for path in URL_FIELDS:
            for url in urls:
                with self.subTest(path=path, url=url):
                    self.assertIn(path, paths_of(check(with_value(make_card(), path, url))))

    def test_non_https_urls_fail(self):
        self.assert_rejected(["http://creditcards.chase.com/x", "ftp://chase.com/x",
                              "chase.com/x", "https://", "https:///path",
                              "javascript:alert(1)", "", False])

    def test_userinfo_fails(self):
        self.assert_rejected(["https://chase.com@evil.io/x", "https://user@chase.com/x",
                              "https://user:pw@chase.com/x", "https://:@chase.com/x"])

    def test_backslash_whitespace_and_control_chars_fail(self):
        self.assert_rejected(["https://chase.com\\@evil.io/x", "https://chase.com/a\\b",
                              " https://chase.com/x", "https://chase.com/x ",
                              "https://chase.com/a b", "https://chase.com/a\tb",
                              "https://chase.com/\x07", "https://chase.com/a\u200bb",
                              "https://chase.com/　"])

    def test_bad_host_characters_fail(self):
        self.assert_rejected(["https://*.chase.com/x", "https://chase_cards.com/x",
                              "https://chase..com/x", "https://.chase.com/x",
                              "https://ch%61se.com/x", "https://[::1]/x",
                              "https://-chase.com/x", "https://chase-.com/x"])

    def test_ports_other_than_443_fail(self):
        self.assert_rejected(["https://chase.com:8443/x", "https://chase.com:0/x",
                              "https://chase.com:abc/x", "https://chase.com:/x",
                              "https://chase.com:99999/x"])

    def test_https_source_on_any_non_community_domain_passes(self):
        card = with_value(make_card(), "sources", [
            "https://creditcards.chase.com/sample", "https://www.consumerfinance.gov/x",
            "https://www.consumerfinance.gov:443/x"])
        self.assertEqual(check(card), [])

    def test_https_host_helper(self):
        self.assertEqual(rules.https_host("https://Cards.Chase.com:443/x"), "cards.chase.com")
        self.assertIsNone(rules.https_host("https://a@chase.com/"))
        self.assertIsNone(rules.https_host(None))


class IssuerDomainTest(unittest.TestCase):
    def test_each_issuer_with_its_own_domain_passes(self):
        for issuer, urls in ISSUER_URLS.items():
            for url in urls:
                with self.subTest(issuer=issuer, url=url):
                    self.assertEqual(check(card_for(issuer, url)), [])

    def test_issuer_table_matches_allowlist(self):
        self.assertEqual(dict(rules.ISSUER_DOMAINS), {
            "Chase": "chase.com", "American Express": "americanexpress.com",
            "Citi": "citi.com", "Capital One": "capitalone.com", "Discover": "discover.com",
            "Wells Fargo": "wellsfargo.com", "Bank of America": "bankofamerica.com"})
        with self.assertRaises(TypeError):
            rules.ISSUER_DOMAINS["Evil"] = "evil.io"

    def test_unknown_issuer_fails(self):
        for issuer in ("chase", "Amex", "Synchrony", "JPMorgan Chase"):
            with self.subTest(issuer=issuer):
                issues = check(with_value(make_card(), "issuer", issuer))
                self.assertIn("issuer", paths_of(issues))
                self.assertTrue(any("Chase" in i.message for i in issues))

    def test_non_text_issuer_is_an_error_not_a_crash(self):
        for issuer in (["Chase"], {"name": "Chase"}, 1):
            with self.subTest(issuer=issuer):
                self.assertIn("issuer", paths_of(check(with_value(make_card(), "issuer", issuer))))

    def test_official_url_of_another_issuer_fails(self):
        issues = check(card_for("Chase", "https://www.americanexpress.com/x"))
        self.assertEqual(paths_of(issues), {"official_url"})
        self.assertIn("chase.com", issues[0].message)

    def test_lookalike_and_foreign_domains_fail(self):
        urls = ["https://chase.com.evil.io/x", "https://evilchase.com/x",
                "https://chase.co/x", "https://www.nerdwallet.com/x",
                "https://americanexpress.com-offer.io/x"]
        for url in urls:
            with self.subTest(url=url):
                issues = check(with_value(make_card(), "official_url", url))
                self.assertEqual(paths_of(issues), {"official_url"})
                self.assertTrue(any("발급사" in i.message for i in issues))

    def test_is_issuer_url_helper(self):
        self.assertTrue(rules.is_issuer_url("https://card.citi.com/x"))
        self.assertTrue(rules.is_issuer_url("https://card.citi.com/x", issuer="Citi"))
        self.assertFalse(rules.is_issuer_url("https://card.citi.com/x", issuer="Chase"))
        self.assertFalse(rules.is_issuer_url("https://citi.com.example.org/x"))
        self.assertFalse(rules.is_issuer_url("http://citi.com/x"))
        self.assertFalse(rules.is_issuer_url("https://[::1/x"))
        self.assertFalse(rules.is_issuer_url(None))


if __name__ == "__main__":
    unittest.main()
