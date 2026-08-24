#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses

import octobot_protocol.models as protocol_models


@dataclasses.dataclass
class ExchangeAccountRefreshResult:
    assets: list[protocol_models.DetailedAssetsForTradingType]
    ticker_closes: dict[str, float]
    valuation_unit: str
    open_orders: list[dict]
    trades: list[dict]
    positions: list[dict]
    changed_order_ids: set[str]
