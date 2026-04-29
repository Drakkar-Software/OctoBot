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

from octobot_tentacles_manager.workers import tentacles_worker
from octobot_tentacles_manager.workers.tentacles_worker import (
    TentaclesWorker,
)

from octobot_tentacles_manager.workers import install_worker
from octobot_tentacles_manager.workers.install_worker import (
    InstallWorker,
)

from octobot_tentacles_manager.workers import uninstall_worker
from octobot_tentacles_manager.workers import repair_worker
from octobot_tentacles_manager.workers import update_worker
from octobot_tentacles_manager.workers import single_install_worker

from octobot_tentacles_manager.workers.uninstall_worker import (
    UninstallWorker,
)
from octobot_tentacles_manager.workers.repair_worker import (
    RepairWorker,
)
from octobot_tentacles_manager.workers.update_worker import (
    UpdateWorker,
)
from octobot_tentacles_manager.workers.single_install_worker import (
    SingleInstallWorker,
)

__all__ = [
    "UninstallWorker",
    "RepairWorker",
    "TentaclesWorker",
    "UpdateWorker",
    "InstallWorker",
    "SingleInstallWorker",
]
