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
# Optional separator inside Japanese phrases (no \b: it never matches between CJK chars).
_JS = r"[\s\-・]*"
# Spanish letters that people often type without the accent.
_O = "[oó]"
_E = "[eé]"


def _compile(table):
    return tuple((label, re.compile(pattern)) for label, pattern in table)


# Phrases implying a credit decision (policy.md rule 9; Play deceptive behavior),
# in every app language: English, Korean, Japanese, Spanish.
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
    # Japanese (plan A7). 与信審査不要 comes before 審査なし (the first match names the label).
    ("事前承認", rf"事前{_JS}承認"),
    ("承認保証", rf"承認(?:{_JS}[がをは])?{_JS}保証|保証{_JS}(?:(?:された|される|付きの){_JS})?承認"),
    ("承認保証", rf"必ず{_JS}承認"),
    ("必ず審査に通る", rf"必ず{_JS}審査{_JS}(?:に{_JS})?(?:通|合格)|審査{_JS}(?:に{_JS})?必ず{_JS}(?:通|合格)"),
    ("与信審査不要", rf"(?:与信|信用){_JS}(?:審査|調査|チェック){_JS}(?:不要|なし|無し|なく|せず)"),
    ("審査なし", rf"審査{_JS}(?:不要|なし|無し|なく|せず)"),
    ("承認の可能性", rf"承認(?:{_JS}(?:の|される))?{_JS}(?:可能性|確率|見込み)|承認{_JS}率"),
    # Spanish (plan A7). Accents optional, any gender/number.
    ("preaprobado", rf"\bpre{_SEP}aprobad[oa]s?\b|\bpre{_SEP}aprobaci{_O}n(?:es)?\b"),
    ("precalificado", rf"\bpre{_SEP}calificad[oa]s?\b|\bpre{_SEP}calificaci{_O}n(?:es)?\b"),
    ("aprobación garantizada",
     rf"\baprobaci{_O}n{_SEP}(?:est[aá]{_SEP})?garantizada\b"),
    ("aprobación garantizada",
     rf"\b(?:garantizamos|garantiza|garantizan|garant[ií]a){_SEP}(?:de{_SEP}|la{_SEP})?aprobaci{_O}n\b"),
    ("sin verificación de crédito",
     rf"\bsin{_SEP}(?:verificaci{_O}n|consulta|chequeo|comprobaci{_O}n){_SEP}del?{_SEP}cr{_E}dito\b"),
    ("sin revisión de crédito", rf"\bsin{_SEP}revisi{_O}n{_SEP}del?{_SEP}cr{_E}dito\b"),
    ("probabilidad de aprobación",
     rf"\b(?:probabilidad|posibilidad)(?:es)?{_SEP}de{_SEP}(?:aprobaci{_O}n|ser{_SEP}aprobad[oa]s?)\b"),
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
    # Japanese katakana spellings (plan A7); Spanish uses the Latin names above.
    ("マイルモア", rf"マイル{_JS}モア"),
    ("ドクター・オブ・クレジット", rf"ドクター{_JS}オブ{_JS}クレジット"),
    ("フリークエント・マイラー", rf"フリー?クエント{_JS}マイラー"),
    ("レディット", r"(?<!ク)レディット"),  # not クレディット (credit)
    ("ザ・ポインツ・ガイ", rf"ポインツ{_JS}ガイ|ザ{_JS}ポイント{_JS}ガイ(?!ド)"),
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
