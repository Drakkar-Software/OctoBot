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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypedDict, Union

import pydantic
from pydantic import BaseModel, ConfigDict, Field, model_validator

from octobot_agents import constants
from octobot_agents.errors import AgentError

if TYPE_CHECKING:
    from octobot_agents.team.channels.agents_team import AbstractAgentsTeamChannelProducer


# ============================================================================
# Base Model for JSON Schema Strict Mode Control
# ============================================================================

class AgentBaseModel(BaseModel):
    """
    Base Pydantic model for OctoBot agents with JSON schema strict mode control.
    
    Models can override __strict_json_schema__ to control strict mode:
    - False (default): Disable strict mode (for models with Union types)
    - True: Enable strict mode (for models without Union types)
    """
    __strict_json_schema__: bool = False


# ============================================================================
# Execution Plan Models
# ============================================================================

class AgentInstruction(AgentBaseModel):
    """Instruction to send to an agent via channel.modify()"""
    model_config = ConfigDict(extra="forbid")
    
    modification_type: str  # One of MODIFICATION_ADDITIONAL_INSTRUCTIONS, MODIFICATION_CUSTOM_PROMPT, etc.
    value: Union[str, Dict[str, typing.Any]]  # The instruction content (string for prompts, dict for hints)


class DebatePhaseConfig(AgentBaseModel):
    """Configuration for a debate phase: debators take turns, judge decides continue or exit."""
    model_config = ConfigDict(extra="forbid")

    debator_agent_names: List[str]  # Agent names that debate (e.g. Bull, Bear)
    judge_agent_name: str  # Agent name of the judge that decides continue/exit
    max_rounds: int = 3  # Maximum debate rounds before forcing exit


class JudgeDecision(AgentBaseModel):
    """Result of a judge agent execute(): continue or exit the debate, with reasoning and optional summary."""
    model_config = ConfigDict(extra="forbid")

    decision: str  # JudgeDecisionType.CONTINUE.value or JudgeDecisionType.EXIT.value
    reasoning: str
    summary: Optional[str] = None  # When decision is exit, concise synthesis; when continue, None


class ExecutionStep(AgentBaseModel):
    """Single step in the execution plan"""
    model_config = ConfigDict(extra="forbid")

    # Agent name may be omitted for debate steps (we'll fill a default).
    agent_name: Optional[str] = None
    # Allow instructions as either structured AgentInstruction objects or simple strings
    instructions: Optional[Union[List[AgentInstruction], List[str]]] = None  # Instructions to send before execution
    wait_for: Optional[List[str]] = None  # Agent names to wait for before executing
    skip: bool = False  # Skip this agent in this iteration
    # Debate step: when step_type is StepType.DEBATE.value, use debate_config instead of single agent
    step_type: Optional[str] = None  # StepType.AGENT.value (default) or StepType.DEBATE.value
    debate_config: Optional[DebatePhaseConfig] = None  # Required when step_type == StepType.DEBATE.value

    @pydantic.model_validator(mode="after")
    def validate_and_normalize(self) -> "ExecutionStep":
        """Normalize and validate step after construction.
        
        - For debate steps, set default agent_name if missing.
        - Convert plain string instructions into AgentInstruction objects.
        - Enforce agent_name requirement for non-debate steps.
        """
        # Fill default agent_name for debate steps
        if self.step_type == "debate" and not self.agent_name:
            if self.debate_config and getattr(self.debate_config, "judge_agent_name", None):
                self.agent_name = f"debate_{self.debate_config.judge_agent_name}"
            else:
                self.agent_name = "debate_phase"

        # Require agent_name for agent steps
        if self.step_type in (None, "agent") and not self.agent_name:
            raise ValueError("agent_name is required for agent steps")

        # Normalize instructions: convert plain strings to AgentInstruction
        if self.instructions:
            normalized: List[AgentInstruction] = []
            for instr in self.instructions:
                if isinstance(instr, str):
                    normalized.append(
                        AgentInstruction(
                            modification_type=constants.MODIFICATION_ADDITIONAL_INSTRUCTIONS,
                            value=instr,
                        )
                    )
                else:
                    normalized.append(instr)
            self.instructions = normalized

        return self


