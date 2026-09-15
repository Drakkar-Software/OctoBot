#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses

import octobot_protocol.models as protocol_models


@dataclasses.dataclass
class GlobalViewAccountRefreshResult:
    updated_account: protocol_models.Account
    changed_order_ids: set[str]
    open_orders: list[dict] | None = None
    trades: list[dict] | None = None
    positions: list[dict] | None = None
