import { type DebugState, DebugService } from "@/client"
import { fetchAccountHistoricalValues } from "@/lib/debug/account-historical-values-api"
import { fetchAggregatedAccountHistoricalValues } from "@/lib/debug/aggregated-account-historical-values-api"

export function getDebugQueryOptions(walletAddress?: string | null) {
  const resolved =
    walletAddress && walletAddress.length > 0 ? walletAddress : undefined
  return {
    queryKey: ["debug", resolved ?? "current"] as const,
    queryFn: async () =>
      (await DebugService.debugGetDebug(
          resolved ? { query: { wallet_address: resolved } } : {},
        )).data,
  }
}

export function getAccountHistoricalValuesQueryOptions(
  accountId: string | undefined,
  walletAddress?: string | null,
  enabled = false,
) {
  const resolvedWallet =
    walletAddress && walletAddress.length > 0 ? walletAddress : undefined
  return {
    queryKey: [
      "account-historical-values",
      accountId ?? "none",
      resolvedWallet ?? "current",
    ] as const,
    queryFn: async () => {
      if (!accountId) {
        throw new Error("Account id is required")
      }
      return fetchAccountHistoricalValues(accountId, resolvedWallet)
    },
    enabled: enabled && Boolean(accountId),
  }
}

export function getAggregatedAccountHistoricalValuesQueryOptions(
  isSimulated: boolean,
  walletAddress?: string | null,
  enabled = false,
) {
  const resolvedWallet =
    walletAddress && walletAddress.length > 0 ? walletAddress : undefined
  return {
    queryKey: [
      "aggregated-account-historical-values",
      isSimulated ? "simulated" : "real",
      resolvedWallet ?? "current",
    ] as const,
    queryFn: async () =>
      fetchAggregatedAccountHistoricalValues(isSimulated, resolvedWallet),
    enabled,
  }
}
