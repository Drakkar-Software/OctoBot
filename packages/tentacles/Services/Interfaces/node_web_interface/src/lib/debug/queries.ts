import { DebugService } from "@/client"
import { fetchAccountHistoricalValues } from "@/lib/debug/account-historical-values-api"
import { fetchAggregatedAccountHistoricalValues } from "@/lib/debug/aggregated-account-historical-values-api"

export function getDebugQueryOptions(walletAddress?: string | null) {
  const resolved =
    walletAddress && walletAddress.length > 0 ? walletAddress : undefined
  return {
    queryKey: ["debug", resolved ?? "current"] as const,
    queryFn: () =>
      DebugService.getDebug(resolved ? { walletAddress: resolved } : {}),
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
    queryFn: () => {
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
    queryFn: () =>
      fetchAggregatedAccountHistoricalValues(isSimulated, resolvedWallet),
    enabled,
  }
}
