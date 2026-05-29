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

import ccxt.async_support as ccxt
from octobot_commons import logging
import octobot_commons.enums as commons_enums
import octobot_commons.tree as commons_tree
import octobot_commons.constants as commons_constants
import octobot_commons.html_util as html_util

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.exchanges.util as exchanges_util
import octobot_trading.exchanges.connectors.ccxt.ccxt_connector as ccxt_connector
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
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
    """
    RestExchange is using its exchange connector to interact with the exchange.
    It should be used regardless of the exchange or the exchange library (ccxt or other)
    Always take and returns octobot formatted data and errors
    Is used request regardless of the trading type (spot / future / other)

    Is extended in exchange tentacles to define custom behaviors or exchange adapter (override of get_adapter_class)
    """
    ORDER_NON_EMPTY_FIELDS = [ecoc.EXCHANGE_ID.value, ecoc.TIMESTAMP.value, ecoc.SYMBOL.value, ecoc.TYPE.value,
                              ecoc.SIDE.value, ecoc.PRICE.value, ecoc.AMOUNT.value, ecoc.STATUS.value]
    ORDER_REQUIRED_FIELDS = ORDER_NON_EMPTY_FIELDS + [ecoc.REMAINING.value]
    PRINT_DEBUG_LOGS = False

    # Set False in case this exchange's markets should never be filtered as soon as they are fetched
    # Therefore overriding the env var value for this exchange
    FETCH_MIN_EXCHANGE_MARKETS = constants.FETCH_MIN_EXCHANGE_MARKETS
    WITHDRAW_NETWORK_PARAM_KEY = "network" # key to use in params to specify the network to withdraw to
    HAS_FETCHED_DETAILS = False  # set True when this exchange details (urls etc) have to be fetched before starting the exchange


    DEFAULT_CONNECTOR_CLASS = ccxt_connector.CCXTConnector

    def __init__(
        self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        connector_class=None
    ):
        super().__init__(config, exchange_manager, exchange_config_by_exchange)
        if self.HAS_FETCHED_DETAILS:
            self._apply_fetched_details(config, exchange_manager)
        self.connector = self._create_connector(config, exchange_manager, connector_class, exchange_config_by_exchange)
        self.pair_contracts: dict[str, contracts.MarginContract] = {}

    def _create_connector(self, config, exchange_manager, connector_class, exchange_config_by_exchange):
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
            force_auth=self.requires_authentication(
                self.tentacle_config, None, exchange_config_by_exchange, self.exchange_manager
            ),
        )

    @classmethod
    def requires_authentication(
        cls,
        tentacle_config: typing.Optional[dict],
        tentacles_setup_config,
        exchange_config_by_exchange: typing.Optional[dict[str, dict]],
        exchange_manager=None,
        ccxt_rest_exchange_id: typing.Optional[str] = None,
    ) -> bool:
        if tentacle_config is None:
            tentacle_config = {}
            if exchange_config_by_exchange and (
                _tentacles_config := cls.get_tentacle_config(exchange_config_by_exchange)
            ):
                # copy to avoid editing the original tentacle config in load_user_inputs_from_class
                tentacle_config = copy.copy(_tentacles_config)
            if tentacle_config and tentacles_setup_config is not None:
                cls.load_user_inputs_from_class(tentacles_setup_config, tentacle_config)
        if exchange_manager and exchange_manager.exchange and exchange_manager.exchange.connector:
            always_requires_authentication = bool(exchange_manager.exchange.connector.get_option_value(
                enums.ExchangeClientOptions.ALWAYS_REQUIRES_AUTHENTICATION
            ))
        else:
            if exchange_manager is not None:
                ccxt_rest = cls.get_rest_name(exchange_manager)
            elif ccxt_rest_exchange_id is not None:
                ccxt_rest = ccxt_rest_exchange_id
            else:
                ccxt_rest = cls.get_connector_id()
            always_requires_authentication = bool(ccxt_client_util.get_option_value_from_new_ccxt_client(
                ccxt_rest, enums.ExchangeClientOptions.ALWAYS_REQUIRES_AUTHENTICATION
            ))
        return tentacle_config.get(
            commons_constants.CONFIG_FORCE_AUTHENTICATION, always_requires_authentication
        )

    def requires_authentication_for_this_configuration_only(self) -> bool:
        always_requires_authentication = bool(self.get_option_value(
            enums.ExchangeClientOptions.ALWAYS_REQUIRES_AUTHENTICATION,
        ))
        return (
            self.requires_authentication(
                self.tentacle_config, None, {}, self.exchange_manager
            )
            and not always_requires_authentication
        )

    async def request_exchange_to_ensure_authentication(self):
        await self.connector.request_exchange_to_ensure_authentication()

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

    @classmethod
    def get_connector_id(cls) -> str:
        return cls.get_name()

    def get_associated_websocket_exchange_name(self):
        return self.exchange_manager.exchange_name

    def get_adapter_class(self):
        # Override in tentacles when using a custom adapter
        return None

    def get_option_value(
        self, option_key: enums.ExchangeClientOptions
    ) -> typing.Union[bool, float, int, str, None]:
        return self.connector.get_option_value(option_key)

    def supports_order_type(
        self, order_type: enums.TradeOrderType
    ) -> bool:
        return self.connector.supports_order_type(order_type)

    def supports_bundled_orders(
        self, order_type: enums.TradeOrderType
    ) -> bool:
        return self.connector.supports_bundled_orders(order_type)

    def fetch_stop_order_in_different_request(self, symbol: str) -> bool:
        return self.connector.fetch_stop_order_in_different_request(symbol)
    
    def supports_all_symbols_listing(self) -> bool:
        return bool(self.get_option_value(
            enums.ExchangeClientOptions.SUPPORTS_ALL_SYMBOLS_LISTING
        ))

    def lazy_load_markets(self) -> bool:
        return bool(self.get_option_value(
            enums.ExchangeClientOptions.LAZY_LOAD_MARKETS
        ))

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
                self.logger.debug(f"Created order: {logging.get_private_minimized_message_if_necessary(created_order)}")
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
            self.connector.clear_first_consecutive_authentication_error_at()
        except ccxt.InsufficientFunds as e:
            self._on_missing_funds_err(e, order_type, symbol, quantity, price, stop_price)
        except ccxt.MarketClosed as err:
            raise errors.MarketClosedError(f"{symbol} {html_util.get_html_summary_if_relevant(err)}") from err
        except (ccxt.NotSupported, NotImplementedError) as err:
            raise errors.NotSupported(err) from err
        except ccxt.PermissionDenied as err:
            # invalid api key or missing trading rights
            self.connector.set_first_consecutive_authentication_error_at_if_unset()
            raise errors.AuthenticationError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Please make sure that trading permissions are on for this API key."
            ) from err
        except (errors.AuthenticationError, ccxt.AuthenticationError) as err:
            # invalid api key or missing trading rights
            self.connector.set_first_consecutive_authentication_error_at_if_unset()
            raise errors.AuthenticationError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Please make sure that trading permissions are on for this API key."
            ) from err
        except ccxt.DDoSProtection as e:
            # ccxt.DDoSProtection: raised upon rate limit issues,
            # last response data might have details on what is happening
            if self.should_log_on_ddos_exception(e):
                self.connector.log_ddos_error(e)
            raise errors.FailedRequest(
                f"Failed order operation: {e.__class__.__name__} {html_util.get_html_summary_if_relevant(e)}"
            ) from e
        except ccxt.OBMaxOpenOrdersReached as err:
            raise errors.ExchangeMaxOrdersForMarketReachedError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Exchange is refusing this order: the maximum number of orders for this market has been reached."
            ) from err
        except ccxt.OBClosedPositionError as err:
            raise errors.ExchangeClosedPositionError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Exchange is refusing this order request because associated position is closed."
            ) from err
        except ccxt.OrderImmediatelyFillable as err:
            raise errors.ExchangeOrderInstantTriggerError(
                f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                f"Exchange is refusing this order request because associated order would instantly trigger."
            ) from err
        except (errors.OctoBotExchangeError, errors.OrderCreationError):
            # custom error: forward it
            raise
        except Exception as e:
            if not self.is_market_open_for_order_type(symbol, order_type):
                raise errors.UnavailableOrderTypeForMarketError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(e)}. "
                    f"Exchange currently refuses to create orders of type {order_type} on {symbol}."
                ) from e
            self.log_order_creation_error(e, order_type, symbol, quantity, price, stop_price)
            # import traceback      # uncomment for debugging in tests
            # import sys        # uncomment for debugging in tests
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
                    self.logger.error(
                        f"No order exchange id on created order: {logging.get_private_minimized_message_if_necessary(created_order)}"
                    )
                    return None
                exchange_order_id = created_order[ecoc.EXCHANGE_ID.value]
                params = self.add_stop_param_if_necessary(
                    exchange_order_id,
                    self.get_option_value(enums.ExchangeClientOptions.REQUIRES_STOP_PARAM_TO_FETCH_ORDER),
                    order_type,
                    **(get_order_params or {})
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
            # exchange won't let this order create: raise
            raise errors.ExchangeAccountSymbolPermissionError(
                f"Error when creating {symbol} {order_type} order on "
                f"{self.exchange_manager.exchange_name}: {html_util.get_html_summary_if_relevant(err)}"
            ) from err
        except ccxt.OBUntradableSymbol as err:
            raise errors.UntradableSymbolError(
                f"Error when creating {symbol} {order_type} order on "
                f"{self.exchange_manager.exchange_name}: {html_util.get_html_summary_if_relevant(err)}"
            ) from err
        except ccxt.OBInternalSyncError as err:
            raise errors.ExchangeInternalSyncError(
                f"Error when handling {symbol} {order_type} order. "
                f"Exchange is refusing this order request because of sync error "
                f"({html_util.get_html_summary_if_relevant(err)})."
            ) from err
        except ccxt.InsufficientFunds as err:
            self._on_missing_funds_err(err, order_type, symbol, quantity, price, stop_price)
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
        enable_spot_buy_market_with_cost = bool(
            self.get_option_value(enums.ExchangeClientOptions.ENABLE_SPOT_BUY_MARKET_WITH_COST)
        )
        if enable_spot_buy_market_with_cost and self.exchange_manager.is_spot_only:
            if price is None:
                raise errors.NotSupported(
                    f"price is required for buy market orders when "
                    f"{enums.ExchangeClientOptions.ENABLE_SPOT_BUY_MARKET_WITH_COST.value} "
                    f"is {enable_spot_buy_market_with_cost}"
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

    def get_first_consecutive_authentication_error_at(self) -> typing.Optional[float]:
        return self.connector.first_consecutive_authentication_error_at

    async def load_markets_for_symbols(self, symbols: list[str]) -> list[dict]:
        loaded_markets = await self.connector.load_markets_for_symbols(symbols)
        # ensure symbols are updated
        self.symbols.update(
            self.get_all_available_symbols(active_only=True)
        )
        return loaded_markets

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        """
        Override using get_fixed_market_status in exchange tentacle if the default market status is not as expected
        """
        return self.connector.get_market_status(symbol, price_example=price_example, with_fixer=with_fixer)

    async def get_dex_pairs(self, symbols: list[str], **kwargs: dict) -> list[dict]:
        return await self.connector.get_dex_pairs(symbols, **kwargs)

    def uses_demo_trading_instead_of_sandbox(self, exchange_type: enums.ExchangeTypes) -> bool:
        return self.connector.uses_demo_trading_instead_of_sandbox(exchange_type)

    def _apply_contract_size(self, value, contract_size):
        if value is None:
            return value
        return value * contract_size

    async def get_account_id(self, **kwargs: dict) -> str:
        return await self.connector.get_account_id(**kwargs)
    
    async def get_permissions(self, **kwargs: dict) -> list[enums.APIKeyRights]:
        return await self.connector.get_permissions(**kwargs)

    async def ensure_api_key_permissions(self, **kwargs: dict) -> None:
        try:
            permissions = await self.get_permissions(**kwargs)
        except errors.NotSupported:
            return # not supported, skip permission check
        if not permissions:
            raise errors.InvalidAPIKeyPermissionsError("No permissions found")
        if enums.APIKeyRights.READING not in permissions:
            raise errors.InvalidAPIKeyPermissionsError("READING permission is required")
        if enums.APIKeyRights.SPOT_TRADING not in permissions and self.exchange_manager.is_spot_only:
            raise errors.InvalidAPIKeyPermissionsError("SPOT_TRADING permission is required")
        if enums.APIKeyRights.FUTURES_TRADING not in permissions and self.exchange_manager.is_future:
            raise errors.InvalidAPIKeyPermissionsError("FUTURES_TRADING permission is required")
        if enums.APIKeyRights.WITHDRAWALS in permissions and not constants.ALLOW_FUNDS_TRANSFER:
            raise errors.InvalidAPIKeyPermissionsError(
                "WITHDRAWALS permission found, but funds transfer is disabled. Please remove the permission or enable funds transfer."
            )

    def get_orders_broker_parameters(self, **kwargs: dict) -> dict:
        return self.connector.get_orders_broker_parameters(**kwargs)

    def get_max_open_orders_count(self, symbol: str, order_type: enums.TradeOrderType, **kwargs: dict) -> int:
        return self.connector.get_max_open_orders_count(symbol=symbol, order_type=order_type, **kwargs)

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        return self.connector.is_authenticated_request(url=url, method=method, headers=headers, body=body)

    def supports_fetching_balance(self) -> bool:
        return self.connector.supports_fetching_balance()

    async def get_balance(self, **kwargs: dict):
        return await self.connector.get_balance(**kwargs)

    async def get_user_balance(self, user_id: str, **kwargs: dict):
        return await self.connector.get_user_balance(user_id=user_id, **kwargs)

    async def get_symbol_prices(self, symbol: str, time_frame: commons_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit, **kwargs)

    async def get_kline_price(self, symbol: str, time_frame: commons_enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list]:
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

    async def get_all_currencies_price_ticker(self, symbols: typing.Optional[list[str]] = None, **kwargs: dict) -> typing.Optional[dict[str, dict]]:
        return await self.connector.get_all_currencies_price_ticker(symbols=symbols, **kwargs)

    async def refresh_markets(self):
        return await self.connector.load_symbol_markets(
            reload=True, market_filter=self.exchange_manager.market_filter
        )

    def add_stop_param_if_necessary(
        self,
        exchange_order_id: str,
        require_stop_param_when_relevant: bool,
        order_type: typing.Optional[enums.TraderOrderType] = None,
        **kwargs
    ) -> dict:
        if not require_stop_param_when_relevant:
            return kwargs
        params = kwargs or {}
        try:
            if ccxt_enums.OrderFetchParams.STOP.value not in params:
                order_type = (
                    order_type or 
                    self.exchange_manager.exchange_personal_data.orders_manager.get_order(
                        None, exchange_order_id=exchange_order_id
                    ).order_type
                )
                params[ccxt_enums.OrderFetchParams.STOP.value] = (
                    orders.is_stop_order(order_type)
                    or orders.is_take_profit_order(order_type)
                )
        except KeyError as err:
            self.logger.warning(
                f"Order {exchange_order_id} not found in order manager: considering it a regular (no stop/take profit) order {err}"
            )
        return params

    def get_order_additional_params(self, order: "orders.Order") -> dict:
        """
        Returns a dict with exchange specific additional parameters to set before sending the order
        :param order: the order instance wrapping orders details
        :return: the params dict
        """
        params = {}
        if self.exchange_manager.is_future:
            params[ccxt_enums.ExchangeOrderCCXTColumns.REDUCE_ONLY.value] = order.reduce_only
        return {}

    async def get_order(
        self,
        exchange_order_id: str,
        symbol: typing.Optional[str] = None,
        order_type: typing.Optional[enums.TraderOrderType] = None,
        **kwargs: dict
    ) -> dict:
        extended_kwargs = self.add_stop_param_if_necessary(
            exchange_order_id,
            self.get_option_value(enums.ExchangeClientOptions.REQUIRES_STOP_PARAM_TO_FETCH_ORDER),
            order_type,
            **(kwargs or {})
        )
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
            if self.get_option_value(enums.ExchangeClientOptions.REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES):
                if self.get_option_value(enums.ExchangeClientOptions.REQUIRE_RECENT_TRADES_FROM_CLOSED_ORDERS):
                    raise errors.NotSupported("REQUIRE_RECENT_TRADES_FROM_CLOSED_ORDERS and REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES are incompatible")
                return await self._get_closed_orders_from_my_recent_trades(
                    symbol=symbol, since=since, limit=limit, **kwargs
                )
            raise

    @fetching_orders_request
    async def get_cancelled_orders(
        self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict
    ) -> list:
        if not self.get_option_value(enums.ExchangeClientOptions.SUPPORT_FETCHING_CANCELLED_ORDERS):
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
        if not self.get_option_value(enums.ExchangeClientOptions.REQUIRE_ORDER_FEES_FROM_TRADES) \
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
            or not self.get_option_value(enums.ExchangeClientOptions.REQUIRE_ORDER_FEES_FROM_TRADES)
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
        if self.get_option_value(enums.ExchangeClientOptions.REQUIRE_RECENT_TRADES_FROM_CLOSED_ORDERS):
            if self.get_option_value(enums.ExchangeClientOptions.REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES):
                raise errors.NotSupported("REQUIRE_RECENT_TRADES_FROM_CLOSED_ORDERS and REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES are incompatible")
            return await self.get_closed_orders(
                symbol=symbol, since=since, limit=limit, **kwargs
            )
        return await self.connector.get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_user_recent_trades(self, user_id: str, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_user_recent_trades(user_id=user_id, symbol=symbol, since=since, limit=limit, **kwargs)

    async def cancel_all_orders(self, symbol: str = None, **kwargs: dict) -> None:
        return await self.connector.cancel_all_orders(symbol=symbol, **kwargs)

    async def cancel_order(
        self, exchange_order_id: str, symbol: str, order_type: enums.TraderOrderType, **kwargs: dict
    ) -> enums.OrderStatus:
        extended_kwargs = self.add_stop_param_if_necessary(
            exchange_order_id,
            self.get_option_value(enums.ExchangeClientOptions.REQUIRES_STOP_PARAM_TO_CANCEL_ORDER),
            order_type,
            **(kwargs or {})
        )
        return await self.connector.cancel_order(exchange_order_id, symbol, order_type, **extended_kwargs)

    def get_trade_fee(self, symbol: str, order_type: enums.TraderOrderType, quantity, price, taker_or_maker) -> dict:
        return self.connector.get_trade_fee(symbol, order_type, quantity, price, taker_or_maker)

    def get_fees(self, symbol):
        return self.connector.get_fees(symbol)

    def get_pair_from_exchange(self, pair, error_on_missing=True) -> str:
        return self.connector.get_pair_from_exchange(pair, error_on_missing=error_on_missing)

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
            active_only=False if self.get_option_value(
                enums.ExchangeClientOptions.INCLUDE_DISABLED_SYMBOLS_IN_AVAILABLE_SYMBOLS
            ) else active_only
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
        if position is None and self.get_option_value(enums.ExchangeClientOptions.REQUIRES_MOCKED_EMPTY_POSITION):
            # this exchange does not support empty position fetching, create an empty position from available data
            return await self.get_mocked_empty_position(symbol, **kwargs)
        return position

    async def get_positions(self, symbols=None, **kwargs: dict) -> list:
        """
        Get the current user position list
        :return: the user position list
        """
        if not self.get_option_value(enums.ExchangeClientOptions.REQUIRES_SYMBOL_FOR_EMPTY_POSITION):
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
        Called when requiresMockedEmptyPosition is True and a fetched position is None
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
        if self.get_option_value(enums.ExchangeClientOptions.SUPPORTS_SET_MARGIN_TYPE):
            try:
                return await self.connector.set_symbol_margin_type(symbol=symbol, isolated=isolated, **kwargs)
            except ccxt.PermissionDenied as err:
                # invalid api key or missing trading rights
                raise errors.AuthenticationError(
                    f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                    f"Please make sure that trading permissions are on for this API key."
                ) from err
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
        return bool(self.get_option_value(enums.ExchangeClientOptions.IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH))

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
