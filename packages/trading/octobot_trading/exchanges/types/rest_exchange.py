# pylint: disable=W0706
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
import contextlib
import decimal
import typing
import copy
import asyncio
# import traceback      # uncomment for debugging in tests
# import sys        # uncomment for debugging in tests

import ccxt.async_support as ccxt
import octobot_commons.enums as commons_enums
import octobot_commons.tree as commons_tree
import octobot_commons.constants as commons_constants
import octobot_commons.html_util as html_util
import octobot_commons.number_util as number_util

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.exchanges.util as exchanges_util
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
from octobot_trading.enums import ExchangeConstantsOrderColumns as ecoc
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchange_data.contracts as contracts
import octobot_trading.personal_data.orders as orders



def fetching_orders_request(f):
    async def fetching_orders_request_wrapper(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        fetched_orders = await f(self, symbol=symbol, since=since, limit=limit, **kwargs)
        if ccxt_enums.OrderFetchParams.STOP.value not in kwargs and self.fetch_stop_order_in_different_request(symbol):
            # all order types need to be fetched and stop orders need to be fetched in a separate request
            stop_orders = await f(self, symbol=symbol, since=since, limit=limit, **{
                **kwargs, **{ccxt_enums.OrderFetchParams.STOP.value: True}
            })
            fetched_orders.extend(stop_orders)
        return await self.ensure_orders_completeness(
            fetched_orders, symbol, since=since, limit=limit, **kwargs
        )
    return fetching_orders_request_wrapper



class RestExchange(abstract_exchange.AbstractExchange):
    ORDER_NON_EMPTY_FIELDS = [ecoc.EXCHANGE_ID.value, ecoc.TIMESTAMP.value, ecoc.SYMBOL.value, ecoc.TYPE.value,
                              ecoc.SIDE.value, ecoc.PRICE.value, ecoc.AMOUNT.value, ecoc.STATUS.value]
    ORDER_REQUIRED_FIELDS = ORDER_NON_EMPTY_FIELDS + [ecoc.REMAINING.value]
    PRINT_DEBUG_LOGS = False
    FIX_MARKET_STATUS = False  # set True when get_fixed_market_status should be called when calling get_market_status
    # set True when get_fixed_market_status should be remove price limits (when limits are invalid)
    REMOVE_MARKET_STATUS_PRICE_LIMITS = False
    # set True when get_fixed_market_status should adapt amounts for contract size
    # (amounts are in not kept as contract size with OctoBot)
    ADAPT_MARKET_STATUS_FOR_CONTRACT_SIZE = False
    # set True when disabled symbols should still be considered (ex: mexc with its temporary api trading disabled symbols)
    INCLUDE_DISABLED_SYMBOLS_IN_AVAILABLE_SYMBOLS = False
    # set True when create_market_buy_order_with_cost should be used to create buy market orders
    # (useful to predict the exact spent amount)
    ENABLE_SPOT_BUY_MARKET_WITH_COST = False
    REQUIRE_ORDER_FEES_FROM_TRADES = False  # set True when get_order is not giving fees on closed orders and fees
    # should be fetched using recent trades.
    REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES = False  # set True when get_closed_orders is not supported
    ALLOW_TRADES_FROM_CLOSED_ORDERS = False  # set True when get_my_recent_trades should use get_closed_orders
    DUMP_INCOMPLETE_LAST_CANDLE = False  # set True in tentacle when the exchange can return incomplete last candles
    # Set True when exchange is not returning empty position details when fetching a position with a specified symbol
    # Exchange will then fallback to self.get_mocked_empty_position when having get_position returning None
    REQUIRES_MOCKED_EMPTY_POSITION = False
    # set True when get_positions() is not returning empty positions and should use get_position() instead
    REQUIRES_SYMBOL_FOR_EMPTY_POSITION = False
    SUPPORTS_SET_MARGIN_TYPE = True  # set False when there is no API to switch between cross and isolated margin types
    # set False when the exchange refuses to change margin type when an associated position is open
    SUPPORTS_SET_MARGIN_TYPE_ON_OPEN_POSITIONS = True
    EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = False  # set True when get_order() can return None
    # (order not found) when orders are being created on exchange and are not fully processed on the exchange side.
    ALWAYS_REQUIRES_AUTHENTICATION = False  # set True when even normally public apis require authentication
    # set True when even loading markets can make auth calls when creds are set
    CAN_MAKE_AUTHENTICATED_REQUESTS_WHEN_LOADING_MARKETS = False
    HAS_FETCHED_DETAILS = False  # set True when this exchange details (urls etc) have to be fetched before
    # starting the exchange
    IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH = False    # set True when the exchange is known for not returning any
    # candle when no traded happened during a candle time frame. In this case, a missing candle in backtesting won't
    # trigger an error
    # Name of the price param to give ccxt to edit a stop loss
    STOP_LOSS_EDIT_PRICE_PARAM = ccxt_enums.ExchangeOrderCCXTUnifiedParams.STOP_LOSS_PRICE.value
    STOP_LOSS_CREATE_PRICE_PARAM = ccxt_enums.ExchangeOrderCCXTUnifiedParams.STOP_LOSS_PRICE.value
    WITHDRAW_NETWORK_PARAM_KEY = "network" # key to use in params to specify the network to withdraw to
    """
    RestExchange is using its exchange connector to interact with the exchange.
    It should be used regardless of the exchange or the exchange library (ccxt or other)
    Always take and returns octobot formatted data and errors
    Is used request regardless of the trading type (spot / future / other)

    Is extended in exchange tentacles to define custom behaviors or exchange adapter (override of get_adapter_class)
    """
    # Mark price params
    MARK_PRICE_IN_POSITION = False
    MARK_PRICE_IN_TICKER = False

    # OHLCV params
    # set when the exchange returns nothing when fetching historical candles with a too early start time
    # (will iterate historical OHLCV requests over this window)
    MAX_FETCHED_OHLCV_COUNT = None

    # Funding rate params
    FUNDING_WITH_MARK_PRICE = False
    FUNDING_IN_TICKER = False

    # Set when order cost is not (yet) accurately computed for a given exchange
    MAX_INCREASED_POSITION_QUANTITY_MULTIPLIER = constants.ONE

    SUPPORT_FETCHING_CANCELLED_ORDERS = True
    # Set True when get_open_order() can return outdated orders (cancelled or not yet created)
    CAN_HAVE_DELAYED_OPEN_ORDERS = False
    # Set True when get_cancelled_order() can return outdated open orders
    CAN_HAVE_DELAYED_CANCELLED_ORDERS = False
    # Set True when the "limit" param when fetching order books is taken into account
    SUPPORTS_CUSTOM_LIMIT_ORDER_BOOK_FETCH = False

    # set True when fetch_tickers can sometimes miss symbols. In this case, the connector will try to fix it
    CAN_MISS_TICKERS_IN_ALL_TICKERS = True

    # text content of errors due to orders not found errors
    EXCHANGE_ORDER_NOT_FOUND_ERRORS: typing.List[typing.Iterable[str]] = []
    # when ccxt is raising ccxt.ExchangeError instead of ccxt.AuthenticationError on api key permissions issue
    # text content of errors due to api key permissions issues
    EXCHANGE_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to account compliancy issues
    EXCHANGE_COMPLIANCY_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to exchange internal synch (like when portfolio is not yet up to date after a trade)
    EXCHANGE_INTERNAL_SYNC_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to missing fnuds when creating an order (when not identified as such by ccxt)
    EXCHANGE_MISSING_FUNDS_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to exchange local account permissions (ex: accounts from X country can't trade XYZ)
    # text content of errors due to traded assets for account
    EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to unhandled authentication issues
    EXCHANGE_AUTHENTICATION_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to unhandled IP white list issues
    EXCHANGE_IP_WHITELIST_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to a closed position on the exchange. Relevant for reduce-only orders
    EXCHANGE_CLOSED_POSITION_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to an order that would immediately trigger if created. Relevant for stop losses
    EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to an order that can't be cancelled on exchange (because filled or already cancelled)
    EXCHANGE_ORDER_UNCANCELLABLE_ERRORS: typing.List[typing.Iterable[str]] = []
    # text content of errors due to max open orders being reached
    EXCHANGE_MAX_ORDERS_FOR_MARKET_REACHED_ERRORS: typing.List[typing.Iterable[str]] = []
    # set when the exchange can allow users to pay fees in a custom currency (ex: BNB on binance)
    LOCAL_FEES_CURRENCIES: typing.List[str] = []

    # Set False in case this exchange's markets should never be filtered as soon as they are fetched
    # Therefore overriding the env var value for this exchange
    FETCH_MIN_EXCHANGE_MARKETS = constants.FETCH_MIN_EXCHANGE_MARKETS

    ADJUST_FOR_TIME_DIFFERENCE = False  # set True when the client needs to adjust its requests for time difference with the server

    DEFAULT_CONNECTOR_CLASS = ccxt_connector.CCXTConnector

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        super().__init__(config, exchange_manager, exchange_config_by_exchange)
        if self.HAS_FETCHED_DETAILS:
            self._apply_fetched_details(config, exchange_manager)
        self.connector = self._create_connector(config, exchange_manager, connector_class)
        self.pair_contracts: dict[str, contracts.MarginContract] = {}

    def _create_connector(self, config, exchange_manager, connector_class):
        to_create_connector_class = connector_class or self.DEFAULT_CONNECTOR_CLASS
        extended_additional_config = to_create_connector_class.get_extended_additional_connector_config(
            self.get_additional_connector_config() or {},
        )
        return to_create_connector_class(
            config,
            exchange_manager,
            adapter_class=self.get_adapter_class(),
            additional_config=extended_additional_config,
            rest_name=self.get_rest_name(self.exchange_manager),
            force_auth=self.requires_authentication(self.tentacle_config, None, None),
        )

    @classmethod
    def requires_authentication(
        cls, 
        tentacle_config: typing.Optional[dict], 
        tentacles_setup_config, 
        exchange_config_by_exchange: typing.Optional[dict[str, dict]]
    ) -> bool:
        if tentacle_config is None:
            tentacle_config = {}
            if exchange_config_by_exchange and (
                _tencles_config := cls.get_tentacle_config(exchange_config_by_exchange)
            ):
                # copy to avoid editing the original tentacle config in load_user_inputs_from_class
                tentacle_config = copy.copy(_tencles_config)
            if tentacle_config and tentacles_setup_config is not None:
                cls.load_user_inputs_from_class(tentacles_setup_config, tentacle_config)
        return tentacle_config.get(commons_constants.CONFIG_FORCE_AUTHENTICATION, cls.ALWAYS_REQUIRES_AUTHENTICATION)

    def requires_authentication_for_this_configuration_only(self) -> bool:
        return (
            self.requires_authentication(self.tentacle_config, None, None) 
            and not self.ALWAYS_REQUIRES_AUTHENTICATION
        )

    async def initialize_impl(self):
        await self.connector.initialize()
        self.symbols = self.connector.symbols
        self.time_frames = self.connector.time_frames

    async def stop(self) -> None:
        await self.connector.stop()
        self.exchange_manager = None # type: ignore

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        return cls.get_name() == exchange_candidate_name

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types. Override if necessary
        """
        return [enums.ExchangeTypes.SPOT]

    @classmethod
    def get_rest_name(cls, exchange_manager):
        return exchange_manager.exchange_class_string

    def get_associated_websocket_exchange_name(self):
        return self.exchange_manager.exchange_name

    def get_adapter_class(self):
        # Override in tentacles when using a custom adapter
        return None

    def fetch_stop_order_in_different_request(self, symbol: str) -> bool:
        # Override in tentacles when stop orders need to be fetched in a separate request from CCXT
        return False

    async def create_order(self, order_type: enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) -> typing.Optional[dict]:
        if self.exchange_manager.is_future:
            # on futures exchange expects, quantity in contracts: convert quantity into contracts
            quantity = quantity / self.get_contract_size(symbol)
        async with self._order_operation(order_type, symbol, quantity, price, stop_price):
            with self.creating_order(side, symbol, quantity, price):
                created_order = await self._create_order_with_retry(
                    order_type=order_type, symbol=symbol, quantity=quantity, price=price,
                    stop_price=stop_price, side=side, current_price=current_price,
                    reduce_only=reduce_only, params=params)
                self.logger.debug(f"Created order: {created_order}")
                return await self._verify_order(created_order, order_type, symbol, price, quantity, side)
        return None

    async def edit_order(self, exchange_order_id: str, order_type: enums.TraderOrderType, symbol: str,
                         quantity: decimal.Decimal, price: decimal.Decimal,
                         stop_price: decimal.Decimal = None, side: enums.TradeOrderSide = None,
                         current_price: decimal.Decimal = None,
                         params: dict = None):
        # Note: on most exchange, this implementation will just replace the order by cancelling the one
        # which id is given and create a new one
        if self.exchange_manager.is_future:
            # on futures exchange expects, quantity in contracts: convert quantity into contracts
            quantity = quantity / self.get_contract_size(symbol)
        async with self._order_operation(order_type, symbol, quantity, price, stop_price):
            float_quantity = float(quantity)
            float_price = float(price)
            float_stop_price = None if stop_price is None else float(stop_price)
            float_current_price = None if current_price is None else float(current_price)
            side = None if side is None else side.value
            params = {} if params is None else params
            params.update(self.exchange_manager.exchange_backend.get_orders_parameters(None))
            edited_order = await self._edit_order(exchange_order_id, order_type, symbol, quantity=float_quantity,
                                                  price=float_price, stop_price=float_stop_price, side=side,
                                                  current_price=float_current_price, params=params)
            order = await self._verify_order(edited_order, order_type, symbol, price, quantity, side)
            return order
        return None

    async def _edit_order(self, exchange_order_id: str, order_type: enums.TraderOrderType, symbol: str,
                          quantity: float, price: float, stop_price: float = None, side: str = None,
                          current_price: float = None, params: dict = None):
        return await self.connector.edit_order(exchange_order_id, order_type, symbol,
                                               quantity, price, stop_price, side,
                                               current_price, params)

    def _on_missing_funds_err(self, err, order_type, symbol, quantity, price, stop_price):
        self.log_order_creation_error(err, order_type, symbol, quantity, price, stop_price)
        if self.__class__.PRINT_DEBUG_LOGS:
            self.logger.warning(str(err))
        raise errors.MissingFunds(html_util.get_html_summary_if_relevant(err)) from err

    @contextlib.asynccontextmanager
    async def _order_operation(self, order_type, symbol, quantity, price, stop_price):
        try:
            yield
        except ccxt.InsufficientFunds as e:
            self._on_missing_funds_err(e, order_type, symbol, quantity, price, stop_price)
        except ccxt.MarketClosed as err:
            raise errors.MarketClosedError(f"{symbol} {html_util.get_html_summary_if_relevant(err)}") from err
        except (ccxt.NotSupported, NotImplementedError) as err:
            raise errors.NotSupported(err) from err
        except (errors.AuthenticationError, ccxt.AuthenticationError) as err:
            # invalid api key or missing trading rights
            raise errors.AuthenticationError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Please make sure that trading permissions are on for this API key."
            ) from err
        except ccxt.DDoSProtection as e:
            # ccxt.DDoSProtection: raised upon rate limit issues,
            # last response data might have details on what is happening
            # ensure this is not a permission error (can happen on binance)
            if self.is_api_permission_error(e):
                # invalid api key or missing trading rights
                raise errors.AuthenticationError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Please make sure that trading permissions are on for this API key."
                ) from e
            if self.should_log_on_ddos_exception(e):
                self.connector.log_ddos_error(e)
            raise errors.FailedRequest(
                f"Failed order operation: {e.__class__.__name__} {html_util.get_html_summary_if_relevant(e)}"
            ) from e
        except (errors.OctoBotExchangeError, errors.OrderCreationError):
            # custom error: forward it
            raise
        except Exception as e:
            if not self.is_market_open_for_order_type(symbol, order_type):
                raise errors.UnavailableOrderTypeForMarketError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange currently refuses to create orders of type {order_type} on {symbol}."
                ) from e
            if self.is_api_permission_error(e):
                # invalid api key or missing trading rights
                raise errors.AuthenticationError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Please make sure that trading permissions are on for this API key."
                ) from e
            if self.is_exchange_rules_compliancy_error(e):
                raise errors.ExchangeCompliancyError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange is refusing this order request on this account because "
                    f"of its compliancy requirements."
                ) from e
            if self.is_exchange_max_orders_for_market_reached_error(e):
                raise errors.ExchangeMaxOrdersForMarketReachedError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange is refusing this order: the maximum number of orders for this market has been reached."
                ) from e
            if self.is_exchange_closed_position_error(e):
                raise errors.ExchangeClosedPositionError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange is refusing this order request because associated position is closed."
                ) from e
            if self.is_exchange_order_would_immediately_trigger_error(e):
                raise errors.ExchangeOrderInstantTriggerError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange is refusing this order request because associated order would instantly trigger."
                ) from e
            self.log_order_creation_error(e, order_type, symbol, quantity, price, stop_price)
            # print(traceback.format_exc(), file=sys.stderr)    # uncomment for debugging in tests
            self.logger.exception(
                e,
                False,
                f"Unexpected error during order operation: {html_util.get_html_summary_if_relevant(e)}"
            )

    async def _verify_order(self, created_order, order_type, symbol, price, quantity, side, get_order_params=None):
        # some exchanges are not returning the full order details on creation: fetch it if necessary
        if created_order and not self._ensure_order_details_completeness(created_order):
            if ecoc.EXCHANGE_ID.value in created_order:
                order_exchange_id = created_order[ecoc.EXCHANGE_ID.value]
                if order_exchange_id is None:
                    self.logger.error(f"No order exchange id on created order: {created_order}")
                    return None
                exchange_order_id = created_order[ecoc.EXCHANGE_ID.value]
                params = self.order_request_kwargs_factory(
                    exchange_order_id, order_type, **(get_order_params or {})
                )
                fetched_order = await self.get_order(
                    exchange_order_id, symbol=symbol, **params
                )
                if fetched_order is None:
                    created_order[ecoc.STATUS.value] = enums.OrderStatus.PENDING_CREATION.value
                    # Order is created but not live on exchange. Consider it as pending.
                    # It will be updated later on via order updater
                    created_order[ecoc.SYMBOL.value] = symbol
                    created_order[ecoc.TYPE.value] = orders.get_trade_order_type(order_type).value
                    created_order[ecoc.SIDE.value] = side.value
                else:
                    created_order = fetched_order

        if created_order is not None:
            # on some exchange, market order are not including price, add it manually to ensure uniformity
            if created_order[ecoc.PRICE.value] is None and price is not None:
                created_order[ecoc.PRICE.value] = float(price)
            # sometimes, amount is 0, this is impossible. If it is, restore amount
            if not created_order[ecoc.AMOUNT.value] and quantity is not None:
                created_order[ecoc.AMOUNT.value] = float(quantity)

        return created_order

    async def _create_order_with_retry(self, order_type, symbol, quantity: decimal.Decimal,
                                       price: decimal.Decimal, stop_price: decimal.Decimal,
                                       side: enums.TradeOrderSide,
                                       current_price: decimal.Decimal,
                                       reduce_only: bool, params) -> dict:
        try:
            return await self._create_specific_order(order_type, symbol, quantity, price=price,
                                                     stop_price=stop_price, side=side,
                                                     current_price=current_price,
                                                     reduce_only=reduce_only, params=params)
        except ccxt.PermissionDenied as err:
            if self.is_exchange_account_traded_symbol_permission_error(err):
                # exchange won't let this order create: raise
                raise errors.ExchangeAccountSymbolPermissionError(
                    f"Error when creating {symbol} {order_type} order on "
                    f"{self.exchange_manager.exchange_name}: {html_util.get_html_summary_if_relevant(err)}"
                ) from err
            # otherwise propagate exception: this is not a situation to retry
            raise
        except ccxt.ExchangeNotAvailable as err:
            if not self._enable_create_order_retrier:
                # should not retry, raise
                raise
            is_retriable_error = False
            for error_message in constants.RETRIABLE_EXCHANGE_ERRORS_DESC:
                if error_message in str(err):
                    is_retriable_error = True
            if is_retriable_error:
                self.logger.warning(
                    f"Failed to create order ({html_util.get_html_summary_if_relevant(err)}) : "
                    f"order_type: {order_type}, symbol: {symbol}. Retrying order creation."
                )
                return await self._create_specific_order(order_type, symbol, quantity, price=price,
                                                         stop_price=stop_price, side=side,
                                                         current_price=current_price, reduce_only=reduce_only,
                                                         params=params)
            # not retriable, raise
            raise
        except (ccxt.InvalidOrder, ccxt.BadRequest) as err:
            if self.is_exchange_account_traded_symbol_permission_error(err):
                # exchange won't let this order create: raise
                raise errors.ExchangeAccountSymbolPermissionError(
                    f"Error when creating {symbol} {order_type} order on {self.exchange_manager.exchange_name}: "
                    f"{html_util.get_html_summary_if_relevant(err)}"
                ) from err
            if self.is_exchange_internal_sync_error(err):
                raise errors.ExchangeInternalSyncError(
                    f"Error when handling {symbol} {order_type} order. "
                    f"Exchange is refusing this order request because of sync error "
                    f"({html_util.get_html_summary_if_relevant(err)})."
                ) from err
            if self.is_missing_funds_error(err):
                self._on_missing_funds_err(err, order_type, symbol, quantity, price, stop_price)
            if not self._enable_create_order_retrier:
                # should not retry, raise
                raise
            # can be raised when exchange precision/limits rules change
            self.logger.warning(
                f"Failed to create order ({html_util.get_html_summary_if_relevant(err)}) : "
                f"order_type: {order_type}, symbol: {symbol}. "
                f"This might be due to an update on {self.name} market rules. Fetching updated rules."
            )
            await self.connector.load_symbol_markets(
                reload=True, market_filter=self.exchange_manager.market_filter
            )
            # retry order creation with updated markets (ccxt will use the updated market values)
            return await self._create_specific_order(order_type, symbol, quantity, price=price,
                                                     stop_price=stop_price, side=side,
                                                     current_price=current_price, reduce_only=reduce_only,
                                                     params=params)

    def _ensure_order_details_completeness(self, order, order_required_fields=None, order_non_empty_fields=None):
        if order_required_fields is None:
            order_required_fields = self.ORDER_REQUIRED_FIELDS
        if order_non_empty_fields is None:
            order_non_empty_fields = self.ORDER_NON_EMPTY_FIELDS
        # ensure all order_required_fields are present and all order_non_empty_fields are not empty
        return all(key in order for key in order_required_fields) and \
            all(order[key] for key in order_non_empty_fields)

    async def _create_specific_order(self, order_type, symbol, quantity: decimal.Decimal, price: decimal.Decimal = None,
                                     side: enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                                     stop_price: decimal.Decimal = None, reduce_only: bool = False, params=None) -> dict:
        created_order = None
        float_quantity = float(quantity)
        float_price = price if price is None else float(price)
        float_stop_price = stop_price if stop_price is None else float(stop_price)
        float_current_price = current_price if current_price is None else float(current_price)
        side = None if side is None else side.value
        params = {} if params is None else params
        params.update(self.exchange_manager.exchange_backend.get_orders_parameters(None))
        if order_type == enums.TraderOrderType.BUY_MARKET:
            created_order = await self._create_market_buy_order(symbol, float_quantity, price=float_price,
                                                                reduce_only=reduce_only, params=params)
        elif order_type == enums.TraderOrderType.BUY_LIMIT:
            created_order = await self._create_limit_buy_order(symbol, float_quantity, price=float_price,
                                                               reduce_only=reduce_only, params=params)
        elif order_type == enums.TraderOrderType.SELL_MARKET:
            created_order = await self._create_market_sell_order(symbol, float_quantity, price=float_price,
                                                                 reduce_only=reduce_only, params=params)
        elif order_type == enums.TraderOrderType.SELL_LIMIT:
            created_order = await self._create_limit_sell_order(symbol, float_quantity, price=float_price,
                                                                reduce_only=reduce_only, params=params)
        elif order_type == enums.TraderOrderType.STOP_LOSS:
            created_order = await self._create_market_stop_loss_order(symbol, float_quantity, price=float_price,
                                                                      side=side, current_price=float_current_price,
                                                                      params=params)
        elif order_type == enums.TraderOrderType.STOP_LOSS_LIMIT:
            created_order = await self._create_limit_stop_loss_order(symbol, float_quantity, price=float_price,
                                                                     side=side, stop_price=float_stop_price, params=params)
        elif order_type == enums.TraderOrderType.TAKE_PROFIT:
            created_order = await self._create_market_take_profit_order(symbol, float_quantity, price=float_price,
                                                                        side=side, params=params)
        elif order_type == enums.TraderOrderType.TAKE_PROFIT_LIMIT:
            created_order = await self._create_limit_take_profit_order(symbol, float_quantity, price=float_price,
                                                                       side=side, params=params)
        elif order_type == enums.TraderOrderType.TRAILING_STOP:
            created_order = await self._create_market_trailing_stop_order(symbol, float_quantity, price=float_price,
                                                                          side=side, reduce_only=reduce_only, params=params)
        elif order_type == enums.TraderOrderType.TRAILING_STOP_LIMIT:
            created_order = await self._create_limit_trailing_stop_order(symbol, float_quantity, price=float_price,
                                                                         side=side, reduce_only=reduce_only, params=params)
        return created_order

    async def _create_market_buy_order(
        self, symbol, quantity, price=None, reduce_only: bool = False, params=None
        ) -> dict:
        if self.ENABLE_SPOT_BUY_MARKET_WITH_COST and self.exchange_manager.is_spot_only:
            if price is None:
                raise errors.NotSupported(
                    f"price is required for buy market orders when {self.get_name()}.ENABLE_SPOT_BUY_MARKET_WITH_COST "
                    f"is {self.ENABLE_SPOT_BUY_MARKET_WITH_COST}"
                )
            return await self.connector.create_market_buy_order_with_cost(
                symbol, quantity * price, quantity, params=params
            )
        return await self.connector.create_market_buy_order(symbol, quantity, price=price, params=params)

    async def _create_limit_buy_order(
        self, symbol, quantity, price=None, reduce_only: bool = False, params=None
        ) -> dict:
        return await self.connector.create_limit_buy_order(
            symbol, quantity, price, params=params
        )

    async def _create_market_sell_order(
        self, symbol, quantity, price=None, reduce_only: bool = False, params=None
        ) -> dict:
        return await self.connector.create_market_sell_order(symbol, quantity, price=price, params=params)

    async def _create_limit_sell_order(
        self, symbol, quantity, price=None, reduce_only: bool = False, params=None
        ) -> dict:
        return await self.connector.create_limit_sell_order(
            symbol, quantity, price, params=params)

    async def _create_market_stop_loss_order(self, symbol, quantity, price, side, current_price, params=None) -> dict:
        return await self.connector.create_market_stop_loss_order(
            symbol=symbol, quantity=quantity, price=price,
            side=side, current_price=current_price, params=params)

    async def _create_limit_stop_loss_order(self, symbol, quantity, price, stop_price, side, params=None) -> dict:
        return await self.connector.create_limit_stop_loss_order(
            symbol=symbol, quantity=quantity, price=price, stop_price=stop_price, side=side, params=params)

    async def _create_market_take_profit_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("_create_market_take_profit_order is not implemented")

    async def _create_limit_take_profit_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("_create_limit_take_profit_order is not implemented")

    async def _create_market_trailing_stop_order(
        self, symbol, quantity, price=None, side=None,
        reduce_only: bool = False, params=None) -> dict:
        raise NotImplementedError("_create_market_trailing_stop_order is not implemented")

    async def _create_limit_trailing_stop_order(

        self, symbol, quantity, price=None, side=None,
        reduce_only: bool = False, params=None) -> dict:
        raise NotImplementedError("_create_limit_trailing_stop_order is not implemented")

    def get_exchange_current_time(self):
        return self.connector.get_exchange_current_time()

    def get_uniform_timestamp(self, timestamp):
        return self.connector.get_uniform_timestamp(timestamp)

    def _should_fix_market_status(self):
        return self.FIX_MARKET_STATUS

    def _should_remove_market_status_limits(self):
        return self.REMOVE_MARKET_STATUS_PRICE_LIMITS

    def _should_adapt_market_status_for_contract_size(self):
        return self.ADAPT_MARKET_STATUS_FOR_CONTRACT_SIZE

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        """
        Override using get_fixed_market_status in exchange tentacle if the default market status is not as expected
        """
        if self._should_fix_market_status():
            return self.get_fixed_market_status(
                symbol,
                price_example=price_example,
                with_fixer=with_fixer,
                remove_price_limits=self._should_remove_market_status_limits(),
                adapt_for_contract_size=self._should_adapt_market_status_for_contract_size()
            )
        return self.connector.get_market_status(symbol, price_example=price_example, with_fixer=with_fixer)

    def get_fixed_market_status(self, symbol, price_example=None, with_fixer=True, remove_price_limits=False,
                                adapt_for_contract_size=False):
        """
        Use this method in local get_market_status overrides when market status has to be fixed by
        calling _fix_market_status.
        Changes PRECISION_AMOUNT and PRECISION_PRICE from decimals to integers
        (use number of digits instead of price example) by default.
        Override _fix_market_status to change other elements
        """
        market_status = self.connector.adapter.adapt_market_status(
            copy.deepcopy(
                self.connector.get_market_status(symbol, with_fixer=False)
            ),
            remove_price_limits=remove_price_limits
        )
        if adapt_for_contract_size and self.exchange_manager.is_future:
            self._adapt_market_status_for_contract_size(market_status, self.get_contract_size(symbol))
        if with_fixer:
            return exchanges_util.ExchangeMarketStatusFixer(market_status, price_example).market_status
        return market_status

    def get_max_orders_count(self, symbol: str, order_type: enums.TraderOrderType) -> int:
        return (
            constants.DEFAULT_MAX_STOP_ORDERS_COUNT if orders.is_stop_order(order_type)
            else constants.DEFAULT_MAX_DEFAULT_ORDERS_COUNT
        )

    def uses_demo_trading_instead_of_sandbox(self) -> bool:
        return False

    def _apply_contract_size(self, value, contract_size):
        if value is None:
            return value
        return value * contract_size

    def _adapt_market_status_for_contract_size(self, market_status, contract_size):
        float_size = float(contract_size)
        for limit_type in (enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT.value, ):
            for limit_val in (enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MIN.value,
                              enums.ExchangeConstantsMarketStatusColumns.LIMITS_AMOUNT_MAX.value):

                market_status[enums.ExchangeConstantsMarketStatusColumns.LIMITS.value][limit_type][limit_val] = \
                    self._apply_contract_size(
                        market_status[enums.ExchangeConstantsMarketStatusColumns.LIMITS.value][limit_type][limit_val],
                        float_size
                    )
        market_status[enums.ExchangeConstantsMarketStatusColumns.PRECISION.value][
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value] = \
            number_util.get_digits_count(float_size)

    async def get_account_id(self, **kwargs: dict) -> str:
        raise NotImplementedError(f"get_account_id is not implemented on {self.exchange_manager.exchange_name}")

    async def get_balance(self, **kwargs: dict):
        return await self.connector.get_balance(**kwargs)

    async def get_user_balance(self, user_id: str, **kwargs: dict):
        return await self.connector.get_user_balance(user_id=user_id, **kwargs)

    async def get_symbol_prices(self, symbol: str, time_frame: commons_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit, **kwargs)

    async def get_kline_price(self, symbol: str, time_frame: commons_enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list]:
        if self.DUMP_INCOMPLETE_LAST_CANDLE:
            raise errors.NotSupported(f"Can't fetch kline when the last candle from exchange can't be fetched")
        return await self.connector.get_kline_price(symbol=symbol, time_frame=time_frame, **kwargs)

    async def get_order_book(self, symbol: str, limit: int = 5, **kwargs: dict) -> typing.Optional[dict]:
        return await self.connector.get_order_book(symbol=symbol, limit=limit, **kwargs)

    async def get_order_books(
        self, symbols: typing.Optional[list[str]], limit: int = 5, **kwargs: dict
    ) -> typing.Optional[dict]:
        return await self.connector.get_order_books(symbols=symbols, limit=limit, **kwargs)

    async def get_recent_trades(self, symbol: str, limit: int = 50, **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_recent_trades(symbol=symbol, limit=limit, **kwargs)

    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        return await self.connector.get_price_ticker(symbol=symbol, **kwargs)

    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[dict[str, dict]]:
        return await self.connector.get_all_currencies_price_ticker(**kwargs)

    async def refresh_markets(self):
        return await self.connector.load_symbol_markets(
            reload=True, market_filter=self.exchange_manager.market_filter
        )

    def order_request_kwargs_factory(
        self, 
        exchange_order_id: str, 
        order_type: typing.Optional[enums.TraderOrderType] = None, 
        **kwargs
    ) -> dict:
        # implement if the exchange needs additional kwargs to fetch an order, like to fetch stop orders
        return kwargs

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        extended_kwargs = self.order_request_kwargs_factory(exchange_order_id, order_type, **(kwargs or {}))
        return await self._ensure_order_completeness(
            await self.connector.get_order(exchange_order_id, symbol=symbol, **extended_kwargs),
            symbol, **kwargs
        )

    async def get_order_from_open_and_closed_orders(self, exchange_order_id: str, symbol: str = None, **kwargs: dict) -> dict:
        for order in await self.get_open_orders(symbol, **kwargs):
            if order[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] == exchange_order_id:
                return order
        for order in await self.get_closed_orders(symbol, **kwargs):
            if order[enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value] == exchange_order_id:
                return order
        return None  # OrderNotFound

    async def get_order_from_trades(self, symbol, exchange_order_id, order_to_update=None):
        order_to_update = order_to_update or {}
        trades = await self.get_my_recent_trades(symbol)
        # usually the right trade is within the last ones
        for trade in trades[::-1]:
            if trade[ecoc.ORDER.value] == exchange_order_id:
                return exchanges_util.update_raw_order_from_raw_trade(order_to_update, trade)
        return None  #OrderNotFound

    async def get_all_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_all_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    @fetching_orders_request
    async def get_open_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    @fetching_orders_request
    async def _get_closed_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_closed_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        # uses connector.get_closed_orders if supported, otherwise uses recent trades
        try:
            return await self._get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs)
        except errors.NotSupported:
            if self.REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES:
                return await self._get_closed_orders_from_my_recent_trades(
                    symbol=symbol, since=since, limit=limit, **kwargs
                )
            raise

    @fetching_orders_request
    async def get_cancelled_orders(
        self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict
    ) -> list:
        if not self.SUPPORT_FETCHING_CANCELLED_ORDERS:
            raise errors.NotSupported(f"get_cancelled_orders is not supported")
        return await self.connector.get_cancelled_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    async def _get_closed_orders_from_my_recent_trades(
        self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict
    ) -> list:
        trades = await self.get_my_recent_trades(symbol, since=since, limit=limit, **kwargs)
        return [
            exchanges_util.update_raw_order_from_raw_trade({}, trade)
            for trade in trades
        ]

    async def ensure_orders_completeness(
        self, raw_orders, symbol, since=None, limit=None, trades_by_exchange_order_id=None, **kwargs
    ):
        if not self.REQUIRE_ORDER_FEES_FROM_TRADES \
                or not any(exchanges_util.is_missing_trading_fees(order) for order in raw_orders):
            return raw_orders
        trades_by_exchange_order_id = trades_by_exchange_order_id or await self._get_trades_by_exchange_order_id(
            symbol=symbol, since=since, limit=limit, **kwargs
        )
        return [
            await self._ensure_order_completeness(
                order, symbol, trades_by_exchange_order_id=trades_by_exchange_order_id, **kwargs
            )
            for order in raw_orders
        ]

    async def _ensure_order_completeness(
        self, raw_order, symbol, since=None, limit=None, trades_by_exchange_order_id=None, **kwargs
    ):
        if (
            raw_order is None
            or not self.REQUIRE_ORDER_FEES_FROM_TRADES
            or not exchanges_util.is_missing_trading_fees(raw_order)
        ):
            return raw_order
        trades_by_exchange_order_id = trades_by_exchange_order_id or await self._get_trades_by_exchange_order_id(
            symbol=symbol, since=since, limit=limit, **kwargs
        )
        exchanges_util.apply_trades_fees(raw_order, trades_by_exchange_order_id)
        return raw_order

    async def get_user_open_orders(self, user_id: str, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_user_open_orders(user_id=user_id, symbol=symbol, since=since, limit=limit, **kwargs)

    async def _get_trades_by_exchange_order_id(self, symbol=None, since=None, limit=None, **kwargs):
        trades_by_exchange_order_id = {}
        for trade in await self.get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs):
            exchange_order_id = trade[enums.ExchangeConstantsOrderColumns.ORDER.value]
            if exchange_order_id in trades_by_exchange_order_id:
                trades_by_exchange_order_id[exchange_order_id].append(trade)
            else:
                trades_by_exchange_order_id[exchange_order_id] = [trade]
        return trades_by_exchange_order_id

    async def get_my_recent_trades(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_user_recent_trades(self, user_id: str, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_user_recent_trades(user_id=user_id, symbol=symbol, since=since, limit=limit, **kwargs)

    async def cancel_all_orders(self, symbol: str = None, **kwargs: dict) -> None:
        return await self.connector.cancel_all_orders(symbol=symbol, **kwargs)

    async def cancel_order(
        self, exchange_order_id: str, symbol: str, order_type: enums.TraderOrderType, **kwargs: dict
    ) -> enums.OrderStatus:
        extended_kwargs = self.order_request_kwargs_factory(exchange_order_id, order_type, **(kwargs or {}))
        return await self.connector.cancel_order(exchange_order_id, symbol, order_type, **extended_kwargs)

    def get_trade_fee(self, symbol: str, order_type: enums.TraderOrderType, quantity, price, taker_or_maker) -> dict:
        return self.connector.get_trade_fee(symbol, order_type, quantity, price, taker_or_maker)

    def get_fees(self, symbol):
        return self.connector.get_fees(symbol)

    def get_pair_from_exchange(self, pair) -> str:
        return self.connector.get_pair_from_exchange(pair)

    def get_split_pair_from_exchange(self, pair) -> (str, str):
        return self.connector.get_split_pair_from_exchange(pair)

    def get_exchange_pair(self, pair) -> str:
        return self.connector.get_exchange_pair(pair)

    def get_pair_cryptocurrency(self, pair) -> str:
        return self.connector.get_pair_cryptocurrency(pair)

    def get_default_balance(self):
        return self.connector.get_default_balance()

    def get_rate_limit(self):
        return self.connector.get_rate_limit()

    def get_all_available_symbols(self, active_only=True) -> set[str]:
        """
        :return: the list of all symbols supported by the exchange
        """
        return self.connector.get_client_symbols(
            active_only=False if self.INCLUDE_DISABLED_SYMBOLS_IN_AVAILABLE_SYMBOLS else active_only
        )

    async def get_all_tradable_symbols(self, active_only=True) -> set[str]:
        """
        Override if the exchange is not allowing trading for all available symbols (ex: MEXC)
        :return: the list of all symbols supported by the exchange that can currently be traded through API
        """
        return self.get_all_available_symbols(active_only=active_only)

    def get_alias_symbols(self) -> set[str]:
        """
        :return: a set of symbol of this exchange that are aliases to other symbols
        """
        return set()

    async def switch_to_account(self, account_type: enums.AccountTypes):
        return await self.connector.switch_to_account(account_type=account_type)

    def is_successfully_authenticated(self) -> bool:
        return self.connector.is_authenticated

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        raise NotImplementedError("is_authenticated_request is not implemented")

    async def withdraw(
        self, asset: str, amount: decimal.Decimal, network: str, address: str, tag: str = "", params: dict = None
    ) -> dict:
        """
        Withdraw funds from the exchange
        :param asset: the asset to withdraw
        :param amount: the amount to withdraw
        :param network: the network to withdraw to
        :param address: the address to withdraw to
        :param tag: the tag to withdraw with
        :param params: the withdrawal request params
        """
        return await self.connector.withdraw(asset, amount, network, address, tag=tag, params=params)

    async def get_deposit_address(self, asset: str, params: dict = None) -> dict:
        return await self.connector.get_deposit_address(asset, params=params)

    # Futures
    async def load_pair_contract(self, pair: str):
        """
        Load and create a new FutureContract for the pair
        :param pair: the contract pair
        """
        try:
            return self.create_pair_contract(
                pair=pair,
                current_leverage=await self.get_symbol_leverage(pair),
                contract_size=self.get_contract_size(pair),
                margin_type=await self.get_margin_type(pair),
                contract_type=self.get_contract_type(pair),
                position_mode=await self.get_position_mode(pair),
                maintenance_margin_rate=await self.get_maintenance_margin_rate(pair),
            )
        except NotImplementedError:
            try:
                positions = [await self.get_position(pair)]
            except NotImplementedError:
                positions = await self.get_positions(symbols=[pair])
            contracts.update_contracts_from_positions(self.exchange_manager, positions)

    """
    Deprecated: Use load_pair_contract instead
    """
    async def load_pair_future_contract(self, pair: str):
        await self.load_pair_contract(pair)

    def create_pair_contract(self, pair, current_leverage, contract_size, margin_type,
                             contract_type, position_mode, maintenance_margin_rate, maximum_leverage=None):
        """
        Create a new FutureContract for the pair
        # TODO: support 1 contract by side when using hedge position mode --> think about another way to store contracts
        :param pair: the contract pair
        :param current_leverage: the contract current leverage
        :param margin_type: the contract margin type
        :param contract_size: the size of a contract
        :param contract_type: the contract type
        :param position_mode: the contract position mode
        :param maintenance_margin_rate: the contract maintenance margin rate
        :param maximum_leverage: the contract maximum leverage
        """
        self.logger.debug(f"Creating {pair} contract...")
        contract = contracts.create_contract(pair=pair,
                                            current_leverage=current_leverage,
                                            contract_size=contract_size,
                                            margin_type=margin_type,
                                            contract_type=contract_type,
                                            position_mode=position_mode,
                                            maintenance_margin_rate=maintenance_margin_rate,
                                            maximum_leverage=maximum_leverage)
        self.pair_contracts[pair] = contract
        return contract

    def has_pair_contract(self, pair: str) -> bool:
        """
        :param pair: the pair
        :return: True if the given pair is in local contracts
        """
        return pair in self.pair_contracts

    """
    Deprecated: Use get_pair_contract or get_pair_contract_async instead
    """
    def get_pair_future_contract(self, pair):
        """
        Return the FutureContract instance associated to the pair
        :param pair: the pair
        :return: the FutureContract instance
        """
        try:
            return self.pair_contracts[pair]
        except KeyError:
            asyncio.create_task(self.load_pair_contract(pair))
            raise errors.ContractExistsError(f"{pair} future contract doesn't exist, fetching it...")

    def get_pair_contract(self, pair: str) -> contracts.Contract:
        """
        Return the Contract (FutureContract, OptionContract, MarginContract) instance associated to the pair
        :param pair: the pair
        :return: the Contract instance
        """
        try:
            return self.pair_contracts[pair]
        except KeyError:
            asyncio.create_task(self.load_pair_contract(pair))
            raise errors.ContractExistsError(f"{pair} contract doesn't exist, fetching it...")

    async def get_pair_contract_async(self, pair) -> contracts.Contract:
        """
        Return the Contract (FutureContract, OptionContract, MarginContract) instance associated to the pair
        :param pair: the pair
        :return: the Contract instance
        """
        try:
            return self.pair_contracts[pair]
        except KeyError:
            await self.load_pair_contract(pair)

    def set_pair_contract(self, pair: str, contract: contracts.Contract):
        """
        Set the pair contract
        :param pair: the pair
        :param contract: the contract
        """
        self.pair_contracts[pair] = contract

    """
    Deprecated: Use set_pair_contract instead
    """
    def set_pair_future_contract(self, pair, future_contract):
        self.set_pair_contract(pair, future_contract)

    def set_contract_initialized_event(self, symbol):
        commons_tree.EventProvider.instance().trigger_event(
            self.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.exchange_manager.exchange_name,
                commons_enums.InitializationEventExchangeTopics.CONTRACTS.value,
                symbol=symbol
            )
        )

    """
    Positions
    """

    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        """
        Get the current user symbol position
        :param symbol: the position symbol
        :return: the user symbol position
        """
        position = await self.connector.get_position(symbol=symbol, **kwargs)
        if position is None and self.REQUIRES_MOCKED_EMPTY_POSITION:
            # this exchange does not support empty position fetching, create an empty position from available data
            return await self.get_mocked_empty_position(symbol, **kwargs)
        return position

    async def get_positions(self, symbols=None, **kwargs: dict) -> list:
        """
        Get the current user position list
        :return: the user position list
        """
        if not self.REQUIRES_SYMBOL_FOR_EMPTY_POSITION:
            return await self.connector.get_positions(symbols=symbols, **kwargs)
        if symbols is None:
            raise NotImplementedError(f"The symbols param is required to get multiple positions at once")
        # force get_position when symbols is set as ccxt get_positions is only returning open positions
        return list(
            await asyncio.gather(*(
                self.get_position(symbol, **kwargs)
                for symbol in symbols
            ))
        )

    async def get_closed_positions(self, symbols=None, **kwargs: dict) -> list:
        """
        Get the closed position list
        :param symbols: the symbols or None
        :return: the closed position list
        """
        return await self.connector.get_closed_positions(symbols=symbols, **kwargs)

    async def get_user_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        """
        Get the user position list
        :param user_id: the user id
        :param symbols: the symbols or None
        :return: the user position list
        """
        return await self.connector.get_user_positions(user_id=user_id, symbols=symbols, **kwargs)

    async def get_user_closed_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        """
        Get the user closed position list
        :param user_id: the user id
        :param symbols: the symbols or None
        :return: the user closed position list
        """
        return await self.connector.get_user_closed_positions(user_id=user_id, symbols=symbols, **kwargs)

    async def get_mocked_empty_position(self, symbol: str, **kwargs: dict) -> dict:
        """
        Override when necessary
        Called when self.REQUIRES_MOCKED_EMPTY_POSITION is True and a fetched position is None
        :param symbol: the position symbol
        """
        return await self.connector.get_mocked_empty_position(symbol=symbol, **kwargs)

    async def get_funding_rate(self, symbol: str, **kwargs: dict) -> dict:
        """
        :param symbol: the symbol
        :return: the current symbol funding rate
        """
        return await self.connector.get_funding_rate(symbol=symbol, **kwargs)

    async def get_funding_rate_history(self, symbol: str, limit: int = 1, **kwargs: dict) -> list:
        """
        :param symbol: the symbol
        :param limit: the history limit size
        :return: the funding rate history
        """
        return await self.connector.get_funding_rate_history(symbol=symbol, limit=limit, **kwargs)

    """
    Margin and leverage
    """

    async def get_symbol_leverage(self, symbol: str, **kwargs: dict):
        """
        :param symbol: the symbol
        :return: the current symbol leverage multiplier
        """
        raise NotImplementedError("get_symbol_leverage is not implemented")

    async def get_leverage_tiers(self, symbols: list = None, **kwargs: dict)-> dict:
        """
        :param symbols: the symbols or None
        :return: the current leverage tiers by symbols
        """
        return await self.connector.get_leverage_tiers(symbols=symbols, **kwargs)

    async def get_margin_type(self, symbol: str):
        """
        :param symbol: the symbol
        :return: the margin type for the requested symbol. Can be MarginType.ISOLATED or MarginType.CROSS
        """
        raise NotImplementedError("get_margin_type is not implemented")

    def get_contract_type(self, symbol: str) -> enums.FutureContractType | enums.OptionContractType:
        """
        :param symbol: the symbol
        :return: the contract type for the requested symbol.
        Can be FutureContractType or OptionContractType
        Requires is_inverse_symbol and is_linear_symbol to be implemented
        """
        return contracts.get_contract_type_from_symbol(symbol, self.is_linear_symbol(symbol), self.is_inverse_symbol(symbol))

    def get_contract_size(self, symbol: str):
        """
        :param symbol: the symbol
        :return: the contract size for the requested symbol.
        """
        return self.connector.get_contract_size(symbol)

    async def get_position_mode(self, symbol: str):
        """
        :param symbol: the symbol
        :return: the position mode for the requested symbol. Can be PositionMode HEDGE or ONE_WAY
        """
        raise NotImplementedError("get_position_mode is not implemented")

    async def get_maintenance_margin_rate(self, symbol: str):
        """
        :param symbol: the symbol
        :return: the symbol maintenance margin rate
        """
        raise NotImplementedError("get_maintenance_margin_rate is not implemented")

    async def set_symbol_leverage(self, symbol: str, leverage: float, **kwargs):
        """
        Set the symbol leverage
        :param symbol: the symbol
        :param leverage: the leverage
        :return: the update result
        """
        if self.supports_api_leverage_update(symbol):
            return await self.connector.set_symbol_leverage(leverage=leverage, symbol=symbol, **kwargs)
        # nothing to do when UPDATE_LEVERAGE_FROM_API is False
        return None

    def supports_api_leverage_update(self, symbol: str) -> bool:
        """
        Override if necessary
        :param symbol:
        :return:
        """
        return self.exchange_manager.is_future

    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict):
        """
        Set the symbol margin type
        :param symbol: the symbol
        :param isolated: when False, margin type is cross, else it's isolated
        :return: the update result
        """
        if self.SUPPORTS_SET_MARGIN_TYPE:
            try:
                return await self.connector.set_symbol_margin_type(symbol=symbol, isolated=isolated, **kwargs)
            except Exception as e:
                if self.is_api_permission_error(e):
                    # invalid api key or missing trading rights
                    raise errors.AuthenticationError(
                        f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                        f"Please make sure that trading permissions are on for this API key."
                    ) from e
                raise
        raise errors.NotSupported(f"set_symbol_margin_type is not supported on {self.get_name()}")

    async def set_symbol_position_mode(self, symbol: str, one_way: bool):
        """
        Set the symbol margin type
        :param symbol: the symbol
        :param one_way: when False, position mode is hedge, else it's one_way
        :return: the update result
        """
        return await self.connector.set_symbol_position_mode(symbol=symbol, one_way=one_way)

    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: enums.TakeProfitStopLossMode):
        return await self.connector.set_symbol_partial_take_profit_stop_loss(symbol=symbol, inverse=inverse,
                                                                             tp_sl_mode=tp_sl_mode)

    def supports_trading_type(self, symbol, trading_type: enums.ContractTradingTypes):
        return self.connector.supports_trading_type(symbol, trading_type)

    def supports_native_edit_order(self, order_type: enums.TraderOrderType) -> bool:
        # return False when default edit_order can't be used and order should always be canceled and recreated instead
        return True

    def is_linear_symbol(self, symbol) -> bool:
        """
        :param symbol: the symbol
        :return: True if the symbol is related to a linear contract
        """
        return self.supports_trading_type(symbol, enums.ContractTradingTypes.LINEAR)

    def is_inverse_symbol(self, symbol) -> bool:
        """
        :param symbol: the symbol
        :return: True if the symbol is related to an inverse contract
        """
        return self.supports_trading_type(symbol, enums.ContractTradingTypes.INVERSE)

    def is_expirable_symbol(self, symbol):
        """
        :param symbol: the symbol
        :return: True if the symbol is related to a contract having an expiration date
        """
        return self.connector.is_expirable_symbol(symbol)

    def is_skipping_empty_candles_in_ohlcv_fetch(self):
        return self.IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH

    def is_order_not_found_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_ORDER_NOT_FOUND_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_ORDER_NOT_FOUND_ERRORS)
        return False

    def is_api_permission_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_PERMISSION_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_PERMISSION_ERRORS)
        return False

    def is_exchange_rules_compliancy_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_COMPLIANCY_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_COMPLIANCY_ERRORS)
        return False

    def is_exchange_closed_position_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_CLOSED_POSITION_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_CLOSED_POSITION_ERRORS)
        return False

    def is_exchange_order_would_immediately_trigger_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_ORDER_IMMEDIATELY_TRIGGER_ERRORS)
        return False

    def is_exchange_order_uncancellable(self, error: BaseException) -> bool:
        if self.EXCHANGE_ORDER_UNCANCELLABLE_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_ORDER_UNCANCELLABLE_ERRORS)
        return False

    def is_exchange_max_orders_for_market_reached_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_MAX_ORDERS_FOR_MARKET_REACHED_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_MAX_ORDERS_FOR_MARKET_REACHED_ERRORS)
        return False

    def is_exchange_internal_sync_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_INTERNAL_SYNC_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_INTERNAL_SYNC_ERRORS)
        return False

    def is_missing_funds_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_MISSING_FUNDS_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_MISSING_FUNDS_ERRORS)
        return False

    def is_exchange_account_traded_symbol_permission_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_ACCOUNT_TRADED_SYMBOL_PERMISSION_ERRORS)
        return False

    def is_authentication_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_AUTHENTICATION_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_AUTHENTICATION_ERRORS)
        return False

    def is_ip_whitelist_error(self, error: BaseException) -> bool:
        if self.EXCHANGE_IP_WHITELIST_ERRORS:
            return exchanges_util.is_error_on_this_type(error, self.EXCHANGE_IP_WHITELIST_ERRORS)
        return False

    """
    Auto fetched and filled exchanges
    """
    def _apply_fetched_details(self, config, exchange_manager):
        raise NotImplementedError("_apply_fetched_details is not implemented")

    @classmethod
    async def fetch_exchange_config(
        cls, exchange_config_by_exchange: typing.Optional[dict[str, dict]], exchange_manager
    ):
        raise NotImplementedError("fetch_exchange_config is not implemented")

    @classmethod
    def get_custom_url_config(cls, tentacle_config: dict, exchange_name: str) -> dict:
        raise NotImplementedError("get_custom_url_config is not implemented")

    @classmethod
    def supported_autofill_exchanges(cls, tentacle_config):
        raise NotImplementedError("supported_autofill_exchanges is not implemented")

    @classmethod
    async def get_autofilled_exchange_details(cls, aiohttp_session, tentacle_config, exchange_name):
        raise NotImplementedError("get_autofilled_exchange_details is not implemented")

    @staticmethod
    def get_default_reference_market(exchange_name: str) -> str:
        return commons_constants.DEFAULT_REFERENCE_MARKET


    """
    Parsers todo remove ?
    """

    def parse_order_book_ticker(self, order_book_ticker):
        return self.connector.parse_order_book_ticker(order_book_ticker)

    def parse_exhange_order_id(self, order):
        return self.connector.parse_exhange_order_id(order)

    def parse_order_symbol(self, order):
        return self.connector.parse_order_symbol(order)

    def parse_funding(self, funding_dict, from_ticker=False) -> dict:
        """
        :param from_ticker: when True, the funding dict is extracted from ticker data
        :param funding_dict: the funding dict
        :return: the uniformized funding dict
        """
        return self.connector.parse_funding(funding_dict, from_ticker=from_ticker)

    def parse_mark_price(self, mark_price_dict, from_ticker=False) -> dict:
        """
        :param from_ticker: when True, the mark price dict is extracted from ticker data
        :param mark_price_dict: the mark price dict
        :return: the uniformized mark price status
        """
        return self.connector.parse_mark_price(mark_price_dict, from_ticker=from_ticker)
