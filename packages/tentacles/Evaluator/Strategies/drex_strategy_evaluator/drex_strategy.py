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
import os

import aiohttp

import octobot.constants as octobot_constants
import octobot_evaluators.enums as evaluators_enums
import tentacles.Evaluator.Strategies.ai_strategies_evaluator as ai_strategies_evaluator

# attribution sent with every Drex request
CLIENT = f"octobot/{octobot_constants.LONG_VERSION}"
STANCES = ["Strong sell", "Sell", "Neutral", "Buy", "Strong buy"]
# evaluators keep their own sign: OctoBot's TA and real-time evaluators use -1 for buy, social ones +1 for positive
EVAL_NOTE_MEANINGS = {
    evaluators_enums.EvaluatorMatrixTypes.TA.value: "-1 is a buy signal (bullish), 1 is a sell signal (bearish)",
    evaluators_enums.EvaluatorMatrixTypes.REAL_TIME.value: "-1 is a buy signal (bullish), 1 is a sell signal (bearish)",
    evaluators_enums.EvaluatorMatrixTypes.SOCIAL.value:
        "-1 is negative sentiment or falling market data, 1 is positive sentiment or rising market data",
}


class DrexStrategyMixin:
    async def _run_agents_analysis(self, aggregated_data, missing_data_types, ai_service):
        if api_key := os.getenv("NACE_API_KEY"):
            try:
                eval_note, description = await self._ask_drex(api_key, aggregated_data, missing_data_types)
            except (aiohttp.ClientError, TimeoutError, KeyError, TypeError, ValueError) as err:
                self.logger.warning(
                    f"Drex request failed, asking the LLM agents instead: {err} ({err.__class__.__name__})"
                )
            else:
                self.logger.info(f"Drex's evaluation is {eval_note:+.2f}: {description}")
                return eval_note, description
        return await super()._run_agents_analysis(aggregated_data, missing_data_types, ai_service)

    async def _ask_drex(self, api_key, aggregated_data, missing_data_types) -> tuple[float, str]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{os.getenv('NACE_BASE_URL', 'https://console.nace.ai').rstrip('/')}/v1/systemone",
                headers={"Authorization": f"Bearer {api_key}", "X-Nace-Client": CLIENT, "User-Agent": CLIENT},
                json={
                    "model": os.getenv("NACE_DEFAULT_DECISION_MODEL", "drex-max-finance"),
                    "state": {
                        "evaluations by evaluator type": aggregated_data,
                        "eval_note meaning by evaluator type": {
                            eval_type: EVAL_NOTE_MEANINGS[eval_type]
                            for eval_type in aggregated_data if eval_type in EVAL_NOTE_MEANINGS
                        },
                        "missing evaluator types": missing_data_types,
                    },
                    "questions": {
                        "stance": {
                            "type": "score",
                            "instructions": "Taking every evaluation into account, "
                                            "what trading stance do they support?",
                            "criteria": STANCES,
                        },
                    },
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                answer = (await response.json())["answers"]["stance"]
        # same scale as the LLM agents' summary: -1 strong sell to 1 strong buy
        eval_note = float(answer["score"]) / 2 - 1
        probabilities = [float(answer["probabilities"][str(index)]) for index in range(len(STANCES))]
        description = f"Drex: {STANCES[probabilities.index(max(probabilities))]} (" + ", ".join(
            f"{stance} {probability:.0%}" for stance, probability in zip(STANCES, probabilities)
        ) + ")"
        return eval_note, description


class CryptoDrexStrategyEvaluator(DrexStrategyMixin, ai_strategies_evaluator.CryptoLLMAIStrategyEvaluator):
    pass


class GlobalDrexStrategyEvaluator(DrexStrategyMixin, ai_strategies_evaluator.GlobalLLMAIStrategyEvaluator):
    pass
