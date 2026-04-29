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
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.api as util
import octobot_tentacles_manager.workers as workers


USER_HELP = """Uninstall the given tentacle modules.
    Does not delete the associated tentacle configuration."""


async def uninstall_all_tentacles(tentacle_path=constants.TENTACLES_PATH,
                                  bot_path=constants.DEFAULT_BOT_PATH,
                                  use_confirm_prompt=False,
                                  quite_mode=False,
                                  setup_config=None) -> int:
    return await _uninstall_tentacles(None, tentacle_path,
                                      bot_path,
                                      use_confirm_prompt,
                                      quite_mode=quite_mode,
                                      tentacles_setup_config_to_update=setup_config)


async def uninstall_tentacles(tentacle_names,
                              tentacle_path=constants.TENTACLES_PATH,
                              bot_path=constants.DEFAULT_BOT_PATH,
                              use_confirm_prompt=False,
                              quite_mode=False) -> int:
    return await _uninstall_tentacles(tentacle_names,
                                      tentacle_path,
                                      bot_path,
                                      use_confirm_prompt,
                                      quite_mode=quite_mode)


async def _uninstall_tentacles(tentacle_names,
                               tentacle_path=constants.TENTACLES_PATH,
                               bot_path=constants.DEFAULT_BOT_PATH,
                               use_confirm_prompt=False,
                               quite_mode=False,
                               tentacles_setup_config_to_update=None) -> int:
    uninstall_worker = workers.UninstallWorker(None, tentacle_path, bot_path, use_confirm_prompt,
                                               None, quite_mode=quite_mode)
    uninstall_worker.tentacles_setup_config_to_update = tentacles_setup_config_to_update
    return await util.manage_tentacles(uninstall_worker, tentacle_names)
