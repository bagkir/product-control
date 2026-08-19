from datetime import date


def _parse_date(
    value: str | None,
) -> date | None:
    if not value:
        return None

    return date.fromisoformat(value)
