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
import octobot_commons.databases.bases.base_database as base_database


class DBReader(base_database.BaseDatabase):
    async def select(self, table_name: str, query: str) -> list:
        """
        :param table_name: table to select data from
        :param query: select query
        :return: list of selected results
        """
        return await self._database.select(table_name, query)

    async def tables(self) -> list:
        """
        :return: list of tables contained in the database
        """
        return await self._database.tables()

    async def all(self, table_name: str) -> list:
        """
        :param table_name: table to select data from
        :return: all data of the selected table
        """
        return await self._database.select(table_name, None)
