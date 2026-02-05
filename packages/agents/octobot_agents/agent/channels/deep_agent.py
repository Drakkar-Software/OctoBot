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
Deep Agent channel, consumer, and producer for LangChain Deep Agents integration.

Features:
- SubAgentMiddleware for manager delegation
- TodoListMiddleware for task planning
- CompositeBackend for long-term memory
- Dangling tool call repair
- Streaming support
- Debug logging for agent operations

See LangChain Deep Agents docs:
- https://docs.langchain.com/oss/python/deepagents/middleware
- https://docs.langchain.com/oss/python/deepagents/long-term-memory
- https://docs.langchain.com/oss/python/deepagents/harness
"""

import abc
import typing
import logging
import uuid

from octobot_agents.agent.channels.ai_agent import (
    AbstractAIAgentChannel,
    AbstractAIAgentChannelConsumer,
    AbstractAIAgentChannelProducer,
)
from octobot_agents.errors import DeepAgentNotAvailableError
from octobot_agents.constants import (
    MEMORIES_PATH_PREFIX,
    AGENT_NAME_KEY,
    HITL_DECISION_APPROVE,
    HITL_DECISION_EDIT,
    HITL_DECISION_REJECT,
    HITL_ALLOWED_DECISIONS,
    HITL_INTERRUPT_KEY,
    SKILLS_PATH_PREFIX,
    SKILLS_MANIFEST_FILE,
)
import octobot_services.services as services

logger = logging.getLogger(__name__)

try:
    from deepagents import create_deep_agent, CompiledSubAgent
    from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
    from langchain.agents.middleware import TodoListMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langgraph.store.memory import InMemoryStore
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    DEEP_AGENTS_AVAILABLE = True
except ImportError as e:
    DEEP_AGENTS_AVAILABLE = False
    logger.warning(f"deepagents not available - Deep Agent features disabled: {e}")


class AbstractDeepAgentChannel(AbstractAIAgentChannel):
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentChannelConsumer(AbstractAIAgentChannelConsumer):
    __metaclass__ = abc.ABCMeta
    
    def __init__(
        self,
        callback: typing.Optional[typing.Callable] = None,
        size: int = 0,
        priority_level: int = AbstractAIAgentChannel.DEFAULT_PRIORITY_LEVEL,
        expected_inputs: int = 1,
    ):
        super().__init__(
            callback=callback,
            size=size,
            priority_level=priority_level,
            expected_inputs=expected_inputs,
        )
        self.subagent_results: typing.Dict[str, typing.Any] = {}
    
    def add_subagent_result(self, subagent_name: str, result: typing.Any) -> None:
        self.subagent_results[subagent_name] = result
    
    def get_subagent_results(self) -> typing.Dict[str, typing.Any]:
        return self.subagent_results.copy()
    
    def clear_subagent_results(self) -> None:
        self.subagent_results.clear()


class AbstractDeepAgentChannelProducer(AbstractAIAgentChannelProducer, abc.ABC):
    """
    Producer for Deep Agents with supervisor pattern and subagent orchestration.
    
    Features:
    - SubAgentMiddleware for task delegation
    - TodoListMiddleware for planning
    - CompositeBackend with /memories/ for persistent storage
    - Dangling tool call repair
    - Streaming support
    - Debug logging
    """
    
    AGENT_CHANNEL: typing.Optional[typing.Type[AbstractDeepAgentChannel]] = None
    AGENT_CONSUMER: typing.Optional[typing.Type[AbstractDeepAgentChannelConsumer]] = None
    
    MAX_ITERATIONS: int = 10
    ENABLE_WRITE_TODOS: bool = True
    ENABLE_STREAMING: bool = False
    
    ENABLE_HITL: bool = False
    HITL_INTERRUPT_TOOLS: dict[str, typing.Any] = {}
    
    SKILLS_DIRS: list[str] = []
    
    def __init__(
        self,
        channel: typing.Optional[AbstractDeepAgentChannel],
        ai_service: typing.Optional[services.AbstractAIService] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        enable_memory: typing.Optional[bool] = None,
        store: typing.Any | None = None,
        checkpointer: typing.Any | None = None,
        skills: list[str] | None = None,
        interrupt_on: dict[str, typing.Any] | None = None,
        enable_streaming: bool | None = None,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_memory=enable_memory,
        )
        
        self.ai_service = ai_service
        
        self._store = store
        self._checkpointer = checkpointer
        self._deep_agent = None
        self._subagents: list[dict[str, typing.Any]] = []
        
        self._interrupt_on = interrupt_on or self.HITL_INTERRUPT_TOOLS
        self._skills = skills or self.SKILLS_DIRS
        self._enable_streaming = enable_streaming if enable_streaming is not None else self.ENABLE_STREAMING
        
        self._current_thread_id: str | None = None
    
    def get_subagents(self) -> list[dict[str, typing.Any]]:
        return []
    
    def get_compiled_subagents(self) -> list[typing.Any]:
        return []
    
    def get_skills(self) -> list[str]:
        return self._skills
    
    def get_agent_skills(self, agent_name: str) -> list[str] | None:
        """
        Get skills for a specific agent/subagent.
        Override to provide agent-specific skills.
        
        Args:
            agent_name: Name of the agent/subagent
            
        Returns:
            List of skill paths (e.g., ["./technical-analysis/"]) or None
        """
        return None
    
    def get_agent_skills_files(self, agent_name: str) -> dict[str, str] | None:
        """
        Get skill files for a specific agent/subagent.
        Override to provide agent-specific skill files.
        
        Args:
            agent_name: Name of the agent/subagent
            
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
            return create_skills_files_dict(agent_skills_dir)
        
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
    
    def get_interrupt_config(self) -> dict[str, typing.Any]:
        return self._interrupt_on
    
    def get_middleware(self) -> list[typing.Any]:
        """
        Get middleware list for this producer.
        
        Override to add custom middleware. Default includes:
        - TodoListMiddleware (if ENABLE_WRITE_TODOS)
        - SubAgentMiddleware with subagents
        """
        middleware = []
        
        if not DEEP_AGENTS_AVAILABLE:
            return middleware
        
        # Build middleware with deduplication and merging
        middleware_dict = {}  # Map middleware type to instance
        
        if self.ENABLE_WRITE_TODOS and TodoListMiddleware:
            middleware_type_name = TodoListMiddleware.__name__
            if middleware_type_name not in middleware_dict:
                middleware_dict[middleware_type_name] = TodoListMiddleware()
        
        subagents = self.get_subagents() + self.get_compiled_subagents()
        if subagents and SubAgentMiddleware:
            model = self.model
            if self.ai_service:
                model = self.ai_service.model or self.model
            middleware_type_name = SubAgentMiddleware.__name__
            
            if middleware_type_name in middleware_dict:
                # Merge subagents: append new subagents to existing ones
                existing = middleware_dict[middleware_type_name]
                try:
                    existing_subagents = existing.subagents
                    if existing_subagents:
                        # Only add subagents that aren't already present
                        existing_names = {s.get('name') if isinstance(s, dict) else getattr(s, 'name', None) for s in existing_subagents}
                        new_subagents = [s for s in subagents if (s.get('name') if isinstance(s, dict) else getattr(s, 'name', None)) not in existing_names]
                        if new_subagents:
                            existing.subagents = existing_subagents + new_subagents
                except AttributeError:
                    pass
            else:
                middleware_dict[middleware_type_name] = SubAgentMiddleware(
                    default_model=model,
                    default_tools=[],
                    subagents=subagents,
                )
        
        return list(middleware_dict.values())
    
    def _create_memory_backend(self) -> typing.Callable:
        """
        Create a CompositeBackend factory for long-term memory.
        
        Routes:
        - /memories/* -> StoreBackend (persistent)
        - else -> StateBackend (transient)
        """
        def make_backend(runtime):
            if not DEEP_AGENTS_AVAILABLE or not CompositeBackend:
                return None
            return CompositeBackend(
                default=StateBackend(runtime),
                routes={
                    f"{MEMORIES_PATH_PREFIX}": StoreBackend(runtime)
                }
            )
        return make_backend
    
    def _get_or_create_store(self) -> typing.Any:
        if self._store is None and DEEP_AGENTS_AVAILABLE:
            self._store = InMemoryStore()
        return self._store
    
    def _get_or_create_checkpointer(self) -> typing.Any:
        if self._checkpointer is None and DEEP_AGENTS_AVAILABLE:
            self._checkpointer = MemorySaver()
        return self._checkpointer
    
    def _build_deep_agent(
        self,
        additional_tools: list[typing.Callable] | None = None,
    ) -> typing.Any:
        if not DEEP_AGENTS_AVAILABLE:
            raise DeepAgentNotAvailableError("deep_agents package is required")
        
        logger.debug(f"[{self.name}] Building deep agent...")
        
        store = self._get_or_create_store()
        
        model = None
        if self.ai_service:
            logger.debug(f"[{self.name}] Initializing chat model from AI service")
            model = self.ai_service.init_chat_model(model=self.model)
        else:
            model = self.model
        
        agent_kwargs: dict[str, typing.Any] = {
            "model": model,
            "system_prompt": self.prompt,
            "tools": additional_tools or [],
            "store": store,
            "backend": self._create_memory_backend(),
        }
        
        middleware = self.get_middleware()
        if middleware:
            agent_kwargs["middleware"] = middleware
            logger.debug(f"[{self.name}] Using middleware: {[type(m).__name__ for m in middleware]}")
        
        # Auto-discover skills from tentacle's resources/skills directory
        skills = self.get_skills()
        skills_dir = self.get_skills_resources_dir()  # pylint: disable=assignment-from-none
        
        if skills_dir:
            discovered = discover_skills(skills_dir)
            if discovered:
                skills = (skills or []) + discovered
                logger.debug(f"[{self.name}] Auto-discovered {len(discovered)} skills from {skills_dir}")
        
        if skills:
            agent_kwargs["skills"] = skills
            logger.debug(f"[{self.name}] Using skills: {skills}")
        
        interrupt_config = self.get_interrupt_config()
        if interrupt_config:
            checkpointer = self._get_or_create_checkpointer()
            agent_kwargs["interrupt_on"] = interrupt_config
            agent_kwargs["checkpointer"] = checkpointer
            logger.debug(f"[{self.name}] HITL enabled for tools: {list(interrupt_config.keys())}")
        
        logger.debug(f"[{self.name}] Deep agent built successfully")
        return create_deep_agent(**agent_kwargs)
    
    def get_deep_agent(
        self,
        additional_tools: list[typing.Callable] | None = None,
        force_rebuild: bool = False,
    ) -> typing.Any:
        if self._deep_agent is None or force_rebuild:
            self._deep_agent = self._build_deep_agent(additional_tools)
        return self._deep_agent
    
    async def invoke_deep_agent(
        self,
        message: str,
        additional_tools: list[typing.Callable] | None = None,
        thread_id: str | None = None,
    ) -> dict:
        agent = self.get_deep_agent(additional_tools)
        if agent is None:
            return {"error": "Deep Agent not available"}
        
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self._current_thread_id = thread_id
        
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.debug(f"[{self.name}] Invoking deep agent with message: {message[:100]}...")
        
        try:
            if self._enable_streaming:
                return await self._invoke_with_streaming(agent, message, config)
            else:
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": message}]},
                    config=config,
                )
                logger.debug(f"[{self.name}] Deep agent invocation complete")
                return result
        except Exception as e:
            logger.error(f"[{self.name}] Error invoking Deep Agent: {e}")
            return {"error": str(e)}
    
    async def _invoke_with_streaming(
        self,
        agent: typing.Any,
        message: str,
        config: dict,
    ) -> dict:
        """Invoke agent with streaming, logging events as they occur."""
        result = None
        
        logger.debug(f"[{self.name}] Starting streaming invocation")
        
        async for event in agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                if node_name == "agent":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        tool_calls = msg.get("tool_calls")
                        if tool_calls:
                            for tc in tool_calls:
                                tool_name = tc["name"] if isinstance(tc, dict) else tc.name
                                logger.debug(f"[{self.name}] 🔧 Calling tool: {tool_name}")
                        elif msg.get("content"):
                            content = msg.get("content", "")
                            content_preview = content[:100] if len(content) > 100 else content
                            logger.debug(f"[{self.name}] 💭 Agent thinking: {content_preview}...")
                
                elif node_name == "tools":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        msg_name = msg.get("name")
                        if msg_name:
                            logger.debug(f"[{self.name}] ✅ Tool result from: {msg_name}")
            
            result = event
        
        state = await agent.aget_state(config)
        logger.debug(f"[{self.name}] Streaming complete")
        return {"messages": state.values.get("messages", [])}
    
    def is_interrupted(self, result: dict) -> bool:
        return HITL_INTERRUPT_KEY in result
    
    def get_interrupt_info(self, result: dict) -> dict | None:
        if not self.is_interrupted(result):
            return None
        
        interrupts = result[HITL_INTERRUPT_KEY]
        if not interrupts:
            return None
        
        return interrupts[0].get('value', interrupts[0])
    
    async def resume_with_decisions(
        self,
        decisions: list[dict[str, typing.Any]],
        thread_id: str | None = None,
    ) -> dict:
        if not DEEP_AGENTS_AVAILABLE:
            return {"error": "Deep Agents not available"}
        
        agent = self.get_deep_agent()
        if agent is None:
            return {"error": "Deep Agent not available"}
        
        thread_id = thread_id or self._current_thread_id
        if thread_id is None:
            return {"error": "No thread_id for resume"}
        
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.debug(f"[{self.name}] Resuming with {len(decisions)} decisions")
        
        try:
            result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config,
            )
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Error resuming Deep Agent: {e}")
            return {"error": str(e)}
    
    async def approve_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": HITL_DECISION_APPROVE} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    async def reject_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": HITL_DECISION_REJECT} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)


