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
import asyncio
import typing
import decimal
import time
import copy
import contextlib

import octobot_commons.constants
import octobot_commons.enums as common_enums
import octobot_commons.logging as logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.html_util as html_util

import octobot_trading.constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.exchanges
import octobot_trading.accounts


class AbstractExchange(octobot_trading.accounts.AbstractAccount):
    USER_INPUT_TENTACLE_TYPE = common_enums.UserInputTentacleTypes.EXCHANGE
    BUY_STR = enums.TradeOrderSide.BUY.value
    SELL_STR = enums.TradeOrderSide.SELL.value

    # should be overridden locally to match exchange support
    SUPPORTED_ELEMENTS = {
        enums.ExchangeTypes.FUTURE.value: {
            # order that should be self-managed by OctoBot
            enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                enums.TraderOrderType.STOP_LOSS,
                enums.TraderOrderType.STOP_LOSS_LIMIT,
                enums.TraderOrderType.TAKE_PROFIT,
                enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                enums.TraderOrderType.TRAILING_STOP,
                enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            # format: dict of bundled types by base order type
            # ex: SUPPORTED_BUNDLED_ORDERS[enums.TraderOrderType.BUY_MARKET] = \
            # [enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.TAKE_PROFIT]
            enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        },
        enums.ExchangeTypes.SPOT.value: {
            # order that should be self-managed by OctoBot
            enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS.value: [
                enums.TraderOrderType.STOP_LOSS,
                enums.TraderOrderType.STOP_LOSS_LIMIT,
                enums.TraderOrderType.TAKE_PROFIT,
                enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                enums.TraderOrderType.TRAILING_STOP,
                enums.TraderOrderType.TRAILING_STOP_LIMIT
            ],
            # order that can be bundled together to create them all in one request
            # format: dict of bundled types by base order type
            # ex: SUPPORTED_BUNDLED_ORDERS[enums.TraderOrderType.BUY_MARKET] = \
            # [enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.TAKE_PROFIT]
            enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS.value: {},
        }
    }
    ACCOUNTS = {}

    def __init__(self, config, exchange_manager, exchange_config_by_exchange: typing.Optional[dict[str, dict]]):
        super().__init__()
        self.config: dict[str, typing.Any] = config
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = exchange_manager
        self.connector: "octobot_trading.exchanges.connectors.AbstractConnector" = None # type: ignore
        self.is_initialized: bool = False

        self.tentacle_config: dict[str, typing.Any] = {}

        # Initialized when initializing exchange connector
        self.symbols: set[str] = set()
        self.time_frames: set[str] = set()

        # exchange name related attributes
        self.name: str = self.exchange_manager.exchange_class_string
        self.logger: logging.BotLogger = logging.get_logger(f"{self.__class__.__name__}[{self.name}]")

        # exchange related constants
        self.allowed_time_lag: float = octobot_trading.constants.DEFAULT_EXCHANGE_TIME_LAG
        self.current_account: enums.AccountTypes = enums.AccountTypes.CASH

        self.is_unreachable: bool = False

        self._creating_exchange_order_descriptions: set[str] = set()
        self._enable_create_order_retrier: bool = True

        if exchange_config_by_exchange and (
            tencles_config := self.get_tentacle_config(exchange_config_by_exchange)
        ):
            # copy to avoid editing the original tentacle config in load_user_inputs_from_class
            self.tentacle_config = copy.copy(tencles_config)
        if self.exchange_manager.tentacles_setup_config is not None:
            self.load_user_inputs_from_class(self.exchange_manager.tentacles_setup_config, self.tentacle_config)

    async def initialize(self, force=False, **kwargs):
        if not self.is_initialized or force:
            await self.initialize_impl(**kwargs)
            self.is_initialized = True
            return True
        return False

    async def initialize_impl(self):
        """
        Contains the exchange initialization code
        """
        raise NotImplementedError("initialize_impl not implemented")

    async def stop(self) -> None:
        """
        Implement the exchange stopping process
        """
        raise NotImplementedError("stop not implemented")

    @classmethod
    def get_name(cls) -> str:
        """
        :return: the exchange name
        """
        raise NotImplementedError("get_name is not implemented")

    @classmethod
    def is_simulated_exchange(cls) -> bool:
        """
        :return: True if this implementation corresponds to a simulated exchange
        """
        return False

    def authenticated(self) -> bool:
        return False if self.connector is None else self.connector.is_authenticated

    @classmethod
    def is_default_exchange(cls) -> bool:
        """
        :return: True if this implementation corresponds to a default exchange implementation
        """
        return False

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        """
        :param exchange_candidate_name: the exchange name
        :return: True if this implementation supports the exchange name
        """
        raise NotImplementedError("is_supporting_exchange is not implemented")

    @classmethod
    def is_supporting_sandbox(cls) -> bool:
        """
        :return: True if the exchange is supporting sandbox mode
        """
        return True

    def get_exchange_current_time(self):
        """
        :return: the exchange current time in seconds
        """
        raise NotImplementedError("get_exchange_current_time is not implemented")

    def get_uniform_timestamp(self, timestamp):
        """
        WARNING: does not check if the timestamp is already in the right form, better using get_uniformized_timestamp
        to be sure to keep the right format and uniformize if necessary only
        :param timestamp: the timestamp to uniformize
        :return: the uniformized timestamp
        """
        raise NotImplementedError("get_uniform_timestamp not implemented")

    def get_supported_elements(self, element_key: enums.ExchangeSupportedElements):
        """
        :return: the supported elements such as order type and bundle orders for the current exchange and trading type
        """
        exchange_type_key = enums.ExchangeTypes.FUTURE if self.exchange_manager.is_future \
            else enums.ExchangeTypes.SPOT
        return self.__class__.SUPPORTED_ELEMENTS[exchange_type_key.value][element_key.value]

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        """
        Return the market status
        :param symbol: the symbol
        :param price_example: a price example to be used in MarketStatusFixer
        :param with_fixer: when True, return a new instance of MarketStatusFixer
        :return: market status dict
        """
        raise NotImplementedError("get_market_status is not implemented")

    async def get_balance(self, **kwargs: dict):
        """
        :return: current user balance from exchange
        """
        raise NotImplementedError("get_balance is not implemented")

    async def get_user_balance(self, user_id: str, **kwargs: dict):
        """
        :param user_id: the user id
        :return: current user balance from exchange
        """
        raise NotImplementedError("get_user_balance is not implemented")

    async def get_symbol_prices(self,
                                symbol: str,
                                time_frame: common_enums.TimeFrames,
                                limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        """
        Return the candle history
        :param symbol: the symbol
        :param time_frame: the timeframe
        :param limit: the history limit size
        :return: the symbol candle history
        """
        raise NotImplementedError("get_symbol_prices is not implemented")

    async def get_kline_price(self,
                              symbol: str,
                              time_frame: common_enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list]:
        """
        Return the symbol current kline dict
        :param symbol: the symbol
        :param time_frame: the timeframe
        :return: the symbol current klint
        """
        raise NotImplementedError("get_symbol_prices is not implemented")

    async def get_order_book(self, symbol: str, limit: int = 5, **kwargs: dict) -> typing.Optional[dict]:
        """
        Return the current symbol order book snapshot
        :param symbol: the symbol
        :param limit: the order book size
        :return: the order book snapshot
        """
        raise NotImplementedError("get_order_book is not implemented")

    async def get_recent_trades(self, symbol: str, limit: int = 50, **kwargs: dict) -> typing.Optional[list]:
        """
        Return the last "limit" recent trades for the specified symbol
        :param symbol: the symbol
        :param limit: the recent trade history size
        :return: the recent trade history for the symbol
        """
        raise NotImplementedError("get_recent_trades is not implemented")

    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        """
        Get the symbol ticker from the exchange
        :param symbol: the symbol
        :return: the symbol ticker
        """
        raise NotImplementedError("get_price_ticker is not implemented")

    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[list]:
        """
        Get all exchange currency tickers
        :return: the list of exchange currencies tickers
        """
        raise NotImplementedError("get_all_currencies_price_ticker is not implemented")

    async def refresh_markets(self):
        """
        Refresh the exchange markets
        """
        raise NotImplementedError("refresh_markets is not implemented")

    async def get_order(self, exchange_order_id: str, symbol: str = None, **kwargs: dict) -> dict:
        """
        Get the order data from the exchange
        :param exchange_order_id: the order id on exchange
        :param symbol: the order symbol
        :return: the order data
        """
        raise NotImplementedError("get_order is not implemented")

    async def get_all_orders(self, symbol: str = None, since: int = None,
                             limit: int = None, **kwargs: dict) -> list:
        """
        Get the current user order list
        :param symbol: the order symbol
        :param since: the starting timestamp
        :param limit: the list limit size
        :return: the user order list
        """
        raise NotImplementedError("get_all_orders is not implemented")

    async def get_open_orders(self, symbol: str = None, since: int = None,
                              limit: int = None, **kwargs: dict) -> list:
        """
        Get the current user open order list
        :param symbol: the order symbol
        :param since: the starting timestamp
        :param limit: the list limit size
        :return: the user open order list
        """
        raise NotImplementedError("get_open_orders is not implemented")
    
    async def get_user_open_orders(self, user_id: str, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        """
        Get the user open order list
        :param user_id: the user id
        :param symbol: the order symbol
        :param since: the starting timestamp
        :param limit: the list limit size
        :return: the user open order list
        """
        raise NotImplementedError("get_user_open_orders is not implemented")
    
    async def get_closed_orders(self, symbol: str = None, since: int = None,
                                limit: int = None, **kwargs: dict) -> list:
        """
        Get the user closed order list
        :param symbol: the order symbol
        :param since: the starting timestamp
        :param limit: the list limit size
        :return: the user closed order list
        """
        raise NotImplementedError("get_closed_orders is not implemented")

    async def get_cancelled_orders(self, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        """
        Get the user closed order list
        :param symbol: the order symbol
        :param since: the starting timestamp
        :param limit: the list limit size
        :return: the user closed order list
        """
        raise NotImplementedError("get_cancelled_orders is not implemented")

    async def get_my_recent_trades(self, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        """
        Get the user recent trades
        :param symbol: trades symbol
        :param since: the trade history starting timestamp
        :param limit: the history limit size
        :return: the user trades history list
        """
        raise NotImplementedError("get_my_recent_trades is not implemented")
    
    async def get_user_recent_trades(self, user_id: str, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        """
        Get the user recent trades
        :param user_id: the user id
        :param symbol: trades symbol
        :param since: the trade history starting timestamp
        :param limit: the history limit size
        :return: the user trades history list
        """
        raise NotImplementedError("get_user_recent_trades is not implemented")
    
    async def get_leverage_tiers(self, symbols: list = None, **kwargs: dict)-> dict:
        """
        :param symbols: the symbols or None
        :return: the current leverage tiers by symbols
        """
        raise NotImplementedError("get_leverage_tiers is not implemented")

    async def cancel_all_orders(self, symbol: str = None, **kwargs: dict) -> None:
        """
        Cancel all orders on the exchange
        :param symbol: the orders symbol
        """
        raise NotImplementedError("cancel_all_orders is not implemented")

    async def cancel_order(
            self, exchange_order_id: str, symbol: str, order_type: enums.TraderOrderType, **kwargs: dict
    ) -> enums.OrderStatus:
        """
        Cancel a order on the exchange
        :param exchange_order_id: the order id on exchange
        :param symbol: the order symbol
        :param order_type: the type of the order
        :return: True if the order is successfully cancelled
        """
        raise NotImplementedError("cancel_order is not implemented")

    async def create_order(self, order_type: enums.TraderOrderType, symbol: str, quantity: decimal.Decimal,
                           price: decimal.Decimal = None, stop_price: decimal.Decimal = None,
                           side: enums.TradeOrderSide = None, current_price: decimal.Decimal = None,
                           reduce_only: bool = False, params: dict = None) \
            -> typing.Optional[dict]:
        """
        Create a order on the exchange
        :param order_type: the order type
        :param symbol: the order symbol
        :param quantity: the order quantity
        :param price: the order price
        :param stop_price: the order stop price
        :param side: the order side
        :param current_price: the symbol current price
        :param params: the order request params
        :return: the created order dict
        """
        raise NotImplementedError("create_order is not implemented")

    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        """
        Get a position
        :param symbol: the symbol
        :return: the user position
        """
        raise NotImplementedError("get_position is not implemented")

    async def get_positions(self, symbols=None, **kwargs: dict) -> list:
        """
        Get the positions list
        :param symbols: the symbols or None
        :return: the user position list
        """
        raise NotImplementedError("get_positions is not implemented")
    
    async def get_closed_positions(self, symbols=None, **kwargs: dict) -> list:
        """
        Get the closed position list
        :param symbols: the symbols or None
        :return: the closed position list
        """
        raise NotImplementedError("get_closed_positions is not implemented")
    
    async def get_user_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        """
        Get the user position list
        :param user_id: the user id
        :param symbols: the symbols or None
        :return: the user position list
        """
        raise NotImplementedError("get_user_positions is not implemented")

    async def get_user_closed_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        """
        Get the user closed position list
        :param user_id: the user id
        :param symbols: the symbols or None
        :return: the user closed position list
        """
        raise NotImplementedError("get_user_closed_positions is not implemented")

    def get_order_additional_params(self, order) -> dict:
        """
        Returns a dict with exchange specific additional parameters to set before sending the order
        :param order: the order instance wrapping orders details
        :return: the params dict
        """
        return {}

    def supports_bundled_order_on_order_creation(self, base_order, bundled_order_type) -> bool:
        """
        Returns True when this exchange supports orders created upon other orders fill (ex: a stop loss created at
        the same time as a buy order)
        :param base_order: the first order of the combo
        :param bundled_order_type: the type of the order that we try to bundle with base_order
        :return: True if an order of type tied_order_type can be pushed alongside base_order to the exchange
        in one request
        """
        try:
            return bundled_order_type in self.get_supported_elements(
                enums.ExchangeSupportedElements.SUPPORTED_BUNDLED_ORDERS
            )[base_order.order_type]
        except KeyError:
            return False

    def get_bundled_order_parameters(self, order, stop_loss_price=None, take_profit_price=None) -> dict:
        """
        Returns the updated params when this exchange supports orders created upon other orders fill
        (ex: a stop loss created at the same time as a buy order)
        :param order: the initial order
        :param stop_loss_price: the bundled order stop_loss price
        :param take_profit_price: the bundled order take_profit price
        :return: A dict with the necessary parameters to create the bundled order on exchange alongside the
        base order in one request
        """
        raise NotImplementedError("get_bundled_order_parameters is not implemented")

    def is_supported_order_type(self, order_type: enums.TraderOrderType) -> bool:
        """
        Check if the order type is supported by the current exchange instance
        Should be used to know if we should simulate this order or create it on the exchange
        :param order_type: the order type, should be a member of enums.TraderOrderType
        :return: True if the order type is supported by the exchange, else False
        """
        return order_type not in self.get_supported_elements(enums.ExchangeSupportedElements.UNSUPPORTED_ORDERS)

    def is_market_open_for_order_type(self, symbol: str, order_type: enums.TraderOrderType) -> bool:
        """
        Override if necessary
        """
        return True

    def get_trade_fee(self, symbol: str, order_type: enums.TraderOrderType, quantity, price, taker_or_maker):
        """
        Calculates fees resulting to a trade
        :param symbol: the symbol
        :param order_type: the order type
        :param quantity: the trade quantity
        :param price: the trade price
        :param taker_or_maker: if the trade was taker or maker
        :return: the trade fees
        """
        raise NotImplementedError("get_trade_fee is not implemented")

    def get_fees(self, symbol):
        """
        :param symbol: the symbol
        :return: the symbol fees dict
        """
        raise NotImplementedError("get_fees is not implemented")

    def get_pair_from_exchange(self, pair) -> str:
        """
        :param pair: the pair
        :return: the symbol associated to the pair
        """
        raise NotImplementedError("get_pair_from_exchange is not implemented")

    def get_split_pair_from_exchange(self, pair) -> (str, str):
        """
        :param pair: the pair
        :return: the currency, market tuple associated to the pair
        """
        raise NotImplementedError("get_split_pair_from_exchange is not implemented")

    def get_exchange_pair(self, pair) -> str:
        """
        :param pair: the pair
        :return: the exchange pair from an uniformized symbol
        """
        raise NotImplementedError("get_exchange_pair is not implemented")

    def get_pair_cryptocurrency(self, pair) -> str:
        """
        :param pair: the pair
        :return: the currency associated to the input pair
        """
        raise NotImplementedError("get_pair_cryptocurrency is not implemented")

    def get_default_balance(self):
        """
        :return: the default balance dict from exchange
        """
        raise NotImplementedError("get_default_balance is not implemented")

    def get_rate_limit(self):
        """
        :return: the exchange rate limit
        """
        raise NotImplementedError("get_default_balance is not implemented")

    async def switch_to_account(self, account_type: enums.AccountTypes):
        """
        Request to switch account from exchange
        :param account_type: the account destination
        """
        raise NotImplementedError("switch_to_account is not available on this exchange")

    async def get_sub_account_list(self):
        """
        :return: the exchange sub account list if supported by the exchange
        """
        raise NotImplementedError("get_sub_account_list is not available on this exchange")
    
    async def retry_till_success(self, timeout, request_func, *args, **kwargs):
        return await self._retry_until(timeout, 0, request_func, *args, **kwargs)

    async def retry_n_time(self, n_times, request_func, *args, **kwargs):
        return await self._retry_until(0, n_times, request_func, *args, **kwargs)

    async def _retry_until(self, timeout, n_times, request_func, *args, **kwargs):
        t0 = time.time()
        minimal_interval = 0.1
        attempt = 1
        latest_error = None
        latest_request_url = None
        while (timeout != 0 and time.time() - t0 < timeout) or (n_times != 0 and attempt <= n_times + 1):
            last_request_time = time.time()
            try:
                result = await request_func(*args, **kwargs)
                if attempt > 1:
                    self.logger.debug(f"Request retrier success for {request_func.__name__} after {attempt} attempts")
                return result
            except errors.FailedRequest as err:
                latest_error = err
                latest_request_url = self.get_latest_request_url()
                self.logger.debug(
                    f"Request retrier failed for {request_func.__name__}({args} {kwargs}) "
                    f"(attempt {attempt}) ({html_util.get_html_summary_if_relevant(err)})"
                )
                if time.time() - last_request_time < minimal_interval:
                    await asyncio.sleep(minimal_interval)
                attempt += 1
        latest_error = latest_error or RuntimeError("unknown error, this is unexpected, latest_error should be set")
        raise errors.FailedRequest(
            f"Failed to successfully run {request_func.__name__}(args={args}, kwargs={kwargs}) request after {attempt} "
            f"attempts. Latest error: {latest_error} ({latest_error.__class__.__name__}). "
            f"Last request url: {latest_request_url}"
        ) from latest_error

    """
    Parsers
    """

    def parse_balance(self, balance):
        """
        :param balance: the balance dict
        :return: the uniformized balance dict
        """
        raise NotImplementedError("parse_balance is not implemented")

    def parse_trade(self, trade):
        """
        :param trade: the trade dict
        :return: the uniformized trade dict
        """
        raise NotImplementedError("parse_trade is not implemented")

    def parse_order(self, order):
        """
        :param order: the order dict
        :return: the uniformized order dict
        """
        raise NotImplementedError("parse_order is not implemented")

    def parse_ticker(self, ticker):
        """
        :param ticker: the ticker dict
        :return: the uniformized ticker dict
        """
        raise NotImplementedError("parse_ticker is not implemented")

    def parse_ohlcv(self, ohlcv):
        """
        :param ohlcv: the ohlcv dict
        :return: the uniformized ohlcv dict
        """
        raise NotImplementedError("parse_ohlcv is not implemented")

    def parse_order_book(self, order_book):
        """
        :param order_book: the order book data
        :return: the uniformized order book data
        """
        raise NotImplementedError("parse_order_book is not implemented")

    def parse_order_book_ticker(self, order_book_ticker):
        """
        :param order_book_ticker: the order book ticker
        :return: the uniformized order book ticker
        """
        raise NotImplementedError("parse_order_book_ticker is not implemented")

    def parse_timestamp(self, data_dict, timestamp_key, default_value=None, ms=False):
        """
        Uniformize a raw timestamp from an input dict
        :param data_dict: the input dict
        :param timestamp_key: the timestamp dict in the input dict
        :param default_value: the default timestamp value
        :param ms: when True, return the timestamp in milliseconds
        :return: the uniformized timestamp
        """
        raise NotImplementedError("parse_timestamp is not implemented")

    def parse_currency(self, currency):
        """
        :param currency: the raw currency
        :return: the uniformized currency
        """
        raise NotImplementedError("parse_currency is not implemented")

    def parse_order_id(self, order):
        """
        :param order: the order dict
        :return: the order id
        """
        raise NotImplementedError("parse_order_id is not implemented")

    def parse_order_symbol(self, order):
        """
        :param order: the order dict
        :return: the order symbol
        """
        raise NotImplementedError("parse_order_symbol is not implemented")

    def parse_side(self, side):
        """
        :param side: the raw side
        :return: the TradeOrderSide related to the side
        """
        raise NotImplementedError("parse_side is not implemented")

    def parse_account(self, account):
        """
        :param account: the raw account
        :return: the AccountTypes related to the account
        """
        raise NotImplementedError("parse_account is not implemented")

    def get_latest_request_url(self) -> str:
        """
        :return: the URL of the last request
        """
        return self.connector.get_latest_request_url()

    """
    Uniformization
    """

    def need_to_uniformize_timestamp(self, timestamp):
        """
        Return True if the timestamp should be uniformized
        :param timestamp: the timestamp to check
        :return: True if the timestamp should be uniformized
        """
        return not timestamp_util.is_valid_timestamp(timestamp)

    def get_uniformized_timestamp(self, timestamp):
        """
        Uniformize a timestamp
        :param timestamp: the timestamp to uniform
        :return: the timestamp uniformized
        """
        if self.need_to_uniformize_timestamp(timestamp):
            return self.get_uniform_timestamp(timestamp)
        return timestamp

    def uniformize_candles_if_necessary(self, candle_or_candles):
        """
        Uniform timestamps of a list of candles or a candle
        :param candle_or_candles: a list of candles or a candle to be uniformized
        :return: the list of candles or the candle uniformized
        """
        if candle_or_candles:  # TODO improve
            if isinstance(candle_or_candles[0], list):
                if self.need_to_uniformize_timestamp(
                        candle_or_candles[0][common_enums.PriceIndexes.IND_PRICE_TIME.value]):
                    self.uniformize_candles_timestamps(candle_or_candles)
            else:
                if self.need_to_uniformize_timestamp(candle_or_candles[common_enums.PriceIndexes.IND_PRICE_TIME.value]):
                    self.uniformize_candle_timestamps(candle_or_candles)
        return candle_or_candles

    def uniformize_candles_timestamps(self, candles):
        """
        Uniformize a list candle timestamps
        :param candles: the list of candles to uniformize
        """
        for candle in candles:
            self.uniformize_candle_timestamps(candle)

    def uniformize_candle_timestamps(self, candle):
        """
        Uniformize a candle timestamp
        :param candle: the candle to uniformize
        """
        candle[common_enums.PriceIndexes.IND_PRICE_TIME.value] = \
            self.get_uniform_timestamp(candle[common_enums.PriceIndexes.IND_PRICE_TIME.value])

    def get_candle_since_timestamp(self, time_frame, count):
        """
        :param time_frame: the time frame to use
        :param count: the number of candle
        :return: the timestamp since "count" candles
        """
        return self.get_exchange_current_time() - (common_enums.TimeFramesMinutes[time_frame]
                                                   * octobot_commons.constants.MSECONDS_TO_MINUTE
                                                   * count)

    def get_max_handled_pair_with_time_frame(self) -> int:
        """
        :return: the maximum number of simultaneous pairs * time_frame that this exchange can handle.
        """
        return self.connector.get_max_handled_pair_with_time_frame()

    def get_additional_connector_config(self):
        """
        :return: a dict with additional elements to give to the connector constructor
        """
        return {}

    @classmethod
    def is_configurable(cls):
        """
        Override if the exchange is allowed to be configured
        """
        return False

    def should_log_on_ddos_exception(self, _) -> bool:
        """
        Override when necessary
        """
        return True

    def log_order_creation_error(self, error, order_type, symbol, quantity, price, stop_price):
        order_desc = f"order_type: {order_type}, symbol: {symbol}, quantity: {str(quantity)}, price: {str(price)}," \
                     f" stop_price: {str(stop_price)}"
        log_func = self.logger.error if self._enable_create_order_retrier else self.logger.warning
        log_func(
            f"Failed to create order : {error.__class__.__name__} {html_util.get_html_summary_if_relevant(error)}: "
            f"({order_desc})"
        )

    def handle_token_error(self, error):
        self.logger.error(f"Exchange configuration is invalid : please check your configuration ! "
                          f"({error.__class__.__name__}: {html_util.get_html_summary_if_relevant(error)})")

    @contextlib.contextmanager
    def skipped_create_order_retry(self):
        previous_enable_create_order_retrier = self._enable_create_order_retrier
        try:
            self._enable_create_order_retrier = False
            yield
        finally:
            self._enable_create_order_retrier = previous_enable_create_order_retrier

    @contextlib.contextmanager
    def creating_order(
        self, side: enums.TradeOrderSide, symbol: str, quantity: decimal.Decimal, price: decimal.Decimal
    ):
        desc = self._get_order_description(side, symbol, quantity, price)
        try:
            self._creating_exchange_order_descriptions.add(desc)
            yield
        finally:
            try:
                self._creating_exchange_order_descriptions.remove(desc)
            except KeyError:
                self.logger.error(f"Failed to remove {desc} from exchange order descriptions")

    def is_creating_order(
        self, order: dict, symbol: str
    ) -> bool:
        try:
            quantity = decimal.Decimal(str(order[enums.ExchangeConstantsOrderColumns.AMOUNT.value] or 0))
        except decimal.DecimalException:
            quantity = octobot_trading.constants.ZERO
        try:
            price = decimal.Decimal(str(
                order[enums.ExchangeConstantsOrderColumns.PRICE.value]
                # when fetching stop/tp orders PRICE might not be set, also check STOP_PRICE and TAKE_PROFIT_PRICE
                or order.get(enums.ExchangeConstantsOrderColumns.STOP_PRICE.value, 0)
                or order.get(enums.ExchangeConstantsOrderColumns.TAKE_PROFIT_PRICE.value, 0)
                or 0
            ))
        except decimal.DecimalException:
            price = octobot_trading.constants.ZERO
        side = enums.TradeOrderSide(
            str(order[enums.ExchangeConstantsOrderColumns.SIDE.value]) or enums.TradeOrderSide.BUY.value
        )
        return self._get_order_description(side, symbol, quantity, price) in self._creating_exchange_order_descriptions

    def _get_order_description(
        self, side: enums.TradeOrderSide, symbol: str, quantity: decimal.Decimal, price: decimal.Decimal
    ) -> str:
        return (
            f"{side.value if side else None}-{symbol}-"
            f"{float(quantity) if quantity else None}-{float(price) if price else None}"
        )

    @classmethod
    def get_tentacle_config(
        cls, exchange_config_by_exchange: dict[str, dict]
    ) -> typing.Optional[dict]:
        """
        Exchange config can be stored using exchange names and class names
        when taken from exchange_config_by_exchange, this is expected
        """
        exchange_name = cls.get_name()
        if exchange_name in exchange_config_by_exchange:
            return exchange_config_by_exchange[exchange_name]
        elif cls.__name__ in exchange_config_by_exchange:
            return exchange_config_by_exchange[cls.__name__]
        return None
