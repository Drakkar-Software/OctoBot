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

import abc
import typing


class AbstractAnalysisStorage(abc.ABC):
    """
    Abstract base class for team analysis storage.
    
    Handles persistence of agent analysis results for debugging and audit purposes.
    Implementations manage directory structure, file format, and cleanup operations.
    """
    
    @abc.abstractmethod
    def save_analysis(
        self,
        agent_name: str,
        result: typing.Any,
        team_name: str,
        team_id: typing.Optional[str],
    ) -> None:
        """
        Save analysis results to persistent storage.
        
        Args:
            agent_name: Name of the agent producing the analysis.
            result: The analysis result to save (dict, str, or other serializable).
            team_name: Name of the team.
            team_id: ID of the team instance (optional).
        """
        raise NotImplementedError("save_analysis must be implemented by subclasses")
    
    @abc.abstractmethod
    def clear_transient_files(self) -> None:
        """
        Clear analysis files from previous runs.
        
        Removes all analysis files to ensure clean state for next execution.
        """
        raise NotImplementedError("clear_transient_files must be implemented by subclasses")
    
    @abc.abstractmethod
    def get_analysis_path(self) -> str:
        """
        Get the base directory path for analysis storage.
        
        Returns:
            The directory path where analysis files are stored.
        """
        raise NotImplementedError("get_analysis_path must be implemented by subclasses")
