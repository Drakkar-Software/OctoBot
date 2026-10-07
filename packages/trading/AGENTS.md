# Agents: trading

## Role

`octobot_trading` is the **shared trading engine** for the live bot, backtesting, and flow/node jobs—not strategy or UI logic.

- **Exchange lifecycle:** `ExchangeBuilder` → `ExchangeManager` and global registry; live **ccxt** connector + adapters vs simulator/backtest paths. Exchange-specific REST overrides subclass connectors in **tentacles**; abstractions and wiring live here.
- **Market data:** per-type managers, channels, and updaters (candles, ticker, order book, trades, funding); exchange **readiness** before strategies act on incomplete state.
- **Orders and portfolio:** order graph (chains, groups, triggers, trailing); fund reservations; sub-portfolios per trading mode; futures position variants; trades, transactions, optional persistence and recovery.
- **Trading modes and signals:** producer/consumer channel from evaluators to order execution; scripted modes and trading DSL hooks; signal broadcast for copy trading.
- **Out of scope:** evaluator matrices, automation DAGs, FastAPI/node scheduling, tentacle `metadata.json` or web UI.

## Owns

- `packages/trading/octobot_trading/`
- `packages/trading/tests/`

## Public surface

- `octobot_trading.exchanges` — `ExchangeManager`, `ExchangeBuilder`, channel wiring
- `octobot_trading.exchanges.connectors.ccxt` — production connector and adapters
- `octobot_trading.api` — exchange, portfolio, and related helpers
- `octobot_trading.personal_data` — orders, portfolios, positions, trades
- `octobot_trading.storage`, `octobot_trading.signals`, trading-mode channels

## May depend on

- `octobot_commons`, `async_channel` (as imported today)

## Do not

- Add flow `AutomationState`, node DBOS, or scheduler code here
- Put evaluator or tentacle class implementations here
- Edit repo-root `tentacles/` (install output)
- Bypass connector abstractions with one-off exchange REST in core—extend tentacle connectors and add tests

## Tests

- **cwd:** `packages/trading`
- **Example:** `pytest tests -n auto --dist loadfile`
- CI matrix runs from this package dir; tentacles not required unless the test integrates installed tentacles

## Related human doc

- `docs/content/developers/packages/trading.md`

## Last reviewed

- 2026-09-16
