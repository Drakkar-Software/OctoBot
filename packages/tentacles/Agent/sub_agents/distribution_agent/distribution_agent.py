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
Distribution Agent.
Makes final portfolio distribution decisions based on synthesized signals and risk assessment.
Uses ai_index_distribution functions to apply changes.
"""
import json
import typing

import octobot_agents as agent
from octobot_agents.constants import RESULT_KEY
from octobot_services.enums import AIModelPolicy

from tentacles.Agent.sub_agents.signal_agent.state import AIAgentState
from .models import DistributionOutput


class DistributionAIAgentChannel(agent.AbstractAgentChannel):
    """Channel for DistributionAIAgentProducer."""
    OUTPUT_SCHEMA = DistributionOutput


class DistributionAIAgentConsumer(agent.AbstractAIAgentChannelConsumer):
    """Consumer for DistributionAIAgentProducer."""
    pass


class DistributionAIAgentProducer(agent.AbstractAIAgentChannelProducer):
    """
    Distribution agent producer that makes final portfolio allocation decisions.
    Combines signal synthesis and risk assessment to determine target distribution.
    """
    MODEL_POLICY = AIModelPolicy.REASONING
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = DistributionAIAgentChannel
    AGENT_CONSUMER = DistributionAIAgentConsumer
    ENABLE_MEMORY = True
    
    def __init__(self, channel, model=None, max_tokens=None, temperature=None, **kwargs):
        """
        Initialize the distribution agent producer.
        
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
You are a Portfolio Distribution Agent for cryptocurrency trading.
Your task is to make FINAL portfolio allocation decisions based on synthesized signals and risk assessment.

## Your Role
- Determine target percentage allocation for each asset.
- Balance signal-driven opportunities with risk constraints.
- Decide on rebalancing urgency.

## Important Constraints
- Total allocation MUST sum to exactly 100%.
- Respect maximum allocation limits from risk assessment.
- Maintain minimum cash reserve as recommended by risk agent.
- Consider current distribution to minimize unnecessary trades.

## Allocation Actions
- "increase": Increase allocation from current level
- "decrease": Decrease allocation from current level
- "maintain": Keep current allocation
- "add": Add new asset to portfolio
- "remove": Remove asset from portfolio entirely

## Rebalancing Urgency
- "immediate": Critical signals or risk levels require immediate action
- "soon": Moderate signals suggest rebalancing within the trading session
- "low": Minor adjustments that can wait
- "none": Current distribution is acceptable

## Decision Framework
1. Start with current distribution as baseline
2. Apply signal synthesis recommendations (increase/decrease based on direction and strength)
3. Apply risk constraints (max allocation limits, min cash reserve)
4. Ensure total sums to 100%
5. Determine urgency based on signal strength and risk level

## REQUIRED OUTPUT FORMAT - STRICT SCHEMA

Output a JSON object with:
- "distributions" (or "allocations"): Array of objects, each with ALL of these REQUIRED fields:
  * "asset" (string): Asset symbol like "BTC", "ETH", "USD" - REQUIRED
  * "percentage" (number): Float between 0.0 and 100.0 - REQUIRED (can also be named "target_percentage", "target_allocation", "allocation", "weight", or "ratio")
  * "action" (string): EXACTLY one of "increase", "decrease", "maintain", "add", "remove" - REQUIRED
  * "explanation" (string): Clear explanation text for this allocation - REQUIRED
- "rebalance_urgency" (string): EXACTLY one of "immediate", "soon", "low", "none" - REQUIRED
- "reasoning" (string): Summary explanation - REQUIRED

CRITICAL: Every field above is REQUIRED. Do NOT omit any field, especially "explanation" in each distribution object.
"""
    
    def _build_user_prompt(self, state: AIAgentState) -> str:
        """Build the user prompt with all decision inputs."""
        signal_synthesis = state.get("signal_synthesis")
        risk_output = state.get("risk_output")
        current_distribution = state.get("current_distribution", {})
        cryptocurrencies = state.get("cryptocurrencies", [])
        reference_market = state.get("reference_market", "USD")
        
        # Format signal synthesis
        synthesis_data = {}
        if signal_synthesis:
            try:
                # Try Pydantic model access
                synthesis_data = {
                    "market_outlook": signal_synthesis.market_outlook,
                    "summary": signal_synthesis.summary,
                    "signals": [
                        {
                            "asset": s.asset,
                            "direction": s.direction,
                            "strength": s.strength,
                            "consensus_level": s.consensus_level,
                            "trading_instruction": s.trading_instruction
                        }
                        for s in signal_synthesis.synthesized_signals
                    ]
                }
            except AttributeError:
                # It's a dict
                synthesis_data = signal_synthesis
        
        # Format risk output
        risk_data = {}
        if risk_output:
            try:
                # Try Pydantic model access
                risk_data = {
                    "overall_risk_level": risk_output.metrics.overall_risk_level,
                    "concentration_risk": risk_output.metrics.concentration_risk,
                    "volatility_exposure": risk_output.metrics.volatility_exposure,
                    "liquidity_risk": risk_output.metrics.liquidity_risk,
                    "max_allocations": risk_output.max_allocation_per_asset,
                    "min_cash_reserve": risk_output.min_cash_reserve,
                    "recommendations": risk_output.recommendations,
                    "reasoning": risk_output.reasoning
                }
            except AttributeError:
                # It's a dict
                risk_data = risk_output
        
        allowed_assets = cryptocurrencies + [reference_market]
        
        return f"""
# Determine Portfolio Distribution

## Allowed Assets
{json.dumps(allowed_assets, indent=2)}

## Current Distribution (percentages)
{json.dumps(current_distribution, indent=2)}

