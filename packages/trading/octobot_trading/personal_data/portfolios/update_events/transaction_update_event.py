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

import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.update_events.portfolio_update_event as portfolio_update_event

if typing.TYPE_CHECKING:
    import octobot_trading.personal_data

class TransactionUpdateEvent(portfolio_update_event.PortfolioUpdateEvent):
    def __init__(
        self,
        initial_portfolio: "octobot_trading.personal_data.Portfolio",
        transaction: dict,
        are_added_funds: bool
    ):
        super().__init__()
        self.currency: str = transaction[enums.ExchangeConstantsTransactionColumns.CURRENCY.value]
        self.amount: decimal.Decimal = transaction[enums.ExchangeConstantsTransactionColumns.AMOUNT.value]
        self.initial_currency_holdings: decimal.Decimal = self._get_holdings(initial_portfolio)
        self.are_added_funds: bool = are_added_funds

    def is_resolved(
        self, updated_portfolio: "octobot_trading.personal_data.Portfolio"
    ) -> bool:
        updated_currency_holdings = self._get_holdings(updated_portfolio)
        # consider transaction successful if the portfolio available amount is more:less than 
        # the previous available amount minus the transaction amount - 5% (for withdrawal fees etc)
        if self.are_added_funds:
            return updated_currency_holdings >= (
                self.initial_currency_holdings + (self.amount * constants.NINETY_FIVE_PERCENT)
            )
        else:
            return updated_currency_holdings <= (
                self.initial_currency_holdings - (self.amount * constants.NINETY_FIVE_PERCENT)
            )

    def _get_holdings(
        self, portfolio: "octobot_trading.personal_data.Portfolio"
    ) -> decimal.Decimal:
        return portfolio.get_currency_portfolio(self.currency).get_total_holdings()

    def __repr__(self) -> str:
        return (
            f"{super().__repr__()}: {'+' if self.are_added_funds else '-'}{self.currency} "
            f"{self.amount} to {self.initial_currency_holdings}"
        )
