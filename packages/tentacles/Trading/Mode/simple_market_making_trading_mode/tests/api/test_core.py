#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or modify it under the terms of the GNU
#  General Public License as published by the Free Software Foundation; either version 3.0 of the
#  License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#  even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with OctoBot. If not,
#  see <https://www.gnu.org/licenses/>.

import contextlib
import decimal

import mock
import pytest

import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.enums as commons_enums
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_trading.exchange_data as trading_exchange_data
import octobot_trading.exchanges as trading_exchanges
import octobot_tentacles_manager.api as tentacles_manager_api
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc

import tentacles.Meta.DSL_operators.exchange_operators as exchange_operators
import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as \
    advanced_reference_price_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.constants as market_making_constants
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.core as market_making_core
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as market_making_models
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as \
    simple_market_making_trading
import octobot_protocol.models as protocol_models


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def profile_data_with_full_mm_config() -> commons_profile_data.ProfileData:
    mm_config = {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_SPREAD: 0.5,
                simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_SPREAD: 5.0,
                simple_market_making_trading.SimpleMarketMakingTradingMode.BIDS_COUNT: 3,
                simple_market_making_trading.SimpleMarketMakingTradingMode.ASKS_COUNT: 3,
                simple_market_making_trading.SimpleMarketMakingTradingMode.ORDER_BOOK_DEPTH: {
                    simple_market_making_trading.SimpleMarketMakingTradingMode.CUMULATED_VOLUME_PERCENT: 1.0,
                    simple_market_making_trading.SimpleMarketMakingTradingMode.PERCENT_DAILY_TRADING_VOLUME: 2.0,
                },
                simple_market_making_trading.SimpleMarketMakingTradingMode.ORDERS_DISTRIBUTION: "linear",
                simple_market_making_trading.SimpleMarketMakingTradingMode.FUNDS_DISTRIBUTION: "valley",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    }
                ]
            }
        ]
    }

    return commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC")
        ],
        commons_profile_data.TradingData("USDT"),
        tentacles=[
            commons_profile_data.TentaclesData(
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
                mm_config
            )
        ]
    )


@pytest.fixture
def mm_data_by_exchange() -> dict[str, dict[str, market_making_models.MarketMakingData]]:
    return {
        "binance": {
            "BTC/USDT": market_making_models.MarketMakingData(
                exchange="binance",
                pair="BTC/USDT",
                pair_alias=None,
                price=decimal.Decimal("50000.0"),
                market_status={
                    Ecmsc.PRECISION.value: {
                        Ecmsc.PRECISION_AMOUNT.value: 2,
                        Ecmsc.PRECISION_PRICE.value: 2,
                    }
                },
                market_details=[
                    exchange_data_import.MarketDetails(
                        symbol="BTC/USDT",
                        time_frame=advanced_reference_price_import.DEFAULT_TIME_FRAME,
                        close=[45999.0, 45900.0, 50000.0, 50000.0, 50010.0],
                        open=[50000.0, 50000.0, 50000.0, 50000.0, 50000.0],
                        high=[50000.0, 50000.0, 50000.0, 50000.0, 50000.0],
                        low=[50000.0, 50000.0, 50000.0, 50000.0, 50000.0],
                        volume=[100.0, 89.0, 100.0, 40.0, 110.0],
                        time=[100.0, 101.0, 102.0, 103.0, 104.0],
                    )
                ],
                base_volume=decimal.Decimal("100.0"),
                quote_volume=decimal.Decimal("5000000.0"),
            )
        }
    }


def test_get_aggregated_price_sources_by_exchange():
    """Test get_aggregated_price_sources_by_exchange function."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC"),
            commons_profile_data.CryptoCurrencyData(["ETH/USDT"], name="ETH")
        ],
        commons_profile_data.TradingData("USDT")
    )

    mm_config = {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    }
                ]
            },
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "bingx",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    }
                ]
            },
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "ETH/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "kucoin",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "ETH/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    },
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE,
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "ETH/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("0.5"),
                        simple_market_making_trading.SimpleMarketMakingTradingMode.TIME_FRAME: commons_enums.TimeFrames.FOUR_HOURS.value,
                    }
                ]
            }
        ]
    }

    profile_data.set_tentacles_config(
        {
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(): mm_config
        }
    )

    mm_exchanges = ["binance", "kucoin", "bingx"]

    result = market_making_core.get_aggregated_price_sources_by_exchange(
        profile_data,
        mm_exchanges
    )

    assert result == {
        "binance": [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                weight=decimal.Decimal("1.0"),
                formula="",
            ),
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="ETH/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                weight=decimal.Decimal("1.0"),
                formula="",
            )
        ],
        "bingx": [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange=simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE,
                pair="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                weight=trading_constants.ZERO,
                formula="",
            )
        ],
        "kucoin": [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange=simple_market_making_trading.SimpleMarketMakingTradingMode.LOCAL_EXCHANGE_PRICE,
                pair="ETH/USDT",
                time_frame=commons_enums.TimeFrames.FOUR_HOURS.value,
                weight=decimal.Decimal("0.5"),
                formula="",
            )
        ]
    }


def test_get_aggregated_price_sources_by_exchange_empty_inputs():
    """Test get_aggregated_price_sources_by_exchange with empty exchanges list."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [],
        commons_profile_data.TradingData("USDT"),
        tentacles=[
            commons_profile_data.TentaclesData(
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
                {}
            )
        ]
    )

    mm_exchanges = []

    result = market_making_core.get_aggregated_price_sources_by_exchange(
        profile_data,
        mm_exchanges
    )

    assert result == {}


