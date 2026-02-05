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
import sys
import typing
import uuid

import pydantic
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging

from octobot_agents.storage.memory.abstract_memory_storage import AbstractMemoryStorage
from octobot_agents.constants import (
    MEMORY_FOLDER_NAME,
    MEMORY_FILE_EXTENSION,
    DEFAULT_CATEGORY,
    DEFAULT_IMPORTANCE_SCORE,
    DEFAULT_CONFIDENCE_SCORE,
    DEFAULT_MAX_MEMORIES,
    MEMORY_TITLE_MAX_LENGTH,
    MEMORY_CONTEXT_MAX_LENGTH,
    MEMORY_CONTENT_MAX_LENGTH,
)
import octobot_agents.models as models

# Platform-specific file locking
fcntl = None
msvcrt = None
try:
    if sys.platform != 'win32':
        import fcntl
        HAS_FCNTL = True
    else:
        import msvcrt
        HAS_FCNTL = False
    HAS_FILE_LOCKING = True
except ImportError:
    HAS_FILE_LOCKING = False


class JSONMemoryStorage(AbstractMemoryStorage):
    """
    Memory storage for AI agents using JSON file-based storage.
    
    Each agent has its own JSON file at `user/data/agents/memories/<agent_name>.json`.
    Memory is stored with structured fields: id, title, context, content, category, tags,
    importance_score, confidence_score, and metadata (with use_count).
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_version: str,
        enabled: bool = True,
        search_limit: int = 5,
        storage_enabled: bool = True,
        agent_id_key: str = "agent_id",
        max_memories: int = DEFAULT_MAX_MEMORIES,
    ):
        """
        Initialize the memory storage.
        
        Args:
            agent_name: Name of the agent using this memory storage.
            agent_version: Version of the agent.
            enabled: Whether memory is enabled.
            search_limit: Maximum number of memories to retrieve.
            storage_enabled: Whether to store new memories.
            agent_id_key: Key in input_data for agent_id.
            max_memories: Maximum number of memories to store (default: 100).
        """
        self.agent_name = agent_name
        self._agent_version = agent_version
        self.enabled = enabled
        self.search_limit = search_limit
        self.storage_enabled = storage_enabled
        self.agent_id_key = agent_id_key
        self._max_memories = max_memories
        self.logger = logging.get_logger(f"{self.__class__.__name__}[{agent_name}]")
        
        self._memories: typing.List[dict] = []
        self._memory_file_path: typing.Optional[str] = None
        
        if self.enabled:
            self._memory_file_path = self._get_memory_file_path()
            self._ensure_directory_exists()
            self._load_memories()
            self.logger.debug(f"Memory storage initialized for {agent_name} with {len(self._memories)} memories")
    
    def _get_memory_file_path(self) -> str:
        """Build path to memory JSON file."""
        memory_dir = os.path.join(
            commons_constants.USER_FOLDER,
            commons_constants.DATA_FOLDER,
            MEMORY_FOLDER_NAME,
            "memories"
        )
        # Sanitize agent_name for filename
        safe_agent_name = self.agent_name.replace("/", "_").replace("\\", "_")
        return os.path.join(memory_dir, f"{safe_agent_name}{MEMORY_FILE_EXTENSION}")
    
    def _ensure_directory_exists(self) -> None:
        """Create memory directory if it doesn't exist."""
        if self._memory_file_path:
            directory = os.path.dirname(self._memory_file_path)
            os.makedirs(directory, exist_ok=True)
    
    def _load_memories(self) -> None:
        """Load memories from JSON file."""
        if not self._memory_file_path or not os.path.exists(self._memory_file_path):
            self._memories = []
            return
        
        try:
            with open(self._memory_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate agent_version
            stored_version = data.get("agent_version")
            if stored_version and stored_version != self.agent_version:
                self.logger.warning(
                    f"Memory file version mismatch for {self.agent_name}: "
                    f"stored={stored_version}, current={self.agent_version}"
                )
            
            self._memories = data.get("memories", [])
            self.logger.debug(f"Loaded {len(self._memories)} memories from {self._memory_file_path}")
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Error loading memories from {self._memory_file_path}: {e}")
            self._memories = []
    
    def _save_memories(self) -> None:
        """Save memories to JSON file with file locking."""
        if not self._memory_file_path:
            return
        
        try:
            # Use atomic write: write to temp file, then rename
            temp_path = f"{self._memory_file_path}.tmp"
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Acquire exclusive lock if available
                if HAS_FILE_LOCKING:
                    try:
                        if HAS_FCNTL:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        else:
                            # Windows
                            file_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, file_size)
                    except (IOError, OSError) as e:
                        self.logger.warning(f"Could not acquire file lock: {e}")
                
                data = {
                    "agent_version": self.agent_version,
                    "memories": self._memories,
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename
            os.replace(temp_path, self._memory_file_path)
            self.logger.debug(f"Saved {len(self._memories)} memories to {self._memory_file_path}")
        except (IOError, OSError) as e:
            self.logger.warning(f"Error saving memories to {self._memory_file_path}: {e}")
    
    def is_enabled(self) -> bool:
        """Check if memory is enabled and available."""
        return self.enabled
    
    def extract_agent_id(self, input_data: typing.Any) -> str:
        """Extract agent_id from input_data."""
        if isinstance(input_data, dict):
            return input_data.get(self.agent_id_key, "")
        return ""
    
    async def search_memories(
        self,
        query: str,
        input_data: typing.Any,
        limit: typing.Optional[int] = None,
    ) -> typing.List[dict]:
        """
        Search for relevant memories.
        
        Returns memory summaries (title, context, tags) for LLM tool-based retrieval.
        
        Args:
            query: Search query.
            input_data: Input data containing agent_id.
            limit: Maximum memories to retrieve (defaults to search_limit).
            
        Returns:
            List of memory dictionaries with 'memory' and 'metadata' keys for compatibility.
        """
        if not self.is_enabled():
            return []
        
        try:
            limit = limit or self.search_limit
            
            # TODO: Implement Embedding-Based Search for better semantic matching
            # - Use sentence-transformers with 'all-MiniLM-L6-v2' model
            # - Generate embeddings when storing memories
            # - Calculate cosine similarity for search queries
            # - See plan documentation for detailed implementation guide
            
            # For now, return all memories as summaries (LLM will filter via tools)
            # Sort by importance_score and confidence_score (highest first)
            sorted_memories = sorted(
                self._memories,
                key=lambda m: (
                    m.get("importance_score", 0.5) * 0.6 +
                    m.get("confidence_score", 0.5) * 0.4
                ),
                reverse=True
            )
            
            # Return summaries (limit applied by LLM tool)
            results = []
            for mem in sorted_memories[:limit]:
                results.append({
                    "memory": mem.get("content", ""),
                    "metadata": {
                        "id": mem.get("id"),
                        "title": mem.get("title", ""),
                        "context": mem.get("context", ""),
                        "category": mem.get("category", DEFAULT_CATEGORY),
                        "tags": mem.get("tags", []),
                        "importance_score": mem.get("importance_score", DEFAULT_IMPORTANCE_SCORE),
                        "confidence_score": mem.get("confidence_score", DEFAULT_CONFIDENCE_SCORE),
                    }
                })
            
            if results:
                self.logger.debug(f"Retrieved {len(results)} memory summaries")
            return results
        except Exception as e:
            self.logger.warning(f"Error searching memories: {e}")
            return []
    
    def _truncate_content(
        self,
        title: str,
        context: str,
        content: str,
        title_max_length: typing.Optional[int] = None,
        context_max_length: typing.Optional[int] = None,
        content_max_length: typing.Optional[int] = None,
    ) -> typing.Tuple[str, str, str]:
        """
        Truncate title, context, and content to fit within limits.
        
        Uses smart truncation at word/sentence boundaries as fallback.
        Content should already be concise and generic from memory agent generation.
        
        Args:
            title: Title to truncate
            context: Context to truncate
            content: Full content to truncate
            title_max_length: Maximum length for title (uses constant if None)
            context_max_length: Maximum length for context (uses constant if None)
            content_max_length: Maximum length for content (uses constant if None)
            
        Returns:
            Tuple of (truncated_title, truncated_context, truncated_content)
        """
        title_max = title_max_length or MEMORY_TITLE_MAX_LENGTH
        context_max = context_max_length or MEMORY_CONTEXT_MAX_LENGTH
        content_max = content_max_length or MEMORY_CONTENT_MAX_LENGTH
        
        # Truncate title if needed
        if len(title) > title_max:
            truncated_title = title[:title_max]
            last_space = truncated_title.rfind(' ')
            if last_space > title_max * 0.7:
                title = truncated_title[:last_space].strip()
            else:
                title = truncated_title.strip()
        
        # Truncate context if needed
        if len(context) > context_max:
            truncated_context = context[:context_max]
            last_space = truncated_context.rfind(' ')
            if last_space > context_max * 0.7:
                context = truncated_context[:last_space].strip()
            else:
                context = truncated_context.strip()
        
        # Truncate content if needed
        if len(content) > content_max:
            truncated = content[:content_max]
            # Try to truncate at sentence boundary
            last_period = truncated.rfind('.')
            last_newline = truncated.rfind('\n')
            last_break = max(last_period, last_newline)
            if last_break > content_max * 0.7:
                content = truncated[:last_break + 1].strip()
            else:
                content = truncated.strip()
        
        return title, context, content
    
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
        if not self.is_enabled() or not self.storage_enabled:
            return
        
        try:
            agent_id = self.extract_agent_id(input_data)
            
            # Extract title and context from metadata if provided, otherwise generate from messages
            user_message = None
            assistant_message = None
            for msg in messages:
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                elif msg.get("role") == "assistant":
                    assistant_message = msg.get("content", "")
            
            # Use title from metadata if provided, otherwise generate from user message
            if metadata and metadata.get("title"):
                title = metadata.get("title")
            else:
                title = (user_message[:50] if user_message else "Memory") if user_message else "Memory"
            
            # Use context from metadata if provided, otherwise generate from agent_id
            if metadata and metadata.get("context"):
                context = metadata.get("context")
            else:
                context = f"Agent execution context"
                if agent_id:
                    context += f" for agent_id: {agent_id}"
            
            # Build content from messages
            # If metadata has title/context, it's likely instructional content - use user_message directly
            # Otherwise, format as conversation
            if metadata and (metadata.get("title") or metadata.get("context")):
                # Instructional content - use user_message directly without "User: " prefix
                content = user_message if user_message else ""
            else:
                # Regular conversation memory - format with prefixes
                content_parts = []
                if user_message:
                    content_parts.append(f"User: {user_message}")
                if assistant_message:
                    content_parts.append(f"Assistant: {assistant_message}")
                if output is not None:
                    if isinstance(output, dict):
                        content_parts.append(f"Output: {json.dumps(output, indent=2, default=str)}")
                    else:
                        content_parts.append(f"Output: {str(output)}")
                content = "\n".join(content_parts)
            
            # Truncate content if needed to fit within limits (fallback safety check)
            # Content should already be concise from memory agent generation
            title, context, content = self._truncate_content(
                title=title,
                context=context,
                content=content
            )
            
            # Extract category and tags from metadata
            category = metadata.get("category", DEFAULT_CATEGORY) if metadata else DEFAULT_CATEGORY
            tags = metadata.get("tags", []) if metadata else []
            importance_score = metadata.get("importance_score", DEFAULT_IMPORTANCE_SCORE) if metadata else DEFAULT_IMPORTANCE_SCORE
            
            # Create and validate MemoryStorageModel
            try:
                memory_model = models.MemoryStorageModel(
                    title=title,
                    context=context,
                    content=content,
                    category=category,
                    tags=tags,
                    importance_score=importance_score,
                    confidence_score=DEFAULT_CONFIDENCE_SCORE,
                )
            except pydantic.ValidationError as e:
                self.logger.error(f"Memory validation failed: {e}")
                raise
            
            # Create memory dict from validated model
            base_metadata = {
                self.agent_id_key: agent_id,
                "use_count": 0,
            }

            extra_metadata = {}
            if metadata:
                for key, value in metadata.items():
                    if key not in {
                        "category",
                        "tags",
                        "importance_score",
                        "confidence_score",
                        "title",
                        "context",
                    }:
                        extra_metadata[key] = value
            memory = {
                "id": uuid.uuid4().hex,
                "title": memory_model.title,
                "context": memory_model.context,
                "content": memory_model.content,
                "category": memory_model.category,
                "tags": memory_model.tags,
                "importance_score": memory_model.importance_score,
                "confidence_score": memory_model.confidence_score,
                "metadata": {
                    **base_metadata,
                    **extra_metadata,
                },
            }
            
            self._memories.append(memory)
            
            # Prune if needed
            if len(self._memories) > self.max_memories:
                self._prune_memories()
            
            self._save_memories()
            self.logger.debug("Stored memory")
        except Exception as e:
            self.logger.warning(f"Error storing memory: {e}")
    
    def format_memories_for_prompt(self, memories: typing.List[dict]) -> str:
        """
        Format memories for inclusion in prompts.
        
        Args:
            memories: List of memory dictionaries.
            
        Returns:
            Formatted string with memories, or empty string if none.
        """
        if not memories:
            return ""
        
        memory_lines = []
        for mem in memories:
            memory_text = mem.get("memory", "")
            metadata = mem.get("metadata", {})
            if memory_text:
                title = metadata.get("title", "")
                context = metadata.get("context", "")
                tags = metadata.get("tags", [])
                category = metadata.get("category", "")
                importance = metadata.get("importance_score", 0.5)
                confidence = metadata.get("confidence_score", 0.5)
                use_count = metadata.get("use_count", 0)
                
                line = f"- {memory_text}"
                if title:
                    line = f"## {title}\n{line}"
                if context:
                    line += f"\n  Context: {context}"
                if category:
                    line += f"\n  Category: {category}"
                if tags:
                    line += f"\n  Tags: {', '.join(tags)}"
                line += f"\n  Importance: {importance}, Confidence: {confidence}, Used: {use_count} times"
                memory_lines.append(line)
        
        if memory_lines:
            return "\n".join(memory_lines)
        return ""
    
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
        if not self.is_enabled() or not self.storage_enabled:
            return
        
        # Build messages if not provided
        messages = []
        if user_message:
            messages.append({"role": "user", "content": user_message})
        elif isinstance(input_data, dict):
            # Auto-build user message from input_data
            user_content = json.dumps(input_data, indent=2, default=str)[:500]
            messages.append({"role": "user", "content": user_content})
        
        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})
        elif output is not None:
            # Auto-build assistant message from output
            if isinstance(output, dict):
                assistant_content = json.dumps(output, indent=2, default=str)[:500]
            else:
                assistant_content = str(output)[:500]
            messages.append({"role": "assistant", "content": assistant_content})
        
        if messages:
            await self.store_memory(messages, input_data, output, metadata)
    
    def _prune_memories(self) -> None:
        """Remove memories when limit exceeded using priority scoring."""
        if len(self._memories) <= self.max_memories:
            return
        
        # Calculate priority score for each memory
        def priority_score(mem: dict) -> float:
            importance = mem.get("importance_score", DEFAULT_IMPORTANCE_SCORE)
            confidence = mem.get("confidence_score", DEFAULT_CONFIDENCE_SCORE)
            use_count = mem.get("metadata", {}).get("use_count", 0)
            return (importance * 0.4) + (confidence * 0.3) + (use_count / 100.0 * 0.3)
        
        # Sort by priority (lowest first)
        sorted_memories = sorted(self._memories, key=priority_score)
        
        # Remove lowest priority memories, but never prune critical ones (importance >= 0.9)
        to_remove = []
        for mem in sorted_memories:
            if len(self._memories) - len(to_remove) <= self.max_memories:
                break
            if mem.get("importance_score", 0) < 0.9:
                to_remove.append(mem)
        
        # Remove from memories list
        for mem in to_remove:
            self._memories.remove(mem)
        
        if to_remove:
            self.logger.info(f"Pruned {len(to_remove)} memories (kept {len(self._memories)})")
    
    def update_memory_importance(self, memory_id: str, score: float) -> None:
        """Update importance score for a memory."""
        for mem in self._memories:
            if mem.get("id") == memory_id:
                mem["importance_score"] = max(0.0, min(1.0, score))
                self._save_memories()
                return
        self.logger.warning(f"Memory {memory_id} not found for importance update")
    
    def update_memory_confidence(self, memory_id: str, score: float) -> None:
        """Update confidence score for a memory."""
        for mem in self._memories:
            if mem.get("id") == memory_id:
                mem["confidence_score"] = max(0.0, min(1.0, score))
                self._save_memories()
                return
        self.logger.warning(f"Memory {memory_id} not found for confidence update")
    
    def increment_memory_use(self, memory_id: str) -> None:
        """Increment use_count for a memory."""
        for mem in self._memories:
            if mem.get("id") == memory_id:
                metadata = mem.setdefault("metadata", {})
                metadata["use_count"] = metadata.get("use_count", 0) + 1
                self._save_memories()
                return
        self.logger.warning(f"Memory {memory_id} not found for use count increment")
    
    def get_memory_by_id(self, memory_id: str) -> typing.Optional[dict]:
        """Get a memory by its ID."""
        for mem in self._memories:
            if mem.get("id") == memory_id:
                return mem
        return None
    
    def get_all_memories(self) -> typing.List[dict]:
        """Get all memories (for summaries)."""
        return self._memories.copy()
    
    @property
    def agent_version(self) -> str:
        """Get the agent version."""
        return self._agent_version
    
    @property
    def max_memories(self) -> int:
        """Get the maximum number of memories."""
        return self._max_memories
