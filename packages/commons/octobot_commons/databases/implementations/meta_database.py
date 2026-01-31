# pylint: disable=R0902,C0103
#  Drakkar-Software OctoBot-Commons
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

import octobot_commons.databases.implementations.db_writer_reader as db_writer_reader
import octobot_commons.databases.implementations._exchange_database as _exchange_database
import octobot_commons.enums as enums


class MetaDatabase:
    def __init__(self, run_dbs_identifier, with_lock=False, cache_size=None):
        self.run_dbs_identifier = run_dbs_identifier
        self.with_lock = with_lock
        self.cache_size = cache_size
        self.database_adaptor = self.run_dbs_identifier.database_adaptor
        self.run_db: db_writer_reader.DBWriterReader = None
        self.backtesting_metadata_db: db_writer_reader.DBWriterReader = None
        self.exchange_dbs = {}

    def get_run_db(self):
        """
        :return: the run database. Opens it if not open already
        """
        if self.run_db is None:
            self.run_db = self.get_db(
                self.run_dbs_identifier.get_run_data_db_identifier()
            )
        return self.run_db

    def get_backtesting_metadata_db(self):
        """
        :return: the backtesting metadata database. Opens it if not open already
        """
        if self.backtesting_metadata_db is None:
            self.backtesting_metadata_db = self.get_db(
                self.run_dbs_identifier.get_backtesting_metadata_identifier()
            )
        return self.backtesting_metadata_db

    async def get_backtesting_metadata_from_run(self):
        """
        :return: the backtesting metadata for the associated run_dbs_identifier's backtesting_id
        """
        db = self.get_backtesting_metadata_db()
        return (
            await db.select(
                enums.CacheDatabaseTables.METADATA.value,
                (await db.search()).id == self.run_dbs_identifier.backtesting_id,
            )
        )[0]

    def _get_exchange_db(self, exchange=None):
        """
        :return: the ExchangeDatabase associated to the given exchange
        """
        exchange = exchange or self.run_dbs_identifier.context.exchange_name
        try:
            return self.exchange_dbs[exchange]
        except KeyError:
            self.exchange_dbs[exchange] = _exchange_database.ExchangeDatabase(
                self, exchange
            )
        return self.exchange_dbs[exchange]

    def get_orders_db(self, account_type, exchange=None):
        """
        :return: the orders database. Opens it if not open already
        """
        return self._get_exchange_db(exchange).get_orders_db(account_type)

    def get_trades_db(self, account_type, exchange=None):
        """
        :return: the trades database. Opens it if not open already
        """
        return self._get_exchange_db(exchange).get_trades_db(account_type)

    def get_transactions_db(self, account_type, exchange=None):
        """
        :return: the transactions database. Opens it if not open already
        """
        return self._get_exchange_db(exchange).get_transactions_db(account_type)

    def get_historical_portfolio_value_db(self, account_type, exchange):
        """
        :return: the historical portfolio database. Opens it if not open already
        """
        return self._get_exchange_db(exchange).get_historical_portfolio_value_db(
            account_type
        )

    def get_symbol_db(self, exchange, symbol):
        """
        :return: the symbol database. Opens it if not open already
        """
        return self._get_exchange_db(exchange).get_symbol_db(symbol)

    async def get_all_symbol_dbs(self, exchange):
        """
        :return: an iterable over each symbol database for the given exchange
        """
        return await self._get_exchange_db(exchange).get_all_symbol_dbs()

    def all_basic_run_db(self, account_type, exchange=None):
        """
        yields the run, orders, trades and transactions databases
        """
        yield self.get_run_db()
        exchange = exchange or self.run_dbs_identifier.context.exchange_name
        yield from self.exchange_dbs[exchange].all_basic_run_db(account_type)

    def get_db(self, db_identifier):
        """
        :return: the database associated to the given identifier
        """
        return db_writer_reader.DBWriterReader(
            db_identifier,
            with_lock=self.with_lock,
            cache_size=self.cache_size,
            database_adaptor=self.database_adaptor,
            enable_storage=self.run_dbs_identifier.enable_storage,
        )

    async def close(self):
        """
        Closes all the open databases
        """
        # avoid asyncio.gather here as it is producing unexplained side effects (frozen thread preventing stop)
        for coro in (
            db.close()
            for db in (
                self.run_db,
                self.backtesting_metadata_db,
            )
            if db is not None
        ):
            await coro
        for exchange_db in self.exchange_dbs.values():
            await exchange_db.close()

    @classmethod
    @contextlib.asynccontextmanager
    async def database(cls, database_manager, with_lock=False, cache_size=None):
        """
        Created a local meta database and closes it upon leaving the context manager
        """
        meta_db = None
        try:
            meta_db = MetaDatabase(
                database_manager, with_lock=with_lock, cache_size=cache_size
            )
            yield meta_db
        finally:
            if meta_db is not None:
                await meta_db.close()
