#  Drakkar-Software OctoBot-Interfaces
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
import time
import sortedcontainers

import octobot_services.interfaces.util as interfaces_util
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.pretty_printer as pretty_printer
import octobot_commons.symbols as commons_symbols
import tentacles.Services.Interfaces.web_interface.errors as errors
import tentacles.Services.Interfaces.web_interface.models.dashboard as dashboard
import tentacles.Services.Interfaces.web_interface.models.configuration as configuration


def ensure_valid_exchange_id(exchange_id) -> str:
    try:
        trading_api.get_exchange_manager_from_exchange_id(exchange_id)
    except KeyError as e:
        raise errors.MissingExchangeId() from e


def get_exchange_watched_time_frames(exchange_id):
    try:
        exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
        return trading_api.get_watched_timeframes(exchange_manager), trading_api.get_exchange_name(exchange_manager)
    except KeyError:
        return [], ""


def get_all_watched_time_frames():
    time_frames = []
    for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids()):
        if not trading_api.get_is_backtesting(exchange_manager):
            time_frames += trading_api.get_watched_timeframes(exchange_manager)
    return time_frame_manager.sort_time_frames(list(set(time_frames)))


def get_initializing_currencies_prices_set(fetch_timeout):
    initializing_currencies = set()
    # if fetch_timeout is > 0 and prices are still missing after fetch_timeout, ignore them
    if fetch_timeout and time.time() > interfaces_util.get_bot_api().get_start_time() + fetch_timeout:
        return initializing_currencies
    for exchange_manager in interfaces_util.get_exchange_managers():
        initializing_currencies = initializing_currencies.union(
            trading_api.get_initializing_currencies_prices(exchange_manager))
    return initializing_currencies


def get_evaluation(symbol, exchange_name, exchange_id):
    try:
        if exchange_name:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_name_and_id(exchange_name, exchange_id)
            for trading_mode in trading_api.get_trading_modes(exchange_manager):
                if trading_api.get_trading_mode_symbol(trading_mode) == symbol:
                    state_desc, val_state = trading_api.get_trading_mode_current_state(trading_mode)
                    try:
                        val_state = round(val_state)
                    except TypeError:
                        pass
                    return f"{state_desc.replace('_', ' ')}, {val_state}"
    except KeyError:
        pass
    return "N/A"


def get_exchanges_load():
    return {
        trading_api.get_exchange_name(exchange_manager): {
            "load": trading_api.get_currently_handled_pair_with_time_frame(exchange_manager),
            "max_load": trading_api.get_max_handled_pair_with_time_frame(exchange_manager),
            "overloaded": trading_api.is_overloaded(exchange_manager),
            "has_websocket": trading_api.get_has_websocket(exchange_manager),
            "has_reached_websocket_limit": trading_api.get_has_reached_websocket_limit(exchange_manager)
        }
        for exchange_manager in interfaces_util.get_exchange_managers()
    }


def _add_exchange_portfolio(portfolio, exchange, holdings_per_symbol):
    exchanges_key = "exchanges"
    total_key = "total"
    free_key = "free"
    locked_key = "locked"
    for currency, amounts in portfolio.items():
        total_amount = amounts.total
        free_amount = amounts.available
        if total_amount > 0:
            if currency not in holdings_per_symbol:
                holdings_per_symbol[currency] = {
                    exchanges_key: {}
                }
            holdings_per_symbol[currency][exchanges_key][exchange] = {
                total_key: total_amount,
                free_key: free_amount,
                locked_key: total_amount - free_amount,
            }
            holdings_per_symbol[currency][total_key] = holdings_per_symbol[currency].get(total_key, 0) + total_amount
            holdings_per_symbol[currency][free_key] = holdings_per_symbol[currency].get(free_key, 0) + free_amount
            holdings_per_symbol[currency][locked_key] = holdings_per_symbol[currency][total_key] - \
                holdings_per_symbol[currency][free_key]


