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
Risk Judge Agent.
Implements AIJudgeAgentProducer: evaluates risk debate history and decides continue or exit with summary.
"""
import typing

import octobot_commons.logging as logging
import octobot_agents.models as models
from octobot_agents.enums import JudgeDecisionType
import octobot_services.services.abstract_ai_service as abstract_ai_service

from octobot_services.enums import AIModelPolicy
from octobot_agents.team.judge import AIJudgeAgentProducer


class RiskJudgeAIAgentProducer(AIJudgeAgentProducer):
    """
    Risk judge agent: evaluates debate history from risk debators (e.g. risky/safe/neutral)
    and decides whether to continue the debate or exit with a risk synthesis summary.
    """
    MODEL_POLICY = AIModelPolicy.REASONING

    def __init__(
        self,
        channel: typing.Optional[typing.Any] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens or 2000,
            temperature=temperature if temperature is not None else 0.3,
            **kwargs,
        )
        self.logger = logging.get_logger(self.__class__.__name__)

    def _get_default_prompt(self) -> str:
        return """You are a Risk Judge in a portfolio risk debate.
You receive a debate history: messages from debators (e.g. risky analyst, safe analyst, neutral analyst) arguing about portfolio risk.

Your role:
1. Evaluate whether the debate has reached a clear conclusion or needs more rounds.
2. If views have converged or max useful exchange reached, decide "exit" and provide a short synthesis summary (risk level and key recommendations).
3. If important points are still unresolved, decide "continue" and briefly explain why.

Output a JSON object with:
- "decision": exactly "continue" or "exit"
- "reasoning": short explanation for your decision
- "summary": when decision is "exit", a concise risk synthesis (overall risk level and top recommendations); when "continue", null or empty
"""

    async def execute(
        self,
        input_data: typing.Union[models.JudgeInput, typing.Dict[str, typing.Any]],
        ai_service: abstract_ai_service.AbstractAIService,
    ) -> models.JudgeDecision:
        debate_history = input_data.get("debate_history", [])
        debator_agent_names = input_data.get("debator_agent_names", [])
        current_round = input_data.get("current_round", 1)
        max_rounds = input_data.get("max_rounds", 3)

        if not debate_history:
            return models.JudgeDecision(
                decision=JudgeDecisionType.EXIT.value,
                reasoning="No debate history; exiting.",
                summary="No risk debate content.",
            )

        debate_text = "\n\n".join(
            f"[Round {e.get('round', '?')}] {e.get('agent_name', '?')}: {e.get('message', '')}"
            for e in debate_history
        )
        user_content = f"""Debate history (round {current_round} of {max_rounds}, debators: {debator_agent_names}):

{debate_text}

Decide: continue the debate or exit with a risk synthesis?"""

        messages = [
            {"role": "system", "content": self._get_default_prompt()},
            {"role": "user", "content": user_content},
        ]

        try:
            response = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
                response_schema=models.JudgeDecision,
            )
        except Exception as e:
            self.logger.exception(f"Risk judge LLM call failed: {e}")
            return models.JudgeDecision(
                decision=JudgeDecisionType.EXIT.value,
                reasoning=f"Error: {e}",
                summary=None,
            )

        if isinstance(response, dict):
            return models.JudgeDecision(
                decision=response.get("decision", JudgeDecisionType.EXIT.value),
                reasoning=response.get("reasoning", ""),
                summary=response.get("summary"),
            )
        return response
