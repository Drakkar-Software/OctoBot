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
import os.path as path

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.workers as workers


class SingleInstallWorker(workers.InstallWorker):

    def __init__(self, reference_tentacles_dir, tentacle_path,
                 bot_installation_path, use_confirm_prompt, aiohttp_session,
                 bot_install_dir=constants.DEFAULT_BOT_INSTALL_DIR):
        super().__init__(reference_tentacles_dir, tentacle_path,
                         bot_installation_path, use_confirm_prompt, aiohttp_session, bot_install_dir=bot_install_dir)
        self.single_tentacle_path = None
        self.single_tentacle_type = None

    async def process(self, name_filter=None) -> int:
        self.reset_worker()
        if self.single_tentacle_path is None or self.single_tentacle_type is None:
            self.errors.append("Impossible to install tentacle: please provide the tentacle path and type")
        else:
            await self.tentacles_setup_manager.create_missing_tentacles_arch()
            self.progress = 1
            self.total_steps = 1
            split_path = path.split(self.single_tentacle_path)
            tentacle_name = split_path[1]
            factory = models.TentacleFactory(split_path[0])
            tentacle = factory.create_tentacle_from_type(tentacle_name, models.TentacleType(self.single_tentacle_type))
            # remove tentacle type from tentacle origin path since in this context it doesn't exist in filesystem
            tentacle.tentacle_path = split_path[0]
            await tentacle.initialize()
            self.register_to_process_tentacles_modules([tentacle])
            await self._install_tentacle(tentacle)
            self.tentacles_setup_manager.refresh_user_tentacles_setup_config_file()
            self.tentacles_setup_manager.cleanup_temp_dirs()
            if not self.quite_mode:
                self.logger.info(f"{tentacle_name} installed")
        self.log_summary()
        return len(self.errors)
