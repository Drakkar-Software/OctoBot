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
import typing

import octobot_commons.constants as common_constants

import octobot_agents as agent
from octobot_agents.constants import RESULT_KEY, AGENT_NAME_KEY

from .models import SummarizationOutput


class AgentResult(typing.TypedDict, total=False):
    """Type definition for agent evaluation results."""
    eval_note: float | str | None
    eval_note_description: str
    confidence: float
    error: str
    agent_name: str
    agent_id: str
    result: dict  # Nested result from team execution


# Input can be either a dict mapping agent names to results, or a list of results
AgentResultsDict = dict[str, AgentResult]
AgentResultsList = list[AgentResult]
AgentResultsInput = AgentResultsDict | AgentResultsList


class SummarizationAIAgentChannel(agent.AbstractAgentChannel):
    """Channel for SummarizationAIAgentProducer."""
    OUTPUT_SCHEMA = SummarizationOutput


class SummarizationAIAgentConsumer(agent.AbstractAIAgentChannelConsumer):
    """Consumer for SummarizationAIAgentProducer."""
    pass


class SummarizationAIAgentProducer(agent.AbstractAIAgentChannelProducer):
    """Producer specialized in combining multiple evaluations into a final recommendation."""
    
    AGENT_VERSION = "1.0.0"
    AGENT_CHANNEL = SummarizationAIAgentChannel
    AGENT_CONSUMER = SummarizationAIAgentConsumer
    ENABLE_MEMORY = True
    DEFAULT_CONFIDENCE = 50  # Default confidence value (0-100 scale)

    def __init__(self, channel, synthesis_method: str = "weighted", **kwargs):
        super().__init__(channel, **kwargs)
        self.synthesis_method = synthesis_method

    def _get_default_prompt(self) -> str:
        return (
            "You are a Market Analysis Synthesis AI expert. Your task is to combine multiple specialized AI agent evaluations "
            "into a single, coherent, and actionable trading recommendation.\n\n"
            "Follow these steps:\n"
            "1. Review all agent evaluations comprehensively: technical, sentiment, and real-time analysis\n"
            "2. Assess overall market direction: Determine if signals indicate strong bullish, bearish, neutral, or mixed conditions\n"
            "3. Consider different perspectives: Weight technical signals, social sentiment, and real-time momentum appropriately\n"
            "4. Evaluate signal convergence/divergence: Look for confirmation across agents vs. conflicting signals\n"
            "5. Calculate balanced final eval_note: Use the full range from -1 (strong sell) to 1 (strong buy), but most syntheses result in neutral to mildly bullish/bearish recommendations\n"
            "6. Consider confidence levels (0-1): Higher confidence for consistent signals; lower for conflicting or weak data\n"
            "7. Provide detailed reasoning in description: Explain key consensus points, overall outlook, recommendations, and identified risks\n\n"
            "Important: Markets are rarely extremely bullish or bearish. Use extreme values (-1/1) only for very strong, consistent signals across all agents.\n\n"
            "MANDATORY FIELDS:\n"
            "- eval_note: final score from -1 (strong sell) to 1 (strong buy)\n"
            "- confidence: confidence level (0-1)\n"
            "- description: comprehensive summary including key points, outlook (bullish/bearish/mixed), recommendations, and risks\n\n"
            "Output only valid JSON matching the SummarizationOutput schema with these three fields."
        )

    def _collect_failure_details(
        self,
        agent_results_dict: AgentResultsDict | None,
        agent_results_list: AgentResultsList,
    ) -> str:
        """Collect detailed information about why agent evaluations failed."""
        failure_reasons: list[str] = []
        
        # Use dict with agent names if available, otherwise use list
        if agent_results_dict is not None:
            for agent_name, result in agent_results_dict.items():
                reason = self._get_failure_reason(result, agent_name)
                if reason:
                    failure_reasons.append(reason)
        else:
            for i, result in enumerate(agent_results_list):
                agent_name = result.get("agent_name", f"Agent_{i}")
                reason = self._get_failure_reason(result, agent_name)
                if reason:
                    failure_reasons.append(reason)
        
        if not failure_reasons:
            return f"Received {len(agent_results_list)} result(s) but all had eval_note=None"
        
        return "Failures: " + "; ".join(failure_reasons)

    def _get_failure_reason(self, result: AgentResult, agent_name: str) -> str:
        """Extract the failure reason from a single agent result."""
        # Check for explicit error field
        if error := result.get("error"):
            return f"{agent_name}: {error}"
        
        # Check for error in description
        if result.get("eval_note") is None:
            if desc := result.get("eval_note_description"):
                # Truncate long descriptions
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                return f"{agent_name}: {desc}"
            
            # Try to find any useful info in the result
            available_keys = [k for k in result.keys() if result[k] is not None]
            if available_keys:
                return f"{agent_name}: eval_note=None (available: {', '.join(available_keys)})"
            return f"{agent_name}: eval_note=None (empty result)"
        
        return ""

    def _unwrap_agent_result(self, result: AgentResult) -> AgentResult:
        """
        Unwrap nested result from team execution.
        
        Team passes results as: {"agent_name": ..., "agent_id": ..., "result": {...}}
        We need to extract the inner result dict which contains eval_note, etc.
        """
        result_key = RESULT_KEY
        agent_name_key = AGENT_NAME_KEY
        
        try:
            inner_result = result[result_key]
            if isinstance(inner_result, dict):
                # Preserve agent_name if available
                if agent_name_key not in inner_result and agent_name_key in result:
                    inner_result[agent_name_key] = result[agent_name_key]
                return typing.cast(AgentResult, inner_result)
        except (KeyError, TypeError):
            pass
        return result

    async def execute(
        self,
        input_data: AgentResultsInput,
        ai_service,
        context_info: dict | None = None,
    ) -> tuple[float | str, str]:
        """Combine multiple agent results into final evaluation."""
        if not input_data:
            return common_constants.START_PENDING_EVAL_NOTE, "No agent results available"

        # Convert input to list, preserving dict for failure details if needed
        agent_results_dict: AgentResultsDict | None = None
        agent_results_list: AgentResultsList
        try:
            # Try dict access
            agent_results_dict = typing.cast(AgentResultsDict, input_data)
            agent_results_list = list(agent_results_dict.values())
        except (TypeError, AttributeError):
            # List input
            agent_results_list = typing.cast(AgentResultsList, input_data)

        # Unwrap nested results from team execution
        agent_results_list = [self._unwrap_agent_result(r) for r in agent_results_list]

        # Filter out empty/error results
        valid_results = [r for r in agent_results_list if r.get("eval_note") is not None]

        if not valid_results:
            # Collect failure details for better debugging
            failure_details = self._collect_failure_details(agent_results_dict, agent_results_list)
            return common_constants.START_PENDING_EVAL_NOTE, f"All agent evaluations failed. {failure_details}"

        # If only one result, use it directly
        if len(valid_results) == 1:
            result = valid_results[0]
            # eval_note is guaranteed non-None due to valid_results filter
            eval_note = result.get("eval_note") or common_constants.INIT_EVAL_NOTE
            return float(eval_note), result.get("eval_note_description", "")

        # Prepare summarization data
        summary_data = {}
        for i, result in enumerate(valid_results):
            summary_data[f"agent_{i}"] = {
                "eval_note": result.get("eval_note", common_constants.INIT_EVAL_NOTE),
                "description": result.get("eval_note_description", ""),
                "confidence": result.get("confidence", self.DEFAULT_CONFIDENCE),
            }

        # Add context about data completeness
        context_str = ""
        if context_info:
            missing = context_info.get("missing_data_types", [])
            available = context_info.get("available_data_types", [])
            total = context_info.get("total_expected_types", [])
            if missing:
                context_str = f"\n\nNote: Analysis is based on incomplete data. Missing evaluator types: {missing}. Available: {available}. Expected total: {total}."

        messages = [
            ai_service.create_message("system", self.prompt),
            ai_service.create_message(
                "user",
                f"Agent evaluations to synthesize:\n{json.dumps(summary_data, indent=2)}{context_str}\n\n"
                "Provide final evaluation as JSON matching the SummarizationOutput schema with three fields: eval_note, confidence, and description.",
            ),
        ]

        try:
            # Uses SummarizationAIAgentChannel.OUTPUT_SCHEMA by default
            parsed = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
            )
            final_eval_note = float(parsed.get("eval_note", common_constants.INIT_EVAL_NOTE))
            final_eval_note_description = parsed.get("description", "AI synthesis")
            confidence = float(parsed.get("confidence", self.DEFAULT_CONFIDENCE))

            # Clamp eval_note
            final_eval_note = max(-1, min(1, final_eval_note))
            
            # Include confidence in description
            final_eval_note_description = f"{final_eval_note_description} (Confidence: {confidence:.1%})"

            return final_eval_note, final_eval_note_description
        except Exception as e:
            self.logger.error(f"Error in summarization: {e}")
            # Fallback: weighted average of agent results
            total_weight = 0.0
            weighted_sum = 0.0
            descriptions: list[str] = []

            for result in valid_results:
                confidence = float(result.get("confidence", self.DEFAULT_CONFIDENCE)) / 100.0  # Normalize to 0-1
                eval_note = float(result.get("eval_note") or common_constants.INIT_EVAL_NOTE)
                weighted_sum += eval_note * confidence
                total_weight += confidence
                descriptions.append(result.get("eval_note_description", ""))

            if total_weight > 0:
                final_eval_note = weighted_sum / total_weight
            else:
                final_eval_note = sum(
                    float(r.get("eval_note") or common_constants.INIT_EVAL_NOTE) for r in valid_results
                ) / len(valid_results)

            final_eval_note_description = (
                " | ".join(descriptions) if descriptions else "Fallback synthesis"
            )

            return max(-1, min(1, final_eval_note)), final_eval_note_description