class ExecutionPlan(AgentBaseModel):
    """Complete execution plan - returned by plan-driven AI managers like AIPlanTeamManagerAgent"""
    model_config = ConfigDict(extra="forbid")
    
    steps: List[ExecutionStep]
    loop: bool = False  # Whether to loop execution
    loop_condition: Optional[str] = None  # Condition description for looping
    max_iterations: Optional[int] = None  # Maximum loop iterations
    
    @classmethod
    def model_validate_or_self(cls, data: Any) -> "ExecutionPlan":
        """
        Validate dict to model, or return model if already validated.
        
        Args:
            data: Either a dict to validate or an ExecutionPlan instance.
            
        Returns:
            ExecutionPlan model instance.
        """
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)
    
    def to_dict(self) -> dict:
        """
        Convert to dict.
        
        Returns:
            Dict representation of the execution plan.
        """
        try:
            return self.model_dump()
        except AttributeError:
            # Fallback for Pydantic v1
            return self.dict()


# ============================================================================
# Tools-driven Manager Models
# ============================================================================

class ManagerToolCall(AgentBaseModel):
    """Tool call from LLM in tools-driven manager."""
    model_config = ConfigDict(extra="forbid")
    
    tool_name: str  # Name of the tool to call (e.g., "run_agent", "run_debate", "finish")
    arguments: Dict[str, Any]  # Arguments for the tool call


class RunAgentArgs(AgentBaseModel):
    """Arguments for run_agent tool."""
    model_config = ConfigDict(extra="forbid")
    
    # Allow agent_name to be optional here; manager may fill defaults or validate later.
    agent_name: Optional[str] = None  # Name of the agent to run
    instructions: Optional[Union[List[AgentInstruction], List[str]]] = None  # Instructions to send before execution
    
    @model_validator(mode="before")
    @classmethod
    def normalize_instructions(cls, data: Any) -> Any:
        if isinstance(data, dict) and "instructions" in data:
            instructions = data["instructions"]
            # If instructions is a string, wrap it in a list
            if isinstance(instructions, str):
                data["instructions"] = [instructions]
        return data


class RunDebateArgs(AgentBaseModel):
    """Arguments for run_debate tool."""
    model_config = ConfigDict(extra="forbid")
    
    debator_agent_names: List[str]  # Agent names that debate
    judge_agent_name: str  # Agent name of the judge
    max_rounds: int = 3  # Maximum debate rounds


class ManagerState(AgentBaseModel):
    """State maintained during tools-driven manager execution."""
    model_config = ConfigDict(extra="forbid")
    
    completed_agents: List[str]  # Names of agents that have been executed
    results: Dict[str, Any]  # Results from completed agents
    initial_data: Dict[str, Any]  # Original input data
    tool_call_history: List[ManagerToolCall]  # History of tool calls made


class ManagerResult(AgentBaseModel):
    """Result returned by tools-driven manager after execution."""
    model_config = ConfigDict(extra="forbid")
    
    completed_agents: List[str]  # Names of agents that were executed
    results: Dict[str, Any]  # Results from completed agents (agent_name -> result)
    tool_calls_used: int  # Number of tool calls made during execution


# ============================================================================
# Critic Models
# ============================================================================

class AgentImprovement(AgentBaseModel):
    """Improvements needed for a specific agent."""
    __strict_json_schema__ = True
    
    agent_name: str  # Name of the agent
    improvements: List[str]  # Specific improvements for this agent
    issues: List[str]  # Agent-specific issues
    errors: List[str]  # Agent-specific errors
    reasoning: str  # Why this agent needs improvement
    
    @classmethod
    def model_validate_or_self(cls, data: Any) -> "AgentImprovement":
        """
        Validate dict to model, or return model if already validated.
        
        Args:
            data: Either a dict to validate or an AgentImprovement instance.
            
        Returns:
            AgentImprovement model instance.
        """
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)