# ============================================================================
# Utility Functions
# ============================================================================

def create_memory_backend(
    memories_path_prefix: str = MEMORIES_PATH_PREFIX,
) -> typing.Any:
    if not DEEP_AGENTS_AVAILABLE:
        raise DeepAgentNotAvailableError("deep_agents is required for memory backend")
    
    return InMemoryStore()


def get_agent_memory_path(agent_name: str, memory_type: str = "data") -> str:
    return f"{MEMORIES_PATH_PREFIX}{agent_name}/{memory_type}"


def build_dictionary_subagent(
    name: str,
    instructions: str,
    description: str | None = None,
    tools: list[typing.Callable] | None = None,
    model: str | None = None,
    model_provider: str | None = None,
    handoff_back: bool = True,
    interrupt_on: dict[str, typing.Any] | None = None,
    middleware: list[typing.Any] | None = None,
    skills: list[str] | None = None,
    files: dict[str, str] | None = None,
) -> dict[str, typing.Any]:
    """Build a dictionary-based subagent definition.
    
    Args:
        name: Agent name
        instructions: System prompt/instructions
        description: Optional description for delegation
        tools: Optional list of tools
        model: Optional model override
        model_provider: Optional model provider (e.g., 'ollama', 'openai', 'anthropic')
        handoff_back: Whether agent can hand back to manager
        interrupt_on: HITL interrupt configuration
        middleware: Optional middleware list
        skills: Optional list of skill paths (e.g., ["./technical-analysis/"])
        files: Optional dict of virtual files (e.g., {"/skills/ta/SKILL.md": content})
    """
    subagent: dict[str, typing.Any] = {
        "name": name,
        "system_prompt": instructions,
    }
    
    if description:
        subagent["description"] = description
    else:
        subagent["description"] = instructions[:200] + "..." if len(instructions) > 200 else instructions
    
    if tools:
        subagent["tools"] = tools
    
    if model:
        subagent["model"] = model
    
    if model_provider:
        subagent["model_provider"] = model_provider
        
    if handoff_back:
        subagent["handoff_back"] = True
    
    if interrupt_on:
        subagent["interrupt_on"] = interrupt_on
    
    if middleware:
        subagent["middleware"] = middleware
    
    if skills:
        subagent["skills"] = skills
    
    if files:
        subagent["files"] = files
        
    return subagent


