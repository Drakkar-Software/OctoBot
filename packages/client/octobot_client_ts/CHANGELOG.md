# Changelog

## Unreleased

Initial version. `@drakkar.software/octobot-client` is the extraction of `@drakkar.software/octobot-sdk`'s
wallet identity, sync transport, payload encryption, collection registry, node REST client,
strategy/account/automation protocol builders and parsers, user-action orchestration, and the
`connectOctoBot()` facade into its own package, at `packages/client/octobot_client_ts`.

- **Read-only device pairing**: `createReadOnlyPairing()`/`parseReadOnlyPairing()`
  (`identity/pairing.js`) mint and parse a scoped, node-enforced bearer credential for a
  less-trusted client — an ephemeral keypair the scanning device never shares, plus a cap-cert
  restricted to `ops: ['read','list']` and (by default) the `userData`/`accounts` collections.
  The payload carries `collectionKeys`, one HKDF-derived AES-256 subkey per granted collection
  (`crypto/collectionKeys.ts`) — one-way and collection-independent, so a grant can decrypt
  exactly what it was given and nothing else. `connectReadOnlyDevice()` connects with that
  credential instead of a seed; a read-only session throws `OctoBotScopeError` client-side for
  any collection outside its grant, before any network request (the node itself does not yet
  enforce a cap's collection scope). Its `accounts`/`automations`/`strategies` write methods
  build the action(s) and return a `ProposedAction` (a QR-encodable payload) instead of
  appending — `encodeActionProposal()`/`decodeActionProposal()` (`protocol/proposal.js`) define
  that wire format, including the ordering marker `automations.create()`'s two-phase
  `strategy_create`/`automation_create` race needs when a privileged device later executes it.
  `classifyScannedCode()` recognizes both new payload kinds (`octobotReadOnlyPairing`,
  `octobotActionProposal`). See [Read-only devices](https://docs.octobot.cloud/client-sdk/read-only-pairing).
- **Website device-code pairing**: `startPairingRequest()`/`fetchPairingRequestByCode()`
  (`client/pairing/pairingRequest.js`) publish and look up a pairing request; on approval,
  `mintPairingGrant()`/`revokePairingGrant()` (`client/pairing/mirrorGrant.js`) invite/remove the
  website's ephemeral device as a real, read-only `space:member` of the wallet's cloud mirror, and
  `publishPairingGrant()`/`fetchPairingGrant()`/`awaitPairingGrant()`/`clearPairingGrant()`
  (`client/pairing/pairingGrantExchange.js`) seal and exchange that grant. This delivers a live,
  read-only cloud-mirror membership, not a one-time data export — a website reads through
  `readMirrorCollections()`, a real pull against the mirror space, every time. `origin`/`code` are
  what the approving human relies on for identity, not a node credential (this package does not
  yet verify `origin` itself — see [Website pairing](https://docs.octobot.cloud/client-sdk/website-pairing)'s
  `.well-known` convention). New dependency: `@drakkar.software/starfish-keyring`, for
  `seal()`/`unseal()`. Transport primitives in `transport/rendezvous.js` against a single
  `joinsessions` collection (`_pairing/session/{code}`) — the existing `_pairing` QR-pairing
  collection is too small (16 KB, no TTL) for this. Request and grant share one address, keyed by
  the same human-typeable `code`, told apart on the wire by an unsealed `kind` field (see
  [Wire contract](https://docs.octobot.cloud/client-sdk/wire-contract)). See
  [Website pairing](https://docs.octobot.cloud/client-sdk/website-pairing).
- **Breaking**: `PairingRequestPayload` gains a required `requesterKind: 'website' | 'device'` field
  (`identity/pairingRequest.ts`) — `'website'` for the original case, `'device'` for another OctoBot
  client (e.g. a second phone) pairing as a read-only viewer of a wallet's cloud mirror.
  `createPairingRequest()`/`startPairingRequest()` default it to `'website'` when not passed, but
  `parsePairingRequest()` now rejects a payload that omits it — there is no absent-means-website
  fallback. An approving UI should branch its copy on this field (mobile2's
  `website-pairing-approve.tsx` is the reference: a `'device'` request skips the origin-unverified
  warning, since there's no origin to verify — the human relaying the code between two devices they
  hold is the trust anchor). See [Website pairing](https://docs.octobot.cloud/client-sdk/website-pairing)'s
  new `requesterKind` section.
- `accounts.update()` rotates `account_auth_edit`/`exchange_config_edit` before `account_edit`,
  matching the safety ordering the node's account re-validation depends on, and preserves the
  account's original `created_at` rather than re-stamping it on every edit.
- The root `index.ts` re-exports the full protocol type surface (including `AccountTrading`,
  `DetailedAssetsForTradingType`, `CreateAutomationConfiguration`), so `octobot-sdk` sources
  every protocol type through this package instead of depending on
  `@drakkar.software/octobot-protocol` directly.
