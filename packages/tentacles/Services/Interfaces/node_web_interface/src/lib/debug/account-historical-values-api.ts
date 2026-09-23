import { AccountsService } from "@/client"
import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

export async function fetchAccountHistoricalValues(
  accountId: string,
  walletAddress?: string,
): Promise<PortfolioHistoricalValuesState> {
  const response = await AccountsService.accountsGetAccountHistoricalValues({
    path: { account_id: accountId },
    query: { wallet_address: walletAddress ?? null },
    throwOnError: true,
  })
  return response.data as PortfolioHistoricalValuesState
}
