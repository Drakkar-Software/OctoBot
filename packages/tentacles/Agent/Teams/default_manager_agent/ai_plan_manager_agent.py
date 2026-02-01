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
AI team manager agent - uses LLM to decide execution flow.
"""
import typing
from typing import TYPE_CHECKING

from octobot_agents.team.manager import (
    AIPlanManagerAgentChannel,
    AIPlanManagerAgentConsumer,
    AIPlanManagerAgentProducer,
    AbstractTeamManagerAgent,
)
from octobot_agents.models import ExecutionPlan

if TYPE_CHECKING:
    from octobot_agents.models import ManagerInput


class AIPlanTeamManagerAgentChannel(AIPlanManagerAgentChannel):
    """Channel for AI plan team manager."""
    __slots__ = ()


class AIPlanTeamManagerAgentConsumer(AIPlanManagerAgentConsumer):
    """Consumer for AI plan team manager."""
    __slots__ = ()


class AIPlanTeamManagerAgentProducer(AIPlanManagerAgentProducer):
    """
    AI plan team manager agent - uses LLM to decide execution flow.
    
    Inherits from AIPlanManagerAgentProducer. Has Channel, Producer, Consumer components (as all AI agents do).
    """
    
    AGENT_CHANNEL: typing.Type[AIPlanManagerAgentChannel] = AIPlanTeamManagerAgentChannel
    AGENT_CONSUMER: typing.Type[AIPlanManagerAgentConsumer] = AIPlanTeamManagerAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[AIPlanTeamManagerAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
    
    def _get_default_prompt(self) -> str:
        """
        Return the default prompt for the AI team manager.
        
        Returns:
            The default system prompt string.
        """
        return """You are a team execution manager for an agent team system.
Your role is to analyze the team structure, current state, and any instructions,
then create an execution plan. The plan can contain two kinds of steps:

1. Agent steps (step_type "agent" or omit): run a single agent.
   - agent_name: name of the agent to run
   - instructions (optional): list of instructions to send before execution
   - wait_for (optional): agent names that must complete before this step
   - skip (optional): set true to skip this step in this iteration

2. Debate steps (step_type "debate"): run a debate phase (debators take turns, then judge decides continue or exit).
   - debate_config: object with debator_agent_names (list of agent names that debate, e.g. Bull, Bear),
     judge_agent_name (name of the judge agent), max_rounds (max debate rounds, e.g. 3)
   - For debate steps, agent_name can be a placeholder (e.g. "debate_1") for logging.

You may include zero, one, or multiple debate steps in the plan. Debate steps run debators in rounds until the judge decides exit or max_rounds is reached. Order and instructions for agent steps, and whether to loop execution, should optimize for the team's goals while respecting dependencies."""
    
    async def execute(
        self,
        input_data: typing.Union["ManagerInput", typing.Dict[str, typing.Any]],
        ai_service: typing.Any  # AbstractAIService - type not available at runtime
    ) -> ExecutionPlan:
        """
        Build execution plan using LLM.
        
        Args:
            input_data: Contains {"team_producer": team_producer, "initial_data": initial_data, "instructions": instructions}
            ai_service: The AI service instance for LLM calls
            
        Returns:
            ExecutionPlan from LLM
        """
        team_producer = input_data.get("team_producer")
        initial_data = input_data.get("initial_data", {})
        instructions = input_data.get("instructions")
        
        if team_producer is None:
            raise ValueError("team_producer is required in input_data")
        
        # Build context
        agents_info = []
        for agent in team_producer.agents:
            agents_info.append({
                "name": agent.name,
                "channel": agent.AGENT_CHANNEL.__name__ if agent.AGENT_CHANNEL else None,
            })
        
        relations_info = []
        for source_channel, target_channel in team_producer.relations:
            relations_info.append({
                "source": source_channel.__name__,
                "target": target_channel.__name__,
            })
        
        context = {
            "team_name": team_producer.team_name,
            "agents": agents_info,
            "relations": relations_info,
            "initial_data": initial_data,
            "instructions": instructions,
        }
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.prompt},
            {
                "role": "user",
                "content": f"""Analyze the following team structure and create an execution plan:

Team: {team_producer.team_name}
Agents: {self.format_data(agents_info)}
Relations: {self.format_data(relations_info)}
Initial Data: {self.format_data(initial_data)}
Instructions: {self.format_data(instructions) if instructions else "None"}

Create an execution plan. Use agent steps (step_type "agent" or omit) for single-agent steps and debate steps (step_type "debate" with debate_config) when you want debators to argue and a judge to decide; you can include multiple debate steps if needed."""
            },
        ]
        
        # Call LLM with ExecutionPlan as response schema
        response_data = await self._call_llm(
            messages,
            ai_service,
            json_output=True,
            response_schema=ExecutionPlan,
        )
        
        execution_plan = ExecutionPlan.model_validate(response_data)
        
        # Filter out debate steps if no judge agent is configured in the team
        team_producer = input_data.get("team_producer")
        if team_producer is None or team_producer.judge_agent is None:
            filtered_steps = []
            for step in execution_plan.steps:
                if step.step_type == "debate":
                    self.logger.debug(f"Skipping debate step '{step.agent_name}' - no judge agent configured in team")
                    continue
                filtered_steps.append(step)
            execution_plan.steps = filtered_steps
        
        self.logger.debug(f"Generated execution plan with {len(execution_plan.steps)} steps")
        
        return execution_plan
