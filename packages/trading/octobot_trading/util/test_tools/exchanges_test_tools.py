#  Drakkar-Software OctoBot-Private-Tentacles
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
import asyncio
import decimal
import time
import typing

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.enums as common_enums
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.api as trading_api
import octobot_trading.exchanges as exchanges
import octobot_trading.errors as errors
import octobot_trading.exchange_data as trading_exchange_data
import octobot_tentacles_manager.api as tentacles_manager_api

import octobot_trading.personal_data as personal_data

import octobot_trading.util.test_tools.exchange_data as exchange_data_import


BASE_TIMEOUT = 10


async def create_test_exchange_manager(
        config: dict,
        exchange_name: str,
        is_spot_only: bool = True,
        is_margin: bool = False,
        is_future: bool = False,
        rest_only: bool = False,
        is_real: bool = True,
        is_sandboxed: bool = False,
        ignore_exchange_config: bool = True) -> exchanges.ExchangeManager:
    if ignore_exchange_config:
        # enable exchange name in config
        config[commons_constants.CONFIG_EXCHANGES][exchange_name] = {commons_constants.CONFIG_ENABLED_OPTION: True}

    builder = exchanges.create_exchange_builder_instance(config, exchange_name)
    builder.disable_trading_mode()
    builder.use_tentacles_setup_config(tentacles_manager_api.get_tentacles_setup_config())
    if is_spot_only:
        builder.is_spot_only()
    if is_margin:
        builder.is_margin()
    if is_future:
        builder.is_future()
    if rest_only:
        builder.is_rest_only()
    if is_sandboxed:
        builder.is_sandboxed(is_sandboxed)
    if is_real:
        builder.is_real()
    else:
        builder.is_simulated()
    await builder.build()
    return builder.exchange_manager


async def stop_test_exchange_manager(exchange_manager_instance: exchanges.ExchangeManager):
    trading_api.cancel_ccxt_throttle_task()
    await exchange_manager_instance.stop()
    # let updaters gracefully shutdown
    await asyncio_tools.wait_asyncio_next_cycle()


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def _get_symbol_prices(exchange_manager, symbol, parsed_tf, limit):
    return await exchange_manager.exchange.get_symbol_prices(symbol, parsed_tf, limit=limit)


async def fetch_ohlcv(
    exchange_manager, symbol: str, time_frame: str,
    history_size=1, start_time=0, end_time=0, close_price_only=False,
    include_latest_candle=True
) -> exchange_data_import.MarketDetails:
    parsed_tf = common_enums.TimeFrames(time_frame)
    if start_time == 0:
        ohlcvs = await _get_symbol_prices(exchange_manager, symbol, parsed_tf, history_size)
    else:
        ohlcvs = []
        async for ohlcv in exchanges.get_historical_ohlcv(
            exchange_manager, symbol, parsed_tf, start_time * 1000, (end_time or time.time()) * 1000,
            request_retry_timeout=BASE_TIMEOUT
        ):
            ohlcvs.extend(ohlcv)
    if not include_latest_candle:
        ohlcvs = ohlcvs[:-1]
    return exchange_data_import.MarketDetails(
        symbol=symbol,
        time_frame=time_frame,
        close=[ohlcv[common_enums.PriceIndexes.IND_PRICE_CLOSE.value] for ohlcv in ohlcvs],
        open=[ohlcv[common_enums.PriceIndexes.IND_PRICE_OPEN.value] for ohlcv in ohlcvs] if not close_price_only else [],
        high=[ohlcv[common_enums.PriceIndexes.IND_PRICE_HIGH.value] for ohlcv in ohlcvs] if not close_price_only else [],
        low=[ohlcv[common_enums.PriceIndexes.IND_PRICE_LOW.value] for ohlcv in ohlcvs] if not close_price_only else [],
        volume=[ohlcv[common_enums.PriceIndexes.IND_PRICE_VOL.value] for ohlcv in ohlcvs] if not close_price_only else [],
        time=[ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value] for ohlcv in ohlcvs],
    )


