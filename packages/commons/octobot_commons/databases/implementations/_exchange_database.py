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
import os

import octobot_commons.databases.implementations.db_writer_reader as db_writer_reader


class ExchangeDatabase:
    def __init__(self, meta_database, exchange):
        self.meta_database = meta_database
        self.run_dbs_identifier = self.meta_database.run_dbs_identifier
        self.exchange = exchange
        self.orders_db: db_writer_reader.DBWriterReader = None
        self.trades_db: db_writer_reader.DBWriterReader = None
        self.transactions_db: db_writer_reader.DBWriterReader = None
        self.historical_portfolio_value_db: db_writer_reader.DBWriterReader = None
        self.symbol_dbs: dict = {}

    def get_orders_db(self, account_type):
        """
        :return: the orders database. Opens it if not open already
        """
        if self.orders_db is None:
            self.orders_db = self.meta_database.get_db(
                self.run_dbs_identifier.get_orders_db_identifier(
                    account_type,
                    self.exchange,
                )
            )
        return self.orders_db

    def get_trades_db(self, account_type):
        """
        :return: the trades database. Opens it if not open already
        """
        if self.trades_db is None:
            self.trades_db = self.meta_database.get_db(
                self.run_dbs_identifier.get_trades_db_identifier(
                    account_type,
                    self.exchange,
                )
            )
        return self.trades_db

    def get_transactions_db(self, account_type):
        """
        :return: the transactions database. Opens it if not open already
        """
        if self.transactions_db is None:
            self.transactions_db = self.meta_database.get_db(
                self.run_dbs_identifier.get_transactions_db_identifier(
                    account_type,
                    self.exchange,
                )
            )
        return self.transactions_db

    def get_historical_portfolio_value_db(self, account_type):
        """
        :return: the historical portfolio database. Opens it if not open already
        """
        if self.historical_portfolio_value_db is None:
            self.historical_portfolio_value_db = self.meta_database.get_db(
                self.run_dbs_identifier.get_historical_portfolio_value_db_identifier(
                    account_type, self.exchange
                )
            )
        return self.historical_portfolio_value_db

    def get_symbol_db(self, symbol):
        """
        :return: the symbol database. Opens it if not open already
        """
        key = self._get_symbol_db_key(self.exchange, symbol)
        if key not in self.symbol_dbs:
            self.symbol_dbs[key] = self.meta_database.get_db(
                self.run_dbs_identifier.get_symbol_db_identifier(self.exchange, symbol)
            )
        return self.symbol_dbs[key]

    async def get_all_symbol_dbs(self):
        """
        :return: an iterable over each symbol database for the given exchange
        """
        if self.run_dbs_identifier.database_adaptor.is_file_system_based():
            return [
                self.get_symbol_db(self.run_dbs_identifier.get_symbol_db_name(db.name))
                for db in os.scandir(
                    self.run_dbs_identifier.get_exchange_based_identifier(self.exchange)
                )
                if self.run_dbs_identifier.is_symbol_database(db.name)
            ]
        raise NotImplementedError(
            "get_all_symbol_dbs is not implemented for non is_file_system_based databases"
        )

    def all_basic_run_db(self, account_type):
        """
        yields the run, orders, trades and transactions databases
        """
        yield self.get_orders_db(account_type)
        yield self.get_trades_db(account_type)
        yield self.get_transactions_db(account_type)

    @staticmethod
    def _get_symbol_db_key(exchange, symbol):
        return f"{exchange}{symbol}"

    async def close(self):
        """
        Closes all the open databases
        """
        # avoid asyncio.gather here as it is producing unexplained side effects (frozen thread preventing stop)
        for coro in (
            db.close()
            for db in (
                self.orders_db,
                self.trades_db,
                self.transactions_db,
                self.historical_portfolio_value_db,
                *self.symbol_dbs.values(),
            )
            if db is not None
        ):
            await coro
