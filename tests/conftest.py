"""Pytest fixtures: bar sequences for deterministic tests."""

from datetime import datetime, timezone

import pytest

from vpa_core.contracts import Bar


def _ts(year: int, month: int, day: int, hour: int = 9, minute: int = 30) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


@pytest.fixture
def symbol() -> str:
    return "SPY"


@pytest.fixture
def uptrend_bars(symbol: str) -> list[Bar]:
    """Five bars that form an uptrend (each close > prior close)."""
    return [
        Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), symbol),
        Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), symbol),
        Bar(101.0, 102.0, 100.5, 101.5, 1_050_000, _ts(2024, 1, 4), symbol),
        Bar(101.5, 102.5, 101.0, 102.0, 1_200_000, _ts(2024, 1, 5), symbol),
        Bar(102.0, 103.0, 101.5, 102.5, 900_000, _ts(2024, 1, 6), symbol),  # up bar, low vol
    ]


@pytest.fixture
def no_demand_bar_sequence(symbol: str) -> list[Bar]:
    """Uptrend then a clear no-demand bar: up close, low volume."""
    base = [
        Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), symbol),
        Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), symbol),
        Bar(101.0, 102.0, 100.5, 101.5, 1_050_000, _ts(2024, 1, 4), symbol),
        Bar(101.5, 102.5, 101.0, 102.0, 1_200_000, _ts(2024, 1, 5), symbol),
    ]
    # Current: up bar (102.5 > 102.0), volume 400k well below 1M+ baseline -> low relative volume
    no_demand_bar = Bar(
        102.0, 103.0, 101.5, 102.8, 400_000, _ts(2024, 1, 6), symbol
    )
    return base + [no_demand_bar]


@pytest.fixture
def down_bar_sequence(symbol: str) -> list[Bar]:
    """Five bars ending with a down bar."""
    return [
        Bar(100.0, 101.0, 99.0, 100.5, 1_000_000, _ts(2024, 1, 2), symbol),
        Bar(100.5, 101.5, 100.0, 101.0, 1_100_000, _ts(2024, 1, 3), symbol),
        Bar(101.0, 102.0, 100.5, 101.5, 1_050_000, _ts(2024, 1, 4), symbol),
        Bar(101.5, 102.5, 101.0, 102.0, 1_200_000, _ts(2024, 1, 5), symbol),
        Bar(102.0, 102.5, 101.0, 101.2, 1_000_000, _ts(2024, 1, 6), symbol),
    ]
