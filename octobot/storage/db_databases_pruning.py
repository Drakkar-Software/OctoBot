#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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
import octobot_commons.databases as databases
import octobot.constants as constants


async def enforce_total_databases_max_size():
    run_databases_identifier = databases.RunDatabasesProvider.instance().get_any_run_databases_identifier()
    pruner = databases.run_databases_pruner_factory(
        run_databases_identifier,
        constants.MAX_TOTAL_RUN_DATABASES_SIZE,
    )
    await pruner.explore()
    await pruner.prune_oldest_run_databases()
