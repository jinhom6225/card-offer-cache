"""Text patterns: forbidden credit-decision phrases, community sources, URL shorteners.

All matching runs on ``normalize(text)``: percent-decoded, NFKC (fullwidth ->
ASCII), casefolded, with invisible format chars (zero-width space etc.) removed.
"""

import re
import unicodedata
from urllib.parse import unquote

# Optional separator between words: spaces, hyphens/dashes, underscores (or nothing).
_SEP = r"[\s\-_‐-―]*"
# Optional separator inside Korean phrases.
_KS = r"[\s\-]*"


def _compile(table):
    return tuple((label, re.compile(pattern)) for label, pattern in table)


# Phrases implying a credit decision (policy.md rule 9; Play deceptive behavior).
FORBIDDEN_PATTERNS = _compile((
    ("pre-approved", rf"\bpre{_SEP}approv(?:ed|al)\b"),
    ("pre-qualified", rf"\bpre{_SEP}qualif(?:ied|y|ication)\b"),
    ("guaranteed approval", rf"\bguarantee[ds]?{_SEP}(?:approval|acceptance)\b"),
    ("guaranteed approval", rf"\b(?:approval|acceptance){_SEP}(?:is{_SEP})?guaranteed\b"),
    ("guaranteed approval", rf"\bguaranteed{_SEP}(?:to{_SEP}be{_SEP})?(?:approved|accepted)\b"),
    ("instant approval", rf"\binstant(?:ly)?{_SEP}approv(?:al|ed)\b"),
    ("no credit check", rf"\b(?:no|without(?:{_SEP}a)?){_SEP}credit{_SEP}checks?\b"),
    ("approval odds", rf"\bapproval{_SEP}odds\b"),
    ("best card for you", rf"\bbest{_SEP}cards?{_SEP}for{_SEP}your?\b"),
    ("사전 승인", rf"사전{_KS}승인"),
    ("승인 보장", rf"승인(?:{_KS}(?:을|이|은))?{_KS}보장|보장{_KS}(?:된|되는){_KS}승인"),
    ("무조건 승인", rf"무조건{_KS}승인"),
    ("신용조회 없음", rf"신용{_KS}조회{_KS}(?:없|불필요|필요{_KS}없|안{_KS}함)"),
    ("승인 가능성", rf"승인(?:{_KS}(?:될|이{_KS}될|받을))?{_KS}(?:가능성|확률)"),
))

# Community sources must never appear in app data.
COMMUNITY_PATTERNS = _compile((
    ("milemoa", rf"mile{_SEP}moa"),
    ("마일모아", rf"마일{_KS}모아"),
    ("doctorofcredit", rf"doctor{_SEP}of{_SEP}credit"),
    ("닥터오브크레딧", rf"닥터{_KS}오브{_KS}크레딧"),
    ("frequentmiler", rf"frequent{_SEP}miler"),
    ("프리퀀트 마일러", rf"프리퀀트{_KS}마일러"),
    ("reddit", r"reddit|redd\.it"),
    ("레딧", r"(?<!크)레딧"),  # not 크레딧 (credit)
    ("r/게시판", r"(?:^|[\s(\[{<\"'“‘,;:])/?r/[a-z0-9_]{2,}"),
    ("thepointsguy", rf"the{_SEP}points{_SEP}guy"),
    ("더 포인츠 가이", rf"더{_KS}포인츠{_KS}가이"),
))

SHORTENER_DOMAINS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
                     "buff.ly", "rebrand.ly", "lnkd.in")
SHORTENER_PATTERNS = _compile(
    (domain, rf"(?<![a-z0-9-]){re.escape(domain)}(?![a-z0-9-])") for domain in SHORTENER_DOMAINS)


def normalize(text):
    """Percent-decode (up to 3 times), NFKC, casefold and drop invisible format chars."""
    for _ in range(3):
        decoded = unquote(text)
        if decoded == text:
            break
        text = decoded
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if unicodedata.category(ch) != "Cf")


def _first_label(text, patterns):
    normalized = normalize(text)
    return next((label for label, pattern in patterns if pattern.search(normalized)), None)


def find_forbidden_phrase(text):
    """Return the label of the forbidden phrase found in ``text``, or None."""
    return _first_label(text, FORBIDDEN_PATTERNS)


def find_community_marker(text):
    """Return the label of the community source found in ``text``, or None."""
    return _first_label(text, COMMUNITY_PATTERNS)


def find_shortener(text):
    """Return the URL-shortener domain found in ``text``, or None."""
    return _first_label(text, SHORTENER_PATTERNS)
