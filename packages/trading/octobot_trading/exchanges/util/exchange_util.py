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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import contextlib
import typing
import ccxt
import trading_backend

import octobot_commons.logging as logging
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.symbols as common_symbols
import octobot_commons.tentacles_management as tentacles_management

import octobot_tentacles_manager.api as api

import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.exchanges.types as exchanges_types
import octobot_trading.exchanges.implementations as exchanges_implementations
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.exchange_details as exchange_details
import octobot_trading.exchanges.exchange_builder as exchange_builder


def get_rest_exchange_class(
    exchange_name: str, tentacles_setup_config, exchange_config_by_exchange: typing.Optional[dict[str, dict]]
):
    return search_exchange_class_from_exchange_name(
        exchanges_types.RestExchange, exchange_name, tentacles_setup_config, exchange_config_by_exchange
    )


def search_exchange_class_from_exchange_name(
    exchange_class, exchange_name, tentacles_setup_config, exchange_config_by_exchange, enable_default=False
):
    exchange_class = get_exchange_class_from_name(
        exchange_class, exchange_name,  tentacles_setup_config, exchange_config_by_exchange, enable_default
    )
    if exchange_class is not None:
        return exchange_class
    if enable_default:
        return None

    logging.get_logger("ExchangeUtil").debug(f"No specific exchange implementation for {exchange_name} found, "
                                             f"using a default one.")
    children_classes = tentacles_management.get_all_classes_from_parent(exchanges_implementations.DefaultRestExchange)
    if children_classes:
        # last one is the most advanced one
        return children_classes[-1]
    # fallback to DefaultRestExchange
    return exchanges_implementations.DefaultRestExchange


def get_exchange_class_from_name(
    exchange_parent_class, exchange_name, tentacles_setup_config, exchange_config_by_exchange,
    enable_default_implementation, strict_name_matching=False
):
    for exchange_candidate in tentacles_management.get_all_classes_from_parent(exchange_parent_class):
        try:
            if _is_exchange_candidate_matching(
                exchange_candidate, exchange_name, tentacles_setup_config,
                enable_default_implementation=enable_default_implementation
            ) and (not strict_name_matching or exchange_candidate.get_name() == exchange_name):
                return exchange_candidate
        except NotImplementedError:
            # A subclass of AbstractExchange will raise a NotImplementedError when calling its get_name() method
            # Here we are returning only a subclass that matches the expected name
            # Only Exchange Tentacles are implementing get_name() to specify the related exchange
            # As we are searching for an exchange_type specific subclass
            # We should ignore classes that raises NotImplementedError
            pass
    auto_filled_exchanges = _get_auto_filled_exchanges(tentacles_setup_config, exchange_config_by_exchange)
    if exchange_name in auto_filled_exchanges:
        return auto_filled_exchanges[exchange_name][0]
    return None


