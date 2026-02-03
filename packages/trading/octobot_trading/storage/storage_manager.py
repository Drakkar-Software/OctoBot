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
#  License along with this library
import typing

import octobot_commons.display as commons_display
import octobot_commons.enums as commons_enums
import octobot_commons.databases as commons_databases
import octobot_commons.logging as commons_logging
import octobot_commons.errors as commons_errors

import octobot_trading.util as util
import octobot_trading.storage.trades_storage as trades_storage
import octobot_trading.storage.orders_storage as orders_storage
import octobot_trading.storage.transactions_storage as transactions_storage
import octobot_trading.storage.candles_storage as candles_storage
import octobot_trading.storage.portfolio_storage as portfolio_storage


class StorageManager(util.Initializable):
    def __init__(self, exchange_manager):
        super().__init__()
        self.logger: commons_logging.BotLogger = commons_logging.get_logger(self.__class__.__name__)
        self.exchange_manager = exchange_manager
        self.trades_storage: typing.Optional[trades_storage.TradesStorage] = None
        self.orders_storage: typing.Optional[orders_storage.OrdersStorage] = None
        self.transactions_storage: typing.Optional[transactions_storage.TransactionsStorage] = None
        self.portfolio_storage: typing.Optional[portfolio_storage.PortfolioStorage] = None
        self.candles_storage: typing.Optional[candles_storage.CandlesStorage] = None

    async def initialize_impl(self):
        await commons_databases.RunDatabasesProvider.instance().get_run_databases_identifier(
            self.exchange_manager.bot_id
        ).initialize(
            exchange=self.exchange_manager.exchange_name
        )
        for storage in self._storages(True):
            try:
                await storage.start()
            except Exception as e:
                self.logger.exception(e, True, f"Error when initializing {storage}: {e}")

    async def stop(self):
        for storage in self._storages(False):
            if storage:
                await storage.stop()
        self.exchange_manager = None
        self.trades_storage = self.orders_storage = self.transactions_storage = \
            self.portfolio_storage = self.candles_storage = None

    async def store_history(self):
        if self.exchange_manager is None:
            raise commons_errors.MissingExchangeDataError("This exchange storage has been stopped")
        for storage in self._historical_storages():
            await storage.store_history()

    def _historical_storages(self):
        for storage in self._storages(True):
            if storage.is_historical:
                yield storage

    def _storages(self, create_missing):
        return (
            self.trades_storage or self._trade_storage_factory() if create_missing else self.trades_storage,
            self.orders_storage or self._order_storage_factory() if create_missing else self.orders_storage,
            self.transactions_storage or self._transaction_storage_factory() if create_missing else self.transactions_storage,
            self.candles_storage or self._candles_storage_factory() if create_missing else self.candles_storage,
            self.portfolio_storage or self._portfolio_storage_factory() if create_missing else self.portfolio_storage,
        )

    def _trade_storage_factory(self):
        self.trades_storage = trades_storage.TradesStorage(
            self.exchange_manager,
            commons_display.PlotSettings(
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
                x_multiplier=1000,
                mode="markers",
                kind="scattergl",
            )
        )
        return self.trades_storage

    def _order_storage_factory(self):
        self.orders_storage = orders_storage.OrdersStorage(self.exchange_manager)
        return self.orders_storage

    def _transaction_storage_factory(self):
        self.transactions_storage = transactions_storage.TransactionsStorage(
            self.exchange_manager,
            commons_display.PlotSettings(
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
                x_multiplier=1000,
                mode="markers",
                kind="scattergl",
                y_data=None,
            )
        )
        return self.transactions_storage

    def _candles_storage_factory(self):
        self.candles_storage = candles_storage.CandlesStorage(
            self.exchange_manager,
            commons_display.PlotSettings(
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
            )
        )
        return self.candles_storage

    def _portfolio_storage_factory(self):
        self.portfolio_storage = portfolio_storage.PortfolioStorage(
            self.exchange_manager,
            commons_display.PlotSettings()
        )
        return self.portfolio_storage