async def _update_ohlcv(
    exchange_manager, symbol: str, time_frame: str, exchange_data: exchange_data_import.ExchangeData,
    history_size=1, start_time=0, end_time=0, close_price_only=False,
    include_latest_candle=True
):
    market = await fetch_ohlcv(
        exchange_manager, symbol, time_frame, history_size, 
        start_time, end_time, close_price_only, include_latest_candle
    )
    exchange_data.markets.append(market)


async def add_symbols_details(
    exchange_manager, symbols: list, time_frame: str, exchange_data: exchange_data_import.ExchangeData,
    history_size=1, start_time=0, end_time=0, close_price_only=False,
    include_latest_candle=True, reload_markets=False,
    market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None
) -> exchange_data_import.ExchangeData:

    await ensure_symbol_markets(exchange_manager, reload=reload_markets, market_filter=market_filter)
    if len(symbols) == 1:
        await _update_ohlcv(
            exchange_manager, next(iter(symbols)), time_frame, exchange_data,
            history_size, start_time, end_time, close_price_only, include_latest_candle
        )
    else:
        await asyncio.gather(*(
            _update_ohlcv(
                exchange_manager, symbol, time_frame, exchange_data,
                history_size, start_time, end_time, close_price_only, include_latest_candle
            )
            for symbol in symbols
        ))
    return exchange_data


async def ensure_symbol_markets(
    exchange_manager,
    reload=False,
    market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None
):
    if reload or not exchange_manager.exchange.connector.has_markets():
        await exchange_manager.exchange.connector.load_symbol_markets(reload=reload, market_filter=market_filter)


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def get_portfolio(exchange_manager, as_float=False, clear_empty=True) -> dict:
    balance = await exchange_manager.exchange.get_balance()
    # filter out 0 values
    return {
        asset: {key: float(val) if as_float else val for key, val in values.items()}  # use float for values
        for asset, values in balance.items()
        if not clear_empty or (clear_empty and any(value for value in values.values()))
    }


def _parse_order_dict(
    exchange_manager, order: dict, force_open_or_pending_creation: bool
) -> typing.Optional[personal_data.Order]:
    if not order:
        return None
    try:
        return personal_data.create_order_instance_from_raw(
            exchange_manager.trader, order, force_open_or_pending_creation=force_open_or_pending_creation
        )
    except Exception as err:
        logging.get_logger("_parse_order_dict").exception(
            err,
            True,
            f"Unexpected error when parsing [{exchange_manager.exchange_name}] "
            f"order ({err} {err.__class__.__name__}), order ignored: {order}"
        )
    return None


def _parse_order_into_dict(
    exchange_manager, order: dict, force_open_or_pending_creation: bool, ignore_unsupported_orders: bool
) -> typing.Optional[dict]:
    if (
        ignore_unsupported_orders and
        order[enums.ExchangeConstantsOrderColumns.TYPE.value] == enums.TradeOrderType.UNSUPPORTED.value
    ):
        logging.get_logger("_parse_order_into_dict").warning(
            f"Ignored unsupported [{exchange_manager.exchange_name}] order: {order}"
        )
        return None
    if parsed_order := _parse_order_dict(exchange_manager, order, force_open_or_pending_creation):
        try:
            return parsed_order.to_dict()
        except AttributeError as err:
            if exchange_manager.trader is None:
                # exchange manager has been stopped, don't continue
                logging.get_logger("_parse_order_dict").error(
                    f"[{exchange_manager.exchange_name}] exchange manager has been stopped, skipping order parsing ({err})"
                )
                raise errors.StoppedExchangeManagerError() from err
            # unexpected error, raise
            raise
        except Exception as err:
            logging.get_logger("_parse_order_dict").exception(
                err,
                True,
                f"Unexpected error when converting [{exchange_manager.exchange_name}] order to dict" 
                f"({err}. {err.__class__.__name__}), order: {order}"
            )
    return None


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def _get_open_orders(exchange_manager, symbol: str, open_orders: list, ignore_unsupported_orders: bool):
    orders = await exchange_manager.exchange.get_open_orders(symbol=symbol)
    for order in orders:
        if order_dict := _parse_order_into_dict(
            exchange_manager, order, True,  ignore_unsupported_orders
        ):
            open_orders.append(order_dict)


