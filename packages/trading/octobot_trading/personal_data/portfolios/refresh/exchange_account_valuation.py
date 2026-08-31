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

import octobot_commons.constants as commons_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_util as exchange_util_module
import octobot_trading.personal_data.portfolios.portfolio_util as portfolio_util_module


def ticker_close_by_symbol_from_tickers(tickers: dict[str, dict]) -> dict[str, float]:
    close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
    ticker_close_by_symbol: dict[str, float] = {}
    for symbol, ticker in tickers.items():
        close_price = ticker.get(close_column)
        if close_price is not None:
            ticker_close_by_symbol[symbol] = float(close_price)
    return ticker_close_by_symbol


def refresh_portfolio_valuation(
    exchange_manager,
    valuation_unit: str,
    *,
    tickers: dict[str, dict] | None = None,
    valuation_symbols: list[str] | None = None,
) -> None:
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    if portfolio_manager is None:
        return
    if valuation_symbols is None:
        portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
        if portfolio_manager is None:
            portfolio_content = {}
        else:
            portfolio_content = portfolio_util_module.portfolio_to_float(
                portfolio_manager.portfolio.portfolio
            )
        valuation_symbols = valuation_symbols_from_portfolio(
            exchange_manager,
            portfolio_content,
            valuation_unit,
        )
    if tickers:
        close_column = trading_enums.ExchangeConstantsTickersColumns.CLOSE.value
        symbols_to_apply = valuation_symbols if valuation_symbols is not None else list(tickers)
        for symbol in symbols_to_apply:
            ticker = tickers.get(symbol)
            if not ticker:
                continue
            close_price = ticker.get(close_column)
            if close_price is None:
                continue
            mark_price = decimal.Decimal(str(close_price))
            portfolio_manager.portfolio_value_holder.value_converter.update_last_price(symbol, mark_price)
            if exchange_manager.symbol_exists(symbol):
                exchange_manager.get_symbol_data(symbol).handle_ticker_update(ticker)
    portfolio_manager.portfolio_value_holder._sync_portfolio_current_value_using_available_currencies_values(
        init_price_fetchers=False,
    )


def valuation_symbols_from_portfolio(
    exchange_manager,
    portfolio_content: dict,
    valuation_unit: str,
) -> list[str]:
    valuation_symbols: set[str] = set()
    bridge_quote_currencies = []
    if valuation_unit in commons_constants.USD_LIKE_COINS:
        bridge_quote_currencies = [
            quote_currency
            for quote_currency in commons_constants.USD_LIKE_COINS
            if quote_currency != valuation_unit
        ]
    for currency, symbol_balance in portfolio_content.items():
        total_holdings = float(symbol_balance.get(commons_constants.PORTFOLIO_TOTAL) or 0)
        if total_holdings == 0 or currency == valuation_unit:
            continue
        direct_symbol, _is_reversed_symbol = exchange_util_module.get_associated_symbol(
            exchange_manager,
            currency,
            valuation_unit,
        )
        if direct_symbol is not None:
            valuation_symbols.add(direct_symbol)
            continue
        for bridge_quote in bridge_quote_currencies:
            asset_symbol, _is_reversed_symbol = exchange_util_module.get_associated_symbol(
                exchange_manager,
                currency,
                bridge_quote,
            )
            if asset_symbol is None:
                continue
            valuation_symbols.add(asset_symbol)
            if bridge_quote != valuation_unit:
                bridge_symbol, _is_reversed_bridge_symbol = exchange_util_module.get_associated_symbol(
                    exchange_manager,
                    bridge_quote,
                    valuation_unit,
                )
                if bridge_symbol is not None:
                    valuation_symbols.add(bridge_symbol)
            break
    return list(valuation_symbols)