def get_exchange_holdings_per_symbol():
    holdings_per_symbol = {}
    for exchange_manager in configuration.get_live_trading_enabled_exchange_managers():
        portfolio = trading_api.get_portfolio(exchange_manager)
        _add_exchange_portfolio(portfolio, trading_api.get_exchange_name(exchange_manager), holdings_per_symbol)
    return holdings_per_symbol


def get_symbols_values(symbols, has_real_trader, has_simulated_trader):
    loading = 0
    value_per_symbols = {symbol: loading for symbol in symbols}
    real_portfolio_holdings, simulated_portfolio_holdings = interfaces_util.get_portfolio_holdings()
    portfolio = real_portfolio_holdings if has_real_trader else simulated_portfolio_holdings
    value_per_symbols.update(portfolio)
    return value_per_symbols


def _get_exchange_historical_portfolio(exchange_manager, currency, time_frame, from_timestamp, to_timestamp) -> list:
    return [
        {
            trading_enums.HistoricalPortfolioValue.TIME.value: value[trading_enums.HistoricalPortfolioValue.TIME.value],
            trading_enums.HistoricalPortfolioValue.VALUE.value: pretty_printer.get_min_string_from_number(
                value[trading_enums.HistoricalPortfolioValue.VALUE.value]
            )
        }
        for value in trading_api.get_portfolio_historical_values(
            exchange_manager, currency, time_frame, from_timestamp=from_timestamp, to_timestamp=to_timestamp
        )
    ]


def _merge_all_exchanges_historical_portfolio(currency, time_frame, from_timestamp, to_timestamp):
    merged_result = sortedcontainers.SortedDict()
    for exchange_manager in configuration.get_live_trading_enabled_exchange_managers():
        for value in _get_exchange_historical_portfolio(
                exchange_manager, currency, time_frame, from_timestamp, to_timestamp
        ):
            if value[trading_enums.HistoricalPortfolioValue.TIME.value] not in merged_result:
                merged_result[value[trading_enums.HistoricalPortfolioValue.TIME.value]] = \
                    value[trading_enums.HistoricalPortfolioValue.VALUE.value]
            else:
                merged_result[value[trading_enums.HistoricalPortfolioValue.TIME.value]] += str(decimal.Decimal(
                    value[trading_enums.HistoricalPortfolioValue.VALUE.value]
                ))
    return [
        {
            trading_enums.HistoricalPortfolioValue.TIME.value: key,
            trading_enums.HistoricalPortfolioValue.VALUE.value: val,
        }
        for key, val in merged_result.items()
    ]


def get_portfolio_historical_values(currency, time_frame=None, from_timestamp=None, to_timestamp=None, exchange=None):
    time_frame = commons_enums.TimeFrames(time_frame) if time_frame else commons_enums.TimeFrames.ONE_DAY
    if exchange is None:
        return _merge_all_exchanges_historical_portfolio(currency, time_frame, from_timestamp, to_timestamp)
    return _get_exchange_historical_portfolio(
        dashboard.get_first_exchange_data(exchange, trading_exchange_only=True)[0],
        currency, time_frame, from_timestamp, to_timestamp
    )


def _get_valid_pnl_history(exchange_manager, quote, symbol, since):
    return [
        pnl
        for pnl in trading_api.get_completed_pnl_history(
            exchange_manager,
            quote=quote,
            symbol=symbol,
            since=since
        )
        if _is_valid_pnl(pnl)
    ]


def _is_valid_pnl(pnl):
    try:
        return pnl.get_entry_time() and pnl.get_close_time()
    except trading_errors.IncompletePNLError:
        return False


def _get_pnl_history(exchange, quote, symbol, since):
    if exchange:
        return {
            exchange: _get_valid_pnl_history(
                dashboard.get_first_exchange_data(exchange, trading_exchange_only=True)[0],
                quote, symbol, since
            )
        }
    history = {}
    for exchange_manager in configuration.get_live_trading_enabled_exchange_managers():
        history[trading_api.get_exchange_name(exchange_manager)] = _get_valid_pnl_history(
            exchange_manager, quote, symbol, since
        )
    return history


