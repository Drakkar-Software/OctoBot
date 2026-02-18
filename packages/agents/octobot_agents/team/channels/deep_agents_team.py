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

Features:
- SubAgentMiddleware for task delegation to workers
- TodoListMiddleware for planning
- CompositeBackend for long-term memory (/memories/)
- Streaming support
- Debug logging for agent operations
"""

import abc
import typing
import json
import logging
import uuid

import octobot_agents.team.channels.agents_team as agents_team
import octobot_agents.agent.channels.agent as agent_channels
import octobot_agents.agent.channels.deep_agent as deep_agent
import octobot_agents.constants as constants
import octobot_agents.errors as errors
import octobot_agents.storage.history as history
import octobot_services.services.abstract_ai_service as abstract_ai_service

logger = logging.getLogger(__name__)

try:
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    from langgraph.store.memory import InMemoryStore
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    DEEP_AGENTS_AVAILABLE = True
except ImportError as e:
    DEEP_AGENTS_AVAILABLE = False
    logger.debug(f"deepagents not available - Deep Agent features disabled: {e}")


class AbstractDeepAgentsTeamChannel(agents_team.AbstractAgentsTeamChannel):
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentsTeamChannelConsumer(agents_team.AbstractAgentsTeamChannelConsumer):
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentsTeamChannelProducer(agents_team.AbstractAgentsTeamChannelProducer, abc.ABC):
    """
    Team producer using LangChain Deep Agents with supervisor pattern.
    
    Features:
    - SubAgentMiddleware for worker delegation
    - TodoListMiddleware for planning
    - CompositeBackend with /memories/ for persistent storage
    - Streaming support
    - Debug logging
    """
    
    TEAM_CHANNEL: typing.Type[AbstractDeepAgentsTeamChannel] = AbstractDeepAgentsTeamChannel
    TEAM_CONSUMER: typing.Type[AbstractDeepAgentsTeamChannelConsumer] = AbstractDeepAgentsTeamChannelConsumer
    
    MAX_ITERATIONS: int = 10
    ENABLE_DEBATE: bool = False
    ENABLE_STREAMING: bool = False
    
    ENABLE_HITL: bool = False
    HITL_INTERRUPT_TOOLS: dict[str, typing.Any] = {}
    
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
        enable_streaming: bool | None = None,
        analysis_storage: typing.Optional[typing.Any] = None,
    ):
        # pylint: disable=super-init-not-called,non-parent-init-called
        agent_channels.AbstractAgentChannelProducer.__init__(self, channel)
        self.ai_service = ai_service
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature or constants.AGENT_DEFAULT_TEMPERATURE
        self.team_name = team_name or self.__class__.__dict__.get('TEAM_NAME', self.__class__.__name__)
        self.team_id = team_id
        
        self._store = store
        self._checkpointer = checkpointer
        self._deep_agent = None
        self._workers: list[dict[str, typing.Any]] = []
        
        self._interrupt_on = interrupt_on or self.HITL_INTERRUPT_TOOLS
        self._skills = skills or self.SKILLS_DIRS
        self._enable_streaming = enable_streaming if enable_streaming is not None else self.ENABLE_STREAMING
        
        self._current_thread_id: str | None = None
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize analysis storage
        if analysis_storage is None:
            self.analysis_storage = history.create_analysis_storage()
        else:
            self.analysis_storage = analysis_storage
        
        if not deep_agent.DEEP_AGENTS_AVAILABLE:
            self.logger.warning("deep_agents not available - team will not function")
    
    @abc.abstractmethod
    def get_worker_definitions(self) -> list[dict[str, typing.Any]]:
        raise NotImplementedError("Subclasses must implement get_worker_definitions()")
    
    @abc.abstractmethod
    def get_manager_instructions(self) -> str:
        raise NotImplementedError("Subclasses must implement get_manager_instructions()")
    
    def save_analysis(
        self,
        agent_name: str,
        result: typing.Any,
    ) -> None:
        """
        Save analysis results to storage for debugging/audit purposes.
        
        Delegates to the analysis storage backend. Results are saved with metadata
        for cross-agent access and debugging.
        
        Args:
            agent_name: Name of the agent/worker producing the analysis.
            result: The analysis result to save (dict, str, or other serializable).
        """
        try:
            self.analysis_storage.save_analysis(
                agent_name=agent_name,
                result=result,
                team_name=self.team_name,
                team_id=self.team_id,
            )
        except Exception as e:
            self.logger.warning(f"Failed to save analysis for {agent_name}: {e}")
    
    def clear_transient_files(self) -> None:
        """
        Clear analysis files from previous runs.
        
        Delegates to the analysis storage backend to ensure clean state
        for the next execution.
        """
        try:
            self.analysis_storage.clear_transient_files()
        except Exception as e:
            self.logger.warning(f"Failed to clear transient files: {e}")
    
    def get_manager_tools(self) -> list[typing.Callable] | None:
        return None
    
    def get_critic_config(self) -> dict[str, typing.Any] | None:
        if not self.ENABLE_DEBATE:
            return None
        return {
            "name": "critic",
            "instructions": "Critique the analysis, identify weaknesses, suggest improvements.",
        }
    
    def get_interrupt_config(self) -> dict[str, typing.Any]:
        return self._interrupt_on
    
    def get_skills(self) -> list[str]:
        return self._skills
    
    def get_agent_skills(self, agent_name: str) -> list[str] | None:
        """
        Get skills for a specific worker agent.
        Override to provide agent-specific skills.
        
        Args:
            agent_name: Name of the worker agent
            
        Returns:
            List of skill paths (e.g., ["./technical-analysis/"]) or None
        """
        return None
    
    def get_agent_skills_files(self, agent_name: str) -> dict[str, str] | None:
        """
        Get skill files for a specific worker agent.
        Override to provide agent-specific skill files.
        
        Args:
            agent_name: Name of the worker agent
            
        Returns:
            Dict mapping virtual paths to file content or None
        """
        skills_dir = self.get_skills_resources_dir()  # pylint: disable=assignment-from-none
        if not skills_dir:
            return None
        
        # Try to find agent-specific skills directory
        import os
        agent_skills_dir = os.path.join(skills_dir, agent_name)
        if os.path.isdir(agent_skills_dir):
            return deep_agent.create_skills_files_dict(agent_skills_dir)
        
        return None
    
    def get_skills_resources_dir(self) -> str | None:
        """
        Get the tentacle's resources/skills directory path.
        Override this to provide a custom skills directory.
        By default, returns None (no auto-discovery).
        
        Example implementation in tentacle:
            import os
            return os.path.join(os.path.dirname(__file__), "resources", "skills")
        """
        return None
    
    def _create_memory_backend(self) -> typing.Callable:
        def make_backend(runtime):
            if not deep_agent.DEEP_AGENTS_AVAILABLE or not CompositeBackend:
                return None
            return CompositeBackend(
                default=StateBackend(runtime),
                routes={
                    f"{constants.MEMORIES_PATH_PREFIX}": StoreBackend(runtime)
                }
            )
        return make_backend
    
    def _get_or_create_store(self) -> typing.Any:
        if self._store is None and deep_agent.DEEP_AGENTS_AVAILABLE:
            self._store = InMemoryStore()
        return self._store
    
    def _get_or_create_checkpointer(self) -> typing.Any:
        if self._checkpointer is None and deep_agent.DEEP_AGENTS_AVAILABLE:
            self._checkpointer = MemorySaver()
        return self._checkpointer
    
    def _build_deep_agent(self) -> typing.Any:
        if not deep_agent.DEEP_AGENTS_AVAILABLE:
            raise errors.DeepAgentNotAvailableError("deep_agents package is required")
        
        self.logger.debug(f"[{self.team_name}] Building deep agent team...")
        
        workers = self.get_worker_definitions()
        self._workers = workers
        
        # Build subagents with their individual skills
        subagents = []
        for w in workers:
            agent_name = w.get("name", "unnamed")
            
            # Get agent-specific skills
            agent_skills = self.get_agent_skills(agent_name)  # pylint: disable=assignment-from-none
            agent_files = self.get_agent_skills_files(agent_name)  # pylint: disable=assignment-from-none
            
            if agent_skills:
                self.logger.debug(f"[{self.team_name}] Loading skills for {agent_name}: {agent_skills}")
            if agent_files:
                self.logger.debug(f"[{self.team_name}] Loading {len(agent_files)} skill files for {agent_name}")
            
            # Prefer using the default_model when available (it can be a BaseChatModel instance).
            # If a worker overrides the model, build a concrete chat model instance so LangChain
            # does not need to infer a provider from a raw model string.
            subagent_model = w.get("model")
            if subagent_model is None:
                if self.ai_service is None:
                    subagent_model = self.model
                else:
                    subagent_model = None
            elif self.ai_service is not None and isinstance(subagent_model, str):
                subagent_model = self.ai_service.init_chat_model(model=subagent_model)

            subagent = deep_agent.build_dictionary_subagent(
                name=agent_name,
                instructions=w.get("instructions", ""),
                description=w.get("description"),
                tools=w.get("tools"),
                model=subagent_model,
                model_provider=w.get("model_provider") or (self.ai_service.ai_provider.value if self.ai_service else None),
                handoff_back=w.get("handoff_back", True),
                interrupt_on=w.get("interrupt_on"),
                skills=agent_skills,
                files=agent_files,
            )
            subagents.append(subagent)
        
        self.logger.debug(f"[{self.team_name}] Created {len(subagents)} worker subagents")
        
        critic_config = self.get_critic_config()
        if self.ENABLE_DEBATE and critic_config:
            critic_subagent = deep_agent.build_dictionary_subagent(
                name=critic_config.get("name", "critic"),
                instructions=critic_config.get("instructions", ""),
                description="Critiques analyses and suggests improvements",
                tools=critic_config.get("tools"),
                model_provider=critic_config.get("model_provider") or (self.ai_service.ai_provider.value if self.ai_service else None),
                handoff_back=True,
            )
            subagents.append(critic_subagent)
            self.logger.debug(f"[{self.team_name}] Added critic subagent for debate mode")
        
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
        
        self.logger.debug(f"[{self.team_name}] Initializing chat model from AI service")
        model = None
        if self.ai_service is not None:
            model = self.ai_service.init_chat_model(model=self.model)
        
        agent_kwargs: dict[str, typing.Any] = {
            "model": model,
            "system_prompt": team_instructions,
            "tools": self.get_manager_tools() or [],
            "store": self._get_or_create_store(),
            "backend": self._create_memory_backend(),
            "name": f"{self.team_name}_manager",
        }
        
        # Pass subagents directly - create_deep_agent will wrap them in SubAgentMiddleware
        if subagents:
            agent_kwargs["subagents"] = subagents
            self.logger.debug(f"[{self.team_name}] Passing {len(subagents)} subagents to create_deep_agent")
        
        # Auto-discover skills from tentacle's resources/skills directory for manager
        skills = self.get_skills()
        skills_dir = self.get_skills_resources_dir()  # pylint: disable=assignment-from-none
        
        if skills_dir:
            discovered = deep_agent.discover_skills(skills_dir)
            if discovered:
                skills = (skills or []) + discovered
                self.logger.debug(f"[{self.team_name}] Auto-discovered {len(discovered)} skills from {skills_dir}")
        
        if skills:
            agent_kwargs["skills"] = skills
            self.logger.debug(f"[{self.team_name}] Using skills: {skills}")
        
        interrupt_config = self.get_interrupt_config()
        if interrupt_config:
            checkpointer = self._get_or_create_checkpointer()
            agent_kwargs["interrupt_on"] = interrupt_config
            agent_kwargs["checkpointer"] = checkpointer
            self.logger.debug(f"[{self.team_name}] HITL enabled for tools: {list(interrupt_config.keys())}")
        
        self.logger.debug(f"[{self.team_name}] Deep agent team built successfully")
        return create_deep_agent(**agent_kwargs)
    
    def get_deep_agent(self, force_rebuild: bool = False) -> typing.Any:
        if self._deep_agent is None or force_rebuild:
            self._deep_agent = self._build_deep_agent()
        return self._deep_agent
    
    async def run(
        self,
        initial_data: typing.Dict[str, typing.Any],
        thread_id: str | None = None,
        skills_files: dict[str, str] | None = None,
    ) -> typing.Dict[str, typing.Any]:
        if not deep_agent.DEEP_AGENTS_AVAILABLE:
            return {"error": "Deep Agents not available"}
        
        agent = self.get_deep_agent()
        if agent is None:
            return {"error": "Failed to create Deep Agent"}
        
        message = self._build_input_message(initial_data)
        
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self._current_thread_id = thread_id
        
        config = {"configurable": {"thread_id": thread_id}}
        
        invoke_input: dict[str, typing.Any] = {
            "messages": [{"role": "user", "content": message}]
        }
        
        if skills_files:
            invoke_input["files"] = skills_files
        
        self.logger.debug(f"[{self.team_name}] Running team with input: {message[:100]}...")
        
        try:
            if self._enable_streaming:
                result = await self._run_with_streaming(agent, invoke_input, config)
            else:
                result = await agent.ainvoke(invoke_input, config=config)
            
            if self.is_interrupted(result):
                return result
            
            parsed_result = self._parse_result(result)
            
            if self.channel is not None:
                await self.push(parsed_result)
            
            self.logger.debug(f"[{self.team_name}] Team run complete")
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"[{self.team_name}] Error running Deep Agent team: {e}")
            return {"error": str(e)}
    
    async def _run_with_streaming(
        self,
        agent: typing.Any,
        invoke_input: dict,
        config: dict,
    ) -> dict:
        
        self.logger.debug(f"[{self.team_name}] Starting streaming run")
        
        async for event in agent.astream(
            invoke_input,
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                if node_name == "agent":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        # Handle both dict-like messages and LangChain message objects
                        tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
                        if tool_calls:
                            for tc in tool_calls:
                                tool_name = tc["name"] if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                                self.logger.debug(f"[{self.team_name}] 🔧 Calling tool: {tool_name}")
                        else:
                            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
                            if content:
                                content_preview = content[:100] if len(content) > 100 else content
                                self.logger.debug(f"[{self.team_name}] 💭 Agent thinking: {content_preview}...")
                
                elif node_name == "tools":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        msg_name = msg.get("name") if isinstance(msg, dict) else getattr(msg, "name", None)
                        if msg_name:
                            self.logger.debug(f"[{self.team_name}] ✅ Tool result from: {msg_name}")
            
            result = event  # pylint: disable=unused-variable
        
        state = await agent.aget_state(config)
        self.logger.debug(f"[{self.team_name}] Streaming complete")
        return {"messages": state.values.get("messages", [])}
    
    def is_interrupted(self, result: dict) -> bool:
        return constants.HITL_INTERRUPT_KEY in result
    
    def get_interrupt_info(self, result: dict) -> dict | None:
        if not self.is_interrupted(result):
            return None
        
        interrupts = result[constants.HITL_INTERRUPT_KEY]
        if not interrupts:
            return None
        
        interrupt_obj = interrupts[0]
        # Handle both dict and object types
        if isinstance(interrupt_obj, dict):
            return interrupt_obj.get('value', interrupt_obj)
        else:
            return getattr(interrupt_obj, 'value', interrupt_obj)
    
    async def resume_with_decisions(
        self,
        decisions: list[dict[str, typing.Any]],
        thread_id: str | None = None,
    ) -> dict:
        if not deep_agent.DEEP_AGENTS_AVAILABLE:
            return {"error": "Deep Agents not available"}
        
        agent = self.get_deep_agent()
        if agent is None:
            return {"error": "Deep Agent not available"}
        
        thread_id = thread_id or self._current_thread_id
        if thread_id is None:
            return {"error": "No thread_id for resume"}
        
        config = {"configurable": {"thread_id": thread_id}}
        
        self.logger.debug(f"[{self.team_name}] Resuming with {len(decisions)} decisions")
        
        try:
            result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config,
            )
            
            if self.is_interrupted(result):
                return result
            
            parsed_result = self._parse_result(result)
            
            if self.channel is not None:
                await self.push(parsed_result)
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"[{self.team_name}] Error resuming Deep Agent team: {e}")
            return {"error": str(e)}
    
    async def approve_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": constants.HITL_DECISION_APPROVE} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    async def reject_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": constants.HITL_DECISION_REJECT} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    def _build_input_message(self, initial_data: typing.Dict[str, typing.Any]) -> str:
        data_str = json.dumps(initial_data, indent=2, default=str)
        return f"""
Process the following data with your team:

{data_str}

Coordinate with your workers and provide a final synthesized result.
""".strip()
    
    def _parse_result(self, result: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        try:
            messages = result.get("messages", [])
            if not messages:
                return {"error": "No response from agent"}
            
            last_message = messages[-1]
            # Handle both dict and LangChain message objects
            if isinstance(last_message, dict):
                content = last_message.get("content", "")
            else:
                content = getattr(last_message, "content", str(last_message))
            
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            return {"result": content}
            
        except Exception as e:
            self.logger.error(f"Error parsing result: {e}")
            return {"error": str(e)}
    
    async def push(self, result: typing.Any) -> None:
        if self.channel is None:
            return
        
        for consumer in self.channel.get_consumers():
            await consumer.queue.put({
                "team_name": self.team_name,
                "team_id": self.team_id or "",
                "result": result,
            })
    
    def get_memory_path(self, memory_type: str = "data") -> str:
        return f"{constants.MEMORIES_PATH_PREFIX}{self.team_name}/{memory_type}"
