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
Signal Agent.
Analyzes all cryptocurrencies and generates both individual and synthesized signals.
Combines per-crypto analysis with overall market signal synthesis in a single agent.
"""
import json
import typing

from pydantic import BaseModel, model_validator
from typing import List

import octobot_agents as agent
from octobot_agents.models import AgentBaseModel
from octobot_agents.utils.extractor import extract_json_from_content
from octobot_services.enums import AIModelPolicy

from .state import AIAgentState
from .models import CryptoSignalOutput, SignalSynthesisOutput


class SignalAgentOutput(AgentBaseModel):
    """Output schema for SignalAIAgentProducer."""
    __strict_json_schema__ = True
    
    per_crypto_signals: List[CryptoSignalOutput]
    synthesis: SignalSynthesisOutput

    @model_validator(mode="after")
    def ensure_output_present(self):
        if not self.per_crypto_signals:
            raise ValueError("per_crypto_signals must not be empty")
        if not self.synthesis:
            raise ValueError("synthesis must not be empty")
        return self


class SignalAIAgentChannel(agent.AbstractAgentChannel):
    """Channel for SignalAIAgentProducer."""
    OUTPUT_SCHEMA = SignalAgentOutput


class SignalAIAgentConsumer(agent.AbstractAIAgentChannelConsumer):
    """Consumer for SignalAIAgentProducer."""
    pass


class SignalAIAgentProducer(agent.AbstractAIAgentChannelProducer):
    """
    Signal agent producer that analyzes all cryptocurrencies and synthesizes signals.
    
    This agent:
    1. Analyzes each cryptocurrency against all available data
    2. Generates individual signals with confidence levels
    3. Synthesizes signals across all cryptos to identify market consensus
    """
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = SignalAIAgentChannel
    AGENT_CONSUMER = SignalAIAgentConsumer
    ENABLE_MEMORY = True
    MODEL_POLICY = AIModelPolicy.FAST
    
    def __init__(self, channel, model=None, max_tokens=None, temperature=None, **kwargs):
        """
        Initialize the signal agent producer.
        
        Args:
            channel: The channel this producer is registered to.
            model: LLM model to use.
            max_tokens: Maximum tokens for response.
            temperature: Temperature for LLM randomness.
        """
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
    
    def _get_default_prompt(self) -> str:
        """Return the default system prompt."""
        return """
You are a Comprehensive Signal Analysis Agent for cryptocurrency portfolio management.
Your task is to analyze all tracked cryptocurrencies and generate both individual trading signals and synthesized market signals.

## Your Dual Role

### Part 1: Per-Cryptocurrency Analysis
- Analyze each cryptocurrency provided
- Consider global market strategy data and crypto-specific data
- Consider current portfolio holdings and open orders
- Generate a clear trading signal with confidence level
- Identify key factors driving each signal

### Part 2: Signal Synthesis (CRITICAL)
- Identify consensus across cryptocurrency signals
- Synthesize signals into clear trading instructions
- Provide overall market outlook
- Do NOT make allocation decisions - only synthesize

## Per-Crypto Signal Actions (for "action" field only)
- "buy": Strong bullish signal, recommend increasing position
- "sell": Strong bearish signal, recommend decreasing position
- "hold": Neutral signal, recommend maintaining current position
- "increase": Moderate bullish, suggest gradual increase
- "decrease": Moderate bearish, suggest gradual decrease

## CRITICAL: Synthesis Direction Values (for "direction" field ONLY)
When synthesizing signals, ALWAYS use ONLY these exact values for direction:
- "bullish": Positive market direction
- "bearish": Negative market direction
- "neutral": No clear direction

DO NOT use "buy", "sell", "hold", "increase", or "decrease" in the direction field. ONLY use: bullish, bearish, or neutral.

## Consensus Levels (for "consensus_level" field ONLY)
Must be EXACTLY one of:
- "strong": High agreement (>0.7 confidence)
- "moderate": Moderate agreement (0.5-0.7)
- "weak": Low agreement or mixed signals
- "conflicting": Opposing signals

