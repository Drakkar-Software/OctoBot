# pylint: disable=R0902,R0913,C0415,R0904
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
import shutil

import octobot_commons.databases.document_database_adaptors as adaptors
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.symbols.symbol_util as symbol_util


class RunDatabasesIdentifier:
    def __init__(
        self,
        tentacle_class,
        optimization_campaign_name=None,
        database_adaptor=adaptors.TinyDBAdaptor,
        backtesting_id=None,
        live_id=None,
        optimizer_id=None,
        context=None,
        enable_storage=True,
    ):
        self.database_adaptor = database_adaptor
        self.optimization_campaign_name = optimization_campaign_name
        self.backtesting_id = backtesting_id
        self.live_id = live_id
        self.optimizer_id = optimizer_id
        self.tentacle_class = (
            tentacle_class
            if isinstance(tentacle_class, str)
            else tentacle_class.__name__
        )
        self.enable_storage = enable_storage
        self.context = context
        self.data_path = self._merge_parts(constants.USER_FOLDER, constants.DATA_FOLDER)
        self.base_path = self._merge_parts(self.data_path, self.tentacle_class)
        self.suffix = (
            self.database_adaptor.get_db_file_ext()
            if self.database_adaptor.is_file_system_based()
            else ""
        )

    async def initialize(self, exchange=None):
        """
        Initializes the necessary elements for these run databases. Creates necessary folder on file system databases
        :param exchange: name of the associated exchange
        Used for live trading cross trading mode stats (such as profitability)
        """
        if not self.enable_storage:
            return
        # global history is a live only feature
        from_global_history = self.backtesting_id is None
        deepest_identifier = (
            self._base_folder(from_global_history=from_global_history)
            if exchange is None
            else self._merge_parts(
                self._base_folder(from_global_history=from_global_history), exchange
            )
        )
        await self.database_adaptor.create_identifier(deepest_identifier)

    def is_backtesting(self) -> bool:
        """
        :return: True when the database identifier associated to a backtesting run
        """
        return self.backtesting_id is not None

    def get_run_data_db_identifier(self) -> str:
        """
        :return: the database identifier associated to the run database
        """
        return self._get_db_identifier(enums.RunDatabases.RUN_DATA_DB.value, None)

    def get_orders_db_identifier(self, account_type, exchange) -> str:
        """
        :return: the database identifier associated to this exchange's orders
        :param account_type: type of account
        :param exchange: name of the associated exchange
        """
        return self._get_db_identifier(
            f"{enums.RunDatabases.ORDERS_DB.value}{account_type}", exchange
        )

    def get_trades_db_identifier(self, account_type, exchange) -> str:
        """
        :return: the database identifier associated to this exchange's trades
        :param account_type: type of account
        :param exchange: name of the associated exchange
        """
        return self._get_db_identifier(
            f"{enums.RunDatabases.TRADES_DB.value}{account_type}", exchange
        )

    def get_transactions_db_identifier(self, account_type, exchange) -> str:
        """
        :return: the database identifier associated to this exchange's transactions
        :param account_type: type of account
        :param exchange: name of the associated exchange
        """
        return self._get_db_identifier(
            f"{enums.RunDatabases.TRANSACTIONS_DB.value}{account_type}", exchange
        )

    def get_symbol_db_identifier(self, exchange, symbol) -> str:
        """
        :return: the database identifier associated to this exchange's symbol data
        :param exchange: name of the associated exchange
        :param symbol: the associated symbol
        """
        return self._get_db_identifier(symbol_util.merge_symbol(symbol), exchange)

    def get_historical_portfolio_value_db_identifier(
        self, account_type, exchange
    ) -> str:
        """
        :return: the database identifier associated to this exchange's historical portfolio value
        :param account_type: a suffix identifying the type of portfolio (future / sandbox etc)
        :param exchange: name of the associated exchange
        """
        return self._get_db_identifier(
            f"{enums.RunDatabases.PORTFOLIO_VALUE_DB.value}{account_type}",
            exchange,
        )

    def get_backtesting_metadata_identifier(self) -> str:
        """
        :return: the database identifier associated to backtesting metadata
        """
        return self._get_db_identifier(
            enums.RunDatabases.METADATA.value, None, ignore_backtesting_id=True
        )

    def get_bot_live_metadata_identifier(self) -> str:
        """
        :return: the database identifier associated to live metadata
        """
        return self._get_db_identifier(
            enums.RunDatabases.METADATA.value, None, ignore_live_id=True
        )

    def _get_db_identifier(self, run_database_name, exchange, **base_folder_kwargs):
        if exchange is None:
            return self._merge_parts(
                self._base_folder(**base_folder_kwargs),
                self.get_db_full_name(run_database_name),
            )
        return self._merge_parts(
            self._base_folder(**base_folder_kwargs),
            exchange,
            self.get_db_full_name(run_database_name),
        )

    def get_db_full_name(self, db_name):
        """
        :return: the db_name's associated database name including suffix
        """
        return f"{db_name}{self.suffix}"

    async def exchange_base_identifier_exists(self, exchange) -> bool:
        """
        :return: True if there are data under this exchange name
        """
        return await self.database_adaptor.identifier_exists(
            self.get_exchange_based_identifier(exchange), False
        )

    def get_exchange_based_identifier(self, exchange):
        """
        :return: the database identifier associated to the given exchange
        """
        return self._merge_parts(self._base_folder(), exchange)

    async def get_single_existing_exchange(self) -> str:
        """
        :return: the name of the only exchange the backtesting happened on if it only ran on a single exchange,
        None otherwise
        """
        ignored_folders = [enums.RunDatabases.LIVE.value]
        try:
            import octobot_tentacles_manager.constants as tentacles_manager_constants

            ignored_folders.append(
                tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER
            )
        except ImportError:
            pass
        return await self.database_adaptor.get_single_sub_identifier(
            self._base_folder(), ignored_folders
        )

    async def symbol_base_identifier_exists(self, exchange, symbol) -> bool:
        """
        :return: True if there are data under this exchange name
        """
        identifier = self._merge_parts(
            self._base_folder(),
            exchange,
            self.get_db_full_name(symbol_util.merge_symbol(symbol)),
        )
        return await self.database_adaptor.identifier_exists(identifier, True)

    def get_backtesting_run_folder(self) -> str:
        """
        :return: base folder associated to a backtesting run
        """
        return self._base_folder()

    def get_optimizer_runs_schedule_identifier(self) -> str:
        """
        :return: the identifier associated to the optimizer run schedule database
        """
        return self._merge_parts(
            self.base_path,
            self.optimization_campaign_name,
            enums.RunDatabases.OPTIMIZER.value,
            self.get_db_full_name(enums.RunDatabases.OPTIMIZER_RUNS_SCHEDULE_DB.value),
        )

    async def generate_new_backtesting_id(self) -> int:
        """
        :return: a new unique backtesting id
        """
        return await self._generate_new_id(is_optimizer=False)

    async def generate_new_bot_live_id(self) -> int:
        """
        :return: a new unique bot recording id
        """
        return await self._generate_new_id(is_optimizer=False, is_bot_recording=True)

    async def generate_new_optimizer_id(self, back_list) -> int:
        """
        :return: a new unique optimizer id
        """
        return await self._generate_new_id(back_list=back_list, is_optimizer=True)

    def is_symbol_database(self, database_identifier: str) -> bool:
        """
        :return: True if the given identifier is related to a symbol database
        """
        return database_identifier.endswith(self.suffix) and all(
            not other_identifier.value in database_identifier
            for other_identifier in enums.RunDatabases
        )

    def get_symbol_db_name(self, symbol_db_identifier):
        """
        :return: the given identifier's database name (without suffix if any)
        """
        return symbol_db_identifier.split(self.suffix)[0]

    def remove_all(self):
        """
        Clears every data from a backtesting run
        """
        identifier = self._base_folder()
        if self.database_adaptor.is_file_system_based():
            if os.path.isdir(identifier):
                shutil.rmtree(identifier)
            return
        raise RuntimeError(f"Unhandled database_adaptor {self.database_adaptor}")

    async def _generate_new_id(
        self, back_list=None, is_optimizer=False, is_bot_recording=False
    ):
        back_list = back_list or []
        max_runs = (
            constants.MAX_OPTIMIZER_RUNS
            if is_optimizer
            else constants.MAX_BACKTESTING_RUNS
        )
        for index in range(1, max_runs + 1):
            if index in back_list:
                continue
            name_candidate = (
                self._base_folder(optimizer_id=index)
                if is_optimizer
                else (
                    self._base_folder(live_id=index)
                    if is_bot_recording
                    else self._base_folder(backtesting_id=index)
                )
            )
            if not await self.database_adaptor.identifier_exists(name_candidate, False):
                return index
        raise RuntimeError(
            f"Reached maximum number of {'optimizer' if is_optimizer else 'backtesting'} runs "
            f"({constants.MAX_BACKTESTING_RUNS}). Please remove some."
        )

    async def get_optimization_campaign_names(self) -> list:
        """
        :return: a list of every existing campaign name
        """
        optimization_campaign_folder = self._merge_parts(self.base_path)
        if await self.database_adaptor.identifier_exists(
            optimization_campaign_folder, False
        ):
            return [
                element
                async for element in self.database_adaptor.get_sub_identifiers(
                    optimization_campaign_folder, [enums.RunDatabases.LIVE.value]
                )
            ]
        return []

    async def get_optimizer_run_ids(self) -> list:
        """
        :return: a list of every optimizer id in the current campaign
        """
        optimizer_runs_path = self._merge_parts(
            self.base_path,
            self.optimization_campaign_name,
            enums.RunDatabases.OPTIMIZER.value,
        )
        if await self.database_adaptor.identifier_exists(optimizer_runs_path, False):
            return [
                self.parse_optimizer_id(element)
                async for element in self.database_adaptor.get_sub_identifiers(
                    optimizer_runs_path, []
                )
            ]

    async def get_backtesting_run_ids(self) -> list:
        """
        :return: a list of every backtesting id in the current campaign
        """
        runs_path = self._base_folder(ignore_backtesting_id=True)
        if await self.database_adaptor.identifier_exists(runs_path, False):
            return [
                self.parse_backtesting_id(element)
                async for element in self.database_adaptor.get_sub_identifiers(
                    runs_path, []
                )
            ]

    @staticmethod
    def parse_optimizer_id(identifier) -> str:
        """
        :return: the associated optimizer id
        """
        return identifier.split(constants.DB_SEPARATOR)[-1]

    @staticmethod
    def parse_backtesting_id(identifier) -> str:
        """
        :return: the associated backtesting id
        """
        return identifier.split(constants.DB_SEPARATOR)[-1]

    def _get_base_path(self, from_global_history, backtesting_id, optimizer_id):
        if from_global_history and (backtesting_id is None and optimizer_id is None):
            # in live global history, use self.data_path as it's not related to a trading mode
            return self.data_path
        return self.base_path

    def _base_folder(
        self,
        ignore_backtesting_id=False,
        backtesting_id=None,
        live_id=None,
        ignore_live_id=None,
        ignore_optimizer_id=False,
        optimizer_id=None,
        from_global_history=True,
    ) -> str:
        backtesting_id = backtesting_id or self.backtesting_id
        optimizer_id = optimizer_id or self.optimizer_id
        path = self._get_base_path(from_global_history, backtesting_id, optimizer_id)
        live_id = live_id or self.live_id
        # when in optimizer or backtesting: wrap it into the current campaign
        if backtesting_id is not None or optimizer_id is not None:
            if self.optimization_campaign_name is None:
                raise RuntimeError(
                    f"optimization_campaign_name is required in {RunDatabasesIdentifier} "
                    f"constructor while in a backtesting or optimizer context"
                )
            path = self._merge_parts(path, self.optimization_campaign_name)
        if optimizer_id is not None:
            if ignore_optimizer_id:
                path = self._merge_parts(path, enums.RunDatabases.OPTIMIZER.value)
            else:
                path = self._merge_parts(
                    path,
                    enums.RunDatabases.OPTIMIZER.value,
                    f"{enums.RunDatabases.OPTIMIZER.value}{constants.DB_SEPARATOR}{optimizer_id}",
                )
        if backtesting_id is not None:
            if optimizer_id is None:
                path = self._merge_parts(path, enums.RunDatabases.BACKTESTING.value)
            if ignore_backtesting_id:
                return path
            return self._merge_parts(
                path,
                f"{enums.RunDatabases.BACKTESTING.value}"
                f"{constants.DB_SEPARATOR}{backtesting_id}",
            )
        if optimizer_id is None:
            # live mode
            if ignore_live_id:
                return self._merge_parts(path, enums.RunDatabases.LIVE.value)
            return self._merge_parts(
                path,
                f"{os.path.join(enums.RunDatabases.LIVE.value, enums.RunDatabases.LIVE.value)}"
                f"{constants.DB_SEPARATOR}{live_id}",
            )
        return path

    def _merge_parts(self, *parts):
        return (
            os.path.join(*parts)
            if self.database_adaptor.is_file_system_based()
            else constants.DB_SEPARATOR.join(*parts)
        )
