# CLAUDE.md — @drakkar.software/octobot-client

## Hard rules

- **No state, no storage, no React, no zustand.** Every read pulls fresh; nothing is cached beyond
  the derived key material for the current `connectOctoBot()` session (dropped by `close()`).
- **Layering: `client/` is the only tier that may be imported by an external user.** Everything else
  (`identity/ transport/ crypto/ collections/ protocol/ node-api/`) is tier 1 — pure primitives,
  no lifecycle, no caching beyond what a single function call needs. Tier 1 code NEVER imports
  `client/`. `protocol/` additionally never imports `transport/`, `identity/`, or `crypto/` — it
  stays I/O-free so its tests run with zero network stub. Both rules are enforced by
  `tests/layering.test.ts`; a failure there means a file landed in the wrong tier, not that the test
  needs updating.
- **Comments explaining *why* are load-bearing — never shorten them during a refactor.** The
  `LEGACY_PATH` prose in `identity/evm.ts`, the account-graph derived-id comments in
  `protocol/actions.ts`, and the two-phase race explanation in
  `protocol/orchestration/createAutomation.ts` encode expensive-to-relearn knowledge.
- **The QR wire format lives here, all of it.** `protocol/qrFrames.ts` is the multi-frame QR
  transport (`OBQR2|…`), and it belongs next to `protocol/proposal.ts` rather than in whichever app
  happens to render a code: a client that can decode a single-frame payload but not a framed one is
  broken in a way nothing here would catch. It is payload-agnostic on purpose, so a reassembled
  string goes back through `classifyScannedCode` like any other scan. It reaches `keccak_256` by
  importing `@noble/hashes` directly, never `crypto/`, which is what keeps it inside `protocol/`
  under the layering rule above. This package still never renders a QR image itself.
- **Every wire-shared literal is a silent-failure hazard.** Check https://docs.octobot.cloud/client-sdk/wire-contract and
  `tests/wireContract.test.ts` before changing anything in `crypto/wireConstants.ts`,
  `identity/capProvider.ts`'s `BOOTSTRAP_CHALLENGE`, or `collections/nodeCollections.ts`'s
  `encryptionInfo` strings — the node's Python side (`packages/sync/octobot_sync/`) has to change in
  the same commit, or sync breaks with no error on either side.

## Commands

```bash
npm run build   # tsc --build
npm test        # vitest run
```

## Type boundary, if you're moving more code here from octobot-sdk

A function moves here iff it operates purely on protocol-shaped types (`Account`/`Strategy`/
`AutomationState`/`UserAction` from `@drakkar.software/octobot-protocol`). A function that merges
protocol state into a CRDT-tombstoned, UI-shaped local domain object — or converts one into a
protocol payload — stays in the consuming app as a thin adapter that imports the moved primitive.
