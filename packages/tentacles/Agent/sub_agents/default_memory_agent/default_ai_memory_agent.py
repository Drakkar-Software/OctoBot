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

import octobot_agents.agent.memory as memory
import octobot_agents.models as agent_models
from octobot_services.enums import AIModelPolicy

MEMORY_TITLE_MAX_LENGTH = 100
MEMORY_CONTEXT_MAX_LENGTH = 300
MEMORY_CONTENT_MAX_LENGTH = 1000


class DefaultAIMemoryAgentChannel(memory.AIMemoryAgentChannel):
    pass


class DefaultAIMemoryAgentConsumer(memory.AIMemoryAgentConsumer):
    pass


class DefaultAIMemoryAgentProducer(memory.AIMemoryAgentProducer):
    """
    AI-powered memory agent that transforms critic feedback into structured memory instructions.
    
    Uses LLM to analyze critic analysis and generate behavioral, strategic, risk management,
    and coordination improvement instructions for agents.
    
    Inherits from AIMemoryAgentProducer. Uses LLM to transform critic feedback
    into structured memory instructions.
    
    Design influenced by multi-layer and agent memory works including:
    Mem-Agent, Moom, LightMem, Nemori, O-Mem (Omni Memory), SEDM, MemoRAG,
    EM-LLM, COMEDY, Agent Workflow Memory (AWM), temporal/meta-data-aware RAG,
    Memory Decoder (MemDec), Explicit Working Memory (Ewe),
    Memento 2 (Stateful Reflective Memory), Agentic Memory (AgeMem),
    Agentic Context Engineering (ACE), and practical agent memory systems
    such as MemoryBank, LONGMEM, Reflexion and Generative Agents.
    """
    
    AGENT_CHANNEL: typing.Type[memory.AIMemoryAgentChannel] = DefaultAIMemoryAgentChannel
    AGENT_CONSUMER: typing.Type[memory.AIMemoryAgentConsumer] = DefaultAIMemoryAgentConsumer
    MODEL_POLICY = AIModelPolicy.REASONING
    
    def __init__(
        self,
        channel: typing.Optional[DefaultAIMemoryAgentChannel] = None,
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
    
    def _get_default_prompt(self) -> str:
        """
        Return the default prompt for the AI-powered memory agent.
        
        Returns:
            The default system prompt string.
        """
        return f"""You are a memory management agent for an AI agent team.
Your role is to analyze critic feedback and transform it into short, simple, precise, command-like
instructions that help agents improve their behavior, strategies, and coordination over time.

CRITICAL REQUIREMENTS:
1. Title (max {MEMORY_TITLE_MAX_LENGTH} chars): short, direct, action-oriented
   (e.g., "Tighten risk on low-liquidity assets", "Use conservative allocation when volatility spikes").
2. Context (max {MEMORY_CONTEXT_MAX_LENGTH} chars): very brief description of the situation or
   recurring pattern (e.g., "Over-trading in sideways markets", "Stops too tight in high volatility").
3. Content (max {MEMORY_CONTENT_MAX_LENGTH} chars): simple list of direct behavior-level commands,
   one per line, no headers or long explanations.

PRECISION REQUIREMENTS (CRITICAL):
- Focus on decision-making, strategy, risk management, and coordination between agents.
- Describe WHEN to apply a rule (market regime, instrument type, time horizon, signal conditions).
- Describe WHAT to do differently (e.g., adjust thresholds, avoid certain patterns, prefer
  particular workflows, add safety checks).
- Avoid restating low-level schema or type constraints that are already enforced by Pydantic
  models (do NOT create memories whose only purpose is to list required fields or types).
- Instead, capture the reasoning behind *why* an agent failed or succeeded so behavior can be
  improved or reused in future similar situations.

FORMAT REQUIREMENTS:
- Use imperative, command-like sentences (e.g., "Reduce position size when volatility increases",
  "Wait for confirmation from multiple indicators before entering a trade").
- NO section headers like "Structured Actions:" or "Guidance:".
- NO numbering prefixes ("1.", "2.", etc.).
- NO full stack traces or raw error messages; summarize them into a short, human-readable issue.
- Prefer a handful of strong, high-value commands over many tiny, redundant ones.

GENERALIZATION RULES (STRICTLY ENFORCED):
- DO NOT include specific cryptocurrency names (e.g., "BTC", "ETH") or hard-coded tickers.
- DO express conditions and behaviors in generic terms (e.g., "asset", "market", "indicator",
  "volatility spike", "low liquidity", "trend vs range").
- Make content reusable across agents and markets by focusing on patterns, not one-off incidents.

You will receive critic analysis that identifies which specific agents need improvements.
Only process memories for agents listed in critic_analysis.agent_improvements.
For each such agent, produce a small set of concise, high-impact behavioral or strategic
instructions that would have helped avoid the issues or replicate the successes."""
    
    async def execute(
        self,
        input_data: typing.Union[agent_models.MemoryInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any,
    ) -> agent_models.MemoryOperation:
        """
        Execute memory operations using LLM.
        
        Args:
            input_data: Contains {"critic_analysis": CriticAnalysis, "agent_outputs": Dict, "execution_metadata": dict}
            ai_service: The AI service instance for LLM calls
            
        Returns:
            MemoryOperation with list of operations performed
        """
        critic_analysis = input_data.get("critic_analysis") if isinstance(input_data, dict) else None
        agent_outputs = input_data.get("agent_outputs", {}) if isinstance(input_data, dict) else {}
        execution_metadata = input_data.get("execution_metadata", {}) if isinstance(input_data, dict) else {}
        
        if not critic_analysis:
            return agent_models.MemoryOperation(
                success=False,
                operations=[],
                memory_ids=[],
                agent_updates={},
                agents_processed=[],
                agents_skipped=[],
                message="No critic analysis provided",
            )
        
        critic_analysis = agent_models.CriticAnalysis.model_validate_or_self(critic_analysis)
        agent_improvements = critic_analysis.get_agent_improvements()
        agents_to_process = list(agent_improvements.keys())
        
        if not agents_to_process:
            return agent_models.MemoryOperation(
                success=True,
                operations=[],
                memory_ids=[],
                agent_updates={},
                agents_processed=[],
                agents_skipped=list(agent_outputs.keys()),
                message="No agents need memory updates",
            )
        
        improvements_summary = []
        for agent_name, improvement in agent_improvements.items():
            improvement = agent_models.AgentImprovement.model_validate_or_self(improvement)
            improvements_summary.append(
                {
                    "agent_name": agent_name,
                    "improvements": improvement.improvements,
                    "issues": improvement.issues,
                    "errors": improvement.errors,
                    "reasoning": improvement.reasoning,
                }
            )
        
        critic_summary = critic_analysis.get_summary()
        critic_issues = critic_analysis.get_issues()
        critic_errors = critic_analysis.errors
        
        messages = [
            {"role": "system", "content": self.prompt},
            {
                "role": "user",
                "content": f"""Transform the following critic feedback into short, simple, precise, command-like
instructions for each agent. Focus ONLY on behavioral, strategic, risk, and coordination
improvements – ignore pure schema/format/type issues.

IMPORTANT FILTER:
- If the feedback for an agent only contains schema/format/type errors (e.g., missing keys,
  wrong types, "output must be dict"), and NO behavioral or strategic issues, then:
  -> Do NOT return any instructions for that agent.
- Only create instructions when there is at least one behavior/strategy/risk/logic issue
  that can improve the agent's decisions.

CRITICAL REQUIREMENTS:
- Title: Maximum {MEMORY_TITLE_MAX_LENGTH} characters - short, direct, behavioral/strategic command.
- Context: Maximum {MEMORY_CONTEXT_MAX_LENGTH} characters - short description of the situation or
  recurring pattern (NOT raw error messages).
- Content: Maximum {MEMORY_CONTENT_MAX_LENGTH} characters - simple list of behavior-level commands,
  one per line.

Critic Summary: {critic_summary}
Team Issues: {self.format_data(critic_issues)}
Team Errors: {self.format_data(critic_errors)}
Agent Improvements:
{self.format_data(improvements_summary)}

Return a JSON object with an "instructions" array containing entries only for agents that
have at least one behavioral or strategic issue to learn from.""",
            },
        ]
        
        try:
            response_data = await self._call_llm(
                messages,
                ai_service,
                json_output=True,
                response_schema=agent_models.AgentMemoryInstructionsList,
                input_data=input_data,
            )
            
            instructions_list_model = agent_models.AgentMemoryInstructionsList.model_validate(response_data)
            
            operations: typing.List[str] = []
            memory_ids: typing.List[str] = []
            agent_updates: typing.Dict[str, typing.List[str]] = {}
            team_producer = execution_metadata.get("team_producer")
            agents_processed: typing.List[str] = []
            agents_skipped: typing.List[str] = []
            
            instructions_list = instructions_list_model.instructions
            instructions_by_agent = {
                item.agent_name: item.instructions
                for item in instructions_list
            }
            
            for agent_name in agents_to_process:
                improvement = agent_improvements[agent_name]
                improvement = agent_models.AgentImprovement.model_validate_or_self(improvement)
                
                agent = None
                if team_producer:
                    try:
                        agent = team_producer.get_agent_by_name(agent_name)
                        if agent is None:
                            manager = team_producer.get_manager()
                            if manager and manager.name == agent_name:
                                agent = manager
                    except (AttributeError, KeyError):
                        agent = None
                
                if agent is None:
                    agents_skipped.append(agent_name)
                    continue
                
                try:
                    memory_enabled = agent.has_memory_enabled()
                except AttributeError:
                    memory_enabled = getattr(agent, "ENABLE_MEMORY", False)
                
                if not memory_enabled:
                    agents_skipped.append(agent_name)
                    continue
                
                try:
                    agent_memory_storage = agent.memory_manager
                except AttributeError:
                    agent_memory_storage = None
                
                if agent_memory_storage is None:
                    agents_skipped.append(agent_name)
                    continue
                
                agent_instructions = instructions_by_agent.get(agent_name)
                if not agent_instructions:
                    agents_skipped.append(agent_name)
                    continue
                
                memory_instruction = agent_models.MemoryInstruction.model_validate_or_self(agent_instructions)
                title = memory_instruction.title
                context_text = memory_instruction.context
                content = memory_instruction.build_content()
                
                await agent_memory_storage.store_memory(
                    messages=[{"role": "user", "content": content}],
                    input_data={"agent_id": ""},
                    metadata={
                        "category": "improvement",
                        "importance_score": 0.7,
                        "title": title,
                        "context": context_text,
                        "source_agent": agent_name,
                        "source_type": "critic_improvement",
                        "memory_system": "ai_memory_agent",
                        "domain_tags": execution_metadata.get("domain_tags", []),
                    },
                )
                
                all_memories = agent_memory_storage.get_all_memories()
                if all_memories:
                    new_memory_id = all_memories[-1].get("id")
                    memory_ids.append(new_memory_id)
                    agent_updates.setdefault(agent_name, []).append(new_memory_id)
                    if "generated" not in operations:
                        operations.append("generated")
                
                agents_processed.append(agent_name)
            
            return agent_models.MemoryOperation(
                success=True,
                operations=operations,
                memory_ids=memory_ids,
                agent_updates=agent_updates,
                agents_processed=agents_processed,
                agents_skipped=agents_skipped,
                message=f"Processed memories for {len(agents_processed)} agents",
            )
        
        except Exception as e:
            self.logger.error(f"DefaultAIMemoryAgentProducer error executing memory operations: {e}")
            return agent_models.MemoryOperation(
                success=False,
                operations=[],
                memory_ids=[],
                agent_updates={},
                agents_processed=[],
                agents_skipped=agents_to_process,
                message=f"Error: {str(e)}",
            )
