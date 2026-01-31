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

import octobot_commons.enums

import octobot_trading.enums
import octobot_trading.exchange_data as exchange_data
import octobot_trading.util as util


def get_symbol_data(exchange_manager, symbol, allow_creation=True) -> exchange_data.ExchangeSymbolData:
    return exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol, allow_creation=allow_creation)


def get_symbol_candles_manager(symbol_data, time_frame) -> exchange_data.CandlesManager:
    return symbol_data.symbol_candles[octobot_commons.enums.TimeFrames(time_frame)]


def get_symbol_historical_candles(symbol_data, time_frame, limit=-1) -> object:
    return get_symbol_candles_manager(symbol_data, time_frame).get_symbol_prices(limit)


async def create_preloaded_candles_manager(preloaded_candles):
    candles_manager = exchange_data.PreloadedCandlesManager()
    await candles_manager.initialize()
    candles_manager.replace_all_candles(preloaded_candles)
    return candles_manager


def are_symbol_candles_initialized(exchange_manager, symbol, time_frame) -> bool:
    try:
        return get_symbol_candles_manager(
            get_symbol_data(exchange_manager, symbol, allow_creation=False),
            time_frame
        ).candles_initialized
    except KeyError:
        return False


def get_candles_as_list(candles_arrays) -> list:
    return [
        exchange_data.get_candle_as_list(candles_arrays, index)
        for index in range(len(candles_arrays[0]))
    ]


def get_candle_as_list(candles_arrays, candle_index=0) -> list:
    return exchange_data.get_candle_as_list(candles_arrays, candle_index)


def has_symbol_klines(symbol_data, time_frame) -> bool:
    return octobot_commons.enums.TimeFrames(time_frame) in symbol_data.symbol_klines


def get_symbol_klines(symbol_data, time_frame) -> list:
    return symbol_data.symbol_klines[octobot_commons.enums.TimeFrames(time_frame)].kline


def get_symbol_candles_count(symbol_data, time_frame) -> int:
    return get_symbol_candles_manager(symbol_data, time_frame).get_symbol_candles_count()


def get_symbol_close_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_close_candles(symbol_data, time_frame, limit, include_in_construction)


def get_symbol_open_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_open_candles(symbol_data, time_frame, limit, include_in_construction)


def get_symbol_high_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_high_candles(symbol_data, time_frame, limit, include_in_construction)


def get_symbol_low_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_low_candles(symbol_data, time_frame, limit, include_in_construction)


def get_symbol_volume_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_volume_candles(symbol_data, time_frame, limit, include_in_construction)


def get_daily_base_and_quote_volume(symbol_data, reference_price: decimal.Decimal) -> (decimal.Decimal, decimal.Decimal):
    return get_daily_base_and_quote_volume_from_ticker(
        symbol_data.ticker_manager.ticker, reference_price=reference_price
    )


def get_daily_base_and_quote_volume_from_ticker(
    ticker: dict, reference_price: typing.Optional[decimal.Decimal] = None
) -> (decimal.Decimal, decimal.Decimal):
    base_volume = ticker.get(
        octobot_trading.enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value,
        "nan"
    )
    quote_volume = ticker.get(
        octobot_trading.enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value,
        "nan"
    )
    reference_price = reference_price or decimal.Decimal(str(
        ticker[octobot_trading.enums.ExchangeConstantsTickersColumns.CLOSE.value]
    ))
    return compute_base_and_quote_volume(base_volume, quote_volume, reference_price)

def compute_base_and_quote_volume(
    base_volume: decimal.Decimal,
    quote_volume: decimal.Decimal,
    reference_price: decimal.Decimal
) -> (decimal.Decimal, decimal.Decimal):
    if base_volume:
        base_volume = decimal.Decimal(str(base_volume))
        if not quote_volume or decimal.Decimal(str(quote_volume)).is_nan():
            # compute from the other if missing
            quote_volume = base_volume * reference_price
    if quote_volume:
        quote_volume = decimal.Decimal(str(quote_volume))
        if not base_volume or decimal.Decimal(str(base_volume)).is_nan():
            # compute from the other if missing
            base_volume = quote_volume / reference_price
    if not (base_volume and quote_volume) or (base_volume.is_nan() or quote_volume.is_nan()):
        raise ValueError(
            f"Missing volume {base_volume=} {quote_volume=}"
        )
    return base_volume, quote_volume


def get_symbol_time_candles(symbol_data, time_frame, limit=-1, include_in_construction=False):
    return exchange_data.get_symbol_time_candles(symbol_data, time_frame, limit, include_in_construction)


def create_new_candles_manager(candles=None, max_candles_count=None) -> exchange_data.CandlesManager:
    manager = exchange_data.CandlesManager(max_candles_count=max_candles_count)
    if candles is not None:
        manager.replace_all_candles(candles)
    return manager


def force_set_mark_price(exchange_manager, symbol, price):
    exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol).prices_manager.\
        set_mark_price(decimal.Decimal(str(price)), octobot_trading.enums.MarkPriceSources.EXCHANGE_MARK_PRICE.value)


def is_mark_price_initialized(exchange_manager, symbol: str) -> bool:
    return exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol).prices_manager.\
        valid_price_received_event.is_set()


def get_config_symbols(config, enabled_only) -> list:
    return util.get_symbols(config, enabled_only)
