import { describe, expect, it } from "vitest"

import type { Account, ExchangeConfig } from "@/client"
import {
  accountFilterHeadClass,
  accountFilterValues,
  filterAccounts,
  sortAccounts,
} from "@/lib/debug/table-accounts"

const exchangeConfigs: ExchangeConfig[] = [
  {
    id: "cfg-1",
    name: "Binance",
    exchange: "binance",
    sandboxed: false,
  },
]

describe("accountFilterHeadClass", () => {
  it("adds compact column class for orders and trades", () => {
    expect(accountFilterHeadClass("orders")).toContain("w-0 px-2")
    expect(accountFilterHeadClass("name")).not.toContain("w-0 px-2")
  })
})

describe("accountFilterValues", () => {
  it("builds searchable account values", () => {
    const account: Account = {
      id: "acc-1",
      name: "Main",
      is_simulated: true,
      created_at: "2024-01-01T00:00:00.000Z",
      specifics: {
        account_type: "exchange",
        remote_account_id: "remote",
        exchange_config_ids: ["cfg-1"],
      },
    } as Account
    const values = accountFilterValues(account, exchangeConfigs, [])
    expect(values.exchange).toBe("binance")
    expect(values.simulated).toBe("yes")
  })
})

describe("filterAccounts", () => {
  it("filters by account name", () => {
    const rows: Account[] = [
      {
        id: "acc-1",
        name: "Alpha",
        is_simulated: false,
        created_at: "2024-01-01T00:00:00.000Z",
      },
      {
        id: "acc-2",
        name: "Beta",
        is_simulated: false,
        created_at: "2024-01-01T00:00:00.000Z",
      },
    ]
    expect(
      filterAccounts(rows, { name: "beta" }, exchangeConfigs, []),
    ).toHaveLength(1)
  })
})

describe("sortAccounts", () => {
  it("sorts by name ascending", () => {
    const rows: Account[] = [
      {
        id: "acc-2",
        name: "Beta",
        is_simulated: false,
        created_at: "2024-01-01T00:00:00.000Z",
      },
      {
        id: "acc-1",
        name: "Alpha",
        is_simulated: false,
        created_at: "2024-01-01T00:00:00.000Z",
      },
    ]
    const sorted = sortAccounts(
      rows,
      { key: "name", dir: "asc" },
      exchangeConfigs,
      [],
    )
    expect(sorted.map((row) => row.id)).toEqual(["acc-1", "acc-2"])
  })
})