class CriticAnalysis(AgentBaseModel):
    """Analysis result from CriticAgent."""
    __strict_json_schema__ = True
    
    issues: List[str]  # General problems found (team-level)
    errors: List[str]  # General errors encountered (team-level)
    inconsistencies: List[str]  # Inconsistencies detected (team-level)
    optimizations: List[str]  # General optimization opportunities (team-level)
    summary: str  # Overall analysis summary
    agent_improvements: Dict[str, AgentImprovement]  # Agent-specific improvements
    # Key: agent_name, Value: AgentImprovement
    # Only includes agents that need improvements
    # If agent not in dict, no improvements needed for that agent
    
    @classmethod
    def model_validate_or_self(cls, data: Any) -> "CriticAnalysis":
        """
        Validate dict to model, or return model if already validated.
        
        Args:
            data: Either a dict to validate or a CriticAnalysis instance.
            
        Returns:
            CriticAnalysis model instance.
        """
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)
    
    def get_agent_improvements(self) -> Dict[str, AgentImprovement]:
        """
        Get agent improvements.
        
        Returns:
            Dict mapping agent names to AgentImprovement objects.
        """
        return self.agent_improvements
    
    def get_summary(self) -> str:
        """
        Get summary.
        
        Returns:
            Summary string.
        """
        return self.summary
    
    def get_issues(self) -> List[str]:
        """
        Get issues.
        
        Returns:
            List of issue strings.
        """
        return self.issues


# ============================================================================
# Memory Models
# ============================================================================

class MemoryOperation(AgentBaseModel):
    """Result of a memory operation."""
    success: bool
    operations: List[str]  # ["generated", "merged", "updated", "removed", "grouped"]
    memory_ids: List[str]  # UUIDs of affected memories (across all agents)
    agent_updates: Dict[str, List[str]]  # Map of agent_name -> list of memory_ids updated for that agent
    agents_processed: List[str]  # List of agent names that were processed
    agents_skipped: List[str]  # List of agent names that were skipped (no improvements needed)
    message: str  # Description of what happened


