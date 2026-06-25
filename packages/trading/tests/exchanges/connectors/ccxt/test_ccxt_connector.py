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
import decimal
import ccxt
import re
import aiohttp
import aiohttp.client_reqrep

import mock
from mock import patch

import octobot_trading.exchanges.connectors as exchange_connectors
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as enums
import octobot_trading.errors
import octobot_trading.constants
import octobot_trading.exchange_data.contracts as contracts
import octobot_trading.exchanges.connectors.ccxt.ccxt_client_util as ccxt_client_util
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache
import pytest
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants

import tests.exchanges.connectors.ccxt.mock_exchanges_data as mock_exchanges_data
from tests.exchanges import exchange_manager, future_simulated_exchange_manager, set_future_exchange_fees, \
    register_market_status_mocks
from tests.exchanges.traders import future_trader, future_trader_simulator_with_default_linear, DEFAULT_FUTURE_SYMBOL, \
    DEFAULT_FUTURE_SYMBOL_MARGIN_TYPE, DEFAULT_FUTURE_SYMBOL_LEVERAGE

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def ccxt_connector(exchange_manager):
    yield exchange_connectors.CCXTConnector(exchange_manager.config, exchange_manager)


async def test_initialize_impl_with_none_symbols_and_timeframes(ccxt_connector):

    class MockCCXT:
        def __init__(self):
            self.symbols = None
            self.timeframes = None
            self.markets = {}
            self.set_markets_calls = []
            self.urls = {}

        async def load_markets(self, reload=False, market_filter=None):
            pass

        def set_markets(self, markets):
            self.set_markets_calls.append(markets)

        def set_sandbox_mode(self, is_sandboxed):
            pass

    with patch.object(ccxt_connector, 'client', new=MockCCXT()) as mocked_ccxt, \
            patch.object(ccxt_connector, '_ensure_auth', new=mock.AsyncMock()) as _ensure_auth_mock:
        await ccxt_connector.initialize_impl()
        assert len(ccxt_connector.symbols) == 171   # all enabled symbols
        assert ccxt_connector.time_frames == set()
        assert mocked_ccxt.set_markets_calls in ([[]], [])  # depends on call order
        _ensure_auth_mock.assert_called_once()


async def test_initialize_impl_with_empty_symbols_and_timeframes(ccxt_connector):

    class MockCCXT:
        def __init__(self):
            self.symbols = []
            self.timeframes = []
            self.markets = {}
            self.set_markets_calls = []
            self.urls = {}
            self.options = {}

        async def load_markets(self, reload=False, market_filter=None):
            pass

        def set_markets(self, markets):
            self.set_markets_calls.append(markets)

        def set_sandbox_mode(self, is_sandboxed):
            pass

    with patch.object(ccxt_connector, 'client', new=MockCCXT()) as mocked_ccxt, \
            patch.object(ccxt_connector, '_ensure_auth', new=mock.AsyncMock()) as _ensure_auth_mock:
        await ccxt_connector.initialize_impl()
        assert len(ccxt_connector.symbols) == 171   # all enabled symbols
        assert ccxt_connector.time_frames == set()
        assert mocked_ccxt.set_markets_calls in ([[]], [])  # depends on call order
        _ensure_auth_mock.assert_called_once()


async def test_initialize_impl(ccxt_connector):

    class MockCCXT:
        def __init__(self):
            self.symbols = [
                "BTC/USDT",
                "ETH/USDT",
                "ETH/BTC",
                "ETH/USDT"
            ]
            self.timeframes = [
                "1h",
                "2h",
                "4h",
                "2h"
            ]
            self.markets = {}
            self.set_markets_calls = []
            self.urls = {}
            self.options = {}

        async def load_markets(self, reload=False, market_filter=None):
            pass

        def set_markets(self, markets):
            self.set_markets_calls.append(markets)

        def set_sandbox_mode(self, is_sandboxed):
            pass

    original_get_option_value = ccxt_client_util.get_option_value

    def _get_option_value_patch(client, option_key, *args, **kwargs):
        if option_key is enums.ExchangeClientOptions.INCLUDE_DISABLED_SYMBOLS_IN_AVAILABLE_SYMBOLS:
            return True
        return original_get_option_value(client, option_key, *args, **kwargs)

    with patch.object(ccxt_connector, 'client', new=MockCCXT()) as mocked_ccxt, \
        patch.object(ccxt_connector, '_ensure_auth', new=mock.AsyncMock()) as _ensure_auth_mock, \
        patch.object(ccxt_client_util, 'get_option_value', mock.Mock(side_effect=_get_option_value_patch)):
        await ccxt_connector.initialize_impl()
        assert len(ccxt_connector.symbols) == 541   # all enabled + diasabled symbols
        assert ccxt_connector.time_frames == {
            "1h",
            "2h",
            "4h",
        }
        assert mocked_ccxt.set_markets_calls in ([[]], [])  # depends on call order
        _ensure_auth_mock.assert_called_once()


