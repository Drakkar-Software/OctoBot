import type { CreateClientConfig } from "../client/client.gen"

export function resolveApiBaseUrl(): string {
  return (
    import.meta.env.NODE_API_URL ||
    (import.meta.env.DEV ? "http://localhost:8000" : "")
  )
}

export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseURL: resolveApiBaseUrl(),
  throwOnError: true,
})
