---
title: Async Channel
description: Asyncio-based producer/consumer message bus with filtering, priority levels, and synchronized execution mode.
sidebar_position: 1
---

# Async Channel

`async_channel` is OctoBot's internal multi-task communication library. It implements a typed, async producer/consumer message bus built on top of `asyncio.Queue`. Components across the application use it to pass data between loosely coupled parts without holding direct references to each other.

## Channels, producers, and consumers

A `Channel` is the hub that connects one or more producers to one or more consumers. You always subclass it to define a specific data flow, declaring `PRODUCER_CLASS` and `CONSUMER_CLASS` as class attributes. The channel name defaults to the class name with the `"Channel"` suffix stripped; override `get_name()` to change this. `ChannelInstances` is a process-global registry mapping channel names (or `chan_id` and name pairs) to live instances. For deployments where the same channel type exists under multiple IDs, `*_at_id` variant helpers group channels by `chan_id`.

A `Producer` pushes data into consumer queues by calling `send()` to enqueue across all registered consumers. The higher-level `push()` method is the normal entry point and can transform or gate data before calling `send()`. Each producer starts its own `asyncio.Task` via `run()`, unless the channel is in synchronized mode.

A `Consumer` owns an `asyncio.Queue` and runs a background task that continuously dequeues and calls `perform()`, which invokes the registered callback with the queued kwargs. Consumers are registered with a callback and optional filters; each gets its own queue and background task. Stopping the channel stops all producers and consumers in order.

## Filtering

When registering a consumer you provide a `consumer_filters` dict. When a producer calls `get_consumer_from_filters()`, only consumers whose stored filters match all keys in the provided dict are returned. A query value of `CHANNEL_WILDCARD` matches any stored value for that key, and a consumer whose stored value is `CHANNEL_WILDCARD` matches any queried value. If the consumer's stored value is a list, the match succeeds if the queried value appears in it or any list element is the wildcard. An empty filter dict in the query returns all consumers.

## Pause and resume

Channels start in the paused state. A channel resumes its producers automatically when at least one consumer with a non-`OPTIONAL` priority level is registered, and pauses again when no such consumers remain. Producers that only serve `OPTIONAL` consumers are considered logically idle from the channel's perspective — this prevents wasteful processing when nothing meaningful is listening.

## Synchronized mode

In normal operation each consumer and producer runs its own asyncio task. Synchronized mode disables task creation entirely — no tasks are spawned for producers or consumers. Instead, the producer drives execution explicitly by calling `synchronized_perform_consumers_queue()`, which drains each consumer's queue in the current coroutine for consumers at or above the requested priority level. This gives full deterministic control over execution order and is used in backtesting, where you need to replay events in a defined sequence without the non-determinism of concurrent tasks.

## Priority levels

Priority levels serve two purposes. `HIGH` and `MEDIUM` consumers keep producers running; `OPTIONAL` consumers do not. In synchronized mode, consumers are drained in priority order, so high-priority subscribers always process data before lower-priority ones. This ordering matters for backtesting correctness, where strategies must process evaluator output before the next market event is injected.

## Supporting types

`Channel.get_internal_producer()` provides a lazily-created producer that lives on the channel itself, enabling non-producer code to publish without managing an explicit producer reference. It is stopped automatically when the channel stops.

`SupervisedConsumer` extends `Consumer` with an `idle` event that tracks whether `perform()` is currently executing. This lets a producer wait for a specific consumer to finish before continuing — important when correctness depends on consumption order rather than just delivery.

`InternalConsumer` is a consumer subclass where the callback is declared as `internal_callback` on the class itself rather than passed at construction, which is useful when the callback logic is tightly coupled to the consumer's own state.
