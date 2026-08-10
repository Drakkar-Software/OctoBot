import type { NodeEndpoint } from '../transport/urls.js'
import { nodeAuthRequest, type NodeCredentials } from '../transport/rest.js'
import { CREATE_GENERIC_PROCESS_TIMEOUT_MS } from '../transport/constants.js'

export type CreateGenericProcessBotResponse = { automation_id: string }

/** `POST /api/v1/octobots/generic-process` — start a full OctoBot process bot
 *  on the node. Authenticated. Answers 201 with the new automation id; 400 on
 *  an empty/invalid name, 503 when the node's scheduler isn't up, 504 when the
 *  creation workflow times out (all surfaced as `NodeHttpError`). */
export async function createGenericProcessBot(
  node: NodeEndpoint,
  credentials: NodeCredentials,
  name: string,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<CreateGenericProcessBotResponse> {
  return nodeAuthRequest<CreateGenericProcessBotResponse>(node, credentials, '/octobots/generic-process', {
    method: 'POST',
    body: { name },
    signal: options.signal,
    fetch: options.fetch,
    timeoutMs: CREATE_GENERIC_PROCESS_TIMEOUT_MS,
  })
}
