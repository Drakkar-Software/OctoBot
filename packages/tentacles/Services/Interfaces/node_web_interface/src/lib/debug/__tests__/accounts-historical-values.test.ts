import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/client", () => ({
  AccountsService: {
    accountsGetAccountHistoricalValues: vi.fn(),
    accountsGetAggregatedAccountHistoricalValues: vi.fn(),
  },
}))

import { AccountsService } from "@/client"
import { fetchAccountHistoricalValues } from "@/lib/debug/account-historical-values-api"
import { fetchAggregatedAccountHistoricalValues } from "@/lib/debug/aggregated-account-historical-values-api"

const mockedAccountHistorical = vi.mocked(
  AccountsService.accountsGetAccountHistoricalValues,
)
const mockedAggregatedHistorical = vi.mocked(
  AccountsService.accountsGetAggregatedAccountHistoricalValues,
)

describe("fetchAccountHistoricalValues", () => {
  beforeEach(() => {
    mockedAccountHistorical.mockReset()
    mockedAccountHistorical.mockResolvedValue({
      data: { series: [] },
    } as never)
  })

  it("passes account_id path and wallet_address query", async () => {
    await fetchAccountHistoricalValues("acct-1", "0xabc")
    expect(mockedAccountHistorical).toHaveBeenCalledWith({
      path: { account_id: "acct-1" },
      query: { wallet_address: "0xabc" },
      throwOnError: true,
    })
  })

  it("uses null wallet_address when omitted", async () => {
    await fetchAccountHistoricalValues("acct-2")
    expect(mockedAccountHistorical).toHaveBeenCalledWith({
      path: { account_id: "acct-2" },
      query: { wallet_address: null },
      throwOnError: true,
    })
  })
})

describe("fetchAggregatedAccountHistoricalValues", () => {
  beforeEach(() => {
    mockedAggregatedHistorical.mockReset()
    mockedAggregatedHistorical.mockResolvedValue({
      data: { series: [] },
    } as never)
  })

  it("passes is_simulated and wallet_address query", async () => {
    await fetchAggregatedAccountHistoricalValues(true, "0xdef")
    expect(mockedAggregatedHistorical).toHaveBeenCalledWith({
      query: { is_simulated: true, wallet_address: "0xdef" },
      throwOnError: true,
    })
  })
})
