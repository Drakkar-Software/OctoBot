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

import octobot_commons.timestamp_util as timestamp_util
import octobot_protocol.models as protocol_models
import octobot_trading.enums as enums


def _protocol_fee_from_exchange_fee_dict(
    fee: dict | None,
) -> protocol_models.Fee | None:
    if not fee:
        return None
    fee_currency = fee.get(enums.FeePropertyColumns.CURRENCY.value)
    fee_cost = fee.get(enums.FeePropertyColumns.COST.value)
    if not fee_currency or fee_cost is None:
        return None
    return protocol_models.Fee(
        currency=str(fee_currency),
        amount=float(fee_cost),
    )


def to_protocol_trade(trade: dict[str, typing.Any]) -> protocol_models.Trade:
    order_columns = enums.ExchangeConstantsOrderColumns
    trade_id = trade.get(order_columns.EXCHANGE_TRADE_ID.value) or trade.get(order_columns.ID.value)
    local_id = trade.get(order_columns.ID.value) or trade_id
    return protocol_models.Trade(
        id=str(local_id),
        trade_id=str(trade_id),
        type=trade[order_columns.TYPE.value],
        symbol=trade[order_columns.SYMBOL.value],
        side=trade[order_columns.SIDE.value],
        quantity=float(trade[order_columns.AMOUNT.value]),
        price=float(trade[order_columns.PRICE.value]),
        fee=_protocol_fee_from_exchange_fee_dict(trade.get(order_columns.FEE.value)),
        status=trade[order_columns.STATUS.value],
        executed_at=timestamp_util.utc_datetime_from_timestamp(trade[order_columns.TIMESTAMP.value]),
    )


def exchange_columns_dict_from_protocol_trade(
    trade: protocol_models.Trade,
) -> dict[str, typing.Any]:
    order_columns = enums.ExchangeConstantsOrderColumns
    trade_dict = {
        order_columns.ID.value: trade.id,
        order_columns.EXCHANGE_TRADE_ID.value: trade.trade_id,
        order_columns.EXCHANGE_ID.value: trade.id,
        order_columns.SYMBOL.value: trade.symbol,
        order_columns.TYPE.value: trade.type.value,
        order_columns.SIDE.value: trade.side.value,
        order_columns.AMOUNT.value: trade.quantity,
        order_columns.PRICE.value: trade.price,
        order_columns.STATUS.value: trade.status.value,
        order_columns.TIMESTAMP.value: trade.executed_at.timestamp(),
    }
    if trade.fee is not None:
        trade_dict[order_columns.FEE.value] = {
            enums.FeePropertyColumns.CURRENCY.value: trade.fee.currency,
            enums.FeePropertyColumns.COST.value: trade.fee.amount,
        }
    return trade_dict
