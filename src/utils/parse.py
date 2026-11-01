"""Parsing helpers for values coming from users, Discord messages or Excel."""


def to_int(value: object, default: int = 0) -> int:
    """Best-effort int conversion; `default` when the value is not numeric."""
    try:
        if isinstance(value, (bool, int, float)):
            return int(value)
        return int(str(value).strip())
    except (TypeError, ValueError, OverflowError):
        return default


if __name__ == "__main__":
    import math

    assert to_int("42") == 42
    assert to_int(" 7 ") == 7
    assert to_int(None) == 0
    assert to_int("basura", -1) == -1
    assert to_int(3.9) == 3
    assert to_int(math.nan, 5) == 5
    assert to_int(math.inf, 5) == 5
    assert to_int(True) == 1
    print("parse self-check ok")
