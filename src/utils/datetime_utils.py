from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """
    Текущее время в UTC БЕЗ tzinfo.
    """
    return datetime.now(UTC).replace(tzinfo=None)