class MemoryStorageModel(AgentBaseModel):
    """
    Pydantic model for memory storage with enforced structure and length limits.
    
    Ensures memories contain concise, precise instructions/actions/advice.
    """
    title: str = pydantic.Field(
        ...,
        min_length=1,
        max_length=constants.MEMORY_TITLE_MAX_LENGTH,
        description=f"Short, clear title summarizing the memory (max {constants.MEMORY_TITLE_MAX_LENGTH} chars)"
    )
    context: str = pydantic.Field(
        ...,
        min_length=1,
        max_length=constants.MEMORY_CONTEXT_MAX_LENGTH,
        description=f"Context explaining what problem this addresses (max {constants.MEMORY_CONTEXT_MAX_LENGTH} chars)"
    )
    content: str = pydantic.Field(
        ...,
        min_length=1,
        max_length=constants.MEMORY_CONTENT_MAX_LENGTH,
        description=f"Concise, precise instructions/actions/advice (max {constants.MEMORY_CONTENT_MAX_LENGTH} chars). Should be summarized if longer."
    )
    category: str = pydantic.Field(
        default=constants.DEFAULT_CATEGORY,
        description="Memory category"
    )
    tags: typing.List[str] = pydantic.Field(
        default_factory=list,
        description="Tags for categorization"
    )
    importance_score: float = pydantic.Field(
        default=constants.DEFAULT_IMPORTANCE_SCORE,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0-1.0)"
    )
    confidence_score: float = pydantic.Field(
        default=constants.DEFAULT_CONFIDENCE_SCORE,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    
    @pydantic.field_validator('title', 'context', 'content')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not just whitespace."""
        if not v or not v.strip():
            raise AgentError("Field cannot be empty or whitespace only")
        return v.strip()
    
    @pydantic.field_validator('content')
    @classmethod
    def validate_content_format(cls, v: str) -> str:
        """Ensure content is concise and actionable."""
        # Remove excessive whitespace
        v = ' '.join(v.split())
        return v


class MemoryInstruction(AgentBaseModel):
    """Instruction structure for a single memory."""
    title: str = pydantic.Field(
        ...,
        min_length=1,
        max_length=constants.MEMORY_TITLE_MAX_LENGTH,
        description=f"Short, clear title (max {constants.MEMORY_TITLE_MAX_LENGTH} chars)"
    )
    structured_actions: typing.List[str] = pydantic.Field(
        default_factory=list,
        description="Short, direct command-like actions (imperative format)"
    )
    guidance: typing.Optional[str] = pydantic.Field(
        default=None,
        max_length=100,
        description="Optional very short guidance (max 100 chars, only if needed)"
    )
    context: str = pydantic.Field(
        ...,
        min_length=1,
        max_length=constants.MEMORY_CONTEXT_MAX_LENGTH,
        description=f"Short context about what problem this addresses (max {constants.MEMORY_CONTEXT_MAX_LENGTH} chars)"
    )
    
    def build_content(self) -> str:
        """
        Build content string as simple command list - no headers, just direct commands.
        
        Ensures content does not exceed MEMORY_CONTENT_MAX_LENGTH.
        Format: Simple list of commands, one per line, no numbering or headers.
        """
        content_parts = []
        
        # Format as simple command list - no headers, remove numbering
        for action in self.structured_actions:
            # Remove numbering if present (e.g., "1. ", "2. "), make imperative
            action_clean = action.lstrip("0123456789. ").strip()
            if action_clean:
                content_parts.append(action_clean)
        
        # Only add guidance if very short (one sentence max)
        if self.guidance and len(self.guidance) < 100:
            guidance_clean = self.guidance.strip()
            if guidance_clean:
                content_parts.append(guidance_clean)
        
        content = "\n".join(content_parts) if content_parts else "Follow instructions"
        
        # Truncate if exceeds limit (shouldn't happen if LLM follows instructions, but safety check)
        if len(content) > constants.MEMORY_CONTENT_MAX_LENGTH:
            truncated = content[:constants.MEMORY_CONTENT_MAX_LENGTH]
            # Try to truncate at line boundary (prefer) or sentence boundary
            last_newline = truncated.rfind('\n')
            last_period = truncated.rfind('.')
            last_break = max(last_newline, last_period)
            if last_break > constants.MEMORY_CONTENT_MAX_LENGTH * 0.7:
                content = truncated[:last_break + 1].strip()
            else:
                content = truncated.strip()
        
        return content
    
    @classmethod
    def model_validate_or_self(cls, data: typing.Any) -> "MemoryInstruction":
        """Validate dict to model, or return model if already validated."""
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)


class AgentMemoryInstruction(AgentBaseModel):
    """LLM response structure for agent memory instructions."""
    __strict_json_schema__ = True
    
    agent_name: str
    instructions: MemoryInstruction
    
    @classmethod
    def model_validate_or_self(cls, data: typing.Any) -> "AgentMemoryInstruction":
        """Validate dict to model, or return model if already validated."""
        if isinstance(data, cls):
            return data
        return cls.model_validate(data)


class AgentMemoryInstructionsList(AgentBaseModel):
    """Wrapper for list of agent memory instructions."""
    __strict_json_schema__ = True
    
    instructions: typing.List[AgentMemoryInstruction]



class ManagerInput(TypedDict, total=False):
    """Input data structure for manager agent execute() method."""
    team_producer: "AbstractAgentsTeamChannelProducer"
    initial_data: Dict[str, Any]
    instructions: Optional[str]


class CriticInput(TypedDict, total=False):
    """Input data structure for critic agent execute() method."""
    team_producer: "AbstractAgentsTeamChannelProducer"
    execution_plan: "ExecutionPlan"
    execution_results: Dict[str, Any]
    agent_outputs: Dict[str, Any]
    execution_metadata: Dict[str, Any]


class JudgeInput(TypedDict, total=False):
    """Input data structure for judge agent execute() method (debate step)."""
    debate_history: List[Dict[str, Any]]  # List of {agent_name, message, round}
    debator_agent_names: List[str]
    current_round: int
    max_rounds: int
    _initial_state: Dict[str, Any]  # Optional context from team initial_data


class MemoryInput(TypedDict, total=False):
    """Input data structure for memory agent execute() method."""
    critic_analysis: "CriticAnalysis"
    agent_outputs: Dict[str, Any]
    execution_metadata: Dict[str, Any]


class SubagentConfig(AgentBaseModel):
    """Configuration for a Deep Agent subagent."""
    model_config = ConfigDict(extra="forbid")
    
    name: str = pydantic.Field(..., description="Unique name for the subagent")
    instructions: str = pydantic.Field(..., description="System instructions for the subagent")
    tools: Optional[List[str]] = pydantic.Field(default=None, description="Tool names available to subagent")
    model: Optional[str] = pydantic.Field(default=None, description="Model override")
    handoff_back: bool = pydantic.Field(default=True, description="Whether to hand back to supervisor")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Deep Agents."""
        result: Dict[str, Any] = {
            "name": self.name,
            "instructions": self.instructions,
        }
        if self.tools:
            result["tools"] = self.tools
        if self.model:
            result["model"] = self.model
        if self.handoff_back:
            result["handoff_back"] = True
        return result


class MemoryEntry(AgentBaseModel):
    """A single memory entry for Deep Agent persistent storage."""
    model_config = ConfigDict(extra="forbid")
    
    key: str = pydantic.Field(..., description="Memory key/path")
    value: Any = pydantic.Field(..., description="Memory value")
    timestamp: Optional[str] = pydantic.Field(default=None, description="ISO timestamp")
    metadata: Optional[Dict[str, Any]] = pydantic.Field(default=None, description="Additional metadata")


class TodoItem(AgentBaseModel):
    """A todo item for Deep Agent write_todos planning."""
    model_config = ConfigDict(extra="forbid")
    
    task: str = pydantic.Field(..., description="Task description")
    status: str = pydantic.Field(default="pending", description="Task status: pending, in_progress, done")
    assigned_to: Optional[str] = pydantic.Field(default=None, description="Subagent name assigned to task")
    priority: int = pydantic.Field(default=1, description="Priority 1-5 (1=highest)")
    depends_on: Optional[List[str]] = pydantic.Field(default=None, description="Task dependencies")


class DeepAgentResult(AgentBaseModel):
    """Result from Deep Agent execution."""
    model_config = ConfigDict(extra="forbid")
    
    output: Any = pydantic.Field(..., description="Agent output/response")
    iterations: int = pydantic.Field(default=0, description="Number of reasoning iterations")
    subagents_called: List[str] = pydantic.Field(default_factory=list, description="Subagents that were invoked")
    tools_called: List[str] = pydantic.Field(default_factory=list, description="Tools that were called")
    memory_operations: int = pydantic.Field(default=0, description="Number of memory read/write operations")
    
    @classmethod
    def from_agent_output(cls, output: Any, metadata: Optional[Dict[str, Any]] = None) -> "DeepAgentResult":
        """Create result from raw agent output."""
        metadata = metadata or {}
        return cls(
            output=output,
            iterations=metadata.get("iterations", 0),
            subagents_called=metadata.get("subagents_called", []),
            tools_called=metadata.get("tools_called", []),
            memory_operations=metadata.get("memory_operations", 0),
        )


class TeamExecutionResult(AgentBaseModel):
    """Result from a complete team execution using Deep Agents."""
    model_config = ConfigDict(extra="forbid")
    
    team_name: str = pydantic.Field(..., description="Name of the team")
    final_output: Any = pydantic.Field(..., description="Final synthesized output")
    worker_results: Dict[str, DeepAgentResult] = pydantic.Field(
        default_factory=dict, 
        description="Results from each worker agent"
    )
    debate_results: Optional[Dict[str, Any]] = pydantic.Field(
        default=None, 
        description="Results from debate phase if enabled"
    )
    total_iterations: int = pydantic.Field(default=0, description="Total iterations across all agents")
    execution_time_ms: Optional[float] = pydantic.Field(default=None, description="Total execution time")
    
    def get_worker_output(self, worker_name: str) -> Optional[Any]:
        """Get output from a specific worker."""
        if worker_name in self.worker_results:
            return self.worker_results[worker_name].output
        return None


class SupervisorState(AgentBaseModel):
    """State maintained by supervisor during team orchestration."""
    model_config = ConfigDict(extra="forbid")
    
    pending_workers: List[str] = pydantic.Field(default_factory=list, description="Workers not yet called")
    completed_workers: List[str] = pydantic.Field(default_factory=list, description="Workers that completed")
    worker_outputs: Dict[str, Any] = pydantic.Field(default_factory=dict, description="Outputs from workers")
    current_todos: List[TodoItem] = pydantic.Field(default_factory=list, description="Current todo list")
    debate_round: int = pydantic.Field(default=0, description="Current debate round if in debate")
    phase: str = pydantic.Field(default="planning", description="Current phase: planning, delegating, synthesizing, debating")