def _get_auto_filled_exchanges(tentacles_setup_config, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
    auto_filled_exchanges = {}
    for exchange_candidate in _get_auto_filled_exchanges_tentacles():
        if tentacles_setup_config is None:
            # tentacles_setup_config is required for auto-filled exchanges
            continue
        config = exchange_config_by_exchange[exchange_candidate.get_name()] if (
            exchange_config_by_exchange and exchange_candidate.get_name() in exchange_config_by_exchange
        ) else api.get_tentacle_config(
            tentacles_setup_config, exchange_candidate
        )
        for exchange_name in exchange_candidate.supported_autofill_exchanges(config):
            auto_filled_exchanges[exchange_name] = (exchange_candidate, config)
    return auto_filled_exchanges


def get_auto_filled_exchange_names(tentacles_setup_config):
    return list(_get_auto_filled_exchanges(tentacles_setup_config, None))


def _get_auto_filled_exchanges_tentacles():
    return [
        exchange_candidate
        for exchange_candidate in tentacles_management.get_all_classes_from_parent(exchanges_types.RestExchange)
        if exchange_candidate.HAS_FETCHED_DETAILS
    ]


async def get_exchange_details(
    exchange_name, is_autofilled, tentacles_setup_config, aiohttp_session
) -> exchange_details.ExchangeDetails:
    if is_autofilled:
        auto_filled_exchanges = _get_auto_filled_exchanges(tentacles_setup_config, None)
        if exchange_name in auto_filled_exchanges:
            return await auto_filled_exchanges[exchange_name][0].get_autofilled_exchange_details(
                aiohttp_session, auto_filled_exchanges[exchange_name][1], exchange_name
            )
    try:
        exchange = ccxt_client_util.ccxt_exchange_class_factory(exchange_name)()
        return exchange_details.ExchangeDetails(
            exchange.id,
            exchange.name,
            exchange.urls[ccxt_enums.ExchangeColumns.WEBSITE.value],
            exchange.urls[ccxt_enums.ExchangeColumns.API.value],
            exchange.urls[ccxt_enums.ExchangeColumns.LOGO_URL.value],
            False,
        )
    except AttributeError as err:
        raise KeyError from err


def _is_exchange_candidate_matching(
    exchange_candidate, exchange_name, tentacles_setup_config, enable_default_implementation=False
):
    return not exchange_candidate.is_simulated_exchange() and \
           (not exchange_candidate.is_default_exchange() or enable_default_implementation) and \
           exchange_candidate.is_supporting_exchange(exchange_name) and \
           (tentacles_setup_config is None or
            api.is_tentacle_activated_in_tentacles_setup_config(tentacles_setup_config,
                                                                exchange_candidate.__name__))


def get_order_side(order_type):
    return enums.TradeOrderSide.BUY.value if order_type in (enums.TraderOrderType.BUY_LIMIT,
                                                            enums.TraderOrderType.BUY_MARKET) \
        else enums.TradeOrderSide.SELL.value


def log_time_sync_error(logger, exchange_name, error, caller_name):
    logger.error(
        f"{_get_time_sync_error_message(exchange_name, caller_name)} Error: {error}")


def _get_docs_url():
    try:
        import octobot.constants
        return octobot.constants.OCTOBOT_DOCS_URL
    except ImportError:
        return "https://www.octobot.cloud/en/guides"


def _get_exchanges_docs_url():
    try:
        import octobot.constants
        return octobot.constants.EXCHANGES_DOCS_URL
    except ImportError:
        return "https://www.octobot.cloud/en/guides/exchanges"


def _get_time_sync_error_message(exchange_name, caller_name):
    return f"Time synchronization error when calling {caller_name} on {exchange_name.capitalize()}. " \
        f"To fix this, please synchronize your computer's clock. See " \
        f"{_get_docs_url()}/octobot-installation/troubleshoot#time-synchronization"


def get_partners_explanation_message():
    return f"More info on partner exchanges on {_get_exchanges_docs_url()}#partner-exchanges---support-octobot"


def _get_minimal_exchange_config(exchange_name, exchange_config):
    return {
        common_constants.CONFIG_EXCHANGES: {
            exchange_name: exchange_config
        },
        common_constants.CONFIG_TRADER: {
            common_constants.CONFIG_ENABLED_OPTION: False
        },
        common_constants.CONFIG_SIMULATOR: {
            common_constants.CONFIG_ENABLED_OPTION: False
        },
        common_constants.CONFIG_TIME_FRAME: [],
        common_constants.CONFIG_CRYPTO_CURRENCIES: []
    }


def get_enabled_exchanges(config):
    return [
        exchange_name
        for exchange_name in config[common_constants.CONFIG_EXCHANGES]
        if config[common_constants.CONFIG_EXCHANGES][exchange_name].get(
                common_constants.CONFIG_ENABLED_OPTION, True
        )
    ]


@contextlib.asynccontextmanager
async def get_local_exchange_manager(
    exchange_name: str, exchange_config: dict, tentacles_setup_config,
    is_sandboxed: bool, ignore_config=False, builder=None, use_cached_markets=True,
    is_broker_enabled: bool = False, exchange_config_by_exchange: typing.Optional[dict[str, dict]] = None,
    disable_unauth_retry: bool = False,
    market_filter: typing.Union[None, typing.Callable[[dict], bool]] = None,
    rest_exchange: typing.Optional[exchanges_types.RestExchange] = None,
    leave_rest_exchange_open: bool = False,
):
    exchange_type = exchange_config.get(common_constants.CONFIG_EXCHANGE_TYPE, get_default_exchange_type(exchange_name))
    builder = builder or exchange_builder.ExchangeBuilder(
        _get_minimal_exchange_config(exchange_name, exchange_config),
        exchange_name
    )
    exchange_manager = await builder.use_tentacles_setup_config(tentacles_setup_config) \
        .is_checking_credentials(False) \
        .disable_unauth_retry(disable_unauth_retry) \
        .is_sandboxed(is_sandboxed) \
        .is_using_exchange_type(exchange_type) \
        .use_exchange_config_by_exchange(exchange_config_by_exchange) \
        .is_exchange_only() \
        .is_rest_only() \
        .is_broker_enabled(is_broker_enabled) \
        .use_cached_markets(use_cached_markets) \
        .use_market_filter(market_filter) \
        .set_rest_exchange(rest_exchange) \
        .leave_rest_exchange_open(leave_rest_exchange_open) \
        .is_ignoring_config(ignore_config) \
        .disable_trading_mode() \
        .build()
    try:
        with exchange_error_translator(exchange_manager):
            yield exchange_manager
    finally:
        # do not log stopping message
        logger = exchange_manager.exchange.connector.logger
        logger.disable(True)
        builder.clear()
        await exchange_manager.stop(enable_logs=False)
        logger.disable(False)


@contextlib.contextmanager
def exchange_error_translator(exchange_manager):
    try:
        yield
    except ccxt.ExchangeError as err:
        # convert permission and compliancy errors while the exchange manager still exists and can be used
        if exchange_manager.exchange.is_api_permission_error(err):
            raise errors.AuthenticationError(f"{err} ({err.__class__})") from err
        if exchange_manager.exchange.is_exchange_rules_compliancy_error(err):
            raise errors.ExchangeCompliancyError(f"{err} ({err.__class__})") from err
        # default raise
        raise


async def is_compatible_account(exchange_name: str, exchange_config: dict, tentacles_setup_config, is_sandboxed: bool) \
        -> (bool, bool, str):
    """
    Returns details regarding the compatibility of the account given in parameters
    :return: (True if compatible, True if successful login, error explanation if any)
    """
    async with get_local_exchange_manager(
        exchange_name, exchange_config, tentacles_setup_config, is_sandboxed, ignore_config=False,
        disable_unauth_retry=True,
    ) as local_exchange_manager:
        backend = trading_backend.exchange_factory.create_exchange_backend(local_exchange_manager.exchange)
        try:
            is_compatible, error = await backend.is_valid_account(always_check_key_rights=True)
            if not local_exchange_manager.is_spot_only:
                message = f"Future trading on {exchange_name.capitalize()} requires a supporting account. {error}." \
                          f"Please create a new {exchange_name.capitalize()} account to use futures trading. "
                # only ensure compatibility for non spot trading
                return is_compatible, True, message if error else error
            else:
                # auth didn't fail, spot trading is always allowed
                return True, True, None
        except trading_backend.TimeSyncError:
            return False, False, _get_time_sync_error_message(exchange_name, "backend.is_valid_account")
        except trading_backend.APIKeyPermissionsError as err:
            return False, False, f"Please update your API Key permissions: {err}"
        except trading_backend.APIKeyIPWhitelistError as err:
            return False, False, f"Please update your API Key IP whitelist: {err}"
        except trading_backend.UnexpectedError as err:
            return False, False, f"Impossible to check API key: {err}"
        except trading_backend.ExchangeAuthError:
            message = f"Invalid {exchange_name.capitalize()} authentication details"
            if is_sandboxed:
                message = f"{message}. Warning: exchange sandbox is enabled, " \
                          f"this means that OctoBot is connecting to the testnet/sandbox version of " \
                          f"{exchange_name.capitalize()} to trade and validate your api key. " \
                          f"Disable sandbox in your accounts configuration if this is not intended."
            return False, False, message
        except (AttributeError, Exception) as e:
            return True, False, f"Error when loading exchange account: {e}"


async def get_historical_ohlcv(
    local_exchange_manager, symbol, time_frame, start_time, end_time,
    request_retry_timeout=constants.HISTORICAL_CANDLES_FETCH_DEFAULT_TIMEOUT
):
    """
    Async generator, use as follows:
        async for candles in get_historical_ohlcv(exchange_manager, pair, time_frame, start_time, end_time):
            # candles stuff
    WARNING: start_time and end_time are inclusive boundaries and should be milliseconds timestamps
    request_retry_timeout is a timer in seconds to keep retrying to fetch failed candle requests before giving up
    """
    reached_max = False
    time_frame_sec = common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
    time_frame_msec = time_frame_sec * common_constants.MSECONDS_TO_SECONDS
    exchange_time = local_exchange_manager.exchange.get_exchange_current_time()
    max_theoretical_time = exchange_time - exchange_time % time_frame_sec
    while start_time < end_time and not reached_max:
        candles = await local_exchange_manager.exchange.retry_till_success(
            request_retry_timeout,
            local_exchange_manager.exchange.get_symbol_prices,
            symbol, time_frame, since=int(start_time)
        )
        if candles:
            while candles and candles[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value] * 1000 > end_time:
                candles.pop(-1)
                reached_max = True
            if candles:
                if candles[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value] >= max_theoretical_time:
                    reached_max = True
                yield candles
                start_time = candles[-1][common_enums.PriceIndexes.IND_PRICE_TIME.value] * 1000
                # avoid fetching the last element twice
                start_time += 1
            else:
                reached_max = True
        elif local_exchange_manager.exchange.MAX_FETCHED_OHLCV_COUNT:
            # history needs to be fetched step by step
            start_time = start_time + (time_frame_msec * local_exchange_manager.exchange.MAX_FETCHED_OHLCV_COUNT)
        else:
            reached_max = True


def get_exchange_type(exchange_manager_instance):
    if exchange_manager_instance.is_spot_only:
        return enums.ExchangeTypes.SPOT
    if exchange_manager_instance.is_future:
        return enums.ExchangeTypes.FUTURE
    if exchange_manager_instance.is_margin:
        return enums.ExchangeTypes.MARGIN
    if exchange_manager_instance.is_option:
        return enums.ExchangeTypes.OPTION
    return enums.ExchangeTypes.SPOT


def get_default_exchange_type(exchange_name):
    if exchange_name in constants.DEFAULT_FUTURE_EXCHANGES:
        return common_constants.CONFIG_EXCHANGE_FUTURE
    return common_constants.DEFAULT_EXCHANGE_TYPE


def get_supported_exchange_types(exchange_name, tentacles_setup_config, exchange_config_by_exchange=None):
    exchange_class = get_exchange_class_from_name(
        exchanges_types.RestExchange, exchange_name, tentacles_setup_config,
        exchange_config_by_exchange, False, strict_name_matching=True
    )
    if exchange_class is None:
        # default
        return [enums.ExchangeTypes.SPOT]
    return exchange_class.get_supported_exchange_types()


def update_raw_order_from_raw_trade(order_to_update, raw_trade):
    order_to_update[enums.ExchangeConstantsOrderColumns.INFO.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.INFO.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.ORDER.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.SYMBOL.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.SYMBOL.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.TYPE.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.TYPE.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.AMOUNT.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.AMOUNT.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.DATETIME.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.DATETIME.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.SIDE.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.SIDE.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.PRICE.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.PRICE.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] = order_to_update.get(
        enums.ExchangeConstantsOrderColumns.TIMESTAMP.value,
        raw_trade.get(enums.ExchangeConstantsOrderColumns.TIMESTAMP.value))
    order_to_update[enums.ExchangeConstantsOrderColumns.STATUS.value] = enums.OrderStatus.FILLED.value
    order_to_update[enums.ExchangeConstantsOrderColumns.FILLED.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.AMOUNT.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.COST.value] = raw_trade.get(
        enums.ExchangeConstantsOrderColumns.COST.value)
    order_to_update[enums.ExchangeConstantsOrderColumns.REMAINING.value] = 0
    order_to_update[
        enums.ExchangeConstantsOrderColumns.FEE.value
    ] = raw_trade.get(enums.ExchangeConstantsOrderColumns.FEE.value)
    order_to_update[
        enums.ExchangeConstantsOrderColumns.TAG.value
    ] = raw_trade.get(enums.ExchangeConstantsOrderColumns.TAG.value)
    order_to_update[
        enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value
    ] = raw_trade.get(enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value, False)
    return order_to_update


def is_missing_trading_fees(raw_order):
    try:
        return (
            raw_order is not None
            and raw_order[enums.ExchangeConstantsOrderColumns.STATUS.value] in (
                    enums.OrderStatus.CLOSED.value,
                    enums.OrderStatus.FILLED.value,
            )
            and (
                raw_order[enums.ExchangeConstantsOrderColumns.FEE.value] is None
                or raw_order[enums.ExchangeConstantsOrderColumns.FEE.value][
                    enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value
                ] is None
            )
        )
    except KeyError:
        return True


def apply_trades_fees(raw_order, raw_trades_by_exchange_order_id):
    exchange_order_id = raw_order[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
    if exchange_order_id in raw_trades_by_exchange_order_id and raw_trades_by_exchange_order_id[exchange_order_id]:
        order_fee = raw_trades_by_exchange_order_id[exchange_order_id][0][enums.ExchangeConstantsOrderColumns.FEE.value]
        # add each order's trades fee
        for trade in raw_trades_by_exchange_order_id[exchange_order_id][1:]:
            order_fee[enums.FeePropertyColumns.COST.value] += \
                trade[enums.ExchangeConstantsOrderColumns.FEE.value][enums.FeePropertyColumns.COST.value]
            order_fee[enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value] += \
                trade[enums.ExchangeConstantsOrderColumns.FEE.value][
                    enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value]
        raw_order[enums.ExchangeConstantsOrderColumns.FEE.value] = order_fee


def get_common_traded_quote(exchange_manager) -> typing.Union[str, None]:
    quote = None
    for symbol in exchange_manager.exchange_config.traded_symbols:
        if quote is None:
            quote = symbol.quote
        elif quote != symbol.quote:
            return None
    return quote


def get_associated_symbol(exchange_manager, asset: str, target_asset: str) -> (typing.Union[str, None], bool):
    symbol = common_symbols.merge_currencies(asset, target_asset)
    is_reversed_symbol = False
    if symbol not in exchange_manager.client_symbols:
        # try reversed
        reversed_symbol = common_symbols.merge_currencies(target_asset, asset)
        if reversed_symbol not in exchange_manager.client_symbols:
            return None, is_reversed_symbol
        symbol = reversed_symbol
        is_reversed_symbol = True
    return symbol, is_reversed_symbol


def is_error_on_this_type(error: BaseException, descriptions: typing.List[typing.Iterable[str]]) -> bool:
    lower_error = str(error).lower()
    for identifiers in descriptions:
        if all(identifier in lower_error for identifier in identifiers):
            return True
    return False
