#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

from pathlib import Path


def get_dist_directory() -> Path | None:
    """
    Get the path to the dist directory containing the built frontend assets.
    
    The dist directory is always located at octobot_node/ui/dist,
    both in development and when installed as a package.
    
    Returns:
        Path to dist directory if found, None otherwise.
    """
    # Locate octobot_node.ui module directory
    try:
        import octobot_node.ui
        ui_module_path = Path(octobot_node.ui.__file__).resolve().parent
        dist_path = ui_module_path / "dist"
        if dist_path.exists() and dist_path.is_dir():
            return dist_path
    except (ImportError, ModuleNotFoundError, AttributeError):
        pass
    
    # Fallback: try relative to current file (for development if module not found)
    # Go up from octobot_node/app/utils.py -> octobot_node/app -> octobot_node -> ui -> dist
    current_file = Path(__file__).resolve()
    ui_module_path = current_file.parent.parent / "ui"
    dist_path = ui_module_path / "dist"
    
    if dist_path.exists() and dist_path.is_dir():
        return dist_path
    
    return None

