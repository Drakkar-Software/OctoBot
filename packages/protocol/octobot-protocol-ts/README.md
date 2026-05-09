# @drakkarsoftware/octobot-protocol

TypeScript types for the OctoBot protocol. The contents of `src/` are **generated** from `packages/protocol/openapi.json` by the OpenAPI Generator workflow at `packages/protocol/`. Do not edit `src/` by hand — changes will be overwritten on the next codegen.

## Regenerating

```bash
# from packages/protocol/
npm run generate:typescript
```

This wipes everything inside `octobot-protocol-ts/` except this `README.md`, `package.json`, `tsconfig.json`, and `.gitignore`, then re-emits `src/` and `docs/`.

## Building

```bash
# from the workspace root (OctoBot/)
pnpm --filter @drakkarsoftware/octobot-protocol run build
```

Produces ESM (`dist/`) + CJS (`dist/cjs/`) + `.d.ts`. The package re-exports every model and the OpenAPI Generator runtime helpers.

## Consumers

- `@drakkarsoftware/octobot-node` — uses `AutomationState`, `Execution`, `TaskStatus` to type the state bag passed through the automation runner.
