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

import octobot_commons.logging as logging

import octobot_services.enums as services_enums

import octobot_agents.agent.channels.agent as agent_channels
import octobot_agents.agent.channels.ai_agent as ai_agent_channels
import octobot_agents.models as models
import octobot_agents.constants as constants
import octobot_agents.utils.retry as retry_utils

class TeamManagerMixin:
    """
    Mixin that provides team manager functionality.

    Both managers are agents and follow the agent pattern with channels.
    """

    async def execute(
        self,
        input_data: typing.Union[models.ManagerInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any
    ) -> typing.Union[models.ExecutionPlan, models.ManagerResult]:
        """
        Execute the manager's logic and return an execution plan or terminal results.

        Args:
            input_data: Contains {"team_producer": team_producer, "initial_data": initial_data, "instructions": instructions}
            ai_service: The AI service instance (for AI managers)

        Returns:
            ExecutionPlan with steps for team execution (plan-driven) or models.ManagerResult with terminal results (tools-driven)
        """
        raise NotImplementedError("execute must be implemented by subclasses")

    async def send_instruction_to_agent(
        self,
        agent: ai_agent_channels.AbstractAIAgentChannelProducer,
        instruction: typing.Dict[str, typing.Any],
    ) -> None:
        """
        Send instruction to an agent via channel.modify().

        Args:
            agent: The agent producer to send instructions to
            instruction: Dict with modification constants as keys (e.g., {MODIFICATION_ADDITIONAL_INSTRUCTIONS: "..."})
        """
        if agent.channel is None:
            self.logger.debug(f"Agent {agent.name} has no channel, skipping instructions")
            return

        await agent.channel.modify(**instruction)


class ManagerAgentChannel(agent_channels.AbstractAgentChannel):
    OUTPUT_SCHEMA = models.ExecutionPlan


class ManagerAgentConsumer(agent_channels.AbstractAgentChannelConsumer):
    pass


class ManagerAgentProducer(TeamManagerMixin, agent_channels.AbstractAgentChannelProducer):
    AGENT_CHANNEL = ManagerAgentChannel
    AGENT_CONSUMER = ManagerAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[ManagerAgentChannel] = None,
        **kwargs,
    ):
        super().__init__(channel, **kwargs)
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


class AIManagerAgentChannel(ManagerAgentChannel, ai_agent_channels.AbstractAIAgentChannel):
    pass


class AIManagerAgentConsumer(ManagerAgentConsumer, ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class AIManagerAgentProducer(ManagerAgentProducer, ai_agent_channels.AbstractAIAgentChannelProducer):

    AGENT_CHANNEL = AIManagerAgentChannel
    AGENT_CONSUMER = AIManagerAgentConsumer
    MODEL_POLICY = services_enums.AIModelPolicy.REASONING

    def __init__(
        self,
        channel: typing.Optional[AIManagerAgentChannel] = None,
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
            **kwargs
        )
        self.name = self.__class__.__name__


class AIPlanManagerAgentChannel(AIManagerAgentChannel):
    pass


class AIPlanManagerAgentConsumer(AIManagerAgentConsumer):
    pass


class AIPlanManagerAgentProducer(AIManagerAgentProducer):

    AGENT_CHANNEL = AIPlanManagerAgentChannel
    AGENT_CONSUMER = AIPlanManagerAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[AIPlanManagerAgentChannel] = None,
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
            **kwargs
        )

class AIToolsManagerAgentChannel(AIManagerAgentChannel):
    pass


class AIToolsManagerAgentConsumer(AIManagerAgentConsumer):
    pass