async def test_set_symbol_partial_take_profit_stop_loss(ccxt_connector):
    with pytest.raises(NotImplementedError):
        await ccxt_connector.set_symbol_partial_take_profit_stop_loss("BTC/USDT", False,
                                                                     enums.TakeProfitStopLossMode.PARTIAL)


async def test_get_ccxt_order_type(ccxt_connector):
    with pytest.raises(RuntimeError):
        ccxt_connector.get_ccxt_order_type(None)
    with pytest.raises(RuntimeError):
        ccxt_connector.get_ccxt_order_type(enums.TraderOrderType.UNKNOWN)
    assert ccxt_connector.get_ccxt_order_type(enums.TraderOrderType.BUY_LIMIT) == enums.TradeOrderType.LIMIT.value
    assert ccxt_connector.get_ccxt_order_type(enums.TraderOrderType.STOP_LOSS_LIMIT) == enums.TradeOrderType.LIMIT.value
    assert ccxt_connector.get_ccxt_order_type(enums.TraderOrderType.TRAILING_STOP) == enums.TradeOrderType.MARKET.value
    assert ccxt_connector.get_ccxt_order_type(enums.TraderOrderType.SELL_MARKET) == enums.TradeOrderType.MARKET.value


async def test_get_trade_fee(exchange_manager, future_trader_simulator_with_default_linear):
    future_symbol = "BTC/USDT:USDT"
    future_fees_value = 0.0004
    spot_symbol = "BTC/USDT"
    config, fut_exchange_manager_inst, trader_inst, default_contract = future_trader_simulator_with_default_linear
    fut_exchange_manager_inst.is_future = True
    fut_ccxt_exchange = exchange_connectors.CCXTConnector(config, fut_exchange_manager_inst)
    spot_ccxt_exchange = exchange_connectors.CCXTConnector(exchange_manager.config, exchange_manager)

    # spot trading
    spot_ccxt_exchange.client.options['defaultType'] = enums.ExchangeTypes.SPOT.value
    await spot_ccxt_exchange.client.load_markets()
    spot_taker_fees_value = spot_ccxt_exchange.client.markets[spot_symbol]['taker']
    spot_maker_fees_value = spot_ccxt_exchange.client.markets[spot_symbol]['maker']
    spot_taker_fees_decimal = decimal.Decimal(str(spot_taker_fees_value))
    spot_maker_fees_decimal = decimal.Decimal(str(spot_maker_fees_value))
    assert spot_taker_fees_value > 0
    assert spot_maker_fees_value > 0
    assert spot_ccxt_exchange.get_trade_fee(spot_symbol, enums.TraderOrderType.BUY_LIMIT, decimal.Decimal("0.45"),
                                            decimal.Decimal(10000), "taker") == \
           _get_fees("taker", "BTC", spot_taker_fees_value, decimal.Decimal("0.45") * spot_taker_fees_decimal)
    assert spot_ccxt_exchange.get_trade_fee(spot_symbol, enums.TraderOrderType.SELL_LIMIT, decimal.Decimal("0.45"),
                                            decimal.Decimal(10000), "maker") == \
           _get_fees("maker", "USDT", spot_maker_fees_value, decimal.Decimal("4500") * spot_maker_fees_decimal)

    # future trading
    fut_ccxt_exchange.client.options['defaultType'] = enums.ExchangeTypes.FUTURE.value

    if forced_markets := mock_exchanges_data.MOCKED_EXCHANGE_SYMBOL_DETAILS.get(
        fut_exchange_manager_inst.exchange_name, None
    ):
        register_market_status_mocks(fut_exchange_manager_inst.exchange_name)
    await fut_ccxt_exchange.load_symbol_markets()
    # enforce taker and maker values
    set_future_exchange_fees(fut_ccxt_exchange, future_symbol, taker=future_fees_value, maker=future_fees_value)
    assert future_fees_value / 5 <= fut_ccxt_exchange.client.markets[future_symbol]['taker'] <= future_fees_value * 5
    # linear
    assert fut_ccxt_exchange.get_trade_fee(future_symbol, enums.TraderOrderType.BUY_LIMIT, decimal.Decimal("0.45"),
                                           decimal.Decimal(10000), "taker") == \
           _get_fees("taker", "USDT", future_fees_value, decimal.Decimal("1.800000"))
    # inverse
    fut_ccxt_exchange.client.markets[future_symbol]["inverse"] = True
    fut_ccxt_exchange.client.markets[future_symbol]["linear"] = False
    contract = contracts.FutureContract(pair=future_symbol,
                                        margin_type=enums.MarginType.ISOLATED,
                                        contract_type=enums.FutureContractType.INVERSE_PERPETUAL)
    fut_exchange_manager_inst.exchange.pair_contracts[future_symbol] = contract
    assert fut_ccxt_exchange.get_trade_fee(future_symbol, enums.TraderOrderType.BUY_LIMIT, decimal.Decimal("0.45"),
                                           decimal.Decimal(10000), "taker") == \
           _get_fees("taker", "BTC", future_fees_value, decimal.Decimal("0.00018"))


