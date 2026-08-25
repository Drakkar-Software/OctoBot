import { OpenAPI } from "@/client/core/OpenAPI"
import { request } from "@/client/core/request"

import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

/**
 * Interim API helper until OpenAPI regen adds aggregated historical values.
 */
export function fetchAggregatedAccountHistoricalValues(
  isSimulated: boolean,
  walletAddress?: string,
) {
  return request<PortfolioHistoricalValuesState>(OpenAPI, {
    method: "GET",
    url: "/api/v1/accounts/aggregated/historical-values",
    query: {
      is_simulated: isSimulated,
      wallet_address: walletAddress,
    },
    errors: {
      422: "Validation Error",
    },
  })
}
