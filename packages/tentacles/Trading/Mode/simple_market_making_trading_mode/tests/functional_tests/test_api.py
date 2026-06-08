#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  Functional integration tests for predicted_order_book and market_making_volume (live BingX + Dexscreener).

import typing

import pytest

import octobot_commons
import octobot_commons.symbols.symbol_util as commons_symbols

import tentacles.Trading.Mode.simple_market_making_trading_mode.api.api_handlers as api_handlers
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.constants as api_constants


BINGX_EXCHANGE_NAME = "bingx"
DEXSCREENER_EXCHANGE_NAME = "dexscreener"
BINGX_TRADING_PAIR = "BTC/USDT"
DEX_TRADING_PAIR = "BTCB/USDT"

BTCB_TOKEN_ADDRESS = "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
WBNB_TOKEN_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
USDT_TOKEN_ADDRESS = "0x55d398326f99059fF775485246999027B3197955"
WBTC_TOKEN_ADDRESS = "0x0555E30da8f98308EdB960aa94C0Db47230d2B9c"

BSC_NETWORK_NAME = "BEP20"
BSC_DEX_NAME = "UNISWAP"
BSC_DEX_SYMBOL_SUFFIX = (
    f"{octobot_commons.NETWORK_SEPARATOR}{BSC_NETWORK_NAME}"
    f"{octobot_commons.DEX_SEPARATOR}{BSC_DEX_NAME}"
)
DEX_BTCB_USDT_TRADING_PAIR = f"{DEX_TRADING_PAIR}{BSC_DEX_SYMBOL_SUFFIX}"
BSC_ANY_DEX_SYMBOL_SUFFIX = (
    f"{octobot_commons.NETWORK_SEPARATOR}{BSC_NETWORK_NAME}"
    f"{octobot_commons.DEX_SEPARATOR}{octobot_commons.ANY_DEX_WILDCARD}"
)
DEX_BTCB_USDT_ANY_DEX_TRADING_PAIR = f"{DEX_TRADING_PAIR}{BSC_ANY_DEX_SYMBOL_SUFFIX}"

CROSS_PAIR_SYMBOL_FORMULA = (
    f"price('{BTCB_TOKEN_ADDRESS}/{WBNB_TOKEN_ADDRESS}{BSC_DEX_SYMBOL_SUFFIX}')"
    f"*price('{WBNB_TOKEN_ADDRESS}/{USDT_TOKEN_ADDRESS}{BSC_DEX_SYMBOL_SUFFIX}')"
)
CROSS_PAIR_ADDRESS_FORMULA = (
    f'price("{BTCB_TOKEN_ADDRESS}/{WBNB_TOKEN_ADDRESS}{BSC_DEX_SYMBOL_SUFFIX}")'
    f'*price("{WBNB_TOKEN_ADDRESS}/{USDT_TOKEN_ADDRESS}{BSC_DEX_SYMBOL_SUFFIX}")'
)
CROSS_PAIR_ANY_DEX_ADDRESS_FORMULA = (
    f'price("{BTCB_TOKEN_ADDRESS}/{WBNB_TOKEN_ADDRESS}{BSC_ANY_DEX_SYMBOL_SUFFIX}")'
    f'*price("{WBNB_TOKEN_ADDRESS}/{USDT_TOKEN_ADDRESS}{BSC_ANY_DEX_SYMBOL_SUFFIX}")'
)
DIRECT_WBTC_USDT_ADDRESS_FORMULA = (
    f'price("{WBTC_TOKEN_ADDRESS}/{USDT_TOKEN_ADDRESS}{BSC_DEX_SYMBOL_SUFFIX}")'
)

pytestmark = pytest.mark.asyncio


def _bingx_exchange() -> dict:
    return {
        "id": "bingx-config",
        "name": BINGX_EXCHANGE_NAME,
        "exchange": BINGX_EXCHANGE_NAME,
        "sandboxed": False,
    }


def _base_pair_settings(
    trading_pair: str,
    exchange: str,
    reference_price_entries: list[dict],
) -> dict:
    return {
        "trading_pair": trading_pair,
        "exchange": exchange,
        "reference_price": reference_price_entries,
        "min_spread": 0.3,
        "max_spread": 0.5,
        "order_book_depth": {
            "cumulated_volume_percent": 1,
            "percent_daily_trading_volume": 0.45,
        },
        "bids_count": 10,
        "asks_count": 10,
        "orders_distribution": "linear",
        "funds_distribution": "valley",
        "max_base_budget": 0,
        "max_quote_budget": 0,
    }


def _market_making_dispatch_request(
    request_type: str,
    exchanges: list[dict],
    pair_settings: list[dict],
) -> dict:
    return {
        "type": request_type,
        "exchanges": exchanges,
        "config": {
            "name": "SimpleMarketMakingTradingMode",
            "config": {
                "configuration_type": "market_making",
                "pair_settings": pair_settings,
                "required_strategies": [],
            },
        },
    }


def _predicted_order_book_request(
    exchanges: list[dict],
    pair_settings: list[dict],
) -> dict:
    return _market_making_dispatch_request("predicted_order_book", exchanges, pair_settings)


def _market_making_volume_request(
    exchanges: list[dict],
    pair_settings: list[dict],
) -> dict:
    return _market_making_dispatch_request("market_making_volume", exchanges, pair_settings)


