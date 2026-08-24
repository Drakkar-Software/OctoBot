# pylint: disable=C0116,W0511,R0913
#  Drakkar-Software OctoBot-Backtesting
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
import sqlite3

import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.databases.relational_databases.sqlite.base_sqlite_database as base_sqlite_database


class BacktestingDataSQLiteDatabase(base_sqlite_database.BaseSQLiteDatabase):
    TIMESTAMP_COLUMN = "timestamp"
    DEFAULT_ORDER_BY = TIMESTAMP_COLUMN
    DEFAULT_SORT = enums.DataBaseOrderBy.DESC.value
    DEFAULT_WHERE_OPERATION = "="
    DEFAULT_SIZE = -1
    CACHE_SIZE = 50

    def __init__(self, file_name):
        super().__init__(file_name)
        self.tables = []
        self.cache = {}

    async def initialize(self):
        await super().initialize()
        await self.__init_tables_list()

    async def create_index(self, table, columns):
        await self.__execute_index_creation(
            table, "_".join(columns), ", ".join(columns)
        )

    async def __execute_index_creation(self, table, name, columns):
        async with self.aio_cursor() as cursor:
            await cursor.execute(
                f"CREATE INDEX index_{table.value}_{name} ON {table.value} ({columns})"
            )

    async def insert(self, table, timestamp, **kwargs):
        if table.value not in self.tables:
            await self.__create_table(table, **kwargs)

        inserting_values = [f"'{value}'" for value in kwargs.values()]
        await self.__execute_insert(
            table, self.__insert_values(timestamp, ", ".join(inserting_values))
        )

    async def insert_all(self, table, timestamp, **kwargs):
        # TODO refactor with : cursor.executemany("INSERT INTO my_table VALUES (?,?)", values)
        if table.value not in self.tables:
            await self.__create_table(table, **kwargs)

        insert_values = []

        for index, values in enumerate(timestamp):
            inserting_values = [
                f"'{value if not isinstance(value, list) else value[index]}'"
                for value in kwargs.values()
            ]
            insert_values.append(
                self.__insert_values(values, ", ".join(inserting_values))
            )

        await self.__execute_insert(table, ", ".join(insert_values))

    async def update(self, table, updated_value_by_column, **kwargs):
        updating_values = [
            f"{key} = '{value}'" for key, value in updated_value_by_column.items()
        ]
        await self.__execute_update(
            table,
            ", ".join(updating_values),
            self.__where_clauses_from_kwargs(**kwargs),
        )

    def __insert_values(self, timestamp, inserting_values) -> str:
        return f"({timestamp}, {inserting_values})"

    async def __execute_insert(self, table, insert_items) -> None:
        async with self.aio_cursor() as cursor:
            await cursor.execute(f"INSERT INTO {table.value} VALUES {insert_items}")

        await self.connection.commit()

    async def __execute_update(self, table, update_items, where_clauses) -> None:
        async with self.aio_cursor() as cursor:
            await cursor.execute(
                f"UPDATE {table.value} SET {update_items} WHERE {where_clauses}"
            )

        await self.connection.commit()

    async def select(
        self,
        table,
        size=DEFAULT_SIZE,
        order_by=DEFAULT_ORDER_BY,
        sort=DEFAULT_SORT,
        **kwargs,
    ):
        return await self.__execute_select(
            table=table,
            where_clauses=self.__where_clauses_from_kwargs(**kwargs),
            additional_clauses=self.__select_order_by(order_by, sort),
            size=size,
        )

    async def select_count(self, table, selected_items=None, **kwargs):
        return await self.__execute_select(
            table=table,
            select_items=f"{self.__count(selected_items)}",
            where_clauses=self.__where_clauses_from_kwargs(**kwargs),
        )

    async def select_max(
        self, table, max_columns, selected_items=None, group_by=None, **kwargs
    ):
        return await self.__execute_select(
            table=table,
            select_items=f"{self.__max(max_columns)}"
            f"{', ' if selected_items else ''}"
            f"{self.__selected_columns(selected_items)}",
            where_clauses=self.__where_clauses_from_kwargs(**kwargs),
            group_by=self.__select_group_by(group_by) if group_by else "",
        )

    async def select_min(
        self, table, min_columns, selected_items=None, group_by=None, **kwargs
    ):
        return await self.__execute_select(
            table=table,
            select_items=f"{self.__min(min_columns)}"
            f"{', ' if selected_items else ''}"
            f"{self.__selected_columns(selected_items)}",
            where_clauses=self.__where_clauses_from_kwargs(**kwargs),
            group_by=self.__select_group_by(group_by) if group_by else "",
        )

    async def select_from_timestamp(
        self,
        table,
        timestamps: list,
        operations: list,
        size=DEFAULT_SIZE,
        order_by=DEFAULT_ORDER_BY,
        sort=DEFAULT_SORT,
        **kwargs,
    ):
        timestamps_where_clauses = self.__where_clauses_from_operations(
            keys=[self.TIMESTAMP_COLUMN] * len(timestamps),
            values=timestamps,
            operations=operations,
            should_quote_value=False,
        )
        where_clause = self.__where_clauses_from_kwargs(**kwargs)
        final_where_close = (
            f"{where_clause} AND "
            if where_clause and timestamps_where_clauses
            else where_clause
        )
        final_where_close = f"{final_where_close}{timestamps_where_clauses}"
        return await self.__execute_select(
            table=table,
            where_clauses=final_where_close,
            additional_clauses=self.__select_order_by(order_by, sort),
            size=size,
        )

    async def delete(self, table, **kwargs):
        return await self.__execute_delete(
            table,
            self.__where_clauses_from_kwargs(**kwargs),
        )

    def __where_clauses_from_kwargs(self, should_quote_value=True, **kwargs) -> str:
        return self.__where_clauses_from_operations(
            list(kwargs.keys()),
            list(kwargs.values()),
            [],
            should_quote_value=should_quote_value,
        )

    def __where_clauses_from_operation(
        self, key, value, operation=DEFAULT_WHERE_OPERATION, should_quote_value=True
    ):
        return (
            f"{key} {operation if operation is not None else self.DEFAULT_WHERE_OPERATION} "
            f"{self.__quote_value(value) if should_quote_value else value}"
        )

    def __where_clauses_from_operations(
        self, keys, values, operations, should_quote_value=True
    ):
        return " AND ".join(
            [
                self.__where_clauses_from_operation(
                    keys[index],
                    values[index],
                    operations[index] if len(operations) > index else None,
                    should_quote_value=should_quote_value,
                )
                for index in range(len(keys))
                if values[index] is not None
            ]
        )

    def __select_order_by(self, order_by, sort):
        return (
            f"ORDER BY "
            f"{order_by if order_by is not None else self.DEFAULT_ORDER_BY} "
            f"{sort if sort is not None else self.DEFAULT_SORT}"
        )

    def __select_group_by(self, group_by):
        return f"GROUP BY {group_by}"

    def __quote_value(self, value):
        return f"'{value}'"

    def __max(self, columns):
        return f"MAX({self.__selected_columns(columns)})"

    def __min(self, columns):
        return f"MIN({self.__selected_columns(columns)})"

    def __count(self, columns):
        return f"COUNT({self.__selected_columns(columns)})"

    def __selected_columns(self, columns=None):
        return ",".join(columns) if columns else ""

    async def __execute_select(
        self,
        table,
        select_items="*",
        where_clauses="",
        additional_clauses="",
        group_by="",
        size=DEFAULT_SIZE,
    ):
        try:
            async with self.aio_cursor() as cursor:
                limit_clause = "" if size == self.DEFAULT_SIZE else f"LIMIT {size}"
                await cursor.execute(
                    f"SELECT {select_items} FROM {table.value} "
                    f"{'WHERE' if where_clauses else ''} {where_clauses} "
                    f"{additional_clauses} {limit_clause} {group_by}"
                )
                return await cursor.fetchall()
        except sqlite3.OperationalError as err:
            if not await self.check_table_exists(table):
                raise errors.DatabaseNotFoundError(err)
            self.logger.error(f"An error occurred when executing select : {err}")
        return []

    async def __execute_delete(self, table, where_clauses):
        async with self.aio_cursor() as cursor:
            await cursor.execute(f"DELETE FROM {table.value} WHERE {where_clauses} ")

    async def check_table_exists(self, table) -> bool:
        async with self.aio_cursor() as cursor:
            await cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table.value}'"
            )
            return await cursor.fetchall() != []

    async def check_table_not_empty(self, table) -> bool:
        async with self.aio_cursor() as cursor:
            await cursor.execute(f"SELECT count(*) FROM '{table.value}'")
            row_count = await cursor.fetchone()
            return row_count[0] != 0

    async def __create_table(
        self, table, with_index_on_timestamp=True, **kwargs
    ) -> None:
        try:
            columns: list = list(kwargs.keys())
            async with self.aio_cursor() as cursor:
                await cursor.execute(
                    f"CREATE TABLE {table.value} ({self.TIMESTAMP_COLUMN} datetime, "
                    f"{' text, '.join(col for col in columns)})"
                )

            if with_index_on_timestamp:
                await self.create_index(table, [self.TIMESTAMP_COLUMN])

                for index in range(1, round(len(columns) / 2) + 1):
                    await self.create_index(
                        table,
                        [self.TIMESTAMP_COLUMN] + [columns[column_index] for column_index in range(0, index)],
                    )

        except sqlite3.OperationalError:
            self.logger.error(f"{table} already exists")
        finally:
            self.tables.append(table.value)

    async def __init_tables_list(self):
        async with self.aio_cursor() as cursor:
            await cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            self.tables = [res[0] for res in await cursor.fetchall()]


@contextlib.asynccontextmanager
async def new_sqlite_database(file_path):
    local_database = BacktestingDataSQLiteDatabase(file_path)
    try:
        await local_database.initialize()
        yield local_database
    finally:
        await local_database.stop()
