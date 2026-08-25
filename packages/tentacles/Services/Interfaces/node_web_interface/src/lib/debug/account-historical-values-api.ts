import { OpenAPI } from "@/client/core/OpenAPI"
import { request } from "@/client/core/request"

import type { PortfolioHistoricalValuesState } from "@/lib/debug/portfolio-historical-values-types"

/**
 * Interim API helper until OpenAPI regen adds AccountsService.getAccountHistoricalValues.
 */
export function fetchAccountHistoricalValues(
  accountId: string,
  walletAddress?: string,
) {
  return request<PortfolioHistoricalValuesState>(OpenAPI, {
    method: "GET",
    url: "/api/v1/accounts/{account_id}/historical-values",
    path: {
      account_id: accountId,
    },
    query: {
      wallet_address: walletAddress,
    },
    errors: {
      422: "Validation Error",
    },
  })
}
