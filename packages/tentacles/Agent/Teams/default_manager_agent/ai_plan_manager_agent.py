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

import pydantic

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

You may include zero, one, or multiple debate steps in the plan. Debate steps run debators in rounds until the judge decides exit or max_rounds is reached. Order and instructions for agent steps, and whether to loop execution, should optimize for the team's goals while respecting dependencies.

Critical requirements:
- Every agent step MUST include a non-empty agent_name.
- agent_name MUST be one of the provided agent names in the context. Do NOT invent new names.
- Output ONLY valid JSON matching the ExecutionPlan schema. No markdown or extra text."""

    def _repair_execution_plan(self, response_data: typing.Any) -> typing.Optional[ExecutionPlan]:
        if not isinstance(response_data, dict):
            return None
        steps = response_data.get("steps")
        if not isinstance(steps, list):
            return None
        repaired_steps = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_type = step.get("step_type")
            agent_name = step.get("agent_name")
            if not agent_name and step_type in (None, "agent"):
                agent_name = step.get("name") or step.get("agent")
                if agent_name:
                    step = {**step, "agent_name": agent_name}
            if step_type in (None, "agent") and not step.get("agent_name"):
                continue
            repaired_steps.append(step)
        if not repaired_steps:
            return None
        repaired = {**response_data, "steps": repaired_steps}
        try:
            return ExecutionPlan.model_validate(repaired)
        except pydantic.ValidationError:
            return None
    
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

Create an execution plan. Use agent steps (step_type "agent" or omit) for single-agent steps and debate steps (step_type "debate" with debate_config) when you want debators to argue and a judge to decide; you can include multiple debate steps if needed.

CRITICAL: agent_name MUST be exactly one of the provided agent names. Do NOT invent names."""
            },
        ]
        
        # Call LLM with ExecutionPlan as response schema
        response_data = await self._call_llm(
            messages,
            ai_service,
            json_output=True,
            response_schema=ExecutionPlan,
        )
        allowed_agent_names = [agent["name"] for agent in agents_info]
        try:
            execution_plan = ExecutionPlan.model_validate_with_agent_names(
                response_data,
                allowed_agent_names,
            )
        except (pydantic.ValidationError, ValueError) as e:
            repaired = self._repair_execution_plan(response_data)
            if repaired is not None:
                self.logger.warning("Recovered invalid execution plan by repairing steps.")
                return repaired
            self.logger.warning(f"Invalid execution plan. Retrying once. Error: {e}")
            retry_messages = [
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": f"""Analyze the following team structure and create an execution plan:

Team: {team_producer.team_name}
Agents: {self.format_data(agents_info)}
Relations: {self.format_data(relations_info)}
Initial Data: {self.format_data(initial_data)}
Instructions: {self.format_data(instructions) if instructions else "None"}

CRITICAL: Every agent step MUST include agent_name (non-empty string). 
Create an execution plan. Use agent steps (step_type "agent" or omit) for single-agent steps and debate steps (step_type "debate" with debate_config) when you want debators to argue and a judge to decide; you can include multiple debate steps if needed."""
                },
            ]
            response_data = await self._call_llm(
                retry_messages,
                ai_service,
                json_output=True,
                response_schema=ExecutionPlan,
            )
            try:
                execution_plan = ExecutionPlan.model_validate_with_agent_names(
                    response_data,
                    allowed_agent_names,
                )
            except (pydantic.ValidationError, ValueError):
                repaired = self._repair_execution_plan(response_data)
                if repaired is not None:
                    self.logger.warning("Recovered invalid execution plan by repairing steps after retry.")
                    return repaired
                raise
        
        # Debate step normalization is handled in the team executor
        
        self.logger.debug(f"Generated execution plan with {len(execution_plan.steps)} steps")
        
        return execution_plan
