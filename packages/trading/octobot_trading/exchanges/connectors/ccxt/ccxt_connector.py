# pylint: disable=E0611
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
import aiohttp
import ccxt.async_support as ccxt
import ccxt.static_dependencies.ecdsa.der
from ccxt.base.types import (
    # usual "import ccxt.base.types" is not working here from ... import ... is required
    Market as CCXTMarket,
    BalanceAccount as CCXTBalanceAccount,
)
import typing
import inspect
import binascii
import copy

import octobot_commons.enums
import octobot_commons.tree as commons_tree
import octobot_commons.symbols as commons_symbols
import octobot_commons.html_util as html_util

import octobot_trading
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.abstract_exchange as abstract_exchange
import octobot_trading.exchanges.config.exchange_credentials_data as exchange_credentials_data
import octobot_trading.exchanges.connectors.ccxt.ccxt_adapter as ccxt_adapter
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.util as connectors_util
import octobot_trading.personal_data as personal_data
from octobot_trading.enums import ExchangeConstantsOrderColumns as ecoc


class CCXTConnector(abstract_exchange.AbstractExchange):
    """
    CCXT library connector. Everything ccxt related should be in this connector.
    When possible, each call is supposed to create only one request to the exchange.
    Uses self.adapter to parse (and fix if necessary) ccxt raw data.

    Always returns adapted data. Always throws octobot_trading errors
    Never returns row ccxt data or throw ccxt errors
    """

    def __init__(
        self, config, exchange_manager, adapter_class=None, additional_config=None, rest_name=None, force_auth=False
    ):
        super().__init__(config, exchange_manager, None)
        self.client: ccxt.Exchange = None # type: ignore
        self.exchange_type: typing.Type[ccxt.Exchange] = None # type: ignore
        self.adapter: ccxt_adapter.CCXTAdapter = self.get_adapter_class(adapter_class)(self)
        self.all_currencies_price_ticker: dict[str, dict] = {}
        self.is_authenticated: bool = False
        self.rest_name: str = rest_name or self.exchange_manager.exchange_class_string
        self.force_authentication: bool = force_auth
        
        self._force_next_market_reload: bool = False

        # used to save exchange local elements in subclasses
        self.saved_data: dict[str, typing.Any] = {}

        self.additional_config: dict[str, typing.Any] = additional_config
        self.headers: dict[str, str] = {}
        self.options: dict[str, typing.Any] = {}
        # add default options
        self.add_options(
            ccxt_client_util.get_ccxt_client_login_options(self.exchange_manager)
        )
        # add specific options
        if self.additional_config:
            specific_options = self.additional_config.pop(ccxt_constants.CCXT_OPTIONS, None)
            if specific_options:
                self.add_options(specific_options)

        self._create_exchange_type()
        self._create_client()

    async def initialize_impl(self):
        try:
            if self.exchange_manager.exchange.is_supporting_sandbox():
                ccxt_client_util.set_sandbox_mode(
                    self, self.exchange_manager.is_sandboxed
                )
            await self._ensure_exchange_init()

            # initialize symbols and timeframes
            self.symbols = self.exchange_manager.exchange.get_all_available_symbols(active_only=True)
            self.time_frames = self.get_client_time_frames()

        except (ccxt.ExchangeNotAvailable, ccxt.RequestTimeout) as e:
            raise octobot_trading.errors.UnreachableExchange(e) from e

    async def _ensure_exchange_init(self):
        if self.force_authentication or (
            self._should_authenticate() and not self.exchange_manager.exchange_only
        ):
            await self._ensure_auth()
        else:
            await self._unauth_ensure_exchange_init()

    async def _unauth_ensure_exchange_init(self):
        with self.error_describer():
            # already called in _ensure_auth
            await self.load_symbol_markets(
                reload=not self.exchange_manager.use_cached_markets,
                market_filter=self.exchange_manager.market_filter,
            )

    def get_adapter_class(self, adapter_class):
        return adapter_class or ccxt_adapter.CCXTAdapter

    @classmethod
    def load_user_inputs_from_class(cls, tentacles_setup_config, tentacle_config):
        # no user input in connector
        pass

    def _ensure_successful_markets_fetch(self, client):
        if not client.markets:
            return False
        symbols = list[str](client.markets)
        if self.exchange_manager.is_future:
            found_future_markets = False
            for symbol in symbols:
                if commons_symbols.parse_symbol(symbol).is_future():
                    found_future_markets = True
                    break
            if not found_future_markets:
                raise octobot_trading.errors.FailedMarketStatusRequest(
                    f"No future markets found for {self.exchange_manager.exchange_name} - {len(symbols)} fetched markets: {symbols}"
                )
        if self.exchange_manager.is_option:
            found_option_markets = False
            for symbol in symbols:
                if commons_symbols.parse_symbol(symbol).is_option():
                    found_option_markets = True
                    break
            if not found_option_markets:
                raise octobot_trading.errors.FailedMarketStatusRequest(
                    f"No option markets found for {self.exchange_manager.exchange_name} - {len(symbols)} fetched markets: {symbols}"
                )
        if not self.exchange_manager.is_future and not self.exchange_manager.is_option:
            found_spot_markets = False
            for symbol in symbols:
                if commons_symbols.parse_symbol(symbol).is_spot():
                    found_spot_markets = True
                    break
            if not found_spot_markets:
                logged_symbols = (symbols[:3] + ["..."] + symbols[-3:]) if len(symbols) > 10 else symbols
                raise octobot_trading.errors.FailedMarketStatusRequest(
                    f"No spot markets found for {self.exchange_manager.exchange_name}: {len(symbols)} fetched markets: {logged_symbols}"
                )

    async def _filtered_if_necessary_load_markets(
        self,
        client,
        reload: bool,
        market_filter: typing.Optional[typing.Callable[[dict], bool]]
    ):
        try:
            if self.exchange_manager.exchange.ADJUST_FOR_TIME_DIFFERENCE:
                # load time difference before loading markets in case a signature is needed to load markets
                await client.load_time_difference()
            if self.exchange_manager.exchange.FETCH_MIN_EXCHANGE_MARKETS and market_filter:
                with ccxt_client_util.filtered_fetched_markets(client, market_filter):
                    await client.load_markets(reload=reload)
            else:
                await client.load_markets(reload=reload)
                self._ensure_successful_markets_fetch(client)
            message = f"Loaded {len(client.markets) if client.markets else 0} [{self.exchange_manager.exchange_name}] markets"
            if reload:
                self.logger.debug(message)
            else:
                self.logger.info(message)
        except octobot_trading.errors.FailedMarketStatusRequest as err:
            # failed to fetch markets, force reload for next time
            self._force_next_market_reload = True
            raise err
        except Exception as err:
            # ensure this is not a proxy error, raise dedicated error if it is
            if proxy_error := ccxt_client_util.get_proxy_error_if_any(self, err):
                raise ccxt_client_util.get_proxy_error_class(proxy_error)(proxy_error) from err
            raise

    async def _load_markets(
        self, 
        client, 
        reload: bool, 
        market_filter: typing.Optional[typing.Callable[[dict], bool]] = None
    ):
        """
        Override if necessary
        """
        await self._filtered_if_necessary_load_markets(client, reload, market_filter)

    @ccxt_client_util.converted_ccxt_common_errors
    @connectors_util.retried_failed_network_request()
    async def load_symbol_markets(
        self,
        reload=False,
        market_filter: typing.Optional[typing.Callable[[dict], bool]] = None
    ):
        if self._force_next_market_reload:
            self.logger.info(f"Forced market reload for {self.exchange_manager.exchange_name}")
            reload = True
            self._force_next_market_reload = False
        authenticated_cache = self.exchange_manager.exchange.requires_authentication_for_this_configuration_only()
        force_load_markets = reload
        if not force_load_markets:
            try:
                ccxt_client_util.load_markets_from_cache(self.client, authenticated_cache, market_filter=market_filter)
            except KeyError:
                force_load_markets = True
        if force_load_markets:
            self.logger.info(
                f"Loading {self.exchange_manager.exchange_name} "
                f"{exchanges.get_exchange_type(self.exchange_manager).value}"
                f"{' sandbox' if self.exchange_manager.is_sandboxed else ''} exchange markets ({reload=} {authenticated_cache=})"
            )
            try:
                await self._load_markets(self.client, reload, market_filter=market_filter)
                ccxt_client_util.set_markets_cache(self.client, authenticated_cache)
            except (
                ccxt.AuthenticationError, ccxt.ArgumentsRequired, ccxt.static_dependencies.ecdsa.der.UnexpectedDER,
                binascii.Error, AssertionError, IndexError
            ) as err:
                if self.force_authentication:
                    raise ccxt.AuthenticationError(
                        f"Invalid key format ({html_util.get_html_summary_if_relevant(err)})"
                    ) from err
                # should not happen: if it does, propagate it
                if self.exchange_manager.exchange.CAN_MAKE_AUTHENTICATED_REQUESTS_WHEN_LOADING_MARKETS:
                    # can happen, just warn
                    self.logger.warning(f"{err.__class__.__name__} when loading markets: {err}")
                else:
                    # unexpected: notify
                    self.logger.error(f"Unexpected error when loading markets: {err} ({err.__class__.__name__})")
                raise
            except ccxt.NetworkError as err:
                raise octobot_trading.errors.NetworkError(
                    f"Failed to load_symbol_markets: {err.__class__.__name__} "
                    f"on {html_util.get_html_summary_if_relevant(err)}"
                ) from err
            except ccxt.ExchangeError as err:
                if self.exchange_manager.exchange.is_ip_whitelist_error(err):
                    raise octobot_trading.errors.InvalidAPIKeyIPWhitelistError(
                        f"Invalid IP whitelist error: {html_util.get_html_summary_if_relevant(err)}"
                    ) from err
                # includes AuthenticationError but also auth error not identified as such by ccxt
                if not self.force_authentication and self.is_authenticated:
                    self.logger.debug(
                        f"Credentials check enabled when fetching exchange market status, trying with "
                        f"unauthenticated client: {err}."
                    )
                    # auth invalid but not required: fetch markets from another client
                    unauth_client = None
                    try:
                        unauth_client = self._client_factory(True)[0]
                        await self._load_markets(unauth_client, reload, market_filter=market_filter)
                        ccxt_client_util.set_markets_cache(unauth_client, False)
                        # apply markets to target client
                        ccxt_client_util.load_markets_from_cache(self.client, False, market_filter=market_filter)
                        self.logger.debug(
                            f"Fetched exchange market status from unauthenticated client."
                        )
                    finally:
                        if unauth_client:
                            await unauth_client.close()
                else:
                    raise
        # markets are now loaded, trigger event
        commons_tree.EventProvider.instance().trigger_event(
            self.exchange_manager.bot_id, commons_tree.get_exchange_path(
                self.exchange_manager.exchange_name,
                octobot_commons.enums.InitializationEventExchangeTopics.MARKETS.value
            )
        )

    def get_client_symbols(self, active_only=True) -> set[str]:
        return ccxt_client_util.get_symbols(self.client, active_only)

    def get_client_time_frames(self):
        return ccxt_client_util.get_time_frames(self.client)

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        return isinstance(exchange_candidate_name, str)

    def _create_exchange_type(self):
        if self.is_supporting_exchange(self.rest_name):
            self.exchange_type = ccxt_client_util.ccxt_exchange_class_factory(self.rest_name)
        else:
            self.exchange_type = self.rest_name

    def add_headers(self, headers_dict):
        """
        Add new headers to ccxt client
        :param headers_dict: the additional header keys and values as dict
        """
        self.headers.update(headers_dict)
        if self.client is not None:
            ccxt_client_util.add_headers(self.client, headers_dict)

    def add_options(self, options_dict):
        """
        Add new options to ccxt client
        :param options_dict: the additional option keys and values as dict
        """
        self.options.update(options_dict)
        if self.client is not None:
            ccxt_client_util.add_options(self.client, options_dict)

    @classmethod
    def get_extended_additional_connector_config(cls, additional_config: dict):
        extended_ccxt_options = {}
        if extended_ccxt_options:
            if additional_config and ccxt_constants.CCXT_OPTIONS in additional_config:
                additional_config[ccxt_constants.CCXT_OPTIONS].update(extended_ccxt_options)
            else:
                additional_config[ccxt_constants.CCXT_OPTIONS] = extended_ccxt_options
        return additional_config

    @ccxt_client_util.converted_ccxt_common_errors
    async def _ensure_auth(self):
        try:
            # load markets before calling _ensure_auth() to avoid fetching markets status while they are cached
            await self._unauth_ensure_exchange_init()
            await self.exchange_manager.exchange.get_balance()
        except (
            octobot_trading.errors.AuthenticationError, 
            octobot_trading.errors.ExchangeProxyError, 
            ccxt.AuthenticationError
        ) as e:
            await self.client.close()
            if self.force_authentication:
                raise e
            self.client = self.unauthenticated_exchange_fallback(e)
            self.is_authenticated = False
            await self.load_symbol_markets(
                reload=not self.exchange_manager.use_cached_markets,
                market_filter=self.exchange_manager.market_filter,
            )
        except Exception as err:
            if self.force_authentication:
                raise
            # Is probably handled in exchange tentacles, important thing here is that authentication worked
            self.logger.info(f"Error when checking exchange connection: {err}. This should not be an issue.")

    def _create_client(self, force_unauth=False):
        self.client, self.is_authenticated = self._client_factory(force_unauth)

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchange_credentials_data.ExchangeCredentialsData], exchange_credentials_data.ExchangeCredentialsData]=None
    ) -> tuple:
        return ccxt_client_util.create_client(
            self.exchange_type, self.exchange_manager, self.logger,
            self.options, self.headers, self.additional_config,
            False if force_unauth else self._should_authenticate(),
            self.unauthenticated_exchange_fallback,
            keys_adapter=keys_adapter
        )

    def _should_authenticate(self):
        return self.force_authentication or not (
            self.exchange_manager.is_simulated or
            self.exchange_manager.is_backtesting or
            not self.exchange_manager.is_trading
        )

    def unauthenticated_exchange_fallback(self, err):
        if not self.exchange_manager.exchange_only:
            # don't log error when auth is probably not necessary
            self.handle_token_error(err)
        return ccxt_client_util.get_unauthenticated_exchange(
            self.exchange_type,
            self.options, self.headers, self.additional_config,
            self.exchange_manager.exchange_name,
            self.exchange_manager.proxy_config
        )

    def get_market_status(self, symbol, price_example=None, with_fixer=True) -> typing.Union[
        "exchanges.ExchangeMarketStatusFixer", CCXTMarket, dict
    ]:
        try:
            if with_fixer:
                return exchanges.ExchangeMarketStatusFixer(self.client.market(symbol), price_example).market_status
            return self.client.market(symbol)
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except Exception as e:
            self.logger.error(f"Fail to get market status of {symbol}: {html_util.get_html_summary_if_relevant(e)}")
            return {}

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_balance(self, **kwargs: dict):
        """
        fetch balance (free + used) by currency
        :return: balance dict
        """
        if not kwargs:
            kwargs = {}
        with self.error_describer():
            return self.adapter.adapt_balance(
                await self.client.fetch_balance(params=kwargs)
            )
    
    @ccxt_client_util.converted_ccxt_common_errors
    async def get_user_balance(self, user_id: str, **kwargs: dict):
        if not self.client.has['fetchUserBalance']:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchUserBalance")
        try:
            return self.adapter.adapt_balance(
                await self.client.fetch_user_balance(user_id=user_id, params=kwargs)
            )
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_symbol_prices(self,
                                symbol: str,
                                time_frame: octobot_commons.enums.TimeFrames,
                                limit: int = None,
                                since: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        try:
            with self.error_describer():
                return self.adapter.adapt_ohlcv(
                    await self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit, since=since, params=kwargs)
                )
        except ccxt.BadSymbol as err:
            raise octobot_trading.errors.UnSupportedSymbolError(str(err)) from err
        except ccxt.NotSupported as err:
            raise octobot_trading.errors.NotSupported(str(err)) from err
        except ccxt.BaseError as err:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_symbol_prices of {symbol} on {time_frame.value}: {err.__class__.__name__} "
                f"{html_util.get_html_summary_if_relevant(err)}"
            ) from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_kline_price(self,
                              symbol: str,
                              time_frame: octobot_commons.enums.TimeFrames,
                              **kwargs: dict) -> typing.Optional[list[list]]:
        try:
            with self.error_describer():
                limit = kwargs.pop("limit", 1)
                since = kwargs.pop("since", None)
                return self.adapter.adapt_kline(
                    await self.client.fetch_ohlcv(symbol, time_frame.value, limit=limit, since=since, params=kwargs)
                )
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_kline_price {html_util.get_html_summary_if_relevant(e)}"
            )

    # return up to ten bidasks on each side of the order book stack
    @ccxt_client_util.converted_ccxt_common_errors
    async def get_order_book(self, symbol: str, limit: int = 5, **kwargs: dict) -> typing.Optional[dict]:
        try:
            with self.error_describer():
                return self.adapter.adapt_order_book(
                    await self.client.fetch_order_book(symbol, limit=limit, params=kwargs)
                )
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_order_book {html_util.get_html_summary_if_relevant(e)}"
            )

    # return bidasks on each side of the order book stack for each given symbol
    @ccxt_client_util.converted_ccxt_common_errors
    async def get_order_books(
        self, symbols: typing.Optional[list[str]], limit: int = 5, **kwargs: dict
    ) -> typing.Optional[dict[str, dict]]:
        """
        WARNING: not always supported by exchanges.
        Raises octobot_trading.errors.NotSupported when not supported
        :return: a dict of order book by symbol
        """
        try:
            with self.error_describer():
                book_by_symbol = await self.client.fetch_order_books(symbols=symbols, limit=limit, params=kwargs)
                return {
                    symbol: self.adapter.adapt_order_book(book)
                    for symbol, book in book_by_symbol.items()
                }
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_order_books {html_util.get_html_summary_if_relevant(e)}"
            )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_recent_trades(self, symbol: str, limit: int = 50, **kwargs: dict) -> typing.Optional[list[dict]]:
        try:
            with self.error_describer():
                return self.adapter.adapt_public_recent_trades(
                    await self.client.fetch_trades(symbol, limit=limit, params=kwargs)
                )
        except (ccxt.NotSupported, ccxt.ArgumentsRequired) as err:
            raise octobot_trading.errors.NotSupported(err)
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_recent_trades {html_util.get_html_summary_if_relevant(e)}"
            )

    # A price ticker contains statistics for a particular market/symbol for some period of time in recent past (24h)
    @ccxt_client_util.converted_ccxt_common_errors
    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        try:
            with self.error_describer():
                return self.adapter.adapt_ticker(
                    await self.client.fetch_ticker(symbol, params=kwargs)
                )
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_price_ticker {html_util.get_html_summary_if_relevant(e)}"
            )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_all_currencies_price_ticker(
        self, can_try_to_fix_missing_tickers: bool = True, **kwargs: dict
    ) -> typing.Optional[dict[str, dict]]:
        try:
            symbols = kwargs.pop("symbols", None)
            with self.error_describer():
                tickers = {
                    symbol: self.adapter.adapt_ticker(ticker)
                    for symbol, ticker in (await self.client.fetch_tickers(symbols, params=kwargs)).items()
                }
                # self.all_currencies_price_ticker should always contain as many tickers as possible: don't override it
                # with less symbols when fetching only a few tickers
                if self.all_currencies_price_ticker and self.exchange_manager.exchange.CAN_MISS_TICKERS_IN_ALL_TICKERS:
                    # keep track of missed ticker symbols
                    if added_symbols := list(
                        symbol for symbol in tickers if symbol not in self.all_currencies_price_ticker
                    ):
                        added_symbols_str = "" if len(added_symbols) > 10 else f": ({', '.join(added_symbols)})"
                        self.logger.info(
                            f"Adding {len(added_symbols)} symbols to [{self.exchange_manager.exchange_name}] all tickers{added_symbols_str}"
                        )
                self.all_currencies_price_ticker.update(tickers)
                if symbols and self.exchange_manager.exchange.CAN_MISS_TICKERS_IN_ALL_TICKERS:
                    await self._try_to_fix_all_tickers_if_needed(symbols, can_try_to_fix_missing_tickers)
            return {
                symbol: ticker for symbol, ticker in self.all_currencies_price_ticker.items()
                if symbol in symbols
            } if symbols else self.all_currencies_price_ticker
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except ccxt.BaseError as e:
            raise octobot_trading.errors.FailedRequest(
                f"Failed to get_all_currencies_price_ticker {html_util.get_html_summary_if_relevant(e)}"
            )

    async def _try_to_fix_all_tickers_if_needed(self, symbols: list[str], can_try_to_fix_missing_tickers: bool):
        missing_symbols = [
            symbol for symbol in symbols
            if symbol not in self.all_currencies_price_ticker
        ]
        if missing_symbols:
            if can_try_to_fix_missing_tickers:
                self.logger.warning(
                    f"{len(missing_symbols)} required symbols are missing from "
                    f"[{self.exchange_manager.exchange_name}] all tickers: {missing_symbols}. Retrying to fetch them."
                )
                await self.get_all_currencies_price_ticker(symbols=missing_symbols, can_try_to_fix_missing_tickers=False)
            else:
                self.logger.error(
                    f"{len(missing_symbols)} symbols are still missing after a second "
                    f"[{self.exchange_manager.exchange_name}] tickers fetch. Symbols: {missing_symbols}"
                )

    # ORDERS
    @ccxt_client_util.converted_ccxt_common_errors
    async def get_order(self, exchange_order_id: str, symbol: str = None, **kwargs: dict) -> dict:
        if self.client.has['fetchOrder']:
            try:
                with self.error_describer():
                    order = await self.client.fetch_order(exchange_order_id, symbol, params=kwargs)
                    if order.get(ccxt_constants.CCXT_INFO):
                        return self.adapter.adapt_order(order, symbol=symbol)
                    return None
            except (ccxt.OrderNotFound, ccxt.InvalidOrder):
                # some exchanges are throwing this error when an order
                #   - is cancelled (ex: coinbase pro): ccxt.OrderNotFound
                #   - or not yet created (ex: kucoin): ccxt.InvalidOrder
                pass
            except ccxt.NotSupported as e:
                # some exchanges are throwing this error when an order is cancelled (ex: coinbase pro)
                raise octobot_trading.errors.NotSupported(
                    html_util.get_html_summary_if_relevant(e)
                ) from e
            except ccxt.ExchangeError as e:
                if self.exchange_manager.exchange.is_order_not_found_error(e):
                    # when an OrderNotFound error should have been raised but is not for some reason
                    pass
                else:
                    # something went wrong and ccxt did not expect it
                    raise octobot_trading.errors.FailedRequest(html_util.get_html_summary_if_relevant(e)) from e
        else:
            # When fetch_order is not supported, uses get_open_orders or get_closed_orders and extract order id
            for method in (self.get_open_orders, self.get_closed_orders):
                orders = await method(symbol=symbol)
                for order in orders:
                    if order.get(ecoc.EXCHANGE_ID.value, None) == exchange_order_id:
                        return order

        return None  # OrderNotFound

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_all_orders(self, symbol: str = None, since: int = None,
                             limit: int = None, **kwargs: dict) -> list[dict]:
        if self.client.has['fetchOrders']:
            with self.error_describer():
                return self.adapter.adapt_orders(
                    await self.client.fetch_orders(symbol=symbol, since=since, limit=limit, params=kwargs),
                    symbol=symbol
                )
        else:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchOrders")

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_open_orders(self, symbol: str = None, since: int = None,
                              limit: int = None, **kwargs: dict) -> list[dict]:
        if self.client.has['fetchOpenOrders']:
            with self.error_describer():
                return self.adapter.adapt_orders(
                    await self.client.fetch_open_orders(symbol=symbol, since=since, limit=limit, params=kwargs),
                    symbol=symbol
                )
        else:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchOpenOrders")

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_user_open_orders(self, user_id: str, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        if self.client.has['fetchUserOpenOrders']:
            with self.error_describer():
                return self.adapter.adapt_orders(
                    await self.client.fetch_user_open_orders(user_id=user_id, symbol=symbol, since=since, limit=limit, params=kwargs),
                    symbol=symbol
                )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_closed_orders(self, symbol: str = None, since: int = None,
                                limit: int = None, **kwargs: dict) -> list[dict]:
        with self.error_describer():
            return self.adapter.adapt_orders(
                await self.client.fetch_closed_orders(symbol=symbol, since=since, limit=limit, params=kwargs),
                symbol=symbol
            )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_cancelled_orders(self, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list[dict]:
        with self.error_describer():
            method = self.client.fetch_canceled_orders if self.client.has['fetchCanceledOrders'] \
                else (self.client.fetch_closed_orders if self.client.has['fetchClosedOrders'] else None)
            if method is None:
                raise octobot_trading.errors.NotSupported(
                    f"Neither of fetchCanceledOrders and fetchClosedOrders are supported: get_cancelled_orders "
                    f"is not supported"
                )
            return self.adapter.adapt_orders(
                await method(symbol=symbol, since=since, limit=limit, params=kwargs),
                symbol=symbol,
                cancelled_only=True
            )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_my_recent_trades(self, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list[dict]:
        if self.client.has['fetchMyTrades'] or self.client.has['fetchTrades']:
            with self.error_describer():
                method = self.client.fetch_my_trades if self.client.has['fetchMyTrades'] else self.client.fetch_trades
                trades = self.adapter.adapt_trades(await method(symbol=symbol, since=since, limit=limit, params=kwargs))
                if trades or not self.exchange_manager.exchange.ALLOW_TRADES_FROM_CLOSED_ORDERS:
                    return trades
                # on some exchanges, recent trades are only fetching very recent trade. also try closed orders
                return await self.exchange_manager.exchange.get_closed_orders(
                    symbol=symbol,
                    since=since,
                    limit=limit,
                    **kwargs
                )
        else:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchMyTrades nor fetchTrades")

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_user_recent_trades(self, user_id: str, symbol: str = None, since: int = None,
                                   limit: int = None, **kwargs: dict) -> list:
        if self.client.has['fetchUserRecentTrades']:
            with self.error_describer():
                return self.adapter.adapt_trades(
                    await self.client.fetch_user_recent_trades(user_id=user_id, symbol=symbol, since=since, limit=limit, params=kwargs)
                )
        else:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchUserRecentTrades")

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_buy_order(self, symbol, quantity, price=None, params=None) -> dict:
        return self.adapter.adapt_order(
            # use create_order instead of create_market_buy_order to pass the price argument
            await self.client.create_order(
                symbol, enums.TradeOrderType.MARKET.value, enums.TradeOrderSide.BUY.value, quantity,
                price=price, params=params
            ),
            symbol=symbol, quantity=quantity
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_buy_order_with_cost(self, symbol, cost: float, quantity: float, params=None) -> dict:
        return self.adapter.adapt_order(
            # use create_order instead of create_market_buy_order to pass the price argument
            await self.client.create_market_buy_order_with_cost(symbol, cost, params=params),
            symbol=symbol, quantity=quantity
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_limit_buy_order(self, symbol, quantity, price=None, params=None) -> dict:
        return self.adapter.adapt_order(
            await self.client.create_limit_buy_order(symbol, quantity, price, params=params),
            symbol=symbol, quantity=quantity
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_sell_order(self, symbol, quantity, price=None, params=None) -> dict:
        return self.adapter.adapt_order(
            # use create_order instead of create_market_sell_order to pass the price argument
            await self.client.create_order(
                symbol, enums.TradeOrderType.MARKET.value, enums.TradeOrderSide.SELL.value, quantity,
                price=price, params=params
            ),
            symbol=symbol, quantity=quantity
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_limit_sell_order(self, symbol, quantity, price=None, params=None) -> dict:
        return self.adapter.adapt_order(
            await self.client.create_limit_sell_order(symbol, quantity, price, params=params),
            symbol=symbol, quantity=quantity
        )

    def _add_stop_loss_price_param(self, params: dict, price: float):
        params = params or {}
        if self.exchange_manager.exchange.STOP_LOSS_CREATE_PRICE_PARAM not in params:
            params[self.exchange_manager.exchange.STOP_LOSS_CREATE_PRICE_PARAM] = price
        return params

    def _add_edit_stop_loss_price_param(self, params: dict, price: float):
        params = params or {}
        if self.exchange_manager.exchange.STOP_LOSS_EDIT_PRICE_PARAM not in params:
            params[self.exchange_manager.exchange.STOP_LOSS_EDIT_PRICE_PARAM] = price
        return params

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_stop_loss_order(self, symbol, quantity, price, side, current_price, params=None) -> dict:
        try:
            params = self._add_stop_loss_price_param(params, price)
            return self.adapter.adapt_order(
                await self.client.create_order(
                    symbol,
                    enums.TradeOrderType.MARKET.value,
                    side,
                    quantity,
                    params=params,
                ),
                symbol=symbol, quantity=quantity
            )
        except ccxt.NotSupported as err:
            raise NotImplementedError(f"create_market_stop_loss_order is not supported {err}")
        except ccxt.OrderImmediatelyFillable:
            # make sure stop always stops
            created_order = await self.exchange_manager.exchange.create_order(
                order_type=(enums.TraderOrderType.BUY_MARKET
                            if side == enums.TradeOrderSide.BUY.value
                            else enums.TraderOrderType.SELL_MARKET),
                symbol=symbol,
                quantity=decimal.Decimal(str(quantity)),
                price=decimal.Decimal(str(price)),
                current_price=decimal.Decimal(str(current_price))
            )
            created_order[enums.ExchangeConstantsOrderColumns.TYPE.value] = (
                enums.TraderOrderType.STOP_LOSS.value
                )
            return created_order

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_limit_stop_loss_order(self, symbol, quantity, price, stop_price, side, params=None) -> dict:
        try:
            params = self._add_stop_loss_price_param(params, stop_price)
            return self.adapter.adapt_order(
                await self.client.create_order(
                    symbol,
                    enums.TradeOrderType.LIMIT.value,
                    side,
                    quantity,
                    price=price,
                    params=params,
                ),
                symbol=symbol, quantity=quantity
            )
        except ccxt.NotSupported as err:
            raise NotImplementedError(f"create_limit_stop_loss_order is not supported {err}")

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_take_profit_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("create_market_take_profit_order is not implemented")

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_limit_take_profit_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("create_limit_take_profit_order is not implemented")

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_market_trailing_stop_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("create_market_trailing_stop_order is not implemented")

    @ccxt_client_util.converted_ccxt_common_errors
    async def create_limit_trailing_stop_order(self, symbol, quantity, price=None, side=None, params=None) -> dict:
        raise NotImplementedError("create_limit_trailing_stop_order is not implemented")

    @ccxt_client_util.converted_ccxt_common_errors
    async def edit_order(self, exchange_order_id: str, order_type: enums.TraderOrderType, symbol: str,
                         quantity: float, price: float, stop_price: float = None, side: str = None,
                         current_price: float = None, params: dict = None) -> dict:
        ccxt_order_type = self.get_ccxt_order_type(order_type)
        local_params = copy.copy(params)
        if order_type == enums.TraderOrderType.STOP_LOSS:
            local_params = self._add_edit_stop_loss_price_param(local_params, stop_price or price)
        elif order_type == enums.TraderOrderType.STOP_LOSS_LIMIT:
            local_params = self._add_edit_stop_loss_price_param(local_params, stop_price)
        if self.exchange_manager.exchange.supports_native_edit_order(order_type):
            price_to_use = price
            if ccxt_order_type == enums.TradeOrderType.MARKET.value:
                # can't set price in market orders
                price_to_use = None
            edited_order = await self.client.edit_order(
                exchange_order_id, symbol, ccxt_order_type, side, quantity, price_to_use, local_params
            )
            if edited_order is not None:
                # sometimes exchanges don't return the edited order details (ex: coinbase)
                # => fill it with what we know and verify_order will fetch the rest
                if not edited_order.get(ecoc.ID.value):
                    edited_order[ecoc.ID.value] = exchange_order_id
                if not edited_order.get(ecoc.SYMBOL.value):
                    edited_order[ecoc.SYMBOL.value] = symbol
        else:
            # ccxt exchange edit order is disabled: force ccxt.exchange default edit order behavior
            edited_order = await self._edit_order_by_cancel_and_create(
                exchange_order_id, symbol, order_type, side, quantity, price, params
            )
        return self.adapter.adapt_order(edited_order, symbol=symbol, quantity=quantity)

    async def _edit_order_by_cancel_and_create(
        self, exchange_order_id: str, symbol: str, order_type: enums.TraderOrderType,
        side: str, quantity: float, price: float, params: dict
    ) -> dict:
        extended_params = self.exchange_manager.exchange.order_request_kwargs_factory(exchange_order_id, order_type, **(params or {}))
        await self.client.cancel_order(exchange_order_id, symbol=symbol, params=extended_params)
        price_to_use = price
        local_params = copy.copy(params)
        ccxt_order_type = self.get_ccxt_order_type(order_type)
        if ccxt_order_type == enums.TradeOrderType.MARKET.value:
            # can't set price in market orders
            price_to_use = None
            local_params = self._add_stop_loss_price_param(local_params, price)
        return await self.client.create_order(symbol, ccxt_order_type, side, quantity, price_to_use, local_params)

    @ccxt_client_util.converted_ccxt_common_errors
    async def cancel_all_orders(self, symbol: str = None, **kwargs: dict) -> None:
        try:
            with self.error_describer():
                await self.client.cancel_all_orders(symbol=symbol, params=kwargs)
        except (ccxt.NotSupported, octobot_trading.errors.NotSupported) as e:
            raise octobot_trading.errors.NotSupported(e) from e
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Unexpected error when cancelling all {symbol} orders | "
                f"{html_util.get_html_summary_if_relevant(e)} ({e.__class__.__name__})"
            )
            raise e

    @ccxt_client_util.converted_ccxt_common_errors
    async def cancel_order(
        self, exchange_order_id: str, symbol: str, order_type: enums.TraderOrderType, **kwargs: dict
    ) -> enums.OrderStatus:
        try:
            with self.error_describer():
                try:
                    await self.client.cancel_order(exchange_order_id, symbol=symbol, params=kwargs)
                except Exception as err:
                    if self.exchange_manager.exchange.is_exchange_order_uncancellable(err):
                        # handle ExchangeOrderCancelError locally not to raise it from other contexts
                        # (such as if used in error_describer)
                        raise octobot_trading.errors.ExchangeOrderCancelError(
                            f"Error when handling order {html_util.get_html_summary_if_relevant(err)}. "
                            f"Exchange is refusing to cancel this order. The order is probably filled "
                            f"or cancelled already."
                        ) from err
                    raise
                # no exception, cancel worked
            try:
                # make sure order is canceled
                cancelled_order = await self.exchange_manager.exchange.get_order(
                    exchange_order_id, symbol=symbol, order_type=order_type
                )
                if cancelled_order is None or personal_data.parse_is_cancelled(cancelled_order):
                    return enums.OrderStatus.CANCELED
                elif (
                    personal_data.parse_is_open(cancelled_order)
                    or personal_data.parse_is_pending_cancel(cancelled_order)
                ):
                    return enums.OrderStatus.PENDING_CANCEL
                # cancel command worked but order is still existing and is not open or canceled. unhandled case
                # log error and consider it canceling. order states will manage the
                self.logger.error(f"Unexpected order status after cancel for order: {cancelled_order}. "
                                  f"Considered as {enums.OrderStatus.PENDING_CANCEL.value}")
                return enums.OrderStatus.PENDING_CANCEL
            except ccxt.OrderNotFound:
                # Order is not found: it has successfully been cancelled (some exchanges don't allow to
                # get a cancelled order).
                return enums.OrderStatus.CANCELED
        except ccxt.OrderNotFound as e:
            self.logger.debug(
                f"Trying to cancel order with id {exchange_order_id} but order was not found. It might have "
                f"already been cancelled or be filled."
            )
            raise octobot_trading.errors.OrderNotFoundOnCancelError(
                html_util.get_html_summary_if_relevant(e)
            ) from e
        except (ccxt.NotSupported, octobot_trading.errors.NotSupported) as e:
            raise octobot_trading.errors.NotSupported(
                html_util.get_html_summary_if_relevant(e)
            ) from e
        except octobot_trading.errors.ExchangeOrderCancelError:
            # propagate error
            raise
        except Exception as e:
            self.logger.exception(
                e,
                True,
                f"Unexpected error when cancelling order with exchange id: "
                f"{exchange_order_id} failed to cancel | {html_util.get_html_summary_if_relevant(e)} "
                f"({e.__class__.__name__})")
            raise e

    async def withdraw(
        self, asset: str, amount: decimal.Decimal, network: str, address: str, tag: str = "", params: dict = None
    ) -> dict:
        if not constants.ALLOW_FUNDS_TRANSFER:
            # always make sure to check this constant to avoid any potential security issue
            raise octobot_trading.errors.DisabledFundsTransferError(
                f"Withdraw funds is not enabled"
            )
        if self.exchange_manager.exchange.WITHDRAW_NETWORK_PARAM_KEY:
            params = params or {}
            params[self.exchange_manager.exchange.WITHDRAW_NETWORK_PARAM_KEY] = network
        return self.adapter.adapt_transaction(
            await self.client.withdraw(asset, float(amount), address, tag=tag, params=params)
        )

    async def get_deposit_address(self, asset: str, params: dict = None) -> dict:
        return self.adapter.adapt_deposit_address(
            await self.client.fetch_deposit_address(asset, params=params)
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_positions(self, symbols=None, **kwargs: dict) -> list[dict]:
        try:
            return [
                self.adapter.adapt_position(position)
                for position in await self.client.fetch_positions(symbols=symbols, params=kwargs)
            ]
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_position(self, symbol: str, **kwargs: dict) -> dict:
        try:
            return self.adapter.adapt_position(
                await self.client.fetch_position(symbol=symbol, params=kwargs)
            )
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_closed_positions(self, symbols=None, **kwargs: dict) -> list:
        if not self.client.has['fetchClosedPositions']:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchClosedPositions")
        try:
            return self.adapter.adapt_position(
                await self.client.fetch_closed_positions(symbols=symbols, params=kwargs)
            )
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_user_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        if not self.client.has['fetchUserPositions']:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchUserPositions")
        try:
            return [
                self.adapter.adapt_position(position)
                for position in await self.client.fetch_user_positions(user_id, symbols=symbols, params=kwargs)
            ]
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_user_closed_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        if not self.client.has['fetchUserClosedPositions']:
            raise octobot_trading.errors.NotSupported("This exchange doesn't support fetchUserClosedPositions")
        try:
            return [
                self.adapter.adapt_position(position)
                for position in await self.client.fetch_user_closed_positions(user_id, symbols=symbols, params=kwargs)
            ]
        except ccxt.NotSupported as err:
            raise NotImplementedError from err

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_mocked_empty_position(self, symbol: str, **kwargs: dict) -> dict:
        return self.adapter.adapt_position(
            self.client.parse_position({}, market=self.client.market(symbol)),
            force_empty=True
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_funding_rate(self, symbol: str, **kwargs: dict) -> dict:
        return self.adapter.adapt_funding_rate(
            await self.client.fetch_funding_rate(symbol=symbol, params=kwargs)
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_funding_rate_history(self, symbol: str, limit: int = 1, **kwargs: dict) -> list[dict]:
        return self.adapter.adapt_funding_rate(
            await self.client.fetch_funding_rate_history(symbol=symbol, limit=limit, params=kwargs)
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_leverage_tiers(self, symbols: list = None, **kwargs: dict) -> dict[str, list[dict]]:
        if self.client.has.get("fetchLeverageTiers"):
            return self.adapter.adapt_leverage_tiers(
                await self.client.fetch_leverage_tiers(symbols=symbols, params=kwargs)
            )
        raise NotImplementedError("get_leverage_tiers is not supported")

    def get_contract_size(self, symbol: str) -> decimal.Decimal:
        return decimal.Decimal(str(ccxt_client_util.get_contract_size(self.client, symbol)))

    @ccxt_client_util.converted_ccxt_common_errors
    async def get_symbol_leverage(self, symbol: str, **kwargs: dict) -> dict:
        return self.adapter.adapt_leverage(
            await self.client.fetch_leverage(symbol=symbol, params=kwargs)
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def set_symbol_leverage(self, symbol: str, leverage: float, **kwargs: dict) -> dict:
        return await self.client.set_leverage(leverage=int(leverage), symbol=symbol, params=kwargs)

    @ccxt_client_util.converted_ccxt_common_errors
    async def set_symbol_margin_type(self, symbol: str, isolated: bool, **kwargs: dict) -> dict:
        return await self.client.set_margin_mode(
            ccxt_enums.ExchangeMarginTypes.ISOLATED.value if isolated else ccxt_enums.ExchangeMarginTypes.CROSS.value,
            symbol=symbol,
            params=kwargs,
        )

    @ccxt_client_util.converted_ccxt_common_errors
    async def set_symbol_position_mode(self, symbol: str, one_way: bool) -> dict:
        return await self.client.set_position_mode(self, hedged=not one_way, symbol=symbol)

    @ccxt_client_util.converted_ccxt_common_errors
    async def set_symbol_partial_take_profit_stop_loss(self, symbol: str, inverse: bool,
                                                       tp_sl_mode: enums.TakeProfitStopLossMode):
        raise NotImplementedError("set_symbol_partial_take_profit_stop_loss is not implemented")

    def get_ccxt_order_type(self, order_type: enums.TraderOrderType):
        if order_type in (enums.TraderOrderType.BUY_LIMIT, enums.TraderOrderType.SELL_LIMIT,
                          enums.TraderOrderType.STOP_LOSS_LIMIT, enums.TraderOrderType.TAKE_PROFIT_LIMIT,
                          enums.TraderOrderType.TRAILING_STOP_LIMIT):
            return enums.TradeOrderType.LIMIT.value
        if order_type in (enums.TraderOrderType.BUY_MARKET, enums.TraderOrderType.SELL_MARKET,
                          enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.TAKE_PROFIT,
                          enums.TraderOrderType.TRAILING_STOP):
            return enums.TradeOrderType.MARKET.value
        raise RuntimeError(f"Unknown order type: {order_type}")

    def get_trade_fee(self, symbol: str, order_type: enums.TraderOrderType, quantity, price, taker_or_maker) -> dict:
        fees = self.calculate_fees(symbol, order_type, quantity, price, taker_or_maker)
        fees[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] = False
        fees[enums.FeePropertyColumns.COST.value] = decimal.Decimal(
            str(fees.get(enums.FeePropertyColumns.COST.value) or 0)
        )
        if self.exchange_manager.is_future:
            # fees on futures are wrong
            rate = fees.get(enums.FeePropertyColumns.RATE.value, 0) or 0
            # avoid using ccxt computed fees as they are often wrong
            # see https://docs.ccxt.com/en/latest/manual.html#trading-fees
            parsed_symbol = commons_symbols.parse_symbol(symbol)
            if self.exchange_manager.exchange.get_pair_future_contract(symbol).is_inverse_contract():
                fees[enums.FeePropertyColumns.COST.value] = decimal.Decimal(str(rate)) * quantity
                fees[enums.FeePropertyColumns.CURRENCY.value] = parsed_symbol.base
            else:
                fees[enums.FeePropertyColumns.COST.value] = decimal.Decimal(str(rate)) * quantity * price
                fees[enums.FeePropertyColumns.CURRENCY.value] = parsed_symbol.quote
        return fees

    def calculate_fees(
        self, symbol: str, order_type: enums.TraderOrderType,
        quantity: decimal.Decimal, price: decimal.Decimal, taker_or_maker: str
    ) -> dict:
        limit_or_market_order_type = (
            enums.TradeOrderType.MARKET
            if taker_or_maker == enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
            else enums.TradeOrderType.LIMIT
        )
        return self.client.calculate_fee(
            symbol=symbol,
            type=limit_or_market_order_type.value,
            side=exchanges.get_order_side(order_type),
            amount=float(quantity),
            price=float(price),
            takerOrMaker=taker_or_maker
        )

    def get_fees(self, symbol) -> dict[str, float]:
        try:
            return ccxt_client_util.get_fees(self.client.market(symbol))
        except ccxt.NotSupported:
            raise octobot_trading.errors.NotSupported
        except Exception as e:
            self.logger.error(f"Fees data for {symbol} was not found ({html_util.get_html_summary_if_relevant(e)})")
            return {
                enums.ExchangeConstantsMarketPropertyColumns.TAKER.value: constants.CONFIG_DEFAULT_FEES,
                enums.ExchangeConstantsMarketPropertyColumns.MAKER.value: constants.CONFIG_DEFAULT_FEES,
                enums.ExchangeConstantsMarketPropertyColumns.FEE.value: constants.CONFIG_DEFAULT_FEES
            }

    @classmethod
    def register_simulator_connector_fee_methods(cls, exchange_name: str, simulator_connector):
        # override if necessary
        pass

    def get_exchange_current_time(self) -> int:
        return self.get_uniform_timestamp(self.client.milliseconds())

    def get_uniform_timestamp(self, timestamp) -> float:
        return self.adapter.get_uniformized_timestamp(timestamp)

    async def stop(self) -> None:
        self.logger.debug(f"Closing connection.")
        await ccxt_client_util.close_client(self.client)
        self.logger.debug(f"Connection closed.")
        self.client = None
        self.exchange_manager = None

    def get_pair_from_exchange(self, pair) -> typing.Optional[str]:
        try:
            return self.client.market(pair)["symbol"]
        except ccxt.BadSymbol:
            try:
                return self.client.markets_by_id[pair]["symbol"]
            except KeyError:
                self.logger.error(f"Failed to get market of {pair} [{self.exchange_manager.exchange_name}]")
        return None

    def get_split_pair_from_exchange(self, pair) -> (str, str):
        try:
            market_data: dict = self.client.market(pair)
            return market_data["base"], market_data["quote"]
        except ccxt.BadSymbol:
            try:
                return self.client.markets_by_id[pair]["base"], self.client.markets_by_id[pair]["quote"]
            except KeyError:
                self.logger.error(f"Failed to get market of {pair} [{self.exchange_manager.exchange_name}]")
                return None, None

    def get_exchange_pair(self, pair) -> str:
        return ccxt_client_util.get_exchange_pair(self.client, pair)

    def get_pair_cryptocurrency(self, pair) -> str:
        return ccxt_client_util.get_pair_cryptocurrency(self.client, pair)

    def get_default_balance(self) -> CCXTBalanceAccount:
        return self.client.account()

    def get_rate_limit(self) -> float:
        return self.exchange_type.rateLimit / 1000

    def has_markets(self) -> bool:
        return bool(self.client.markets)

    def supports_trading_type(self, symbol, trading_type: enums.ContractTradingTypes) -> bool:
        trading_type_to_ccxt_property = {
            enums.ContractTradingTypes.LINEAR: "linear",
            enums.ContractTradingTypes.INVERSE: "inverse",
        }
        return self.client.safe_string(
            self.client.market(symbol),
            trading_type_to_ccxt_property[trading_type],
            "False"
        ) == "True"

    def is_expirable_symbol(self, symbol) -> bool:
        return self.client.market(symbol).get("expiry") is not None

    def get_pair_market_type(self, pair, property_name, def_value=False) -> str:
        return self.client.safe_string(
            self.client.safe_value(self.client.markets, pair, {}), property_name, def_value
        )

    def get_saved_data(self, key):
        return self.saved_data[key]

    def set_saved_data(self, key, value):
        self.saved_data[key] = value

    """
    Parsers todo: remove all parsers
    """

    def parse_balance(self, balance):
        return self.client.parse_balance(balance)

    def parse_trade(self, trade):
        return self.client.parse_trade(trade)

    def parse_order(self, order):
        return self.client.parse_order(order)

    def parse_ticker(self, ticker):
        return self.client.parse_ticker(ticker)

    def parse_ohlcv(self, ohlcv):
        return self.uniformize_candles_if_necessary(self.client.parse_ohlcv(ohlcv))

    def parse_order_book(self, order_book):
        return self.client.parse_order_book(order_book)

    def parse_order_book_ticker(self, order_book_ticker):
        return order_book_ticker

    def parse_timestamp(self, data_dict, timestamp_key, default_value=None, ms=False):
        parsed_timestamp = self.client.parse8601(self.client.safe_string(data_dict, timestamp_key))
        return (parsed_timestamp if ms else parsed_timestamp * 10 ** -3) if parsed_timestamp else default_value

    def parse_currency(self, currency):
        return self.client.safe_currency_code(currency)

    def parse_exhange_order_id(self, order):
        return order.get(ecoc.EXCHANGE_ID.value, None)

    def parse_order_symbol(self, order):
        return order.get(ecoc.SYMBOL.value, None)

    def parse_side(self, side):
        return enums.TradeOrderSide.BUY if side == self.BUY_STR else enums.TradeOrderSide.SELL

    def parse_account(self, account):
        return enums.AccountTypes[account]

    def parse_funding(self, funding_dict, from_ticker=False) -> dict:
        return self.adapter.adapt_funding_rate(funding_dict, from_ticker=from_ticker)

    def parse_mark_price(self, mark_price_dict, from_ticker=False) -> dict:
        return self.adapter.adapt_mark_price(mark_price_dict, from_ticker=from_ticker)

    def get_max_handled_pair_with_time_frame(self) -> int:
        """
        Override when necessary
        :return: the maximum number of simultaneous pairs * time_frame that this exchange can handle.
        """
        # 15 pairs, each on 3 time frames
        return 45

    def raise_or_prefix_proxy_error_if_relevant(self, cause_error: Exception, raised_error: typing.Optional[Exception]) -> None:
        """
        Will raise octobot_trading.errors.ExchangeProxyError when the error is linked to a proxy
        server of configuration issue.
        Will re-raise a "[Proxied request] " prefix given error message if relevant, otherwise will just raise the error
        """
        if proxy_error := ccxt_client_util.get_proxy_error_if_any(self, cause_error):
            raise ccxt_client_util.get_proxy_error_class(proxy_error)(proxy_error) from cause_error
        # when api key is wrong or proxy is unavailable
        ccxt_client_util.reraise_with_proxy_prefix_if_relevant(self, cause_error, raised_error)
        # reraise_with_proxy_prefix_if_relevant did not raise, raise the error as is
        if raised_error is None:
            raise cause_error
        raise raised_error from cause_error

    def log_ddos_error(self, error) -> None:
        self.logger.error(
            f"DDoSProtection triggered [{html_util.get_html_summary_if_relevant(error)} ({error.__class__.__name__})]. "
            f"Last response headers: {self.client.last_response_headers} "
            f"Last json response: {self.client.last_json_response}"
        )

    def get_latest_request_url(self) -> str:
        return self.client.last_request_url

    @contextlib.contextmanager
    def error_describer(self):
        try:
            yield
        except ccxt.DDoSProtection as err:
            # raised upon rate limit issues, last response data might have details on what is happening
            if self.exchange_manager.exchange.should_log_on_ddos_exception(err):
                self.log_ddos_error(err)
            self.raise_or_prefix_proxy_error_if_relevant(err, None)
        except ccxt.InvalidNonce as err:
            # use 2 index to get the caller of the context manager
            caller_function_name = inspect.stack()[2].function
            exchanges.log_time_sync_error(self.logger, self.name, err, caller_function_name)
            raise octobot_trading.errors.FailedRequest(html_util.get_html_summary_if_relevant(err)) from err
        except ccxt.AuthenticationError as err:
            error_class = (
                octobot_trading.errors.InvalidAPIKeyIPWhitelistError
                if self.exchange_manager.exchange.is_ip_whitelist_error(err)
                else octobot_trading.errors.AuthenticationError
            )
            self.raise_or_prefix_proxy_error_if_relevant(
                err,
                error_class(html_util.get_html_summary_if_relevant(err))
            )
        except (
            # Generic connection / exchange error
            ccxt.ExchangeNotAvailable, ccxt.ExchangeError,
            # Proxy errors
            aiohttp.ClientHttpProxyError, aiohttp.ClientProxyConnectionError, ccxt_client_util.ProxyConnectionError
        ) as err:
            error_message = html_util.get_html_summary_if_relevant(err)
            if self.exchange_manager.exchange.is_ip_whitelist_error(err):
                # ensure this is not an IP whitelist error
                raise octobot_trading.errors.InvalidAPIKeyIPWhitelistError(error_message) from err
            if self.exchange_manager.exchange.is_authentication_error(err):
                # ensure this is not an unhandled authentication error
                raise octobot_trading.errors.AuthenticationError(error_message) from err
            # keep ccxt.ExchangeError, convert others into network error
            raised_error = None if isinstance(err, ccxt.ExchangeError) else octobot_trading.errors.NetworkError(
                f"Failed to execute request: {err.__class__.__name__}: {error_message}"
            )
            self.raise_or_prefix_proxy_error_if_relevant(err, raised_error)
        except ccxt.NetworkError as err:
            raise octobot_trading.errors.NetworkError(
                f"Request network error ({err.__class__.__name__}): {html_util.get_html_summary_if_relevant(err)}"
            ) from err