def get_pnl_history_symbols(exchange=None, quote=None, symbol=None, since=None):
    return set(
        historical_pnl.entries[0].symbol
        for exchange_name, historical_pnl_elements in _get_pnl_history(exchange, quote, symbol, since).items()
        for historical_pnl in historical_pnl_elements
        if historical_pnl.entries
    )


def _convert_timestamp(timestamp):
    return timestamp_util.convert_timestamp_to_datetime(timestamp, time_format='%Y-%m-%d %H:%M:%S', local_timezone=True)


def get_pnl_history(exchange=None, quote=None, symbol=None, since=None, scale=None):
    ENTRY_PRICE = "en_p"
    EXIT_PRICE = "ex_p"
    ENTRY_TIME = "en_t"
    ENTRY_DATE = "en_d"
    EXIT_TIME = "ex_t"
    EXIT_DATE = "ex_d"
    ENTRY_SIDE = "en_s"
    EXIT_SIDE = "ex_s"
    ENTRY_AMOUNT = "en_a"
    EXIT_AMOUNT = "ex_a"
    DETAILS = "d"
    PNL = "pnl"
    PNL_AMOUNT = "pnl_a"
    EXCHANGE = "ex"
    FEES = "f"
    SPECIAL_FEES = "s_f"
    BASE = "b"
    QUOTE = "q"
    CURRENCY = "c"
    SYMBOL = "s"
    TRADES_COUNT = "tc"
    pnl_history = {}
    use_detailed_history = not(scale)
    scale_seconds = commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(scale)] * \
        commons_constants.MINUTE_TO_SECONDS if scale else 1
    symbol = symbol or None
    # set quote filter to None when symbol is not provided
    quote = None if symbol else quote
    history_by_exchange = _get_pnl_history(exchange, quote, symbol, since)
    invalid_pnls = 0
    for exchange_name, historical_pnl_elements in history_by_exchange.items():
        for historical_pnl in historical_pnl_elements:
            try:
                close_time = historical_pnl.get_close_time()
                scaled_time = close_time - (close_time % scale_seconds)
                pnl, pnl_p = historical_pnl.get_profits()
                pnl_a = historical_pnl.get_closed_close_value()
                if scaled_time not in pnl_history:
                    pnl_history[scaled_time] = {
                        PNL: pnl,
                        PNL_AMOUNT: pnl_a,
                        QUOTE: historical_pnl.entries[0].market,
                        TRADES_COUNT: len(historical_pnl.entries) + len(historical_pnl.closes),
                        DETAILS: None
                    }
                else:
                    pnl_val = pnl_history[scaled_time]
                    pnl_val[PNL] += pnl
                    pnl_val[PNL_AMOUNT] += pnl_a
                    pnl_val[TRADES_COUNT] += len(historical_pnl.entries) + len(historical_pnl.closes)
                if use_detailed_history:
                    pnl_history[scaled_time][DETAILS] = {
                        ENTRY_TIME: historical_pnl.get_entry_time(),
                        ENTRY_DATE: _convert_timestamp(historical_pnl.get_entry_time()),
                        ENTRY_PRICE: float(historical_pnl.get_entry_price()),
                        EXIT_PRICE: float(historical_pnl.get_close_price()),
                        ENTRY_SIDE: historical_pnl.entries[0].side.value,
                        EXIT_SIDE: historical_pnl.closes[0].side.value,
                        ENTRY_AMOUNT: historical_pnl.get_total_entry_quantity(),
                        EXIT_AMOUNT: historical_pnl.get_total_close_quantity(),
                        SYMBOL: historical_pnl.entries[0].symbol,
                        FEES: float(historical_pnl.get_paid_regular_fees_in_quote()),
                        SPECIAL_FEES: [
                            {
                                CURRENCY: currency,
                                FEES: float(value),
                            }
                            for currency, value in historical_pnl.get_paid_special_fees_by_currency().items()
                        ],
                        BASE: historical_pnl.entries[0].currency,
                        EXCHANGE: exchange_name,
                    }
            except trading_errors.IncompletePNLError:
                invalid_pnls += 1
    if invalid_pnls:
        logging.get_logger("TradingModel").warning(f"{invalid_pnls} invalid TradePNLs in history")
    return sorted(
        [
            {
                EXIT_TIME: t,
                EXIT_DATE: _convert_timestamp(t),
                PNL: float(pnl[PNL]),
                PNL_AMOUNT: float(pnl[PNL_AMOUNT]),
                QUOTE: pnl[QUOTE],
                TRADES_COUNT: pnl[TRADES_COUNT],
                DETAILS: pnl[DETAILS],
            }
            for t, pnl in pnl_history.items()
            # skip 0 value pnl in detailed history
            if not use_detailed_history or (pnl[PNL] or pnl.get(DETAILS, {}).get(SPECIAL_FEES, 0))
        ],
        key=lambda x: x[EXIT_TIME]
    )


