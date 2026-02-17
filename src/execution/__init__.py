"""
Paper execution: TradePlan → orders, single-writer state, risk limits.
Restart-safe. No live capital.
"""

from execution.models import Fill, Order, Position
from execution.paper_executor import PaperExecutor

__all__ = ["Fill", "Order", "PaperExecutor", "Position"]
