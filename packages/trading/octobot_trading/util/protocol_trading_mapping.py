#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_protocol.models as protocol_models
import octobot_trading.enums as trading_enums


TRADING_TYPE_TO_EXCHANGE_TYPE: dict[protocol_models.TradingType, trading_enums.ExchangeTypes] = {
    protocol_models.TradingType.SPOT: trading_enums.ExchangeTypes.SPOT,
    protocol_models.TradingType.FUTURES: trading_enums.ExchangeTypes.FUTURE,
    protocol_models.TradingType.OPTIONS: trading_enums.ExchangeTypes.OPTION,
    protocol_models.TradingType.MARGIN: trading_enums.ExchangeTypes.MARGIN,
}

API_KEY_RIGHT_TO_ACCOUNT_PERMISSION: dict[
    trading_enums.APIKeyRights,
    protocol_models.AccountPermission,
] = {
    trading_enums.APIKeyRights.READING: protocol_models.AccountPermission.READ,
    trading_enums.APIKeyRights.SPOT_TRADING: protocol_models.AccountPermission.SPOT_TRADING,
    trading_enums.APIKeyRights.FUTURES_TRADING: protocol_models.AccountPermission.FUTURES_TRADING,
    trading_enums.APIKeyRights.WITHDRAWALS: protocol_models.AccountPermission.WITHDRAW,
}

OPTIMISTIC_API_KEY_RIGHTS_WHEN_PERMISSIONS_UNSUPPORTED: list[trading_enums.APIKeyRights] = [
    trading_enums.APIKeyRights.READING,
    trading_enums.APIKeyRights.SPOT_TRADING,
    trading_enums.APIKeyRights.FUTURES_TRADING,
]