class AIToolsManagerAgentProducer(AIManagerAgentProducer):

    AGENT_CHANNEL = AIToolsManagerAgentChannel
    AGENT_CONSUMER = AIToolsManagerAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[AIToolsManagerAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        max_tool_calls: typing.Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        self.max_tool_calls = max_tool_calls or 50

    async def execute(
        self,
        input_data: typing.Union[models.ManagerInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any
    ) -> models.ManagerResult:
        """
        Execute tools-driven management with internal tool loop.
        
        Returns models.ManagerResult with terminal results instead of ExecutionPlan.
        """       
        team_producer = input_data.get("team_producer")
        initial_data = input_data.get("initial_data", {})
        instructions = input_data.get("instructions")
        
        if team_producer is None:
            raise ValueError("team_producer is required in input_data")
        
        # Initialize state
        state = models.ManagerState(
            completed_agents=[],
            results={},
            initial_data=initial_data,
            tool_call_history=[]
        )
        
        tool_call_count = 0
        
        while tool_call_count < self.max_tool_calls:
            # Build context for LLM
            context = self._build_tools_context(team_producer, state, instructions)
            
            # Get tool call from LLM
            tool_call = await self._get_tool_call(context, ai_service)
            
            if tool_call.tool_name == constants.TOOL_FINISH:
                # Finish tool called - return current results
                break
            
            # Execute the tool
            await self._execute_tool(tool_call, team_producer, state, ai_service)
            
            tool_call_count += 1
            state.tool_call_history.append(tool_call)
        
        return models.ManagerResult(
            completed_agents=state.completed_agents,
            results=state.results,
            tool_calls_used=tool_call_count,
        )

    def _build_tools_context(
        self,
        team_producer: typing.Any,
        state: models.ManagerState,
        instructions: typing.Optional[str]
    ) -> typing.Dict[str, typing.Any]:
        """Build context dict for LLM tool call."""
        agents_info = []
        for agent in team_producer.agents:
            agents_info.append({
                "name": agent.name,
                "channel": agent.AGENT_CHANNEL.__name__ if agent.AGENT_CHANNEL else None,
            })
        
        return {
            "team_name": team_producer.team_name,
            "agents": agents_info,
            "completed_agents": state.completed_agents,
            "current_results": state.results,
            "initial_data": state.initial_data,
            "instructions": instructions,
            "tool_call_history": [call.model_dump() for call in state.tool_call_history],
        }

    async def _get_tool_call(
        self,
        context: typing.Dict[str, typing.Any],
        ai_service: typing.Any
    ) -> models.ManagerToolCall:
        system_prompt = self._get_tools_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {self.format_data(context)}"},
        ]
        
        tools = [
            ai_service.format_tool_definition(
                name=constants.TOOL_RUN_AGENT,
                description="Run a specific agent and get its result",
                parameters=models.RunAgentArgs.model_json_schema(),
            ),
            ai_service.format_tool_definition(
                name=constants.TOOL_RUN_DEBATE,
                description="Run a debate between agents with a judge",
                parameters=models.RunDebateArgs.model_json_schema(),
            ),
            ai_service.format_tool_definition(
                name=constants.TOOL_FINISH,
                description="Finish execution and return current results",
                parameters={},
            ),
        ]
        
        response_data = await self._call_llm(
            messages,
            ai_service,
            json_output=True,
            tools=tools,
            return_tool_calls=True,
        )
        
        response_data, error_msg = models.AgentBaseModel.normalize_tool_call_response(
            response_data,
            finish_tool_name=constants.TOOL_FINISH,
        )
        if error_msg:
            raise ValueError(f"LLM failed to return valid tool calls: {error_msg}")
        return models.ManagerToolCall.model_validate(response_data)

    @retry_utils.retry_async(lambda self, agent, *args, **kwargs: agent.MAX_RETRIES)
    async def _execute_agent_with_retry(
        self,
        agent: ai_agent_channels.AbstractAIAgentChannelProducer,
        agent_input: typing.Dict[str, typing.Any],
        ai_service: typing.Any,
    ) -> typing.Any:
        return await agent.execute(agent_input, ai_service)

    def _get_tools_prompt(self) -> str:
        """Get the tools system prompt."""
        return """You are a tools-driven team manager responsible for coordinating AI agents to complete tasks.

Your goal is to analyze the available agents and current context, then use the available tools to execute the appropriate agents in sequence to achieve the team's objective.

Available tools:
- run_agent: Execute a single agent by name to get its specialized output
- run_debate: Run a debate between multiple agents with a judge to resolve complex decisions
- finish: Complete execution when you have gathered sufficient results

Important:
- Always run at least one agent before calling finish.
- Do NOT respond with plain text. You MUST respond with a tool call.
- If unsure, call finish with empty arguments.

Examples (tool calls only, no prose):
- run_agent {\"agent_name\": \"SignalAIAgentProducer\"}
- run_debate {\"debator_agent_names\": [\"BullResearchAIAgentProducer\", \"BearResearchAIAgentProducer\"], \"judge_agent_name\": \"RiskJudgeAIAgentProducer\", \"max_rounds\": 3}
- finish {}
"""

    async def _execute_tool(
        self,
        tool_call: models.ManagerToolCall,
        team_producer: typing.Any,
        state: models.ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Execute a tool and update state."""
        if tool_call.tool_name == constants.TOOL_RUN_AGENT:
            await self._tool_run_agent(tool_call.arguments, team_producer, state, ai_service)
        elif tool_call.tool_name == constants.TOOL_RUN_DEBATE:
            await self._tool_run_debate(tool_call.arguments, team_producer, state, ai_service)
        else:
            self.logger.warning(f"Unknown tool: {tool_call.tool_name}")

    async def _tool_run_agent(
        self,
        args: typing.Dict[str, typing.Any],
        team_producer: typing.Any,
        state: models.ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Run a single agent with proper input structure for team execution."""
        run_args = models.RunAgentArgs.model_validate(args)
        agent = team_producer._producer_by_name.get(run_args.agent_name)  # pylint: disable=protected-access
        
        if agent is None:
            self.logger.warning(f"Agent {run_args.agent_name} not found")
            return
        
        # Build agent input following team channel structure
        # For entry agents: pass initial_data directly
        # For non-entry agents: pass dict with predecessor results keyed by agent name
        
        # Check if agent is an entry agent (has no predecessors in the team)
        incoming_edges, _ = team_producer._build_dag()  # pylint: disable=protected-access
        agent_channel_type = agent.AGENT_CHANNEL
        predecessors = incoming_edges.get(agent_channel_type, [])
        
        if not predecessors:
            # Entry agent: receives initial_data directly
            agent_input = state.initial_data.copy()
            if run_args.instructions:
                agent_input["instructions"] = run_args.instructions
        else:
            # Non-entry agent: receives predecessor results in channel format
            agent_input = {}
            
            # Add each predecessor's result in the expected format
            for pred_channel_type in predecessors:
                # Find the predecessor agent by channel type
                pred_agent = team_producer._producer_by_channel.get(pred_channel_type)  # pylint: disable=protected-access
                if pred_agent and pred_agent.name in state.results:
                    pred_result_entry = state.results[pred_agent.name]
                    agent_input[pred_agent.name] = {
                        constants.AGENT_NAME_KEY: pred_agent.name,
                        constants.RESULT_KEY: pred_result_entry.get("result"),
                    }
            
            # Also preserve initial_state for agents that need it
            agent_input["_initial_state"] = state.initial_data.copy()
            
            if run_args.instructions:
                agent_input["instructions"] = run_args.instructions
        
        result = await self._execute_agent_with_retry(agent, agent_input, ai_service)
        state.completed_agents.append(run_args.agent_name)
        state.results[run_args.agent_name] = {
            "agent_name": run_args.agent_name,
            "result": result,
        }

    async def _tool_run_debate(
        self,
        args: typing.Dict[str, typing.Any],
        team_producer: typing.Any,
        state: models.ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Run a debate."""
        debate_args = models.RunDebateArgs.model_validate(args)
        
        # Use team's debate method
        debate_results, completed = await team_producer._run_debate(  # pylint: disable=protected-access
            debate_config={
                "debator_agent_names": debate_args.debator_agent_names,
                "judge_agent_name": debate_args.judge_agent_name,
                "max_rounds": debate_args.max_rounds,
            },
            initial_data=state.initial_data,
            results=state.results,
            completed_agents=set(state.completed_agents),
            incoming_edges={},  # Simplified
        )
        
        # Update state
        state.completed_agents.extend(completed - set(state.completed_agents))
        state.results.update(debate_results)
