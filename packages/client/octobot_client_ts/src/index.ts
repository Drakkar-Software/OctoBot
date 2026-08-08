// @drakkar.software/octobot-client — a TypeScript client for the OctoBot node
// protocol: wallet identity, accounts, automations, strategies, and user
// actions over the Starfish sync transport.
//
// This is the facade tier. It keeps no document cache and no offline
// queue — every read is a fresh pull, every write is a fresh push/append.
// An app that needs persistence, an offline queue, or CRDT merge across
// devices builds that layer ON TOP of this package (see
// https://docs.octobot.cloud/client-sdk/advanced-primitives for the subpath
// exports this is built from).

export {
  connectOctoBot,
  type OctoBotClient,
  type ConnectOptions,
  type SeedDerivation,
  type CallOptions,
  type AccountsApi,
  type AccountInput,
  type AutomationsApi,
  type CreateAutomationInput,
  type CreateAutomationProgress,
  type StrategiesApi,
  type SettingsApi,
  type NodeApi,
  type DocumentsApi,
  type ReadOnlyDocumentsApi,
  type ActionHandle,
  type AccountView,
  type AccountKind,
  type AutomationView,
  type Holding,
  OctoBotError,
  OctoBotConfigError,
  OctoBotConnectionError,
  OctoBotAuthError,
  OctoBotHttpError,
  OctoBotConflictError,
  OctoBotActionError,
  OctoBotTimeoutError,
  OctoBotScopeError,
  isOctoBotError,
  type OctoBotErrorCode,
  connectReadOnlyDevice,
  type ConnectReadOnlyOptions,
  type ReadOnlyOctoBotClient,
  type ReadOnlyAccountsApi,
  type ReadOnlyAutomationsApi,
  type ReadOnlyStrategiesApi,
  type ProposedAction,
  accountViewOf,
  automationViewOf,
  startPairingRequest,
  fetchPairingRequestByCode,
  type StartPairingRequestOptions,
  type PairingRequestSession,
  type PairingRequestLookup,
  buildJoinRequestJson,
  mintPairingGrant,
  revokePairingGrant,
  NothingToShareError,
  type MintedPairingGrant,
  parseMirrorGrantBundle,
  readMirrorCollections,
  attemptDirectMirrorWrite,
  type MirrorGrantBundle,
  type ReadMirrorCollectionsOptions,
  type AttemptDirectMirrorWriteOptions,
  publishPairingGrant,
  clearPairingGrant,
  fetchPairingGrant,
  awaitPairingGrant,
  type UnsealedPairingGrant,
} from './client/index.js'
export {
  MIRROR_COLLECTIONS,
  DEFAULT_MIRROR_COLLECTIONS,
  THIRD_PARTY_ELIGIBLE_MIRROR_COLLECTIONS,
  MIRROR_SPACE_NAME,
  isIsolatedMirrorCollection,
  isKnownMirrorCollection,
  isPublicMirrorCollection,
  isThirdPartyEligible,
  mirrorVisibilityFor,
  type MirrorCollection,
  type MirrorCollectionId,
  type MirrorVisibility,
  syncCloudMirror,
  type SyncCloudMirrorOptions,
  type SyncCloudMirrorResult,
} from './client/mirror/index.js'
export { strategy, type StrategyBuilders } from './client/strategy.js'
export { createReadOnlyPairing, parseReadOnlyPairing, type ReadOnlyPairingPayload } from './identity/pairing.js'
export { createPairingRequest, parsePairingRequest, type PairingRequestPayload } from './identity/pairingRequest.js'
export {
  createRendezvousClient,
  pullRendezvousDoc,
  pushRendezvousDoc,
  clearRendezvousDoc,
  joinSessionPath,
  type RendezvousDoc,
} from './transport/rendezvous.js'
export { encodeActionProposal, decodeActionProposal, type ActionProposal, type ProposedActionEntry } from './protocol/proposal.js'

// The ~20 protocol types the facade's own signatures mention, flattened so a
// first-time user never has to install/import a second package to name a
// return type. For everything else, import from '@drakkar.software/octobot-protocol'
// directly, or '@drakkar.software/octobot-client/protocol' for this package's
// own strategy/state/action builders.
export type {
  Strategy as ProtocolStrategy,
  Account as ProtocolAccount,
  AccountState,
  AccountAuthentication,
  ExchangeConfig,
  AutomationState,
  WorkflowStatus,
  DetailedAsset,
  UserAction,
  UserActionConfiguration,
  DslKeywordsState,
  MarketMakingConfiguration,
  AccountTrading,
  AccountTradingWithAccountId,
  DetailedAssetsForTradingType,
  CreateAutomationConfiguration,
} from '@drakkar.software/octobot-protocol'
