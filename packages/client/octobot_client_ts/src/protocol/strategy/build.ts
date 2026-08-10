import type { Strategy } from '@drakkar.software/octobot-protocol'
import type { StrategyKind } from './kinds.js'
import {
  buildMarketMakingConfig,
  buildGridConfig,
  buildDCAConfig,
  buildIndexConfig,
  buildCopyConfig,
  buildSignalConfig,
  buildGenericProcessConfig,
  type MmInput,
  type GridInput,
  type DcaInput,
  type IndexInput,
  type CopyInput,
  type SignalInput,
} from './builders.js'

// Construction: local input -> a full protocol Strategy. Kept separate from
// ./patch.ts (the inverse, protocol -> input, plus incremental edits) — build
// and patch are different concerns, and folding them into one file (as the
// old strategyPatch.ts did) is what buried this discriminated union next to
// an unrelated 250-line rehydration reader.

export type StrategyInput =
  | { kind: 'mm';     mm:     MmInput }
  | { kind: 'grid';   grid:   GridInput }
  | { kind: 'dca';    dca:    DcaInput }
  | { kind: 'basket'; basket: IndexInput }
  | { kind: 'copy';   copy:   CopyInput }
  | { kind: 'signal'; signal: SignalInput }
  | { kind: 'custom' }
  | { kind: 'ai-agents' }

function buildConfiguration(input: StrategyInput): Strategy['configuration'] {
  switch (input.kind) {
    case 'mm':     return buildMarketMakingConfig(input.mm)
    case 'grid':   return buildGridConfig(input.grid)
    case 'dca':    return buildDCAConfig(input.dca)
    case 'basket': return buildIndexConfig(input.basket)
    case 'copy':   return buildCopyConfig(input.copy)
    case 'signal': return buildSignalConfig(input.signal)
    default:       return buildGenericProcessConfig()
  }
}

export type BuildStrategyOptions = {
  id?: string
  version?: string
  name?: string
  description?: string
  /** Overrides the quote currency derived from the input pairs. */
  referenceMarket?: string
}

const DEFAULT_REFERENCE_MARKET = 'USDT'

function quoteOf(pair: string | undefined): string | null {
  // Strip the perp settle suffix: 'BTC/USDT:USDT' quotes in USDT, and
  // 'USDT:USDT' is not a currency the node can value a portfolio in.
  const quote = pair?.split('/')[1]?.split(':')[0]
  return quote?.trim() ? quote.trim() : null
}

/** The node values the automation's portfolio in Strategy.reference_market
 *  (required in protocol 0.4.0) — derive it from the traded pairs' quote. */
export function referenceMarketOf(input: StrategyInput): string {
  switch (input.kind) {
    case 'mm':     return quoteOf(input.mm.pairs[0]) ?? DEFAULT_REFERENCE_MARKET
    case 'grid':   return quoteOf(input.grid.pairs[0]) ?? DEFAULT_REFERENCE_MARKET
    case 'dca':    return quoteOf(input.dca.pairs[0]) ?? DEFAULT_REFERENCE_MARKET
    case 'signal': return quoteOf(input.signal.pair) ?? DEFAULT_REFERENCE_MARKET
    // Basket coins are bare base symbols; copy has no pairs of its own.
    default:       return DEFAULT_REFERENCE_MARKET
  }
}

/** Build a complete protocol `Strategy` from a `StrategyInput`. This is the
 *  function `strategy.build()` in the public facade wraps; `strategy.dca()` /
 *  `.grid()` / etc are one-line convenience wrappers around this with the
 *  `kind` pre-filled. */
export function buildStrategy(input: StrategyInput, opts: BuildStrategyOptions = {}): Strategy {
  const id = opts.id ?? `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
  const now = new Date().toISOString()
  return {
    id,
    version:     opts.version ?? '1.0.0',
    name:        opts.name,
    description: opts.description,
    created_at:  now,
    updated_at:  now,
    reference_market: opts.referenceMarket ?? referenceMarketOf(input),
    configuration: buildConfiguration(input),
  }
}

export type { StrategyKind }