def test_get_aggregated_price_sources_by_exchange_no_pairs():
    """Test get_aggregated_price_sources_by_exchange when no pairs are configured."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [],
        commons_profile_data.TradingData("USDT"),
        tentacles=[
            commons_profile_data.TentaclesData(
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
                {
                    simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: []
                }
            )
        ]
    )

    mm_exchanges = ["binance"]

    result = market_making_core.get_aggregated_price_sources_by_exchange(
        profile_data,
        mm_exchanges
    )
    assert result == {
        "binance": []
    }


def test_get_aggregated_price_sources_by_exchange_multiple_sources_same_exchange():
    """Test get_aggregated_price_sources_by_exchange with multiple sources for same exchange."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC"),
            commons_profile_data.CryptoCurrencyData(["ETH/USDT"], name="ETH")
        ],
        commons_profile_data.TradingData("USDT")
    )

    mm_config = {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    },
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "BTC/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                        simple_market_making_trading.SimpleMarketMakingTradingMode.TIME_FRAME: commons_enums.TimeFrames.FOUR_HOURS.value,
                        simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA: "ma(close, 12)",
                    }
                ]
            },
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "ETH/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
                    {
                        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "ETH/USDT",
                        simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
                    }
                ]
            }
        ]
    }

    profile_data.set_tentacles_config(
        {
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(): mm_config
        }
    )

    mm_exchanges = ["binance"]

    result = market_making_core.get_aggregated_price_sources_by_exchange(
        profile_data,
        mm_exchanges
    )

    assert result == {
        "binance": [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                weight=decimal.Decimal("1.0"),
                formula="",
            ),
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=commons_enums.TimeFrames.FOUR_HOURS.value,
                weight=decimal.Decimal("1.0"),
                formula="ma(close, 12)",
            ),
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="ETH/USDT",
                time_frame=commons_enums.TimeFrames.ONE_HOUR.value,
                weight=decimal.Decimal("1.0"),
                formula="",
            )
        ],
    }


def test_get_trading_exchanges():
    """Test get_trading_exchanges function."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC"),
            commons_profile_data.CryptoCurrencyData(["ETH/USDT"], name="ETH")
        ],
        commons_profile_data.TradingData("USDT")
    )

    mm_config = {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: []
            },
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "ETH/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "kucoin",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: []
            },
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: []
            }
        ]
    }

    profile_data.set_tentacles_config(
        {
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(): mm_config
        }
    )

    mm_exchanges = ["binance", "kucoin", "bingx"]

    result = market_making_core.get_trading_exchanges(
        profile_data,
        mm_exchanges
    )

    assert result == ["binance", "kucoin", "bingx"]


def test_get_trading_exchanges_no_matching_exchanges():
    """Test get_trading_exchanges when no exchanges match."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC")
        ],
        commons_profile_data.TradingData("USDT")
    )

    mm_config = {
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: []
            }
        ]
    }

    profile_data.set_tentacles_config(
        {
            simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(): mm_config
        }
    )

    mm_exchanges = ["kucoin", "bingx"]

    result = market_making_core.get_trading_exchanges(
        profile_data,
        mm_exchanges
    )

    assert result == []


def test_get_trading_exchanges_empty_exchanges():
    """Test get_trading_exchanges with empty exchanges list."""
    profile_data = commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [
            commons_profile_data.CryptoCurrencyData(["BTC/USDT"], name="BTC")
        ],
        commons_profile_data.TradingData("USDT"),
        tentacles=[
            commons_profile_data.TentaclesData(
                simple_market_making_trading.SimpleMarketMakingTradingMode.get_name(),
                {
                    simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS: [
                        {
                            simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "BTC/USDT",
                            simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                            simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: []
                        }
                    ]
                }
            )
        ]
    )

    mm_exchanges = []

    result = market_making_core.get_trading_exchanges(
        profile_data,
        mm_exchanges
    )

    assert result == []


