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
Bear Research Agent.
Takes the bearish side in a research debate: argues for caution, lower allocation, or risk reduction.
"""
import json
import typing

import octobot_agents as agent
from octobot_services.enums import AIModelPolicy

from .models import ResearchDebateOutput


class BearResearchAIAgentChannel(agent.AbstractAgentChannel):
    """Channel for BearResearchAIAgentProducer."""
    OUTPUT_SCHEMA = ResearchDebateOutput


class BearResearchAIAgentConsumer(agent.AbstractAIAgentChannelConsumer):
    """Consumer for BearResearchAIAgentProducer."""
    pass


class BearResearchAIAgentProducer(agent.AbstractAIAgentChannelProducer):
    """
    Bear researcher: argues the bearish case in a research debate.
    Uses strategy data, portfolio context, and debate history to argue for caution.
    """

    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = BearResearchAIAgentChannel
    AGENT_CONSUMER = BearResearchAIAgentConsumer
    MODEL_POLICY = AIModelPolicy.FAST

    def __init__(self, channel=None, model=None, max_tokens=None, temperature=None, **kwargs):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    def _get_default_prompt(self) -> str:
        return """You are the Bear Researcher in an investment research debate.
Your role is to argue the bearish case: reasons to reduce exposure, be cautious, or favor defensive allocation.

You receive:
1. Initial state: portfolio, strategy data (global and per-crypto), current distribution.
2. Debate history: previous messages from you and the Bull researcher.

Respond with a short, focused argument (one paragraph) for the bearish side. Consider risks, overvaluation, and downside.
Output JSON with: "message" (your argument text), optionally "reasoning" (brief)."""

    def _build_user_prompt(self, input_data: typing.Dict[str, typing.Any]) -> str:
        initial_state = input_data.get("_initial_state") or {}
        debate_history = input_data.get("_debate_history") or []
        round_num = input_data.get("_debate_round", 1)
        state_preview = json.dumps({
            "crypto_strategy_data_keys": list((initial_state.get("crypto_strategy_data") or {}).keys()),
            "global_strategy_data_keys": list((initial_state.get("global_strategy_data") or {}).keys()),
            "current_distribution": initial_state.get("current_distribution"),
            "reference_market": initial_state.get("reference_market"),
        }, indent=2)
        debate_text = "\n".join(
            f"[{e.get('agent_name', '?')}]: {e.get('message', '')[:300]}"
            for e in debate_history
        ) if debate_history else "No previous messages."
        return f"""Round {round_num}

Initial state (summary):
{state_preview}

Debate so far:
{debate_text}

Your bearish argument (short, one paragraph):"""

    async def execute(self, input_data: typing.Any, ai_service) -> typing.Any:
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": self._build_user_prompt(input_data)},
        ]
        response_data = await self._call_llm(messages, ai_service, json_output=True, response_schema=ResearchDebateOutput)
        out = ResearchDebateOutput(**response_data)
        
        # Check if the model contains an error
        if out.error:
            raise ValueError(f"LLM failed to return valid bearish research: {out.error}")
        if not out.message:
            raise ValueError("LLM returned empty message for bearish research")
        
        return {"message": out.message, "reasoning": out.reasoning}
