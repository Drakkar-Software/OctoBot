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
import copy
import decimal
import typing
import itertools
import math
import asyncio
import time
import threading
import random

import octobot_trading.personal_data.portfolios.asset as asset
import octobot_trading.personal_data.portfolios.assets
import octobot_trading.personal_data.orders.order as order_import
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.personal_data.portfolios.sub_portfolio_data as sub_portfolio_data
import octobot_trading.personal_data.portfolios.resolved_orders_portfolio_delta as resolved_orders_portfolio_delta
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.symbols as symbol_util
import octobot_commons.list_util as list_util

import numpy as numpy


def parse_decimal_portfolio(portfolio, as_decimal=True):
    decimal_portfolio = {}
    for symbol, symbol_balance in portfolio.items():
        if isinstance(symbol_balance, dict):
            decimal_portfolio[symbol] = {}
            portfolio_to_fill = decimal_portfolio[symbol]
            for balance_type, balance_val in symbol_balance.items():
                if isinstance(balance_val, (int, float, decimal.Decimal)):
                    portfolio_to_fill[balance_type] = decimal.Decimal(str(balance_val)) \
                        if as_decimal else float(balance_val)
                    # convert negative values to zero, as this can happen 
                    # (ex: bingx: 'SSV': {'free': -7e-07, 'total': -7e-07})
                    if as_decimal and balance_val < constants.ZERO:
                        portfolio_to_fill[balance_type] = constants.ZERO
                    elif not as_decimal and balance_val < 0:
                        portfolio_to_fill[balance_type] = 0
    return decimal_portfolio


def parse_decimal_config_portfolio(portfolio):
    return {
        symbol: {
            k: decimal.Decimal(str(v))
            for k, v in symbol_balance.items()
        } if isinstance(symbol_balance, dict) else decimal.Decimal(str(symbol_balance))
        for symbol, symbol_balance in portfolio.items()
    }


def filter_empty_values(portfolio):
    return {
        symbol: value
        for symbol, value in portfolio.items()
        if value[commons_constants.PORTFOLIO_TOTAL] > 0
    }


def portfolio_to_float(portfolio, use_wallet_balance_on_futures=False):
    float_portfolio = {}
    for symbol, symbol_balance in portfolio.items():
        if (
            isinstance(symbol_balance, octobot_trading.personal_data.portfolios.assets.FutureAsset)
            and use_wallet_balance_on_futures
        ):
            float_portfolio[symbol] = {
                commons_constants.PORTFOLIO_AVAILABLE: float(symbol_balance.available),
                commons_constants.PORTFOLIO_TOTAL: float(symbol_balance.wallet_balance)
            }
        elif isinstance(symbol_balance, asset.Asset):
            float_portfolio[symbol] = {
                commons_constants.PORTFOLIO_AVAILABLE: float(symbol_balance.available),
                commons_constants.PORTFOLIO_TOTAL: float(symbol_balance.total)
            }
    return float_portfolio


def format_dict_portfolio_values(
    portfolio: dict[str, dict[str, typing.Union[float, decimal.Decimal]]], as_decimal: bool
) -> dict[str, dict[str, typing.Union[float, decimal.Decimal]]]:
    return {
        asset_name: {
            key: decimal.Decimal(str(val)) if as_decimal else float(val)
            for key, val in asset_content.items()
        }
        for asset_name, asset_content in portfolio.items()
    }


def get_draw_down(exchange_manager):
    """
    Draw down is the lowest portfolio value in % ever reached during a run
    :return: the Draw down value
    """
    draw_down = constants.ZERO
    if exchange_manager.is_future:
        try:
            value_currency = exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            draw_down_pair = exchange_manager.exchange_config.traded_symbol_pairs[0]
            if exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
                draw_down_pair,
                enums.PositionSide.BOTH
            ).symbol_contract.is_inverse_contract():
                value_currency = symbol_util.parse_symbol(draw_down_pair).base
            if exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.origin_portfolio \
                    is None:
                return constants.ZERO
            origin_value = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder \
                .origin_portfolio.portfolio[value_currency].total
            portfolio_history = [origin_value]
            for transaction in exchange_manager.exchange_personal_data.transactions_manager.transactions.values():
                current_pnl = transaction.quantity if hasattr(transaction, "quantity") else transaction.realised_pnl
                portfolio_history.append(portfolio_history[-1] + current_pnl)

                current_draw_down = constants.ONE_HUNDRED - \
                    (portfolio_history[-1] / (max(portfolio_history) / constants.ONE_HUNDRED))

                draw_down = current_draw_down if current_draw_down > draw_down else draw_down
        except Exception as e:
            commons_logging.get_logger(__name__).warning(f"Error when computing draw down: {e}")
    return draw_down


async def get_coefficient_of_determination_data(transactions, start_balance,
                                                use_high_instead_of_end_balance=True,
                                                x_as_trade_count=True):
    if transactions:
        # get realized portfolio history

        pnl_history = [start_balance]
        pnl_history_times = []
        for transaction in transactions:
            current_pnl = None
            if hasattr(transaction, "quantity"):
                current_pnl = float(transaction.quantity)
                pnl_history_times.append(transaction.creation_time)
            elif hasattr(transaction, 'realised_pnl'):
                current_pnl = float(transaction.realised_pnl)
                pnl_history_times.append(transaction.creation_time)
            elif isinstance(transaction, dict):
                if transaction["quantity"]:
                    current_pnl = transaction["quantity"]
                    pnl_history_times.append(transaction["x"])
                elif transaction['realised_pnl']:
                    current_pnl = transaction['realised_pnl']
                    pnl_history_times.append(transaction["x"])

            if current_pnl is not None:
                pnl_history.append(pnl_history[-1] + current_pnl)

        if pnl_history_times:

            pnl_history_for_every_candle = None
            # either use trade to trade basis or candle to candle basis
            if x_as_trade_count is True:
                start_time = pnl_history_times[0]
                pnl_history_times.insert(0, start_time)
                end_time = pnl_history_times[-1]
                data_length = len(pnl_history)

            else:  # calculate pnl history for every candle
                raise NotImplementedError("x_as_trade_count=False is not implemented")
            # calculate best case data (exponential growth)
            end_balance = pnl_history[-1]

            if start_balance > end_balance:
                # if we end up with a negative balance we can't compute this
                return None, None, None, None, None

            if use_high_instead_of_end_balance:
                end_value = max(pnl_history)
            else:  # use the end balance
                end_value = end_balance

            def get_ideal_value(linear_growth, adj1, adj2):
                return ((linear_growth + adj1) ** pw) * adj2

            x = [start_time, end_time]
            y = [start_balance, end_value]

            pw = 15
            A = numpy.exp(numpy.log(y[0] / y[1]) / pw)
            a = (x[0] - x[1] * A) / (A - 1)
            b = y[0] / (x[0] + a) ** pw

            linear_growth = numpy.linspace(start_time, end_time, data_length)
            best_case = get_ideal_value(linear_growth, a, b)
            pnl_data = pnl_history_for_every_candle or pnl_history
            return list(best_case), pnl_data, start_balance, end_balance, pnl_history_times
    return None, None, None, None, None