async def get_open_orders(
    exchange_manager,
    exchange_data: typing.Optional[exchange_data_import.ExchangeData],
    symbols: list = None,
    ignore_unsupported_orders: bool = True,
) -> list:
    open_orders = []
    symbols = symbols or [market.symbol for market in exchange_data.markets]
    if len(symbols) == 1:
        await _get_open_orders(exchange_manager, next(iter(symbols)), open_orders, ignore_unsupported_orders)
    else:
        # wait all as a not-stopped exchange manager is required to parse orders
        await asyncio_tools.gather_waiting_for_all_before_raising(*(
            _get_open_orders(exchange_manager, symbol, open_orders, ignore_unsupported_orders) for symbol in symbols
        ))
    return open_orders


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def get_order(
    exchange_manager,
    exchange_order_id: str,
    symbol: str,
    order_type: enums.TraderOrderType,
) -> typing.Optional[dict]:
    return await exchange_manager.exchange.get_order(
        exchange_order_id, symbol=symbol, order_type=order_type
    )


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def _get_cancelled_orders(exchange_manager, symbol: str, cancelled_orders: list, ignore_unsupported_orders: bool):
    orders = await exchange_manager.exchange.get_cancelled_orders(symbol=symbol)
    for order in orders:
        if order_dict := _parse_order_into_dict(
            exchange_manager, order, False, ignore_unsupported_orders
        ):
            cancelled_orders.append(order_dict)


async def get_cancelled_orders(
    exchange_manager,
    exchange_data: exchange_data_import.ExchangeData,
    symbols: list = None,
    ignore_unsupported_orders: bool = True,
) -> list:
    cancelled_orders = []
    symbols = symbols or [market.symbol for market in exchange_data.markets]
    if len(symbols) == 1:
        await _get_cancelled_orders(exchange_manager, next(iter(symbols)), cancelled_orders, ignore_unsupported_orders)
    else:
        # wait all as a not-stopped exchange manager is required to parse orders
        await asyncio_tools.gather_waiting_for_all_before_raising(*(
            _get_cancelled_orders(exchange_manager, symbol, cancelled_orders, ignore_unsupported_orders)
            for symbol in symbols
        ))
    return cancelled_orders


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def _get_trades(exchange_manager, symbol: str, trades: list):
    row_trades = await exchange_manager.exchange.get_my_recent_trades(symbol=symbol)
    for raw_trade in row_trades:
        try:
            trades.append(
                personal_data.create_trade_instance_from_raw(exchange_manager.trader, raw_trade).to_dict()
            )
        except Exception as err:
            logging.get_logger("get_trades").exception(
                err,
                True,
                f"Unexpected error when parsing [{exchange_manager.exchange_name}] trade "
                f"({err} {err.__class__.__name__}), trade: {raw_trade}. Ignored trade."
            )


async def get_trades(
    exchange_manager,
    exchange_data: typing.Optional[exchange_data_import.ExchangeData],
    symbols: list = None
) -> list:
    trades = []
    symbols = symbols or [market.symbol for market in exchange_data.markets]
    if len(symbols) == 1:
        await _get_trades(exchange_manager, next(iter(symbols)), trades)
    else:
        # wait all as a not-stopped exchange manager is required to parse trades
        await asyncio_tools.gather_waiting_for_all_before_raising(*(
            _get_trades(exchange_manager, symbol, trades)
            for symbol in symbols
        ))
    return trades


