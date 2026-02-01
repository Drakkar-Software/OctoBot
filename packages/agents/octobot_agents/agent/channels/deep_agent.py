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

Provides:
- AbstractDeepAgentChannel: Channel for Deep Agent communication
- AbstractDeepAgentChannelConsumer: Consumer for Deep Agent outputs
- AbstractDeepAgentChannelProducer: Producer with Deep Agent orchestration
- Human-in-the-loop (HITL) support for tool approval workflows
- Skills support for extensible agent capabilities
- Subagent support for context isolation and specialized work
- Long-term memory via /memories/ path
- Utility functions for memory backend and subagent building

See LangChain Deep Agents docs:
- https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
- https://docs.langchain.com/oss/python/deepagents/subagents
- https://docs.langchain.com/oss/python/deepagents/long-term-memory
- https://docs.langchain.com/oss/python/deepagents/skills
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
from octobot_agents.utils.deep_agent_adapter import create_model_for_deep_agent
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
from octobot_agents.errors import DeepAgentNotAvailableError
import octobot_services.services as services

logger = logging.getLogger(__name__)

try:
    from deepagents import create_deep_agent, CompiledSubAgent
    from langgraph.store.memory import InMemoryStore
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    DEEP_AGENTS_AVAILABLE = True
except ImportError:
    DEEP_AGENTS_AVAILABLE = False
    create_deep_agent = None
    CompiledSubAgent = None
    InMemoryStore = None
    MemorySaver = None
    Command = None
    logger.warning("deepagents not available - Deep Agent features disabled")


class AbstractDeepAgentChannel(AbstractAIAgentChannel):
    """
    Channel for Deep Agent communication.
    
    Inherits from AbstractAIAgentChannel with Deep Agent specific functionality.
    """
    __metaclass__ = abc.ABCMeta


class AbstractDeepAgentChannelConsumer(AbstractAIAgentChannelConsumer):
    """
    Consumer for Deep Agent channels.
    
    Handles outputs from Deep Agent producers with subagent result aggregation.
    """
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
        """Add result from a subagent."""
        self.subagent_results[subagent_name] = result
    
    def get_subagent_results(self) -> typing.Dict[str, typing.Any]:
        """Get all subagent results."""
        return self.subagent_results.copy()
    
    def clear_subagent_results(self) -> None:
        """Clear subagent results."""
        self.subagent_results.clear()


