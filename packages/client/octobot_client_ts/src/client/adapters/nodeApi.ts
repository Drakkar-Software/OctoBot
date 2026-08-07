import type { DslKeywordsState, MarketMakingConfiguration } from '@drakkar.software/octobot-protocol'
import type { ClientSession } from '../core/session.js'
import type { CallOptions } from '../core/options.js'
import { detectNode } from '../../transport/probe.js'
import {
  fetchNodeTradedPairs,
  fetchPredictedOrderBook,
  fetchRequiredFunds,
  fetchNodeDslKeywords,
  fetchNodeWalletExport,
  createGenericProcessBot,
  type ExchangeConfigParams,
  type PredictedOrderBookResponse,
  type RequiredFundsResponse,
  type NodeWalletExport,
  type TradedPairsByExchange,
  type LegacyTradedPairsByExchange,
} from '../../node-api/index.js'
import { OctoBotConfigError, rethrowAsOctoBotError } from '../core/errors.js'

export interface NodeApi {
  status(opts?: CallOptions): Promise<{ reachable: boolean; configured: boolean }>
  tradedPairs(
    exchange: ExchangeConfigParams,
    opts?: CallOptions & { withVolume?: boolean },
  ): Promise<TradedPairsByExchange | LegacyTradedPairsByExchange>
  predictedOrderBook(
    exchange: ExchangeConfigParams,
    config: MarketMakingConfiguration,
    opts?: CallOptions,
  ): Promise<PredictedOrderBookResponse>
  requiredFunds(
    exchange: ExchangeConfigParams,
    config: MarketMakingConfiguration,
    opts?: CallOptions,
  ): Promise<RequiredFundsResponse>
  /** Requires `ConnectOptions.basicAuth` — throws `OctoBotConfigError` otherwise. */
  dslKeywords(opts?: CallOptions): Promise<DslKeywordsState>
  /** Requires `ConnectOptions.basicAuth`. */
  exportWallet(opts?: CallOptions): Promise<NodeWalletExport>
  /** Requires `ConnectOptions.basicAuth`. */
  createGenericProcessBot(name: string, opts?: CallOptions): Promise<{ automation_id: string }>
}

export function createNodeApi(session: ClientSession): NodeApi {
  function requireBasicAuth() {
    if (!session.basicAuth) {
      throw new OctoBotConfigError(
        'this call requires ConnectOptions.basicAuth — only a node paired by an older QR carries HTTP Basic credentials',
      )
    }
    return session.basicAuth
  }

  return {
    async status(opts) {
      try {
        const result = await detectNode(session.node.host, session.node.port, session.node.secure, {
          signal: opts?.signal,
          timeoutMs: opts?.timeoutMs,
          fetch: session.fetch,
        })
        if (result.status === 'reachable') return { reachable: true, configured: result.configured }
        return { reachable: false, configured: false }
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async tradedPairs(exchange, opts) {
      try {
        return await fetchNodeTradedPairs(session.node, exchange, {
          withVolume: opts?.withVolume,
          signal: opts?.signal,
          fetch: session.fetch,
        })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async predictedOrderBook(exchange, config, opts) {
      try {
        return await fetchPredictedOrderBook(session.node, exchange, config, { signal: opts?.signal, fetch: session.fetch })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async requiredFunds(exchange, config, opts) {
      try {
        return await fetchRequiredFunds(session.node, exchange, config, { signal: opts?.signal, fetch: session.fetch })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async dslKeywords(opts) {
      try {
        return await fetchNodeDslKeywords(session.node, requireBasicAuth(), { signal: opts?.signal, fetch: session.fetch })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async exportWallet(opts) {
      try {
        return await fetchNodeWalletExport(session.node, requireBasicAuth(), { signal: opts?.signal, fetch: session.fetch })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
    async createGenericProcessBot(name, opts) {
      try {
        return await createGenericProcessBot(session.node, requireBasicAuth(), name, { signal: opts?.signal, fetch: session.fetch })
      } catch (err) {
        rethrowAsOctoBotError(err)
      }
    },
  }
}
