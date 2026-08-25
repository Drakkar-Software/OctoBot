# Changelog

## 0.8.0

- **New: `describeProposedAction(configuration)` (`protocol/proposalSummary.js`)** —
  a human-readable one-line label for a single `ProposedActionEntry`'s configuration
  (`"automation stop"`, `"account create — \"Binance\""`), derived generically from
  `action_type` and an optional nested `name`, never reading credential fields. Promoted
  from mobile2's `src/lib/protocol/proposalSummary.ts`, ported verbatim, now that a second
  consumer outside Astrolab (the OctoBot node web interface's paste-a-proposal dialog)
  needs the identical wording — keeping it in one place avoids the two copies drifting.
  Exported from both the root package and `./protocol`.

## 0.7.0

- **`AccountView`, `AutomationView`, `AccountKind` and `AutomationRunStatus` are un-promoted
  from `@drakkar.software/octobot-protocol` back to hand-declared types in this package
  (partially reverting 0.6.0).** Re-examined against the promotion's own governing rule
  ("does this ever ride the wire?") they all fail it: each is a client-computed projection
  over a real wire type, rebuilt fresh on every call, never itself serialized —
  `AccountKind` only ever typed `AccountView.type` (a coarsening of the real `AccountType`),
  `AutomationRunStatus` only ever typed `AutomationView.status` (a coarsening of the real
  `WorkflowStatus`). Putting them in the shared protocol implied a cross-client wire
  contract that never existed. Behavior and field shapes are unchanged for everything
  except `holdings` (next item) — this is a where-it-lives change, not a what-it-is change.

- **`Holding` is removed entirely, not just un-promoted — `AccountView.holdings` and
  `AutomationView.holdings` are now `DetailedAsset[]` (`{symbol, total, available}`)
  instead of `Holding[]` (`{symbol, total, free, used}`).** Unlike the three types above,
  `Holding` had zero node-side producers anywhere (confirmed against the node's Python
  source) — `free` was always a straight rename of `DetailedAsset.available`, and `used`
  was always `Math.max(0, total - available)`, computed client-side at exactly the two
  sites that built a `Holding`. Since it added no information over `DetailedAsset`, dropping
  it removes a real duplicate rather than just relocating one. **Breaking:** any caller
  reading `.free`/`.used` off an `AccountView`/`AutomationView` holding must now read
  `.available` and compute `total - available` itself (see `octobot-sdk`'s `usedOf` helper
  in the paired Astrolab2 change for the `used` clamp, preserved exactly). `AccountInput.
  holdings` (the write side, in `accounts.ts`) is `DetailedAsset[]` for the same reason.

  As a side effect, `automationViewOf`'s holdings assignment simplifies to
  `automationHoldings(state)` directly — the `{symbol,total,free,used}` mapping used to be
  duplicated between `accountHoldingsFromNodeState` and `automationViewOf`; with `Holding`
  gone, `automationViewOf` needed no mapping of its own at all (nothing downstream ever
  read `Automation.holdings` as `free`/`used`, confirmed against every mobile2 consumer).

- Bump `@drakkar.software/octobot-protocol` dependency to `^0.8.0` (the version with these
  5 schemas removed).

## 0.6.0

- **`AccountView`, `AutomationView`, `AccountKind`, `Holding` and `NodeEndpoint` are now
  generated from `@drakkar.software/octobot-protocol` instead of hand-written here.** They were a client-side
  convenience projection with no room to grow — nothing outside this package could reuse them, and
  a shape only this package knew about is exactly the kind of duplication `octobot-protocol` exists
  to remove. `accountViewOf`/`automationViewOf` still build the same views from the same inputs.
  `AccountView`'s `type: AccountKind` still collapses every non-exchange, non-wallet account (now
  including `broker`/`bank`/`asset`, see below) to `'generic'`.

  **Breaking:** `AutomationView.assets` is renamed to `AutomationView.holdings`. The generated
  `AutomationView` schema composes the wire `AutomationState` (which already has its own, differently
  shaped `assets?: DetailedAssetsForTradingType[]`) with this view's own normalized-to-`Holding[]`
  projection — reusing the same field name for both would have made the schema's `assets` property
  unsatisfiable under strict JSON Schema `allOf` semantics (no value can be simultaneously valid
  against two incompatible item types for one key). `AccountView` already avoided this by naming its
  own projection `holdings` rather than reusing `Account`'s own `assets` field; `AutomationView` now
  follows the same convention.

  Import from `'@drakkar.software/octobot-protocol'` if you were relying on structural identity with
  a hand-built object literal; nothing else changes if you only consumed the exported type names.

