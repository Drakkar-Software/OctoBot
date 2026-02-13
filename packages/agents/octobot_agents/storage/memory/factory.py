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
import octobot_agents.storage.memory.abstract_memory_storage as abstract_memory_storage
import octobot_agents.enums as enums
import octobot_agents.storage.memory.json_memory_storage as json_memory_storage
import octobot_agents.constants as constants
import octobot_agents.errors as errors


def create_memory_storage(
    storage_type: enums.MemoryStorageType,
    agent_name: str,
    agent_version: str,
    enabled: bool = True,
    search_limit: int = 5,
    storage_enabled: bool = True,
    agent_id_key: str = "agent_id",
    max_memories: int = constants.DEFAULT_MAX_MEMORIES,
) -> abstract_memory_storage.AbstractMemoryStorage:
    """
    Factory function to create a memory storage instance based on storage type.
    
    Args:
        storage_type: The type of storage to create (MemoryStorageType enum).
        agent_name: Name of the agent using this memory storage.
        agent_version: Version of the agent.
        enabled: Whether memory is enabled.
        search_limit: Maximum number of memories to retrieve.
        storage_enabled: Whether to store new memories.
        agent_id_key: Key in input_data for agent_id.
        max_memories: Maximum number of memories to store.
    
    Returns:
        An instance of AbstractMemoryStorage corresponding to the storage_type.
    
    Raises:
        ValueError: If storage_type is not supported.
    """
    if storage_type == enums.MemoryStorageType.JSON:
        return json_memory_storage.JSONMemoryStorage(
            agent_name=agent_name,
            agent_version=agent_version,
            enabled=enabled,
            search_limit=search_limit,
            storage_enabled=storage_enabled,
            agent_id_key=agent_id_key,
            max_memories=max_memories,
        )
    else:
        raise errors.UnsupportedStorageTypeError(f"Unsupported memory storage type: {storage_type}")
