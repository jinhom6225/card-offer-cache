"""Declarative field specs. Each spec checks one value and returns a list of Issues.

``None`` (or a missing key) means "absent": an error for required fields,
fine for optional ones. Specs never modify the values they check.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from types import MappingProxyType

from .issues import error, join_path, warning
from .urls import ISSUER_DOMAINS, https_host, is_issuer_url

MISSING = "필수 항목입니다. 값을 적어 주세요."
NOT_TEXT = "글자여야 합니다. yes/no·숫자·날짜처럼 보이는 글자는 따옴표로 감싸세요(예: \"no\")."
NOT_NUMBER = "숫자만 적어 주세요(쉼표·$·% 없이, 예: 4000)."
NOT_FINITE = "실제 숫자를 적어 주세요(.nan·.inf 같은 값은 쓸 수 없습니다)."
NOT_BOOL = "true 또는 false로 적어 주세요."
NOT_DATE = "날짜는 YYYY-MM-DD 형식의 실제 날짜여야 합니다(예: 2026-11-09)."
NOT_LIST = "목록이어야 합니다(각 줄을 '- '로 시작)."
NOT_MAPPING = "하위 항목(이름: 값)들로 적어야 합니다."
UNKNOWN_KEY = "알 수 없는 항목입니다. 오타인지 확인하세요(앱에는 쓰이지 않습니다)."
UNKNOWN_STRICT_KEY = ("알 수 없는 항목입니다. 보너스(bonus)·높음 표시(elevated) 안에는 "
                      "정해진 항목만 쓸 수 있습니다. 오타인지 확인하세요.")
BAD_URL = ("https:// 로 시작하는 올바른 주소여야 합니다(아이디·비밀번호, 빈칸, 역슬래시, "
           "443 외 포트, 영문 소문자·숫자·'.'·'-' 밖의 도메인 글자는 안 됨)")


def parse_date(value):
    """Normalize a YAML date (``date`` object or ``YYYY-MM-DD`` string) to ``date``.

    Raises ValueError for anything else, including datetimes and booleans.
    """
    if isinstance(value, datetime):
        raise ValueError("datetime is not a date")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    raise ValueError(f"not a YYYY-MM-DD date: {value!r}")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Spec:
    required = True

    def check(self, value, path, card):
        if value is None:
            return [error(card, path, MISSING)] if self.required else []
        return self.check_present(value, path, card)

    def check_present(self, value, path, card):  # pragma: no cover - abstract
        raise NotImplementedError


@dataclass(frozen=True)
class Text(Spec):
    required: bool = True
    pattern: str | None = None
    pattern_hint: str = ""
    choices: tuple = ()

    def check_present(self, value, path, card):
        if not isinstance(value, str):
            return [error(card, path, NOT_TEXT)]
        if not value.strip():
            return [error(card, path, MISSING)] if self.required else []
        return self.check_text(value, path, card)

    def check_text(self, value, path, card):
        if self.pattern and not re.fullmatch(self.pattern, value):
            return [error(card, path, f"형식이 맞지 않습니다: '{value}'. {self.pattern_hint}")]
        if self.choices and value not in self.choices:
            allowed = ", ".join(self.choices)
            return [error(card, path, f"허용되지 않는 값입니다: '{value}'. 다음 중 하나: {allowed}")]
        return []


@dataclass(frozen=True)
class Url(Text):
    issuer_only: bool = False

    def check_text(self, value, path, card):
        if https_host(value) is None:
            return [error(card, path, f"{BAD_URL}: '{value}'")]
        if self.issuer_only and not is_issuer_url(value):
            domains = ", ".join(ISSUER_DOMAINS.values())
            return [error(card, path, (
                f"발급사 공식 도메인 주소가 아닙니다: '{https_host(value)}'. "
                f"허용 도메인(하위 도메인 포함): {domains}"))]
        return []


@dataclass(frozen=True)
class Number(Spec):
    minimum: float = 0
    above_minimum: bool = False
    maximum: float | None = None
    integer: bool = False

    def check_present(self, value, path, card):
        if not _is_number(value):
            return [error(card, path, NOT_NUMBER)]
        if isinstance(value, float) and not math.isfinite(value):
            return [error(card, path, NOT_FINITE)]
        if self.integer and isinstance(value, float) and not value.is_integer():
            return [error(card, path, "정수(소수점 없이)여야 합니다.")]
        if self.above_minimum and value <= self.minimum:
            return [error(card, path, f"{self.minimum:g}보다 커야 합니다.")]
        if value < self.minimum:
            return [error(card, path, f"{self.minimum:g} 이상이어야 합니다.")]
        if self.maximum is not None and value > self.maximum:
            return [error(card, path, f"{self.maximum:g} 이하여야 합니다.")]
        return []


@dataclass(frozen=True)
class Bool(Spec):
    def check_present(self, value, path, card):
        return [] if isinstance(value, bool) else [error(card, path, NOT_BOOL)]


@dataclass(frozen=True)
class Date(Spec):
    required: bool = True

    def check_present(self, value, path, card):
        if isinstance(value, datetime):
            return [error(card, path, "날짜만 적어 주세요(시각 없이, 예: 2026-11-09).")]
        try:
            parse_date(value)
        except ValueError:
            return [error(card, path, NOT_DATE)]
        return []


@dataclass(frozen=True)
class ListOf(Spec):
    item: Spec
    min_items: int = 1

    def check_present(self, value, path, card):
        if not isinstance(value, list):
            return [error(card, path, NOT_LIST)]
        if len(value) < self.min_items:
            return [error(card, path, f"최소 {self.min_items}개가 있어야 합니다.")]
        return [issue for index, item in enumerate(value)
                for issue in self.item.check(item, f"{path}[{index}]", card)]


@dataclass(frozen=True)
class Mapping(Spec):
    """A mapping with known ``fields``. Unknown keys warn, or fail when ``strict``."""

    fields: dict = field(default_factory=dict)
    required: bool = True
    strict: bool = False

    def __post_init__(self):
        # Specs are shared module-level constants; make the field table read-only.
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def check_present(self, value, path, card):
        if not isinstance(value, dict):
            return [error(card, path, NOT_MAPPING)]
        known = [issue for name, spec in self.fields.items()
                 for issue in spec.check(value.get(name), join_path(path, name), card)]
        return known + [self._unknown(card, join_path(path, key))
                        for key in value if key not in self.fields]

    def _unknown(self, card, path):
        if self.strict:
            return error(card, path, UNKNOWN_STRICT_KEY)
        return warning(card, path, UNKNOWN_KEY)