def _assert_successful_predicted_order_book(
    body: typing.Any,
    exchange: str,
    symbol: str,
) -> None:
    assert exchange in body, f"expected exchange {exchange!r} in response, got keys: {list(body)}"
    by_symbol = body[exchange]
    assert symbol in by_symbol, f"expected symbol {symbol!r} for {exchange}, got keys: {list(by_symbol)}"
    order_book = by_symbol[symbol]
    if api_constants.ERROR_KEY in order_book:
        pytest.fail(f"unexpected order book error for {exchange}/{symbol}: {order_book[api_constants.ERROR_KEY]}")
    assert order_book[api_constants.PRICE_KEY] > 0
    assert isinstance(order_book[api_constants.BIDS_KEY], list)
    assert isinstance(order_book[api_constants.ASKS_KEY], list)
    assert len(order_book[api_constants.BIDS_KEY]) > 0
    assert len(order_book[api_constants.ASKS_KEY]) > 0
    first_bid = order_book[api_constants.BIDS_KEY][0]
    for key in (api_constants.PRICE_KEY, api_constants.AMOUNT_KEY, api_constants.TOTAL_KEY):
        assert key in first_bid


def _assert_successful_market_making_volume(
    body: typing.Any,
    exchange: str,
    symbol: str,
) -> None:
    assert exchange in body, f"expected exchange {exchange!r} in response, got keys: {list(body)}"
    by_symbol = body[exchange]
    assert symbol in by_symbol, f"expected symbol {symbol!r} for {exchange}, got keys: {list(by_symbol)}"
    per_symbol = by_symbol[symbol]
    assert api_constants.VOLUME_KEY in per_symbol
    assert api_constants.ERROR_KEY in per_symbol
    if per_symbol[api_constants.ERROR_KEY]:
        pytest.fail(
            f"unexpected volume error for {exchange}/{symbol}: {per_symbol[api_constants.ERROR_KEY]}"
        )
    volume = per_symbol[api_constants.VOLUME_KEY]
    assert isinstance(volume, dict)
    base, quote = commons_symbols.parse_symbol(symbol).base_and_quote()
    assert volume[base] > 0
    assert volume[quote] > 0


class TestDispatchMarketMakingRequestPredictedOrderBook:
    async def test_bingx_spot_btc_usdt(self):
        request_data = _predicted_order_book_request(
            exchanges=[_bingx_exchange()],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": BINGX_EXCHANGE_NAME,
                            "pair": BINGX_TRADING_PAIR,
                            "weight": 1,
                            "formula": "",
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_bingx_with_dexscreener_cross_pair_symbol_formula(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": BINGX_TRADING_PAIR,
                            "weight": 1,
                            "formula": CROSS_PAIR_SYMBOL_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_dexscreener_token_address_formula(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": DEX_TRADING_PAIR,
                            "weight": 1,
                            "formula": CROSS_PAIR_ADDRESS_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_dexscreener_direct_btcb_usdt(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": DEX_BTCB_USDT_TRADING_PAIR,
                            "weight": 1,
                            "formula": "",
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_dexscreener_direct_btcb_usdt_any_dex(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": DEX_BTCB_USDT_ANY_DEX_TRADING_PAIR,
                            "weight": 1,
                            "formula": "",
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_dexscreener_any_dex_cross_pair_address_formula(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": DEX_TRADING_PAIR,
                            "weight": 1,
                            "formula": CROSS_PAIR_ANY_DEX_ADDRESS_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_dexscreener_cross_pair_address_formula_with_unified_dex_reference_pair(self):
        request_data = _predicted_order_book_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": DEX_BTCB_USDT_TRADING_PAIR,
                            "weight": 1,
                            "formula": CROSS_PAIR_ADDRESS_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_predicted_order_book(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)


class TestDispatchMarketMakingRequestMarketMakingVolume:
    async def test_bingx_with_bingx_price_source(self):
        request_data = _market_making_volume_request(
            exchanges=[_bingx_exchange()],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": BINGX_EXCHANGE_NAME,
                            "pair": BINGX_TRADING_PAIR,
                            "weight": 1,
                            "formula": "",
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_market_making_volume(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_bingx_with_dexscreener_cross_pair_symbol_formula(self):
        request_data = _market_making_volume_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": BINGX_TRADING_PAIR,
                            "weight": 1,
                            "formula": CROSS_PAIR_SYMBOL_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_market_making_volume(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)

    async def test_bingx_with_dexscreener_direct_wbtc_usdt_address_formula(self):
        request_data = _market_making_volume_request(
            exchanges=[
                _bingx_exchange(),
                {
                    "id": "dexscreener-config",
                    "name": DEXSCREENER_EXCHANGE_NAME,
                    "exchange": DEXSCREENER_EXCHANGE_NAME,
                    "sandboxed": False,
                },
            ],
            pair_settings=[
                _base_pair_settings(
                    BINGX_TRADING_PAIR,
                    BINGX_EXCHANGE_NAME,
                    [
                        {
                            "exchange": DEXSCREENER_EXCHANGE_NAME,
                            "pair": BINGX_TRADING_PAIR,
                            "weight": 1,
                            "formula": DIRECT_WBTC_USDT_ADDRESS_FORMULA,
                        }
                    ],
                )
            ],
        )
        body, status = await api_handlers.dispatch_market_making_request(request_data)
        assert status == 200
        _assert_successful_market_making_volume(body, BINGX_EXCHANGE_NAME, BINGX_TRADING_PAIR)