async def test_get_price_and_predicted_order_book(profile_data_with_full_mm_config, mm_data_by_exchange):
    """Test _get_price_and_predicted_order_book (legacy triple-arg API from octobot_wrapper)."""
    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.PRICE_KEY: decimal.Decimal("50000.0"),
            market_making_constants.BIDS_KEY: _get_order_book_data_dict([
                (49875.00, 2), (49312.50, 3.04), (48750.00, 4.1)
            ]),
            market_making_constants.ASKS_KEY: _get_order_book_data_dict([
                (50125.00, 2), (50687.50, 3), (51250.00, 4)
            ]),
            market_making_constants.VOLUME_KEY: {
                "BTC": decimal.Decimal("9"),
                "USDT": decimal.Decimal("450000"),
            }
        }
    }


async def test_get_price_and_predicted_order_book_with_formula(profile_data_with_full_mm_config, mm_data_by_exchange):
    """Test _get_price_and_predicted_order_book with formula."""
    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "ma(close, 2)[-1]"

    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.PRICE_KEY: decimal.Decimal("50005"),
            market_making_constants.BIDS_KEY: _get_order_book_data_dict([
                (49879.98, 2), (49317.43, 3.04), (48754.87, 4.1)
            ]),
            market_making_constants.ASKS_KEY: _get_order_book_data_dict([
                (50130.01, 2), (50692.56, 3), (51255.12, 4)
            ]),
            market_making_constants.VOLUME_KEY: {
                "BTC": decimal.Decimal("9"),
                "USDT": decimal.Decimal("450000"),
            }
        }
    }


async def test_get_price_and_predicted_order_book_with_invalid_formula(profile_data_with_full_mm_config, mm_data_by_exchange):
    ref_price_config = profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0]
    ref_price_config[simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "ma(close, ERROR, 2)[-1]"
    assert await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    ) == {
        "BTC/USDT": {
            market_making_constants.ERROR_KEY: "Invalid BTC/USDT reference price formula: Unknown name: ERROR"
        }
    }

    ref_price_config[simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "ma(close, 3)*0.6"
    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )
    assert result == {
        "BTC/USDT": {
            market_making_constants.ERROR_KEY: "Invalid BTC/USDT reference price formula: TypeError: can't multiply sequence by non-int of type 'float'"
        }
    }

    ref_price_config[simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "(ma(close,50)[-1]*0.4 + vwma(close, volume, 14)*0.6)+ 10"
    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )
    assert result == {
        "BTC/USDT": {
            market_making_constants.ERROR_KEY: "Invalid BTC/USDT reference price formula: TypeError: Invalid technical indicator parameter - InvalidOptionError"
        }
    }

    ref_price_config[simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = "close + 10000"
    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )
    assert result == {
        "BTC/USDT": {
            market_making_constants.ERROR_KEY: "Configured formula \"close + 10000\" should return a number, got ndarray (value: [np.float64(55999.0), np.float64(55900.0), '...', np.float64(60000.0), np.float64(60010.0)])"
        }
    }


async def test_get_price_and_predicted_order_book_with_error(profile_data_with_full_mm_config, mm_data_by_exchange):
    """Test _get_price_and_predicted_order_book with error handling."""
    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE] = []

    result = await market_making_core._get_price_and_predicted_order_book(
        profile_data_with_full_mm_config,
        mm_data_by_exchange,
        "binance"
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.ERROR_KEY: "BTC/USDT reference price on binance can't be computed from the following price sources: {}"
        }
    }


def _get_order_book_data_dict(price_and_amount_list: list[tuple[float, float]]) -> list[dict]:
    return market_making_core._book_order_data_to_dict(
        [
            order_book_distribution.BookOrderData(
                price=decimal.Decimal(str(price)),
                amount=decimal.Decimal(str(amount)),
                side=trading_enums.TradeOrderSide.BUY
            )
            for price, amount in price_and_amount_list
        ]
    )


async def test_get_minimal_volume_by_symbol(profile_data_with_full_mm_config, mm_data_by_exchange):
    """Test get_minimal_volume_by_symbol function."""
    volumes_by_symbol, error_by_symbol = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )
    assert volumes_by_symbol == {
        "BTC/USDT": {
            "BTC": decimal.Decimal("9"),
            "USDT": decimal.Decimal("450000"),
        }
    }
    assert error_by_symbol == {}

    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = (
        "(vwma(close, volume, 2)[-1] * 0.7 + ma(close, 2)[-1] * 0.3) / 2"
    )
    volumes_by_symbol, error_by_symbol = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )
    assert volumes_by_symbol == {
        "BTC/USDT": {
            "BTC": decimal.Decimal("9"),
            "USDT": decimal.Decimal("450000"),
        }
    }
    assert error_by_symbol == {}


async def test_get_minimal_volume_by_symbol_with_invalid_formula(profile_data_with_full_mm_config, mm_data_by_exchange):
    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA] = (
        "(vwma(close, volume, 2)[-1] * 0.7 + ma(close, ERROR, 2)[-1] * 0.3) / 2"
    )
    volumes_by_symbol, error_by_symbol = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )
    assert volumes_by_symbol == {}
    assert error_by_symbol == {
        "BTC/USDT": "Invalid BTC/USDT reference price formula: Unknown name: ERROR"
    }