class AbstractDeepAgentChannelProducer(AbstractAIAgentChannelProducer, abc.ABC):
    """
    Producer for Deep Agents with supervisor pattern and subagent orchestration.
    
    Extends AbstractAIAgentChannelProducer with:
    - Deep Agent creation and management
    - Subagent orchestration (dictionary-based and CompiledSubAgent)
    - Memory backend with /memories/ path
    - Supervisor pattern support
    - Human-in-the-loop (HITL) for tool approval
    - Skills support for extensible capabilities
    
    Subclasses should implement:
    - _get_default_prompt(): Return default system prompt
    - execute(): Main execution logic
    - get_subagents(): Return list of subagent definitions (optional)
    """
    
    AGENT_CHANNEL: typing.Optional[typing.Type[AbstractDeepAgentChannel]] = None
    AGENT_CONSUMER: typing.Optional[typing.Type[AbstractDeepAgentChannelConsumer]] = None
    
    # Deep Agent specific configuration
    MAX_ITERATIONS: int = 10
    ENABLE_WRITE_TODOS: bool = True
    
    # Human-in-the-loop configuration
    ENABLE_HITL: bool = False
    HITL_INTERRUPT_TOOLS: dict[str, typing.Any] = {}  # tool_name -> True or {"allowed_decisions": [...]}
    
    # Skills configuration
    SKILLS_DIRS: list[str] = []  # List of skill source paths
    
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
    ):
        """
        Initialize the Deep Agent producer.
        
        Args:
            channel: The channel this producer is registered to.
            ai_service: The LLM service instance.
            model: LLM model to use.
            max_tokens: Maximum tokens for response.
            temperature: Temperature for LLM randomness.
            enable_memory: Override class-level ENABLE_MEMORY setting.
            store: Optional memory store for Deep Agent.
            checkpointer: Optional checkpointer for HITL (required for interrupts).
            skills: Optional list of skill source paths.
            interrupt_on: Optional tool interrupt configuration for HITL.
        """
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_memory=enable_memory,
        )
        
        self.ai_service = ai_service
        
        # Deep Agent specific
        self._store = store
        self._checkpointer = checkpointer
        self._deep_agent = None
        self._subagents: list[dict[str, typing.Any]] = []
        
        # HITL configuration
        self._interrupt_on = interrupt_on or self.HITL_INTERRUPT_TOOLS
        
        # Skills configuration
        self._skills = skills or self.SKILLS_DIRS
        
        # Thread management for HITL
        self._current_thread_id: str | None = None
    
    def get_subagents(self) -> list[dict[str, typing.Any]]:
        """
        Get subagent definitions for this producer.
        
        Override in subclasses to define subagents.
        Dictionary-based subagents should have:
        - name: Unique identifier
        - description: What the subagent does
        - system_prompt: Instructions for the subagent
        - tools: Optional list of tool functions
        - model: Optional model override
        - interrupt_on: Optional HITL config for this subagent
        
        Returns:
            List of subagent definition dictionaries.
        """
        return []
    
    def get_compiled_subagents(self) -> list[typing.Any]:
        """
        Get CompiledSubAgent instances for complex workflows.
        
        Override to provide pre-built LangGraph graphs as subagents.
        
        Returns:
            List of CompiledSubAgent instances.
        """
        return []
    
    def get_skills(self) -> list[str]:
        """
        Get skill source paths for this producer.
        
        Override to provide custom skill directories.
        
        Returns:
            List of skill source paths.
        """
        return self._skills
    
    def get_interrupt_config(self) -> dict[str, typing.Any]:
        """
        Get interrupt configuration for HITL.
        
        Override to customize which tools require approval.
        
        Returns:
            Dict mapping tool names to interrupt configs.
        """
        return self._interrupt_on
    
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
    
    def _build_deep_agent(
        self,
        additional_tools: list[typing.Callable] | None = None,
    ) -> typing.Any:
        """
        Build and return a Deep Agent instance.
        
        Args:
            additional_tools: Extra tools to provide to the agent.
        
        Returns:
            Configured Deep Agent or None if not available.
        """
        if not DEEP_AGENTS_AVAILABLE:
            raise DeepAgentNotAvailableError("deep_agents package is required")
        
        # Gather all subagents
        dict_subagents = self.get_subagents()
        compiled_subagents = self.get_compiled_subagents()
        all_subagents = dict_subagents + compiled_subagents
        
        store = self._get_or_create_store()
        
        model = None
        if self.ai_service:
            model = create_model_for_deep_agent(self.ai_service, self.model)
        else:
            model = self.model
        
        # Build agent kwargs
        agent_kwargs: dict[str, typing.Any] = {
            "model": model,
            "system_prompt": self.prompt,
            "tools": additional_tools or [],
            "subagents": all_subagents,
            "store": store,
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
    
    def get_deep_agent(
        self,
        additional_tools: list[typing.Callable] | None = None,
        force_rebuild: bool = False,
    ) -> typing.Any:
        """
        Get the Deep Agent instance, creating if necessary.
        
        Args:
            additional_tools: Extra tools for the agent.
            force_rebuild: Force rebuilding the agent.
        
        Returns:
            Deep Agent instance.
        """
        if self._deep_agent is None or force_rebuild:
            self._deep_agent = self._build_deep_agent(additional_tools)
        return self._deep_agent
    
    async def invoke_deep_agent(
        self,
        message: str,
        additional_tools: list[typing.Callable] | None = None,
        thread_id: str | None = None,
    ) -> dict:
        """
        Invoke the Deep Agent with a message.
        
        Args:
            message: User message to send to the agent.
            additional_tools: Optional extra tools.
            thread_id: Optional thread ID for HITL state persistence.
        
        Returns:
            Agent response dictionary. If HITL interrupt triggered,
            contains "__interrupt__" key with pending actions.
        """
        agent = self.get_deep_agent(additional_tools)
        if agent is None:
            return {"error": "Deep Agent not available"}
        
        # Use provided thread_id or generate new one
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        self._current_thread_id = thread_id
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
            )
            return result
        except Exception as e:
            self.logger.error(f"Error invoking Deep Agent: {e}")
            return {"error": str(e)}
    
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
        Resume agent execution after HITL interrupt with user decisions.
        
        Each decision should be one of:
        - {"type": "approve"} - Execute tool with original args
        - {"type": "edit", "edited_action": {"name": "...", "args": {...}}} - Execute with modified args
        - {"type": "reject"} - Skip the tool call
        
        Args:
            decisions: List of decisions, one per interrupted action.
            thread_id: Thread ID to resume (uses current if not provided).
        
        Returns:
            Agent response dictionary.
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
            return result
        except Exception as e:
            self.logger.error(f"Error resuming Deep Agent: {e}")
            return {"error": str(e)}
    
    async def approve_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        """
        Convenience method to approve all pending HITL interrupts.
        
        Args:
            result: Result containing interrupts.
            thread_id: Optional thread ID.
        
        Returns:
            Agent response after approval.
        """
        interrupt_info = self.get_interrupt_info(result)
        if interrupt_info is None:
            return result
        
        action_requests = interrupt_info.get("action_requests", [])
        decisions = [{"type": HITL_DECISION_APPROVE} for _ in action_requests]
        
        return await self.resume_with_decisions(decisions, thread_id)
    
    async def reject_all_interrupts(self, result: dict, thread_id: str | None = None) -> dict:
        """
        Convenience method to reject all pending HITL interrupts.
        
        Args:
            result: Result containing interrupts.
            thread_id: Optional thread ID.
        
        Returns:
            Agent response after rejection.
        """
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
    """
    Create a simple memory backend with /memories/ path routing.
    
    Uses LangGraph's InMemoryStore with namespace routing:
    - /memories/* -> StoreBackend (persistent across sessions)
    - else -> StateBackend (transient within session)
    
    Args:
        memories_path_prefix: Path prefix for persistent memory.
    
    Returns:
        Configured InMemoryStore instance.
    
    Raises:
        DeepAgentNotAvailableError: If deep_agents is not installed.
    """
    if not DEEP_AGENTS_AVAILABLE:
        raise DeepAgentNotAvailableError("deep_agents is required for memory backend")
    
    return InMemoryStore()


