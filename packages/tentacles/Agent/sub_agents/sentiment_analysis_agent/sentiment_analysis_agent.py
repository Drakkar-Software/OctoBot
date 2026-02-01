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

import octobot_agents as agent

from .models import SentimentAnalysisOutput


class SentimentAnalysisAIAgentChannel(agent.AbstractAgentChannel):
    """Channel for SentimentAnalysisAIAgentProducer."""
    OUTPUT_SCHEMA = SentimentAnalysisOutput


class SentimentAnalysisAIAgentConsumer(agent.AbstractAIAgentChannelConsumer):
    """Consumer for SentimentAnalysisAIAgentProducer."""
    pass


class SentimentAnalysisAIAgentProducer(agent.AbstractAIAgentChannelProducer):
    """Producer specialized in sentiment analysis evaluation."""
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = SentimentAnalysisAIAgentChannel
    AGENT_CONSUMER = SentimentAnalysisAIAgentConsumer

    def __init__(self, channel, **kwargs):
        super().__init__(channel, **kwargs)

    def _get_default_prompt(self) -> str:
        return (
            "You are a Social Sentiment Analysis AI expert.\n\n"
            "Follow these steps:\n"
            "1. Review diverse social signals: news sentiment, market buzz, community discussions, global indicators\n"
            "2. Assess overall market mood objectively: Determine if sentiment is bullish, bearish, or neutral\n"
            "3. Consider signal sources: Institutional news (ETFs, regulations) outweighs social media noise\n"
            "4. Evaluate sentiment strength and consistency across sources\n"
            "5. Calculate eval_note using full range from -1 to 1: Most markets show neutral to mildly bullish/bearish sentiment\n"
            "6. Assess confidence (0-1) based on data quality and signal clarity\n"
            "7. Provide detailed analysis explaining the score\n\n"
            "IMPORTANT: Positive regulatory developments are MAJOR bullish signals. Institutional news outweighs social media sentiment.\n"
            "Markets are rarely extremely bullish or bearish - use extreme values (-1/1) only for very strong, consistent signals.\n\n"
            "MANDATORY FIELDS (always include):\n"
            "- eval_note: float between -1 (very bearish sentiment) to 1 (very bullish sentiment)\n"
            "- confidence: float between 0 (low confidence) to 1 (high confidence)\n"
            "- description: detailed explanation of the sentiment analysis\n"
            "- sentiment_score: float between -1 to 1 for aggregate sentiment\n\n"
            "OPTIONAL FIELDS (only include if available):\n"
            "- sources_analyzed: list of sentiment sources examined (e.g., 'Twitter', 'News', 'Crypto Forums') - Leave empty if not clearly identified\n"
            "- key_mentions: list of key topics/assets/events mentioned - Leave empty if none stand out\n"
            "- market_implications: string describing sentiment impact on market - Leave empty if unclear\n"
            "- recommendations: list of action recommendations based on sentiment - Leave empty if none\n\n"
            "If you lack data for any optional field, omit it from the response (leave as null).\n"
            "Output only valid JSON matching the SentimentAnalysisOutput schema."
        )

    async def execute(self, input_data, ai_service) -> dict:
        """Evaluate aggregated sentiment analysis data."""
        aggregated_data = input_data
        if not aggregated_data:
            return {
                "eval_note": 0,
                "eval_note_description": "No sentiment analysis data available",
                "confidence": 0,
            }

        data_str = json.dumps(aggregated_data, indent=2)

        messages = [
            ai_service.create_message("system", self.prompt),
            ai_service.create_message(
                "user",
                f"Sentiment analysis data:\n{data_str}\n\n"
                "Provide evaluation as JSON matching the SentimentAnalysisOutput schema. "
                "Include mandatory fields (eval_note, confidence, description, sentiment_score). "
                "Include optional fields only if you have data for them.",
            ),
        ]

        try:
            # Uses SentimentAnalysisAIAgentChannel.OUTPUT_SCHEMA by default
            parsed = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            eval_note = float(parsed.get("eval_note", 0))
            eval_note_description = parsed.get("description", "Sentiment analysis")
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
            self.logger.error(f"Error in sentiment analysis: {e}")
            return {
                "eval_note": 0,
                "eval_note_description": f"Error in sentiment analysis: {str(e)}",
                "confidence": 0,
            }