async def test_get_minimal_volume_by_symbol_no_reference_price(profile_data_with_full_mm_config, mm_data_by_exchange):
    """Test get_minimal_volume_by_symbol function with no reference price configured."""
    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE] = []

    volumes_by_symbol, error_by_symbol = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )

    assert volumes_by_symbol == {}
    assert error_by_symbol == {
        "BTC/USDT": "BTC/USDT reference price on binance can't be computed from the following price sources: {}"
    }


async def test_get_minimal_volume_by_symbol_missing_pair_data(profile_data_with_full_mm_config):
    """Test get_minimal_volume_by_symbol function when pair data is missing."""
    mm_data_by_exchange = {
        "binance": {}
    }

    volumes_by_symbol, error_by_pair = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )

    assert volumes_by_symbol == {}
    assert error_by_pair == {
        "BTC/USDT": "BTC/USDT not found in binance all market data (price ticker empty or not found). BTC/USDT market is likely missing or disabled on binance"
    }


async def test_get_minimal_volume_by_symbol_multiple_pairs(profile_data_with_full_mm_config):
    """Test get_minimal_volume_by_symbol function with multiple pairs."""
    profile_data_with_full_mm_config.tentacles[0].config[
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
    ].append({
        simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR: "ETH/USDT",
        simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
        simple_market_making_trading.SimpleMarketMakingTradingMode.MIN_SPREAD: 0.5,
        simple_market_making_trading.SimpleMarketMakingTradingMode.MAX_SPREAD: 5.0,
        simple_market_making_trading.SimpleMarketMakingTradingMode.BIDS_COUNT: 3,
        simple_market_making_trading.SimpleMarketMakingTradingMode.ASKS_COUNT: 3,
        simple_market_making_trading.SimpleMarketMakingTradingMode.ORDER_BOOK_DEPTH: {
            simple_market_making_trading.SimpleMarketMakingTradingMode.CUMULATED_VOLUME_PERCENT: 1.0,
            simple_market_making_trading.SimpleMarketMakingTradingMode.PERCENT_DAILY_TRADING_VOLUME: 2.0,
        },
        simple_market_making_trading.SimpleMarketMakingTradingMode.ORDERS_DISTRIBUTION: "linear",
        simple_market_making_trading.SimpleMarketMakingTradingMode.FUNDS_DISTRIBUTION: "valley",
        simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE: [
            {
                simple_market_making_trading.SimpleMarketMakingTradingMode.EXCHANGE: "binance",
                simple_market_making_trading.SimpleMarketMakingTradingMode.PAIR: "ETH/USDT",
                simple_market_making_trading.SimpleMarketMakingTradingMode.WEIGHT: decimal.Decimal("1.0"),
            }
        ]
    })

    profile_data_with_full_mm_config.crypto_currencies.append(
        commons_profile_data.CryptoCurrencyData(["ETH/USDT"], name="ETH")
    )

    mm_data_by_exchange = {
        "binance": {
            "BTC/USDT": market_making_models.MarketMakingData(
                exchange="binance",
                pair="BTC/USDT",
                pair_alias=None,
                price=decimal.Decimal("50000.0"),
                market_status={
                    Ecmsc.PRECISION.value: {
                        Ecmsc.PRECISION_AMOUNT.value: 2,
                        Ecmsc.PRECISION_PRICE.value: 2,
                    }
                },
                market_details=[],
                base_volume=decimal.Decimal("100.0"),
                quote_volume=decimal.Decimal("5000000.0"),
            ),
            "ETH/USDT": market_making_models.MarketMakingData(
                exchange="binance",
                pair="ETH/USDT",
                pair_alias=None,
                price=decimal.Decimal("3000.0"),
                market_status={
                    Ecmsc.PRECISION.value: {
                        Ecmsc.PRECISION_AMOUNT.value: 2,
                        Ecmsc.PRECISION_PRICE.value: 2,
                    }
                },
                market_details=[],
                base_volume=decimal.Decimal("500.0"),
                quote_volume=decimal.Decimal("1500000.0"),
            )
        }
    }

    volumes_by_symbol, error_by_symbol = await market_making_core.get_minimal_volume_by_symbol(
        profile_data_with_full_mm_config,
        "binance",
        mm_data_by_exchange
    )

    assert "BTC/USDT" in volumes_by_symbol
    assert "ETH/USDT" in volumes_by_symbol
    assert error_by_symbol == {}

    assert "BTC" in volumes_by_symbol["BTC/USDT"]
    assert "USDT" in volumes_by_symbol["BTC/USDT"]
    assert "ETH" in volumes_by_symbol["ETH/USDT"]
    assert "USDT" in volumes_by_symbol["ETH/USDT"]

    assert volumes_by_symbol["BTC/USDT"]["BTC"] > trading_constants.ZERO
    assert volumes_by_symbol["BTC/USDT"]["USDT"] > trading_constants.ZERO
    assert volumes_by_symbol["ETH/USDT"]["ETH"] > trading_constants.ZERO
    assert volumes_by_symbol["ETH/USDT"]["USDT"] > trading_constants.ZERO