async def test_set_first_consecutive_authentication_error_at_if_unset(ccxt_connector):
    assert ccxt_connector.first_consecutive_authentication_error_at is None
    with mock.patch.object(ccxt_connector, 'get_exchange_current_time', return_value=123.456) as get_time_mock:
        # sets the value when None
        ccxt_connector.set_first_consecutive_authentication_error_at_if_unset()
        assert ccxt_connector.first_consecutive_authentication_error_at == 123.456
        get_time_mock.assert_called_once()
        get_time_mock.reset_mock()

        # does not overwrite when already set
        ccxt_connector.set_first_consecutive_authentication_error_at_if_unset()
        assert ccxt_connector.first_consecutive_authentication_error_at == 123.456
        get_time_mock.assert_not_called()


async def test_clear_first_consecutive_authentication_error_at(ccxt_connector):
    ccxt_connector.first_consecutive_authentication_error_at = 123.456
    ccxt_connector.clear_first_consecutive_authentication_error_at()
    assert ccxt_connector.first_consecutive_authentication_error_at is None
    # calling again when already None is fine
    ccxt_connector.clear_first_consecutive_authentication_error_at()
    assert ccxt_connector.first_consecutive_authentication_error_at is None


async def test_error_describer(ccxt_connector):
    with mock.patch.object(
        ccxt_connector, 'clear_first_consecutive_authentication_error_at', new=mock.Mock()
    ) as clear_first_consecutive_authentication_error_at_mock, mock.patch.object(
        ccxt_connector, 'set_first_consecutive_authentication_error_at_if_unset', new=mock.Mock()
    ) as set_first_consecutive_authentication_error_at_if_unset_mock:
        # test successful non-authenticated request: no mock called
        with ccxt_connector.error_describer(is_authenticated_request=False):
            pass
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        # test successful authenticated request: clear is called
        with ccxt_connector.error_describer(is_authenticated_request=True):
            pass
        clear_first_consecutive_authentication_error_at_mock.assert_called_once()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()
        clear_first_consecutive_authentication_error_at_mock.reset_mock()

        with pytest.raises(ZeroDivisionError, match="plop"):
            # random error is just forwarded
            with ccxt_connector.error_describer(is_authenticated_request=False):
                raise ZeroDivisionError("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(ccxt.DDoSProtection):
            # forwarded ccxt error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.DDoSProtection("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.FailedRequest):
            # transformed ccxt error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.InvalidNonce("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.NetworkError):
            # transformed ccxt error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.RequestTimeout("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(ccxt.ExchangeError):
            # forwarded ccxt error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        # proxied errors
        with pytest.raises(octobot_trading.errors.AuthenticationError):
            # transformed ccxt error: set is called on auth error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.AuthenticationError("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_called_once()
        set_first_consecutive_authentication_error_at_if_unset_mock.reset_mock()

        with pytest.raises(octobot_trading.errors.FailedRequest):
            # transformed ccxt error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeNotAvailable("plop")
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        # default host, not using proxy exception for generic exception
        with pytest.raises(octobot_trading.errors.AuthenticationError):
            # proxy connection error: set is called on auth error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.AuthenticationError from aiohttp.ClientConnectionError(
                    aiohttp.client_reqrep.ConnectionKey("host", 11, True, True, None, None, None), OSError("plop")
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_called_once()
        set_first_consecutive_authentication_error_at_if_unset_mock.reset_mock()

        # default host, using proxy exception for proxy exception
        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # proxy connection error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError from aiohttp.ClientProxyConnectionError(
                    aiohttp.client_reqrep.ConnectionKey("host", 11, True, True, None, None, None), OSError("plop")
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # non retriable proxy client error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError from aiohttp.ClientHttpProxyError(
                    aiohttp.client_reqrep.RequestInfo("www.google.com", "GET", {}, "www.google.com"), OSError("plop")
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # non retriable proxy client error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError from aiohttp.ClientHttpProxyError(
                    aiohttp.client_reqrep.RequestInfo("www.google.com", "GET", {}, "www.google.com"),
                    OSError("plop"),
                    message="random"
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.RetriableExchangeProxyError):
            # proxy client error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError from aiohttp.ClientHttpProxyError(
                    aiohttp.client_reqrep.RequestInfo("www.google.com", "GET", {}, "www.google.com"),
                    OSError("plop"),
                    message=f"random{next(iter(octobot_trading.constants.RETRIABLE_EXCHANGE_PROXY_ERRORS_DESC))}"
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # socks proxy error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.ExchangeError from ccxt_client_util.ProxyConnectionError(
                    aiohttp.client_reqrep.ConnectionKey("host", 11, True, True, None, None, None), OSError("plop")
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        ccxt_connector.exchange_manager.proxy_config.proxy_host = "host"
        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # proxy connection error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt.AuthenticationError from ccxt_client_util.ProxyConnectionError(
                    aiohttp.client_reqrep.ConnectionKey("host", 11, True, True, None, None, None), OSError("plop")
                )
        # no set call as it's a proxy error (not a real auth error)
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with pytest.raises(octobot_trading.errors.ExchangeProxyError):
            # proxy connection error
            with ccxt_connector.error_describer(is_authenticated_request=True):
                raise ccxt_client_util.ProxyConnectionError(
                    aiohttp.client_reqrep.ConnectionKey("host", 11, True, True, None, None, None), OSError("plop")
                )
        clear_first_consecutive_authentication_error_at_mock.assert_not_called()
        set_first_consecutive_authentication_error_at_if_unset_mock.assert_not_called()

        with mock.patch.object(
            ccxt_connector.exchange_manager.proxy_config, "get_last_proxied_request_url",
                mock.Mock(return_value="https///plop.com/coucou")
        ) as get_last_proxied_request_url_mock:
            with pytest.raises(octobot_trading.errors.AuthenticationError, match="plop"):
                # not proxied request error: set is called on auth error
                with ccxt_connector.error_describer(is_authenticated_request=True):
                    raise ccxt.AuthenticationError("plop")
            get_last_proxied_request_url_mock.assert_called_once()
            get_last_proxied_request_url_mock.reset_mock()
            clear_first_consecutive_authentication_error_at_mock.assert_not_called()
            set_first_consecutive_authentication_error_at_if_unset_mock.assert_called_once()
            set_first_consecutive_authentication_error_at_if_unset_mock.reset_mock()

            with pytest.raises(octobot_trading.errors.AuthenticationError, match="plop"):
                # not proxied request error: set is called on auth error
                ccxt_connector.client.last_request_url = "not_plop"
                with ccxt_connector.error_describer(is_authenticated_request=True):
                    raise ccxt.AuthenticationError("plop")
            get_last_proxied_request_url_mock.assert_called_once()
            get_last_proxied_request_url_mock.reset_mock()
            clear_first_consecutive_authentication_error_at_mock.assert_not_called()
            set_first_consecutive_authentication_error_at_if_unset_mock.assert_called_once()
            set_first_consecutive_authentication_error_at_if_unset_mock.reset_mock()

            with pytest.raises(octobot_trading.errors.AuthenticationError, match=re.escape(r"[Proxied] plop [URL: https///plop.com/coucou]")):
                # proxied request error: add prefix, set is called on auth error
                ccxt_connector.client.last_request_url = "https///plop.com/coucou"
                with ccxt_connector.error_describer(is_authenticated_request=True):
                    raise ccxt.AuthenticationError("plop")
            get_last_proxied_request_url_mock.assert_called_once()
            get_last_proxied_request_url_mock.reset_mock()
            clear_first_consecutive_authentication_error_at_mock.assert_not_called()
            set_first_consecutive_authentication_error_at_if_unset_mock.assert_called_once()
            set_first_consecutive_authentication_error_at_if_unset_mock.reset_mock()