⚠️ CRITICAL: "neutral" is NOT valid for consensus_level - use "weak" instead.
⚠️ CRITICAL: "none", "null", "n/a", and "unknown" are NOT valid for consensus_level - use "weak" instead.

If you would normally output "neutral", "none", "null", "n/a", or "unknown" for consensus_level, output "weak".

## Market Outlook (for "market_outlook" field)
Must be EXACTLY one of:
- "bullish": Majority positive signals
- "bearish": Majority negative signals
- "neutral": Balanced or low conviction
- "mixed": Strong conflicting signals
CRITICAL: market_outlook MUST be a single word enum value only.
Do NOT output explanations like "neutral with bearish risks" in market_outlook.
Put all nuance in "summary" instead.

## REQUIRED OUTPUT SCHEMA - STRICT ENFORCEMENT

The "synthesis" object MUST include ALL of these REQUIRED fields:
- "synthesized_signals": Array where each object has ALL of these REQUIRED fields:
  * "asset" (string): REQUIRED - Asset symbol like "BTC" or "ETH"
  * "direction" (string): REQUIRED - EXACTLY "bullish", "bearish", or "neutral"
  * "strength" (number): REQUIRED - Float between 0.0 and 1.0 (NOT a string like "strong")
  * "consensus_level" (string): REQUIRED - EXACTLY "strong", "moderate", "weak", or "conflicting"
  * "trading_instruction" (string): REQUIRED - Clear trading instruction text
- "market_outlook" (string): REQUIRED - EXACTLY "bullish", "bearish", "neutral", or "mixed"
- "summary" (string): REQUIRED - Summary text

CRITICAL: Every field is REQUIRED. Do NOT omit any field. "strength" must be a NUMBER, NOT a string.
CRITICAL: "synthesized_signals" MUST be a non-empty array. If you have low confidence, still provide entries with "neutral"/"weak" and low strength.

Be precise, data-driven, and base all recommendations ONLY on provided data.
"""
    
    def _format_strategy_data(self, data: dict) -> str:
        """Format strategy data for the prompt."""
        if not data:
            return "No data available"
        return json.dumps(data, indent=2, default=str)
    
    def _build_user_prompt(self, state: AIAgentState) -> str:
        """Build the user prompt with all available data."""
        global_strategy = state.get("global_strategy_data", {})
        crypto_strategy = state.get("crypto_strategy_data", {})
        cryptocurrencies = state.get("cryptocurrencies", [])
        portfolio = state.get("portfolio", {})
        orders = state.get("orders", {})
        current_distribution = state.get("current_distribution", {})

        global_filtered = dict(global_strategy)
        crypto_filtered = dict(crypto_strategy)
        try:
            global_entries = global_strategy.get("STRATEGIES", [])
        except Exception:
            global_entries = []
        try:
            crypto_entries = crypto_strategy.get("STRATEGIES", [])
        except Exception:
            crypto_entries = []

        try:
            global_filtered["STRATEGIES"] = [
                entry for entry in global_entries if entry.get("cryptocurrency") is None
            ]
        except Exception:
            pass

        try:
            crypto_filtered["STRATEGIES"] = [
                entry for entry in crypto_entries if entry.get("cryptocurrency") is not None
            ]
        except Exception:
            pass
        
        portfolio_str = json.dumps(portfolio, indent=2, default=str) if portfolio else "No portfolio data"
        orders_str = json.dumps(orders, indent=2, default=str) if orders else "No orders"
        
        return f"""
# Analyze All Cryptocurrencies and Synthesize Signals

## Global Strategy Data
{self._format_strategy_data(global_filtered)}

## Per-Cryptocurrency Strategy Data
{self._format_strategy_data(crypto_filtered)}

## Tracked Cryptocurrencies
{json.dumps(cryptocurrencies, indent=2)}

## Current Portfolio Context
{portfolio_str}

## Current Distribution
{json.dumps(current_distribution, indent=2)}

## Open Orders
{orders_str}

## Reference Market
{portfolio.get('reference_market', 'USD')}

## Task

1. **Generate Individual Signals**: For each cryptocurrency, analyze all available data and generate:
   - Trading signal (buy/sell/hold/increase/decrease)
   - Confidence level (0-1)
   - Reasoning based on strategy data
   - Market context
   - Key factors (max 5)

