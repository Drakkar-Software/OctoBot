#  Drakkar-Software OctoBot
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

import logging

from ccxt.async_support import OrderNotFound, BaseError, InsufficientFunds
from ccxt.base.errors import ExchangeNotAvailable, InvalidNonce

from config.config import decrypt
from config import CONFIG_EXCHANGES, CONFIG_EXCHANGE_KEY, CONFIG_EXCHANGE_SECRET, CONFIG_EXCHANGE_PASSWORD, \
    CONFIG_PORTFOLIO_FREE, CONFIG_PORTFOLIO_USED, CONFIG_PORTFOLIO_TOTAL, CONFIG_PORTFOLIO_INFO, TraderOrderType, \
    ExchangeConstantsMarketPropertyColumns, CONFIG_DEFAULT_FEES, ExchangeConstantsOrderColumns as ecoc, OrderStatus
from trading.exchanges.abstract_exchange import AbstractExchange
from trading.exchanges.exchange_market_status_fixer import ExchangeMarketStatusFixer
from tools.initializable import Initializable
from tools.dict_util import get_value_or_default


class RESTExchange(AbstractExchange, Initializable):
    """
    CCXT library wrapper
    """

    def __init__(self, config, exchange_type, exchange_manager):
        AbstractExchange.__init__(self, config, exchange_type)
        Initializable.__init__(self)
        self.exchange_manager = exchange_manager

        # ccxt client
        self.client = None

        # balance additional info
        self.info_list = None
        self.free = None
        self.used = None
        self.total = None

        # We will need to create the rest client and fetch exchange config
        self.create_client()

        self.all_currencies_price_ticker = None

    async def initialize_impl(self):
        try:
            await self.client.load_markets()
        except ExchangeNotAvailable as e:
            self.logger.error(f"initialization impossible: {e}")

    def get_symbol_data(self, symbol):
        return self.exchange_manager.get_symbol_data(symbol)

    def get_personal_data(self):
        return self.exchange_manager.get_personal_data()

    # ccxt exchange instance creation
    def create_client(self):
        if self.exchange_manager.ignore_config or self.exchange_manager.check_config(self.get_name()):
            try:
                if self.exchange_manager.ignore_config or not self.exchange_manager.should_decrypt_token(self.logger):
                    key = ""
                    secret = ""
                    password = ""
                else:
                    config_exchange = self.config[CONFIG_EXCHANGES][self.name]
                    key = decrypt(config_exchange[CONFIG_EXCHANGE_KEY])
                    secret = decrypt(config_exchange[CONFIG_EXCHANGE_SECRET])
                    password = decrypt(config_exchange[CONFIG_EXCHANGE_PASSWORD]) \
                        if CONFIG_EXCHANGE_PASSWORD in config_exchange else None

                self.client = self.exchange_type({
                    'apiKey': key,
                    'secret': secret,
                    'password': password,
                    'verbose': False,
                    'enableRateLimit': True
                })
            except Exception as e:
                self.exchange_manager.handle_token_error(e, self.logger)
                self.client = self.exchange_type({'verbose': False})
        else:
            self.client = self.exchange_type({'verbose': False})
            self.logger.error("configuration issue: missing login information !")
        self.client.logger.setLevel(logging.INFO)

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        try:
            if with_fixer:
                return ExchangeMarketStatusFixer(self.client.find_market(symbol), price_example).get_market_status()
            else:
                return self.client.find_market(symbol)
        except Exception as e:
            self.logger.error(f"Fail to get market status of {symbol}: {e}")
            return {}

    def get_client(self):
        return self.client

    # total (free + used), by currency
    async def get_balance(self):
        try:
            balance = await self.client.fetch_balance()

            # store portfolio global info
            self.info_list = balance[CONFIG_PORTFOLIO_INFO]
            self.free = balance[CONFIG_PORTFOLIO_FREE]
            self.used = balance[CONFIG_PORTFOLIO_USED]
            self.total = balance[CONFIG_PORTFOLIO_TOTAL]

            # remove not currency specific keys
            balance.pop(CONFIG_PORTFOLIO_INFO, None)
            balance.pop(CONFIG_PORTFOLIO_FREE, None)
            balance.pop(CONFIG_PORTFOLIO_USED, None)
            balance.pop(CONFIG_PORTFOLIO_TOTAL, None)

            self.get_personal_data().set_portfolio(balance)

        except InvalidNonce as e:
            self.logger.error(f"Error when loading {self.get_name()} real trader portfolio: {e}. "
                              f"To fix this, please synchronize your computer's clock. ")
            raise e

    async def get_symbol_prices(self, symbol, time_frame, limit=None, return_list=True):
        if limit:
            candles = await self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit)
        else:
            candles = await self.client.fetch_ohlcv(symbol, time_frame.value)

        self.exchange_manager.uniformize_candles_if_necessary(candles)

        self.get_symbol_data(symbol).update_symbol_candles(time_frame, candles, replace_all=True)

    # return up to ten bidasks on each side of the order book stack
    async def get_order_book(self, symbol, limit=5):
        order_book = await self.client.fetch_order_book(symbol, limit)
        self.get_symbol_data(symbol).update_order_book(order_book)

    async def get_recent_trades(self, symbol, limit=50):
        trades = await self.client.fetch_trades(symbol, limit=limit)
        self.get_symbol_data(symbol).update_recent_trades(trades)

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    async def get_price_ticker(self, symbol):
        try:
            self.get_symbol_data(symbol).update_symbol_ticker(await self.client.fetch_ticker(symbol))
        except BaseError as e:
            self.logger.error(f"Failed to get_price_ticker {e}")

    async def get_all_currencies_price_ticker(self):
        try:
            self.all_currencies_price_ticker = await self.client.fetch_tickers()
            return self.all_currencies_price_ticker
        except BaseError as e:
            self.logger.error(f"Failed to get_all_currencies_price_ticker {e}")
            return None

    # ORDERS
    async def get_order(self, order_id, symbol=None):
        if self.client.has['fetchOrder']:
            try:
                updated_order = await self.client.fetch_order(order_id, symbol)
                self.get_personal_data().upsert_order(order_id, updated_order)
            except OrderNotFound:
                # some exchanges are throwing this error when an order is cancelled (ex: coinbase pro)
                self.get_personal_data().update_order_attribute(order_id, ecoc.STATUS.value, OrderStatus.CANCELED.value)
        else:
            raise Exception("This exchange doesn't support fetchOrder")

    async def get_all_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchOrders']:
            self.get_personal_data().upsert_orders(
                await self.client.fetch_orders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchOrders")

    async def get_open_orders(self, symbol=None, since=None, limit=None, force_rest=False):
        if self.client.has['fetchOpenOrders']:
            self.get_personal_data().upsert_orders(
                await self.client.fetch_open_orders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchOpenOrders")

    async def get_closed_orders(self, symbol=None, since=None, limit=None):
        if self.client.has['fetchClosedOrders']:
            self.get_personal_data().upsert_orders(
                await self.client.fetch_closed_orders(symbol=symbol, since=since, limit=limit))
        else:
            raise Exception("This exchange doesn't support fetchClosedOrders")

    async def get_my_recent_trades(self, symbol=None, since=None, limit=None):
        return await self.client.fetch_my_trades(symbol=symbol, since=since, limit=limit)

    async def cancel_order(self, order_id, symbol=None):
        try:
            await self.client.cancel_order(order_id, symbol=symbol)
            return True
        except OrderNotFound:
            self.logger.error(f"Order {order_id} was not found")
        except Exception as e:
            self.logger.error(f"Order {order_id} failed to cancel | {e}")
        return False

    async def create_order(self, order_type, symbol, quantity, price=None, stop_price=None):
        try:
            created_order = await self._create_specific_order(order_type, symbol, quantity, price)
            # some exchanges are not returning the full order details on creation: fetch it if necessary
            if created_order and not self._ensure_order_details_completeness(created_order):
                if ecoc.ID.value in created_order:
                    order_symbol = created_order[ecoc.SYMBOL.value] if ecoc.SYMBOL.value in created_order else None
                    created_order = await self.exchange_manager.get_exchange().get_order(created_order[ecoc.ID.value],
                                                                                         order_symbol)

            # on some exchange, market order are not not including price, add it manually to ensure uniformity
            if created_order[ecoc.PRICE.value] is None and price is not None:
                created_order[ecoc.PRICE.value] = price

            return created_order

        except InsufficientFunds as e:
            self._log_error(e, order_type, symbol, quantity, price, stop_price)
            raise e
        except Exception as e:
            self._log_error(e, order_type, symbol, quantity, price, stop_price)
            self.logger.exception(e)
        return None

    # todo { 'type': 'trailing-stop' }
    async def _create_specific_order(self, order_type, symbol, quantity, price=None):
        created_order = None
        if order_type == TraderOrderType.BUY_MARKET:
            created_order = await self.client.create_market_buy_order(symbol, quantity)
        elif order_type == TraderOrderType.BUY_LIMIT:
            created_order = await self.client.create_limit_buy_order(symbol, quantity, price)
        elif order_type == TraderOrderType.SELL_MARKET:
            created_order = await self.client.create_market_sell_order(symbol, quantity)
        elif order_type == TraderOrderType.SELL_LIMIT:
            created_order = await self.client.create_limit_sell_order(symbol, quantity, price)
        elif order_type == TraderOrderType.STOP_LOSS:
            created_order = None
        elif order_type == TraderOrderType.STOP_LOSS_LIMIT:
            created_order = None
        elif order_type == TraderOrderType.TAKE_PROFIT:
            created_order = None
        elif order_type == TraderOrderType.TAKE_PROFIT_LIMIT:
            created_order = None
        return created_order

    @staticmethod
    def _ensure_order_details_completeness(order, order_required_fields=None):
        if order_required_fields is None:
            order_required_fields = [ecoc.ID.value, ecoc.TIMESTAMP.value, ecoc.SYMBOL.value, ecoc.TYPE.value,
                                     ecoc.SIDE.value, ecoc.PRICE.value, ecoc.AMOUNT.value, ecoc.REMAINING.value]
        return all(key in order for key in order_required_fields)

    def _log_error(self, error, order_type, symbol, quantity, price, stop_price):
        order_desc = f"order_type: {order_type}, symbol: {symbol}, quantity: {quantity}, price: {price}," \
            f" stop_price: {stop_price}"
        self.logger.error(f"Failed to create order : {error} ({order_desc})")

    def get_trade_fee(self, symbol, order_type, quantity, price,
                      taker_or_maker=ExchangeConstantsMarketPropertyColumns.TAKER.value):
        return self.client.calculate_fee(symbol=symbol,
                                         type=order_type,
                                         side=self._get_side(order_type),
                                         amount=quantity,
                                         price=price,
                                         takerOrMaker=taker_or_maker)

    def get_fees(self, symbol):
        try:
            market_status = self.client.find_market(symbol)
            return {
                ExchangeConstantsMarketPropertyColumns.TAKER.value:
                    get_value_or_default(market_status, ExchangeConstantsMarketPropertyColumns.TAKER.value,
                                         CONFIG_DEFAULT_FEES),
                ExchangeConstantsMarketPropertyColumns.MAKER.value:
                    get_value_or_default(market_status, ExchangeConstantsMarketPropertyColumns.MAKER.value,
                                         CONFIG_DEFAULT_FEES),
                ExchangeConstantsMarketPropertyColumns.FEE.value:
                    get_value_or_default(market_status, ExchangeConstantsMarketPropertyColumns.FEE.value,
                                         CONFIG_DEFAULT_FEES)
            }
        except Exception as e:
            self.logger.error(f"Fees data for {symbol} was not found ({e})")
            return {
                ExchangeConstantsMarketPropertyColumns.TAKER.value: CONFIG_DEFAULT_FEES,
                ExchangeConstantsMarketPropertyColumns.MAKER.value: CONFIG_DEFAULT_FEES,
                ExchangeConstantsMarketPropertyColumns.FEE.value: CONFIG_DEFAULT_FEES
            }

    def get_uniform_timestamp(self, timestamp):
        return timestamp / 1000

    async def stop(self):
        self.logger.info(f"Closing connection.")
        await self.client.close()
        self.logger.info(f"Connection closed.")

    @staticmethod
    def _get_side(order_type):
        return "buy" if order_type == TraderOrderType.BUY_LIMIT or order_type == TraderOrderType.BUY_MARKET else "sell"