class _LazyLoadMarketsMockCCXT:
    def __init__(self, populate_markets_on_load: bool = True):
        self.markets = {}
        self.has = {'obLoadMarketsForSymbols': True}
        self.urls = {'api': {'public': 'https://test.example'}}
        self.apiKey = None
        self.options = {}
        self.name = 'test'
        self.populate_markets_on_load = populate_markets_on_load

    async def ob_load_markets_for_symbols(self, symbols, reload=False, params=None):
        if self.populate_markets_on_load:
            for symbol in symbols:
                self.markets[symbol] = {'symbol': symbol}
        return []


class TestCcxtConnectorLoadMarketsForSymbols:

    async def test_persists_markets_cache_after_lazy_symbol_load(self, ccxt_connector):
        symbol = "BTC/ETH"
        with (
            mock.patch.object(ccxt_connector, 'client', new=_LazyLoadMarketsMockCCXT()),
            mock.patch.object(ccxt_connector, '_persist_markets_cache') as persist_markets_cache_mock,
        ):
            await ccxt_connector.load_markets_for_symbols([symbol])

        persist_markets_cache_mock.assert_called_once()

    async def test_skips_cache_persist_when_lazy_load_leaves_markets_empty(self, ccxt_connector):
        lazy_client = _LazyLoadMarketsMockCCXT(populate_markets_on_load=False)
        with (
            ccxt_clients_cache.isolated_empty_cache(),
            mock.patch.object(octobot_trading.constants, "USE_CCXT_SHARED_MARKETS_CACHE", False),
            mock.patch.object(ccxt_connector, 'client', new=lazy_client),
        ):
            await ccxt_connector.load_markets_for_symbols(["BTC/ETH"])
            client_key = ccxt_clients_cache.get_client_key(lazy_client, False)
            with pytest.raises(KeyError):
                ccxt_clients_cache.get_exchange_parsed_markets(client_key)

    async def test_accumulates_markets_in_cache_across_lazy_loads(self, ccxt_connector):
        symbol_a = "BTC/ETH"
        symbol_b = "ETH/USDT"
        lazy_client = _LazyLoadMarketsMockCCXT()
        with (
            ccxt_clients_cache.isolated_empty_cache(),
            mock.patch.object(octobot_trading.constants, "USE_CCXT_SHARED_MARKETS_CACHE", False),
            mock.patch.object(ccxt_connector, 'client', new=lazy_client),
        ):
            await ccxt_connector.load_markets_for_symbols([symbol_a])
            await ccxt_connector.load_markets_for_symbols([symbol_b])
            client_key = ccxt_clients_cache.get_client_key(lazy_client, False)
            cached_markets = ccxt_clients_cache.get_exchange_parsed_markets(client_key)
            cached_symbols = {market['symbol'] for market in cached_markets}
            assert cached_symbols == {symbol_a, symbol_b}


