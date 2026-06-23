import { describe, expect, it } from "vitest"

import type { Account, ExchangeConfig } from "@/client"
import {
  exchangeConfigFilterValues,
  filterExchangeConfigs,
  sortExchangeConfigs,
} from "@/lib/debug/table-exchange-configs"

const accounts: Account[] = [
  {
    id: "acc-1",
    name: "Main",
    is_simulated: false,
    created_at: "2024-01-01T00:00:00.000Z",
    specifics: {
      account_type: "exchange",
      remote_account_id: "remote",
      exchange_config_ids: ["cfg-1"],
    },
  } as Account,
]

describe("exchangeConfigFilterValues", () => {
  it("includes linked account names", () => {
    const config: ExchangeConfig = {
      id: "cfg-1",
      name: "Binance main",
      exchange: "binance",
      sandboxed: false,
    }
    expect(exchangeConfigFilterValues(config, accounts).accounts).toBe("Main")
  })
})

describe("filterExchangeConfigs", () => {
  it("filters by exchange name", () => {
    const rows: ExchangeConfig[] = [
      { id: "cfg-1", name: "A", exchange: "binance", sandboxed: false },
      { id: "cfg-2", name: "B", exchange: "kraken", sandboxed: false },
    ]
    expect(
      filterExchangeConfigs(rows, { exchange: "kraken" }, accounts),
    ).toHaveLength(1)
  })
})

describe("sortExchangeConfigs", () => {
  it("sorts by exchange ascending", () => {
    const rows: ExchangeConfig[] = [
      { id: "cfg-2", name: "B", exchange: "kraken", sandboxed: false },
      { id: "cfg-1", name: "A", exchange: "binance", sandboxed: false },
    ]
    const sorted = sortExchangeConfigs(
      rows,
      { key: "exchange", dir: "asc" },
      accounts,
    )
    expect(sorted.map((row) => row.exchange)).toEqual(["binance", "kraken"])
  })
})
