#  Drakkar-Software OctoBot-Tentacles-Manager
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
import octobot_tentacles_manager.api as util
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.workers as workers

USER_HELP = """Update the given tentacle modules and install missing requirements if any.
Does not update already filled requirements regardless of their version to avoid conflicts.
Prefer a full tentacles update if a requirement version is creating conflicts.
    Does not edit tentacles configuration files."""


async def update_all_tentacles(tentacles_path_or_url, tentacle_path=constants.TENTACLES_PATH,
                               bot_path=constants.DEFAULT_BOT_PATH, aiohttp_session=None,
                               quite_mode=False, authenticator=None) -> int:
    return await _update_tentacles(None, tentacles_path_or_url, tentacle_path,
                                   bot_path, aiohttp_session=aiohttp_session, quite_mode=quite_mode,
                                   authenticator=authenticator)


async def update_tentacles(tentacle_names, tentacles_path_or_url, tentacle_path=constants.TENTACLES_PATH,
                           bot_path=constants.DEFAULT_BOT_PATH, aiohttp_session=None, quite_mode=False,
                           authenticator=None) -> int:
    return await _update_tentacles(tentacle_names, tentacles_path_or_url,
                                   tentacle_path, bot_path, aiohttp_session=aiohttp_session, quite_mode=quite_mode,
                                   authenticator=authenticator)


async def _update_tentacles(tentacle_names, tentacles_path_or_url, tentacle_path=constants.TENTACLES_PATH,
                            bot_path=constants.DEFAULT_BOT_PATH, use_confirm_prompt=False, aiohttp_session=None,
                            quite_mode=False, authenticator=None) -> int:
    update_worker = workers.UpdateWorker(constants.TENTACLES_INSTALL_TEMP_DIR, tentacle_path, bot_path,
                                         use_confirm_prompt, aiohttp_session, quite_mode=quite_mode)
    return await util.manage_tentacles(update_worker, tentacle_names, tentacles_path_or_url,
                                       aiohttp_session, authenticator)
