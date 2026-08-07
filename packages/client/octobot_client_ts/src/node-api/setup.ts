import type { NodeEndpoint } from '../transport/urls.js'
import { nodeAuthRequest, type NodeCredentials } from '../transport/rest.js'

/** A node's own copy of the wallet it runs on. `seed` is only set when that
 *  wallet was created from a mnemonic; a node set up from a raw key has the
 *  private key alone. Declared here rather than imported from
 *  `@drakkar.software/octobot-protocol` because the node's setup routes are
 *  not part of its generated model set. */
export type NodeWalletExport = {
  address: string
  private_key: string
  seed?: string | null
}

/** `GET /api/v1/setup/wallet/export` — the wallet behind the credentials being
 *  presented. Only a node paired by an older QR needs this: that code carried a
 *  password rather than the wallet, so the wallet had to be fetched. A current
 *  pairing code is read offline and never reaches here.
 *
 *  `NodeHttpError` statuses worth telling apart: 401 (wrong password, or the
 *  node has no wallet for that address), 403 (asking for someone else's wallet
 *  without being the admin), 503 (node not configured yet). */
export async function fetchNodeWalletExport(
  node: NodeEndpoint,
  credentials: NodeCredentials,
  options: { signal?: AbortSignal; fetch?: typeof fetch } = {},
): Promise<NodeWalletExport> {
  return nodeAuthRequest<NodeWalletExport>(node, credentials, '/setup/wallet/export', options)
}
