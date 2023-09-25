#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import typing
import supafunc.functions_client


class PostgresFunctions(supafunc.functions_client.FunctionsClient):
    """
    Allow to use database functions
    There should not be OctoBot specific code here
    """
    def __init__(self, supabase_url: str, headers: typing.Dict):
        postgres_func_url = f"{supabase_url}/rest/v1/rpc"
        super().__init__(postgres_func_url, headers)