class _TickerMarketsMockCCXT:
    def __init__(self, symbols_to_add_on_fetch: list[str] | None = None):
        self.markets = {}
        self.urls = {'api': {'public': 'https://test.example'}}
        self.apiKey = None
        self.symbols_to_add_on_fetch = symbols_to_add_on_fetch or []

    async def fetch_ticker(self, symbol, params=None):
        for symbol_to_add in self.symbols_to_add_on_fetch:
            self.markets[symbol_to_add] = {'symbol': symbol_to_add}
        return {'symbol': symbol}

    async def fetch_tickers(self, symbols, params=None):
        for symbol_to_add in self.symbols_to_add_on_fetch:
            self.markets[symbol_to_add] = {'symbol': symbol_to_add}
        return {
            symbol_to_add: {'symbol': symbol_to_add}
            for symbol_to_add in self.symbols_to_add_on_fetch
        }


class TestCcxtConnectorGetPriceTicker:

    async def test_persists_markets_cache_when_ticker_adds_symbol(self, ccxt_connector):
        symbol = "BTC/ETH"
        ticker_client = _TickerMarketsMockCCXT(symbols_to_add_on_fetch=[symbol])
        with (
            mock.patch.object(ccxt_connector, 'client', new=ticker_client),
            mock.patch.object(ccxt_connector.adapter, 'adapt_ticker', side_effect=lambda ticker: ticker),
            mock.patch.object(
                ccxt_connector,
                '_persist_markets_cache_if_new_symbols',
            ) as persist_markets_cache_if_new_symbols_mock,
        ):
            await ccxt_connector.get_price_ticker(symbol)

        persist_markets_cache_if_new_symbols_mock.assert_called_once_with(set())

    async def test_skips_cache_persist_when_ticker_does_not_add_symbol(self, ccxt_connector):
        symbol = "BTC/ETH"
        ticker_client = _TickerMarketsMockCCXT()
        ticker_client.markets = {symbol: {'symbol': symbol}}
        with (
            mock.patch.object(ccxt_connector, 'client', new=ticker_client),
            mock.patch.object(ccxt_connector.adapter, 'adapt_ticker', side_effect=lambda ticker: ticker),
            mock.patch.object(ccxt_connector, '_persist_markets_cache') as persist_markets_cache_mock,
        ):
            await ccxt_connector.get_price_ticker(symbol)

        persist_markets_cache_mock.assert_not_called()


