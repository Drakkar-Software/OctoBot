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
| `scripts/clean-protocol-codegen-output.mjs` | Deletes previous codegen output before regenerate (cleans root `test/test_*.py` only; keeps `test/compat/`) |
| `test/` | Generated model tests + hand-written compat under `test/compat/` (never cleaned on regen) |

Note: `octobot_protocol_ts/` is tracked and published from this repo (see its own
`package.json`). `octobot_protocol_rs/` is configured in `openapitools.json` but has never
been generated, so it does not exist on disk yet.

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

**Python generation** cleans `octobot_protocol/` and root `test/test_*.py` only (not `test/compat/`), regenerates into `octobot_protocol/`, then runs generated model tests (`npm run test:models`).

Consumers locate wire JSON via `scripts.lib.openapi_compat_lib.wire_root_dir()` → `test/compat/static/wire/`. Downstream wire tests in sync, node, and flow prepend `packages/protocol` via scoped `conftest.py` so `import scripts.lib.openapi_compat_lib` is not shadowed by another `scripts` package on `PYTHONPATH`.

After changing `openapi.json`, regenerate the languages you ship so consumers stay in sync.

## Backwards compatibility workflow

After editing `openapi.json`:

```bash
npm run generate:python
python -m scripts.build_openapi_schema_manifest
npm run generate:fixtures
```

Run compatibility tests with `pytest test` (or `npm run test:pytest`).

Hand-written compat tests and static fixtures live in `test/compat/`. Root `test/test_*.py` are openapi-generator output and are wiped on `npm run generate:python` before regen.

- `test/compat/static/openapi_schema_manifest.json` — structural schema contract.
- `test/compat/static/wire/` — versioned wire JSON consumed by sync, node, and flow tests.
- `npm run check:fixtures` — fails if wire fixtures are stale.
- `npm run promote:fixtures -- 1.1.0` — archive active wire version to `legacy/` and regenerate a new active version after an intentional breaking change.

Non-breaking changes: regenerate manifest and fixtures in the same PR. Breaking changes: add sync migration tests, archive legacy wire snapshots, bump versions, then regenerate manifest and fixtures.

### Compatibility test layers

| Layer | Package | What it checks |
|-------|---------|----------------|
| Strict parse + roundtrip | `protocol` | Active and archived wire JSON must parse with generated models |
| Tolerant load | `sync` | State envelopes load through `TolerantStateLoader` (active + `legacy/v*/`) |
| Bridge transforms | `node` | Outbound protocol bridges produce wire-safe output (`test_wire_compat.py`) |
| Consumer smoke | `flow` | Fixtures feed real consumer code paths |

After `npm run promote:fixtures -- <new_version>`, the previous active tree is archived under `legacy/v{old}/`. Protocol strict-parse tests and sync tolerant-load tests pick up those snapshots automatically.

After `npm run generate:fixtures -- --promote-files <paths...>`, register each archived file in `test/compat/legacy_fixture_expectations.py` and `SYNC_LEGACY_AD_HOC_EXPECTATIONS` in `packages/sync/tests/protocol/test_wire_compat.py` before merging.

## Schemas in `openapi.json`

Component schemas (subject to change when the spec changes):

- **Enums / simple types:** `WorkflowStatus`, `Side`, `OrderType`, `OrderStatus`, `PositionStatus`, `AccountType`
- **Trading:** `Order`, `OrderGroup`, `OrderSummary`, `Trade`, `TradeSummary`, `Position`, `PositionSummary`, `TrailingProfile`, `CancelPolicy`, `ActiveOrderSwapStrategy`
- **Accounts & assets:** `Account`, `AccountsState`, `ExchangeAccount`, `BlockchainAccount`, `GenericAccount`, `CopiedAccount`, `CopiedAsset`, `Asset`
- **Automations:** `AutomationState`, `AutomationsState`, `AutomationMetadata`, `Action`

## Consuming the Python package

Add `OctoBot/packages/protocol` (or the generated tree) to `PYTHONPATH`, or install the package however your workspace wires local packages. Import models from `octobot_protocol.models`.

## Consuming TypeScript / Rust

TypeScript output lives under `octobot_protocol_ts/` (package name in codegen: `@octobot/protocol-ts`). Rust output lives under `octobot_protocol_rs/` with `packageName=octobot_protocol_rs`. Regenerate after spec changes before publishing or vendoring those trees.
