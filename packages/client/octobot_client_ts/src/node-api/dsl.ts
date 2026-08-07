import type { DslKeywordsState } from '@drakkar.software/octobot-protocol'
import type { NodeEndpoint } from '../transport/urls.js'
import { nodeAuthRequest, type NodeCredentials } from '../transport/rest.js'

/** `GET /api/v1/dsl/keywords` — the DSL keywords this node can run, with the
 *  state version they were authored against. Authenticated. */
export async function fetchNodeDslKeywords(
  node: NodeEndpoint,
  credentials: NodeCredentials,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<DslKeywordsState> {
  return nodeAuthRequest<DslKeywordsState>(node, credentials, '/dsl/keywords', options)
}
