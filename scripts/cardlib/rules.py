"""Content rules checked in every string of a card (values and key names)."""

from .issues import error, join_path
from .phrases import find_community_marker, find_forbidden_phrase, find_shortener
from .urls import ISSUER_DOMAINS, https_host, is_issuer_url

__all__ = ["ISSUER_DOMAINS", "https_host", "is_issuer_url", "iter_strings",
           "check_text_content", "find_forbidden_phrase", "find_community_marker",
           "find_shortener"]


def iter_strings(node, path=""):
    """Yield ``(path, text)`` for every string inside ``node``, including dict keys.

    Lists and tuples are walked in order, sets in a stable (repr-sorted) order.
    """
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            child = join_path(path, key)
            yield from iter_strings(key, child)
            yield from iter_strings(value, child)
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            yield from iter_strings(value, f"{path}[{index}]")
    elif isinstance(node, (set, frozenset)):
        for index, value in enumerate(sorted(node, key=repr)):
            yield from iter_strings(value, f"{path}[{index}]")


def _text_issues(label, path, text):
    issues = []
    marker = find_community_marker(text)
    if marker:
        issues.append(error(label, path, (
            f"커뮤니티 출처('{marker}')는 어떤 항목에도 넣을 수 없습니다. "
            "카드사 공식 페이지만 적어 주세요.")))
    shortener = find_shortener(text)
    if shortener:
        issues.append(error(label, path, (
            f"단축 주소('{shortener}')는 쓸 수 없습니다. "
            "카드사 공식 페이지의 원래 주소를 적어 주세요.")))
    phrase = find_forbidden_phrase(text)
    if phrase:
        issues.append(error(label, path, (
            f"금지 문구('{phrase}')가 있습니다. "
            "승인·신용 판단을 암시하는 표현은 쓸 수 없습니다.")))
    return issues


def check_text_content(card, label):
    """Community sources, URL shorteners and forbidden phrases, in every string of the card."""
    return [issue for path, text in iter_strings(card)
            for issue in _text_issues(label, path, text)]
