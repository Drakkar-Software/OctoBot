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

import octobot_trading.enums
import octobot_trading.personal_data as personal_data
import octobot_commons.symbols as commons_symbols


def get_trade_history(
        exchange_manager, quote=None, symbol=None, since=None, as_dict=False, include_cancelled=False
) -> list:
    return [
        trade.to_dict() if as_dict else trade
        for trade in exchange_manager.exchange_personal_data.trades_manager.get_trades()
        if _trade_filter(trade, quote, symbol, since, include_cancelled)
    ]


def get_completed_pnl_history(exchange_manager, quote=None, symbol=None, since=None) -> list:
    return exchange_manager.exchange_personal_data.trades_manager.get_completed_trades_pnl(
        get_trade_history(
            exchange_manager, quote=quote, symbol=symbol, since=since, as_dict=False, include_cancelled=False
        )
    )


def get_trade_pnl(
    exchange_manager, trade_id: typing.Optional[str] = None, order_id: typing.Optional[str] = None
) -> typing.Optional[personal_data.TradePnl]:
    return exchange_manager.exchange_personal_data.trades_manager.get_completed_trade_pnl(
        trade_id, order_id
    )


def _trade_filter(trade, quote=None, symbol=None, timestamp=None, include_cancelled=False) -> bool:
    if trade.status is octobot_trading.enums.OrderStatus.CANCELED and not include_cancelled:
        return False
    if timestamp is not None and not _is_trade_after_or_at(trade, timestamp):
        return False
    if quote is not None and commons_symbols.parse_symbol(trade.symbol).quote != quote:
        return False
    elif symbol is not None and trade.symbol != symbol:
        return False
    return True


def is_executed_trade(trade: dict) -> bool:
    try:
        return trade[octobot_trading.enums.ExchangeConstantsOrderColumns.STATUS.value] not in (
            octobot_trading.enums.OrderStatus.CANCELED.value,
            octobot_trading.enums.OrderStatus.EXPIRED.value,
        )
    except KeyError:
        return False


def is_trade_after_or_at(trade: dict, timestamp: float) -> bool:
    try:
        return trade[octobot_trading.enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] >= timestamp
    except KeyError:
        return False


def _is_trade_after_or_at(trade: personal_data.Trade, timestamp: float) -> bool:
    return trade.executed_time >= timestamp or trade.canceled_time >= timestamp


def get_total_paid_trading_fees(exchange_manager) -> dict:
    return exchange_manager.exchange_personal_data.trades_manager.get_total_paid_fees()


def get_trade_exchange_name(trade) -> str:
    return trade.exchange_manager.get_exchange_name()


def parse_trade_type(dict_trade) -> octobot_trading.enums.TraderOrderType:
    # can use parse_order_type since format is compatible
    return personal_data.parse_order_type(dict_trade)[1]


def trade_to_dict(trade) -> dict:
    return trade.to_dict()


def get_win_rate(exchange_manager) -> decimal.Decimal:
    return personal_data.compute_win_rate(exchange_manager)
