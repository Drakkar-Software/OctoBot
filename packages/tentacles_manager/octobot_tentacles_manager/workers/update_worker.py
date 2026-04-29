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
import distutils.version as loose_version
import packaging.version as packaging_version

import octobot_tentacles_manager.workers as workers
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.util as util


class UpdateWorker(workers.InstallWorker):

    def __init__(self, reference_tentacles_dir, tentacle_path,
                 bot_installation_path, use_confirm_prompt, aiohttp_session, quite_mode=False):
        super().__init__(reference_tentacles_dir, tentacle_path,
                         bot_installation_path, use_confirm_prompt, aiohttp_session,
                         quite_mode=quite_mode)

    async def process(self, name_filter=None) -> int:
        self.available_tentacles = util.load_tentacle_with_metadata(self.tentacle_path)
        return await super().process(name_filter)

    def _should_tentacle_be_processed(self, tentacle, name_filter):
        name = tentacle.name
        if name_filter is None or name in name_filter:
            installed_tentacle = models.Tentacle.find(self.available_tentacles, name)
            if installed_tentacle is not None:
                installed_version = installed_tentacle.version
                return packaging_version.Version(installed_version) < packaging_version.Version(tentacle.version)
        return False
