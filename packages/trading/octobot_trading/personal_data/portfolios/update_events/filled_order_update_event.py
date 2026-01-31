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
import decimal
import typing

import octobot_commons.symbols as commons_symbols
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.update_events.portfolio_update_event as portfolio_update_event

if typing.TYPE_CHECKING:
    import octobot_trading.personal_data

class FilledOrderUpdateEvent(portfolio_update_event.PortfolioUpdateEvent):
    def __init__(
        self,
        order: "octobot_trading.personal_data.Order"
    ):
        super().__init__()
        if order.trader.exchange_manager.is_future:
            raise NotImplementedError("Futures are not supported yet")
        # don't save the full order to avoid memory issues
        self.origin_quantity: decimal.Decimal = order.origin_quantity
        self.origin_price: decimal.Decimal = order.origin_price
        self.side: enums.TradeOrderSide = order.side
        self.symbol: str = order.symbol

    def is_resolved(
        self, updated_portfolio: "octobot_trading.personal_data.Portfolio"
    ) -> bool:
        checked_amount = (
            self.origin_quantity if self.side == enums.TradeOrderSide.BUY 
            else (self.origin_quantity * self.origin_price)
        )
        available_amount = self._get_checked_asset_available_amount(updated_portfolio)
        # if available_amount > checked_amount, then the order fill is most likely taken into account in portfolio
        return available_amount > (checked_amount * constants.NINETY_FIVE_PERCENT)

    def _get_checked_asset_available_amount(
        self, portfolio: "octobot_trading.personal_data.Portfolio"
    ) -> decimal.Decimal:
        base, quote = commons_symbols.parse_symbol(self.symbol).base_and_quote()
        checked_asset = base if self.side == enums.TradeOrderSide.BUY else quote
        return portfolio.get_currency_portfolio(checked_asset).available

    def __repr__(self) -> str:
        return (
            f"{super().__repr__()}: {self.side.value} {self.origin_quantity} {self.symbol} @ {self.origin_price}"
        )