def build_compiled_subagent(
    name: str,
    description: str,
    runnable: typing.Any,
) -> typing.Any:
    if not DEEP_AGENTS_AVAILABLE or CompiledSubAgent is None:
        logger.error("Cannot create CompiledSubAgent - deep_agents not installed")
        return None
    
    return CompiledSubAgent(
        name=name,
        description=description,
        runnable=runnable,
    )


def build_subagents_from_agents(
    agents: list[dict[str, typing.Any]],
) -> list[dict[str, typing.Any]]:
    return [
        build_dictionary_subagent(
            name=agent.get("name", agent.get(AGENT_NAME_KEY, "unnamed")),
            instructions=agent.get("instructions", agent.get("system_prompt", agent.get("prompt", ""))),
            description=agent.get("description"),
            tools=agent.get("tools"),
            model=agent.get("model"),
            model_provider=agent.get("model_provider"),
            handoff_back=agent.get("handoff_back", True),
            interrupt_on=agent.get("interrupt_on"),
            middleware=agent.get("middleware"),
        )
        for agent in agents
    ]


def build_subagents_from_producers(
    producers: list[AbstractAIAgentChannelProducer],
    include_descriptions: bool = True,
) -> list[dict[str, typing.Any]]:
    subagents = []
    for producer in producers:
        description = None
        if include_descriptions:
            description = producer.__class__.__doc__ or f"Agent: {producer.name}"
            if len(description) > 200:
                description = description[:200] + "..."
        
        subagents.append(build_dictionary_subagent(
            name=producer.name,
            instructions=producer.prompt,
            description=description,
            model=producer.model,
            model_provider=producer.ai_service.ai_provider.value if producer.ai_service else None,
            handoff_back=True,
        ))
    
    return subagents