## Signal Synthesis (from Signal Agent)
{json.dumps(synthesis_data, indent=2, default=str)}

## Risk Assessment (from Risk Agent)
{json.dumps(risk_data, indent=2, default=str)}

## Reference Market (Stablecoin/Cash)
{reference_market}

## Task
Based on the synthesized signals and risk assessment:
1. Determine target allocation percentage for each asset
2. Specify the action (increase/decrease/maintain/add/remove)
3. Ensure total allocations sum to exactly 100%
4. Respect risk constraints (max allocations, min cash reserve)
5. Set rebalancing urgency
6. Provide reasoning for decisions

## REQUIRED OUTPUT FORMAT - STRICT SCHEMA

You MUST return a JSON object with:
- "distributions" (or "allocations"): Array where each object has ALL of these REQUIRED fields:
  * "asset" (string): REQUIRED - Asset symbol
  * "percentage" (number): REQUIRED - Float 0.0-100.0 (can also be named "target_percentage", "target_allocation", "allocation", "weight", or "ratio")
  * "action" (string): REQUIRED - One of "increase", "decrease", "maintain", "add", "remove"
  * "explanation" (string): REQUIRED - Clear explanation for this allocation decision
- "rebalance_urgency" (string): REQUIRED - One of "immediate", "soon", "low", "none"
- "reasoning" (string): REQUIRED - Overall reasoning

CRITICAL: Every field is REQUIRED. Do NOT omit "explanation" in any distribution object.

Remember: 
- Percentages must sum to 100%
- Only use allowed assets
- Balance opportunity with risk
"""
    
    def _merge_predecessor_outputs(self, input_data: typing.Any) -> dict:
        """
        Merge predecessor agent outputs into state.
        
        When the distribution agent has multiple predecessors (Signal and Risk),
        the team system passes them as a dict with agent names as keys.
        This method extracts and merges their outputs into the state.
        
        Args:
            input_data: Either a state dict (for entry agents) or a dict with 
                       predecessor outputs keyed by agent name.
                       
        Returns:
            Merged state dict with signal_synthesis and risk_output at top level.
        """
        
        # Extract initial state if available (stored in _initial_state by team system)
        initial_state = {}
        if isinstance(input_data, dict) and "_initial_state" in input_data:
            initial_state = input_data["_initial_state"]
            # Create a copy of input_data without _initial_state for processing
            input_data = {k: v for k, v in input_data.items() if k != "_initial_state"}
        
        # If input_data is already a state dict (has expected keys), use it directly
        if isinstance(input_data, dict):
            # Check if it's a state dict (has state keys) or predecessor outputs (has agent names)
            state_keys = {"cryptocurrencies", "reference_market", "portfolio", "current_distribution"}
            if state_keys.intersection(input_data.keys()):
                # It's already a state dict
                state = input_data.copy()
                # Remove predecessor agent keys from state copy to avoid conflicts
                # We'll merge their outputs properly below
                agent_names = ["SignalAIAgentProducer", "RiskAIAgentProducer"]
                for agent_name in agent_names:
                    state.pop(agent_name, None)
            elif initial_state:
                # Use initial_state as base if available
                state = initial_state.copy()
            else:
                # Fallback: It's only predecessor outputs
                state = {}
        
        # Extract outputs from predecessor agents
        # Signal agent output structure: {"signal_outputs": {...}, "signal_synthesis": {...}}
        # Risk agent output structure: {"risk_output": {...}}
        
        # Check for Signal agent output
        signal_agent_name = "SignalAIAgentProducer"
        if signal_agent_name in input_data:
            signal_result = input_data[signal_agent_name]
            if isinstance(signal_result, dict):
                # Extract RESULT_KEY if present (team system wraps results)
                signal_output = signal_result.get(RESULT_KEY, signal_result)
                if isinstance(signal_output, dict):
                    # Merge signal outputs into state
                    if "signal_outputs" in signal_output:
                        state["signal_outputs"] = signal_output["signal_outputs"]
                    if "signal_synthesis" in signal_output:
                        state["signal_synthesis"] = signal_output["signal_synthesis"]
        
        # Check for Risk agent output
        risk_agent_name = "RiskAIAgentProducer"
        if risk_agent_name in input_data:
            risk_result = input_data[risk_agent_name]
            if isinstance(risk_result, dict):
                # Extract RESULT_KEY if present
                risk_output = risk_result.get(RESULT_KEY, risk_result)
                if isinstance(risk_output, dict) and "risk_output" in risk_output:
                    state["risk_output"] = risk_output["risk_output"]
        
        # If state is still empty, try to use input_data as state (fallback)
        if not state and isinstance(input_data, dict):
            state = input_data
        
        return state
    
    async def execute(self, input_data: typing.Any, ai_service) -> typing.Any:
        # Merge predecessor outputs into state
        state = self._merge_predecessor_outputs(input_data)
        self.logger.debug(f"Starting {self.name}...")
        
        try:
            messages = [
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": self._build_user_prompt(state)},
            ]
            
            response_data = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            distribution_output = DistributionOutput(**response_data)
            
            self.logger.debug(f"{self.name} completed successfully.")
            
            return {"distribution_output": distribution_output}
            
        except Exception as e:
            self.logger.exception(f"Error in {self.name}: {e}")
            return {}


async def run_distribution_agent(state: AIAgentState, ai_service, agent_id: str = "distribution-agent") -> dict:
    """
    Convenience function to run the distribution agent.
    
    Args:
        state: The current agent state.
        ai_service: The AI service instance.
        agent_id: Unique identifier for the agent instance.
        
    Returns:
        State updates from the agent.
    """
    distribution_agent = DistributionAIAgentProducer(channel=None)
    return await distribution_agent.execute(state, ai_service)
