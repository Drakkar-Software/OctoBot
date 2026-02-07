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
    
    The dist directory is always located at
    tentacles/Services/Interfaces/node_web_interface/dist,
    both in development and when installed as a package.
    
    Returns:
        Path to dist directory if found, None otherwise.
    """
    # Locate node_web_interface module directory
    try:
        import tentacles.Services.Interfaces.node_web_interface as node_web_interface
        interface_path = Path(node_web_interface.__file__).resolve().parent
        dist_path = interface_path / "dist"
        if dist_path.exists() and dist_path.is_dir():
            return dist_path
    except (ImportError, ModuleNotFoundError, AttributeError):
        pass
    
    # Fallback: try relative to current file (for development if module not found)
    # Go up from node_api/utils.py -> node_api -> Interfaces -> node_web_interface -> dist
    current_file = Path(__file__).resolve()
    interface_path = current_file.parent.parent / "node_web_interface"
    dist_path = interface_path / "dist"
    
    if dist_path.exists() and dist_path.is_dir():
        return dist_path
    
    return None