def create_deep_agent_safe(
    model: str | None = None,
    instructions: str = "",
    tools: list[typing.Callable] | None = None,
    subagents: list[dict[str, typing.Any]] | None = None,
    store: typing.Any | None = None,
    enable_todos: bool = True,
    **kwargs,
) -> typing.Any:
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create Deep Agent - deep_agents not installed")
        return None
    
    if store is None:
        store = create_memory_backend()
    
    middleware = []
    if enable_todos and TodoListMiddleware:
        middleware.append(TodoListMiddleware())
    if subagents and SubAgentMiddleware:
        middleware.append(SubAgentMiddleware(
            default_model=model,
            default_tools=[],
            subagents=subagents,
        ))
    
    def make_backend(runtime):
        return CompositeBackend(
            default=StateBackend(runtime),
            routes={f"{MEMORIES_PATH_PREFIX}": StoreBackend(runtime)}
        )
    
    return create_deep_agent(
        model=model,
        system_prompt=instructions,
        tools=tools or [],
        store=store,
        backend=make_backend,
        middleware=middleware if middleware else None,
        **kwargs,
    )


def create_supervisor_agent(
    name: str,
    instructions: str,
    subagents: list[dict[str, typing.Any]],
    model: str | None = None,
    tools: list[typing.Callable] | None = None,
    store: typing.Any | None = None,
    **kwargs,
) -> typing.Any:
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create supervisor - deep_agents not installed")
        return None
    
    supervisor_instructions = f"""
{instructions}

As a supervisor, you coordinate the following workers:
{', '.join(s.get('name', 'unnamed') for s in subagents)}

Use write_todos to plan your approach before delegating.
Delegate specific tasks to appropriate workers.
Synthesize their outputs into a coherent result.
""".strip()
    
    return create_deep_agent_safe(
        model=model,
        instructions=supervisor_instructions,
        tools=tools or [],
        subagents=subagents,
        store=store,
        **kwargs,
    )