2. **Synthesize Signals**: After analyzing all cryptos, synthesize them into:
   - Synthesized signal for each cryptocurrency with direction and strength
   - Consensus level for each asset
   - Clear trading instructions (without specific percentages)
   - Overall market outlook
   - Summary of the synthesis

## REQUIRED OUTPUT FORMAT - STRICT SCHEMA

The "synthesis" object MUST contain:
- "synthesized_signals": Array of objects, each with ALL of these REQUIRED fields:
  * "asset" (string): Asset symbol like "BTC" or "ETH" - REQUIRED
  * "direction" (string): EXACTLY one of "bullish", "bearish", "neutral" - REQUIRED
  * "strength" (number): Float between 0.0 and 1.0 - REQUIRED (NOT a string like "strong")
  * "consensus_level" (string): EXACTLY one of "strong", "moderate", "weak", "conflicting" - REQUIRED
  * "trading_instruction" (string): Clear trading instruction text - REQUIRED
- "market_outlook" (string): EXACTLY one of "bullish", "bearish", "neutral", "mixed" - REQUIRED
- "summary" (string): Summary text - REQUIRED

CRITICAL: Every field above is REQUIRED. Do NOT omit any field. "strength" must be a NUMBER (0.0-1.0), NOT a string.

Output a JSON object with TWO sections:
- "per_crypto_signals": Array of individual signals
- "synthesis": Overall signal synthesis (with ALL required fields above)

Remember: Base ONLY on the provided data. Do not make allocation decisions - only synthesize.
"""
    
    async def execute(self, input_data: typing.Any, ai_service) -> typing.Any:
        """
        Execute signal analysis and synthesis.
        
        Args:
            input_data: The current agent state (AIAgentState).
            ai_service: The AI service instance.
            
        Returns:
            Dictionary with signal_outputs and signal_synthesis.
        """
        state = input_data
        self.logger.debug(f"Starting {self.name}...")
        
        try:
            messages = [
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": self._build_user_prompt(state)},
            ]
            
            # Uses SignalAIAgentChannel.OUTPUT_SCHEMA (SignalAgentOutput) by default
            response_data = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            
            try:
                response_data.get("synthesis", {})
            except AttributeError:
                parsed = extract_json_from_content(str(response_data))
                if parsed is None:
                    raise ValueError("Failed to parse JSON response.")
                response_data = parsed
            if not isinstance(response_data, dict):
                raise ValueError("Signal agent response must be a JSON object.")
            if "synthesis" not in response_data:
                # If the model omitted the expected wrapper, treat the whole
                # object as synthesis payload without creating recursive dicts.
                response_data = {
                    "per_crypto_signals": response_data.get("per_crypto_signals", []),
                    "synthesis": dict(response_data),
                }

            # Process per-crypto signals
            signal_outputs = {"signals": {}}
            per_crypto = response_data.get("per_crypto_signals", [])
            
            for signal_data in per_crypto:
                crypto = signal_data.get("cryptocurrency", "")
                if crypto:
                    signal_output = CryptoSignalOutput(**signal_data)
                    signal_outputs["signals"][crypto] = signal_output
            
            # Process synthesis
            synthesis_data = response_data.get("synthesis", {})
            if synthesis_data:
                synthesis_output = SignalSynthesisOutput(**synthesis_data)
            else:
                raise ValueError("Signal synthesis is missing or empty.")
            
            self.logger.debug(f"{self.name} completed successfully.")
            
            return {
                "signal_outputs": signal_outputs,
                "signal_synthesis": synthesis_output,
            }
            
        except Exception as e:
            self.logger.exception(f"Error in {self.name}: {e}")
            raise


async def run_signal_agent(state: AIAgentState, ai_service, agent_id: str = "signal-agent") -> dict:
    """
    Convenience function to run the signal agent.
    
    Args:
        state: The current agent state.
        ai_service: The AI service instance.
        agent_id: Unique identifier for the agent instance.
        
    Returns:
        State updates from the agent.
    """
    signal_agent = SignalAIAgentProducer(channel=None)
    return await signal_agent.execute(state, ai_service)
