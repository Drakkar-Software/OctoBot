import type { Strategy as ProtocolStrategy } from '@drakkar.software/octobot-protocol'
import {
  buildStrategy,
  type BuildStrategyOptions,
  type StrategyInput,
  type MmInput,
  type GridInput,
  type DcaInput,
  type IndexInput,
  type CopyInput,
  type SignalInput,
  protocolStrategyToInput,
  bumpStrategyPatchVersion,
  type StrategyInputPatch,
} from '../protocol/strategy/index.js'

/** Pure, synchronous(-ish — everything here is actually sync, `Promise`-free),
 *  zero-I/O strategy builders. Needs no connection: build a strategy, then
 *  pass it to `client.automations.create()` or `client.strategies.create()`. */
export interface StrategyBuilders {
  dca(input: DcaInput, opts?: BuildStrategyOptions): ProtocolStrategy
  grid(input: GridInput, opts?: BuildStrategyOptions): ProtocolStrategy
  index(input: IndexInput, opts?: BuildStrategyOptions): ProtocolStrategy
  marketMaking(input: MmInput, opts?: BuildStrategyOptions): ProtocolStrategy
  copy(input: CopyInput, opts?: BuildStrategyOptions): ProtocolStrategy
  signal(input: SignalInput, opts?: BuildStrategyOptions): ProtocolStrategy
  genericProcess(opts?: BuildStrategyOptions): ProtocolStrategy
  /** The discriminated-union entry point (`{ kind: 'dca', dca: {...} }`),
   *  for callers that already have a `StrategyInput` rather than picking a
   *  kind-specific method. */
  build(input: StrategyInput, opts?: BuildStrategyOptions): ProtocolStrategy
  /** Recover an editable input from a strategy the node returned — the
   *  inverse of every builder above. Feed the result's fields into a new
   *  `strategy.dca(...)`/etc call (with `bumpVersion` applied) to edit it. */
  toInput(existing: ProtocolStrategy): StrategyInputPatch
  /** Bump a `MAJOR.MINOR.PATCH` version string's patch component by one. */
  bumpVersion(version: string): string
}

/** Needs no `ClientSession` — unlike every other `create*Api` in
 *  `client/adapters/`, these builders do no I/O and touch no connection,
 *  so there is nothing to construct them from. Kept as a factory anyway, for
 *  the same reason those are: `strategy` below is just `createStrategyBuilders()`
 *  called once, so the object literal isn't duplicated between this module's
 *  own export and a hypothetical future caller that wants its own instance. */
export function createStrategyBuilders(): StrategyBuilders {
  return {
    dca: (input, opts) => buildStrategy({ kind: 'dca', dca: input }, opts),
    grid: (input, opts) => buildStrategy({ kind: 'grid', grid: input }, opts),
    index: (input, opts) => buildStrategy({ kind: 'basket', basket: input }, opts),
    marketMaking: (input, opts) => buildStrategy({ kind: 'mm', mm: input }, opts),
    copy: (input, opts) => buildStrategy({ kind: 'copy', copy: input }, opts),
    signal: (input, opts) => buildStrategy({ kind: 'signal', signal: input }, opts),
    genericProcess: (opts) => buildStrategy({ kind: 'custom' }, opts),
    build: (input, opts) => buildStrategy(input, opts),
    toInput: (existing) => protocolStrategyToInput(existing),
    bumpVersion: (version) => bumpStrategyPatchVersion(version),
  }
}

/** The public entry point every caller uses — `strategy.dca(...)`, etc. A
 *  single shared instance, since these builders carry no state and creating
 *  a fresh one per call would be pointless. */
export const strategy: StrategyBuilders = createStrategyBuilders()