async def get_coefficient_of_determination(exchange_manager, use_high_instead_of_end_balance=True):
    """
    Calculates proximity to the best case growth for the current run (best growth being associated to an exponential
    curve). The closer the actual result, the higher the coefficient_of_determination (R squared) will be.
    Return 0 if we end up with less money that we had to begin with
    :param use_high_instead_of_end_balance: best case exponential growth based on end balance or highest balance
    """
    coefficient_of_determination = 0
    if exchange_manager.exchange_personal_data.portfolio_manager is None or \
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.origin_portfolio is None:
        return 0
    # get data the data necessary to compute the coefficient_of_determination
    origin_portfolio = portfolio_to_float(
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.origin_portfolio.portfolio
    )
    start_balance = origin_portfolio[
        exchange_manager.exchange_personal_data.portfolio_manager.reference_market][commons_constants.PORTFOLIO_TOTAL]

    best_case, pnl_data, start_balance, _, _ \
        = await get_coefficient_of_determination_data(transactions=exchange_manager.exchange_personal_data.
                                                      transactions_manager.transactions.values(),
                                                      start_balance=start_balance,
                                                      use_high_instead_of_end_balance=use_high_instead_of_end_balance)

    if pnl_data:
        # calculate r²
        corr_matrix = numpy.corrcoef(best_case, pnl_data)
        corr = corr_matrix[0, 1]
        coefficient_of_determination = corr ** 2

    return round(coefficient_of_determination, 3)


def get_asset_price_from_converter_or_tickers(
    exchange_manager, to_convert_asset: str, target_asset: str, symbol: str, tickers: dict
):
    # 1. try with converter
    try:
        price = exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.value_converter.evaluate_value(
                to_convert_asset, constants.ONE, raise_error=True,
                target_currency=target_asset, init_price_fetchers=False
            )
        if price == constants.ZERO:
            raise errors.MissingPriceDataError
    except errors.MissingPriceDataError:
        # 2. try with tickers
        try:
            price = decimal.Decimal(str(
                tickers[symbol][enums.ExchangeConstantsTickersColumns.CLOSE.value]
                or tickers[symbol][enums.ExchangeConstantsTickersColumns.PREVIOUS_CLOSE.value]
            ))
        except KeyError:
            price = None
    return price


def resolve_sub_portfolios(
    master_portfolio: sub_portfolio_data.SubPortfolioData,
    sub_portfolios: list[sub_portfolio_data.SubPortfolioData],
    market_prices: dict[str, float],
) -> (sub_portfolio_data.SubPortfolioData, list[sub_portfolio_data.SubPortfolioData]):
    resolved_portfolios = []
    remaining_master_portfolio = copy.deepcopy(master_portfolio)
    for sub_portfolio in sorted(sub_portfolios, key=lambda x: x.priority_key):
        resolved_portfolio = _resolve_sub_portfolio(remaining_master_portfolio, sub_portfolio, market_prices)
        resolved_portfolios.append(resolved_portfolio)
    return remaining_master_portfolio, resolved_portfolios


def _resolve_sub_portfolio(
    remaining_master_portfolio: sub_portfolio_data.SubPortfolioData,
    sub_portfolio: sub_portfolio_data.SubPortfolioData,
    market_prices: dict[str, float],
) -> sub_portfolio_data.SubPortfolioData:
    resolved_content = {}
    funds_deltas = {}
    missing_funds = {}
    missing_amount_by_asset = {}
    forecasted_sub_portfolio_content = sub_portfolio.get_content_after_deltas()
    for asset_name, holdings in forecasted_sub_portfolio_content.items():
        missing_amount_in_asset = _resolve_sub_portfolio_asset(
            asset_name, holdings, remaining_master_portfolio, resolved_content,
            sub_portfolio.locked_funds_by_asset.get(asset_name, constants.ZERO), sub_portfolio.forbidden_filling_assets
        )
        if missing_amount_in_asset > constants.ZERO:
            missing_amount_by_asset[asset_name] = missing_amount_in_asset
    # now that assets have been allocated, try to compensate missing assets
    for asset_name, missing_amount_in_asset in missing_amount_by_asset.items():
        _fill_missing_assets_from_allowed_filling_assets(
            asset_name, sub_portfolio.allowed_filling_assets, market_prices,
            remaining_master_portfolio, missing_amount_in_asset,
            resolved_content, funds_deltas, missing_funds
        )

    return sub_portfolio_data.SubPortfolioData(
        sub_portfolio.bot_id,
        sub_portfolio.portfolio_id,
        sub_portfolio.priority_key,
        resolved_content,
        sub_portfolio.unit,
        funds_deltas=funds_deltas,
        missing_funds=missing_funds,
        locked_funds_by_asset=sub_portfolio.locked_funds_by_asset,
    )


def _resolve_sub_portfolio_asset(
    asset_name: str,
    holdings: dict[str, decimal.Decimal],
    remaining_master_portfolio: sub_portfolio_data.SubPortfolioData,
    resolved_content: dict[str, dict[str, decimal.Decimal]],
    locked_funds: decimal.Decimal,
    forbidden_filling_assets: list[str]
) -> decimal.Decimal:
    required_total_amount = holdings[commons_constants.PORTFOLIO_TOTAL]
    required_available_amount = holdings[commons_constants.PORTFOLIO_TOTAL] - locked_funds
    missing_amount_in_asset = constants.ZERO
    if asset_name in remaining_master_portfolio.content and asset_name not in forbidden_filling_assets:
        remaining_master_holding = remaining_master_portfolio.content[asset_name]
        # available = total - locked_funds
        remaining_total = remaining_master_holding[commons_constants.PORTFOLIO_TOTAL]
        remaining_available = remaining_master_holding[commons_constants.PORTFOLIO_AVAILABLE]
        allowed_missing_ratio_multiplier = constants.ONE - constants.SUB_PORTFOLIO_ALLOWED_MISSING_RATIO
        if remaining_total < locked_funds * allowed_missing_ratio_multiplier:
            # should never happen, log it in case it does
            commons_logging.get_logger(__name__).error(
                f"Unexpected missing locked {asset_name} funds in total portfolio {remaining_total=} {locked_funds=}"
            )
        # As orders are still open, their funds must be locked. Therefore, only consider available funds
        if remaining_available >= required_available_amount * allowed_missing_ratio_multiplier:
            if remaining_total < required_total_amount * allowed_missing_ratio_multiplier:
                # should never happen, log it in case it does
                commons_logging.get_logger(__name__).error(
                    f"Unexpected missing total {asset_name} value in portfolio: ensure order funds really locked"
                )
            sub_portfolio_total_amount = min(remaining_total, required_total_amount)
            # Do not use remaining_available or remaining_available here to avoid side effects due to locked fees
            # on some exchanges and not on others. Only compute from total holdings.
            # ex: coinbase locks 101 USDC to buy for 100 USDC + 1 USDC fee,
            # binance will just lock 100 and given less of the bought asset
            sub_portfolio_available_amount = sub_portfolio_total_amount - locked_funds
            # assets are available in master portfolio: reduce it from master
            if asset_name in resolved_content:
                resolved_content[asset_name][commons_constants.PORTFOLIO_TOTAL] += sub_portfolio_total_amount
                resolved_content[asset_name][commons_constants.PORTFOLIO_AVAILABLE] += sub_portfolio_available_amount
            else:
                resolved_content[asset_name] = {
                    commons_constants.PORTFOLIO_TOTAL: sub_portfolio_total_amount,
                    commons_constants.PORTFOLIO_AVAILABLE: sub_portfolio_available_amount,
                }
            remaining_master_portfolio.content[asset_name][commons_constants.PORTFOLIO_TOTAL] -= sub_portfolio_total_amount
            # don't make remaining available negative
            removed_portfolio_available_amount = min(remaining_available, sub_portfolio_available_amount)
            remaining_master_portfolio.content[asset_name][commons_constants.PORTFOLIO_AVAILABLE] -= removed_portfolio_available_amount
        else:
            # As orders are still open, their funds must be locked. Therefore, only consider available funds
            # Not enough assets in master portfolio
            usable_total = min(remaining_total, remaining_available + locked_funds)
            if asset_name in resolved_content:
                resolved_content[asset_name][commons_constants.PORTFOLIO_TOTAL] += usable_total
                resolved_content[asset_name][commons_constants.PORTFOLIO_AVAILABLE] += remaining_available
            else:
                resolved_content[asset_name] = {
                    commons_constants.PORTFOLIO_TOTAL: usable_total,
                    commons_constants.PORTFOLIO_AVAILABLE: remaining_available,
                }
            missing_amount_in_asset = abs(remaining_available - required_available_amount)
            remaining_master_portfolio.content[asset_name][commons_constants.PORTFOLIO_TOTAL] -= usable_total
            remaining_master_portfolio.content[asset_name][commons_constants.PORTFOLIO_AVAILABLE] -= remaining_available
    else:
        if locked_funds > constants.ZERO:
            # should never happen, log it in case it does
            commons_logging.get_logger(__name__).error(
                f"Unexpected missing {asset_name} value in portfolio but {locked_funds=}"
            )
        resolved_content[asset_name] = {
            commons_constants.PORTFOLIO_TOTAL: constants.ZERO,
            commons_constants.PORTFOLIO_AVAILABLE: constants.ZERO,
        }
        # asset not in master portfolio (anymore):
        missing_amount_in_asset = required_available_amount
    return missing_amount_in_asset


