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
Abstract agents team channel classes for orchestrating teams of agents.

Teams follow the same channel pattern as individual agents, enabling:
- Composable teams (teams can consume from other teams)
- DAG-based agent relationships
"""
import abc
import typing
from collections import defaultdict

import octobot_commons.logging as logging

from octobot_agents.constants import AGENT_NAME_KEY, AGENT_ID_KEY, RESULT_KEY
from octobot_agents.agent import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
    AbstractAIAgentChannelProducer,
)
from octobot_agents.team.manager import AbstractTeamManagerAgent
from octobot_agents.team.critic import AbstractCriticAgent
from octobot_agents.team.judge import AbstractJudgeAgent
from octobot_agents.agent.memory.channels import AbstractMemoryAgent
from octobot_agents.enums import JudgeDecisionType, StepType
from octobot_agents.errors import MissingManagerError
import octobot_agents.models as models
from octobot_agents.constants import (
    MODIFICATION_ADDITIONAL_INSTRUCTIONS,
    MODIFICATION_CUSTOM_PROMPT,
    MODIFICATION_EXECUTION_HINTS,
)
import octobot_services.services.abstract_ai_service as abstract_ai_service

class AbstractAgentsTeamChannelConsumer(AbstractAgentChannelConsumer):
    """
    Consumer for team outputs.
    
    Can be used to consume results from a team's final output channel.
    """
    __metaclass__ = abc.ABCMeta


class AbstractAgentsTeamChannelProducer(AbstractAgentChannelProducer, abc.ABC):
    """
    Base producer for agent teams with common DAG logic.
    
    This class provides:
    - DAG computation from relations
    - Entry/terminal agent identification
    - Topological ordering for execution
    
    Subclasses implement different execution modes:
    - AbstractSyncAgentsTeamChannelProducer: Direct one-shot execution
    - AbstractLiveAgentsTeamChannelProducer: Channel-based long-running execution
    
    Relation semantics:
    - relations = [(A, B), ...] where A and B are Channel types
    - Means: A's producer output feeds into B's producer input
    """
    
    # Override in subclasses with dedicated channel and consumer classes
    TEAM_CHANNEL: typing.Optional[typing.Type["AbstractAgentsTeamChannel"]] = None
    TEAM_CONSUMER: typing.Optional[typing.Type[AbstractAgentsTeamChannelConsumer]] = None
    TEAM_NAME: str = "AbstractAgentsTeam"
    
    # Class attributes for critic, memory, manager, and judge agent classes
    # Teams can override these to specify which implementations to use
    # If None, the feature is disabled
    CriticAgentClass: typing.Optional[typing.Type["AbstractCriticAgent"]] = None
    MemoryAgentClass: typing.Optional[typing.Type["AbstractMemoryAgent"]] = None
    ManagerAgentClass: typing.Optional[typing.Type[AbstractTeamManagerAgent]] = None
    JudgeAgentClass: typing.Optional[typing.Type["AbstractJudgeAgent"]] = None

    def __init__(
        self,
        channel: typing.Optional["AbstractAgentsTeamChannel"],
        agents: typing.List[AbstractAIAgentChannelProducer],
        relations: typing.List[typing.Tuple[typing.Type[AbstractAgentChannel], typing.Type[AbstractAgentChannel]]],
        ai_service: abstract_ai_service.AbstractAIService,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
        manager: typing.Optional[AbstractTeamManagerAgent] = None,
        self_improving: bool = False,
        critic_agent: typing.Optional[AbstractCriticAgent] = None,
        memory_agent: typing.Optional[AbstractMemoryAgent] = None,
        judge_agent: typing.Optional[AbstractJudgeAgent] = None,
    ):
        """
        Initialize the agent team producer.

        Args:
            channel: The team's output channel (optional).
            agents: List of agent producer instances.
            relations: List of (SourceAgentChannel, TargetAgentChannel) edges.
                       e.g., [(SignalAIAgentChannel, RiskAIAgentChannel)] means
                       RiskAgent receives input from SignalAgent.
            ai_service: The AI service for LLM calls.
            team_name: Name of the team (defaults to TEAM_NAME).
            team_id: Unique identifier for this team instance.
            manager: Optional team manager agent. If None, uses ManagerAgentClass if defined.
                     Raises MissingManagerError if both are None.
            self_improving: Whether to enable automatic critic and memory update after execution.
            critic_agent: Optional critic agent. If None and self_improving=True, uses CriticAgentClass if defined.
            memory_agent: Optional memory agent. If None and self_improving=True, uses MemoryAgentClass if defined.
            judge_agent: Optional judge agent for debate phases. If None, uses JudgeAgentClass if defined.
        """
        super().__init__(channel)
        self.agents = agents
        self.relations = relations
        self.ai_service = ai_service
        self.team_name = team_name or self.TEAM_NAME
        self.team_id = team_id or ""
        self.logger = logging.get_logger(f"{self.__class__.__name__}{f'[{self.team_id}]' if self.team_id else ''}")
        
        # Initialize manager - use class attribute if not provided
        if manager is None:
            if self.ManagerAgentClass is not None:
                self.manager = self.ManagerAgentClass(channel=None)
            else:
                raise MissingManagerError(
                    f"{self.__class__.__name__} requires a manager. "
                    f"Either set ManagerAgentClass class attribute or pass manager parameter."
                )
        else:
            self.manager = manager
        
        # Initialize self-improving mechanism
        self.self_improving = self_improving
        if self_improving:
            if critic_agent is None:
                if self.CriticAgentClass is not None:
                    self.critic_agent = self.CriticAgentClass(channel=None)
                else:
                    self.critic_agent = None
            else:
                self.critic_agent = critic_agent
            
            if memory_agent is None:
                if self.MemoryAgentClass is not None:
                    self.memory_agent = self.MemoryAgentClass(channel=None)
                else:
                    self.memory_agent = None
            else:
                self.memory_agent = memory_agent
        else:
            self.critic_agent = critic_agent
            self.memory_agent = memory_agent

        # Judge agent for debate phases (optional)
        if judge_agent is None and self.JudgeAgentClass is not None:
            self.judge_agent = self.JudgeAgentClass()
            if self.judge_agent.logger is None:
                self.judge_agent.logger = self.logger
        else:
            self.judge_agent = judge_agent

        self.last_execution_plan: typing.Optional[models.ExecutionPlan] = None
        self.last_execution_results: typing.Dict[str, typing.Any] = {}
        self.last_debate_state: typing.Optional[typing.Dict[str, typing.Any]] = None  # debate_history, judge_decisions for logging
        
        self._producer_by_channel: typing.Dict[typing.Type[AbstractAgentChannel], AbstractAIAgentChannelProducer] = {}
        self._producer_by_name: typing.Dict[str, AbstractAIAgentChannelProducer] = {}
        for agent in self.agents:
            if agent.AGENT_CHANNEL is not None:
                self._producer_by_channel[agent.AGENT_CHANNEL] = agent
            self._producer_by_name[agent.name] = agent
    
    def get_manager(self) -> typing.Optional[AbstractTeamManagerAgent]:
        """
        Get the team manager.
        
        Returns:
            The team manager agent, or None if not set.
        """
        return self.manager
    
    def get_agent_by_name(self, name: str) -> typing.Optional[AbstractAIAgentChannelProducer]:
        """
        Get an agent by name.
        
        Args:
            name: The name of the agent to retrieve.
            
        Returns:
            The agent producer if found, None otherwise.
        """
        return self._producer_by_name.get(name)
    
    def _build_dag(self) -> typing.Tuple[
        typing.Dict[typing.Type[AbstractAgentChannel], typing.List[typing.Type[AbstractAgentChannel]]],
        typing.Dict[typing.Type[AbstractAgentChannel], typing.List[typing.Type[AbstractAgentChannel]]]
    ]:
        """
        Build DAG edge mappings from relations.
        
        Returns:
            Tuple of (incoming_edges, outgoing_edges) dicts.
            - incoming_edges[B] = [A, ...] means B receives from A
            - outgoing_edges[A] = [B, ...] means A sends to B
        """
        incoming_edges: typing.Dict[typing.Type[AbstractAgentChannel], typing.List[typing.Type[AbstractAgentChannel]]] = defaultdict(list)
        outgoing_edges: typing.Dict[typing.Type[AbstractAgentChannel], typing.List[typing.Type[AbstractAgentChannel]]] = defaultdict(list)
        
        for source_channel, target_channel in self.relations:
            incoming_edges[target_channel].append(source_channel)
            outgoing_edges[source_channel].append(target_channel)
        
        return incoming_edges, outgoing_edges
    
    def _get_entry_agents(self) -> typing.List[AbstractAIAgentChannelProducer]:
        """
        Get agents with no incoming edges (entry points).
        
        Returns:
            List of agent producers that have no dependencies.
        """
        incoming_edges, _ = self._build_dag()
        entry_agents = []
        
        for agent in self.agents:
            channel_type = agent.AGENT_CHANNEL
            if channel_type is None:
                continue
            # Entry: no incoming edges
            if channel_type not in incoming_edges or not incoming_edges[channel_type]:
                entry_agents.append(agent)
        
        return entry_agents
    
    def _get_terminal_agents(self) -> typing.List[AbstractAIAgentChannelProducer]:
        """
        Get agents with no outgoing edges (terminal points).
        
        Returns:
            List of agent producers that have no dependents.
        """
        _, outgoing_edges = self._build_dag()
        terminal_agents = []
        
        for agent in self.agents:
            channel_type = agent.AGENT_CHANNEL
            if channel_type is None:
                continue
            # Terminal: no outgoing edges
            if channel_type not in outgoing_edges or not outgoing_edges[channel_type]:
                terminal_agents.append(agent)
        
        return terminal_agents
    
    def _get_execution_order(self) -> typing.List[AbstractAIAgentChannelProducer]:
        """
        Get topological order of agents for sequential execution.
        
        Uses Kahn's algorithm for topological sorting.
        
        Returns:
            List of agent producers in execution order.
        """
        incoming_edges, outgoing_edges = self._build_dag()
        
        # Count incoming edges for each node
        in_degree: typing.Dict[typing.Type[AbstractAgentChannel], int] = defaultdict(int)
        for agent in self.agents:
            channel_type = agent.AGENT_CHANNEL
            if channel_type is not None:
                in_degree[channel_type] = len(incoming_edges.get(channel_type, []))
        
        # Start with nodes that have no incoming edges
        queue: typing.List[typing.Type[AbstractAgentChannel]] = [
            channel_type for channel_type, degree in in_degree.items() if degree == 0
        ]
        
        ordered_channels: typing.List[typing.Type[AbstractAgentChannel]] = []
        
        while queue:
            current = queue.pop(0)
            ordered_channels.append(current)
            
            # Reduce in-degree for all successors
            for successor in outgoing_edges.get(current, []):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)
        
        # Convert channel types back to producers
        return [self._producer_by_channel[ch] for ch in ordered_channels if ch in self._producer_by_channel]

    @staticmethod
    def _get_debate_message(result: typing.Union[typing.Dict[str, typing.Any], typing.Any]) -> str:
        """Extract message text from a debator result (dict or object with message/reasoning)."""
        if isinstance(result, dict):
            return result.get("message", result.get("reasoning", result.get("content", str(result))))
        msg = getattr(result, "message", None)
        if msg is not None:
            return str(msg)
        reasoning = getattr(result, "reasoning", None)
        if reasoning is not None:
            return str(reasoning)
        return str(result)

    async def _run_debate(
        self,
        debate_config: "models.DebatePhaseConfig",
        initial_data: typing.Dict[str, typing.Any],
        results: typing.Dict[str, typing.Dict[str, typing.Any]],
        completed_agents: typing.Set[str],
        incoming_edges: typing.Dict[typing.Type[AbstractAgentChannel], typing.List[typing.Type[AbstractAgentChannel]]],
    ) -> typing.Tuple[typing.Dict[str, typing.Dict[str, typing.Any]], typing.Set[str]]:
        """
        Run a debate phase: debators take turns each round, then judge decides continue or exit.

        Updates results and completed_agents. Sets self.last_debate_state with debate_history
        and judge_decisions for structured logging.
        """
        if self.judge_agent is None:
            self.logger.warning("Debate step requires a judge agent but none is configured; skipping debate.")
            return results, completed_agents

        debate_history: typing.List[typing.Dict[str, typing.Any]] = []
        judge_decisions: typing.List[typing.Dict[str, typing.Any]] = []
        debator_names = list(debate_config.debator_agent_names)
        max_rounds = debate_config.max_rounds
        judge_name = debate_config.judge_agent_name

        for round_num in range(1, max_rounds + 1):
            # Run each debator in order this round
            for debator_name in debator_names:
                agent = self._producer_by_name.get(debator_name)
                if agent is None:
                    self.logger.warning(f"Debator {debator_name} not found in team; skipping.")
                    continue
                # Build input: initial state + debate history so far
                agent_input: typing.Dict[str, typing.Any] = {
                    "_debate_history": debate_history,
                    "_debate_round": round_num,
                }
                if isinstance(initial_data, dict):
                    agent_input["_initial_state"] = initial_data
                # Predecessor outputs for DAG semantics
                channel_type = agent.AGENT_CHANNEL
                predecessors = []
                if channel_type is not None:
                    predecessors = incoming_edges.get(channel_type, [])
                    for pred_channel in predecessors:
                        pred_agent = self._producer_by_channel.get(pred_channel)
                        if pred_agent and pred_agent.name in results:
                            pred_result = results[pred_agent.name]
                            agent_input[pred_agent.name] = {
                                AGENT_NAME_KEY: pred_agent.name,
                                AGENT_ID_KEY: "",
                                RESULT_KEY: pred_result.get(RESULT_KEY),
                            }
                if not agent_input.get("_initial_state") and not predecessors:
                    agent_input = initial_data if isinstance(initial_data, dict) else agent_input

                try:
                    result = await agent.execute(agent_input, self.ai_service)
                except Exception as e:
                    self.logger.exception(f"Debator {debator_name} execution failed: {e}")
                    raise
                # Extract message text for debate history (agent-specific)
                message = self._get_debate_message(result)
                debate_history.append({
                    "agent_name": debator_name,
                    "message": str(message),
                    "round": round_num,
                })
                results[debator_name] = {
                    AGENT_NAME_KEY: debator_name,
                    AGENT_ID_KEY: "",
                    RESULT_KEY: result,
                }
                completed_agents.add(debator_name)

            # Run judge
            judge_input = {
                "debate_history": debate_history,
                "debator_agent_names": debator_names,
                "current_round": round_num,
                "max_rounds": max_rounds,
            }
            if isinstance(initial_data, dict):
                judge_input["_initial_state"] = initial_data
            try:
                judge_out = await self.judge_agent.execute(judge_input, self.ai_service)
            except Exception as e:
                self.logger.exception(f"Judge execution failed: {e}")
                raise
            if isinstance(judge_out, dict):
                judge_dict = judge_out
            else:
                _dump = getattr(judge_out, "model_dump", None) or getattr(judge_out, "dict", None)
                judge_dict = _dump() if _dump else {"decision": JudgeDecisionType.EXIT.value, "reasoning": str(judge_out), "summary": None}
            judge_decisions.append({
                "round": round_num,
                "decision": judge_dict.get("decision", JudgeDecisionType.EXIT.value),
                "reasoning": judge_dict.get("reasoning", ""),
                "summary": judge_dict.get("summary"),
            })
            if self.logger:
                self.logger.debug(
                    f"Debate round {round_num}: judge decision={judge_dict.get('decision', 'exit')} "
                    f"reasoning={judge_dict.get('reasoning', '')[:100]}..."
                )
            if judge_dict.get("decision") == JudgeDecisionType.EXIT.value or round_num >= max_rounds:
                break

        self.last_debate_state = {
            "debate_history": debate_history,
            "judge_decisions": judge_decisions,
        }
        return results, completed_agents

    async def _execute_plan(
        self,
        execution_plan: models.ExecutionPlan,
        initial_data: typing.Dict[str, typing.Any],
    ) -> typing.Dict[str, typing.Any]:
        """
        Execute an ExecutionPlan.
        
        Args:
            execution_plan: The execution plan to execute
            initial_data: Initial data to pass to entry agents
            
        Returns:
            Dict with results from terminal agents
        """
        incoming_edges, _ = self._build_dag()
        terminal_agents = self._get_terminal_agents()
        
        # Store results by agent name
        results: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        completed_agents: typing.Set[str] = set()
        
        iteration = 0
        max_iterations = execution_plan.max_iterations or 1
        
        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Executing plan iteration {iteration}/{max_iterations}")
            
            # Execute each step in the plan
            for step in execution_plan.steps:
                if step.skip:
                    self.logger.debug(f"Skipping agent: {step.agent_name}")
                    continue

                # Debate step: run debators and judge with rounds
                step_type = step.step_type or StepType.AGENT.value
                debate_config = step.debate_config
                if step_type == StepType.DEBATE.value and debate_config is not None:
                    results, completed_agents = await self._run_debate(
                        debate_config, initial_data, results, completed_agents, incoming_edges
                    )
                    continue

                agent = self._producer_by_name.get(step.agent_name)
                if agent is None:
                    self.logger.warning(f"Agent {step.agent_name} not found in team")
                    continue

                # Wait for dependencies if specified
                if step.wait_for:
                    for dep_name in step.wait_for:
                        if dep_name not in completed_agents:
                            self.logger.debug(f"Waiting for dependency: {dep_name}")
                            # In a real implementation, we might want to wait for actual completion
                            # For now, we assume dependencies are already completed
                
                # Send instructions if provided
                if step.instructions:
                    instruction_dict: typing.Dict[str, typing.Any] = {}
                    for instruction in step.instructions:
                        if instruction.modification_type == MODIFICATION_ADDITIONAL_INSTRUCTIONS:
                            instruction_dict[MODIFICATION_ADDITIONAL_INSTRUCTIONS] = instruction.value
                        elif instruction.modification_type == MODIFICATION_CUSTOM_PROMPT:
                            instruction_dict[MODIFICATION_CUSTOM_PROMPT] = instruction.value
                        elif instruction.modification_type == MODIFICATION_EXECUTION_HINTS:
                            instruction_dict[MODIFICATION_EXECUTION_HINTS] = instruction.value
                    
                    if instruction_dict:
                        await self.manager.send_instruction_to_agent(agent, instruction_dict)
                
                # Gather inputs from predecessors
                channel_type = agent.AGENT_CHANNEL
                if channel_type is None:
                    continue
                
                predecessors = incoming_edges.get(channel_type, [])
                
                if not predecessors:
                    # Entry agent: use initial_data
                    agent_input = initial_data
                else:
                    # Non-entry agent: gather predecessor outputs
                    agent_input = {}
                    for pred_channel in predecessors:
                        pred_agent = self._producer_by_channel.get(pred_channel)
                        if pred_agent and pred_agent.name in results:
                            pred_result = results[pred_agent.name]
                            agent_input[pred_agent.name] = {
                                AGENT_NAME_KEY: pred_agent.name,
                                AGENT_ID_KEY: "",
                                RESULT_KEY: pred_result.get(RESULT_KEY),
                            }
                    
                    # Store initial_data in a special key for agents that need it (like distribution agent)
                    # This allows agents to access initial state without breaking agents that expect only predecessor outputs
                    if isinstance(initial_data, dict):
                        agent_input["_initial_state"] = initial_data
                
                self.logger.debug(f"Executing agent: {agent.name}")
                try:
                    result = await agent.execute(agent_input, self.ai_service)
                    results[agent.name] = {
                        AGENT_NAME_KEY: agent.name,
                        AGENT_ID_KEY: "",
                        RESULT_KEY: result,
                    }
                    completed_agents.add(agent.name)
                except Exception as e:
                    self.logger.error(f"Agent {agent.name} execution failed: {e}")
                    raise
            
            # Check loop condition
            if not execution_plan.loop:
                break
            
            # Evaluate loop condition (simplified - in real implementation, this would be more sophisticated)
            if execution_plan.loop_condition:
                self.logger.debug(f"Loop condition: {execution_plan.loop_condition}")
                # For now, we'll break after one iteration if loop_condition is set
                # In a real implementation, this would evaluate the condition
        
        # Collect terminal results and all agent outputs for critic
        terminal_results: typing.Dict[str, typing.Any] = {}
        all_agent_outputs: typing.Dict[str, typing.Any] = {}
        for agent in self.agents:
            if agent.name in results:
                agent_result = results[agent.name].get(RESULT_KEY)
                all_agent_outputs[agent.name] = agent_result
                if agent in terminal_agents:
                    terminal_results[agent.name] = agent_result
        
        # Store for self-improvement
        self.last_execution_results = all_agent_outputs
        
        return terminal_results
    
    def _get_agent_outputs_from_execution(self) -> typing.Dict[str, typing.Any]:
        """
        Collect agent outputs from last execution.
        
        Returns:
            Dict mapping agent names to their outputs.
        """
        outputs = {}
        for agent in self.agents:
            # Try to get output from execution results
            if agent.name in self.last_execution_results:
                result = self.last_execution_results[agent.name]
                try:
                    # Try dict access
                    outputs[agent.name] = result.get("result", result)
                except AttributeError:
                    # Not a dict, use directly
                    outputs[agent.name] = result
        
        # Include manager output if manager is an AI agent with memory enabled
        manager = self.get_manager()
        if manager is not None:
            try:
                if manager.has_memory_enabled():
                    # Manager's output is the execution plan
                    if self.last_execution_plan is not None:
                        outputs[manager.name] = self.last_execution_plan
            except AttributeError:
                # Manager is not an AI agent (no has_memory_enabled method)
                pass
        
        return outputs
    
    async def _self_improve_in_background(self, execution_results: typing.Dict[str, typing.Any]) -> None:
        """
        Run critic and memory update in background without blocking.
        
        Args:
            execution_results: Results from team execution.
        """
        try:
            # 1. Run critic agent
            # Manager is already included in agent_outputs via _get_agent_outputs_from_execution()
            critic_input = {
                "team_producer": self,
                "execution_plan": self.last_execution_plan,
                "execution_results": execution_results,
                "agent_outputs": self._get_agent_outputs_from_execution(),
                "execution_metadata": {
                    "team_name": self.team_name,
                    "team_id": self.team_id,
                },
            }
            critic_analysis = await self.critic_agent.execute(critic_input, self.ai_service)
            
            # 2. Run memory agent with critic output (only for agents needing improvements)
            memory_input = {
                "critic_analysis": critic_analysis,  # Contains agent_improvements dict
                "agent_outputs": self._get_agent_outputs_from_execution(),
                "execution_metadata": {
                    "execution_plan": self.last_execution_plan,
                    "team_name": self.team_name,
                    "team_producer": self,
                },
            }
            memory_operation = await self.memory_agent.execute(memory_input, self.ai_service)
            
            self.logger.debug(
                f"Self-improvement completed: {memory_operation.message}. "
                f"Processed {len(memory_operation.agents_processed)} agents, "
                f"skipped {len(memory_operation.agents_skipped)} agents"
            )
        except Exception as e:
            self.logger.warning(f"Self-improvement failed (non-blocking): {e}")
    
    @abc.abstractmethod
    async def run(self, initial_data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Execute the team pipeline.
        
        Args:
            initial_data: Initial data to pass to entry agents.
            
        Returns:
            Dict with results from terminal agents.
        """
        raise NotImplementedError("run must be implemented by subclasses")
    
    async def push(
        self,
        result: typing.Any,
        agent_name: typing.Optional[str] = None,
        agent_id: typing.Optional[str] = None,
    ) -> None:
        """Push team result to the team's channel."""
        if self.channel is None:
            return
        
        team_name = agent_name or self.team_name
        for consumer_instance in self.channel.get_filtered_consumers(
            agent_name=team_name,
            agent_id=agent_id or self.team_id,
        ):
            await consumer_instance.queue.put({
                AGENT_NAME_KEY: team_name,
                AGENT_ID_KEY: agent_id or self.team_id,
                RESULT_KEY: result,
            })


class AbstractAgentsTeamChannel(AbstractAgentChannel):
    """
    Channel for team outputs.
    
    Allows teams to be composed - one team's output can feed another team.
    """
    __metaclass__ = abc.ABCMeta
    
    PRODUCER_CLASS = AbstractAgentsTeamChannelProducer
    CONSUMER_CLASS = AbstractAgentsTeamChannelConsumer