async def _create_order(
    exchange_manager,
    order_dict: dict,
    order_creation_timeout: float,
    price_by_symbol: dict[str, float],
) -> typing.Optional[personal_data.Order]:
    symbol = order_dict[enums.ExchangeConstantsOrderColumns.SYMBOL.value]
    side, order_type = personal_data.parse_order_type(order_dict)
    temp_order = _parse_order_dict(exchange_manager, order_dict, True)
    if temp_order is None:
        logging.get_logger("_create_order").error(f"Unexpected: order can't be created.")
        return None
    order_params = exchange_manager.exchange.get_order_additional_params(temp_order)
    created_order = await exchange_manager.exchange.create_order(
        order_type,
        symbol,
        decimal.Decimal(str(order_dict[enums.ExchangeConstantsOrderColumns.AMOUNT.value])),
        price=decimal.Decimal(str(order_dict[enums.ExchangeConstantsOrderColumns.PRICE.value])),
        side=side,
        current_price=price_by_symbol[symbol],
        reduce_only=order_dict[enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value],
        params=order_params
    )
    # is private, to use in tests context only
    order = _parse_order_dict(exchange_manager, created_order, True)
    if order is None:
        logging.get_logger("_create_order").warning(
            f"Unexpected: [{exchange_manager.exchange_name}] order hasn't been created (order: {order_dict})."
        )
        return order
    if order.status is enums.OrderStatus.PENDING_CREATION and order_creation_timeout > 0:
        try:
            return await wait_for_other_status(order, order_creation_timeout)
        except TimeoutError as err:
            logging.get_logger(order.get_logger_name()).error(f"Created order can't be fetched: {err}")
            return None
    return order


async def create_orders(
    exchange_manager,
    orders: list,
    order_creation_timeout: float,
    price_by_symbol: dict[str, float],
) -> list:
    if len(orders) == 1:
        return [
            await _create_order(exchange_manager, next(iter(orders)), order_creation_timeout, price_by_symbol)
        ]
    # wait all as a not-stopped exchange manager is required to parse orders
    return await asyncio_tools.gather_waiting_for_all_before_raising(*(
        _create_order(exchange_manager, order_dict, order_creation_timeout, price_by_symbol)
        for order_dict in orders
    ))


async def wait_for_other_status(order: personal_data.Order, timeout) -> personal_data.Order:
    t0 = time.time()
    iterations = 0
    origin_status = order.status.value
    while time.time() - t0 < timeout:
        raw_order = await order.exchange_manager.exchange.get_order(
            order.exchange_order_id, order.symbol, order_type=order.order_type
        )
        iterations += 1
        if raw_order is not None and raw_order[enums.ExchangeConstantsOrderColumns.STATUS.value] != origin_status:
            logging.get_logger(order.get_logger_name()).info(
                f"Order fetched with status different from {origin_status} after {iterations} "
                f"iterations and {round(time.time() - t0)}s"
            )
            if parsed_order := _parse_order_dict(order.exchange_manager, raw_order, False):
                return parsed_order
        if time.time() - t0 + constants.CREATED_ORDER_FORCED_UPDATE_PERIOD >= timeout:
            break
        await asyncio.sleep(constants.CREATED_ORDER_FORCED_UPDATE_PERIOD)
    raise TimeoutError(f"Order was not found with another status than {origin_status} within {timeout} seconds")


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def get_positions(
    exchange_manager,
    exchange_data: typing.Optional[exchange_data_import.ExchangeData],
    symbols: list = None
) -> list[dict]:
    symbols = symbols or [market.symbol for market in exchange_data.markets]
    if not symbols:
        # nothing to fetch
        return []
    raw_positions = await exchange_manager.exchange.get_positions(symbols=symbols)
    # initialize relevant contracts first as they might be waited for
    trading_exchange_data.update_contracts_from_positions(exchange_manager, raw_positions)
    dict_positions = []
    for raw_position in raw_positions:
        try:
            dict_positions.append(
                personal_data.create_position_instance_from_raw(
                    exchange_manager.trader, raw_position
                ).to_dict()
            )
        except Exception as err:
            logging.get_logger("get_positions").exception(
                err,
                True,
                f"Unexpected error when parsing [{exchange_manager.exchange_name}] position"
                f"({err}. {err.__class__.__name__}), position: {raw_position}. Ignored position."
            )
    return dict_positions


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def get_all_currencies_price_ticker(exchange_manager, **kwargs) -> dict[str, dict]:
    return await exchange_manager.exchange.get_all_currencies_price_ticker(**kwargs)


@exchanges.retried_failed_network_request(
    attempts=constants.TOOLS_FAILED_NETWORK_REQUEST_ATTEMPTS,
    delay=constants.TOOLS_FAILED_NETWORK_REQUEST_RETRY_DELAY
)
async def get_price_ticker(exchange_manager, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
    return await exchange_manager.exchange.get_price_ticker(symbol, **kwargs)