class TestCcxtConnectorGetAllCurrenciesPriceTicker:

    async def test_persists_markets_cache_when_tickers_add_symbols(self, ccxt_connector):
        symbol_a = "BTC/ETH"
        symbol_b = "ETH/USDT"
        ticker_client = _TickerMarketsMockCCXT(symbols_to_add_on_fetch=[symbol_a, symbol_b])
        with (
            mock.patch.object(ccxt_connector, 'client', new=ticker_client),
            mock.patch.object(ccxt_connector.adapter, 'adapt_ticker', side_effect=lambda ticker: ticker),
            mock.patch.object(
                ccxt_connector,
                '_persist_markets_cache_if_new_symbols',
            ) as persist_markets_cache_if_new_symbols_mock,
        ):
            await ccxt_connector.get_all_currencies_price_ticker(symbols=[symbol_a, symbol_b])

        persist_markets_cache_if_new_symbols_mock.assert_called_once_with(set())

    async def test_skips_cache_persist_when_tickers_do_not_add_symbols(self, ccxt_connector):
        symbol_a = "BTC/ETH"
        symbol_b = "ETH/USDT"
        ticker_client = _TickerMarketsMockCCXT()
        ticker_client.markets = {
            symbol_a: {'symbol': symbol_a},
            symbol_b: {'symbol': symbol_b},
        }
        with (
            mock.patch.object(ccxt_connector, 'client', new=ticker_client),
            mock.patch.object(ccxt_connector.adapter, 'adapt_ticker', side_effect=lambda ticker: ticker),
            mock.patch.object(ccxt_connector, '_persist_markets_cache') as persist_markets_cache_mock,
        ):
            await ccxt_connector.get_all_currencies_price_ticker(symbols=[symbol_a, symbol_b])

        persist_markets_cache_mock.assert_not_called()


def _get_fees(type, currency, rate, cost):
    return {
        enums.FeePropertyColumns.TYPE.value: type,
        enums.FeePropertyColumns.CURRENCY.value: currency,
        enums.FeePropertyColumns.RATE.value: rate,
        enums.FeePropertyColumns.COST.value: decimal.Decimal(str(cost)),
        enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: False,
    }