def test_format_market_making_volume_by_symbol_with_volumes_only():
    """Test format_market_making_volume_by_symbol with volumes only (no errors)."""
    volume_by_symbol = {
        "BTC/USDT": {
            "BTC": decimal.Decimal("9"),
            "USDT": decimal.Decimal("450000"),
        },
        "ETH/USDT": {
            "ETH": decimal.Decimal("5"),
            "USDT": decimal.Decimal("15000"),
        }
    }
    error_by_symbol = {}

    result = market_making_core.format_market_making_volume_by_symbol(
        volume_by_symbol,
        error_by_symbol
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.VOLUME_KEY: {
                "BTC": decimal.Decimal("9"),
                "USDT": decimal.Decimal("450000"),
            },
            market_making_constants.ERROR_KEY: None,
        },
        "ETH/USDT": {
            market_making_constants.VOLUME_KEY: {
                "ETH": decimal.Decimal("5"),
                "USDT": decimal.Decimal("15000"),
            },
            market_making_constants.ERROR_KEY: None,
        }
    }


def test_format_market_making_volume_by_symbol_with_errors_only():
    """Test format_market_making_volume_by_symbol with errors only (no volumes)."""
    volume_by_symbol = {}
    error_by_symbol = {
        "BTC/USDT": "BTC/USDT reference price on binance can't be computed from the following price sources: {}",
        "ETH/USDT": "ETH/USDT not found in binance all market data (price ticker empty or not found). ETH/USDT market is likely missing or disabled on binance"
    }

    result = market_making_core.format_market_making_volume_by_symbol(
        volume_by_symbol,
        error_by_symbol
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.VOLUME_KEY: None,
            market_making_constants.ERROR_KEY: "BTC/USDT reference price on binance can't be computed from the following price sources: {}",
        },
        "ETH/USDT": {
            market_making_constants.VOLUME_KEY: None,
            market_making_constants.ERROR_KEY: "ETH/USDT not found in binance all market data (price ticker empty or not found). ETH/USDT market is likely missing or disabled on binance",
        }
    }


def test_format_market_making_volume_by_symbol_with_both():
    """Test format_market_making_volume_by_symbol with both volumes and errors for different symbols."""
    volume_by_symbol = {
        "BTC/USDT": {
            "BTC": decimal.Decimal("9"),
            "USDT": decimal.Decimal("450000"),
        }
    }
    error_by_symbol = {
        "ETH/USDT": "ETH/USDT not found in binance all market data (price ticker empty or not found). ETH/USDT market is likely missing or disabled on binance"
    }

    result = market_making_core.format_market_making_volume_by_symbol(
        volume_by_symbol,
        error_by_symbol
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.VOLUME_KEY: {
                "BTC": decimal.Decimal("9"),
                "USDT": decimal.Decimal("450000"),
            },
            market_making_constants.ERROR_KEY: None,
        },
        "ETH/USDT": {
            market_making_constants.VOLUME_KEY: None,
            market_making_constants.ERROR_KEY: "ETH/USDT not found in binance all market data (price ticker empty or not found). ETH/USDT market is likely missing or disabled on binance",
        }
    }


def test_format_market_making_volume_by_symbol_empty_inputs():
    """Test format_market_making_volume_by_symbol with empty inputs."""
    volume_by_symbol = {}
    error_by_symbol = {}

    result = market_making_core.format_market_making_volume_by_symbol(
        volume_by_symbol,
        error_by_symbol
    )

    assert result == {}


def test_format_market_making_volume_by_symbol_multiple_symbols_mixed():
    """Test format_market_making_volume_by_symbol with multiple symbols in various states."""
    volume_by_symbol = {
        "BTC/USDT": {
            "BTC": decimal.Decimal("9"),
            "USDT": decimal.Decimal("450000"),
        },
        "ETH/USDT": {
            "ETH": decimal.Decimal("5"),
            "USDT": decimal.Decimal("15000"),
        }
    }
    error_by_symbol = {
        "ETH/USDT": "Some error occurred",
        "XRP/USDT": "XRP/USDT not found in binance all market data (price ticker empty or not found). XRP/USDT market is likely missing or disabled on binance"
    }

    result = market_making_core.format_market_making_volume_by_symbol(
        volume_by_symbol,
        error_by_symbol
    )

    assert result == {
        "BTC/USDT": {
            market_making_constants.VOLUME_KEY: {
                "BTC": decimal.Decimal("9"),
                "USDT": decimal.Decimal("450000"),
            },
            market_making_constants.ERROR_KEY: None,
        },
        "ETH/USDT": {
            market_making_constants.VOLUME_KEY: {
                "ETH": decimal.Decimal("5"),
                "USDT": decimal.Decimal("15000"),
            },
            market_making_constants.ERROR_KEY: "Some error occurred",
        },
        "XRP/USDT": {
            market_making_constants.VOLUME_KEY: None,
            market_making_constants.ERROR_KEY: "XRP/USDT not found in binance all market data (price ticker empty or not found). XRP/USDT market is likely missing or disabled on binance",
        }
    }


