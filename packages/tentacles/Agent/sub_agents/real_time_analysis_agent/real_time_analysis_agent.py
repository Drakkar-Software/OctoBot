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

from .models import RealTimeAnalysisOutput


class RealTimeAnalysisAIAgentChannel(ai_agent_channels.AbstractAIAgentChannel):
    OUTPUT_SCHEMA = RealTimeAnalysisOutput


class RealTimeAnalysisAIAgentConsumer(ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class RealTimeAnalysisAIAgentProducer(ai_agent_channels.AbstractAIAgentChannelProducer):
    """Producer specialized in real-time market analysis."""
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = RealTimeAnalysisAIAgentChannel
    AGENT_CONSUMER = RealTimeAnalysisAIAgentConsumer

    def __init__(self, channel, **kwargs):
        super().__init__(channel, **kwargs)

    def _get_default_prompt(self) -> str:
        return (
            "You are a Real-Time Market Analysis AI expert. Follow these steps to analyze the provided real-time evaluator signals:\n"
            "1. Examine real-time data comprehensively: Review order book dynamics, recent trades, price velocity, and market depth.\n"
            "2. Assess market momentum: Determine current buying/selling pressure, accumulation/distribution patterns, and directional bias.\n"
            "3. Evaluate market microstructure: Consider bid-ask spreads, order book imbalance, and trade flow characteristics.\n"
            "4. Calculate momentum eval_note: Use the full range from -1 (strong selling pressure) to 1 (strong buying pressure), but most real-time data shows neutral to mild momentum.\n"
            "5. Assess confidence (0-1) based on data quality: Higher confidence for strong, consistent signals; lower for noisy or conflicting data.\n"
            "6. Provide detailed description: Explain current market dynamics, momentum indicators, and short-term outlook.\n\n"
            "Important: Real-time momentum is rarely extreme. Use extreme values (-1/1) only for very strong, sustained pressure.\n\n"
            "MANDATORY FIELDS (always include):\n"
            "- eval_note: float between -1 (strong selling pressure) to 1 (strong buying pressure)\n"
            "- confidence: float between 0 (low confidence) to 1 (high confidence)\n"
            "- description: detailed explanation of current market momentum and dynamics\n\n"
            "OPTIONAL FIELDS (only include if available):\n"
            "- price_momentum: float for price momentum strength (-1 to 1) - Leave empty if not clearly identifiable\n"
            "- current_status: string like 'accumulating', 'distributing', 'consolidating' - Leave empty if unclear\n"
            "- volume_signal: string describing volume patterns - Leave empty if no strong volume signals\n"
            "- urgency_level: string like 'low', 'medium', 'high' - Leave empty if no clear urgency\n"
            "- critical_events: list of critical market events affecting momentum - Leave empty if none\n"
            "- recommendations: list of action recommendations based on real-time analysis - Leave empty if none\n\n"
            "If you lack data for any optional field, omit it from the response (leave as null).\n"
            "Output only valid JSON matching the RealTimeAnalysisOutput schema."
        )

    async def execute(self, input_data, ai_service) -> dict:
        """Evaluate aggregated real-time market data."""
        aggregated_data = input_data
        if not aggregated_data:
            return {
                "eval_note": 0,
                "eval_note_description": "No real-time market data available",
                "confidence": 0,
            }

        data_str = json.dumps(aggregated_data, indent=2)

        messages = [
            ai_service.create_message("system", self.prompt),
            ai_service.create_message(
                "user",
                f"Real-time market data:\n{data_str}\n\n"
                "Provide evaluation as JSON matching the RealTimeAnalysisOutput schema. "
                "Include mandatory fields (eval_note, confidence, description). "
                "Include optional fields only if you have data for them.",
            ),
        ]

        try:
            # Uses RealTimeAnalysisAIAgentChannel.OUTPUT_SCHEMA by default
            parsed = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            eval_note = float(parsed.get("eval_note", 0))
            eval_note_description = parsed.get("description", "Real-time analysis")
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
            self.logger.error(f"Error in real-time analysis: {e}")
            return {
                "eval_note": 0,
                "eval_note_description": f"Error in real-time analysis: {str(e)}",
                "confidence": 0,
            }