def _get_dumped_data(real, simulated, dump_func):
    return [
        dumped
        for dumped in tuple(
            dump_func(order, False)
            for order in real
        ) + tuple(
            dump_func(order, True)
            for order in simulated
        )
        if dumped is not None
    ]


SYMBOL = "symbol"
TYPE = "type"
PRICE = "price"
AMOUNT = "amount"
EXCHANGE = "exchange"
TIME = "time"
DATE = "date"
COST = "cost"
MARKET = "market"
SIMULATED_OR_REAL = "SoR"
ID = "id"
FEE_COST = "fee_cost"
REF_MARKET_COST = "ref_market_cost"
FEE_CURRENCY = "fee_currency"
SIDE = "side"
CONTRACT = "contract"
VALUE = "value"
ENTRY_PRICE = "entry_price"
LIQUIDATION_PRICE = "liquidation_price"
MARGIN = "margin"
UNREALIZED_PNL = "unrealized_pnl"


def _dump_order(order, is_simulated):
    try:
        market = _get_market(order.symbol)
        return {
            SYMBOL: order.symbol,
            TYPE: order.order_type.name.replace("_", " "),
            PRICE: order.origin_price if not order.origin_stop_price else order.origin_stop_price,
            AMOUNT: order.origin_quantity,
            EXCHANGE: order.exchange_manager.exchange.name if order.exchange_manager else '',
            DATE: _convert_timestamp(order.creation_time),
            TIME: order.creation_time,
            COST: _convert_amount(order.exchange_manager, order.total_cost, market) or order.total_cost,
            MARKET: market,
            SIMULATED_OR_REAL: (
                "Simulated" if is_simulated
                else "Virtual" if order.is_self_managed()
                else "Inactive" if not order.is_active
                else "Real"
            ),
            ID: order.order_id,
        }
    except Exception as err:
        logging.get_logger("TradingModel").exception(f"Error when dumping order {err}, order: {order}")
        return None


def get_all_orders_data():
    return _get_dumped_data(*interfaces_util.get_all_open_orders(), _dump_order)


def _convert_amount(exchange_manager, amount, currency):
    multiplier = trading_api.get_currency_ref_market_value(exchange_manager, currency)
    if multiplier is None:
        return None
    return float(multiplier * amount)


def _dump_trade(trade, is_simulated):
    try:
        market = _get_market(trade.symbol)
        return {
            SYMBOL: trade.symbol,
            TYPE: trade.trade_type.name.replace("_", " "),
            PRICE: trade.executed_price,
            AMOUNT: trade.executed_quantity,
            EXCHANGE: trade.exchange_manager.exchange.name if trade.exchange_manager else '',
            DATE: _convert_timestamp(trade.executed_time),
            TIME: trade.executed_time,
            COST: trade.total_cost,
            REF_MARKET_COST: _convert_amount(trade.exchange_manager, trade.total_cost, market),
            MARKET: market,
            FEE_COST: trade.fee.get(trading_enums.FeePropertyColumns.COST.value, 0) if trade.fee else 0,
            FEE_CURRENCY: trade.fee.get(trading_enums.FeePropertyColumns.CURRENCY.value, '') if trade.fee else '',
            SIMULATED_OR_REAL: "Simulated" if is_simulated else "Real",
            ID: trade.trade_id,
        }
    except Exception as err:
        logging.get_logger("TradingModel").exception(f"Error when dumping trade {err}, trade: {trade}")
        return None