def get_agent_memory_path(agent_name: str, memory_type: str = "data") -> str:
    """
    Build a memory path for a specific agent.
    
    Uses /memories/ prefix for persistent storage via the store backend.
    
    Args:
        agent_name: Name of the agent.
        memory_type: Type of memory (data, context, history, etc.).
    
    Returns:
        Full memory path string.
    """
    return f"{MEMORIES_PATH_PREFIX}{agent_name}/{memory_type}"


def build_dictionary_subagent(
    name: str,
    instructions: str,
    description: str | None = None,
    tools: list[typing.Callable] | None = None,
    model: str | None = None,
    handoff_back: bool = True,
    interrupt_on: dict[str, typing.Any] | None = None,
    middleware: list[typing.Any] | None = None,
) -> dict[str, typing.Any]:
    """
    Build a dictionary-based subagent definition for Deep Agents.
    
    Deep Agents use dictionary format for subagent definitions:
    {"name": "...", "description": "...", "system_prompt": "...", "tools": [...]}
    
    Args:
        name: Unique name for the subagent.
        instructions: System instructions/prompt for the agent.
        description: What this subagent does (for main agent to decide delegation).
        tools: Optional list of tool functions.
        model: Optional model override.
        handoff_back: Whether agent hands back to supervisor when done.
        interrupt_on: Optional HITL config for this subagent's tools.
        middleware: Optional list of middleware for custom behavior.
    
    Returns:
        Dictionary subagent definition.
    """
    subagent: dict[str, typing.Any] = {
        "name": name,
        "system_prompt": instructions,
    }
    
    # Description is important for the main agent to decide when to delegate
    if description:
        subagent["description"] = description
    else:
        # Generate description from instructions
        subagent["description"] = instructions[:200] + "..." if len(instructions) > 200 else instructions
    
    if tools:
        subagent["tools"] = tools
    
    if model:
        subagent["model"] = model
        
    if handoff_back:
        subagent["handoff_back"] = True
    
    if interrupt_on:
        subagent["interrupt_on"] = interrupt_on
    
    if middleware:
        subagent["middleware"] = middleware
        
    return subagent