def _market_making_ticker(**overrides) -> dict:
    return {
        trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 5000,
        trading_enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: 10,
        trading_enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: 50000,
        **overrides,
    }


class TestCreateMarketData:
    def test_uses_both_volumes_from_ticker_when_present(self):
        ticker = _market_making_ticker()
        market_status = {Ecmsc.PRECISION.value: {Ecmsc.PRECISION_PRICE.value: 2}}

        market_data = market_making_core._create_market_data(
            "dexscreener",
            "BTC/USDT",
            None,
            ticker,
            {"BTC/USDT": market_status},
            [],
        )

        assert market_data.exchange == "dexscreener"
        assert market_data.pair == "BTC/USDT"
        assert market_data.pair_alias is None
        assert market_data.price == decimal.Decimal("5000")
        assert market_data.base_volume == decimal.Decimal("10")
        assert market_data.quote_volume == decimal.Decimal("50000")
        assert market_data.market_status == market_status
        assert market_data.market_details == []

    def test_computes_quote_volume_when_quote_is_none(self):
        ticker = _market_making_ticker(
            **{trading_enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: None}
        )

        market_data = market_making_core._create_market_data(
            "dexscreener", "BTC/USDT", None, ticker, {}, []
        )

        assert market_data.base_volume == decimal.Decimal("10")
        assert market_data.quote_volume == decimal.Decimal("50000")

    def test_computes_base_volume_when_base_is_none(self):
        ticker = _market_making_ticker(
            **{trading_enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: None}
        )

        market_data = market_making_core._create_market_data(
            "dexscreener", "BTC/USDT", None, ticker, {}, []
        )

        assert market_data.base_volume == decimal.Decimal("10")
        assert market_data.quote_volume == decimal.Decimal("50000")

    def test_uses_zero_volumes_when_both_volumes_are_none(self):
        ticker = _market_making_ticker(
            **{
                trading_enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: None,
                trading_enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: None,
            }
        )

        market_data = market_making_core._create_market_data(
            "dexscreener", "BTC/USDT", None, ticker, {}, []
        )

        assert market_data.price == decimal.Decimal("5000")
        assert market_data.base_volume == trading_constants.ZERO
        assert market_data.quote_volume == trading_constants.ZERO

    def test_uses_nan_price_and_zero_volumes_when_ticker_is_none(self):
        market_data = market_making_core._create_market_data(
            "dexscreener", "BTC/USDT", None, None, {}, []
        )

        assert market_data.price.is_nan()
        assert market_data.base_volume == trading_constants.ZERO
        assert market_data.quote_volume == trading_constants.ZERO

    def test_uses_nan_price_and_zero_volumes_when_close_is_none(self):
        ticker = {
            trading_enums.ExchangeConstantsTickersColumns.SYMBOL.value: "USDT/KGS",
            trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: None,
            trading_enums.ExchangeConstantsTickersColumns.LAST.value: None,
            trading_enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: 0.0,
            trading_enums.ExchangeConstantsTickersColumns.QUOTE_VOLUME.value: None,
        }

        market_data = market_making_core._create_market_data(
            "cne", "USDT/KGS", None, ticker, {}, []
        )

        assert market_data.price.is_nan()
        assert market_data.base_volume == trading_constants.ZERO
        assert market_data.quote_volume == trading_constants.ZERO


def _profile_data_for_market_making_fill(exchange_internal_name="binance"):
    return commons_profile_data.ProfileData(
        commons_profile_data.ProfileDetailsData(),
        [],
        commons_profile_data.TradingData("USDT"),
        exchanges=[
            commons_profile_data.ExchangeData(internal_name=exchange_internal_name)
        ],
    )


@contextlib.asynccontextmanager
async def _mock_exchange_manager_context(exchange_manager):
    yield exchange_manager


