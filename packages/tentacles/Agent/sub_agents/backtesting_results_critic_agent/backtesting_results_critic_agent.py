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
Backtesting Results Critic Agent.
Analyzes backtesting results (portfolio, trades, profitability) and produces critic analysis
for learning and strategy improvement.
"""
import json
import typing

import octobot_commons.logging as logging
import octobot_agents.models as models
import octobot_services.services.abstract_ai_service as abstract_ai_service

from octobot_agents.team.critic import AICriticAgentProducer


class BacktestingResultsAICriticAgentProducer(AICriticAgentProducer):
    """
    Critic agent dedicated to backtesting results.
    Takes a backtesting report (profitability, portfolio, trades, etc.) and produces
    issues, improvements, and summary for strategy refinement.
    """

    def __init__(
        self,
        channel: typing.Optional[typing.Any] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens or 3000,
            temperature=temperature if temperature is not None else 0.3,
            self_improving=self_improving,
            **kwargs,
        )
        self.logger = logging.get_logger(self.__class__.__name__)

    def _get_default_prompt(self) -> str:
        return """You are a Backtesting Results Critic for a trading system.
You receive a backtesting report: profitability, starting/end portfolio, trades, market comparison.

Your role:
1. Identify issues: poor risk-adjusted returns, concentration risks, timing issues, overtrading.
2. Suggest improvements: allocation changes, risk limits, entry/exit rules.
3. Summarize: short actionable summary and key lessons.

Output a JSON object matching CriticAnalysis:
- "issues": list of general problems (team-level)
- "errors": list of errors encountered (can be empty)
- "inconsistencies": list of inconsistencies (e.g. portfolio vs trades)
- "optimizations": list of optimization opportunities
- "summary": overall analysis summary (2-4 sentences)
- "agent_improvements": {} (empty dict; this critic does not target specific agents)
"""

    async def execute(
        self,
        input_data: typing.Union[models.CriticInput, typing.Dict[str, typing.Any]],
        ai_service: abstract_ai_service.AbstractAIService,
    ) -> models.CriticAnalysis:
        report = input_data if isinstance(input_data, dict) else getattr(input_data, "backtesting_report", input_data)
        if isinstance(input_data, dict) and "backtesting_report" in input_data:
            report = input_data["backtesting_report"]
        report_str = json.dumps(report, indent=2, default=str) if report else "No report."

        messages = [
            {"role": "system", "content": self._get_default_prompt()},
            {"role": "user", "content": f"Backtesting report:\n{report_str}\n\nAnalyze and return CriticAnalysis JSON."},
        ]

        try:
            response = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
                response_schema=models.CriticAnalysis,
            )
        except Exception as e:
            self.logger.exception(f"Backtesting critic LLM call failed: {e}")
            return models.CriticAnalysis(
                issues=[f"Critic analysis failed: {e}"],
                errors=[],
                inconsistencies=[],
                optimizations=[],
                summary="Backtesting critic could not complete analysis.",
                agent_improvements={},
            )

        if isinstance(response, dict):
            return models.CriticAnalysis(
                issues=response.get("issues", []),
                errors=response.get("errors", []),
                inconsistencies=response.get("inconsistencies", []),
                optimizations=response.get("optimizations", []),
                summary=response.get("summary", ""),
                agent_improvements=response.get("agent_improvements", {}),
            )
        return response
