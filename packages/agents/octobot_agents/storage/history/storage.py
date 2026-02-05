#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
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

import typing

from octobot_agents.storage.history.abstract_analysis_storage import AbstractAnalysisStorage
from octobot_agents.storage.history.json_analysis_storage import JSONAnalysisStorage


def create_analysis_storage(
    storage_type: str = "json",
    analysis_dir: str = "analysis",
) -> AbstractAnalysisStorage:
    """
    Create an analysis storage instance.
    
    Args:
        storage_type: Type of storage to create (default: "json").
        analysis_dir: Directory name for storing analysis files (default: "analysis").
        
    Returns:
        An AbstractAnalysisStorage instance.
        
    Raises:
        ValueError: If storage_type is not recognized.
    """
    if storage_type == "json":
        return JSONAnalysisStorage(analysis_dir=analysis_dir)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
