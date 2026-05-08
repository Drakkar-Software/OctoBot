# OctoBot Protocol

Shared **data shapes** for OctoBot (accounts, orders, trades, automations, and related enums) used across runtimes. The contract is an OpenAPI 3.1 document with **only component schemas**—there are no HTTP paths; this package is for types and serialization, not for describing REST endpoints.

## Layout

| Path | Role |
|------|------|
| `openapi.json` | Source of truth for all generated models |
| `octobot_protocol/` | Python package (`octobot_protocol.models`) |
| `octobot_protocol_ts/` | TypeScript (`typescript-fetch` codegen) |
| `octobot_protocol_rs/` | Rust crate (`rust` codegen) |
| `openapi_generator_templates/python/` | Mustache overrides for Python package layout |
| `scripts/clean-protocol-codegen-output.mjs` | Deletes previous codegen output before regenerate (keeps `octobot_protocol_ts/README.md`) |
| `test/` | Python unittest suite for generated models |

Note: for now octobot_protocol_ts and octobot_protocol_rs are gitignored.

## Regenerating clients

From this directory, install dev tooling once, then run the generators you need:

```bash
npm install
npm run generate:python    # Python + model tests
npm run generate:typescript
npm run generate:rust
npm run generate:all       # all three
```

Shortcuts: `npm run gen` runs Python generation only.

Generators are driven by `@openapitools/openapi-generator-cli`; the CLI version is pinned in `openapitools.json` (currently **7.22.0**).

**Python generation** cleans `octobot_protocol/` and the root-level OpenAPI Python artifacts (`setup.py`, `requirements.txt`, etc.), regenerates into `octobot_protocol/`, then runs `python -m unittest discover -s test` (`npm run test:models`).

After changing `openapi.json`, regenerate the languages you ship so consumers stay in sync.

## Schemas in `openapi.json`

Component schemas (subject to change when the spec changes):

- **Enums / simple types:** `TaskStatus`, `Side`, `OrderType`, `OrderStatus`, `PositionStatus`, `AccountType`
- **Trading:** `Order`, `OrderGroup`, `OrderSummary`, `Trade`, `TradeSummary`, `Position`, `PositionSummary`, `TrailingProfile`, `CancelPolicy`, `ActiveOrderSwapStrategy`
- **Accounts & assets:** `Account`, `AccountsState`, `ExchangeAccount`, `BlockchainAccount`, `GenericAccount`, `CopiedAccount`, `CopiedAsset`, `Asset`
- **Automations:** `AutomationState`, `AutomationsState`, `AutomationMetadata`, `Action`

## Consuming the Python package

Add `OctoBot/packages/protocol` (or the generated tree) to `PYTHONPATH`, or install the package however your workspace wires local packages. Import models from `octobot_protocol.models`.

## Consuming TypeScript / Rust

TypeScript output lives under `octobot_protocol_ts/` (package name in codegen: `@octobot/protocol-ts`). Rust output lives under `octobot_protocol_rs/` with `packageName=octobot_protocol_rs`. Regenerate after spec changes before publishing or vendoring those trees.
