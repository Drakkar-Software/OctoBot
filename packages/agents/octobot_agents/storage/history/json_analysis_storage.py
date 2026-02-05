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

import json
import os
import typing

import octobot_commons.logging as logging

from octobot_agents.storage.history.abstract_analysis_storage import AbstractAnalysisStorage


class JSONAnalysisStorage(AbstractAnalysisStorage):
    """
    JSON file-based storage for team analysis results.
    
    Saves agent analysis results to individual JSON files in an analysis directory
    for cross-agent access and debugging/audit purposes.
    
    Directory structure:
        analysis/
            {agent_name}.json
    """
    
    def __init__(
        self,
        analysis_dir: str = "analysis",
    ):
        """
        Initialize JSON analysis storage.
        
        Args:
            analysis_dir: Directory name for storing analysis files (default: "analysis").
        """
        self.analysis_dir = analysis_dir
        self.logger = logging.get_logger(self.__class__.__name__)
    
    def get_analysis_path(self) -> str:
        """
        Get the base directory path for analysis storage.
        
        Returns:
            The directory path where analysis files are stored.
        """
        return os.path.join(os.getcwd(), self.analysis_dir)
    
    def save_analysis(
        self,
        agent_name: str,
        result: typing.Any,
        team_name: str,
        team_id: typing.Optional[str],
    ) -> None:
        """
        Save analysis results to a JSON file.
        
        Saves agent analysis results to {analysis_dir}/{agent_name}.json with metadata.
        Creates the analysis directory if it doesn't exist.
        
        Args:
            agent_name: Name of the agent producing the analysis.
            result: The analysis result to save (dict, str, or other serializable).
            team_name: Name of the team.
            team_id: ID of the team instance (optional).
        """
        try:
            # Get base directory and create if needed
            base_dir = self.get_analysis_path()
            os.makedirs(base_dir, exist_ok=True)
            
            # Build file path
            file_path = os.path.join(base_dir, f"{agent_name}.json")
            
            # Convert result to serializable format
            if isinstance(result, dict):
                analysis_data = result
            else:
                # Try to get attributes as dict, otherwise convert to string
                try:
                    analysis_data = vars(result) if hasattr(result, "__dict__") else str(result)
                except Exception:
                    analysis_data = str(result)
            
            # Add metadata
            output_data = {
                "agent_name": agent_name,
                "team_name": team_name,
                "team_id": team_id,
                "result": analysis_data,
            }
            
            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, default=str)
            
            self.logger.debug(f"Analysis saved for {agent_name} to {file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to save analysis for {agent_name}: {e}")
    
    def clear_transient_files(self) -> None:
        """
        Clear all JSON files from the analysis directory.
        
        Removes all .json files from the analysis directory to ensure clean state
        for the next execution. Gracefully handles non-existent directories.
        """
        try:
            base_dir = self.get_analysis_path()
            
            # Skip if directory doesn't exist
            if not os.path.exists(base_dir):
                self.logger.debug(f"Analysis directory {base_dir} does not exist; nothing to clear")
                return
            
            # Remove all JSON files in the analysis directory
            cleared_count = 0
            for filename in os.listdir(base_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(base_dir, filename)
                    try:
                        os.remove(file_path)
                        cleared_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to remove {file_path}: {e}")
            
            self.logger.debug(f"Cleared {cleared_count} analysis files from {base_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to clear transient files: {e}")
