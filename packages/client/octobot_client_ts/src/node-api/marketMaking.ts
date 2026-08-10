import type { MarketMakingConfiguration } from '@drakkar.software/octobot-protocol'
import type { NodeEndpoint } from '../transport/urls.js'
import { nodeBaseUrl } from '../transport/urls.js'
import { NodeHttpError } from '../transport/rest.js'
import { MARKET_MAKING_TIMEOUT_MS } from '../transport/constants.js'
import type { ExchangeConfigParams } from './exchanges.js'

/** Per-symbol predicted order-book ladder level. */
export type PredictedOrderLevel = {
  price: number
  amount: number
  total: number
}

/** One pair's `predicted_order_book` result — `error` is set instead of the
 *  other fields when the node couldn't compute a preview for that pair
 *  (e.g. missing ticker, unsupported pair). */
export type PredictedOrderBookEntry = {
  price: number | null
  bids: PredictedOrderLevel[] | null
  asks: PredictedOrderLevel[] | null
  volume: Record<string, number> | null
  error: string | null
}

/** `{ [exchangeInternalName]: { [symbol]: PredictedOrderBookEntry } }`. */
export type PredictedOrderBookResponse = Record<string, Record<string, PredictedOrderBookEntry>>

/** One pair's `market_making_volume` result — the minimal base/quote amounts
 *  needed to run the configured order-book distribution at the current
 *  reference price. */
export type RequiredFundsEntry = {
  volume: Record<string, number> | null
  error: string | null
}

/** `{ [exchangeInternalName]: { [symbol]: RequiredFundsEntry } }`. */
export type RequiredFundsResponse = Record<string, Record<string, RequiredFundsEntry>>

/** POSTs to the node's single market-making dispatch route
 *  (`POST /api/v1/tentacles/market-making/`), which branches on `type`
 *  (`predicted_order_book`, `market_making_volume`, `update_liquidity_score`). */
export async function postMarketMakingRequest<T>(
  node: NodeEndpoint,
  body: unknown,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<T> {
  const fetchImpl = options.fetch ?? globalThis.fetch
  const url = `${nodeBaseUrl(node)}/tentacles/market-making/`
  const internalController = new AbortController()
  const timer = setTimeout(() => internalController.abort(), MARKET_MAKING_TIMEOUT_MS)
  const onCallerAbort = () => internalController.abort()
  if (options.signal) options.signal.addEventListener('abort', onCallerAbort)
  try {
    const res = await fetchImpl(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: internalController.signal,
    })
    if (!res.ok) throw new NodeHttpError(res.status)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
    if (options.signal) options.signal.removeEventListener('abort', onCallerAbort)
  }
}

export function marketMakingRequestBody(
  type: 'predicted_order_book' | 'market_making_volume',
  exchange: ExchangeConfigParams,
  config: MarketMakingConfiguration,
): unknown {
  return {
    type,
    auth: null,
    // Unlike the GET traded-pairs query (where an omitted `sandboxed` falls
    // through to the FastAPI route's own `= False` default), this route's
    // pydantic ExchangeConfig has no default for `sandboxed` — omitting it
    // is a 422/validation error the node surfaces as a bare 404.
    exchanges: [{ ...exchange, sandboxed: exchange.sandboxed ?? false }],
    config: { config },
  }
}
