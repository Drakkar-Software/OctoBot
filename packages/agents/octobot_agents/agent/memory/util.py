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
"""
Utility functions for memory export and import.
"""
import json
import os
import typing

import octobot_commons.logging as logging

from octobot_agents.storage import JSONMemoryStorage

logger = logging.get_logger("MemoryUtil")


def export_memories(memory_manager: JSONMemoryStorage, file_path: str) -> None:
    """
    Export all memories to a JSON file.
    
    Args:
        memory_manager: The memory manager instance.
        file_path: Path to export file.
    """
    if not memory_manager or not memory_manager.is_enabled():
        logger.warning("Memory manager is not enabled, cannot export")
        return
    
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        data = {
            "agent_version": memory_manager.agent_version,
            "memories": memory_manager.get_all_memories(),
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(data['memories'])} memories to {file_path}")
    except Exception as e:
        logger.error(f"Error exporting memories: {e}")
        raise


def import_memories(
    memory_manager: JSONMemoryStorage,
    file_path: str,
    merge: bool = False,
) -> None:
    """
    Import memories from a JSON file.
    
    Args:
        memory_manager: The memory manager instance.
        file_path: Path to import file.
        merge: If True, merge with existing memories (check for duplicates by id).
               If False, replace all existing memories.
    """
    if not memory_manager or not memory_manager.is_enabled():
        logger.warning("Memory manager is not enabled, cannot import")
        return
    
    if not os.path.exists(file_path):
        logger.error(f"Import file not found: {file_path}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported_memories = data.get("memories", [])
        imported_version = data.get("agent_version")
        
        # Validate version
        if imported_version and imported_version != memory_manager.agent_version:
            logger.warning(
                f"Version mismatch: imported={imported_version}, "
                f"current={memory_manager.agent_version}"
            )
        
        if merge:
            # Merge: check for duplicates by id
            existing_ids = {m.get("id") for m in memory_manager.get_all_memories()}
            new_memories = [m for m in imported_memories if m.get("id") not in existing_ids]
            memory_manager._memories.extend(new_memories)
            logger.info(f"Merged {len(new_memories)} new memories (skipped {len(imported_memories) - len(new_memories)} duplicates)")
        else:
            # Replace
            memory_manager._memories = imported_memories
            logger.info(f"Replaced all memories with {len(imported_memories)} imported memories")
        
        # Prune if needed
        if len(memory_manager._memories) > memory_manager.max_memories:
            memory_manager._prune_memories()
        
        memory_manager._save_memories()
    except Exception as e:
        logger.error(f"Error importing memories: {e}")
        raise