def get_all_trades_data(independent_backtesting=None):
    return _get_dumped_data(*interfaces_util.get_trades_history(independent_backtesting=independent_backtesting), _dump_trade)


def _get_market(symbol_str):
    symbol = commons_symbols.parse_symbol(symbol_str)
    return symbol.settlement_asset or symbol.quote


def _dump_position(position, is_simulated):
    try:
        return {
            SYMBOL: position.symbol,
            SIDE: position.side.value,
            CONTRACT: str(position.symbol_contract),
            AMOUNT: position.size,
            VALUE: position.value,
            MARKET: position.currency if position.symbol_contract.is_inverse_contract() else position.market,
            ENTRY_PRICE: position.entry_price,
            LIQUIDATION_PRICE: position.liquidation_price,
            MARGIN: position.margin,
            UNREALIZED_PNL: position.unrealized_pnl,
            EXCHANGE: position.exchange_manager.exchange.name if position.exchange_manager else '',
            SIMULATED_OR_REAL: "Simulated" if is_simulated else "Real",
        }
    except Exception as err:
        logging.get_logger("TradingModel").exception(f"Error when dumping position {err}, position: {position}")
        return None


def get_all_positions_data():
    real, simulated = interfaces_util.get_all_positions()
    return _get_dumped_data(
        (position for position in real if not position.is_idle()),
        (position for position in simulated if not position.is_idle()),
        _dump_position
    )


def clear_exchanges_orders_history(simulated_only=False):
    _run_on_exchange_ids(trading_api.clear_orders_storage_history, simulated_only=simulated_only)
    return {"title": "Cleared orders history"}


def clear_exchanges_trades_history(simulated_only=False):
    _run_on_exchange_ids(trading_api.clear_trades_storage_history, simulated_only=simulated_only)
    return {"title": "Cleared trades history"}


def clear_exchanges_transactions_history(simulated_only=False):
    _run_on_exchange_ids(trading_api.clear_transactions_storage_history, simulated_only=simulated_only)
    return {"title": "Cleared transactions history"}


def clear_exchanges_portfolio_history(simulated_only=False, simulated_portfolio=None):
    # apply updated simulated portfolio to init new historical values on this new portfolio
    simulated_portfolio = simulated_portfolio or \
        interfaces_util.get_edited_config(dict_only=True).get(commons_constants.CONFIG_SIMULATOR, {}).get(
            commons_constants.CONFIG_STARTING_PORTFOLIO, None)
    if simulated_portfolio:
        _sync_run_on_exchange_ids(trading_api.set_simulated_portfolio_initial_config, simulated_only=simulated_only,
                                  portfolio_content=simulated_portfolio)
    _run_on_exchange_ids(trading_api.clear_portfolio_storage_history, simulated_only=simulated_only)
    return {"title": "Cleared portfolio history"}


async def _async_run_on_exchange_ids(coro, exchange_ids, simulated_only, **kwargs):
    for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(exchange_ids):
        if (not simulated_only or trading_api.is_trader_simulated(exchange_manager)) \
                and not trading_api.get_is_backtesting(exchange_manager):
            await coro(exchange_manager, **kwargs)


def _run_on_exchange_ids(coro, simulated_only=False, **kwargs):
    interfaces_util.run_in_bot_main_loop(
        _async_run_on_exchange_ids(coro, trading_api.get_exchange_ids(), simulated_only, **kwargs)
    )


def _sync_run_on_exchange_ids(func, simulated_only=False, **kwargs):
    for exchange_manager in trading_api.get_exchange_managers_from_exchange_ids(trading_api.get_exchange_ids()):
        if (not simulated_only or trading_api.is_trader_simulated(exchange_manager)) \
                and not trading_api.get_is_backtesting(exchange_manager):
            func(exchange_manager, **kwargs)
