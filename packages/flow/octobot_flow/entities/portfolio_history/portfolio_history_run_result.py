#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses


@dataclasses.dataclass
class PortfolioHistoryRunResult:
    account_id: str
    exchange_name: str
    trades_count: int = 0
    transactions_count: int = 0
    skipped: bool = False
    error: str | None = None
    is_simulated: bool = False
    trading_type: str = ""
    duration_seconds: float | None = None
    price_symbols_count: int = 0
    trade_symbols_count: int = 0
