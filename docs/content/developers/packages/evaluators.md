---
title: Evaluators
description: Overview of the octobot_evaluators package — the framework for signal generation, strategy composition, and the evaluation matrix.
sidebar_position: 1
---

# Evaluators Package

The `octobot_evaluators` package is the signal-generation and strategy-composition layer of OctoBot. It defines the abstract base classes that all evaluators and strategies extend, the Matrix data structure that holds live evaluation results, and the async channels that route those results to trading modes.

## Evaluator types

All concrete evaluators extend `AbstractEvaluator`, which itself extends `AbstractTentacle` from `octobot_commons`. Three wildcard class methods — one for cryptocurrency, one for symbol, one for time frame — return `True` by default. The factory uses these to decide how many instances to create: one per concrete combination of dimensions, or one shared instance for each wildcard dimension.

`TAEvaluator` fires on closed OHLCV candles. When a re-evaluation trigger arrives on `EvaluatorsChannel`, it re-fetches the last full candle and replays the callback. In live mode it waits up to five minutes for price initialisation before processing the first candle. `RealTimeEvaluator` fires on forming candles and selects the shortest available time frame that satisfies the requested frame at registration.

`SocialEvaluator` consumes external feeds such as news and social media through `octobot_services`. A single instance is shared across all symbols. `ScriptedEvaluator` runs a user-supplied async coroutine, caches results via the trading `Context` cache, and supports hot-reload of the script module via a `RELOAD_SCRIPT` command — it is always bound to specific symbols and time frames, never wildcard.

`StrategyEvaluator` aggregates signals from all other evaluators. Before calling its callback it applies a cycle guard: it checks that the triggering evaluator's Matrix timestamp has actually changed, and that every TA evaluator for the strategy's relevant time frames has a value within the allowed time delta of exchange time. This prevents acting on stale or mixed-freshness signals.

## The eval note

Every evaluator stores its result in `self.eval_note`, a float in `[-1.0, 1.0]` where `-1` is the strongest sell signal and `+1` is the strongest buy. `START_PENDING_EVAL_NOTE` is the sentinel value meaning no result yet. After computing, the evaluator calls `evaluation_completed()`, which writes to the Matrix and broadcasts on `MatrixChannel`. Passing `notify=False` updates the Matrix silently without broadcasting.

## The Matrix

The Matrix is a lazy path-based tree where nodes are created on first write. The canonical path is six segments: exchange name, evaluator type, evaluator name, cryptocurrency, symbol, and time frame. The evaluator type is always one of the `EvaluatorMatrixTypes` string values. Segments are omitted — not set to `None` — when they don't apply, so a social evaluator with no time frame produces a four-segment path while a TA evaluator produces all six. Traversal helpers treat a missing segment as a wildcard, so you can fetch all evaluator nodes under a given exchange and type with a two-segment query.

Each node carries the `eval_note` float, the Unix timestamp at which it was evaluated, the eval note type string, and optional description and metadata blobs. Writes always go through `MatrixChannelProducer.send_eval_note`, and the timestamp stored is the one passed by the evaluator — not wall clock at write time — so backtesting can inject historical timestamps without the staleness check falsely failing.

Reading uses `get_evaluations_by_evaluator`, which walks evaluator-name nodes under a given exchange and type prefix and returns a name-to-node dict. Nodes whose value fails the valid eval note check are silently dropped unless `allow_missing=False`, in which case an `UnsetTentacleEvaluation` is raised.

A node is considered fresh if the current time is within the time frame's duration plus a 10-second allowed delta of the evaluation timestamp. The staleness check requires a path ending in a valid time frame value — paths for non-TA evaluators with no time frame will always be considered stale by that check, which is intentional.

Each `Matrix` instance is assigned a UUID at construction and registered in the process-global `Matrices` singleton. Separate exchange connections therefore have separate matrices and separate channel instances keyed by the same matrix ID.

## Channels and factory

Two async channels run per matrix ID. `EvaluatorsChannel` carries inter-evaluator commands such as re-evaluation triggers and resets; each evaluator subscribes here filtered by symbol and time frame. `MatrixChannel` broadcasts on every `evaluation_completed()` call and is where strategy evaluators and trading modes subscribe.

The factory `create_and_start_all_type_evaluators` is triggered by an evaluator creation event on `OctoBotChannel`. It computes the Cartesian product of cryptocurrencies, symbols, and time frames per evaluator class, skips instances that don't pass the relevant-evaluators filter, and starts survivors in descending priority order drawn from each evaluator's tentacle config. Before the factory runs, a startup helper reads required time frames from all active strategy classes and required candle counts from all active evaluators, writing both into the bot config so the exchange feed buffers the right amount of history before evaluators begin.
