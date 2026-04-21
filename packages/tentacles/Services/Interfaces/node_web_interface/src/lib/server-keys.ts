import { TasksService } from "@/client"

export type ServerPublicKeys = {
  rsa_public: string
  ecdsa_public: string
}

let cache: ServerPublicKeys | null = null

export async function fetchServerPublicKeys(): Promise<ServerPublicKeys> {
  if (cache) return cache
  const raw = await TasksService.getServerPublicKeys()
  const data = raw as { server_rsa_public_pem: string; server_ecdsa_public_pem: string }
  if (!data.server_rsa_public_pem || !data.server_ecdsa_public_pem) {
    throw new Error("Server public keys not available — encryption may not be configured")
  }
  cache = { rsa_public: data.server_rsa_public_pem, ecdsa_public: data.server_ecdsa_public_pem }
  return cache
}
