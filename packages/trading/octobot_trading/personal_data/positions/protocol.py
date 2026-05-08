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
import typing

import octobot_protocol.models as protocol_models
import octobot_trading.enums as enums

def to_protocol_position(
    position: dict[str, typing.Any]
) -> protocol_models.Position:
    return protocol_models.Position(
        id=position[enums.ExchangeConstantsPositionColumns.ID.value],
        symbol=position[enums.ExchangeConstantsPositionColumns.SYMBOL.value],
        side=position[enums.ExchangeConstantsPositionColumns.SIDE.value],
        quantity=float(position[enums.ExchangeConstantsPositionColumns.QUANTITY.value]),
        entry_price=float(position[enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value]),
        mark_price=float(position[enums.ExchangeConstantsPositionColumns.MARK_PRICE.value]),
        liquidation_price=float(position[enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value]),
        status=position[enums.ExchangeConstantsPositionColumns.STATUS.value],
    )
