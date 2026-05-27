import { DebugService } from "@/client"

export function getDebugQueryOptions(walletAddress?: string | null) {
  const resolved =
    walletAddress && walletAddress.length > 0 ? walletAddress : undefined
  return {
    queryKey: ["debug", resolved ?? "current"] as const,
    queryFn: () =>
      DebugService.getDebug(
        resolved ? { walletAddress: resolved } : {},
      ),
  }
}
