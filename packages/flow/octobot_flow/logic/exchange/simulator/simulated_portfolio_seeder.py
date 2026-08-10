#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_trading.api as trading_api


def seed_simulated_portfolio(exchange_manager, account: protocol_models.Account) -> None:
    portfolio_content: dict[str, dict[str, float]] = {}
    if account.assets:
        for assets_for_trading_type in account.assets:
            for detailed_asset in assets_for_trading_type.assets:
                portfolio_content[detailed_asset.symbol] = {
                    commons_constants.PORTFOLIO_AVAILABLE: float(detailed_asset.available),
                    commons_constants.PORTFOLIO_TOTAL: float(detailed_asset.total),
                }
    if portfolio_content:
        trading_api.set_simulated_portfolio_initial_config(exchange_manager, portfolio_content)
