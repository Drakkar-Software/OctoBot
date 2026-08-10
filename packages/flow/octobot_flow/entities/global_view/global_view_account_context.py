#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import dataclasses

import octobot_protocol.models as protocol_models
import octobot_trading.exchanges.util.exchange_data as exchange_data_module


@dataclasses.dataclass
class GlobalViewAccountContext:
    account: protocol_models.Account
    exchange_account: protocol_models.ExchangeAccount
    exchange_config: protocol_models.ExchangeConfig
    trading_type: protocol_models.TradingType
    auth_details: exchange_data_module.ExchangeAuthDetails
