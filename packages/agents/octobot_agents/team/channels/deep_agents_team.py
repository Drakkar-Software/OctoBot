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
Deep Agents Team implementation using LangChain Deep Agents.

Provides AbstractDeepAgentsTeamChannelProducer which uses the Deep Agent
supervisor pattern for team orchestration instead of the traditional
channel-based execution.

Features:
- Subagent orchestration for context isolation
- Human-in-the-loop (HITL) for tool approval
- Skills for extensible capabilities
- Long-term memory via /memories/ path

See LangChain Deep Agents docs:
- https://docs.langchain.com/oss/python/deepagents/subagents
- https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
- https://docs.langchain.com/oss/python/deepagents/skills
- https://docs.langchain.com/oss/python/deepagents/long-term-memory
"""
from __future__ import annotations

import abc
import typing
import json
import logging
import uuid

from octobot_agents.team.channels.agents_team import (
    AbstractAgentsTeamChannel,
    AbstractAgentsTeamChannelConsumer,
    AbstractAgentsTeamChannelProducer,
)
from octobot_agents.agent.channels.ai_agent import (
    AbstractAIAgentChannel,
    AbstractAIAgentChannelProducer,
)
from octobot_agents.agent.channels.deep_agent import (
    AbstractDeepAgentChannel,
    AbstractDeepAgentChannelConsumer,
    AbstractDeepAgentChannelProducer,
    create_memory_backend,
    build_dictionary_subagent,
    build_subagents_from_producers,
    create_supervisor_agent,
    # HITL utilities
    create_interrupt_config,
    build_hitl_decision,
    # Skills utilities
    discover_skills,
    create_skills_files_dict,
)
from octobot_agents.constants import (
    MEMORIES_PATH_PREFIX,
    AGENT_DEFAULT_TEMPERATURE,
    # HITL
    HITL_DECISION_APPROVE,
    HITL_DECISION_REJECT,
    HITL_INTERRUPT_KEY,
    # Skills
    SKILLS_PATH_PREFIX,
    SKILLS_DEFAULT_DIR,
)
from octobot_agents.errors import DeepAgentNotAvailableError
import octobot_services.services.abstract_ai_service as abstract_ai_service
from octobot_agents.utils.deep_agent_adapter import create_model_for_deep_agent

try:
    from deepagents import create_deep_agent, CompiledSubAgent
    from langchain.chat_models import init_chat_model
    from langgraph.store.memory import InMemoryStore
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    DEEP_AGENTS_AVAILABLE = True
except ImportError:
    DEEP_AGENTS_AVAILABLE = False
    create_deep_agent = None
    init_chat_model = None
    CompiledSubAgent = None
    InMemoryStore = None
    MemorySaver = None
    Command = None
    logging.getLogger(__name__).warning("deepagents not available - Deep Agent features disabled")


class AbstractDeepAgentsTeamChannel(AbstractAgentsTeamChannel):
    """Channel for Deep Agents Team outputs."""
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentsTeamChannelConsumer(AbstractAgentsTeamChannelConsumer):
    """Consumer for Deep Agents Team outputs."""
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentsTeamChannelProducer(AbstractAgentsTeamChannelProducer, abc.ABC):
    """
    Team producer using LangChain Deep Agents with supervisor pattern.
    
    Instead of traditional channel-based execution, this uses Deep Agents
    where the manager is a supervisor that orchestrates worker subagents.
    
    Key differences from AbstractSyncAgentsTeamChannelProducer:
    - Workers are Deep Agent subagents, not channel producers
    - Manager is a supervisor that delegates via natural language
    - Uses /memories/ path for persistent memory
    - No DAG-based execution - Deep Agent handles orchestration
    
    Features:
    - Subagent orchestration for context isolation
    - Human-in-the-loop (HITL) for tool approval workflows
    - Skills for extensible agent capabilities
    - Long-term memory via /memories/ path
    
    Subclasses should:
    - Define TEAM_NAME and TEAM_CHANNEL
    - Implement get_worker_definitions() to return worker configs
    - Implement get_manager_instructions() for supervisor behavior
    - Optionally override get_interrupt_config() for HITL
    - Optionally override get_skills() for skills support
    """
    
    TEAM_CHANNEL: typing.Type[AbstractDeepAgentsTeamChannel] = AbstractDeepAgentsTeamChannel
    TEAM_CONSUMER: typing.Type[AbstractDeepAgentsTeamChannelConsumer] = AbstractDeepAgentsTeamChannelConsumer
    
    # Deep Agent specific
    MAX_ITERATIONS: int = 10
    ENABLE_DEBATE: bool = False
    
    # HITL configuration
    ENABLE_HITL: bool = False
    HITL_INTERRUPT_TOOLS: dict[str, typing.Any] = {}
    
    # Skills configuration
    SKILLS_DIRS: list[str] = []
    
    def __init__(
        self,
        channel: typing.Optional[AbstractDeepAgentsTeamChannel] = None,
        ai_service: typing.Optional[abstract_ai_service.AbstractAIService] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
        store: typing.Any = None,
        checkpointer: typing.Any = None,
        skills: list[str] | None = None,
        interrupt_on: dict[str, typing.Any] | None = None,
    ):
        """
        Initialize the Deep Agents team producer.
        
        Args:
            channel: Optional output channel for team results.
            ai_service: The LLM service instance.
            model: LLM model to use.
            max_tokens: Maximum tokens for LLM responses.
            temperature: Temperature for LLM randomness.
            team_name: Override default team name.
            team_id: Unique identifier for this team instance.
            store: Optional memory store for Deep Agent.
            checkpointer: Optional checkpointer for HITL (required for interrupts).
            skills: Optional list of skill source paths.
            interrupt_on: Optional tool interrupt configuration for HITL.
        """
        # We don't use the parent's agent/relations initialization
        # Deep Agents handle orchestration internally
        self.channel = channel
        self.ai_service = ai_service
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature or AGENT_DEFAULT_TEMPERATURE
        self.team_name = team_name or getattr(self.__class__, 'TEAM_NAME', self.__class__.__name__)
        self.team_id = team_id
        
        self._store = store
        self._checkpointer = checkpointer
        self._deep_agent = None
        self._workers: list[dict[str, typing.Any]] = []
        
        # HITL configuration
        self._interrupt_on = interrupt_on or self.HITL_INTERRUPT_TOOLS
        
        # Skills configuration
        self._skills = skills or self.SKILLS_DIRS
        
        # Thread management for HITL
        self._current_thread_id: str | None = None
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        if not DEEP_AGENTS_AVAILABLE:
            self.logger.warning("deep_agents not available - team will not function")
    
    @abc.abstractmethod
    def get_worker_definitions(self) -> list[dict[str, typing.Any]]:
        """
        Get worker subagent definitions for the team.
        
        Returns list of worker configs, each with:
        - name: Unique worker name
        - instructions: Worker's system prompt
        - tools: Optional list of tool functions
        - model: Optional model override
        
        Returns:
            List of worker definition dictionaries.
        """
        raise NotImplementedError("Subclasses must implement get_worker_definitions()")
    
    @abc.abstractmethod
    def get_manager_instructions(self) -> str:
        """
        Get the manager/supervisor instructions.
        
        These instructions tell the supervisor how to:
        - Coordinate workers
        - Handle the workflow
        - Synthesize results
        
        Returns:
            Manager instruction string.
        """
        raise NotImplementedError("Subclasses must implement get_manager_instructions()")
    
    def get_manager_tools(self) -> list[typing.Callable] | None:
        """
        Get additional tools for the manager.
        
        Override to provide custom tools to the supervisor.
        
        Returns:
            List of tool functions or None.
        """
        return None
    
    def get_critic_config(self) -> dict[str, typing.Any] | None:
        """
        Get critic configuration for debate mode.
        
        Override to configure critic behavior when ENABLE_DEBATE is True.
        
        Returns:
            Critic config dict or None.
        """
        if not self.ENABLE_DEBATE:
            return None
        return {
            "name": "critic",
            "instructions": "Critique the analysis, identify weaknesses, suggest improvements.",
        }
    
    def get_interrupt_config(self) -> dict[str, typing.Any]:
        """
        Get interrupt configuration for HITL.
        
        Override to customize which tools require approval.
        
        Returns:
            Dict mapping tool names to interrupt configs.
        """
        return self._interrupt_on
    
    def get_skills(self) -> list[str]:
        """
        Get skill source paths for this team.
        
        Override to provide custom skill directories.
        
        Returns:
            List of skill source paths.
        """
        return self._skills
    
    def _get_or_create_store(self) -> typing.Any:
        """Get or create the memory store."""
        if self._store is None:
            self._store = create_memory_backend()
        return self._store
    
    def _get_or_create_checkpointer(self) -> typing.Any:
        """Get or create the checkpointer for HITL."""
        if self._checkpointer is None and DEEP_AGENTS_AVAILABLE:
            self._checkpointer = MemorySaver()
        return self._checkpointer
    
    def _build_deep_agent(self) -> typing.Any:
        """Build the Deep Agent with supervisor pattern, HITL, and Skills."""
        if not DEEP_AGENTS_AVAILABLE:
            raise DeepAgentNotAvailableError("deep_agents package is required")
        
        workers = self.get_worker_definitions()
        self._workers = workers
        
        # Build subagents from worker definitions
        subagents = [
            build_dictionary_subagent(
                name=w.get("name", "unnamed"),
                instructions=w.get("instructions", ""),
                description=w.get("description"),
                tools=w.get("tools"),
                model=w.get("model") or (self.ai_service.model if self.ai_service else self.model),
                handoff_back=w.get("handoff_back", True),
                interrupt_on=w.get("interrupt_on"),
            )
            for w in workers
        ]
        
        # Add critic if debate is enabled
        critic_config = self.get_critic_config()
        if self.ENABLE_DEBATE and critic_config:
            critic_subagent = build_dictionary_subagent(
                name=critic_config.get("name", "critic"),
                instructions=critic_config.get("instructions", ""),
                description="Critiques analyses and suggests improvements",
                tools=critic_config.get("tools"),
                handoff_back=True,
            )
            subagents.append(critic_subagent)
        
        # Build supervisor instructions
        manager_instructions = self.get_manager_instructions()
        team_instructions = f"""
