#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
"""
Default team manager agent - simple agent that executes in topological order.
"""
import typing
from typing import List, Optional

import octobot_agents.team.manager as agent_manager
import octobot_agents.enums as agent_enums
import octobot_agents.models as agent_models


class DefaultTeamManagerAgentChannel(agent_manager.ManagerAgentChannel):
    pass


class DefaultTeamManagerAgentConsumer(agent_manager.ManagerAgentConsumer):
    pass


class DefaultTeamManagerAgentProducer(agent_manager.ManagerAgentProducer):
    """
    Default team manager agent - simple agent that executes in topological order.
    
    Inherits from ManagerAgentProducer. Has Channel, Producer, Consumer components (as all agents do).
    """
    
    AGENT_CHANNEL: typing.Type[agent_manager.ManagerAgentChannel] = DefaultTeamManagerAgentChannel
    AGENT_CONSUMER: typing.Type[agent_manager.ManagerAgentConsumer] = DefaultTeamManagerAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[DefaultTeamManagerAgentChannel] = None,
    ):
        super().__init__(channel=channel)
    
    async def execute(
        self,
        input_data: typing.Union[agent_models.ManagerInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any  # AbstractAIService - type not available at runtime
    ) -> agent_models.ExecutionPlan:
        """
        Build execution plan from topological sort.
        
        Args:
            input_data: Contains {"team_producer": team_producer, "initial_data": initial_data, "instructions": instructions}
            ai_service: Not used by default manager
            
        Returns:
            ExecutionPlan with steps in topological order
        """
        team_producer = input_data.get("team_producer")
        if team_producer is None:
            raise ValueError("team_producer is required in input_data")
        
        # Get execution order (topological sort)
        execution_order = team_producer._get_execution_order()
        incoming_edges, _ = team_producer._build_dag()
        
        # Build ExecutionPlan
        steps: List[agent_models.ExecutionStep] = []
        for agent in execution_order:
            # Get predecessors for wait_for
            channel_type = agent.AGENT_CHANNEL
            if channel_type is None:
                continue
            
            predecessors = incoming_edges.get(channel_type, [])
            wait_for: Optional[List[str]] = None
            if predecessors:
                wait_for = []
                for pred_channel in predecessors:
                    pred_agent = team_producer._producer_by_channel.get(pred_channel)
                    if pred_agent:
                        wait_for.append(pred_agent.name)
            
            step = agent_models.ExecutionStep(
                agent_name=agent.name,
                instructions=None,  # No instructions by default
                wait_for=wait_for,
                skip=False,
            )
            steps.append(step)

        # Optional: inject debate steps from initial_data.debate_phases
        initial_data = input_data.get("initial_data") or {}
        debate_phases = initial_data.get("debate_phases") if isinstance(initial_data, dict) else None
        if isinstance(debate_phases, list) and debate_phases:
            for idx, phase in enumerate(debate_phases):
                config = agent_models.DebatePhaseConfig.model_validate(phase) if not isinstance(phase, agent_models.DebatePhaseConfig) else phase
                steps.append(
                    agent_models.ExecutionStep(
                        agent_name=f"debate_{idx + 1}",
                        step_type=agent_enums.StepType.DEBATE.value,
                        debate_config=config,
                        skip=False,
                    )
                )

        return agent_models.ExecutionPlan(
            steps=steps,
            loop=False,
            loop_condition=None,
            max_iterations=None,
        )
