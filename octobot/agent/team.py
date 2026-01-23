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
Abstract agent team channel classes for orchestrating teams of agents.

Teams follow the same channel pattern as individual agents, enabling:
- Composable teams (teams can consume from other teams)
- DAG-based agent relationships
- Two execution modes: Sync (one-shot) and Live (long-running with channels)

Relation semantics:
- relations = [(ChannelA, ChannelB), ...] where A and B are Channel types
- Means: A's producer publishes to A's channel, B has a consumer on A's channel
- When B's consumer receives from A, it triggers B's producer

Execution modes:
- SyncAgentTeam: Direct execution in topological order, no channels/consumers
- LiveAgentTeam: Full channel-based execution with consumer wiring
"""
import abc
import asyncio
import typing
from collections import defaultdict

import octobot_commons.logging as logging

from octobot.agent.channel import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
    AbstractAIAgentChannelConsumer,
    AbstractAIAgentChannelProducer,
)


class AbstractAgentTeamChannelConsumer(AbstractAgentChannelConsumer):
    """
    Consumer for team outputs.
    
    Can be used to consume results from a team's final output channel.
    """
    __metaclass__ = abc.ABCMeta


class AbstractAgentTeamChannelProducer(AbstractAgentChannelProducer, abc.ABC):
    """
    Base producer for agent teams with common DAG logic.
    
    This class provides:
    - DAG computation from relations
    - Entry/terminal agent identification
    - Topological ordering for execution
    
    Subclasses implement different execution modes:
    - AbstractSyncAgentTeamChannelProducer: Direct one-shot execution
    - AbstractLiveAgentTeamChannelProducer: Channel-based long-running execution
    
    Relation semantics:
    - relations = [(A, B), ...] where A and B are Channel types
    - Means: A's producer output feeds into B's producer input
    """
    
    # Override in subclasses with dedicated channel and consumer classes
    TEAM_CHANNEL: typing.Optional[typing.Type["AbstractAgentTeamChannel"]] = None
    TEAM_CONSUMER: typing.Optional[typing.Type[AbstractAgentTeamChannelConsumer]] = None
    TEAM_NAME: str = "AbstractAgentTeam"
    
    def __init__(
        self,
        channel: typing.Optional["AbstractAgentTeamChannel"],
        agents: typing.List[AbstractAIAgentChannelProducer],
        relations: typing.List[typing.Tuple[typing.Type[AbstractAgentChannel], typing.Type[AbstractAgentChannel]]],
        ai_service: typing.Any,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
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
        """
        super().__init__(channel)
        self.agents = agents
        self.relations = relations
        self.ai_service = ai_service
        self.team_name = team_name or self.TEAM_NAME
        self.team_id = team_id or ""
        self.logger = logging.get_logger(f"{self.__class__.__name__}{f'[{self.team_id}]' if self.team_id else ''}")
        
        self._producer_by_channel: typing.Dict[typing.Type[AbstractAgentChannel], AbstractAIAgentChannelProducer] = {}
        for agent in self.agents:
            if agent.AGENT_CHANNEL is not None:
                self._producer_by_channel[agent.AGENT_CHANNEL] = agent
    
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
                AbstractAgentChannel.AGENT_NAME_KEY: team_name,
                AbstractAgentChannel.AGENT_ID_KEY: agent_id or self.team_id,
                AbstractAgentChannel.RESULT_KEY: result,
            })