def _fill_missing_assets_from_allowed_filling_assets(
    asset_name, allowed_filling_assets, market_prices,
    remaining_master_portfolio, missing_amount_in_asset, resolved_content, funds_deltas, missing_funds
):
    # missing funds: try to get it from allowed assets
    for filling_asset, price in _iterate_filling_assets(
        asset_name, allowed_filling_assets, market_prices
    ):
        if filling_asset in remaining_master_portfolio.content and price != constants.ZERO:
            # use available funds only here to avoid taking funds locked in orders
            available_funds_in_filling_asset = remaining_master_portfolio.content[filling_asset][
                commons_constants.PORTFOLIO_AVAILABLE
            ]
            ideal_funds_to_add_in_filling_asset = missing_amount_in_asset * price
            if available_funds_in_filling_asset >= ideal_funds_to_add_in_filling_asset:
                # use a part of available filling asset to compensate missing amount in sub portfolio
                funds_to_add_in_filling_asset = ideal_funds_to_add_in_filling_asset
                taken_filling_asset = ideal_funds_to_add_in_filling_asset
                missing_amount_in_asset = constants.ZERO
            else:
                # use all available filling asset to compensate missing amount in sub portfolio
                funds_to_add_in_filling_asset = available_funds_in_filling_asset
                taken_filling_asset = available_funds_in_filling_asset
                missing_amount_in_asset = missing_amount_in_asset - (funds_to_add_in_filling_asset / price)
            if filling_asset in resolved_content:
                resolved_content[filling_asset][commons_constants.PORTFOLIO_TOTAL] += (
                    funds_to_add_in_filling_asset
                )
                resolved_content[filling_asset][commons_constants.PORTFOLIO_AVAILABLE] += (
                    funds_to_add_in_filling_asset
                )
            else:
                resolved_content[filling_asset] = {
                    commons_constants.PORTFOLIO_TOTAL: funds_to_add_in_filling_asset,
                    commons_constants.PORTFOLIO_AVAILABLE: funds_to_add_in_filling_asset,
                }
            # register filling assets in funds_deltas
            if filling_asset in funds_deltas:
                funds_deltas[filling_asset][commons_constants.PORTFOLIO_TOTAL] += funds_to_add_in_filling_asset
                funds_deltas[filling_asset][commons_constants.PORTFOLIO_AVAILABLE] += funds_to_add_in_filling_asset
            elif funds_to_add_in_filling_asset != constants.ZERO:
                # only add delta when delta is not 0
                funds_deltas[filling_asset] = {
                    commons_constants.PORTFOLIO_TOTAL: funds_to_add_in_filling_asset,
                    commons_constants.PORTFOLIO_AVAILABLE: funds_to_add_in_filling_asset
                }
            remaining_master_portfolio.content[filling_asset][commons_constants.PORTFOLIO_AVAILABLE] -= (
                taken_filling_asset
            )
            remaining_master_portfolio.content[filling_asset][commons_constants.PORTFOLIO_TOTAL] -= (
                taken_filling_asset
            )
        if missing_amount_in_asset == constants.ZERO:
            return constants.ZERO
    if missing_amount_in_asset > constants.ZERO:
        # can't compensate for missing funds
        if asset_name in missing_funds:
            missing_funds[asset_name] += missing_amount_in_asset
        else:
            missing_funds[asset_name] = missing_amount_in_asset
    return missing_amount_in_asset


def _iterate_filling_assets(
    asset_name: str,
    allowed_filling_assets: list[str],
    tickers: dict[str, float],
):
    for allowed_filling_asset in allowed_filling_assets:
        symbol = symbol_util.merge_currencies(asset_name, allowed_filling_asset)
        if symbol in tickers:
            try:
                yield allowed_filling_asset, decimal.Decimal(str(tickers[symbol]))
            except decimal.DecimalException as err:
                commons_logging.get_logger(__name__).warning(
                    f"Error when reading {symbol} price: \"{tickers[symbol]}\": {err}"
                )
        else:
            reversed_symbol = symbol_util.merge_currencies(allowed_filling_asset, asset_name)
            if reversed_symbol in tickers and tickers[reversed_symbol]:
                yield allowed_filling_asset, constants.ONE / decimal.Decimal(str(tickers[reversed_symbol]))


def get_accepted_missed_deltas(
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_sub_portfolio: dict[str, dict[str, decimal.Decimal]],
    missed_deltas: dict[str, dict[str, decimal.Decimal]]
) -> (dict[str, dict[str, decimal.Decimal]], dict[str, dict[str, decimal.Decimal]]):
    # accepted deltas are missed deltas that should still be accepted to avoid ignoring
    # spent assets in master portfolio
    accepted_missed_deltas = {}
    for currency, delta in missed_deltas.items():
        try:
            updated_total = updated_portfolio_content[currency][commons_constants.PORTFOLIO_TOTAL]
        except KeyError:
            updated_total = constants.ZERO
        if currency in updated_sub_portfolio and (
            updated_sub_portfolio[currency][commons_constants.PORTFOLIO_TOTAL] > updated_total
        ):
            # updated sub portfolio asset holding can't be larger than updated total portfolio holding
            # => add this delta to accepted deltas
            accepted_missed_deltas[currency] = delta
    # others are still missed deltas
    remaining_missed_deltas = {
        currency: delta
        for currency, delta in missed_deltas.items()
        if currency not in accepted_missed_deltas
    }
    return accepted_missed_deltas, remaining_missed_deltas


def get_master_checked_sub_portfolio_update(
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_sub_portfolio: dict[str, dict[str, decimal.Decimal]],
) -> dict[str, dict[str, decimal.Decimal]]:
    update = {}
    for currency, amounts in updated_sub_portfolio.items():
        if currency not in updated_portfolio_content:
            # currency can't be in sub portfolio if not in master portfolio
            if amounts[commons_constants.PORTFOLIO_TOTAL] > constants.ZERO:
                commons_logging.get_logger(__name__).warning(
                    f"{currency} removed from sub portfolio as missing from master portfolio"
                )
                update[currency] = {
                    commons_constants.PORTFOLIO_TOTAL: constants.ZERO,
                    commons_constants.PORTFOLIO_AVAILABLE: constants.ZERO
                }
        elif (
            amounts[commons_constants.PORTFOLIO_TOTAL]
            > updated_portfolio_content[currency][commons_constants.PORTFOLIO_TOTAL]
        ):
            commons_logging.get_logger(__name__).warning(
                f"{currency} holdings aligned to master portfolio: {amounts} -> {updated_portfolio_content[currency]}"
            )
            # sub portfolio amount can't be larger than master portfolio
            update[currency] = updated_portfolio_content[currency]
    return update


