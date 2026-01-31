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
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.constants
import octobot_trading.personal_data as personal_data


def get_portfolio(exchange_manager, as_decimal=True) -> dict:
    return format_portfolio(
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio,
        as_decimal
    )


def get_portfolio_historical_values(exchange_manager, currency, time_frame, from_timestamp=None, to_timestamp=None) \
        -> list:
    if exchange_manager.exchange_personal_data.portfolio_manager:
        return exchange_manager.exchange_personal_data.portfolio_manager.get_portfolio_historical_values(
            currency, time_frame, from_timestamp, to_timestamp
        )
    return []


def get_portfolio_reference_market(exchange_manager) -> str:
    return exchange_manager.exchange_personal_data.portfolio_manager.reference_market


def get_global_portfolio_currencies_values(exchange_managers: list) -> dict:
    currencies_values = {}
    for exchange in exchange_managers:
        this_currency_values = (
            exchange.exchange_personal_data.portfolio_manager
            .portfolio_value_holder.get_current_crypto_currencies_values()
        )
        for currency, value in this_currency_values.items():
            if currency not in currencies_values:
                currencies_values[currency] = value
    return currencies_values


def get_portfolio_currency(exchange_manager, currency) -> personal_data.Asset:
    return exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(currency)


def get_origin_portfolio(exchange_manager, as_decimal=True) -> dict:
    return format_portfolio(
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.origin_portfolio.portfolio,
        as_decimal
    )


def set_simulated_portfolio_initial_config(exchange_manager, portfolio_content):
    if exchange_manager.exchange_personal_data.portfolio_manager:
        exchange_manager.exchange_personal_data.portfolio_manager.set_forced_portfolio_initial_config(
            portfolio_content
        )


def format_portfolio(
    portfolio: dict[str, typing.Union[personal_data.Asset, dict[str, typing.Union[float, decimal.Decimal]]]],
    as_decimal: bool
) -> dict[str, typing.Union[personal_data.Asset, dict[str, typing.Union[float, decimal.Decimal]]]]:
    if not portfolio:
        return portfolio
    first_value = next(iter(portfolio.values()))
    if isinstance(first_value, personal_data.Asset):
        if as_decimal:
            return portfolio
        return personal_data.portfolio_to_float(portfolio)
    return personal_data.format_dict_portfolio_values(portfolio, as_decimal)


def parse_decimal_portfolio(portfolio, as_decimal) -> dict:
    return personal_data.parse_decimal_portfolio(portfolio, as_decimal=as_decimal)


async def refresh_real_trader_portfolio(exchange_manager) -> bool:
    return await exchange_channel.get_chan(octobot_trading.constants.BALANCE_CHANNEL, exchange_manager.id). \
        get_internal_producer(). \
        refresh_real_trader_portfolio(True)


def get_draw_down(exchange_manager) -> decimal.Decimal:
    return personal_data.get_draw_down(exchange_manager)


async def get_coefficient_of_determination(exchange_manager, use_high_instead_of_end_balance=True):
    return await personal_data.get_coefficient_of_determination(exchange_manager,
                                                                use_high_instead_of_end_balance)


def get_usd_like_symbol_from_symbols(currency: str, symbols) -> str:
    return personal_data.ValueConverter.get_usd_like_symbol_from_symbols(currency, symbols)


def get_usd_like_symbols_from_symbols(currency: str, symbols) -> list:
    return personal_data.ValueConverter.get_usd_like_symbols_from_symbols(currency, symbols)


def can_convert_symbol_to_usd_like(symbol: str) -> bool:
    return personal_data.ValueConverter.can_convert_symbol_to_usd_like(symbol)


def is_usd_like_coin(coin) -> bool:
    return commons_symbols.is_usd_like_coin(coin)


def resolve_sub_portfolios(
    master_portfolio: personal_data.SubPortfolioData,
    sub_portfolios: list[personal_data.SubPortfolioData],
    market_prices: dict[str, float],
) -> (personal_data.SubPortfolioData, list[personal_data.SubPortfolioData]):
    return personal_data.resolve_sub_portfolios(master_portfolio, sub_portfolios, market_prices)


async def get_portfolio_filled_orders_deltas(
    previous_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    filled_or_partially_filled_orders: list[personal_data.Order],
    unknown_filled_or_cancelled_orders: list[personal_data.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    randomize_secondary_checks: bool,
    timeout: typing.Optional[float],
) -> personal_data.ResolvedOrdersPortoflioDelta:
    return await personal_data.get_portfolio_filled_orders_deltas(
        previous_portfolio_content, updated_portfolio_content, 
        filled_or_partially_filled_orders, unknown_filled_or_cancelled_orders, 
        ignored_filled_quantity_per_order_exchange_id, randomize_secondary_checks, timeout
    )


def get_assets_delta_from_orders(
    orders: list[personal_data.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    compute_forecasted_fees: bool = True,
    force_fully_filled_orders: bool = False
) -> (dict[str, decimal.Decimal], dict[str, decimal.Decimal], dict[str, decimal.Decimal]):
    asset_deltas, expected_fee_related_deltas, possible_fee_related_deltas, _ = personal_data.get_assets_delta_from_orders(
        orders, ignored_filled_quantity_per_order_exchange_id, compute_forecasted_fees, 
        force_fully_filled_orders=force_fully_filled_orders
    )
    return asset_deltas, expected_fee_related_deltas, possible_fee_related_deltas

def get_accepted_missed_deltas(
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_sub_portfolio: dict[str, dict[str, decimal.Decimal]],
    missed_deltas: dict[str, dict[str, decimal.Decimal]]
) -> (dict[str, dict[str, decimal.Decimal]], dict[str, dict[str, decimal.Decimal]]):
    return personal_data.get_accepted_missed_deltas(
        updated_portfolio_content, updated_sub_portfolio, missed_deltas
    )


def get_master_checked_sub_portfolio_update(
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_sub_portfolio: dict[str, dict[str, decimal.Decimal]],
) -> dict[str, dict[str, decimal.Decimal]]:
    return personal_data.get_master_checked_sub_portfolio_update(updated_portfolio_content, updated_sub_portfolio)


def get_fees_only_asset_deltas_from_orders(orders: list[personal_data.Order]) -> dict[str, decimal.Decimal]:
    return personal_data.get_fees_only_asset_deltas_from_orders(orders)
