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
import asyncio
import contextlib
import os.path
import decimal
import mock

import octobot_backtesting.api as backtesting_api
import async_channel.util as channel_util
import octobot_commons.tests.test_config as test_config
import octobot_commons.constants as commons_constants
import octobot_commons.asyncio_tools as asyncio_tools
import octobot_trading.api as trading_api
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.exchanges as exchanges
import tentacles.Trading.Mode as modes
import tests.test_utils.config as test_utils_config
import tests.test_utils.test_exchanges as test_exchanges
import tests.test_utils.trading_modes as test_trading_modes
from tentacles.Trading.Mode.arbitrage_trading_mode.arbitrage_trading import ArbitrageModeProducer


@contextlib.asynccontextmanager
async def exchange(exchange_name, backtesting=None, symbol="BTC/USDT"):
    exchange_manager = None
    try:
        config = test_config.load_test_config()
        config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]["USDT"] = 2000
        exchange_manager = test_exchanges.get_test_exchange_manager(config, exchange_name)
        exchange_manager.tentacles_setup_config = test_utils_config.get_tentacles_setup_config()

        # use backtesting not to spam exchanges apis
        exchange_manager.is_simulated = True
        exchange_manager.is_backtesting = True
        exchange_manager.use_cached_markets = False
        backtesting = backtesting or await backtesting_api.initialize_backtesting(
            config,
            exchange_ids=[exchange_manager.id],
            matrix_id=None,
            data_files=[os.path.join(test_config.TEST_CONFIG_FOLDER,
                                     "AbstractExchangeHistoryCollector_1586017993.616272.data")])

        exchange_manager.exchange = exchanges.ExchangeSimulator(exchange_manager.config,
                                                                exchange_manager,
                                                                backtesting)
        await exchange_manager.exchange.initialize()
        for exchange_channel_class_type in [exchanges_channel.ExchangeChannel,
                                            exchanges_channel.TimeFrameExchangeChannel]:
            await channel_util.create_all_subclasses_channel(exchange_channel_class_type, exchanges_channel.set_chan,
                                                             exchange_manager=exchange_manager)

        trader = exchanges.TraderSimulator(config, exchange_manager)
        await trader.initialize()

        mode = modes.ArbitrageTradingMode(config, exchange_manager)
        mode.symbol = None if mode.get_is_symbol_wildcard() else symbol
        # avoid error with producer init and exchanges keys
        with mock.patch.object(ArbitrageModeProducer, "start", new=mock.AsyncMock()) as start_mock:
            await mode.initialize()
            # add mode to exchange manager so that it can be stopped and freed from memory
            exchange_manager.trading_modes.append(mode)

            # set BTC/USDT price at 1000 USDT
            trading_api.force_set_mark_price(exchange_manager, symbol, 1000)
            # force triggering_price_delta_ratio equivalent to a 0.2% setting in minimal_price_delta_percent
            delta_percent = 2
            test_trading_modes.set_ready_to_start(mode.producers[0])
            mode.producers[0].inf_triggering_price_delta_ratio = decimal.Decimal(str(1 - delta_percent / 100))
            mode.producers[0].sup_triggering_price_delta_ratio = decimal.Decimal(str(1 + delta_percent / 100))
            # let trading modes start
            await asyncio_tools.wait_asyncio_next_cycle()
            start_mock.assert_called_once()
        yield mode.producers[0], mode.get_trading_mode_consumers()[0], exchange_manager
    finally:
        if exchange_manager is not None:
            for importer in backtesting_api.get_importers(exchange_manager.exchange.backtesting):
                await backtesting_api.stop_importer(importer)
            if exchange_manager.exchange.backtesting.time_updater is not None:
                await exchange_manager.exchange.backtesting.stop()
            await exchange_manager.stop()
