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
import octobot_trading.constants as constants
import octobot_trading.exchanges as exchanges
import octobot_trading.exchange_data.prices.channel.prices_updater as prices_updater
import octobot_trading.exchange_channel as exchanges_channel


class MarkPriceUpdaterSimulator(prices_updater.MarkPriceUpdater):
    def __init__(self, channel, importer):
        super().__init__(channel)
        self.exchange_data_importer = importer

    async def start(self):
        exchange = self.channel.exchange_manager.exchange
        available_data = exchanges.ExchangeSimulatorConnector.get_real_available_data(exchange.exchange_importers)
        real_data_for_recent_trades = exchanges.ExchangeSimulatorConnector.handles_real_data_for_updater(
            constants.RECENT_TRADES_CHANNEL, available_data
        )
        real_data_for_ticker = exchanges.ExchangeSimulatorConnector.handles_real_data_for_updater(
            constants.TICKER_CHANNEL, available_data
        )
        # if recent trades and ticker channels are both generated from ohlcv, do not watch them both,
        # prefer ticker
        if real_data_for_ticker or not (real_data_for_recent_trades or real_data_for_ticker):
            await exchanges_channel.get_chan(constants.TICKER_CHANNEL,
                                             self.channel.exchange_manager.id).new_consumer(self.handle_ticker_update)
        if real_data_for_recent_trades:
            await exchanges_channel.get_chan(constants.RECENT_TRADES_CHANNEL, self.channel.exchange_manager.id) \
                .new_consumer(self.handle_recent_trades_update)