def get_missing_master_portfolio_values_update(
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_sub_portfolio: dict[str, dict[str, decimal.Decimal]],
):
    updates = {}
    for currency, amounts in updated_portfolio_content.items():
        if currency in updated_sub_portfolio and (
            updated_sub_portfolio[currency][commons_constants.PORTFOLIO_TOTAL]
            > updated_portfolio_content[currency][commons_constants.PORTFOLIO_TOTAL]
        ):
            # updated sub portfolio asset holding can't be larger than updated total portfolio holding
            updates[currency] = amounts
    return updates


async def get_portfolio_filled_orders_deltas(
    previous_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    updated_portfolio_content: dict[str, dict[str, decimal.Decimal]],
    filled_or_partially_filled_orders: list[order_import.Order],
    unknown_filled_or_cancelled_orders: list[order_import.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    randomize_secondary_checks: bool,
    timeout: typing.Optional[float],
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    portfolios_asset_deltas = _get_assets_delta_from_portfolio(previous_portfolio_content, updated_portfolio_content)
    if unknown_filled_or_cancelled_orders:
        return await _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders(
            filled_or_partially_filled_orders, portfolios_asset_deltas, 
            unknown_filled_or_cancelled_orders, ignored_filled_quantity_per_order_exchange_id,
            randomize_secondary_checks, timeout
        )
    else:
        orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, _ = get_assets_delta_from_orders(
            filled_or_partially_filled_orders, ignored_filled_quantity_per_order_exchange_id, True
        )
        return compute_assets_deltas_from_orders(
            orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, 
            portfolios_asset_deltas, allow_portfolio_delta_shrinking=True
        )


def _reverse_portfolio_deltas(
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
) -> dict[str, dict[str, decimal.Decimal]]:
    return {
        asset_name: {
            key: -delta_values[key] for key in delta_values
        }
        for asset_name, delta_values in portfolios_asset_deltas.items()
    }


def _can_orders_compensate_each_other(unknown_filled_or_cancelled_orders: list[order_import.Order]) -> bool:
    # check if the orders can compensate each other
    # compensation means that the orders have the same symbol and opposite sides
    symbols_with_buy_orders = set(
        order.symbol for order in unknown_filled_or_cancelled_orders if order.side is enums.TradeOrderSide.BUY
    )
    symbols_with_sell_orders = set(
        order.symbol for order in unknown_filled_or_cancelled_orders if order.side is enums.TradeOrderSide.SELL
    )
    return bool(symbols_with_buy_orders.intersection(symbols_with_sell_orders))


def _get_combinations_count(total_elements, selected_elements):
    return math.factorial(total_elements) // (
        math.factorial(selected_elements) * math.factorial(total_elements - selected_elements)
    )


def _get_order_counts_to_fill_and_combinations_count(
    unknown_filled_or_cancelled_orders: list[order_import.Order]
) -> list[tuple[int, int]]:
    """
    returns the order count of each combination and the number of combinations for each count
    sorted by the number of combinations, lowest first
    """
    combinations_per_count = {
        orders_to_fill_count: _get_combinations_count(len(unknown_filled_or_cancelled_orders), orders_to_fill_count)
        for orders_to_fill_count in range(1, len(unknown_filled_or_cancelled_orders) + 1)
    }
    return [
        (orders_to_fill_count, combinations_per_count[orders_to_fill_count])
        for orders_to_fill_count in sorted(
            combinations_per_count,
            # key 1: lowest combinations count first (combinations_per_count[x])
            # key 2: largest filled orders count first (x)
            key=lambda x: combinations_per_count[x] * 100 - x
        )
    ]


def _get_quicky_and_secondary_order_combinations_checks(
    unknown_filled_or_cancelled_orders: list[order_import.Order]
) -> tuple[list[int], list[int], list[tuple[int, int]]]:
    sorted_orders_to_fill_counts_and_combinations_count = _get_order_counts_to_fill_and_combinations_count(
        unknown_filled_or_cancelled_orders
    )
    return [
        orders_to_fill_count
        for orders_to_fill_count, combinations_count in sorted_orders_to_fill_counts_and_combinations_count
        if combinations_count <= constants.MAX_ORDER_INFERENCE_QUICK_CHECK_COMBINATIONS_COUNT
    ], [
        orders_to_fill_count
        for orders_to_fill_count, combinations_count in sorted_orders_to_fill_counts_and_combinations_count
        if constants.MAX_ORDER_INFERENCE_QUICK_CHECK_COMBINATIONS_COUNT < combinations_count <= constants.MAX_ORDER_SECONDARY_INFERENCE_COMBINATIONS_COUNT
    ], [
        (orders_to_fill_count, combinations_count)
        for orders_to_fill_count, combinations_count in sorted_orders_to_fill_counts_and_combinations_count
        if combinations_count > constants.MAX_ORDER_SECONDARY_INFERENCE_COMBINATIONS_COUNT
    ]


async def _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders(
    filled_or_partially_filled_orders: list[order_import.Order],
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    unknown_filled_or_cancelled_orders: list[order_import.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    randomize_secondary_checks: bool,
    timeout: typing.Optional[float],
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    """
    Returns the most probable deltas which are the ones that can be best explained by given orders
    """
    if filled_or_partially_filled_orders:
        orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, _ = get_assets_delta_from_orders(
            filled_or_partially_filled_orders, ignored_filled_quantity_per_order_exchange_id, True
        )
        known_filled_orders_resolved_delta = compute_assets_deltas_from_orders(
            orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, 
            portfolios_asset_deltas, 
            allow_portfolio_delta_shrinking=False, 
            allow_mixed_sign_delta=True,
            register_missed_partial_delta_as_ignored=True, 
            ignore_order_unrelated_deltas=False,
            ignore_order_extra_deltas=False,
        )
    else:
        known_filled_orders_resolved_delta = resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta()
    # init with all cancelled orders and explained+unexplained portfolio deltas from known filled orders
    best_inferred_resolved_delta = resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta(
        inferred_cancelled_orders= list(unknown_filled_or_cancelled_orders), # avoid modifying the original list
    ).merge_order_deltas(known_filled_orders_resolved_delta, portfolios_asset_deltas)
    if (
        not best_inferred_resolved_delta.unexplained_orders_deltas 
        and not _can_orders_compensate_each_other(unknown_filled_or_cancelled_orders)
    ):
        # all orders are cancelled: stop here
        return _get_cleared_inferred_resolved_delta(
            best_inferred_resolved_delta, portfolios_asset_deltas
        )
    remaining_portfolio_asset_deltas = resolved_orders_portfolio_delta.filter_empty_deltas(
        sub_portfolio_data.get_content_after_deltas(
            portfolios_asset_deltas, _reverse_portfolio_deltas(
                best_inferred_resolved_delta.explained_orders_deltas
            ), apply_available_deltas=True
        )
    )
    # split orders by symbol and compute deltas together for each linked order
    orders_per_symbol = {
        symbol: [order for order in unknown_filled_or_cancelled_orders if order.symbol == symbol]
        for symbol in list_util.deduplicate([order.symbol for order in unknown_filled_or_cancelled_orders])
    }
    if len(orders_per_symbol) == 1 or len(unknown_filled_or_cancelled_orders) <= 10:
        # few orders or all orders are for the same symbol: compute deltas together 
        # more accurate that symbol per symbol as it minimizes deltas but more expensive in CPU when many orders
        return await _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_for_symbol(
            unknown_filled_or_cancelled_orders, ignored_filled_quantity_per_order_exchange_id,  remaining_portfolio_asset_deltas, known_filled_orders_resolved_delta, portfolios_asset_deltas, best_inferred_resolved_delta, randomize_secondary_checks, timeout
        )
    else:
        filled_orders = []
        # orders are for different symbols: compute deltas separately when possible to limit the number of combinations
        initial_best_inferred_resolved_delta = resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta()
        for symbol_orders in orders_per_symbol.values():
            symbol_best_inferred_resolved_delta = await _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_for_symbol(
                symbol_orders, ignored_filled_quantity_per_order_exchange_id, remaining_portfolio_asset_deltas, known_filled_orders_resolved_delta, portfolios_asset_deltas, best_inferred_resolved_delta, randomize_secondary_checks, timeout
            )
            filled_orders.extend(symbol_best_inferred_resolved_delta.inferred_filled_orders)
            known_filled_orders_resolved_delta = symbol_best_inferred_resolved_delta
            known_filled_orders_resolved_delta.inferred_filled_orders.clear()
            known_filled_orders_resolved_delta.inferred_cancelled_orders.clear()
            best_inferred_resolved_delta = initial_best_inferred_resolved_delta.merge_order_deltas(
                known_filled_orders_resolved_delta, portfolios_asset_deltas
            )
            remaining_portfolio_asset_deltas = resolved_orders_portfolio_delta.filter_empty_deltas(
                sub_portfolio_data.get_content_after_deltas(
                    portfolios_asset_deltas, _reverse_portfolio_deltas(
                        symbol_best_inferred_resolved_delta.explained_orders_deltas
                    ), apply_available_deltas=True
                )
            )
            if not remaining_portfolio_asset_deltas:
                # all filled orders have been identified: stop here
                break
        

        orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, _ = get_assets_delta_from_orders(
            filled_or_partially_filled_orders + filled_orders, ignored_filled_quantity_per_order_exchange_id, True
        )
        resolved_delta = compute_assets_deltas_from_orders(
            orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, 
            portfolios_asset_deltas, 
            allow_portfolio_delta_shrinking=False, 
            register_missed_partial_delta_as_ignored=True, 
            ignore_order_unrelated_deltas=False,
            ignore_order_extra_deltas=True,
        )
        resolved_delta.inferred_filled_orders = filled_orders
        resolved_delta.inferred_cancelled_orders = [order for order in unknown_filled_or_cancelled_orders if order not in filled_orders]
        return _get_cleared_inferred_resolved_delta(resolved_delta, portfolios_asset_deltas)


async def _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_for_symbol(
    unknown_filled_or_cancelled_orders: list[order_import.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    post_filled_orders_portfolio_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    known_filled_orders_resolved_delta: resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta,
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    best_inferred_resolved_delta: resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta,
    randomize_secondary_checks: bool,
    timeout: typing.Optional[float],
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    inference_start_time = time.time()
    symbols = set(order.symbol for order in unknown_filled_or_cancelled_orders)
    quick_check_orders_to_fill_counts, secondary_check_orders_to_fill_counts, skipped_combinations = _get_quicky_and_secondary_order_combinations_checks(
        unknown_filled_or_cancelled_orders
    )
    
    compute_forecasted_fees = False # don't compute forecasted fees as it will 10x the time to compute the deltas
    best_inferred_resolved_delta = _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_after_filled_orders_deltas(
        quick_check_orders_to_fill_counts, 
        unknown_filled_or_cancelled_orders, ignored_filled_quantity_per_order_exchange_id, 
        compute_forecasted_fees, post_filled_orders_portfolio_asset_deltas, known_filled_orders_resolved_delta, 
        portfolios_asset_deltas, best_inferred_resolved_delta, None
    )
    if not best_inferred_resolved_delta.is_fully_explained() and secondary_check_orders_to_fill_counts:
        # best_inferred_resolved_delta is not found in quick checks, try the (slow) rest in a separate thread
        # to release async loop
        if skipped_combinations:
            min_skipped = min(s[0] for s in skipped_combinations)
            max_skipped = max(s[0] for s in skipped_combinations)
            skipped = (
                f" Skipping {','.join(symbols)} [{min_skipped}:{max_skipped}] filled orders among {len(unknown_filled_or_cancelled_orders)} (which is {len(skipped_combinations)} combinations out of {len(unknown_filled_or_cancelled_orders)}) as they contain more than {constants.MAX_ORDER_SECONDARY_INFERENCE_COMBINATIONS_COUNT} possibilities."
            )
        else:
            skipped = ""
        commons_logging.get_logger(__name__).error(
            f"Best {','.join(symbols)} inferred resolved delta not found in {len(quick_check_orders_to_fill_counts)} "
            f"quick check configurations ({', '.join(str(count) for count in quick_check_orders_to_fill_counts)}), "
            f"trying the (slow) {len(secondary_check_orders_to_fill_counts)} other configurations in a separate thread.{skipped}"
        )
        # Note on the thread: as this is a python thread, it will not really run 
        # concurrently or on different cores, the current CPU will swap between 
        # this thread and the async loop thread, therefore making everything slower but
        # ensuring the async loop is not blocked, which is the goal of this thread
        auto_canceller_task = None
        try:
            if randomize_secondary_checks:
                random.shuffle(secondary_check_orders_to_fill_counts)
            cancelled_event = threading.Event()
            if timeout is not None:
                remaining_timeout = timeout - (time.time() - inference_start_time)
                if remaining_timeout <= 0:
                    # timeout already reached: cancel thread immediately
                    commons_logging.get_logger(__name__).error(
                        f"Timeout of {timeout}s was already reached while computing most probable assets "
                        f"deltas before using background thread for symbol {','.join(symbols)}"
                    )
                    return best_inferred_resolved_delta
                async def _auto_canceller():
                    await asyncio.sleep(remaining_timeout)
                    if not cancelled_event.is_set():
                        commons_logging.get_logger(__name__).warning(
                            f"Timeout: {remaining_timeout}s (remaining of intial {timeout}s) while computing most "
                            f"probable assets deltas for {len(secondary_check_orders_to_fill_counts)} "
                            f"orders for symbol {','.join(symbols)} - cancelling background thread"
                        )
                        cancelled_event.set()
                auto_canceller_task = asyncio.create_task(_auto_canceller())
            best_inferred_resolved_delta = await asyncio.to_thread(    
                _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_after_filled_orders_deltas,
                secondary_check_orders_to_fill_counts, 
                unknown_filled_or_cancelled_orders, ignored_filled_quantity_per_order_exchange_id, 
                compute_forecasted_fees, post_filled_orders_portfolio_asset_deltas, known_filled_orders_resolved_delta, 
                portfolios_asset_deltas, best_inferred_resolved_delta, cancelled_event
            )
        except (asyncio.CancelledError, asyncio.TimeoutError) as err:
            # catch both cancelled and timeout errors to cancel thread when it happens
            if isinstance(err, asyncio.CancelledError) and cancelled_event.is_set():
                # this is an expected cancellation: continue (don't raise)
                return best_inferred_resolved_delta
            commons_logging.get_logger(__name__).warning(
                f"{err.__class__.__name__}:{err} while computing most probable assets deltas for {len(secondary_check_orders_to_fill_counts)} orders for symbol {','.join(symbols)} - cancelling background thread"
            )
            # cancel thread to avoid having it run for nothing
            cancelled_event.set()
            raise
        finally:
            if auto_canceller_task is not None and not auto_canceller_task.done():
                auto_canceller_task.cancel()

    return _get_cleared_inferred_resolved_delta(best_inferred_resolved_delta, portfolios_asset_deltas)


def _compute_most_probable_assets_deltas_from_orders_considering_unknown_orders_after_filled_orders_deltas(
    sorted_orders_to_fill_counts: typing.Iterable[int],
    unknown_filled_or_cancelled_orders: list[order_import.Order],
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    compute_forecasted_fees: bool,
    post_filled_orders_portfolio_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    known_filled_orders_resolved_delta: resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta,
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    best_inferred_resolved_delta: resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta,
    cancelled_event: typing.Optional[threading.Event],
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    last_sleep_time = time.time()
    for orders_to_fill_count in sorted_orders_to_fill_counts:
        for filled_orders_combination in itertools.combinations(unknown_filled_or_cancelled_orders, orders_to_fill_count):
            if cancelled_event:
                if time.time() - last_sleep_time > constants.MAX_ORDER_INFERENCE_ITERATIONS_DURATION:
                    # If cancelled_event is set, this is running in a thread. As this function requires a lot of CPU, force 
                    # it to sleep at regular intervals to let other threads as well since real multi-threading doesn't exist in python du to the GIL.
                    # This is somewhat similar to a lower priority thread, even though this doesn't really exist in python
                    time.sleep(constants.ORDER_INFERENCE_SLEEP_TIME)
                    last_sleep_time = time.time()
                if cancelled_event.is_set():
                    # cancelled, complete function immediately
                    return best_inferred_resolved_delta
            potential_filled_orders_combination = list(filled_orders_combination)
            (
                orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, counted_exchange_fee_deltas
            ) = get_assets_delta_from_orders(
                potential_filled_orders_combination, ignored_filled_quantity_per_order_exchange_id, 
                compute_forecasted_fees, force_fully_filled_orders=True
            )
            if any(
                asset_name not in post_filled_orders_portfolio_asset_deltas
                for asset_name in orders_asset_deltas
                if (
                    # ensure this delta is not due to exchange fees only, which can be in 
                    # local exchange fees currency (ex: binance and BNB)
                    asset_name not in counted_exchange_fee_deltas
                    or counted_exchange_fee_deltas[asset_name] != orders_asset_deltas[asset_name]
                )
            ):
                # at least one of the candidate filled orders is not related to portfolio delta: skip this combination
                continue
            inferred_resolved_delta_candidate = compute_assets_deltas_from_orders(
                orders_asset_deltas, expected_fee_related_deltas, possible_fees_asset_deltas, 
                post_filled_orders_portfolio_asset_deltas, 
                allow_portfolio_delta_shrinking=False, 
                register_missed_partial_delta_as_ignored=True, 
                ignore_order_unrelated_deltas=False,
                ignore_order_extra_deltas=True,
            )
            if not inferred_resolved_delta_candidate.adds_explanations():
                # no added explanations: skip this combination
                continue
            merged_inferred_resolved_delta_candidate = inferred_resolved_delta_candidate.merge_order_deltas(
                known_filled_orders_resolved_delta, portfolios_asset_deltas
            )
            merged_inferred_resolved_delta_candidate.inferred_filled_orders = potential_filled_orders_combination
            merged_inferred_resolved_delta_candidate.inferred_cancelled_orders = [
                order for order in unknown_filled_or_cancelled_orders if order not in potential_filled_orders_combination
            ]
            try:
                if merged_inferred_resolved_delta_candidate.is_fully_explained():
                    return merged_inferred_resolved_delta_candidate
                elif merged_inferred_resolved_delta_candidate.is_more_probable_than(best_inferred_resolved_delta):
                    best_inferred_resolved_delta = merged_inferred_resolved_delta_candidate
            except KeyError as err:
                # should not happen, catch it to avoid raising it if it does
                commons_logging.get_logger(__name__).error(
                    f"Unexpected error when computing most probable assets deltas from orders: {err}"
                )
    return best_inferred_resolved_delta


def _get_cleared_inferred_resolved_delta(
    resolved_delta: resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta,
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    # clear partial deltas as they should not be considered real deltas (they are due to other "unknown" orders)
    resolved_delta.ensure_max_delta_and_clear_irrelevant_deltas(portfolios_asset_deltas)
    return resolved_delta


def compute_assets_deltas_from_orders(
    orders_asset_deltas: dict[str, decimal.Decimal], 
    expected_fee_related_deltas: dict[str, decimal.Decimal], 
    possible_fees_asset_deltas: dict[str, decimal.Decimal],
    portfolios_asset_deltas: dict[str, dict[str, decimal.Decimal]],
    allow_portfolio_delta_shrinking: bool = True,
    allow_mixed_sign_delta: bool = False,
    register_missed_partial_delta_as_ignored: bool = False,
    ignore_order_unrelated_deltas: bool = True,
    ignore_order_extra_deltas: bool = False,
) -> resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta:
    """
    returns portfolio asset deltas that can approximately be explained by given orders
    """
    orders_linked_deltas = {}
    ignored_deltas = {}
    for asset_name, holdings_delta in portfolios_asset_deltas.items():
        if asset_name not in orders_asset_deltas:
            if ignore_order_unrelated_deltas:
                # this delta is not due to these orders: skip it
                continue
            else:
                # this delta is not due to these orders: add it to ignored deltas
                ignored_deltas[asset_name] = holdings_delta
            continue
        order_asset_delta = orders_asset_deltas[asset_name]
        holding_total = holdings_delta[commons_constants.PORTFOLIO_TOTAL]
        min_allowed_equivalent_total_holding = (
            holding_total * (constants.ONE - constants.SUB_PORTFOLIO_ALLOWED_DELTA_RATIO)
        )
        max_allowed_equivalent_total_holding = (
            holding_total * (constants.ONE + constants.SUB_PORTFOLIO_ALLOWED_DELTA_RATIO)
        )
        if (
            order_asset_delta * min_allowed_equivalent_total_holding < 0
            and (order_asset_delta + possible_fees_asset_deltas.get(asset_name, constants.ZERO))
                * min_allowed_equivalent_total_holding < 0
        ):
            # different sign: incompatible, this is unexpected
            if allow_mixed_sign_delta:
                orders_linked_deltas[asset_name] = {
                    key: order_asset_delta
                    for key in holdings_delta
                }
            else:
                ignored_deltas[asset_name] = holdings_delta
        elif (
            # approx same value
            abs(min_allowed_equivalent_total_holding)
            < abs(order_asset_delta)
            < abs(max_allowed_equivalent_total_holding)
        ):
            # similar delta (+/- fees)
            # this delta is due to these orders: add it
            orders_linked_deltas[asset_name] = holdings_delta
        elif asset_name in expected_fee_related_deltas and (
            abs(expected_fee_related_deltas[asset_name]) > abs(holdings_delta[commons_constants.PORTFOLIO_AVAILABLE])
        ):
            # paid fees are higher than holding delta: mostly paid fees, validate this delta
            orders_linked_deltas[asset_name] = holdings_delta
        elif (
            # try while taking expected and lower than expected fees into account
            asset_name in expected_fee_related_deltas and (
                any(
                    abs(min_allowed_equivalent_total_holding)
                    # fees bring back the order delta into the expected portfolio delta window
                    < abs(order_asset_delta + expected_fee)
                    < abs(max_allowed_equivalent_total_holding)
                    for expected_fee in (
                        # try with smaller fees in case user is paying less fees (when having large volume)
                        # test from 10% up to 100% fees
                        expected_fee_related_deltas[asset_name] * decimal.Decimal(multiplier / 10)
                        for multiplier in range(1, 11)
                    )
                )
            )
        ):
            # similar delta considering fees
            # this delta is due to these orders: add it
            orders_linked_deltas[asset_name] = holdings_delta
        elif abs(order_asset_delta) > abs(max_allowed_equivalent_total_holding):
            # last chance: try with potential fees, in case the expected fee currency was wrong
            if (
                # try while taking possible fees into account
                asset_name in possible_fees_asset_deltas and (
                    any(
                        abs(min_allowed_equivalent_total_holding)
                        # fees bring back the order delta into the expected portfolio delta window
                        < abs(order_asset_delta + possible_fee)
                        < abs(max_allowed_equivalent_total_holding)
                        for possible_fee in (
                            # try with smaller fees in case user is paying less fees (when having large volume)
                            # test from 10% up to 100% fees
                            possible_fees_asset_deltas[asset_name] * decimal.Decimal(multiplier / 10)
                            for multiplier in range(1, 11)
                        )
                    )
                )
            ):
                orders_linked_deltas[asset_name] = holdings_delta
            else:
                # too little in portfolio delta to be from those orders
                # As potential fees have already been taken into account, THIS IS UNEXPECTED.
                # Add it to ignored_deltas
                ignored_deltas[asset_name] = holdings_delta
        elif abs(min_allowed_equivalent_total_holding) > abs(order_asset_delta):
            # too much in portfolio delta
            if register_missed_partial_delta_as_ignored:
                # Partial deltas: only take what is linked to the orders deltas
                # => updates both total and available
                orders_linked_deltas[asset_name] = {
                    key: order_asset_delta
                    for key in holdings_delta
                }
                # register extra delta as ignored
                ignored_deltas[asset_name] = {
                    key: pf_delta - order_asset_delta if abs(pf_delta - order_asset_delta) > constants.ZERO else constants.ZERO
                    for key, pf_delta in holdings_delta.items()
                }
            elif allow_portfolio_delta_shrinking:
                # Only take what is linked to the orders deltas and ignore extra delta values (shrink portfolio deltas)
                # => updates both total and available
                # Should very rarely happen as it might reduce the total portfolio if done when unecessary
                commons_logging.get_logger(__name__).warning(
                    f"Too large portfolio {asset_name} delta: {holdings_delta}, reducing to order delta: {order_asset_delta}"
                )
                orders_linked_deltas[asset_name] = {
                    key: order_asset_delta
                    for key in holdings_delta
                }
            else:
                # can't be from those orders: ignore this delta
                ignored_deltas[asset_name] = holdings_delta

    if not ignore_order_extra_deltas:
        # consider order deltas that are seen in portfolio deltas
        for asset_name, order_delta in orders_asset_deltas.items():
            can_have_no_delta = (
                (order_delta == constants.ZERO)
                or (order_delta + possible_fees_asset_deltas.get(asset_name, constants.ZERO)) == constants.ZERO
                or (order_delta - possible_fees_asset_deltas.get(asset_name, constants.ZERO)) == constants.ZERO
            )
            if asset_name not in portfolios_asset_deltas and not can_have_no_delta:
                # asset not in portfolio delta, this is unexpected, register it in ignored deltas
                ignored_deltas[asset_name] = {
                    commons_constants.PORTFOLIO_TOTAL: order_delta,
                    commons_constants.PORTFOLIO_AVAILABLE: order_delta
                }
    return resolved_orders_portfolio_delta.ResolvedOrdersPortoflioDelta(
        explained_orders_deltas=orders_linked_deltas,
        unexplained_orders_deltas=ignored_deltas
    )


def _get_assets_delta_from_portfolio(
    previous_portfolio_content: dict,
    updated_portfolio_content: dict,
) -> dict[str, dict[str, decimal.Decimal]]:
    asset_deltas = {}
    for asset_name in set(previous_portfolio_content).union(updated_portfolio_content):
        if previous_portfolio_content.get(asset_name) != updated_portfolio_content.get(asset_name):
            if asset_name not in previous_portfolio_content:
                # asset has been added
                asset_deltas[asset_name] = updated_portfolio_content[asset_name]
            elif asset_name not in updated_portfolio_content:
                # asset has been removed
                asset_deltas[asset_name] = {key: -val for key, val in previous_portfolio_content[asset_name].items()}
            else:
                # asset was already here
                asset_deltas[asset_name] = {}
                for key, updated_value in updated_portfolio_content[asset_name].items():
                    asset_deltas[asset_name][key] = updated_value - previous_portfolio_content[asset_name][key]
    return asset_deltas


def get_assets_delta_from_orders(
    orders: list[order_import.Order], 
    ignored_filled_quantity_per_order_exchange_id: dict[str, decimal.Decimal],
    compute_forecasted_fees: bool,
    force_fully_filled_orders: bool = False,
) -> tuple[
    dict[str, decimal.Decimal], dict[str, decimal.Decimal], dict[str, decimal.Decimal], dict[str, decimal.Decimal]
]:
    asset_deltas = {}
    expected_fee_related_deltas = {}
    possible_fee_related_deltas = {}
    counted_exchange_fee_deltas = {}
    exchange_local_fees_currency_price = _get_exchange_local_fees_currency_price(orders) if compute_forecasted_fees else None
    for order in orders:
        base, quote = symbol_util.parse_symbol(order.symbol).base_and_quote()
        # order "expected" related deltas
        ignored_filled_quantity = ignored_filled_quantity_per_order_exchange_id.get(order.exchange_order_id)
        # For 0 amout filled orders, use origin quantity as we know they are either fully filled or not filled at all.
        # For partially filled orders, use filled quantity as we know they are partially filled.
        considered_quantity = order.filled_quantity if (order.filled_quantity and not force_fully_filled_orders) else order.origin_quantity
        delta_quantity = (considered_quantity - ignored_filled_quantity) if ignored_filled_quantity else considered_quantity
        if delta_quantity < constants.ZERO:
            commons_logging.get_logger(__name__).error(
                f"Invalid delta quantity: {delta_quantity} for order "
                f"{order.exchange_order_id} on {order.symbol} "
                f"ignored filled quantity: {ignored_filled_quantity}."
            )
            continue
        if delta_quantity == constants.ZERO:
            commons_logging.get_logger(__name__).info(
                f"Skipped zero delta quantity: {delta_quantity} for order "
                f"{order.exchange_order_id} on {order.symbol} "
                f"ignored filled quantity: {ignored_filled_quantity}."
            )
            continue
        if order.side is enums.TradeOrderSide.BUY:
            added_unit_and_amount = (base, delta_quantity)
            removed_unit_and_amount = (quote, order.get_cost(delta_quantity))
        elif order.side is enums.TradeOrderSide.SELL:
            added_unit_and_amount = (quote, order.get_cost(delta_quantity))
            removed_unit_and_amount = (base, delta_quantity)
        else:
            raise ValueError(f"Invalid order side: {order.side}")
        for unit_and_amount, multiplier in zip(
            (added_unit_and_amount, removed_unit_and_amount),
            (decimal.Decimal(1), decimal.Decimal(-1))
        ):
            if unit_and_amount[0] not in asset_deltas:
                asset_deltas[unit_and_amount[0]] = unit_and_amount[1] * multiplier
            else:
                asset_deltas[unit_and_amount[0]] += unit_and_amount[1] * multiplier
        if actual_fees := order.fee:
            if (
                actual_fees[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] 
                and actual_fees[enums.FeePropertyColumns.COST.value]
            ):
                # order fees are from exchange: add them to asset deltas as they are confirmed
                fee_asset = actual_fees[enums.FeePropertyColumns.CURRENCY.value]
                if fee_asset not in asset_deltas:
                    # always substract fees
                    asset_deltas[fee_asset] = -decimal.Decimal(str(actual_fees[enums.FeePropertyColumns.COST.value]))
                else:
                    asset_deltas[fee_asset] -= decimal.Decimal(str(actual_fees[enums.FeePropertyColumns.COST.value]))
                if fee_asset not in counted_exchange_fee_deltas:
                    # always substract fees
                    counted_exchange_fee_deltas[fee_asset] = -decimal.Decimal(str(actual_fees[enums.FeePropertyColumns.COST.value]))
                else:
                    counted_exchange_fee_deltas[fee_asset] -= decimal.Decimal(str(actual_fees[enums.FeePropertyColumns.COST.value]))
        if compute_forecasted_fees:
            # order "probable" related deltas (account for worse case fees)
            expected_forecasted_fees = order.get_computed_fee(use_origin_quantity_and_price=True)
            possible_forecasted_fees = _get_other_asset_forecasted_fees(
                order, expected_forecasted_fees, exchange_local_fees_currency_price
            )
            for fee_asset in (base, quote) + tuple(exchange_local_fees_currency_price):
                for fee in (expected_forecasted_fees, ) + possible_forecasted_fees:
                    is_expected_fee = fee is expected_forecasted_fees
                    if asset_amount := order_util.get_fees_for_currency(fee, fee_asset):
                        for delta_counter in (expected_fee_related_deltas, possible_fee_related_deltas):
                            if delta_counter is expected_fee_related_deltas and not is_expected_fee:
                                # when updating expected_fee_related_deltas, only account for expected fees
                                continue
                            if fee_asset not in delta_counter:
                                delta_counter[fee_asset] = -asset_amount
                            else:
                                delta_counter[fee_asset] += -asset_amount
    return (
        asset_deltas, 
        expected_fee_related_deltas, possible_fee_related_deltas, counted_exchange_fee_deltas
    )


def get_fees_only_asset_deltas_from_orders(orders: list[order_import.Order]) -> dict[str, decimal.Decimal]:
    order_traded_assets = set()
    for order in orders:
        symbol = symbol_util.parse_symbol(order.symbol)
        order_traded_assets.add(symbol.base)
        order_traded_assets.add(symbol.quote)
    return {
        currency: delta
        for currency, delta in _get_fees_assets_deltas_from_orders(orders).items()
        if currency not in order_traded_assets
    }


def _get_fees_assets_deltas_from_orders(orders: list[order_import.Order]) -> dict[str, decimal.Decimal]:
    asset_deltas = {}
    for order in orders:
        if (fees := order.fee) and fees[enums.FeePropertyColumns.COST.value]:
            fee_asset = fees[enums.FeePropertyColumns.CURRENCY.value]
            if fee_asset not in asset_deltas:
                asset_deltas[fee_asset] = -decimal.Decimal(str(fees[enums.FeePropertyColumns.COST.value]))
            else:
                asset_deltas[fee_asset] -= decimal.Decimal(str(fees[enums.FeePropertyColumns.COST.value])) 
    return asset_deltas


def _get_other_asset_forecasted_fees(
    order: order_import.Order, forecasted_fees: dict, 
    exchange_local_fees_currency_price: dict[str, dict[str, decimal.Decimal]]
) -> tuple[dict]:
    base, quote = symbol_util.parse_symbol(order.symbol).base_and_quote()
    other_fee = copy.deepcopy(forecasted_fees)
    base_local_fee = None
    quote_local_fee = None
    if base_fee := order_util.get_fees_for_currency(forecasted_fees, base):
        fee_cost = base_fee * order.origin_price
        other_fee[enums.FeePropertyColumns.CURRENCY.value] = quote
        other_fee[enums.FeePropertyColumns.COST.value] = fee_cost
        if base not in exchange_local_fees_currency_price and quote not in exchange_local_fees_currency_price:
            for fee_currency, fee_price_by_symbol in exchange_local_fees_currency_price.items():
                for fee_symbol, fee_price in fee_price_by_symbol.items():
                    parsed_fee_symbol = symbol_util.parse_symbol(fee_symbol)
                    # shared base or quote ? divive, multiply otherwise
                    if parsed_fee_symbol.base == base or parsed_fee_symbol.quote == quote:
                        base_local_fee = {
                            enums.FeePropertyColumns.CURRENCY.value: fee_currency,
                            enums.FeePropertyColumns.COST.value: fee_cost / fee_price
                        }
                    elif parsed_fee_symbol.base == quote or parsed_fee_symbol.quote == base:
                        base_local_fee = {
                            enums.FeePropertyColumns.CURRENCY.value: fee_currency,
                            enums.FeePropertyColumns.COST.value: fee_cost * fee_price
                        }
    elif quote_fee := order_util.get_fees_for_currency(forecasted_fees, quote):
        fee_cost = quote_fee / order.origin_price
        other_fee[enums.FeePropertyColumns.CURRENCY.value] = base
        other_fee[enums.FeePropertyColumns.COST.value] = fee_cost
        if base not in exchange_local_fees_currency_price and quote not in exchange_local_fees_currency_price:
            for fee_currency, fee_price_by_symbol in exchange_local_fees_currency_price.items():
                for fee_symbol, fee_price in fee_price_by_symbol.items():
                    parsed_fee_symbol = symbol_util.parse_symbol(fee_symbol)
                    # shared base or quote ? divive, multiply otherwise
                    if parsed_fee_symbol.base == base or parsed_fee_symbol.quote == quote:
                        quote_local_fee = {
                            enums.FeePropertyColumns.CURRENCY.value: fee_currency,
                            enums.FeePropertyColumns.COST.value: fee_cost / fee_price
                        }
                    elif parsed_fee_symbol.base == quote or parsed_fee_symbol.quote == base:
                        quote_local_fee = {
                            enums.FeePropertyColumns.CURRENCY.value: fee_currency,
                            enums.FeePropertyColumns.COST.value: fee_cost * fee_price
                        }
    return tuple(
        fee
        for fee in (other_fee, base_local_fee, quote_local_fee)
        if fee is not None
    )


def _get_exchange_local_fees_currency_price(orders: list[order_import.Order]) -> dict[str, dict[str, decimal.Decimal]]:
    exchange_local_fees_currency_price = {}
    # use given orders to get the price of the potential local fees currencies
    # if an order trades this currency, then we can use its price to get the price of the currency
    for order in orders:
        for local_fees_currency in order.trader.exchange_manager.exchange.LOCAL_FEES_CURRENCIES:
            if local_fees_currency not in exchange_local_fees_currency_price:
                exchange_local_fees_currency_price[local_fees_currency] = {}
            if (
                local_fees_currency in symbol_util.parse_symbol(order.symbol).base_and_quote() 
                and order.symbol not in exchange_local_fees_currency_price[local_fees_currency]
            ):
                exchange_local_fees_currency_price[local_fees_currency][order.symbol] = order.origin_price
    return exchange_local_fees_currency_price