class AbstractSyncAgentTeamChannelProducer(AbstractAgentTeamChannelProducer):
    """
    Sync (one-shot) team producer for direct sequential execution.
    
    Executes agents in topological order without using channels or consumers.
    Each agent's execute() is called directly with outputs from predecessors.
    
    Use this for:
    - Simple sequential pipelines
    - One-shot batch processing
    - Testing and debugging
    """
    
    async def run(self, initial_data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Execute the team pipeline synchronously in topological order.
        
        1. Compute topological order of agents
        2. For each agent in order:
           - Gather outputs from predecessor agents
           - Call execute() directly
           - Store result for successor agents
        3. Return terminal agent results
        
        Args:
            initial_data: Initial data to pass to entry agents.
            
        Returns:
            Dict with results from all terminal agents.
        """
        execution_order = self._get_execution_order()
        incoming_edges, _ = self._build_dag()
        terminal_agents = self._get_terminal_agents()
        
        # Store results by channel type
        results: typing.Dict[typing.Type[AbstractAgentChannel], typing.Dict[str, typing.Any]] = {}
        
        self.logger.info(f"Starting sync execution with {len(execution_order)} agents")
        
        for agent in execution_order:
            channel_type = agent.AGENT_CHANNEL
            if channel_type is None:
                continue
            
            # Gather inputs from predecessors
            predecessors = incoming_edges.get(channel_type, [])
            
            if not predecessors:
                # Entry agent: use initial_data
                agent_input = initial_data
            else:
                # Non-entry agent: gather predecessor outputs
                agent_input = {}
                for pred_channel in predecessors:
                    pred_agent = self._producer_by_channel.get(pred_channel)
                    if pred_agent and pred_channel in results:
                        pred_result = results[pred_channel]
                        agent_input[pred_agent.AGENT_NAME] = {
                            AbstractAgentChannel.AGENT_NAME_KEY: pred_agent.AGENT_NAME,
                            AbstractAgentChannel.AGENT_ID_KEY: "",
                            AbstractAgentChannel.RESULT_KEY: pred_result.get(AbstractAgentChannel.RESULT_KEY),
                        }
            
            # Execute agent
            self.logger.info(f"Executing agent: {agent.AGENT_NAME}")
            try:
                result = await agent.execute(agent_input, self.ai_service)
                results[channel_type] = {
                    AbstractAgentChannel.AGENT_NAME_KEY: agent.AGENT_NAME,
                    AbstractAgentChannel.AGENT_ID_KEY: "",
                    AbstractAgentChannel.RESULT_KEY: result,
                }
            except Exception as e:
                self.logger.error(f"Agent {agent.AGENT_NAME} execution failed: {e}")
                raise
        
        # Collect terminal results
        terminal_results: typing.Dict[str, typing.Any] = {}
        for agent in terminal_agents:
            channel_type = agent.AGENT_CHANNEL
            if channel_type and channel_type in results:
                terminal_results[agent.AGENT_NAME] = results[channel_type].get(AbstractAgentChannel.RESULT_KEY)
        
        self.logger.info(f"Sync execution completed with {len(terminal_results)} results")
        
        # Push team result if we have a channel
        if self.channel is not None:
            await self.push(terminal_results)
        
        return terminal_results


class AbstractLiveAgentTeamChannelProducer(AbstractAgentTeamChannelProducer):
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
        channel: typing.Optional["AbstractAgentTeamChannel"],
        agents: typing.List[AbstractAIAgentChannelProducer],
        relations: typing.List[typing.Tuple[typing.Type[AbstractAgentChannel], typing.Type[AbstractAgentChannel]]],
        ai_service: typing.Any,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
    ):
        super().__init__(channel, agents, relations, ai_service, team_name, team_id)
        
        # Live-specific state
        self._channels: typing.Dict[typing.Type[AbstractAgentChannel], AbstractAgentChannel] = {}
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
                raise ValueError(f"Agent {agent.__class__.__name__} has no AGENT_CHANNEL defined")
            
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
            consumer_instance.set_producer(target_producer)
            
            # Register consumer on source channel
            await source_channel.new_consumer(
                consumer_instance=consumer_instance,
                agent_name=self._producer_by_channel[source_channel_type].AGENT_NAME,
            )
        
        # Wire terminal agent callbacks to collect results
        for terminal_agent in self._terminal_agents:
            terminal_channel = self._channels.get(terminal_agent.AGENT_CHANNEL)
            if terminal_channel:
                await terminal_channel.new_consumer(
                    callback=self._create_terminal_callback(terminal_agent),
                    agent_name=terminal_agent.AGENT_NAME,
                )
        
        self.logger.info(
            f"Team setup complete: {len(self._entry_agents)} entry agents, "
            f"{len(self._terminal_agents)} terminal agents, "
            f"{len(self.relations)} relations"
        )
    
    def _create_consumer_callback(
        self,
        target_producer: AbstractAIAgentChannelProducer,
        target_channel_type: typing.Type[AbstractAgentChannel],
    ) -> typing.Callable:
        """Create a callback that aggregates inputs and triggers the producer."""
        
        # Track received inputs for this target (key: agent_name)
        received_inputs: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        incoming_edges, _ = self._build_dag()
        expected_count = len(incoming_edges.get(target_channel_type, []))
        
        async def callback(data: dict) -> None:
            source_name = data.get(AbstractAgentChannel.AGENT_NAME_KEY, "unknown")
            source_id = data.get(AbstractAgentChannel.AGENT_ID_KEY, "")
            result = data.get(AbstractAgentChannel.RESULT_KEY)
            
            # Store with both name and id for full context
            received_inputs[source_name] = {
                AbstractAgentChannel.AGENT_NAME_KEY: source_name,
                AbstractAgentChannel.AGENT_ID_KEY: source_id,
                AbstractAgentChannel.RESULT_KEY: result,
            }
            
            self.logger.debug(
                f"Target {target_producer.AGENT_NAME} received input from {source_name}[{source_id}] "
                f"({len(received_inputs)}/{expected_count})"
            )
            
            # Trigger when all inputs received
            if len(received_inputs) >= expected_count:
                self.logger.info(f"Triggering {target_producer.AGENT_NAME} with {len(received_inputs)} inputs")
                try:
                    # Pass the full input data including agent_id
                    result = await target_producer.execute(received_inputs.copy(), self.ai_service)
                    await target_producer.push(result)
                except Exception as e:
                    self.logger.error(f"Agent {target_producer.AGENT_NAME} execution failed: {e}")
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
            result = data.get(AbstractAgentChannel.RESULT_KEY)
            self._terminal_results[terminal_agent.AGENT_NAME] = result
            
            self.logger.debug(
                f"Terminal agent {terminal_agent.AGENT_NAME} completed "
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
        self.logger.info(f"Starting {len(self._entry_agents)} entry agents")
        
        entry_tasks = []
        for entry_agent in self._entry_agents:
            async def run_entry(agent: AbstractAIAgentChannelProducer) -> None:
                try:
                    result = await agent.execute(initial_data, self.ai_service)
                    await agent.push(result)
                except Exception as e:
                    self.logger.error(f"Entry agent {agent.AGENT_NAME} failed: {e}")
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
        
        self.logger.info(f"Team execution completed with {len(self._terminal_results)} results")
        
        # Push team result if we have a channel
        if self.channel is not None:
            await self.push(self._terminal_results)
        
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
        
        self.logger.info("Team stopped")


class AbstractAgentTeamChannel(AbstractAgentChannel):
    """
    Channel for team outputs.
    
    Allows teams to be composed - one team's output can feed another team.
    """
    __metaclass__ = abc.ABCMeta
    
    PRODUCER_CLASS = AbstractAgentTeamChannelProducer
    CONSUMER_CLASS = AbstractAgentTeamChannelConsumer
