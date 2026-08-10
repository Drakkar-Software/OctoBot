import type { MarketMakingConfiguration } from '@drakkar.software/octobot-protocol'
import type { NodeEndpoint } from '../transport/urls.js'
import type { ExchangeConfigParams } from './exchanges.js'
import { marketMakingRequestBody, postMarketMakingRequest, type RequiredFundsResponse } from './marketMaking.js'

export type { RequiredFundsResponse }

/** `POST /api/v1/tentacles/market-making/` with `type: 'market_making_volume'`. */
export async function fetchRequiredFunds(
  node: NodeEndpoint,
  exchangeConfig: ExchangeConfigParams,
  marketMakingConfig: MarketMakingConfiguration,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<RequiredFundsResponse> {
  const body = marketMakingRequestBody('market_making_volume', exchangeConfig, marketMakingConfig)
  return postMarketMakingRequest<RequiredFundsResponse>(node, body, options)
}
