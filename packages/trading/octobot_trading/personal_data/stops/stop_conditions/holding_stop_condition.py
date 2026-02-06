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
import dataclasses
import decimal
import typing

import octobot_commons.dataclasses as commons_dataclasses
import octobot_trading.personal_data.stops.stop_conditions.stop_condition_mixin as stop_condition_mixin

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges as trading_exchanges


@dataclasses.dataclass
class HoldingStopCondition(commons_dataclasses.FlexibleDataclass, stop_condition_mixin.StopConditionMixin):
    asset_name: str
    amount: decimal.Decimal
    stop_on_inferior: bool

    _last_match_reason: str = ""

    def __post_init__(self):
        self.amount = decimal.Decimal(str(self.amount))

    def is_met(self, exchange_manager: "trading_exchanges.ExchangeManager") -> bool:
        holdings = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(self.asset_name)
        if self.stop_on_inferior:
            if holdings.total <= self.amount:
                self._last_match_reason = self._get_reason(holdings)
                return True
        else:
            if holdings.total >= self.amount:
                self._last_match_reason = self._get_reason(holdings)
                return True
        return False

    def _get_reason(self, holdings) -> str:
        return (
            f"Current {self.asset_name} holdings of {float(holdings.total)} are "
            f"{'lower' if self.stop_on_inferior else 'higher'} than the {float(self.amount)} threshold."
        )

    def get_match_reason(self) -> str:
        return self._last_match_reason
