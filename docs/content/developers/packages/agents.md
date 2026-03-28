---
title: Agents
description: Multi-agent AI orchestration framework built on async channels, supporting teams, memory, self-improvement, debate phases, and LangChain Deep Agents integration.
sidebar_position: 1
---

# Agents Package

`octobot_agents` provides the infrastructure for composing and running multi-agent AI workflows inside OctoBot. It defines an abstract layer on top of `async_channel` that lets you build individual LLM-backed agents, wire them into teams, orchestrate execution order, score results with a critic, and improve performance over time through a persistent memory subsystem.

## Core abstractions

An **Agent** is a single LLM-backed unit that runs against input data and produces a result. Each agent type has its own channel class that routes results from a producer to one or more consumers, following the `async_channel` pattern used throughout OctoBot.

A **Team** is a DAG of agents managed by a single manager agent. The team controls execution order, passes outputs between agents, and optionally runs debate and self-improvement cycles on top of the main execution pass.

The **Manager** decides what runs and in what order. It can work in two modes: plan-driven, where it produces an ordered `ExecutionPlan` before any agent fires, or tools-driven, where it calls agents directly as tools and returns a `ManagerResult`. The right mode depends on whether the task is structured enough to plan ahead.

The **Critic** runs after team execution and produces a structured analysis of issues, inconsistencies, and per-agent improvement notes. Its output feeds directly into the memory subsystem.

The **Judge** arbitrates debate phases: given the accumulated debate history it returns either continue or exit, with an optional synthesis summary. The default maximum is three rounds.

## Execution modes

Three team execution strategies are available. **Sync** is one-shot sequential — the manager produces a plan or result, agents execute in DAG order, and the call returns when all results are collected. **Live** is long-running async — channels are wired, agents fire as upstream results arrive, and completion is signaled when all terminal agents finish. **Deep Agents** delegates to a LangChain supervisor with `SubAgentMiddleware`, which orchestrates workers as subagents and supports both `ainvoke` and streaming. The Deep Agents path is optional; the package remains fully importable without the LangChain dependencies installed.

## Self-improvement loop

When a team is configured with `self_improving=True`, execution triggers an additional pass in the background. The `CriticAgent` receives all agent outputs and produces an analysis, then the `MemoryAgent` writes new memories to each agent's `JSONMemoryStorage`. On the next run, agents retrieve those memories via LLM tool calls and adjust their behavior accordingly. Both steps run as a background `asyncio.Task` so they do not block the caller waiting for results.

Memory files are stored per agent class and pruned when they exceed the configured maximum, prioritizing entries with high importance and high usage. The effect is that frequently useful memories survive compression while stale ones are dropped.

## Skills

Skills are markdown files with YAML frontmatter that describe capabilities or domain knowledge an agent should be aware of. They live in a `skills/` directory alongside the agent's code and are auto-discovered at build time, then passed into the agent's context during inference. Individual agents can also receive skills injected at instantiation time, separate from the directory-level defaults.

## Deep Agents and human-in-the-loop

The Deep Agents integration supports tool-level interrupts. An interrupt configuration identifies which tools require human approval before proceeding — for example, high-risk tools like order placement. When execution hits one of those tools, the workflow pauses and surfaces an `__interrupt__` in its result. The caller can then resume by approving all interrupts, rejecting them, or providing explicit decisions per tool.

## Utilities

The package includes resilient JSON extraction helpers for parsing LLM output, which rarely arrives as clean JSON. The extractor tries multiple strategies in sequence: brace-matching from mixed text, extraction from fenced code blocks, extraction from XML-style tags, and preprocessing to strip fences and escape sequences. An async retry decorator wraps the tools-driven manager's LLM calls internally.
