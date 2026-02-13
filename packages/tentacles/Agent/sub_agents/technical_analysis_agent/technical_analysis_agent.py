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
import json

import octobot_agents.agent.channels.ai_agent as ai_agent_channels

from .models import TechnicalAnalysisOutput


class TechnicalAnalysisAIAgentChannel(ai_agent_channels.AbstractAIAgentChannel):
    OUTPUT_SCHEMA = TechnicalAnalysisOutput


class TechnicalAnalysisAIAgentConsumer(ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class TechnicalAnalysisAIAgentProducer(ai_agent_channels.AbstractAIAgentChannelProducer):
    """Producer specialized in technical analysis evaluation."""
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = TechnicalAnalysisAIAgentChannel
    AGENT_CONSUMER = TechnicalAnalysisAIAgentConsumer

    def __init__(self, channel, **kwargs):
        super().__init__(channel, **kwargs)

    def _get_default_prompt(self) -> str:
        return (
            "You are a Technical Analysis AI expert. Follow these steps to analyze the provided technical evaluator signals:\n"
            "1. Examine TA signals comprehensively: Review RSI, MACD, moving averages, Bollinger Bands, volume patterns, and price action.\n"
            "2. Assess trend strength and direction: Determine if signals indicate strong bullish, bearish, neutral, or mixed conditions.\n"
            "3. Consider timeframe context: Different timeframes may show different trends - longer timeframes are generally more significant.\n"
            "4. Evaluate indicator convergence/divergence: Look for confirmation across multiple indicators vs. conflicting signals.\n"
            "5. Calculate balanced eval_note: Use the full range from -1 (strong sell) to 1 (strong buy), but most markets show neutral to mildly bullish/bearish signals.\n"
            "6. Assess confidence realistically: Base confidence on signal strength, agreement (0-1 range), and data quality.\n"
            "7. Provide detailed description: Explain key indicators, their significance, and potential market implications.\n\n"
            "MANDATORY FIELDS (always include):\n"
            "- eval_note: float between -1 (strong sell) to 1 (strong buy)\n"
            "- confidence: float between 0 (low confidence) to 1 (high confidence)\n"
            "- description: detailed explanation of the analysis\n\n"
            "OPTIONAL FIELDS (only include if available):\n"
            "- trend: string like 'uptrend', 'downtrend', 'ranging' - Leave empty if unclear\n"
            "- support_level: float for identified support price level - Leave empty if not identified\n"
            "- resistance_level: float for identified resistance price level - Leave empty if not identified\n"
            "- key_indicators: list of important technical indicators and their signals - Leave empty if none clearly identified\n"
            "- recommendations: list of trading recommendations - Leave empty if none\n\n"
            "Important: Markets are rarely extremely bullish or bearish. Use extreme values (-1/1) only for very strong, consistent signals across multiple timeframes. Avoid bias toward negative signals.\n"
            "If you lack data for any optional field, omit it from the response (leave as null).\n"
            "Output only valid JSON matching the TechnicalAnalysisOutput schema."
        )

    async def execute(self, input_data, ai_service) -> dict:
        """Evaluate aggregated technical analysis data."""
        aggregated_data = input_data
        if not aggregated_data:
            return {
                "eval_note": 0,
                "eval_note_description": "No technical analysis data available",
                "confidence": 0,
            }

        data_str = json.dumps(aggregated_data, indent=2)

        messages = [
            ai_service.create_message("system", self.prompt),
            ai_service.create_message(
                "user",
                f"Technical analysis data:\n{data_str}\n\n"
                "Provide evaluation as JSON matching the TechnicalAnalysisOutput schema. "
                "Include mandatory fields (eval_note, confidence, description). "
                "Include optional fields only if you have data for them.",
            ),
        ]

        try:
            # Uses TechnicalAnalysisAIAgentChannel.OUTPUT_SCHEMA by default
            parsed = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            eval_note = float(parsed.get("eval_note", 0))
            eval_note_description = parsed.get("description", "Technical analysis")
            confidence = float(parsed.get("confidence", 0))

            # Clamp values
            eval_note = max(-1, min(1, eval_note))
            confidence = max(0, min(1, confidence))

            return {
                "eval_note": eval_note,
                "eval_note_description": eval_note_description,
                "confidence": int(confidence * 100),  # Convert to 0-100 range
            }
        except Exception as e:
            self.logger.error(f"Error in technical analysis: {e}")
            return {
                "eval_note": 0,
                "eval_note_description": f"Error in technical analysis: {str(e)}",
                "confidence": 0,
            }
