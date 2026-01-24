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


class AbstractMemoryStorage(abc.ABC):
    """
    Abstract base class for memory storage.
    
    Defines the interface that all memory storage implementations must follow.
    Memory storage is responsible for storing, retrieving, and managing
    agent memories.
    """
    
    @abc.abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if memory is enabled and available.
        
        Returns:
            True if memory is enabled, False otherwise.
        """
        raise NotImplementedError("is_enabled must be implemented by subclasses")
    
    @abc.abstractmethod
    def extract_agent_id(self, input_data: typing.Any) -> str:
        """
        Extract agent_id from input_data.
        
        Args:
            input_data: Input data that may contain agent_id.
            
        Returns:
            The agent_id string, or empty string if not found.
        """
        raise NotImplementedError("extract_agent_id must be implemented by subclasses")
    
    @abc.abstractmethod
    async def search_memories(
        self,
        query: str,
        input_data: typing.Any,
        limit: typing.Optional[int] = None,
    ) -> typing.List[dict]:
        """
        Search for relevant memories.
        
        Args:
            query: Search query.
            input_data: Input data containing agent_id or other context.
            limit: Maximum memories to retrieve (defaults to search_limit).
            
        Returns:
            List of memory dictionaries with 'memory' and 'metadata' keys.
        """
        raise NotImplementedError("search_memories must be implemented by subclasses")
    
    @abc.abstractmethod
    async def store_memory(
        self,
        messages: typing.List[dict],
        input_data: typing.Any,
        output: typing.Any = None,
        metadata: typing.Optional[dict] = None,
    ) -> None:
        """
        Store memories from agent execution.
        
        Args:
            messages: Conversation messages (user + assistant).
            input_data: Input data for context.
            output: Optional agent output.
            metadata: Optional metadata to attach.
        """
        raise NotImplementedError("store_memory must be implemented by subclasses")
    
    @abc.abstractmethod
    def format_memories_for_prompt(self, memories: typing.List[dict]) -> str:
        """
        Format memories for inclusion in prompts.
        
        Args:
            memories: List of memory dictionaries.
            
        Returns:
            Formatted string with memories, or empty string if none.
        """
        raise NotImplementedError("format_memories_for_prompt must be implemented by subclasses")
    
    @abc.abstractmethod
    async def store_execution_memory(
        self,
        input_data: typing.Any,
        output: typing.Any,
        user_message: typing.Optional[str] = None,
        assistant_message: typing.Optional[str] = None,
        metadata: typing.Optional[dict] = None,
    ) -> None:
        """
        Convenience method to store memory from agent execution.
        
        Automatically builds messages from input_data and output if not provided.
        
        Args:
            input_data: The input data that was processed.
            output: The agent's output/result.
            user_message: Optional user message (auto-built if not provided).
            assistant_message: Optional assistant message (auto-built if not provided).
            metadata: Optional metadata to attach.
        """
        raise NotImplementedError("store_execution_memory must be implemented by subclasses")
    
    @abc.abstractmethod
    def get_all_memories(self) -> typing.List[dict]:
        """
        Get all memories (for summaries).
        
        Returns:
            List of all memory dictionaries.
        """
        raise NotImplementedError("get_all_memories must be implemented by subclasses")
    
    @abc.abstractmethod
    def get_memory_by_id(self, memory_id: str) -> typing.Optional[dict]:
        """
        Get a memory by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve.
            
        Returns:
            The memory dictionary if found, None otherwise.
        """
        raise NotImplementedError("get_memory_by_id must be implemented by subclasses")
    
    @abc.abstractmethod
    def increment_memory_use(self, memory_id: str) -> None:
        """
        Increment use_count for a memory.
        
        Args:
            memory_id: The ID of the memory to update.
        """
        raise NotImplementedError("increment_memory_use must be implemented by subclasses")
    
    @property
    @abc.abstractmethod
    def agent_version(self) -> str:
        """
        Get the agent version.
        
        Returns:
            The agent version string.
        """
        raise NotImplementedError("agent_version property must be implemented by subclasses")
    
    @property
    @abc.abstractmethod
    def max_memories(self) -> int:
        """
        Get the maximum number of memories.
        
        Returns:
            The maximum number of memories that can be stored.
        """
        raise NotImplementedError("max_memories property must be implemented by subclasses")
