# @drakkarsoftware/octobot-commons

Browser-friendly TypeScript port of the subset of `octobot_commons` that downstream OctoBot TS packages need: a swappable logger, async-tool helpers (`Deferred`, `AsyncEvent`, `sleep`, `fireAndForget`), a tiny `EventBus`, decimal-math helpers (`decimal.js`), symbol parsing (`BTC/USDT:USDT`), shared enums (timeframes, price indexes), and a base proxy-config dataclass.

Lives in the `OctoBot/` pnpm workspace alongside the Python pants resolve. Consumed by `@drakkarsoftware/octobot-trading` via `workspace:*`.

## Build and test

```bash
# from the workspace root
pnpm install
pnpm -r --filter "@drakkarsoftware/*" run build

# this package only
pnpm --filter @drakkarsoftware/octobot-commons run build
pnpm --filter @drakkarsoftware/octobot-commons run test
```
