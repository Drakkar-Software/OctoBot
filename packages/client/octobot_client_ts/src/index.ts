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
  exchangeConfigIdOf,
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
  type MirrorGrantNodeRef,
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
export {
  createPairingRequest,
  parsePairingRequest,
  parsePairingCode,
  PAIRING_CODE_ALPHABET,
  PAIRING_CODE_LENGTH,
  type PairingRequestPayload,
} from './identity/pairingRequest.js'
export {
  createRendezvousClient,
  pullRendezvousDoc,
  pushRendezvousDoc,
  clearRendezvousDoc,
  joinSessionPath,
  type RendezvousDoc,
} from './transport/rendezvous.js'
export {
  encodeActionProposal,
  decodeActionProposal,
  UnsupportedActionProposalVersionError,
  type ActionProposal,
  type ProposedActionEntry,
} from './protocol/proposal.js'
export { describeProposedAction } from './protocol/proposalSummary.js'
export {
  encodeQrFrames,
  isQrFrame,
  parseQrFrame,
  createQrFrameAccumulator,
  QrPayloadTooLargeError,
  QR_FRAME_CODEC,
  QR_FRAME_HEADER_LENGTH,
  QR_FRAME_INTERVAL_MS,
  QR_FRAME_STALE_MS,
  QR_FRAME_MAX_BYTES,
  QR_FRAME_BODY_MAX_BYTES,
  QR_SINGLE_FRAME_MAX_BYTES,
  QR_MAX_FRAMES,
  QR_FRAME_KIND_UNSPECIFIED,
  QR_FRAME_KIND_ACTION_PROPOSAL,
  QR_FRAME_KIND_READ_ONLY_PAIRING,
  type QrFrame,
  type QrFrameProgress,
  type QrFrameAcceptResult,
  type QrFrameAccumulator,
} from './protocol/qrFrames.js'

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