async def _call_fill_market_making_data_by_symbol(
    price_sources,
    available_symbols,
    formula_init_patches=None,
):
    profile_data = _profile_data_for_market_making_fill()
    mm_data_by_symbol_by_exchange = {}
    exchange_manager = mock.Mock()
    exchange_manager.exchange.get_all_available_symbols = mock.Mock(
        return_value=available_symbols
    )
    ticker_updater = mock.Mock()
    ticker_updater.fetch_all_tickers = mock.AsyncMock(return_value={})
    ticker_cache = mock.Mock()
    ticker_cache.get_all_tickers = mock.Mock(return_value={})

    patches = [
        mock.patch.object(
            trading_exchanges,
            "exchange_manager_from_exchange_data",
            side_effect=lambda *args, **kwargs: _mock_exchange_manager_context(exchange_manager),
        ),
        mock.patch.object(
            trading_exchanges,
            "create_temporary_exchange_channels_and_producers",
            mock.AsyncMock(),
        ),
        mock.patch.object(
            tentacles_manager_api,
            "get_full_tentacles_setup_config",
            return_value=mock.Mock(),
        ),
        mock.patch.object(
            trading_exchange_data.TickerUpdater,
            "get_ticker_cache",
            return_value=ticker_cache,
        ),
        mock.patch.object(
            market_making_core,
            "_fetch_tickers",
            mock.AsyncMock(return_value=({}, ticker_updater)),
        ),
    ]
    if formula_init_patches:
        patches.extend(formula_init_patches)

    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        await market_making_core._fill_market_making_data_by_symbol(
            profile_data,
            "binance",
            False,
            price_sources,
            mm_data_by_symbol_by_exchange,
            with_market_status=False,
            auth=None,
        )

    return mm_data_by_symbol_by_exchange, ticker_updater.fetch_all_tickers


class TestFillMarketMakingDataBySymbol:
    async def test_skips_ticker_fetch_for_unsupported_ref_price_symbol_with_formula(self):
        price_sources = [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=advanced_reference_price_import.DEFAULT_TIME_FRAME,
                weight=decimal.Decimal("1.0"),
                formula="50000",
            )
        ]
        formula_init_patches = [
            mock.patch.object(
                trading_api,
                "get_watched_timeframes",
                return_value=[commons_enums.TimeFrames.ONE_HOUR.value],
            ),
            mock.patch.object(exchange_operators, "create_ohlcv_operators", return_value=[]),
            mock.patch.object(exchange_operators, "create_price_operators", return_value=[]),
        ]
        mm_data_by_symbol_by_exchange, fetch_all_tickers_mock = await _call_fill_market_making_data_by_symbol(
            price_sources,
            available_symbols={"BTC/ETH", "ETH/USDT"},
            formula_init_patches=formula_init_patches,
        )

        assert fetch_all_tickers_mock.call_count == 0 or all(
            "BTC/USDT" not in call_args.args[0]
            for call_args in fetch_all_tickers_mock.call_args_list
        )
        btc_usdt_data = mm_data_by_symbol_by_exchange["binance"]["BTC/USDT"]
        assert btc_usdt_data.price.is_nan()
        assert btc_usdt_data.base_volume == trading_constants.ZERO
        assert btc_usdt_data.quote_volume == trading_constants.ZERO

    async def test_still_fetches_formula_dependency_symbols(self):
        price_sources = [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=advanced_reference_price_import.DEFAULT_TIME_FRAME,
                weight=decimal.Decimal("1.0"),
                formula="price('BTC/ETH')*price('ETH/USDT')",
            )
        ]
        exchange_manager = mock.Mock()
        exchange_manager.get_exchange_symbol = mock.Mock(
            side_effect=lambda symbol, **kwargs: symbol
        )
        formula_init_patches = [
            mock.patch.object(
                trading_api,
                "get_watched_timeframes",
                return_value=[commons_enums.TimeFrames.ONE_HOUR.value],
            ),
            mock.patch.object(
                exchange_operators,
                "create_ohlcv_operators",
                return_value=exchange_operators.create_ohlcv_operators(
                    exchange_manager, "BTC/USDT", commons_enums.TimeFrames.ONE_HOUR.value
                ),
            ),
            mock.patch.object(
                exchange_operators,
                "create_price_operators",
                return_value=exchange_operators.create_price_operators(exchange_manager, "BTC/USDT"),
            ),
        ]
        mm_data_by_symbol_by_exchange, fetch_all_tickers_mock = await _call_fill_market_making_data_by_symbol(
            price_sources,
            available_symbols={"BTC/ETH", "ETH/USDT"},
            formula_init_patches=formula_init_patches,
        )

        assert fetch_all_tickers_mock.call_count == 1
        fetched_symbols = fetch_all_tickers_mock.call_args.args[0]
        assert "BTC/USDT" not in fetched_symbols
        assert "BTC/ETH" in fetched_symbols
        assert "ETH/USDT" in fetched_symbols
        assert set(mm_data_by_symbol_by_exchange["binance"]) == {"BTC/USDT", "BTC/ETH", "ETH/USDT"}

    async def test_fetches_ticker_for_unsupported_symbol_without_formula(self):
        price_sources = [
            advanced_reference_price_import.AdvancedPriceSource(
                exchange="binance",
                pair="BTC/USDT",
                time_frame=advanced_reference_price_import.DEFAULT_TIME_FRAME,
                weight=decimal.Decimal("1.0"),
                formula="",
            )
        ]
        mm_data_by_symbol_by_exchange, fetch_all_tickers_mock = await _call_fill_market_making_data_by_symbol(
            price_sources,
            available_symbols={"BTC/ETH", "ETH/USDT"},
        )

        assert fetch_all_tickers_mock.call_count == 1
        assert fetch_all_tickers_mock.call_args.args[0] == ["BTC/USDT"]


