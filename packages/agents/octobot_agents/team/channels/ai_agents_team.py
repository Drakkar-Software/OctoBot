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
import asyncio
import typing

from octobot_agents.agent import (
    AbstractAIAgentChannel,
    AbstractAIAgentChannelProducer,
    AbstractAIAgentChannelConsumer,
)
from octobot_agents.constants import AGENT_NAME_KEY, AGENT_ID_KEY, RESULT_KEY
from octobot_agents.team.manager import AbstractTeamManagerAgent
from octobot_agents.team.critic import AbstractCriticAgent
from octobot_agents.agent.memory.channels import AbstractMemoryAgent
from octobot_agents.team.channels.agents_team import (
    AbstractAgentsTeamChannel,
    AbstractAgentsTeamChannelProducer,
)
from octobot_agents.errors import AgentConfigurationError
from octobot_agents.storage.history import create_analysis_storage
import octobot_services.services.abstract_ai_service as abstract_ai_service
import octobot_agents.models as models


class AbstractSyncAgentsTeamChannelProducer(AbstractAgentsTeamChannelProducer):
    """
    Sync (one-shot) team producer for direct sequential execution.
    
    Executes agents in topological order without using channels or consumers.
    Each agent's execute() is called directly with outputs from predecessors.
    
    Use this for:
    - Simple sequential pipelines
    - One-shot batch processing
    - Testing and debugging
    """
    
    def __init__(
        self,
        channel: typing.Optional[AbstractAgentsTeamChannel],
        agents: typing.List[AbstractAIAgentChannelProducer],
        relations: typing.List[typing.Tuple[typing.Type[AbstractAIAgentChannel], typing.Type[AbstractAIAgentChannel]]],
        ai_service: abstract_ai_service.AbstractAIService,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
        manager: typing.Optional[AbstractTeamManagerAgent] = None,
        self_improving: bool = False,
        critic_agent: typing.Optional[AbstractCriticAgent] = None,
        memory_agent: typing.Optional[AbstractMemoryAgent] = None,
        judge_agent: typing.Optional["AbstractJudgeAgent"] = None,
        analysis_storage: typing.Optional[typing.Any] = None,
    ):
        """
        Initialize the sync AI team producer.

        Uses CriticAgentClass / JudgeAgentClass attributes if defined, otherwise disabled.
        
        Args:
            channel: The team's output channel (optional).
            agents: List of agent producer instances.
            relations: List of (SourceAgentChannel, TargetAgentChannel) edges.
            ai_service: The AI service for LLM calls.
            team_name: Name of the team (defaults to TEAM_NAME).
            team_id: Unique identifier for this team instance.
            manager: Optional team manager agent.
            self_improving: Whether to enable automatic improvement after execution.
            critic_agent: Optional critic agent for analysis.
            memory_agent: Optional memory agent for storing improvements.
            judge_agent: Optional judge agent for debate phases.
            analysis_storage: Optional analysis storage instance. If None, uses JSONAnalysisStorage.
        """
        # Call parent init first - it handles critic/memory/judge agent instantiation via class attributes
        super().__init__(
            channel=channel,
            agents=agents,
            relations=relations,
            ai_service=ai_service,
            team_name=team_name,
            team_id=team_id,
            manager=manager,
            self_improving=self_improving,
            critic_agent=critic_agent,
            memory_agent=memory_agent,
            judge_agent=judge_agent,
        )
        
        # Initialize analysis storage
        if analysis_storage is None:
            self.analysis_storage = create_analysis_storage(storage_type="json")
        else:
            self.analysis_storage = analysis_storage
    
    async def run(self, initial_data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Execute the team pipeline synchronously using the manager.
        
        1. Get ExecutionPlan from manager.execute()
        2. Execute the plan
        3. Return terminal agent results
        4. Trigger self-improvement in background if enabled
        
        Args:
            initial_data: Initial data to pass to entry agents.
            
        Returns:
            Dict with results from all terminal agents.
        """ 
        # Build input_data for manager
        manager_input = {
            "team_producer": self,
            "initial_data": initial_data,
            "instructions": None,  # Can be extended to accept instructions
        }
        
        # Get execution plan or terminal results from manager
        manager_result = await self.manager.execute(manager_input, self.ai_service)
        
        terminal_results: typing.Dict[str, typing.Any]
        if isinstance(manager_result, models.ExecutionPlan):
            # Plan-driven manager: execute the plan
            self.last_execution_plan = manager_result
            terminal_results = await self._execute_plan(manager_result, initial_data)
        elif isinstance(manager_result, models.ManagerResult):
            # Tools-driven manager: extract results from ManagerResult model
            terminal_results = manager_result.results
            self.last_execution_plan = None
        else:
            raise ValueError(f"Unexpected manager result type: {type(manager_result)}")
        
        self.last_execution_results = terminal_results
        
        self.logger.debug(f"Sync execution completed with {len(terminal_results)} results")
        
        # Push team result if we have a channel
        if self.channel is not None:
            await self.push(terminal_results)
        
        # Trigger self-improvement in background if enabled
        if self.self_improving and self.critic_agent and self.memory_agent:
            asyncio.create_task(self._self_improve_in_background(terminal_results))
        
        return terminal_results
    
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
            agent_name: Name of the agent producing the analysis.
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



class AbstractLiveAgentsTeamChannelProducer(AbstractAgentsTeamChannelProducer):
    """
    Live (long-running) team producer with full channel-based execution.
    
    Creates channels for each agent and wires consumers based on relations.
    Agents communicate asynchronously through their channels.
    
    Use this for:
    - Long-running pipelines with continuous updates
    - Complex DAG workflows with parallel execution
    - Reactive systems where agents respond to events
    """
    
    def __init__(
        self,
        channel: typing.Optional[AbstractAgentsTeamChannel],
        agents: typing.List[AbstractAIAgentChannelProducer],
        relations: typing.List[typing.Tuple[typing.Type[AbstractAIAgentChannel], typing.Type[AbstractAIAgentChannel]]],
        ai_service: abstract_ai_service.AbstractAIService,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
        manager: typing.Optional[AbstractTeamManagerAgent] = None,
        self_improving: bool = False,
        critic_agent: typing.Optional[AbstractCriticAgent] = None,
        memory_agent: typing.Optional[AbstractMemoryAgent] = None,
        judge_agent: typing.Optional["AbstractJudgeAgent"] = None,
    ):
        """
        Initialize the live AI team producer.

        Uses CriticAgentClass / JudgeAgentClass attribute if defined, otherwise disabled.
        """
        # Call parent init - it handles critic/memory/judge agent instantiation via class attributes
        super().__init__(
            channel=channel,
            agents=agents,
            relations=relations,
            ai_service=ai_service,
            team_name=team_name,
            team_id=team_id,
            manager=manager,
            self_improving=self_improving,
            critic_agent=critic_agent,
            memory_agent=memory_agent,
            judge_agent=judge_agent,
        )

        # Live-specific state
        self._channels: typing.Dict[typing.Type[AbstractAIAgentChannel], AbstractAIAgentChannel] = {}
        self._entry_agents: typing.List[AbstractAIAgentChannelProducer] = []
        self._terminal_agents: typing.List[AbstractAIAgentChannelProducer] = []
        self._terminal_results: typing.Dict[str, typing.Any] = {}
        self._completion_event: typing.Optional[asyncio.Event] = None
    
    async def setup(self) -> None:
        """
        Create channels for all agents and wire consumers based on relations.
        
        This method:
        1. Creates a channel instance for each agent using agent.AGENT_CHANNEL
        2. Identifies entry agents (no incoming edges in relations)
        3. Identifies terminal agents (no outgoing edges in relations)
        4. For each relation (A, B): registers B's consumer on A's channel
        """
        incoming_edges, outgoing_edges = self._build_dag()
        
        # Create channels and map producers
        for agent in self.agents:
            if agent.AGENT_CHANNEL is None:
                raise AgentConfigurationError(f"Agent {agent.__class__.__name__} has no AGENT_CHANNEL defined")
            
            channel_type = agent.AGENT_CHANNEL
            # Pass team_name and team_id to channels
            channel_instance = channel_type(
                team_name=self.team_name,
                team_id=self.team_id,
            )
            self._channels[channel_type] = channel_instance
            
            # Set the channel on the producer
            agent.channel = channel_instance
            agent.ai_service = self.ai_service
        
        # Identify entry and terminal agents
        self._entry_agents = self._get_entry_agents()
        self._terminal_agents = self._get_terminal_agents()
        
        # Wire consumers based on relations
        for source_channel_type, target_channel_type in self.relations:
            source_channel = self._channels.get(source_channel_type)
            target_producer = self._producer_by_channel.get(target_channel_type)
            
            if source_channel is None:
                self.logger.warning(f"Source channel {source_channel_type.__name__} not found in team")
                continue
            if target_producer is None:
                self.logger.warning(f"Target producer for {target_channel_type.__name__} not found in team")
                continue
            
            # Calculate expected inputs for target
            expected_inputs = len(incoming_edges[target_channel_type])
            
            # Create consumer for the target that listens on source's channel
            consumer_class = target_producer.AGENT_CONSUMER or AbstractAIAgentChannelConsumer
            consumer_instance = consumer_class(
                callback=self._create_consumer_callback(target_producer, target_channel_type),
                expected_inputs=expected_inputs,
            )
            
            # Register consumer on source channel
            await source_channel.new_consumer(
                consumer_instance=consumer_instance,
                agent_name=self._producer_by_channel[source_channel_type].name,
            )
        
        # Wire terminal agent callbacks to collect results
        for terminal_agent in self._terminal_agents:
            terminal_channel = self._channels.get(terminal_agent.AGENT_CHANNEL)
            if terminal_channel:
                await terminal_channel.new_consumer(
                    callback=self._create_terminal_callback(terminal_agent),
                    agent_name=terminal_agent.name,
                )
        
        self.logger.debug(
            f"Team setup complete: {len(self._entry_agents)} entry agents, "
            f"{len(self._terminal_agents)} terminal agents, "
            f"{len(self.relations)} relations"
        )
    
    def _create_consumer_callback(
        self,
        target_producer: AbstractAIAgentChannelProducer,
        target_channel_type: typing.Type[AbstractAIAgentChannel],
    ) -> typing.Callable:
        """Create a callback that aggregates inputs and triggers the producer."""
        
        # Track received inputs for this target (key: agent_name)
        received_inputs: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        incoming_edges, _ = self._build_dag()
        expected_count = len(incoming_edges.get(target_channel_type, []))
        
        async def callback(data: dict) -> None:
            source_name = data.get(AGENT_NAME_KEY, "unknown")
            source_id = data.get(AGENT_ID_KEY, "")
            result = data.get(RESULT_KEY)
            
            # Store with both name and id for full context
            received_inputs[source_name] = {
                AGENT_NAME_KEY: source_name,
                AGENT_ID_KEY: source_id,
                RESULT_KEY: result,
            }
            
            self.logger.debug(
                f"Target {target_producer.name} received input from {source_name}[{source_id}] "
                f"({len(received_inputs)}/{expected_count})"
            )
            
            # Trigger when all inputs received
            if len(received_inputs) >= expected_count:
                self.logger.debug(f"Triggering {target_producer.name} with {len(received_inputs)} inputs")
                try:
                    # Pass the full input data including agent_id
                    result = await target_producer.execute(received_inputs.copy(), self.ai_service)
                    await target_producer.push(result)
                except Exception as e:
                    self.logger.error(f"Agent {target_producer.name} execution failed: {e}")
                    raise
                finally:
                    received_inputs.clear()
        
        return callback
    
    def _create_terminal_callback(
        self,
        terminal_agent: AbstractAIAgentChannelProducer,
    ) -> typing.Callable:
        """Create a callback that collects terminal agent results."""
        
        async def callback(data: dict) -> None:
            result = data.get(RESULT_KEY)
            self._terminal_results[terminal_agent.name] = result
            
            self.logger.debug(
                f"Terminal agent {terminal_agent.name} completed "
                f"({len(self._terminal_results)}/{len(self._terminal_agents)})"
            )
            
            # Check if all terminal agents completed
            if len(self._terminal_results) >= len(self._terminal_agents):
                if self._completion_event:
                    self._completion_event.set()
        
        return callback
    
    async def run(self, initial_data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Execute the team pipeline with channels.
        
        1. Setup channels and consumers (if not already done)
        2. Start entry agents with initial_data
        3. Wait for terminal agents to complete
        4. Produce team output to team's channel
        
        Args:
            initial_data: Initial data to pass to entry agents.
            
        Returns:
            Dict with results from all terminal agents.
        """
        # Setup if not already done
        if not self._channels:
            await self.setup()
        
        # Clear previous results
        self._terminal_results.clear()
        self._completion_event = asyncio.Event()
        
        # Start entry agents
        self.logger.debug(f"Starting {len(self._entry_agents)} entry agents")
        
        entry_tasks = []
        for entry_agent in self._entry_agents:
            async def run_entry(agent: AbstractAIAgentChannelProducer) -> None:
                try:
                    result = await agent.execute(initial_data, self.ai_service)
                    await agent.push(result)
                except Exception as e:
                    self.logger.error(f"Entry agent {agent.name} failed: {e}")
                    raise
            
            entry_tasks.append(asyncio.create_task(run_entry(entry_agent)))
        
        # Wait for all entry agents to complete
        if entry_tasks:
            await asyncio.gather(*entry_tasks)
        
        # Wait for terminal agents to complete (with timeout)
        try:
            await asyncio.wait_for(self._completion_event.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            self.logger.error("Team execution timed out waiting for terminal agents")
            raise
        
        self.logger.debug(f"Team execution completed with {len(self._terminal_results)} results")
        
        # Store execution results for self-improvement
        self.last_execution_results = self._terminal_results.copy()
        
        # Push team result if we have a channel
        if self.channel is not None:
            await self.push(self._terminal_results)
        
        # Trigger self-improvement in background if enabled
        if self.self_improving and self.critic_agent and self.memory_agent:
            asyncio.create_task(self._self_improve_in_background(self._terminal_results))
        
        return self._terminal_results
    
    async def stop(self) -> None:
        """Stop all agents and cleanup channels."""
        for channel in self._channels.values():
            try:
                await channel.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping channel: {e}")
        
        self._channels.clear()
        self._entry_agents.clear()
        self._terminal_agents.clear()
        self._terminal_results.clear()
        
        self.logger.debug("Team stopped")
