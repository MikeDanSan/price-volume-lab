"""Tests for the live paper-trading scheduler helpers (no network, no sleep)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from cli.scheduler import (
    ET,
    is_market_open,
    next_bar_close,
    next_market_open,
    parse_tf_minutes,
)

# ---------------------------------------------------------------------------
# parse_tf_minutes
# ---------------------------------------------------------------------------

def test_parse_15m() -> None:
    assert parse_tf_minutes("15m") == 15


def test_parse_1h() -> None:
    assert parse_tf_minutes("1h") == 60


def test_parse_5m() -> None:
    assert parse_tf_minutes("5m") == 5


def test_parse_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        parse_tf_minutes("1d")


# ---------------------------------------------------------------------------
# is_market_open
# ---------------------------------------------------------------------------

def test_market_open_during_session() -> None:
    tuesday_noon = datetime(2026, 2, 17, 12, 0, tzinfo=ET)
    assert is_market_open(tuesday_noon) is True


def test_market_closed_before_open() -> None:
    tuesday_early = datetime(2026, 2, 17, 8, 0, tzinfo=ET)
    assert is_market_open(tuesday_early) is False


def test_market_closed_after_close() -> None:
    tuesday_evening = datetime(2026, 2, 17, 20, 0, tzinfo=ET)
    assert is_market_open(tuesday_evening) is False


def test_market_closed_at_exact_close() -> None:
    tuesday_close = datetime(2026, 2, 17, 16, 0, tzinfo=ET)
    assert is_market_open(tuesday_close) is False


def test_market_open_at_exact_open() -> None:
    tuesday_open = datetime(2026, 2, 17, 9, 30, tzinfo=ET)
    assert is_market_open(tuesday_open) is True


def test_market_closed_saturday() -> None:
    saturday = datetime(2026, 2, 21, 12, 0, tzinfo=ET)
    assert is_market_open(saturday) is False


def test_market_closed_sunday() -> None:
    sunday = datetime(2026, 2, 22, 12, 0, tzinfo=ET)
    assert is_market_open(sunday) is False


# ---------------------------------------------------------------------------
# next_market_open
# ---------------------------------------------------------------------------

def test_next_market_open_before_open_same_day() -> None:
    tuesday_early = datetime(2026, 2, 17, 8, 0, tzinfo=ET)
    nxt = next_market_open(tuesday_early)
    assert nxt == datetime(2026, 2, 17, 9, 30, tzinfo=ET)


def test_next_market_open_after_close_weekday() -> None:
    tuesday_evening = datetime(2026, 2, 17, 20, 0, tzinfo=ET)
    nxt = next_market_open(tuesday_evening)
    assert nxt == datetime(2026, 2, 18, 9, 30, tzinfo=ET)


def test_next_market_open_during_session() -> None:
    tuesday_noon = datetime(2026, 2, 17, 12, 0, tzinfo=ET)
    nxt = next_market_open(tuesday_noon)
    assert nxt == datetime(2026, 2, 18, 9, 30, tzinfo=ET)


def test_next_market_open_saturday() -> None:
    saturday = datetime(2026, 2, 21, 10, 0, tzinfo=ET)
    nxt = next_market_open(saturday)
    assert nxt == datetime(2026, 2, 23, 9, 30, tzinfo=ET)


def test_next_market_open_friday_after_close() -> None:
    friday_evening = datetime(2026, 2, 20, 17, 0, tzinfo=ET)
    nxt = next_market_open(friday_evening)
    assert nxt == datetime(2026, 2, 23, 9, 30, tzinfo=ET)


def test_next_market_open_sunday() -> None:
    sunday = datetime(2026, 2, 22, 14, 0, tzinfo=ET)
    nxt = next_market_open(sunday)
    assert nxt == datetime(2026, 2, 23, 9, 30, tzinfo=ET)


# ---------------------------------------------------------------------------
# next_bar_close
# ---------------------------------------------------------------------------

def _mkt(day: datetime):
    m_open = day.replace(hour=9, minute=30, second=0, microsecond=0)
    m_close = day.replace(hour=16, minute=0, second=0, microsecond=0)
    return m_open, m_close


def test_next_bar_close_alignment_15m() -> None:
    """9:42 with 15m bars -> next close at 9:45."""
    day = datetime(2026, 2, 17, 9, 42, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 15, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 9, 45, tzinfo=ET)


def test_next_bar_close_at_boundary() -> None:
    """Exactly at 10:00 -> next close at 10:15."""
    day = datetime(2026, 2, 17, 10, 0, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 15, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 10, 15, tzinfo=ET)


def test_next_bar_close_first_bar() -> None:
    """At market open -> first close at 9:45."""
    day = datetime(2026, 2, 17, 9, 30, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 15, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 9, 45, tzinfo=ET)


def test_next_bar_close_capped_at_market_close() -> None:
    """Near end of day, don't overshoot 16:00."""
    day = datetime(2026, 2, 17, 15, 55, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 15, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 16, 0, tzinfo=ET)


def test_next_bar_close_5m_alignment() -> None:
    """9:33 with 5m bars -> next close at 9:35."""
    day = datetime(2026, 2, 17, 9, 33, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 5, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 9, 35, tzinfo=ET)


def test_next_bar_close_1h_alignment() -> None:
    """10:15 with 1h bars -> next close at 10:30."""
    day = datetime(2026, 2, 17, 10, 15, tzinfo=ET)
    m_open, m_close = _mkt(day)
    nxt = next_bar_close(day, 60, m_open, m_close)
    assert nxt == datetime(2026, 2, 17, 10, 30, tzinfo=ET)
