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

import decimal

import pytest

import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.enums as commons_enums
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc

import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_reference_price as \
    advanced_reference_price_import
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.constants as market_making_constants
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.core as market_making_core
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as market_making_models
import tentacles.Trading.Mode.simple_market_making_trading_mode.simple_market_making_trading as \
    simple_market_making_trading


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
