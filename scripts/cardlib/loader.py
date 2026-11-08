"""A strict YAML loader for cards.yaml, built on ``yaml.SafeLoader`` (no python tags).

On top of SafeLoader it refuses things a hand editor never means to write:
duplicate keys (YAML keeps the last one silently), aliases (``*name``),
non-decimal integers (``0500`` is octal 320, ``1:30`` is 90) and impossible
dates. Every refusal is a ``CardFileError`` with a Korean, line-numbered message.
"""

import re

import yaml

_MERGE_TAG = "tag:yaml.org,2002:merge"
_DECIMAL_INT = re.compile(r"[-+]?(?:0|[1-9][0-9_]*)")
_NUMBER_HINT = ("숫자로 읽을 수 없습니다. 0으로 시작하거나 ':'·0x가 들어간 숫자는 "
                "YAML이 다른 값으로 바꿉니다. 숫자만 적어 주세요(예: 500). "
                "글자라면 따옴표로 감싸세요.")


class CardFileError(Exception):
    """cards.yaml could not be read as a card list (message is Korean)."""


def _line(node_or_event):
    return node_or_event.start_mark.line + 1


class CardLoader(yaml.SafeLoader):
    """SafeLoader + duplicate-key, alias, number and date checks."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            event = self.peek_event()
            raise CardFileError(
                f"{_line(event)}번째 줄: 별칭(*{event.anchor})은 쓸 수 없습니다. "
                "값을 직접 적어 주세요.")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self._reject_duplicate_keys(node)
        return super().construct_mapping(node, deep=deep)

    def _reject_duplicate_keys(self, node):
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == _MERGE_TAG:
                continue
            key = self.construct_object(key_node, deep=True)
            try:
                is_duplicate = key in seen
            except TypeError:
                continue  # unhashable key: SafeConstructor reports it
            if is_duplicate:
                raise CardFileError(f"{_line(key_node)}번째 줄: '{key}' 항목이 두 번 있습니다. "
                                    "하나만 남기세요.")
            seen.add(key)

    def construct_decimal_int(self, node):
        if not _DECIMAL_INT.fullmatch(node.value):
            raise CardFileError(f"{_line(node)}번째 줄: '{node.value}'는 {_NUMBER_HINT}")
        return self.construct_yaml_int(node)

    def construct_plain_float(self, node):
        if ":" in node.value:
            raise CardFileError(f"{_line(node)}번째 줄: '{node.value}'는 {_NUMBER_HINT}")
        return self.construct_yaml_float(node)

    def construct_checked_date(self, node):
        try:
            return self.construct_yaml_timestamp(node)
        except ValueError as exc:
            raise CardFileError(
                f"{_line(node)}번째 줄에 달력에 없는 날짜가 있습니다: {node.value}") from exc


CardLoader.add_constructor("tag:yaml.org,2002:int", CardLoader.construct_decimal_int)
CardLoader.add_constructor("tag:yaml.org,2002:float", CardLoader.construct_plain_float)
CardLoader.add_constructor("tag:yaml.org,2002:timestamp", CardLoader.construct_checked_date)


def parse_yaml(text, path):
    """Parse ``text`` with CardLoader; every failure becomes a Korean CardFileError."""
    try:
        return yaml.load(text, Loader=CardLoader)  # noqa: S506 - CardLoader is a SafeLoader
    except CardFileError as exc:
        raise CardFileError(f"{path}: {exc}") from exc
    except yaml.MarkedYAMLError as exc:
        line = exc.problem_mark.line + 1 if exc.problem_mark else "?"
        raise CardFileError(f"{path}: YAML 문법 오류({line}번째 줄 근처): {exc.problem}") from exc
    except yaml.YAMLError as exc:
        raise CardFileError(f"{path}: YAML을 읽지 못했습니다: {exc}") from exc
    except RecursionError as exc:
        raise CardFileError(f"{path}: 목록·항목이 너무 깊게 겹쳐 있어 읽을 수 없습니다.") from exc
    except ValueError as exc:
        raise CardFileError(
            f"{path}: 값을 읽지 못했습니다({exc}). 날짜·숫자 형식을 확인하세요.") from exc
