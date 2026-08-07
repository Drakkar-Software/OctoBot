export {
  connectOctoBot,
  type OctoBotClient,
  type ConnectOptions,
  type SeedDerivation,
  type CallOptions,
} from './connect/connect.js'
export {
  connectReadOnlyDevice,
  type ConnectReadOnlyOptions,
  type ReadOnlyOctoBotClient,
  type ReadOnlyAccountsApi,
  type ReadOnlyAutomationsApi,
  type ReadOnlyStrategiesApi,
  type ProposedAction,
} from './connect/readOnly.js'
export { type AccountsApi, type AccountInput } from './adapters/accounts.js'
export { type AutomationsApi, type CreateAutomationInput, type CreateAutomationProgress } from './adapters/automations.js'
export { type StrategiesApi } from './adapters/strategies.js'
export { type SettingsApi } from './adapters/settings.js'
export { type NodeApi } from './adapters/nodeApi.js'
export { type DocumentsApi, type ReadOnlyDocumentsApi } from './adapters/documents.js'
export { type ActionHandle } from './adapters/actionHandle.js'
export { type AccountView, type AccountKind, type AutomationView, type Holding, accountViewOf, automationViewOf } from './core/views.js'
export {
  startPairingRequest,
  fetchPairingRequestByCode,
  type StartPairingRequestOptions,
  type PairingRequestSession,
  type PairingRequestLookup,
} from './pairing/pairingRequest.js'
export {
  buildJoinRequestJson,
  mintPairingGrant,
  revokePairingGrant,
  NothingToShareError,
  type MintedPairingGrant,
} from './pairing/mirrorGrant.js'
export {
  parseMirrorGrantBundle,
  readMirrorCollections,
  attemptDirectMirrorWrite,
  type MirrorGrantBundle,
  type ReadMirrorCollectionsOptions,
  type AttemptDirectMirrorWriteOptions,
} from './pairing/mirrorReader.js'
export {
  publishPairingGrant,
  clearPairingGrant,
  fetchPairingGrant,
  awaitPairingGrant,
  type UnsealedPairingGrant,
} from './pairing/pairingGrantExchange.js'
export {
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
} from './core/errors.js'
