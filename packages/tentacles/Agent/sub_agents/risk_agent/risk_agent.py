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
Risk Assessment Agent.
Evaluates portfolio risk using trading API data.
"""
import json
import typing

import octobot_agents.agent.channels.ai_agent as ai_agent_channels
from octobot_services.enums import AIModelPolicy

from tentacles.Agent.sub_agents.signal_agent.state import AIAgentState
from tentacles.Agent.sub_agents.signal_agent.models import CryptoSignalOutput
from .models import RiskAssessmentOutput


class RiskAIAgentChannel(ai_agent_channels.AbstractAIAgentChannel):
    OUTPUT_SCHEMA = RiskAssessmentOutput


class RiskAIAgentConsumer(ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class RiskAIAgentProducer(ai_agent_channels.AbstractAIAgentChannelProducer):
    """
    Risk assessment agent producer that evaluates portfolio risk.
    Uses portfolio data from trading API to assess concentration, volatility, and liquidity risks.
    """
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = RiskAIAgentChannel
    AGENT_CONSUMER = RiskAIAgentConsumer
    ENABLE_MEMORY = True
    MODEL_POLICY = AIModelPolicy.FAST
    
    def __init__(self, channel, model=None, max_tokens=None, temperature=None, **kwargs):
        """
        Initialize the risk agent producer.
        
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
You are a Portfolio Risk Assessment Agent for cryptocurrency trading.
Your task is to evaluate the current portfolio risk and provide risk mitigation recommendations.

## Your Role
- Analyze the current portfolio holdings and their distribution.
- Evaluate concentration risk (over-exposure to single assets).
- Assess volatility exposure based on asset types.
- Consider liquidity risk from position sizes.
- Incorporate signal outputs from individual cryptocurrency analysis.

## Risk Levels
- "low": Portfolio is well-diversified with manageable risk
- "medium": Some concentration or volatility concerns
- "high": Significant risk factors present
- "critical": Immediate action recommended to reduce risk

## Important Rules
- Base your analysis ONLY on the provided portfolio and signal data.
- Provide actionable recommendations.
- Set realistic maximum allocation limits per asset.
- Consider the reference market (stablecoin) as the safe haven.

## Output Requirements - CRITICAL VALUE RANGES
Output a JSON object with:
- "overall_risk_level": EXACTLY one of "low", "medium", "high", "critical"
- "metrics": Object with:
  - "overall_risk_level": EXACTLY one of "low", "medium", "high", "critical"
  - "concentration_risk": Number between 0 and 1 (0=safe, 1=dangerous)
  - "volatility_exposure": Number between 0 and 1 (0=stable, 1=volatile)
  - "liquidity_risk": Number between 0 and 1 (0=liquid, 1=illiquid)
- "max_allocation_per_asset": Object mapping asset to max percentage (0-100 range, e.g., 25 means 25%)
- "min_cash_reserve": Minimum recommended cash reserve as DECIMAL between 0 and 1 (e.g., 0.1 means 10%, 0.2 means 20%)
- "recommendations": Array of risk mitigation recommendations
- "reasoning": Explanation of the risk assessment
"""
    
    def _build_user_prompt(self, state: AIAgentState) -> str:
        """Build the user prompt with portfolio data."""
        portfolio = state.get("portfolio", {})
        orders = state.get("orders", {})
        signal_outputs = state.get("signal_outputs", {}).get("signals", {})
        current_distribution = state.get("current_distribution", {})
        cryptocurrencies = state.get("cryptocurrencies", [])
        
        # Format signal summaries
        signal_summary = {}
        for crypto, signal in signal_outputs.items():
            try:
                # Try Pydantic model access
                signal_summary[crypto] = {
                    "action": signal.signal.action,
                    "confidence": signal.signal.confidence,
                    "reasoning": signal.signal.reasoning
                }
            except AttributeError:
                # It's a dict
                signal_data = signal.get("signal", {})
                signal_summary[crypto] = {
                    "action": signal_data.get("action", "unknown"),
                    "confidence": signal_data.get("confidence", 0),
                    "reasoning": signal_data.get("reasoning", "")
                }
        
        portfolio_str = json.dumps(portfolio, indent=2, default=str) if portfolio else "No portfolio data"
        orders_str = json.dumps(orders, indent=2, default=str) if orders else "No orders"
        
        return f"""
# Evaluate Portfolio Risk

## Portfolio Holdings
{portfolio_str}

## Current Distribution (percentages)
{json.dumps(current_distribution, indent=2)}

## Open Orders
{orders_str}

## Tracked Cryptocurrencies
{json.dumps(cryptocurrencies, indent=2)}

## Signal Outputs from Crypto Agents
{json.dumps(signal_summary, indent=2, default=str)}

## Reference Market
{portfolio.get('reference_market', 'USD')}

## Task
Evaluate the portfolio risk considering:
1. Concentration risk from any single asset dominating the portfolio
2. Volatility exposure based on the assets held
3. Liquidity risk from position sizes
4. Open orders that may affect risk profile
5. Signals suggesting increased volatility or directional moves

Provide risk metrics, maximum allocation limits, and mitigation recommendations as JSON.
"""
    
    async def execute(self, input_data: typing.Any, ai_service) -> typing.Any:
        """
        Execute risk assessment.
        
        Args:
            input_data: The current agent state (AIAgentState).
            ai_service: The AI service instance.
            
        Returns:
            Dictionary with risk_output.
        """
        state = input_data
        self.logger.debug(f"Starting {self.name}...")
        
        try:
            messages = [
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": self._build_user_prompt(state)},
            ]
            
            # Uses RiskAIAgentChannel.OUTPUT_SCHEMA (RiskAssessmentOutput) by default
            response_data = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            
            # Parse into model
            risk_output = RiskAssessmentOutput(**response_data)
            
            self.logger.debug(f"{self.name} completed successfully.")
            
            return {"risk_output": risk_output}
            
        except Exception as e:
            self.logger.exception(f"Error in {self.name}: {e}")
            return {}


async def run_risk_agent(state: AIAgentState, ai_service, agent_id: str = "risk-agent") -> dict:
    """
    Convenience function to run the risk agent.
    
    Args:
        state: The current agent state.
        ai_service: The AI service instance.
        agent_id: Unique identifier for the agent instance.
        
    Returns:
        State updates from the agent.
    """
    risk_agent = RiskAIAgentProducer(channel=None)
    return await risk_agent.execute(state, ai_service)
