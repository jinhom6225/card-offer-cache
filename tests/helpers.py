"""Shared test helpers: a valid card factory and path-based copy-on-write edits."""

import copy
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

TODAY = date(2026, 11, 9)

_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def make_card(card_id="sample-travel-card"):
    """Return a brand-new, fully valid card dict."""
    return {
        "id": card_id,
        "name": "Sample Travel Card",
        "issuer": "Chase",
        "segment": "personal",
        "official_url": "https://creditcards.chase.com/sample",
        "last_verified": "2026-11-01",
        "sources": ["https://creditcards.chase.com/sample"],
        "annual_fee": {"amount": 95, "first_year_waived": False},
        "foreign_tx_fee_pct": 0,
        "bonus": {
            "current": {
                "parts": [{"value": 75000, "unit": "points"}],
                "min_spend": 4000,
                "spend_months": 3,
                "note_en": "Sample note",
                "note_ko": "샘플 설명",
            },
            "usual": {
                "parts": [{"value": 60000, "unit": "points"}],
                "note_en": "Usual note",
                "note_ko": "평소 설명",
            },
        },
        "elevated": {"start": "2026-10-01", "end": "2026-12-31"},
        "earn": [
            {"category_en": "Travel", "category_ko": "여행", "rate": 2, "unit": "points"}
        ],
        "benefits": [{"en": "Trip delay insurance", "ko": "여행 지연 보험"}],
    }


def _tokens(path):
    return [name if name else int(index) for name, index in _TOKEN.findall(path)]


def _parent(root, tokens):
    node = root
    for token in tokens[:-1]:
        node = node[token]
    return node


def with_value(card, path, value):
    """Return a deep copy of ``card`` with ``path`` (e.g. ``a.b[0].c``) set to ``value``."""
    result = copy.deepcopy(card)
    tokens = _tokens(path)
    _parent(result, tokens)[tokens[-1]] = value
    return result


def without(card, path):
    """Return a deep copy of ``card`` with the key/item at ``path`` removed."""
    result = copy.deepcopy(card)
    tokens = _tokens(path)
    del _parent(result, tokens)[tokens[-1]]
    return result


def errors_of(issues):
    return [issue for issue in issues if issue.level == "error"]


def warnings_of(issues):
    return [issue for issue in issues if issue.level == "warning"]


def paths_of(issues):
    return {issue.path for issue in issues}
