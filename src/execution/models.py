"""Order, Fill, Position for paper execution. Aligned with DATA_MODEL.md."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    qty: int | float
    order_type: str  # "market" | "limit"
    timestamp: datetime
    id: str
    trade_plan_ref: str | None = None
    limit_price: float | None = None


@dataclass
class Fill:
    id: str
    order_id: str
    symbol: str
    side: str
    qty: int | float
    price: float
    timestamp: datetime
    slippage_bps: float | None = None


@dataclass
class Position:
    symbol: str
    side: str  # "long" | "short"
    qty: int | float
    avg_price: float
    updated_at: datetime
