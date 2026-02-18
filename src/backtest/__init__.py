"""
Backtest engine: replay bars, call vpa-core, simulate fills, risk, metrics.
"""

from backtest.runner import BacktestResult, BacktestTrade, run_backtest

__all__ = ["BacktestResult", "BacktestTrade", "run_backtest"]
