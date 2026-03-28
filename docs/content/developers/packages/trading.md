---
title: Trading
description: Overview of the octobot_trading package — the core trading engine for exchange connectivity, order management, portfolio tracking, and trading mode abstraction.
sidebar_position: 1
---

# Trading Package

`octobot_trading` is the core trading engine. It owns everything between a raw exchange API call and a filled order: exchange connectivity, market data ingestion, order lifecycle, portfolio tracking, and the strategy abstraction layer that trading modes build on.

## Exchange management

Each connected exchange gets one `ExchangeManager`, the root object that wires together connectors, traders, and data managers. Mode flags on that object control which code paths activate, so the same trading mode logic runs identically across live, simulated, and backtesting contexts without branching.

`ExchangeBuilder` is the only supported construction path. It resolves the active trading mode, registers the manager in a global registry singleton, and starts all subsystems in the right order. A shared market cache prevents redundant REST fetches when multiple exchange instances reference the same market.

The production connector wraps ccxt and normalises all responses through an adapter layer, converting ccxt exceptions into internal types. Exchange-specific tentacles subclass the REST connector to override parsing or expose additional endpoints. For backtesting, a simulator connector replays data from importers instead of hitting the exchange at all.

## Market data

Each data type — candles, tickers, order book, trades, funding — follows the same manager/channel/updater pattern. Managers hold in-memory state, channels broadcast updates via async_channel, and updaters pull from REST or push via WebSocket. The switch between REST polling and WebSocket is transparent to anything consuming the channel.

Candles are stored as a circular buffer, three thousand entries per time frame. Mark price resolves from four possible sources with automatic fallback. Components can register price-threshold callbacks against the mark price stream; this is how simulated stop-loss and take-profit orders detect when their fill condition is met without polling.

The exchange is considered ready only after a defined set of channel topics has produced their first update. Futures exchanges require additional signals — positions, contracts, funding rates — before the ready flag is set, preventing strategies from acting on incomplete state.

## Orders and portfolio

Orders carry a stable internal UUID alongside the exchange-assigned ID. They support chained orders that auto-submit on fill, order groups for coordinated take-profit and stop-loss, trailing price profiles, and price-based triggers that hold an order inactive until a threshold is crossed. Open orders are capped in count and serialised to storage for restart recovery.

Portfolio accounting uses async locks and maintains fund reservations — funds are locked on order creation and released on fill or cancel. When multiple trading modes share one exchange, sub-portfolios partition the accounting so each mode operates against its own slice. Value conversion to a reference market enables consistent profitability tracking across assets.

Futures positions come in two structural variants — linear/quote-margined and inverse/base-margined — with different PnL and margin calculations. Trades are immutable fill records; transactions cover fees, PnL events, deposits, withdrawals, and transfers, with duplicate-insertion protection to handle exchange re-delivery.

## Trading modes

Trading modes define the strategy abstraction layer. A mode channel carries market signals from producers — which subscribe to evaluator matrix updates or candle-close events — to consumers that translate those signals into exchange operations. The split between producer and consumer is what allows the same evaluation logic to drive different order behaviours.

Scripted trading modes allow user-defined Python scripts with hot reload. A context object aggregates the exchange manager, symbol, time frame, and trigger candle into a single handle. A built-in DSL covers amount translation, price offset calculation, and position inspection. A script declares its required candle feeds upfront so the framework activates them before the first script call.

## Signals and storage

The signal system lets one OctoBot broadcast order operations as structured bundles for followers to replicate. Signals capture the full order dependency graph — chained orders, groups, triggers — and use portfolio-relative sizing so followers scale to their own portfolio rather than copying absolute quantities.

Order storage serialises the complete in-memory graph including groups, chains, trailing profiles, and triggers. On startup, all values are reconstructed with Decimal precision restored from strings to avoid floating-point drift accumulated during serialisation. Optional historical storage records every order status change rather than just the terminal state.
