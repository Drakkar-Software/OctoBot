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
Bull Research Agent.
Takes the bullish side in a research debate: argues for higher allocation / more risk based on strategy data.
"""
import json
import typing

import octobot_agents.agent.channels.ai_agent as ai_agent_channels
from octobot_services.enums import AIModelPolicy

from .models import ResearchDebateOutput


class BullResearchAIAgentChannel(ai_agent_channels.AbstractAIAgentChannel):
    OUTPUT_SCHEMA = ResearchDebateOutput


class BullResearchAIAgentConsumer(ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class BullResearchAIAgentProducer(ai_agent_channels.AbstractAIAgentChannelProducer):
    """
    Bull researcher: argues the bullish case in a research debate.
    Uses strategy data, portfolio context, and debate history to make a short argument.
    """

    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = BullResearchAIAgentChannel
    AGENT_CONSUMER = BullResearchAIAgentConsumer
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
        return """You are the Bull Researcher in an investment research debate.
Your role is to argue the bullish case: reasons to increase exposure, take more risk, or favor allocation to assets.

You receive:
1. Initial state: portfolio, strategy data (global and per-crypto), current distribution.
2. Debate history: previous messages from you and the Bear researcher.

Respond with a short, focused argument (one paragraph) for the bullish side. Consider signals, momentum, and opportunities.
Return ONLY valid JSON (no markdown, no code fences, no extra text).
Required JSON keys:
- "message": string (required)
- "reasoning": string (optional)
- "error": null or empty string (optional; omit unless you cannot answer)

CRITICAL: Do NOT include any other keys. Do NOT include "asset" or lists.
Example:
{"message": "Bullish argument...", "reasoning": "Brief rationale."}"""

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

Your bullish argument (short, one paragraph):"""

    async def execute(self, input_data: typing.Any, ai_service) -> typing.Any:
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": self._build_user_prompt(input_data)},
        ]
        try:
            response_data = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
                response_schema=ResearchDebateOutput,
            )
            out = ResearchDebateOutput(**response_data)
        except Exception as e:
            self.logger.warning(f"LLM call failed with error: {e}. Attempting to extract JSON from error message.")
            extracted_json = ResearchDebateOutput.recover_json_from_error(e)
            if extracted_json:
                try:
                    out = ResearchDebateOutput(**extracted_json)
                except Exception as e2:
                    self.logger.error(f"Failed to parse extracted JSON into ResearchDebateOutput: {e2}")
                    raise ValueError(f"LLM call failed and extracted JSON is invalid: {e2}") from e2
            else:
                self.logger.error("Failed to extract JSON from LLM error message.")
                raise ValueError(f"LLM call failed and no valid JSON could be extracted: {e}") from e
        
        # Check if the model contains an error
        if not out.message and out.reasoning:
            out.message = out.reasoning
        if out.error:
            raise ValueError(f"LLM failed to return valid bullish research: {out.error}")
        if not out.message:
            self.logger.warning("Bull research agent returned empty message; using fallback.")
            out.message = "No bullish argument generated by the LLM."
        
        return {"message": out.message, "reasoning": out.reasoning}
