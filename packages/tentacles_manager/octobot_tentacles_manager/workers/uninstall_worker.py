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

import octobot_tentacles_manager.managers as managers
import octobot_tentacles_manager.workers as workers
import octobot_tentacles_manager.util as util


class UninstallWorker(workers.TentaclesWorker):

    async def process(self, name_filter=None) -> int:
        self.reset_worker()
        if self.confirm_action("Remove all installed tentacles ?"
                               if name_filter is None else "Remove {', '.join(name_filter)} tentacles ?"):
            to_uninstall_tentacles = None
            if name_filter is None:
                self.tentacles_setup_manager.delete_tentacles_arch(force=True, with_user_config=False,
                                                                   bot_installation_path=self.bot_installation_path)
            else:
                self.progress = 1
                self.available_tentacles = util.load_tentacle_with_metadata(self.tentacle_path)
                self.register_error_on_missing_tentacles(self.available_tentacles, name_filter)
                to_uninstall_tentacles = [tentacle
                                          for tentacle in self.available_tentacles
                                          if tentacle.name in name_filter]
                await asyncio.gather(*[self._uninstall_tentacle(tentacle) for tentacle in to_uninstall_tentacles])
            await self.tentacles_setup_manager.create_missing_tentacles_arch()
            self.tentacles_setup_manager.refresh_user_tentacles_setup_config_file(
                self.tentacles_setup_config_to_update,
                self.tentacles_path_or_url,
                True,
                uninstalled_tentacles=to_uninstall_tentacles)
            self.log_summary()
        return len(self.errors)

    async def _uninstall_tentacle(self, tentacle):
        try:
            tentacle_manager = managers.TentacleManager(tentacle)
            await tentacle_manager.uninstall_tentacle()
            managers.update_tentacle_type_init_file(tentacle, tentacle.tentacle_path, remove_import=True)
            if not self.quite_mode:
                self.logger.info(f"[{self.progress}/{self.total_steps}] uninstalled {tentacle}")
        except Exception as e:
            message = f"Error when uninstalling {tentacle.name}: {e}"
            self.errors.append(message)
            self.logger.exception(e, True, message)
        finally:
            self.progress += 1
