#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
"""Exchange price mock helpers for simulator workflow functional tests."""

from __future__ import annotations

import time
import typing

import octobot_commons.enums as common_enums_module
import octobot_trading.enums as trading_enums_module
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_module


def _market_details_for_close_price(
    *,
    symbol: str,
    time_frame: str,
    limit: int,
    close_price: float,
):
    time_frame_seconds = common_enums_module.TimeFramesMinutes[
        common_enums_module.TimeFrames(time_frame)
    ] * 60
    candle_count = max(int(limit or 1), 1)
    local_time = time.time()
    current_candle_open_time = local_time - (local_time % time_frame_seconds)
    first_candle_open_time = current_candle_open_time - (candle_count - 1) * time_frame_seconds
    times = [
        float(first_candle_open_time + step_index * time_frame_seconds)
        for step_index in range(candle_count)
    ]
    closes = [close_price] * candle_count
    ohlc = [close_price] * candle_count
    return exchange_data_module.MarketDetails(
        symbol=symbol,
        time_frame=time_frame,
        close=closes,
        open=ohlc,
        high=ohlc,
        low=ohlc,
        volume=[0.0] * candle_count,
        time=times,
    )


def fetch_ohlcv_side_effect_for_close_price(
    get_close_price: typing.Callable[[], typing.Union[int, float]],
):
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        return _market_details_for_close_price(
            symbol=symbol,
            time_frame=time_frame,
            limit=limit,
            close_price=float(get_close_price()),
        )

    return patched_fetch_ohlcv


def fetch_ohlcv_side_effect_for_close_prices(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
):
    async def patched_fetch_ohlcv(
        symbol: str,
        time_frame: str,
        limit: int,
        _tickers: dict[str, dict[str, typing.Any]],
    ):
        return _market_details_for_close_price(
            symbol=symbol,
            time_frame=time_frame,
            limit=limit,
            close_price=float(get_close_price_for_symbol(symbol)),
        )

    return patched_fetch_ohlcv


def tickers_repository_fetch_tickers_btc_usdc_close_override(
    get_btc_usdc_close: typing.Callable[[], typing.Union[int, float]],
    *,
    btc_usdc_symbol: str = "BTC/USDC",
):
    orig_get_all = exchanges_test_tools_module.get_all_currencies_price_ticker
    orig_get_one = exchanges_test_tools_module.get_price_ticker
    close_col = trading_enums_module.ExchangeConstantsTickersColumns.CLOSE.value

    async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
        tickers = await orig_get_all(exchange_manager, **kwargs)
        close_value = get_btc_usdc_close()
        if btc_usdc_symbol in tickers:
            tickers[btc_usdc_symbol] = {**tickers[btc_usdc_symbol], close_col: close_value}
        else:
            tickers[btc_usdc_symbol] = {close_col: close_value}
        return tickers

    async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
        if symbol == btc_usdc_symbol:
            return {close_col: get_btc_usdc_close()}
        return await orig_get_one(exchange_manager, symbol, **kwargs)

    async def patched_fetch_tickers(self, symbols):
        if symbols == []:
            return {}
        if isinstance(symbols, list) and len(symbols) == 1:
            return {
                symbols[0]: await patched_get_price_ticker(self.exchange_manager, symbols[0])
            }
        return await patched_get_all_currencies_price_ticker(self.exchange_manager, symbols=None)

    return patched_fetch_tickers


def tickers_repository_fetch_tickers_close_override(
    get_close_price_for_symbol: typing.Callable[[str], typing.Union[int, float]],
    *,
    traded_symbols: tuple[str, ...],
):
    orig_get_all = exchanges_test_tools_module.get_all_currencies_price_ticker
    orig_get_one = exchanges_test_tools_module.get_price_ticker
    close_col = trading_enums_module.ExchangeConstantsTickersColumns.CLOSE.value

    async def patched_get_all_currencies_price_ticker(exchange_manager, **kwargs):
        tickers = await orig_get_all(exchange_manager, **kwargs)
        for symbol in traded_symbols:
            close_value = get_close_price_for_symbol(symbol)
            if symbol in tickers:
                tickers[symbol] = {**tickers[symbol], close_col: close_value}
            else:
                tickers[symbol] = {close_col: close_value}
        return tickers

    async def patched_get_price_ticker(exchange_manager, symbol: str, **kwargs):
        if symbol in traded_symbols:
            return {close_col: get_close_price_for_symbol(symbol)}
        return await orig_get_one(exchange_manager, symbol, **kwargs)

    async def patched_fetch_tickers(self, symbols):
        if symbols == []:
            return {}
        if isinstance(symbols, list) and len(symbols) == 1:
            return {
                symbols[0]: await patched_get_price_ticker(self.exchange_manager, symbols[0])
            }
        return await patched_get_all_currencies_price_ticker(self.exchange_manager, symbols=None)

    return patched_fetch_tickers
