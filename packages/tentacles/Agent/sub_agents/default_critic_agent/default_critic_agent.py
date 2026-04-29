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

import octobot_agents.team.critic as critic
import octobot_agents.models as agent_models


class DefaultCriticAgentChannel(critic.CriticAgentChannel):
    pass


class DefaultCriticAgentConsumer(critic.CriticAgentConsumer):
    pass


class DefaultCriticAgentProducer(critic.CriticAgentProducer):
    """
    Default critic agent - simple rule-based analysis.
    
    Inherits from CriticAgentProducer. Uses simple heuristics instead of LLM.
    
    Note: This is a basic rule-based critic with limited quality evaluation capabilities.
    For proper quality evaluation (checking correctness, relevance, completeness, etc.),
    use AICriticAgentProducer which uses LLM-based analysis.
    """
    
    AGENT_CHANNEL: typing.Type[critic.CriticAgentChannel] = DefaultCriticAgentChannel
    AGENT_CONSUMER: typing.Type[critic.CriticAgentConsumer] = DefaultCriticAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[DefaultCriticAgentChannel] = None,
        self_improving: bool = True,
    ):
        super().__init__(channel=channel, self_improving=self_improving)
    
    def _evaluate_result_quality(
        self, 
        output: typing.Any, 
        agent: typing.Optional[typing.Any]
    ) -> typing.Tuple[bool, typing.List[str]]:
        """
        Evaluate result quality using basic heuristics.
        
        Checks for:
        - Empty dict results
        - Schema validation failures (if OUTPUT_SCHEMA available)
        - All empty/None values
        - Placeholder or incomplete data
        
        Args:
            output: The agent output to evaluate
            agent: The agent instance (optional, for schema access)
            
        Returns:
            Tuple of (is_quality_ok, list_of_issues)
        """
        issues = []
        
        # Check for empty dict
        if isinstance(output, dict) and len(output) == 0:
            return False, ["Result is empty dict"]
        
        # Try schema validation if available (team agents are producers with AGENT_CHANNEL)
        if agent is not None:
            try:
                schema = agent.AGENT_CHANNEL.get_output_schema()
                if schema:
                    try:
                        schema.model_validate(output)
                    except Exception as e:
                        issues.append(f"Schema validation failed: {str(e)}")
            except (AttributeError, TypeError):
                # Schema not available or not callable, skip validation
                pass
        
        # Check for all None/empty values in dict
        if isinstance(output, dict):
            all_empty = all(
                v is None or v == "" or (isinstance(v, dict) and len(v) == 0) or (isinstance(v, list) and len(v) == 0)
                for v in output.values()
            )
            if all_empty:
                issues.append("All result fields are empty, None, or empty collections")
        
        # Check for placeholder-like values (very basic check)
        if isinstance(output, dict):
            placeholder_indicators = ["n/a", "none", "null", "placeholder", "todo", "tbd"]
            for key, value in output.items():
                if isinstance(value, str) and value.lower() in placeholder_indicators:
                    issues.append(f"Field '{key}' contains placeholder value: {value}")
                    break
        
        return len(issues) == 0, issues
    
    async def execute(
        self,
        input_data: typing.Union[agent_models.CriticInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any  # AbstractAIService - type not available at runtime
    ) -> agent_models.CriticAnalysis:
        """
        Execute critic analysis using simple heuristics.
        
        Evaluates agent results using basic quality checks:
        - Empty result detection
        - Schema validation (if OUTPUT_SCHEMA available)
        - Completeness checks (empty fields, placeholder values)
        
        Note: This is a basic rule-based approach with limited evaluation capabilities.
        It cannot assess correctness, relevance, or whether results meet expectations.
        For comprehensive quality evaluation, use CriticAgentProducer (LLM-based).
        
        Args:
            input_data: Contains {"team_producer": team_producer, "execution_plan": ExecutionPlan, "execution_results": Dict, "agent_outputs": Dict, "execution_metadata": dict}
            ai_service: Not used by default critic agent
            
        Returns:
            CriticAnalysis with basic findings
        """
        execution_results = input_data.get("execution_results", {})
        agent_outputs = input_data.get("agent_outputs", {})
        execution_metadata = input_data.get("execution_metadata", {})
        
        issues = []
        errors = []
        inconsistencies = []
        optimizations = []
        agent_improvements = {}
        
        # Check for general errors
        if execution_metadata.get("errors"):
            errors.extend(execution_metadata["errors"])
        
        # Get team producer to check agent memory status
        team_producer = input_data.get("team_producer")
        
        # Check each agent - only process agents with valid results
        for agent_name, output in agent_outputs.items():
            # Skip agents that failed (no result available)
            if output is None:
                # Agent failed - skip it, don't include in improvements
                continue
            
            # Check for errors in execution results
            if agent_name in execution_results:
                result = execution_results[agent_name]
                if isinstance(result, dict) and result.get("error"):
                    # Agent failed with error - skip it, don't include in improvements
                    continue
            
            # Get agent instance for quality evaluation and memory check
            agent = None
            has_memory_enabled = False
            if team_producer:
                try:
                    # Try to get agent instance from team
                    agent = team_producer.get_agent_by_name(agent_name)
                    if agent is None:
                        # Check if it's the manager
                        manager = team_producer.get_manager()
                        if manager and manager.name == agent_name:
                            agent = manager
                    
                    if agent:
                        # Check if agent has memory enabled
                        try:
                            has_memory_enabled = agent.has_memory_enabled()
                        except AttributeError:
                            # Check ENABLE_MEMORY class variable as fallback
                            has_memory_enabled = getattr(agent, 'ENABLE_MEMORY', False)
                except (AttributeError, KeyError):
                    # If we can't check, assume no memory
                    has_memory_enabled = False
            
            # Evaluate result quality
            is_quality_ok, quality_issues = self._evaluate_result_quality(output, agent)
            
            # Only include agents with quality results and memory enabled
            if has_memory_enabled:
                if is_quality_ok:
                    # Agent has quality result and memory enabled - capture learnings
                    agent_improvements[agent_name] = agent_models.AgentImprovement(
                        agent_name=agent_name,
                        improvements=["Capture successful execution patterns"],
                        issues=[],
                        errors=[],
                        reasoning=f"Agent {agent_name} produced quality result with memory enabled - capturing learnings",
                    )
                else:
                    # Agent has result but quality issues - include with issues for improvement
                    agent_improvements[agent_name] = agent_models.AgentImprovement(
                        agent_name=agent_name,
                        improvements=["Improve result quality and completeness"],
                        issues=quality_issues,
                        errors=[],
                        reasoning=f"Agent {agent_name} produced result but quality checks failed: {', '.join(quality_issues)}",
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
            f"{quality_issue_count} agents with quality issues identified."
        )
        
        return agent_models.CriticAnalysis(
            issues=issues,
            errors=errors,
            inconsistencies=inconsistencies,
            optimizations=optimizations,
            summary=summary,
            agent_improvements=agent_improvements,
        )
