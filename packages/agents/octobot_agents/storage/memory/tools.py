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

import octobot_services.services.abstract_ai_service as abstract_ai_service

import octobot_agents.storage.memory.abstract_memory_storage as abstract_memory_storage


def get_memory_tools(memory_manager: abstract_memory_storage.AbstractMemoryStorage, ai_service: abstract_ai_service.AbstractAIService) -> typing.List[dict]:
    if not memory_manager or not memory_manager.is_enabled():
        return []
    
    return [
        ai_service.format_tool_definition(
            name="get_memory_summaries",
            description="Get a list of available memories with summaries (id, title, context, tags, category, importance, confidence). Use this to see what memories are available before fetching specific ones.",
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional filter by memory category",
                    },
                    "min_importance": {
                        "type": "number",
                        "description": "Optional minimum importance score (0.0-1.0)",
                    },
                },
            },
        ),
        ai_service.format_tool_definition(
            name="get_memory_by_id",
            description="Get the full content of a specific memory by its UUID. Use this after getting memory summaries to fetch detailed information.",
            parameters={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The UUID of the memory to fetch",
                    },
                },
                "required": ["id"],
            },
        ),
    ]


def execute_memory_tool(
    memory_manager: abstract_memory_storage.AbstractMemoryStorage,
    tool_name: str,
    arguments: dict,
) -> typing.Any:
    if not memory_manager or not memory_manager.is_enabled():
        return {"error": "Memory is not enabled"}
    
    try:
        if tool_name == "get_memory_summaries":
            category = arguments.get("category")
            min_importance = arguments.get("min_importance")
            
            all_memories = memory_manager.get_all_memories()
            
            # Filter by category if provided
            if category:
                all_memories = [m for m in all_memories if m.get("category") == category]
            
            # Filter by importance if provided
            if min_importance is not None:
                all_memories = [
                    m for m in all_memories
                    if m.get("importance_score", 0.5) >= min_importance
                ]
            
            # Return summaries
            summaries = []
            for mem in all_memories:
                summaries.append({
                    "id": mem.get("id"),
                    "title": mem.get("title", ""),
                    "context": mem.get("context", ""),
                    "tags": mem.get("tags", []),
                    "category": mem.get("category", "general"),
                    "importance_score": mem.get("importance_score", 0.5),
                    "confidence_score": mem.get("confidence_score", 0.5),
                })
            
            return summaries
        
        elif tool_name == "get_memory_by_id":
            memory_id = arguments.get("id")
            if not memory_id:
                return {"error": "Memory ID is required"}
            
            memory = memory_manager.get_memory_by_id(memory_id)
            if not memory:
                return {"error": f"Memory with ID {memory_id} not found"}
            
            # Increment use count
            memory_manager.increment_memory_use(memory_id)
            
            return {
                "id": memory.get("id"),
                "title": memory.get("title", ""),
                "context": memory.get("context", ""),
                "content": memory.get("content", ""),
                "category": memory.get("category", "general"),
                "tags": memory.get("tags", []),
                "importance_score": memory.get("importance_score", 0.5),
                "confidence_score": memory.get("confidence_score", 0.5),
                "metadata": memory.get("metadata", {}),
            }
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": str(e)}
