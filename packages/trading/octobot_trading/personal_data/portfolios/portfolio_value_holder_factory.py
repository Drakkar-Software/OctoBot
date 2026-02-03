#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_trading.personal_data.portfolios.portfolio_value_holder as portfolio_value_holder
import octobot_trading.personal_data.portfolios.holders.futures_portfolio_value_holder as futures_portfolio_value_holder
import octobot_trading.personal_data.portfolios.holders.option_portfolio_value_holder as option_portfolio_value_holder
import octobot_trading.personal_data.portfolios.holders.margin_portfolio_value_holder as margin_portfolio_value_holder
import octobot_trading.personal_data.portfolios.holders.spot_portfolio_value_holder as spot_portfolio_value_holder


def create_portfolio_value_holder(exchange_manager, portfolio_manager) -> portfolio_value_holder.PortfolioValueHolder:
    """
    Create a portfolio value holder from an exchange manager and a portfolio manager
    :param exchange_manager: the exchange manager related to the new portfolio value holder instance
    :param portfolio_manager: the portfolio manager related to the new portfolio value holder instance
    :return: the created portfolio value holder instance
    """
    if exchange_manager.is_future:
        return futures_portfolio_value_holder.FuturesPortfolioValueHolder(portfolio_manager)
    if exchange_manager.is_option:
        return option_portfolio_value_holder.OptionPortfolioValueHolder(portfolio_manager)
    if exchange_manager.is_margin:
        return margin_portfolio_value_holder.MarginPortfolioValueHolder(portfolio_manager)
    return spot_portfolio_value_holder.SpotPortfolioValueHolder(portfolio_manager)