You are the manager of the {self.team_name} team.

{manager_instructions}

Your team members:
{chr(10).join(f"- {w.get('name', 'unnamed')}: {w.get('description', w.get('instructions', '')[:100])}..." for w in workers)}

Workflow:
1. Use write_todos to plan your approach
2. Delegate tasks to appropriate team members
3. Collect and synthesize their results
4. {"Run debate rounds with critic if needed" if self.ENABLE_DEBATE else "Provide final synthesized output"}

Save important insights to /memories/ for future reference.
""".strip()
        
        model = create_model_for_deep_agent(self.ai_service, self.model)
        
        # Build agent kwargs
        agent_kwargs: dict[str, typing.Any] = {
            "model": model,
            "system_prompt": team_instructions,
            "tools": self.get_manager_tools() or [],
            "subagents": subagents,
            "store": self._get_or_create_store(),
            "name": f"{self.team_name}_manager",
        }
        
        # Add skills if configured
        skills = self.get_skills()
        if skills:
            agent_kwargs["skills"] = skills
        
        # Add HITL if configured
        interrupt_config = self.get_interrupt_config()
        if interrupt_config:
            checkpointer = self._get_or_create_checkpointer()
            agent_kwargs["interrupt_on"] = interrupt_config
            agent_kwargs["checkpointer"] = checkpointer
        
        return create_deep_agent(**agent_kwargs)
    
    def get_deep_agent(self, force_rebuild: bool = False) -> typing.Any:
        """Get the Deep Agent, creating if necessary."""
        if self._deep_agent is None or force_rebuild:
            self._deep_agent = self._build_deep_agent()
        return self._deep_agent
    
    async def run(
        self,
        initial_data: typing.Dict[str, typing.Any],
        thread_id: str | None = None,
        skills_files: dict[str, str] | None = None,
    ) -> typing.Dict[str, typing.Any]:
        """
        Execute the team using Deep Agent supervisor pattern.
        
        Args:
            initial_data: Initial data to process.
            thread_id: Optional thread ID for HITL state persistence.
            skills_files: Optional dict of skill files for StateBackend.
            
        Returns:
            Dict with team execution results. If HITL interrupt triggered,
            contains "__interrupt__" key with pending actions.
        """
        if not DEEP_AGENTS_AVAILABLE:
            return {"error": "Deep Agents not available"}
        
        agent = self.get_deep_agent()
        if agent is None:
            return {"error": "Failed to create Deep Agent"}
        
        # Build input message
        message = self._build_input_message(initial_data)
        
        # Use provided thread_id or generate new one
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self._current_thread_id = thread_id
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Build invoke input
        invoke_input: dict[str, typing.Any] = {
            "messages": [{"role": "user", "content": message}]
        }
        
        # Add skills files if provided (for StateBackend)
        if skills_files:
            invoke_input["files"] = skills_files
        
        try:
            result = await agent.ainvoke(invoke_input, config=config)
            
            # Check for HITL interrupt
            if self.is_interrupted(result):
                return result  # Return raw result with interrupt info
            
            parsed_result = self._parse_result(result)
            
            # Push result if we have a channel
            if self.channel is not None:
                await self.push(parsed_result)
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"Error running Deep Agent team: {e}")
            return {"error": str(e)}
    
    # ========================================================================
    # HITL Methods
    # ========================================================================
    
    def is_interrupted(self, result: dict) -> bool:
        """Check if the result contains an HITL interrupt."""
        return HITL_INTERRUPT_KEY in result
    
    def get_interrupt_info(self, result: dict) -> dict | None:
        """
        Get interrupt information from a result.
        
        Args:
            result: Agent invocation result.
        
        Returns:
            Dict with action_requests and review_configs, or None.
        """
        if not self.is_interrupted(result):
            return None
        
        interrupts = result[HITL_INTERRUPT_KEY]
        if not interrupts:
            return None
        
        return interrupts[0].value if hasattr(interrupts[0], 'value') else interrupts[0]
    
    async def resume_with_decisions(
        self,
        decisions: list[dict[str, typing.Any]],
        thread_id: str | None = None,
    ) -> dict:
        """
        Resume team execution after HITL interrupt with user decisions.
        
        Each decision should be one of:
        - {"type": "approve"} - Execute tool with original args
        - {"type": "edit", "edited_action": {"name": "...", "args": {...}}} - Execute with modified args
        - {"type": "reject"} - Skip the tool call
        
        Args:
            decisions: List of decisions, one per interrupted action.
            thread_id: Thread ID to resume (uses current if not provided).
        
        Returns:
            Team execution results.
        """
        if not DEEP_AGENTS_AVAILABLE:
            return {"error": "Deep Agents not available"}
        
        agent = self.get_deep_agent()
        if agent is None:
            return {"error": "Deep Agent not available"}
        
        thread_id = thread_id or self._current_thread_id
        if thread_id is None:
            return {"error": "No thread_id for resume"}
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config,
            )
            
            # Check for another interrupt
            if self.is_interrupted(result):
                return result
            
            parsed_result = self._parse_result(result)
            
            # Push result if we have a channel
            if self.channel is not None:
                await self.push(parsed_result)
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"Error resuming Deep Agent team: {e}")
            return {"error": str(e)}
    
    async def approve_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        """Convenience method to approve all pending HITL interrupts."""
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": HITL_DECISION_APPROVE} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    async def reject_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        """Convenience method to reject all pending HITL interrupts."""
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": HITL_DECISION_REJECT} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    def _build_input_message(self, initial_data: typing.Dict[str, typing.Any]) -> str:
        """
        Build the input message for the supervisor.
        
        Override to customize message formatting.
        
        Args:
            initial_data: The initial data dict.
            
        Returns:
            Formatted message string.
        """
        data_str = json.dumps(initial_data, indent=2, default=str)
        return f"""
Process the following data with your team:

{data_str}

Coordinate with your workers and provide a final synthesized result.
""".strip()
    
    def _parse_result(self, result: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Parse the Deep Agent result into a standard format.
        
        Override to customize result parsing.
        
        Args:
            result: Raw Deep Agent result.
            
        Returns:
            Parsed result dict.
        """
        try:
            messages = result.get("messages", [])
            if not messages:
                return {"error": "No response from agent"}
            
            # Get the last assistant message
            last_message = messages[-1]
            content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
            
            # Try to parse as JSON
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # Return raw content
            return {"result": content}
            
        except Exception as e:
            self.logger.error(f"Error parsing result: {e}")
            return {"error": str(e)}
    
    async def push(self, result: typing.Any) -> None:
        """Push result to the team channel."""
        if self.channel is None:
            return
        
        for consumer in self.channel.get_consumers():
            await consumer.queue.put({
                "team_name": self.team_name,
                "team_id": self.team_id or "",
                "result": result,
            })
    
    def get_memory_path(self, memory_type: str = "data") -> str:
        """Get the memory path for this team."""
        return f"{MEMORIES_PATH_PREFIX}{self.team_name}/{memory_type}"