def create_team_deep_agent(
    team_name: str,
    manager_instructions: str,
    workers: list[dict[str, typing.Any]],
    manager_tools: list[typing.Callable] | None = None,
    model: str | None = None,
    store: typing.Any | None = None,
    enable_debate: bool = False,
    critic_config: dict[str, typing.Any] | None = None,
    **kwargs,
) -> typing.Any:
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create team - deep_agents not installed")
        return None
    
    subagents = build_subagents_from_agents(workers)
    
    if enable_debate and critic_config:
        critic_subagent = build_dictionary_subagent(
            name=critic_config.get("name", "critic"),
            instructions=critic_config.get("instructions", "Critique the analysis..."),
            tools=critic_config.get("tools"),
            model_provider=critic_config.get("model_provider"),
            handoff_back=True,
        )
        subagents.append(critic_subagent)
    
    team_instructions = f"""
You are the manager of the {team_name} team.

{manager_instructions}

Your team members:
{chr(10).join(f"- {w.get('name', 'unnamed')}: {w.get('instructions', '')[:100]}..." for w in workers)}

Workflow:
1. Use write_todos to plan your approach
2. Delegate tasks to appropriate team members
3. Collect and synthesize their results
4. {"Run debate rounds with critic if needed" if enable_debate else "Provide final synthesized output"}
""".strip()
    
    return create_supervisor_agent(
        name=f"{team_name}_manager",
        instructions=team_instructions,
        subagents=subagents,
        model=model,
        tools=manager_tools,
        store=store,
        **kwargs,
    )


