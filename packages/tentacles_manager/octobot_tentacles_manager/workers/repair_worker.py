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
import asyncio
import os.path as path

import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.workers as workers
import octobot_tentacles_manager.util as util


class RepairWorker(workers.TentaclesWorker):

    def __init__(self,
                 reference_tentacles_dir,
                 tentacle_path,
                 bot_installation_path,
                 use_confirm_prompt,
                 aiohttp_session,
                 bot_install_dir):
        super().__init__(reference_tentacles_dir,
                         tentacle_path,
                         bot_installation_path,
                         use_confirm_prompt,
                         aiohttp_session,
                         bot_install_dir=bot_install_dir)
        self.verbose = True

    async def process(self, name_filter=None) -> int:
        # force reset of all init files
        await self.tentacles_setup_manager.remove_tentacle_arch_init_files()
        # create missing files and folders
        await self.tentacles_setup_manager.create_missing_tentacles_arch()
        self.reset_worker()
        self.progress = 1
        self.available_tentacles = util.load_tentacle_with_metadata(self.tentacle_path)
        self.total_steps = len(self.available_tentacles)
        await asyncio.gather(*[self._repair_tentacle(tentacle) for tentacle in self.available_tentacles])
        self.tentacles_setup_manager.refresh_user_tentacles_setup_config_file(
            force_update_registered_tentacles=True
        )
        self.log_summary()
        return len(self.errors)

    async def _repair_tentacle(self, tentacle):
        try:
            tentacle_module_path = path.join(tentacle.tentacle_path, tentacle.name)
            await managers.create_tentacle_init_file_if_necessary(tentacle_module_path, tentacle)
            managers.update_tentacle_type_init_file(tentacle, tentacle.tentacle_path)
            if self.verbose:
                self.logger.info(f"[{self.progress}/{self.total_steps}] {tentacle} ready to use")
        except Exception as e:
            message = f"Error when repairing {tentacle.name}: {e}"
            self.errors.append(message)
            self.logger.exception(e, True, message)
        finally:
            self.progress += 1
