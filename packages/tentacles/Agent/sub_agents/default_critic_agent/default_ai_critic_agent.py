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
import typing
from typing import List

from pydantic import Field

import octobot_agents.team.critic as critic
from .default_critic_agent import DefaultCriticAgentProducer
import octobot_agents.models as agent_models


class QualityEvaluationOutput(agent_models.AgentBaseModel):
    """
    Output schema for LLM-based quality evaluation.
    
    This model is intentionally focused on behavioral and strategic quality only.
    Schema/field/type validation is handled separately by Pydantic and runtime
    checks, not by the critic.
    """
    __strict_json_schema__ = True
    
    quality_ok: bool = Field(description="Whether the output quality is acceptable.")
    # Behavior/strategy/risk/logic issues suitable for learning and memory.
    issues: List[str] = Field(
        default_factory=list,
        description="List of behavioral/strategic quality issues (empty if quality_ok is true).",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the behavioral quality assessment."
    )


class DefaultAICriticAgentChannel(critic.AICriticAgentChannel):
    pass


class DefaultAICriticAgentConsumer(critic.AICriticAgentConsumer):
    pass


class DefaultAICriticAgentProducer(critic.AICriticAgentProducer):
    """
    Default AI critic agent - hybrid rule-based + LLM analysis.
    
    Combines basic quality heuristics from DefaultCriticAgentProducer with
    LLM-based evaluation for comprehensive result quality assessment.
    Designed as the default critic for AI teams.
    
    Features:
    - Basic quality checks (empty results, schema validation, placeholder detection)
    - LLM-based quality evaluation (correctness, relevance, completeness, expectations)
    - Context-aware analysis (compares results against execution plan)
    - Enhanced improvement suggestions
    """
    
    AGENT_CHANNEL: typing.Type[critic.AICriticAgentChannel] = DefaultAICriticAgentChannel
    AGENT_CONSUMER: typing.Type[critic.AICriticAgentConsumer] = DefaultAICriticAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[DefaultAICriticAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            self_improving=self_improving,
            **kwargs,
        )
        # Create instance of DefaultCriticAgentProducer to reuse its quality evaluation
        self._basic_critic = DefaultCriticAgentProducer(channel=None)
    
    def _get_default_prompt(self) -> str:
        """
        Return the default prompt for the AI critic agent.
        
        Returns:
            The default system prompt string.
        """
        return """You are an AI critic agent for an AI agent team.
Your role is to analyze team execution and evaluate the *behavioral and strategic quality*
of each agent's output, not to restate low-level schema or type constraints.

Focus on:
1. Result & Behavior Quality:
   - Correctness: Are the decisions and outputs logically and financially sound?
   - Relevance: Do they address the intended trading or evaluation objective?
   - Completeness: Are the key behavioral steps and justifications present (not just fields)?
   - Expectations: Do they match the intent of the execution plan and agent role?

2. Issues and Problems:
   - Identify logical errors, poor risk management, or inconsistent reasoning.
   - Detect off-topic, misleading, or unsupported conclusions.
   - Highlight missing analysis or skipped safety checks that should have been performed.

3. Agent Improvements:
   - Only include agents in agent_improvements if they have memory enabled.
   - Provide specific, actionable improvements to behavior, strategy, or coordination.
   - Explain why each agent needs improvement in terms of its decisions and patterns,
     not just missing keys or fields.
   - For strong results, suggest what should be captured as reusable best practices.

4. Context Awareness:
   - Compare outputs against the execution plan (goals, constraints, and roles).
   - Check consistency between related agent outputs (e.g., no conflicting signals).
   - Consider recent history and regime (if provided) when judging severity of issues.

For each agent with memory enabled:
- If the result is high quality: include a positive learning entry that describes the
  pattern to reuse (what worked and why).
- If the result has quality issues: include specific, behavior-level issues and
  improvements (what to change in logic/decision-making).
- If the result is off-topic or shallow: explain why, and propose how to better
  align with the task and other agents."""
    
    def _evaluate_result_quality_basic(
        self, 
        output: typing.Any, 
        agent: typing.Optional[typing.Any]
    ) -> typing.Tuple[bool, typing.List[str]]:
        """
        Evaluate result quality using basic heuristics (from DefaultCriticAgentProducer).
        
        Args:
            output: The agent output to evaluate
            agent: The agent instance (optional, for schema access)
            
        Returns:
            Tuple of (is_quality_ok, list_of_issues)
        """
        # Reuse the basic quality evaluation from DefaultCriticAgentProducer
        return self._basic_critic._evaluate_result_quality(output, agent)
    
    async def _evaluate_result_quality_with_llm(
        self,
        output: typing.Any,
        agent: typing.Optional[typing.Any],
        agent_name: str,
        execution_plan: typing.Optional[typing.Any],
        other_outputs: typing.Dict[str, typing.Any],
        ai_service: typing.Any,
    ) -> typing.Tuple[bool, typing.List[str], typing.Optional[str]]:
        """
        Evaluate result quality using LLM for deeper assessment.
        
        Args:
            output: The agent output to evaluate
            agent: The agent instance (optional, for schema access)
            agent_name: Name of the agent
            execution_plan: The execution plan (for context)
            other_outputs: Other agent outputs (for consistency checking)
            ai_service: The AI service instance
            
        Returns:
            Tuple of (is_quality_ok, list_of_issues, llm_reasoning)
        """
        issues = []
        reasoning = None
        
        # Build context for LLM evaluation
        agent_context = {
            "agent_name": agent_name,
            "output": output,
        }
        
        # Add schema info if available (team agents are producers with AGENT_CHANNEL)
        if agent is not None:
            try:
                schema = agent.AGENT_CHANNEL.get_output_schema()
                if schema:
                    agent_context["expected_schema"] = schema.__name__
            except (AttributeError, TypeError):
                pass
        
        # Build evaluation prompt
        evaluation_prompt = f"""Evaluate the behavioral and strategic quality of this agent's output:

Agent: {agent_name}
Output: {self.format_data(output)}

Context:
- Execution Plan: {self.format_data(execution_plan.to_dict() if execution_plan else {})}
- Other Agent Outputs: {self.format_data({k: v for k, v in other_outputs.items() if k != agent_name})}

Your task:
1. Completely ignore low-level schema/field/type/format problems. Assume that
   any output you see has already passed structural validation.
2. Evaluate only behavioral and strategic quality:
   - Correctness: Are the decisions and conclusions logically and financially sound?
   - Relevance: Do they address the intended trading or evaluation objective?
   - Completeness: Are key behavioral steps, checks, and justifications present?
   - Expectations: Do they match the intent of the execution plan and agent role?
   - Consistency: Are they coherent with other agent outputs?

Respond with structured JSON fields:
- quality_ok: true/false
- issues: list of BEHAVIORAL issues only (short text, empty if quality_ok is true)
- reasoning: brief explanation of the behavioral assessment

If quality_ok is false, issues should clearly explain what to change in the
agent's decisions, strategies, or risk management, not its output schema."""
        
        try:
            messages = [
                {"role": "system", "content": "You are a quality evaluation expert. Analyze agent outputs for correctness, relevance, completeness, and whether they meet expectations."},
                {"role": "user", "content": evaluation_prompt},
            ]
            
            # Call LLM for quality evaluation with structured output schema
            response = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
                response_schema=QualityEvaluationOutput,
            )
            
            # Parse response using Pydantic model
            quality_eval = QualityEvaluationOutput.model_validate(response)
            quality_ok = quality_eval.quality_ok
            issues.extend(quality_eval.issues)
            reasoning = quality_eval.reasoning
            
            # Return issues directly; they all describe behavioral problems.
            return quality_ok, issues, reasoning
            
        except Exception as e:
            # If LLM evaluation fails, log and fall back to basic evaluation
            self.logger.warning(f"LLM quality evaluation failed for {agent_name}: {e}. Falling back to basic evaluation.")
            return True, [], None
    
    async def execute(
        self,
        input_data: typing.Union[agent_models.CriticInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any
    ) -> agent_models.CriticAnalysis:
        """
        Execute critic analysis using hybrid rule-based + LLM evaluation.
        
        Combines basic heuristics with LLM-based quality assessment for comprehensive
        result quality evaluation.
        
        Args:
            input_data: Contains {"team_producer": team_producer, "execution_plan": ExecutionPlan, "execution_results": Dict, "agent_outputs": Dict, "execution_metadata": dict}
            ai_service: The AI service instance for LLM calls
            
        Returns:
            CriticAnalysis with comprehensive findings
        """
        execution_results = input_data.get("execution_results", {})
        agent_outputs = input_data.get("agent_outputs", {})
        execution_metadata = input_data.get("execution_metadata", {})
        execution_plan = input_data.get("execution_plan")
        team_producer = input_data.get("team_producer")
        
        if team_producer is None:
            raise ValueError("team_producer is required in input_data")
        
        issues = []
        errors = []
        inconsistencies = []
        optimizations = []
        agent_improvements = {}
        
        # Check for general errors
        if execution_metadata.get("errors"):
            errors.extend(execution_metadata["errors"])
        
        # Process each agent with hybrid quality evaluation
        for agent_name, output in agent_outputs.items():
            # Skip agents that failed (no result available)
            if output is None:
                continue
            
            # Check for errors in execution results
            if agent_name in execution_results:
                result = execution_results[agent_name]
                if isinstance(result, dict) and result.get("error"):
                    continue
            
            # Get agent instance for quality evaluation and memory check
            agent = None
            has_memory_enabled = False
            if team_producer:
                try:
                    agent = team_producer.get_agent_by_name(agent_name)
                    if agent is None:
                        manager = team_producer.get_manager()
                        if manager and manager.name == agent_name:
                            agent = manager
                    
                    if agent:
                        try:
                            has_memory_enabled = agent.has_memory_enabled()
                        except AttributeError:
                            has_memory_enabled = getattr(agent, 'ENABLE_MEMORY', False)
                except (AttributeError, KeyError):
                    has_memory_enabled = False
            
            # Skip agents without memory enabled
            if not has_memory_enabled:
                continue
            
            # Step 1: Run basic quality checks
            basic_ok, basic_issues = self._evaluate_result_quality_basic(output, agent)
            
            # Step 2: Run LLM-based quality evaluation
            # NOTE: llm_issues here are already behavior-focused, schema-only
            # issues are kept inside the QualityEvaluationOutput.issues field
            # and added above via the issues list.
            llm_ok, llm_behavior_issues, llm_reasoning = await self._evaluate_result_quality_with_llm(
                output=output,
                agent=agent,
                agent_name=agent_name,
                execution_plan=execution_plan,
                other_outputs=agent_outputs,
                ai_service=ai_service,
            )
            
            # Step 3: Combine assessments
            # basic_issues may contain schema-like problems; llm_behavior_issues
            # are explicitly behavior/strategy/risk oriented.
            all_behavior_issues = basic_issues + llm_behavior_issues
            is_quality_ok = basic_ok and llm_ok
            
            # Build reasoning
            if is_quality_ok:
                reasoning = f"Agent {agent_name} produced quality result"
                if llm_reasoning:
                    reasoning += f": {llm_reasoning}"
                reasoning += " - capturing learnings"
                
                # For successful results, capture positive behavioral pattern
                agent_improvements[agent_name] = agent_models.AgentImprovement(
                    agent_name=agent_name,
                    improvements=["Capture successful execution patterns"],
                    issues=[],
                    errors=[],
                    reasoning=reasoning,
                )
            else:
                # Combine basic and LLM behavior issues for reasoning, while schema-only
                # issues remain available in the global issues list.
                combined_reasoning = f"Agent {agent_name} produced result with quality issues"
                if basic_issues:
                    combined_reasoning += f". Basic checks: {', '.join(basic_issues)}"
                if llm_behavior_issues:
                    combined_reasoning += f". LLM behavior evaluation: {', '.join(llm_behavior_issues)}"
                if llm_reasoning:
                    combined_reasoning += f". Analysis: {llm_reasoning}"
                
                agent_improvements[agent_name] = agent_models.AgentImprovement(
                    agent_name=agent_name,
                    # Focus memory on behavioral improvements, not schema fixes.
                    improvements=["Improve result quality, correctness, and completeness"],
                    issues=all_behavior_issues,
                    errors=[],
                    reasoning=combined_reasoning,
                )
        
        # Count quality vs non-quality results
        quality_count = sum(
            1 for imp in agent_improvements.values() 
            if not imp.issues and not imp.errors
        )
        quality_issue_count = len(agent_improvements) - quality_count
        
        summary = (
            f"Found {len(errors)} errors, {len(issues)} issues. "
            f"{quality_count} agents with quality results processed for memory updates. "
            f"{quality_issue_count} agents with quality issues identified (hybrid evaluation)."
        )
        
        return agent_models.CriticAnalysis(
            issues=issues,
            errors=errors,
            inconsistencies=inconsistencies,
            optimizations=optimizations,
            summary=summary,
            agent_improvements=agent_improvements,
        )
