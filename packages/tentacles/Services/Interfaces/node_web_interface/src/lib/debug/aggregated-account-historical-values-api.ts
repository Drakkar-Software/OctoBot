import { AccountsService } from "@/client"
import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

export async function fetchAggregatedAccountHistoricalValues(
  isSimulated: boolean,
  walletAddress?: string,
): Promise<PortfolioHistoricalValuesState> {
  const response =
    await AccountsService.accountsGetAggregatedAccountHistoricalValues({
      query: {
        is_simulated: isSimulated,
        wallet_address: walletAddress ?? null,
      },
      throwOnError: true,
    })
  return response.data as PortfolioHistoricalValuesState
}
