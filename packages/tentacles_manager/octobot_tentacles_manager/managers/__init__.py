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

from octobot_tentacles_manager.managers import tentacle_manager
from octobot_tentacles_manager.managers import tentacles_setup_manager
from octobot_tentacles_manager.managers import tentacles_init_files_manager
from octobot_tentacles_manager.managers import python_modules_requirements_manager
from octobot_tentacles_manager.managers import profiles_manager

from octobot_tentacles_manager.managers.tentacle_manager import (
    TentacleManager,
)
from octobot_tentacles_manager.managers.tentacles_setup_manager import (
    TentaclesSetupManager,
)
from octobot_tentacles_manager.managers.tentacles_init_files_manager import (
    update_tentacle_type_init_file,
    get_module_init_file_content,
    get_tentacle_import_block,
    find_or_create_module_init_file,
    create_tentacle_init_file_if_necessary,
)
from octobot_tentacles_manager.managers.python_modules_requirements_manager import (
    install_tentacle,
    update_tentacle,
    list_installed_tentacles,
)
from octobot_tentacles_manager.managers.profiles_manager import (
    get_profile_folders,
    import_profile,
)

__all__ = [
    "TentacleManager",
    "TentaclesSetupManager",
    "update_tentacle_type_init_file",
    "get_module_init_file_content",
    "get_tentacle_import_block",
    "find_or_create_module_init_file",
    "create_tentacle_init_file_if_necessary",
    "install_tentacle",
    "update_tentacle",
    "list_installed_tentacles",
    "get_profile_folders",
    "import_profile",
]
