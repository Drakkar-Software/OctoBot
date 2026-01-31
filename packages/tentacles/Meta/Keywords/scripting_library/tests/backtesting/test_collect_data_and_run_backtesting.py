#  Drakkar-Software OctoBot-Tentacles
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
import pytest

import octobot_commons.enums as commons_enums
import octobot_commons.profiles.profile_data as commons_profile_data
import octobot_commons.constants as commons_constants

import octobot_trading.api
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache
import octobot_trading.util.test_tools.exchange_data as exchange_data_import

import tentacles.Meta.Keywords.scripting_library as scripting_library
import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Trading.Mode.index_trading_mode.index_trading as index_trading


@pytest.fixture
def trading_mode_tentacles_data() -> commons_profile_data.TentaclesData:
    distribution = [
        {
            index_distribution.DISTRIBUTION_NAME: "BTC",
            index_distribution.DISTRIBUTION_VALUE: 50.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "ETH",
            index_distribution.DISTRIBUTION_VALUE: 30.0,
        },
        {
            index_distribution.DISTRIBUTION_NAME: "USD",  # Will be replaced by reference market
            index_distribution.DISTRIBUTION_VALUE: 20.0,
        },
    ]
    
    # Create test trading mode config
    trading_mode_config = {
        index_trading.IndexTradingModeProducer.INDEX_CONTENT: distribution,
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT: 5.0,
        index_trading.IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE: "test_profile",
        index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES: [
            {
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: "test_profile",
                index_trading.IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: 5.0,
            }
        ],
    }
    return commons_profile_data.TentaclesData(
        name=index_trading.IndexTradingMode.get_name(),
        config=trading_mode_config
    )

@pytest.mark.asyncio
async def test_collect_candles_without_backend_and_run_backtesting(trading_mode_tentacles_data):
    # 1. init strategy
    exchange_data = exchange_data_import.ExchangeData()
    # run backtesting for 200 days
    days = 200
    profile_data = scripting_library.create_index_config_from_tentacles_config(
        tentacles_config=[trading_mode_tentacles_data],
        exchange="binanceus",
        starting_funds=1000,
        backtesting_start_time_delta=days * commons_constants.DAYS_TO_SECONDS
    )

    # 2. collect candles
    ccxt_clients_cache._MARKETS_BY_EXCHANGE.clear()
    await scripting_library.init_exchange_market_status_and_populate_backtesting_exchange_data(
        exchange_data, profile_data
    )
    # cached markets have been updated and now contain this exchange markets
    assert len(ccxt_clients_cache._MARKETS_BY_EXCHANGE) == 1
    # ensure collected datas are correct
    assert len(exchange_data.markets) == 2
    assert sorted([market.symbol for market in exchange_data.markets]) == ["BTC/USDT", "ETH/USDT"]
    for market in exchange_data.markets:
        assert market.time_frame == commons_enums.TimeFrames.ONE_DAY.value
        assert days - 1 <= len(market.close) <= days
        assert days - 1 <= len(market.open) <= days
        assert days - 1 <= len(market.high) <= days
        assert days - 1 <= len(market.low) <= days
        assert days - 1 <= len(market.volume) <= days
        assert days - 1 <= len(market.time) <= days

    starting_portfolio = profile_data.backtesting_context.starting_portfolio
    assert starting_portfolio == {
        "USDT": 1000,
    }
    # 3. run backtesting
    async with scripting_library.init_and_run_backtesting(
        exchange_data, profile_data
    ) as independent_backtesting:
        # backtesting completed, make sure it executed correctly
        for exchange_id in independent_backtesting.octobot_backtesting.exchange_manager_ids:
            exchange_manager = octobot_trading.api.get_exchange_manager_from_exchange_id(exchange_id)
            ending_portfolio = octobot_trading.api.get_portfolio(exchange_manager, as_decimal=False)
            assert ending_portfolio != starting_portfolio
            assert "ETH" in ending_portfolio
            assert "BTC" in ending_portfolio
            assert "USDT" in ending_portfolio
            trades = octobot_trading.api.get_trade_history(exchange_manager)
            # at least 2 trades are expected, one for each symbol
            assert len(trades) >= 2
            # backtesting is not stopped yet
        assert independent_backtesting.stopped is False

    # 4. ensure backtesting is stopped
    assert independent_backtesting.stopped is True
