import type { MarketMakingConfiguration } from '@drakkar.software/octobot-protocol'
import type { NodeEndpoint } from '../transport/urls.js'
import type { ExchangeConfigParams } from './exchanges.js'
import { marketMakingRequestBody, postMarketMakingRequest, type PredictedOrderBookResponse } from './marketMaking.js'

export type { PredictedOrderBookResponse }

/** `POST /api/v1/tentacles/market-making/` with `type: 'predicted_order_book'`. */
export async function fetchPredictedOrderBook(
  node: NodeEndpoint,
  exchangeConfig: ExchangeConfigParams,
  marketMakingConfig: MarketMakingConfiguration,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<PredictedOrderBookResponse> {
  const body = marketMakingRequestBody('predicted_order_book', exchangeConfig, marketMakingConfig)
  return postMarketMakingRequest<PredictedOrderBookResponse>(node, body, options)
}
