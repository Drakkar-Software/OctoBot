import type { NodeEndpoint } from '../transport/urls.js'
import { NodeHttpError } from '../transport/rest.js'
import {
  fetchNodeTradedPairs,
  type LegacyTradedPairsByExchange,
  type TradedPairsByExchange,
} from './exchanges.js'

/** A trading pair surfaced to an automation's pair-selection step. */
export type AutomationPair = {
  symbol: string
  base: string
  quote: string
  type: string
  active: boolean
  /** 24h volumes as reported by the exchange for this exact pair, when the
   *  node answered a `with_volume` request. Undefined otherwise (older node,
   *  volume lookup unsupported, or the ticker had no entry). */
  baseVolume?: number | null
  quoteVolume?: number | null
}

function numberOrUndefined(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function symbolToPair(symbol: string): AutomationPair {
  const isSwap = symbol.includes(':')
  const [pairPart] = symbol.split(':', 1)
  const slashIdx = pairPart.indexOf('/')
  const base = slashIdx >= 0 ? pairPart.slice(0, slashIdx) : pairPart
  const quote = slashIdx >= 0 ? pairPart.slice(slashIdx + 1) : ''
  return { symbol, base, quote, type: isSwap ? 'swap' : 'spot', active: true }
}

/** Node's `traded-pairs` payload is untyped JSON — validate its actual shape
 *  here rather than trusting the declared type at the call site, so a
 *  mismatched/unexpected response throws a clear error instead of a bare "X
 *  is not a function" once a non-string symbol reaches `symbolToPair`.
 *
 *  Two per-exchange shapes are accepted: the current symbol → volume map, and
 *  the bare symbol array older nodes still answer. Anything else is a payload
 *  we don't understand — throwing beats silently returning an empty list.
 *
 *  A symbol listed by more than one exchange yields one pair (the list is
 *  keyed by symbol downstream), keeping the first volumes reported for it. */
export function extractPairs(
  byExchange: TradedPairsByExchange | LegacyTradedPairsByExchange,
): AutomationPair[] {
  if (byExchange == null || typeof byExchange !== 'object' || Array.isArray(byExchange)) {
    throw new Error('Unexpected traded-pairs payload from node')
  }
  const bySymbol = new Map<string, AutomationPair>()
  const add = (symbol: string, volume?: unknown): void => {
    const known = bySymbol.get(symbol)
    const pair = known ?? symbolToPair(symbol)
    if (volume != null && typeof volume === 'object') {
      const raw = volume as Record<string, unknown>
      pair.baseVolume = pair.baseVolume ?? numberOrUndefined(raw.baseVolume)
      pair.quoteVolume = pair.quoteVolume ?? numberOrUndefined(raw.quoteVolume)
    }
    if (!known) bySymbol.set(symbol, pair)
  }
  for (const value of Object.values(byExchange)) {
    if (Array.isArray(value)) {
      for (const entry of value) {
        if (typeof entry === 'string') add(entry)
      }
      continue
    }
    if (value == null || typeof value !== 'object') continue
    for (const [symbol, volume] of Object.entries(value)) add(symbol, volume)
  }
  return [...bySymbol.values()]
}

/** Fetch and normalize the traded pairs for one exchange on one node. Falls
 *  back to the volume-less request when the node can't fetch tickers for
 *  this exchange (501) rather than surfacing no pairs at all. */
export async function fetchPairsFromNode(
  node: NodeEndpoint,
  providerId: string,
  signal?: AbortSignal,
): Promise<AutomationPair[]> {
  const exchange = { id: providerId, name: providerId, exchange: providerId }
  let byExchange
  try {
    byExchange = await fetchNodeTradedPairs(node, exchange, { withVolume: true, signal })
  } catch (err) {
    if (!(err instanceof NodeHttpError) || err.status !== 501) throw err
    byExchange = await fetchNodeTradedPairs(node, exchange, { signal })
  }
  return extractPairs(byExchange).sort((a, b) => a.symbol.localeCompare(b.symbol))
}