def _mock_create_price_operators(prices_by_symbol: dict[str, float]):
    import tentacles.Meta.DSL_operators.exchange_operators.exchange_public_data_operators.price_operators as price_operators_module

    def create_price_operators(exchange_manager, symbol, price_by_symbol=None, **kwargs):
        class _MockPriceOperator(price_operators_module.PriceOperator):
            @staticmethod
            def get_name() -> str:
                return "price"

            async def pre_compute(self) -> None:
                resolved_symbol = self.get_symbol() or symbol
                self.value = prices_by_symbol[resolved_symbol]

        return [_MockPriceOperator]

    return create_price_operators


def _cross_pair_formula_mm_data_by_exchange(
    btc_eth_price: decimal.Decimal,
    eth_usdt_price: decimal.Decimal,
) -> dict[str, dict[str, market_making_models.MarketMakingData]]:
    market_status = {
        Ecmsc.PRECISION.value: {
            Ecmsc.PRECISION_AMOUNT.value: 2,
            Ecmsc.PRECISION_PRICE.value: 2,
        }
    }
    nan = decimal.Decimal("nan")
    zero_volume = trading_constants.ZERO
    return {
        "binance": {
            "BTC/USDT": market_making_models.MarketMakingData(
                exchange="binance",
                pair="BTC/USDT",
                pair_alias=None,
                price=nan,
                market_status=market_status,
                market_details=[],
                base_volume=zero_volume,
                quote_volume=zero_volume,
            ),
            "BTC/ETH": market_making_models.MarketMakingData(
                exchange="binance",
                pair="BTC/ETH",
                pair_alias=None,
                price=btc_eth_price,
                market_status=market_status,
                market_details=[],
                base_volume=decimal.Decimal("100.0"),
                quote_volume=decimal.Decimal("1500.0"),
            ),
            "ETH/USDT": market_making_models.MarketMakingData(
                exchange="binance",
                pair="ETH/USDT",
                pair_alias=None,
                price=eth_usdt_price,
                market_status=market_status,
                market_details=[],
                base_volume=decimal.Decimal("1000.0"),
                quote_volume=decimal.Decimal("3333333.0"),
            ),
        }
    }


class TestGetPriceAndPredictedOrderBook:
    async def test_computes_order_book_with_nan_price_and_volume_when_formula_set(
        self, profile_data_with_full_mm_config
    ):
        btc_eth_price = decimal.Decimal("15")
        eth_usdt_price = decimal.Decimal("50000") / btc_eth_price
        expected_price = decimal.Decimal("50000")

        profile_data_with_full_mm_config.tentacles[0].config[
            simple_market_making_trading.SimpleMarketMakingTradingMode.CONFIG_PAIR_SETTINGS
        ][0][simple_market_making_trading.SimpleMarketMakingTradingMode.REFERENCE_PRICE][0][
            simple_market_making_trading.SimpleMarketMakingTradingMode.FORMULA
        ] = "price('BTC/ETH')*price('ETH/USDT')"

        mm_data_by_exchange = _cross_pair_formula_mm_data_by_exchange(btc_eth_price, eth_usdt_price)
        prices_by_symbol = {
            "BTC/ETH": float(btc_eth_price),
            "ETH/USDT": float(eth_usdt_price),
        }

        with mock.patch.object(
            exchange_operators,
            "create_price_operators",
            side_effect=_mock_create_price_operators(prices_by_symbol),
        ), mock.patch.object(
            exchange_operators,
            "create_ohlcv_operators",
            return_value=[],
        ):
            result = await market_making_core._get_price_and_predicted_order_book(
                profile_data_with_full_mm_config,
                mm_data_by_exchange,
                "binance",
            )

        assert market_making_constants.ERROR_KEY not in result["BTC/USDT"]
        assert result["BTC/USDT"][market_making_constants.PRICE_KEY] == expected_price
        assert result["BTC/USDT"][market_making_constants.BIDS_KEY] == _get_order_book_data_dict([
            (49875.00, 0.02), (49312.50, 0.03), (48750.00, 0.04)
        ])
        assert result["BTC/USDT"][market_making_constants.ASKS_KEY] == _get_order_book_data_dict([
            (50125.00, 0.02), (50687.50, 0.03), (51250.00, 0.04)
        ])
        assert result["BTC/USDT"][market_making_constants.VOLUME_KEY] == {
            "BTC": decimal.Decimal("0.09"),
            "USDT": decimal.Decimal("4500"),
        }