# ============================================================================
# Skills Utilities
# ============================================================================

def load_skill_from_file(skill_path: str) -> dict[str, typing.Any] | None:
    try:
        with open(skill_path, 'r') as f:
            content = f.read()
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])
                instructions = parts[2].strip()
                
                return {
                    "name": frontmatter.get("name", "unnamed-skill"),
                    "description": frontmatter.get("description", ""),
                    "instructions": instructions,
                    "path": skill_path,
                }
        
        return {
            "name": skill_path.split('/')[-2] if '/' in skill_path else "unnamed-skill",
            "description": "",
            "instructions": content,
            "path": skill_path,
        }
        
    except Exception as e:
        logger.error(f"Error loading skill from {skill_path}: {e}")
        return None


def discover_skills(skills_dir: str) -> list[str]:
    import os
    skill_paths = []
    
    try:
        if not os.path.isdir(skills_dir):
            return []
        
        for entry in os.listdir(skills_dir):
            skill_manifest = os.path.join(skills_dir, entry, SKILLS_MANIFEST_FILE)
            if os.path.isfile(skill_manifest):
                skill_paths.append(f"./{entry}/")
        
    except Exception as e:
        logger.error(f"Error discovering skills in {skills_dir}: {e}")
    
    return skill_paths


def create_skills_files_dict(skills_dir: str) -> dict[str, str]:
    import os
    files = {}
    
    try:
        if not os.path.isdir(skills_dir):
            return {}
        
        for entry in os.listdir(skills_dir):
            skill_folder = os.path.join(skills_dir, entry)
            if not os.path.isdir(skill_folder):
                continue
            
            for filename in os.listdir(skill_folder):
                file_path = os.path.join(skill_folder, filename)
                if os.path.isfile(file_path):
                    virtual_path = f"{SKILLS_PATH_PREFIX}{entry}/{filename}"
                    with open(file_path, 'r') as f:
                        files[virtual_path] = f.read()
        
    except Exception as e:
        logger.error(f"Error creating skills files dict: {e}")
    
    return files


# ============================================================================
# HITL Utilities
# ============================================================================

def create_interrupt_config(
    high_risk_tools: list[str] | None = None,
    medium_risk_tools: list[str] | None = None,
    low_risk_tools: list[str] | None = None,
) -> dict[str, typing.Any]:
    config = {}
    
    for tool_name in (high_risk_tools or []):
        config[tool_name] = {
            "allowed_decisions": [HITL_DECISION_APPROVE, HITL_DECISION_EDIT, HITL_DECISION_REJECT]
        }
    
    for tool_name in (medium_risk_tools or []):
        config[tool_name] = {
            "allowed_decisions": [HITL_DECISION_APPROVE, HITL_DECISION_REJECT]
        }
    
    for tool_name in (low_risk_tools or []):
        config[tool_name] = False
    
    return config


def build_hitl_decision(
    decision_type: str,
    edited_action: dict[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    if decision_type not in HITL_ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision type: {decision_type}. Must be one of {HITL_ALLOWED_DECISIONS}")
    
    decision: dict[str, typing.Any] = {"type": decision_type}
    
    if decision_type == HITL_DECISION_EDIT:
        if edited_action is None:
            raise ValueError("edited_action required for edit decision")
        decision["edited_action"] = edited_action
    
    return decision
