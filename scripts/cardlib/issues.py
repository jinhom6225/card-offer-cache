"""Validation issue type shared by every rule."""

from dataclasses import dataclass

ERROR = "error"
WARNING = "warning"

_LABELS = {ERROR: "오류", WARNING: "경고"}


@dataclass(frozen=True)
class Issue:
    """One problem found in cards.yaml.

    ``card`` is the card id (or "카드 N번" when the id is unusable) and ``path``
    is the field path such as ``bonus.current.parts[0].unit``.
    """

    level: str
    card: str
    path: str
    message: str

    def __str__(self):
        return f"[{_LABELS[self.level]}] {self.card} → {self.path}: {self.message}"


def error(card, path, message):
    return Issue(ERROR, card, path, message)


def warning(card, path, message):
    return Issue(WARNING, card, path, message)


def join_path(parent, key):
    """Build ``parent.key`` (or just ``key`` at the top level)."""
    return f"{parent}.{key}" if parent else str(key)
