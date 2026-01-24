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
import abc
import typing
from typing import TYPE_CHECKING, Dict, Optional

import octobot_commons.logging as logging

from octobot_services.services.abstract_ai_service import AbstractAIService

from octobot_agents.agent.channels.agent import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
)
from octobot_agents.agent.channels.ai_agent import (
    AbstractAIAgentChannel,
    AbstractAIAgentChannelConsumer,
    AbstractAIAgentChannelProducer,
)
from octobot_agents.models import ExecutionPlan
from octobot_agents.models import (
    ManagerState,
    ManagerResult,
    ManagerToolCall,
    RunAgentArgs,
    RunDebateArgs,
)
from octobot_agents.constants import (
    TOOL_RUN_AGENT,
    TOOL_RUN_DEBATE,
    TOOL_FINISH,
    AGENT_NAME_KEY,
    RESULT_KEY,
)

if TYPE_CHECKING:
    from octobot_agents.models import ManagerInput
    from octobot_agents.agent.channels.ai_agent import AbstractAIAgentChannelProducer


class AbstractTeamManagerAgent(abc.ABC):
    """
    Base interface for all team managers.

    Both managers are agents and follow the agent pattern with channels.
    """

    def __init__(self):
        """Initialize the team manager agent."""
        self.logger = logging.get_logger(self.__class__.__name__)

    @abc.abstractmethod
    async def execute(
        self,
        input_data: typing.Union["ManagerInput", typing.Dict[str, typing.Any]],
        ai_service: typing.Any  # AbstractAIService - type not available at runtime
    ) -> typing.Union[ExecutionPlan, ManagerResult]:
        """
        Execute the manager's logic and return an execution plan or terminal results.

        Args:
            input_data: Contains {"team_producer": team_producer, "initial_data": initial_data, "instructions": instructions}
            ai_service: The AI service instance (for AI managers)

        Returns:
            ExecutionPlan with steps for team execution (plan-driven) or ManagerResult with terminal results (tools-driven)
        """
        raise NotImplementedError("execute must be implemented by subclasses")

    async def send_instruction_to_agent(
        self,
        agent: "AbstractAIAgentChannelProducer",
        instruction: Dict[str, typing.Any],
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


class ManagerAgentChannel(AbstractAgentChannel):
    """Base channel for manager agents."""
    __slots__ = ()
    OUTPUT_SCHEMA = ExecutionPlan


class ManagerAgentConsumer(AbstractAgentChannelConsumer):
    """Base consumer for manager agent channels."""
    __slots__ = ()


class ManagerAgentProducer(AbstractAgentChannelProducer, AbstractTeamManagerAgent):
    """Base producer for manager agents. Subclasses implement execute()."""
    __slots__ = ()

    AGENT_CHANNEL = ManagerAgentChannel
    AGENT_CONSUMER = ManagerAgentConsumer

    def __init__(self, channel: Optional[ManagerAgentChannel] = None):
        AbstractTeamManagerAgent.__init__(self)
        AbstractAgentChannelProducer.__init__(self, channel)
        self.name = self.__class__.__name__


class AIManagerAgentChannel(ManagerAgentChannel, AbstractAIAgentChannel):
    """AI channel for manager agents."""
    __slots__ = ()


class AIManagerAgentConsumer(ManagerAgentConsumer, AbstractAIAgentChannelConsumer):
    """AI consumer for manager agent channels."""
    __slots__ = ()


class AIManagerAgentProducer(ManagerAgentProducer, AbstractAIAgentChannelProducer):
    """AI producer for manager agents. Tentacles extend this and implement execute() with LLM."""
    __slots__ = ()

    AGENT_CHANNEL = AIManagerAgentChannel
    AGENT_CONSUMER = AIManagerAgentConsumer

    def __init__(
        self,
        channel: Optional[AIManagerAgentChannel] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ):
        AbstractTeamManagerAgent.__init__(self)
        AbstractAIAgentChannelProducer.__init__(
            self, channel, model=model, max_tokens=max_tokens, temperature=temperature, **kwargs
        )
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


class AIPlanManagerAgentChannel(AIManagerAgentChannel):
    """Plan-driven AI channel for manager agents."""
    __slots__ = ()


class AIPlanManagerAgentConsumer(AIManagerAgentConsumer):
    """Plan-driven AI consumer for manager agent channels."""
    __slots__ = ()


class AIPlanManagerAgentProducer(AIManagerAgentProducer):
    """Plan-driven AI producer for manager agents. execute() returns ExecutionPlan."""
    __slots__ = ()

    AGENT_CHANNEL = AIPlanManagerAgentChannel
    AGENT_CONSUMER = AIPlanManagerAgentConsumer

    def __init__(
        self,
        channel: Optional[AIPlanManagerAgentChannel] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )


# -----------------------------------------------------------------------------
# Tools-driven AI manager agent classes
# -----------------------------------------------------------------------------


class AIToolsManagerAgentChannel(AIManagerAgentChannel):
    """Tools-driven AI channel for manager agents."""
    __slots__ = ()


class AIToolsManagerAgentConsumer(AIManagerAgentConsumer):
    """Tools-driven AI consumer for manager agent channels."""
    __slots__ = ()


class AIToolsManagerAgentProducer(AIManagerAgentProducer):
    """Tools-driven AI producer for manager agents. execute() returns terminal results with internal tool loop."""
    __slots__ = ()

    AGENT_CHANNEL = AIToolsManagerAgentChannel
    AGENT_CONSUMER = AIToolsManagerAgentConsumer

    def __init__(
        self,
        channel: Optional[AIToolsManagerAgentChannel] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_tool_calls: Optional[int] = None,
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
        input_data: typing.Union["ManagerInput", typing.Dict[str, typing.Any]],
        ai_service: AbstractAIService
    ) -> ManagerResult:
        """
        Execute tools-driven management with internal tool loop.
        
        Returns ManagerResult with terminal results instead of ExecutionPlan.
        """       
        team_producer = input_data.get("team_producer")
        initial_data = input_data.get("initial_data", {})
        instructions = input_data.get("instructions")
        
        if team_producer is None:
            raise ValueError("team_producer is required in input_data")
        
        # Initialize state
        state = ManagerState(
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
            
            if tool_call.tool_name == TOOL_FINISH:
                # Finish tool called - return current results
                break
            
            # Execute the tool
            await self._execute_tool(tool_call, team_producer, state, ai_service)
            
            tool_call_count += 1
            state.tool_call_history.append(tool_call)
        
        return ManagerResult(
            completed_agents=state.completed_agents,
            results=state.results,
            tool_calls_used=tool_call_count,
        )

    def _build_tools_context(
        self,
        team_producer: typing.Any,
        state: ManagerState,
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
    ) -> ManagerToolCall:
        """Get tool call from LLM."""
        messages = [
            {"role": "system", "content": self._get_tools_prompt()},
            {"role": "user", "content": f"Context: {self.format_data(context)}"},
        ]
        
        tools = [
            ai_service.format_tool_definition(
                name=TOOL_RUN_AGENT,
                description="Run a specific agent and get its result",
                parameters=RunAgentArgs.model_json_schema(),
            ),
            ai_service.format_tool_definition(
                name=TOOL_RUN_DEBATE,
                description="Run a debate between agents with a judge",
                parameters=RunDebateArgs.model_json_schema(),
            ),
            ai_service.format_tool_definition(
                name=TOOL_FINISH,
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
        
        if response_data is None:
            raise ValueError("LLM did not return any tool calls. The manager agent requires tool calls to coordinate team execution.")
        
        return ManagerToolCall.model_validate(response_data)

    def _get_tools_prompt(self) -> str:
        """Get the tools system prompt."""
        return """You are a tools-driven team manager responsible for coordinating AI agents to complete tasks.

Your goal is to analyze the available agents and current context, then use the available tools to execute the appropriate agents in sequence to achieve the team's objective.

Available tools:
- run_agent: Execute a single agent by name to get its specialized output
- run_debate: Run a debate between multiple agents with a judge to resolve complex decisions
- finish: Complete execution when you have gathered sufficient results

Important: Always run at least one agent before calling finish. Examine the available agents and determine which ones are needed to complete the task. Start by running key agents to gather information, then call finish when you have comprehensive results."""

    async def _execute_tool(
        self,
        tool_call: ManagerToolCall,
        team_producer: typing.Any,
        state: ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Execute a tool and update state."""
        if tool_call.tool_name == TOOL_RUN_AGENT:
            await self._tool_run_agent(tool_call.arguments, team_producer, state, ai_service)
        elif tool_call.tool_name == TOOL_RUN_DEBATE:
            await self._tool_run_debate(tool_call.arguments, team_producer, state, ai_service)
        else:
            self.logger.warning(f"Unknown tool: {tool_call.tool_name}")

    async def _tool_run_agent(
        self,
        args: typing.Dict[str, typing.Any],
        team_producer: typing.Any,
        state: ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Run a single agent with proper input structure for team execution."""
        run_args = RunAgentArgs.model_validate(args)
        agent = team_producer._producer_by_name.get(run_args.agent_name)
        
        if agent is None:
            self.logger.warning(f"Agent {run_args.agent_name} not found")
            return
        
        # Build agent input following team channel structure
        # For entry agents: pass initial_data directly
        # For non-entry agents: pass dict with predecessor results keyed by agent name
        
        # Check if agent is an entry agent (has no predecessors in the team)
        incoming_edges, _ = team_producer._build_dag()
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
                pred_agent = team_producer._producer_by_channel.get(pred_channel_type)
                if pred_agent and pred_agent.name in state.results:
                    pred_result_entry = state.results[pred_agent.name]
                    agent_input[pred_agent.name] = {
                        AGENT_NAME_KEY: pred_agent.name,
                        RESULT_KEY: pred_result_entry.get("result"),
                    }
            
            # Also preserve initial_state for agents that need it
            agent_input["_initial_state"] = state.initial_data.copy()
            
            if run_args.instructions:
                agent_input["instructions"] = run_args.instructions
        
        result = await agent.execute(agent_input, ai_service)
        
        state.completed_agents.append(run_args.agent_name)
        state.results[run_args.agent_name] = {
            "agent_name": run_args.agent_name,
            "result": result,
        }

    async def _tool_run_debate(
        self,
        args: typing.Dict[str, typing.Any],
        team_producer: typing.Any,
        state: ManagerState,
        ai_service: typing.Any
    ) -> None:
        """Run a debate."""
        debate_args = RunDebateArgs.model_validate(args)
        
        # Use team's debate method
        debate_results, completed = await team_producer._run_debate(
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
