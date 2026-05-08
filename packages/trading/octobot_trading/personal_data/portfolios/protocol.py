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

import octobot_protocol.models as protocol_models
import octobot_commons.constants as commons_constants


def to_protocol_assets(
    portfolio: dict[str, dict[str, typing.Union[float, decimal.Decimal]]]
) -> list[protocol_models.Asset]:
    return [
        protocol_models.Asset(
            symbol=symbol,
            available=float(symbol_balance[commons_constants.PORTFOLIO_AVAILABLE]),
            total=float(symbol_balance[commons_constants.PORTFOLIO_TOTAL]),
        )
        for symbol, symbol_balance in portfolio.items()
    ]
