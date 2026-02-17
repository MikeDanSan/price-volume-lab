"""Tests for Alpaca bar fetcher (mocked SDK). No network calls."""

import sys
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_alpaca_modules():
    """Mock the alpaca SDK modules so tests run without alpaca-py installed."""
    alpaca = ModuleType("alpaca")
    alpaca_data = ModuleType("alpaca.data")
    alpaca_data_historical = ModuleType("alpaca.data.historical")
    alpaca_data_requests = ModuleType("alpaca.data.requests")
    alpaca_data_timeframe = ModuleType("alpaca.data.timeframe")

    mock_client_cls = MagicMock()
    alpaca_data_historical.StockHistoricalDataClient = mock_client_cls
    alpaca_data_requests.StockBarsRequest = MagicMock()

    class FakeTimeFrameUnit:
        Min = "Min"
        Hour = "Hour"
        Day = "Day"

    alpaca_data_timeframe.TimeFrameUnit = FakeTimeFrameUnit
    alpaca_data_timeframe.TimeFrame = MagicMock()

    mods = {
        "alpaca": alpaca,
        "alpaca.data": alpaca_data,
        "alpaca.data.historical": alpaca_data_historical,
        "alpaca.data.requests": alpaca_data_requests,
        "alpaca.data.timeframe": alpaca_data_timeframe,
    }
    with patch.dict(sys.modules, mods):
        # Clear any cached import of the fetcher module
        sys.modules.pop("data.alpaca_fetcher", None)
        yield


def test_alpaca_fetcher_maps_bars() -> None:
    """Verify AlpacaBarFetcher converts Alpaca bars to vpa_core.contracts.Bar."""
    from data.alpaca_fetcher import AlpacaBarFetcher

    mock_bar = MagicMock()
    mock_bar.open = 100.0
    mock_bar.high = 101.0
    mock_bar.low = 99.0
    mock_bar.close = 100.5
    mock_bar.volume = 1_000_000
    mock_bar.timestamp = datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)

    mock_response = MagicMock()
    mock_response.data = {"SPY": [mock_bar]}
    mock_response.next_page_token = None

    fetcher = AlpacaBarFetcher("key", "secret")
    fetcher._client = MagicMock()
    fetcher._client.get_stock_bars.return_value = mock_response

    result = fetcher.fetch("SPY", "15m", start=datetime(2024, 1, 1, tzinfo=timezone.utc))

    assert len(result.bars) == 1
    bar = result.bars[0]
    assert bar.symbol == "SPY"
    assert bar.open == 100.0
    assert bar.high == 101.0
    assert bar.close == 100.5
    assert bar.volume == 1_000_000
    assert bar.timestamp.tzinfo is not None
    assert result.next_cursor is None


def test_alpaca_fetcher_empty_response() -> None:
    """No bars returned."""
    from data.alpaca_fetcher import AlpacaBarFetcher

    mock_response = MagicMock()
    mock_response.data = {"SPY": []}
    mock_response.next_page_token = None

    fetcher = AlpacaBarFetcher("key", "secret")
    fetcher._client = MagicMock()
    fetcher._client.get_stock_bars.return_value = mock_response

    result = fetcher.fetch("SPY", "15m")
    assert len(result.bars) == 0


def test_alpaca_fetcher_requires_keys() -> None:
    """Must raise if keys are empty."""
    from data.alpaca_fetcher import AlpacaBarFetcher

    with pytest.raises(ValueError, match="API key"):
        AlpacaBarFetcher("", "")