def build_compiled_subagent(
    name: str,
    description: str,
    runnable: typing.Any,
) -> typing.Any:
    """
    Build a CompiledSubAgent from a pre-built LangGraph graph.
    
    Use this for complex workflows that need custom graph logic.
    The runnable must be a compiled LangGraph graph with a "messages" state key.
    
    Args:
        name: Unique name for the subagent.
        description: What this subagent does.
        runnable: A compiled LangGraph graph (must call .compile() first).
    
    Returns:
        CompiledSubAgent instance or None if not available.
    """
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
    """
    Convert a list of agent configs to Deep Agent subagent definitions.
    
    Args:
        agents: List of agent configuration dictionaries.
    
    Returns:
        List of dictionary subagent definitions.
    """
    return [
        build_dictionary_subagent(
            name=agent.get("name", agent.get(AGENT_NAME_KEY, "unnamed")),
            instructions=agent.get("instructions", agent.get("system_prompt", agent.get("prompt", ""))),
            description=agent.get("description"),
            tools=agent.get("tools"),
            model=agent.get("model"),
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
    """
    Convert a list of AI agent producers to Deep Agent subagent definitions.
    
    Uses the producer's name and prompt to build subagent definitions.
    
    Args:
        producers: List of AbstractAIAgentChannelProducer instances.
        include_descriptions: Whether to include auto-generated descriptions.
    
    Returns:
        List of dictionary subagent definitions.
    """
    subagents = []
    for producer in producers:
        description = None
        if include_descriptions:
            # Generate description from producer class docstring or name
            description = producer.__class__.__doc__ or f"Agent: {producer.name}"
            if len(description) > 200:
                description = description[:200] + "..."
        
        subagents.append(build_dictionary_subagent(
            name=producer.name,
            instructions=producer.prompt,
            description=description,
            model=producer.model,
            handoff_back=True,
        ))
    
    return subagents


def create_deep_agent_safe(
    model: str | None = None,
    instructions: str = "",
    tools: list[typing.Callable] | None = None,
    subagents: list[dict[str, typing.Any]] | None = None,
    store: typing.Any | None = None,
    **kwargs,
) -> typing.Any:
    """
    Safely create a Deep Agent with OctoBot defaults.
    
    Wraps create_deep_agent with default values and error handling.
    Returns None if deep_agents is not available.
    
    Args:
        model: LLM model name.
        instructions: System instructions for the agent.
        tools: Optional list of tool functions.
        subagents: Optional list of subagent definitions.
        store: Optional memory store (created if not provided).
        **kwargs: Additional arguments passed to create_deep_agent.
    
    Returns:
        Deep Agent instance or None if not available.
    """
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create Deep Agent - deep_agents not installed")
        return None
    
    if store is None:
        store = create_memory_backend()
    
    return create_deep_agent(
        model=model,
        instructions=instructions,
        tools=tools or [],
        subagents=subagents or [],
        store=store,
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
    """
    Create a supervisor agent that orchestrates subagents.
    
    This is the manager-as-supervisor pattern where the manager
    agent coordinates worker agents to complete tasks.
    
    Args:
        name: Name of the supervisor agent.
        instructions: Supervisor instructions.
        subagents: List of worker subagent definitions.
        model: Optional model override.
        tools: Additional tools for the supervisor.
        store: Memory store (created if not provided).
        **kwargs: Additional arguments.
    
    Returns:
        Configured supervisor Deep Agent.
    """
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create supervisor - deep_agents not installed")
        return None
    
    # Enhance instructions with orchestration guidance
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
    """
    Create a complete team as a Deep Agent with manager and workers.
    
    This is the main factory for creating OctoBot agent teams using
    the Deep Agent supervisor pattern.
    
    Args:
        team_name: Name of the team.
        manager_instructions: Instructions for the manager/supervisor.
        workers: List of worker agent definitions.
        manager_tools: Tools available to the manager.
        model: Model to use.
        store: Memory store (created if not provided).
        enable_debate: Whether to enable debate workflow.
        critic_config: Optional critic agent configuration for debate.
        **kwargs: Additional arguments.
    
    Returns:
        Configured team Deep Agent.
    """
    if not DEEP_AGENTS_AVAILABLE:
        logger.error("Cannot create team - deep_agents not installed")
        return None
    
    # Build subagents from worker definitions
    subagents = build_subagents_from_agents(workers)
    
    # Add critic if debate is enabled
    if enable_debate and critic_config:
        critic_subagent = build_dictionary_subagent(
            name=critic_config.get("name", "critic"),
            instructions=critic_config.get("instructions", "Critique the analysis..."),
            tools=critic_config.get("tools"),
            handoff_back=True,
        )
        subagents.append(critic_subagent)
    
    # Create supervisor with team context
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
    """
    Load a skill definition from a SKILL.md file.
    
    Skills are YAML frontmatter + markdown format:
    ---
    name: skill-name
    description: What the skill does
    ---
    # Skill Instructions
    ...
    
    Args:
        skill_path: Path to the SKILL.md file.
    
    Returns:
        Dict with name, description, and instructions, or None on error.
    """
    try:
        with open(skill_path, 'r') as f:
            content = f.read()
        
        # Parse YAML frontmatter
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
        
        # Fallback: treat entire file as instructions
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
    """
    Discover skill paths in a directory.
    
    Looks for SKILL.md files in subdirectories.
    
    Args:
        skills_dir: Root directory to search.
    
    Returns:
        List of skill source paths (relative).
    """
    import os
    skill_paths = []
    
    try:
        if not os.path.isdir(skills_dir):
            return []
        
        for entry in os.listdir(skills_dir):
            skill_manifest = os.path.join(skills_dir, entry, SKILLS_MANIFEST_FILE)
            if os.path.isfile(skill_manifest):
                # Return relative path for Deep Agents
                skill_paths.append(f"./{entry}/")
        
    except Exception as e:
        logger.error(f"Error discovering skills in {skills_dir}: {e}")
    
    return skill_paths


def create_skills_files_dict(skills_dir: str) -> dict[str, str]:
    """
    Create a files dict for seeding skills into StateBackend.
    
    When using StateBackend (default), skills are loaded by providing
    files in the invoke call. This function prepares that dict.
    
    Args:
        skills_dir: Root directory containing skill folders.
    
    Returns:
        Dict mapping virtual paths to file contents.
    """
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
    """
    Create an interrupt configuration for HITL based on risk levels.
    
    High risk: Allow approve, edit, reject
    Medium risk: Allow approve, reject (no editing)
    Low risk: No interrupts
    
    Args:
        high_risk_tools: Tools requiring full approval flow.
        medium_risk_tools: Tools requiring approval without edit.
        low_risk_tools: Tools that don't need approval.
    
    Returns:
        Dict mapping tool names to interrupt configs.
    """
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
    """
    Build an HITL decision response.
    
    Args:
        decision_type: One of "approve", "edit", "reject".
        edited_action: For "edit" type, the modified action with name and args.
    
    Returns:
        Decision dict for resume_with_decisions.
    """
    if decision_type not in HITL_ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision type: {decision_type}. Must be one of {HITL_ALLOWED_DECISIONS}")
    
    decision: dict[str, typing.Any] = {"type": decision_type}
    
    if decision_type == HITL_DECISION_EDIT:
        if edited_action is None:
            raise ValueError("edited_action required for edit decision")
        decision["edited_action"] = edited_action
    
    return decision
