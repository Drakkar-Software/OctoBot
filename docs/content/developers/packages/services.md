---
title: Services
description: Architecture and concepts of the octobot_services package — services, service feeds, interfaces, and the notification system.
sidebar_position: 1
---

# Services Package

`octobot_services` is OctoBot's integration layer between external systems and the rest of the bot. It defines the abstract contracts and runtime machinery for connecting to third-party APIs, streaming external data into the internal channel bus, presenting user-facing interfaces, and delivering notifications. All four concepts share a common lifecycle managed by factory and manager utilities and wired together through a single `octobot_channel_consumer` callback.

## Services

`AbstractService` is the base class for every external connection. Each concrete service class is a singleton — at most one live instance per service type exists at runtime. Configuration is stored under the top-level `services` key, with each service reading and writing its own sub-key. `save_service_config` persists changes back to disk. The `say_hello()` method emits a startup message and sets an internal health flag that the factory checks before handing an instance to callers.

`ServiceFactory` provides an idempotent `create_or_get_service` that either returns an existing healthy instance or creates a new one by calling `prepare()` then `say_hello()`. It discovers all concrete service subclasses via the tentacle system.

`AbstractAIService` extends the base for LLM backends. It adds a complete invocation layer: single-shot completions, an agentic loop that drives tool calls up to a configurable iteration limit, provider-aware message construction, and a retry decorator for common parsing failures. Model selection is policy-driven — an `AIModelPolicy` value like `"fast"` or `"reasoning"` is resolved to a concrete model name at runtime via the service's models config. Hooks for LangGraph integration are also provided. `AbstractWebSearchService` follows the same pattern for search backends, adding normalized `search` and `search_news` methods.

## Service feeds

`AbstractServiceFeed` bridges an external data stream to an internal async channel. Each feed declares the `FEED_CHANNEL` that becomes its internal distribution bus and the `REQUIRED_SERVICES` that must be healthy before it can start. Simulator subclasses set a flag for backtesting use. `ServiceFeeds` is a singleton registry mapping `(bot_id, feed_name)` pairs to instances; `ServiceFeedFactory` instantiates feeds and registers them there.

## Interfaces

`AbstractInterface` is the base for all user-facing surfaces. Two specialisations exist: `AbstractBotInterface` for chat-style interfaces such as a Telegram bot, which provides helpers that query the trading API and format responses for portfolio status, trade history, open orders, and control commands; and `AbstractWebInterface` as a marker subclass for browser-based interfaces. All interfaces share class-level metadata — bot ID, project name, project version — set once at startup via `AbstractInterface.initialize_global_project_data`.

## Notifications

A `Notification` is a plain value object carrying a plain-text body, a markdown body, a short title, a severity level, a category, an optional sound hint, and an optional link to a prior notification. `NotificationChannel` is an async channel with a singleton producer. `api.notification.send_notification` pushes onto it. If the channel is not yet running when a notification is sent, it is buffered up to a cap of ten and replayed once the channel comes up.

`AbstractNotifier` is the delivery end. Each notifier declares the config key that activates it, the services it depends on, and a `_handle_notification` implementation that delivers to its transport. Notifiers also subscribe to the trading `OrderChannel` for automatic order lifecycle notifications alongside the `NotificationChannel`.

## Lifecycle utilities

`AbstractServiceUser` combines `InitializableWithPostAction` with automatic service dependency resolution. Subclasses declare `REQUIRED_SERVICES` as a list of service classes, or `False` when no service is needed. During initialization, each required service is created or fetched via the factory. `InitializableWithPostAction` guards against double initialization and chains into a post-init hook. `ReturningStartable` provides both async and threaded start modes. `ExchangeWatcher` tracks exchange registrations and notifies subclasses when a new exchange comes online — used by interfaces and notifiers that need to react to new exchange connections.

## OctoBot channel integration

`octobot_channel_consumer.py` connects this package to the top-level OctoBot channel bus. It handles creation events for interfaces, notifiers, and service feeds; exchange registration updates for interfaces and notifiers; and start requests for named service feeds. After creation, a confirmation is sent back on the OctoBot channel so the caller knows the instance is ready.
