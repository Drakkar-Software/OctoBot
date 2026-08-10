#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums


def resolve_portfolio_valuation_unit(exchange_manager) -> str:
    quote_currency = exchange_manager.exchange.get_option_value(
        trading_enums.ExchangeClientOptions.DEFAULT_QUOTE_CURRENCY
    )
    if quote_currency:
        return str(quote_currency)
    return commons_constants.DEFAULT_REFERENCE_MARKET