- **`Account.specifics` grows three variants: `broker`, `bank`, `asset`.** These existed only as a
  client-side account taxonomy (Astrolab's local mirror) with no way to round-trip through the node,
  which forced every non-exchange, non-wallet account to collapse to `'generic'` and smuggle its real
  kind through `Account.description`. `AccountType` and `AccountSpecifics` now model all five kinds
  directly: `BrokerAccount { account_type: 'broker', provider_id, exchange_config_ids? }`,
  `BankAccount { account_type: 'bank', institution?, currency? }`,
  `AssetAccount { account_type: 'asset', asset_type?, cost_basis? }`. A node that has never seen these
  kinds is unaffected — they are additive to `oneOf`/`enum`, not a change to the existing three.

- **`ActionProposal` and `ProposedActionEntry` are now generated from `@drakkar.software/octobot-protocol`**,
  for the same reason: this envelope crosses client boundaries (a read-only device to a privileged
  one), so it belongs in the shared protocol contract rather than a private type only this package
  declared. `encodeActionProposal`/`decodeActionProposal` remain hand-written here — the protocol
  package ships types only, with no logic and no build step — and their wire format, argument, and
  return shapes are unchanged.

  **`decodeActionProposal` now distinguishes an unsupported envelope version from a malformed one.**
  A payload with `kind: 'octobot-action-proposal'` but a `v` this build does not recognise previously
  threw the same generic `Error` as garbage input. It now throws `UnsupportedActionProposalVersionError`
  (exported from the root, `/protocol`, and this package), carrying the unrecognised `version`, so a
  caller can tell "this is a proposal from a newer app, prompt to update" apart from "this isn't a
  proposal at all."

  **The `after: 'previous-confirmed'` chaining in `connectReadOnlyDevice`'s write methods is now
  complete.** `accounts.create()`/`update()`/`delete()` previously chained only the first pair of a
  three-entry graph; `after` only guarantees the *immediately preceding* entry is confirmed, so an
  unchained third entry could still be appended before the second was confirmed and fail
  non-retriably on the node. All three methods now chain every entry to the one before it.
  `automations.update()` previously omitted the chain between `strategy_edit` and `automation_edit`
  entirely, even though `automation_edit` resolves its strategy by `(id, version)` against the same
  node-side `StrategyProvider` race `automations.create()` already sequences around — it now chains
  them the same way `create()` does.

- **`automationStrategyRefOf` no longer rescans `actions` per automation.** Mapping a whole automation
  list (`listWithActions()`, and `octobot-sdk`'s `automationsFromUserData`) called it once per
  automation, each call re-walking the full `actions` array — O(automations × actions). The scan is
  now factored into `automationStrategyRefsOf(actions)`, a single O(actions) pass returning a
  `Map<automationId, {id, version?}>`; `automationStrategyRefOf` is now a thin `.get()` over it, and
  `automationViewOf` takes an optional third `strategyRefs` parameter so a caller mapping many
  automations can precompute the map once and pass it through instead of paying the scan per item.
- **`exchangeConfigIdOf` (the exchange/blockchain/broker `exchange_config_ids` resolution rule inside
  `accountViewOf`) is now exported.** `octobot-sdk`'s `accountFromNodeState` had an identical,
  hand-copied function; it now imports this one instead.
- **`automationStrategyRefOf` (single-id lookup) no longer routes through `automationStrategyRefsOf`
  (the batch map).** It briefly did, right after the O(automations × actions) fix above, which fixed
  the loop case but made a single one-off lookup build a `Map` entry for every OTHER automation in
  the action history too. Both now share only the per-action extraction logic
  (`automationStrategyRefFromAction`); `automationStrategyRefOf` goes back to a targeted single-pass
  scan, `automationStrategyRefsOf` keeps its own aggregating pass. Same guidance as before: call
  `automationStrategyRefsOf` once for a loop over many automations, `automationStrategyRefOf` for a
  genuine one-off.
- **`connectReadOnlyDevice`'s multi-entry `after: 'previous-confirmed'` chaining is now built by a
  shared `chainEntries()` helper** instead of a repeated `entries.length ? 'previous-confirmed' :
  undefined` ternary at each of `accounts.create/update/delete` and `automations.create/update`. No
  behavior change — every entry past the first was already chained; this just removes the
  duplication.

## 0.5.0

- **Multi-frame QR transport (`protocol/qrFrames.ts`).** This package has always said "render the
  payload as a QR code with whatever QR library you already have", which quietly assumed the payload
  fits one code. Several do not: a multi-action proposal from `automations.create()` runs to
  thousands of bytes, and a read-only pairing payload is around 1.2 KB. Encoded into a single code
  those reach a module density a phone camera struggles with, and nothing in the package helped.

  `encodeQrFrames(payload)` splits an oversized string into `OBQR2|…` frames a producer cycles at
  `QR_FRAME_INTERVAL_MS`, and `createQrFrameAccumulator()` reassembles them on the scanning side.
  The codec is payload-agnostic: plain string in, plain string out, so a reassembled payload goes
  back through `classifyScannedCode` exactly as a single-frame one does, and nothing new has to be
  taught about proposals or pairing payloads. A payload at or below `QR_SINGLE_FRAME_MAX_BYTES` is
  returned unframed and byte-identical, so short codes stay on the path they already use.

  Each frame carries a one-character advisory kind tag (`QR_FRAME_KIND_*`). The codec never
  interprets it. It exists so a single-purpose scanner can pass `acceptKind` and drop another kind's
  transfer at its first frame instead of collecting every frame and discovering the mismatch only
  after reassembly. Pinned in `tests/wireContract.test.ts`: this format is shared between whatever
  displays a QR and whatever scans it, so a drift breaks a hand-off as silently as a sync-path
  mismatch does.

- **Pairing codes are parseable from outside the package.** `CODE_ALPHABET` and `CODE_LENGTH` were
  private, so any client that scans both device-code pairing codes and JSON payloads had to
  re-derive the shape by hand and silently drift the day either changed. `parsePairingCode(value)`
  now normalizes (trim, upper-case) and validates one, returning the canonical code or `null`, and
  `PAIRING_CODE_ALPHABET` / `PAIRING_CODE_LENGTH` are exported alongside it. A pairing code is a
  bare human-typeable string, so `classifyScannedCode` has no shape to match it against and reports
  `'unknown'`: testing for one is necessarily the caller's job, and this gives them the real
  definition instead of a copy of it.

## 0.4.0

- **Cloud mirror: one space per wallet, per-node pairing grants.** The mirror used to spread a
  wallet's collections over three spaces (`octobot-mirror`, `-private`, `-public`) because a space
  keyring is space-wide and a `space:member` grant reaches every encrypted node in the space — so the
  only way to keep `user-settings` out of a website grant was to put it in a different space.
  Per-node keyrings (`starfish-replica`'s new `tier: "isolated"`) remove that constraint: every
  collection now lives in ONE `octobot-mirror` space, and `visibility` decides its tier instead of
  its space — `"shared"` → isolated (own keyring, stored in `objinv`), `"private"` → the space
  keyring (`objdoc`), `"public"` → plaintext (`objpub`).

  `mintPairingGrant` mints one `inviteToNode(..., {isolated: true, write: false})` per granted
  collection instead of a single `inviteToSpace`. The website is never added to the space roster, so
  it cannot read `objindex` and cannot enumerate what other collections exist; `user-settings` is
  unreachable by construction rather than by policy. `revokePairingGrant` now takes the granted node
  ids plus the member's KEM pubkey and rotates each node's keyring, so revoking one collection leaves
  the others working.

  **Breaking, on both halves of the wire.** The grant bundle is now
  `{v: 1, spaceId, nodes: [{collectionId, nodeId, contentCap, keyringCap}]}`; an old space-wide
  bundle is rejected loudly by `parseMirrorGrantBundle` rather than read as empty.
  `readMirrorCollections` takes `nodes` instead of `cap`, `fetchPairingGrant` returns `nodes`
  instead of `cap`, `SyncCloudMirrorResult` collapses its three space ids to one `spaceId`, and
  `MIRROR_SPACE_{SHARED,PRIVATE,PUBLIC}_NAME`/`mirrorSpaceNameFor` are replaced by
  `MIRROR_SPACE_NAME`. Requires `starfish-replica` ≥ 3.0.0-alpha.72.

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
