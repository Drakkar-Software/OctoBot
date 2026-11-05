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
import octobot_evaluators.evaluators as evaluators
import tentacles.Evaluator.TA.ai_evaluator as ai_evaluator

# attribution sent with every Drex request
CLIENT = f"octobot/{octobot_constants.LONG_VERSION}"


class DrexEvaluator(ai_evaluator.GPTEvaluator):
    @classmethod
    def get_signals_history_type(cls):
        # Drex also answers in backtesting: stored GPT signals are only needed without a Nace key
        return None if os.getenv("NACE_API_KEY") else super().get_signals_history_type()

    async def load_and_save_user_inputs(self, bot_id: str) -> dict:
        if not os.getenv("NACE_API_KEY"):
            return await super().load_and_save_user_inputs(bot_id)
        # skip GPTEvaluator's GPT models fetch and its "disabled in backtesting" error
        self.is_backtesting = self._is_in_backtesting()
        return await evaluators.TAEvaluator.load_and_save_user_inputs(self, bot_id)

    async def ask_gpt(self, preprompt, inputs, symbol, time_frame, candle_time) -> str:
        if api_key := os.getenv("NACE_API_KEY"):
            try:
                up_probability = await self._ask_drex(api_key, inputs, time_frame)
            except (aiohttp.ClientError, TimeoutError, KeyError, TypeError, ValueError) as err:
                self.logger.warning(
                    f"Drex request failed for {symbol} on {time_frame}, asking GPT instead: {err} "
                    f"({err.__class__.__name__})"
                )
            else:
                # same "{up or down} {confidence%}" format as GPT answers: parsed by GPTEvaluator.evaluate
                answer = f"up {round(up_probability * 100)}%" if up_probability >= 0.5 \
                    else f"down {round((1 - up_probability) * 100)}%"
                self.logger.info(
                    f"Drex's answer is '{answer}' for {symbol} on {time_frame} with input: {inputs} "
                    f"and candle_time: {candle_time}"
                )
                return answer
        return await super().ask_gpt(preprompt, inputs, symbol, time_frame, candle_time)

    async def _ask_drex(self, api_key, inputs, time_frame) -> float:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{os.getenv('NACE_BASE_URL', 'https://console.nace.ai').rstrip('/')}/v1/systemone",
                headers={"Authorization": f"Bearer {api_key}", "X-Nace-Client": CLIENT, "User-Agent": CLIENT},
                json={
                    "model": os.getenv("NACE_DEFAULT_DECISION_MODEL", "drex-max-finance"),
                    "state": {
                        "time_frame": time_frame,
                        "indicator": self.indicator,
                        "source": self.source,
                        "data (oldest first)": inputs,
                    },
                    "questions": {
                        "up": {
                            "type": "noul",
                            "instructions": "Will the price go up over the next candle?",
                            "criteria": {
                                "true": "The next candle closes above the last close",
                                "false": "The next candle closes at or below the last close",
                            },
                        },
                    },
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                return float((await response.json())["answers"]["up"]["noul"])
