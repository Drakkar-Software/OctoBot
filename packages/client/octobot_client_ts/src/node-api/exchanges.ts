import type { TradedPairVolume } from '@drakkar.software/octobot-protocol'
import type { NodeEndpoint } from '../transport/urls.js'
import { nodeBaseUrl } from '../transport/urls.js'
import { nodeRequest } from '../transport/rest.js'

export type { TradedPairVolume }

/** Mirrors the FastAPI `ExchangeConfig` pydantic model on the node side
 *  (packages/tentacles/.../node_api_interface/core/exchanges.py). `id` and
 *  `name` are required by the node's query schema but not read by the
 *  traded-pairs lookup itself (only `exchange`/`sandboxed`/`url` are) — any
 *  stable non-empty string works for them. */
export type ExchangeConfigParams = {
  id: string
  name: string
  /** Exchange identifier used to build the node's exchange client, e.g. "binance". Required. */
  exchange: string
  sandboxed?: boolean
  url?: string
}

/** One exchange's `traded-pairs` entry: symbol → volume. The volume object is
 *  empty unless the request asked for `with_volume`. */
export type TradedPairsForExchange = Record<string, TradedPairVolume>

/** Per-exchange `traded-pairs` payload: keyed by exchange internal name. */
export type TradedPairsByExchange = Record<string, TradedPairsForExchange>

/** Shape returned by nodes older than the `TradedPairsByExchange` protocol
 *  change (a bare symbol list per exchange). Users run their own nodes, so
 *  both shapes have to be readable — see `extractPairs` in ./pairs.ts. */
export type LegacyTradedPairsByExchange = Record<string, string[]>

/** Per-exchange `traded-pairs-and-timeframes` payload. */
export type TradedPairsAndTimeframesByExchange = Record<
  string,
  { pairs: string[]; timeframes: string[] }
>

function buildExchangeConfigQuery(params: ExchangeConfigParams): string {
  const sp = new URLSearchParams()
  sp.set('id', params.id)
  sp.set('name', params.name)
  sp.set('exchange', params.exchange)
  if (params.sandboxed !== undefined) sp.set('sandboxed', String(params.sandboxed))
  if (params.url !== undefined) sp.set('url', params.url)
  return sp.toString()
}

/** `GET /api/v1/exchanges/traded-pairs?name=<id>&...`
 *  Response: `{ [exchangeInternalName]: { [symbol]: { baseVolume?, quoteVolume? } } }`
 *  (older nodes: `{ [exchangeInternalName]: string[] }`).
 *  `withVolume` asks the node to fill the volumes from the exchange tickers —
 *  it answers 501 when that exchange doesn't support the lookup. */
export async function fetchNodeTradedPairs(
  node: NodeEndpoint,
  exchange: ExchangeConfigParams,
  options: { withVolume?: boolean; signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<TradedPairsByExchange | LegacyTradedPairsByExchange> {
  const query = buildExchangeConfigQuery(exchange)
  const volumeQuery = options.withVolume ? '&with_volume=true' : ''
  return nodeRequest<TradedPairsByExchange | LegacyTradedPairsByExchange>(
    node,
    `/exchanges/traded-pairs?${query}${volumeQuery}`,
    { signal: options.signal, fetch: options.fetch },
  )
}

/** `GET /api/v1/exchanges/traded-pairs-and-timeframes?name=<id>&...`
 *  Response: `{ [exchangeInternalName]: { pairs: string[]; timeframes: string[] } }`. */
export async function fetchNodeTradedPairsAndTimeframes(
  node: NodeEndpoint,
  exchange: ExchangeConfigParams,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<TradedPairsAndTimeframesByExchange> {
  return nodeRequest<TradedPairsAndTimeframesByExchange>(
    node,
    `/exchanges/traded-pairs-and-timeframes?${buildExchangeConfigQuery(exchange)}`,
    options,
  )
}

// nodeBaseUrl re-export kept for callers that build their own custom requests
// against this same node.
export { nodeBaseUrl }
