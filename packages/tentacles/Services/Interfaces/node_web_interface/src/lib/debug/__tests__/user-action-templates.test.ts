import { describe, expect, it } from "vitest"

import type { Account, ExchangeConfig, Strategy } from "@/client"
import {
  buildAccountEditUserActionJson,
  buildAutomationCreateUserActionJsonForAccount,
  buildAutomationCreateUserActionJsonForStrategy,
  buildAutomationSignalUserActionJson,
  buildAutomationStopUserActionJson,
  buildExchangeConfigEditUserActionJson,
  buildStrategyEditUserActionJson,
  buildUserActionTemplate,
  buildUserActionTemplateJson,
  defaultSignalPayloadText,
  userActionTemplateKeyFromActionType,
} from "@/lib/debug/user-action-templates"

const CANONICAL_UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe("defaultSignalPayloadText", () => {
  it("returns sample payloads for payload signal types", () => {
    expect(defaultSignalPayloadText("actions")).toContain("dsl_script")
    expect(defaultSignalPayloadText("trading_signal")).toContain("strategy_id")
    expect(defaultSignalPayloadText("forced_trigger")).toBe("")
  })
})

describe("buildUserActionTemplate", () => {
  it("builds an automation stop template", () => {
    const action = buildUserActionTemplate("automation_stop")
    expect(action.id).toContain("automation_stop")
    expect(action.configuration).toMatchObject({
      action_type: "automation_stop",
      id: "<automation-id>",
    })
  })

  it("builds an automation create template with a random configuration id", () => {
    const action = buildUserActionTemplate("automation_create")
    expect(action.configuration).toMatchObject({
      action_type: "automation_create",
    })

    const automationConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const automationId = automationConfiguration.id
    expect(typeof automationId).toBe("string")
    const automationIdString = automationId as string
    expect(automationIdString).toMatch(CANONICAL_UUID_V4_PATTERN)
    expect(automationIdString).toBe(automationIdString.toLowerCase())
  })

  it("builds an automation edit template without configuration id", () => {
    const action = buildUserActionTemplate("automation_edit")
    expect(action.configuration).toMatchObject({
      action_type: "automation_edit",
      id: "<automation-id>",
    })

    const automationConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(automationConfiguration).not.toHaveProperty("id")
  })

  it("builds an account create template with default USDC assets", () => {
    const action = buildUserActionTemplate("account_create")
    expect(action.configuration).toMatchObject({
      action_type: "account_create",
    })

    const accountConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(accountConfiguration.assets).toEqual([
      {
        trading_type: "spot",
        assets: [{ symbol: "USDC", total: 1000, available: 1000 }],
      },
    ])
  })

  it("builds an account edit template without assets", () => {
    const action = buildUserActionTemplate("account_edit")
    expect(action.configuration).toMatchObject({
      action_type: "account_edit",
      id: "<account-id>",
    })

    const accountConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(accountConfiguration).not.toHaveProperty("assets")
  })

  it("builds a grid strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_grid")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("GridTradingMode")

    const config = tradingConfiguration.config as Record<string, unknown>
    const pairSettings = config.pair_settings as Array<Record<string, unknown>>
    expect(pairSettings[0].pair).toBe("BTC/USDT")
    expect(tradingConfiguration).not.toHaveProperty("symbols")
  })

  it("builds an index strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_index")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("IndexTradingMode")

    const config = tradingConfiguration.config as Record<string, unknown>
    expect(config.index_content).toEqual([{ name: "BTC", value: 1.0 }])
    expect(config.rebalance_trigger_min_percent).toBe(5.0)
  })

  it("builds a copy strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_copy")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDT")

    const copyConfiguration = strategy.configuration as Record<string, unknown>
    expect(copyConfiguration.configuration_type).toBe("copy")
    expect(copyConfiguration.strategy_id).toBe("<master-strategy-id>")
  })

  it("builds a DCA strategy create template with two evaluators", () => {
    const action = buildUserActionTemplate("strategy_create_dca")
    expect(action.id).toBe("ua-manual-strategy_create_dca")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")

    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("DCATradingMode")
    expect(tradingConfiguration).not.toHaveProperty("symbols")

    const dcaConfig = tradingConfiguration.config as Record<string, unknown>
    expect(dcaConfig.trigger_mode).toBe("Maximum evaluators signals based")
    expect(dcaConfig.use_init_entry_orders).toBe(false)
    expect(dcaConfig.use_stop_losses).toBe(false)
    expect(dcaConfig.stop_loss_price_percent).toBe(10)
    expect(dcaConfig.trading_pairs).toEqual([])

    const evaluators = tradingConfiguration.evaluators as Array<{
      name: string
      config: Record<string, unknown>
      symbols: string[]
    }>
    expect(evaluators).toHaveLength(2)
    expect(evaluators[0].name).toBe("RSIMomentumEvaluator")
    expect(evaluators[1].name).toBe("EMAMomentumEvaluator")
    expect(evaluators[0].symbols).toEqual(["BTC/USDC", "ETH/USDC"])

    const strategies = tradingConfiguration.strategies as Array<{
      name: string
      config: Record<string, unknown>
      time_frames: string[]
    }>
    expect(strategies).toHaveLength(1)
    expect(strategies[0].time_frames).toEqual(["1h"])
    expect(strategies[0].name).toBe("SimpleStrategyEvaluator")
  })

  it("builds a DCA always-long strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_dca_always_long")
    expect(action.id).toBe("ua-manual-strategy_create_dca_always_long")

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.name).toBe("DCATradingMode")
    expect(tradingConfiguration).not.toHaveProperty("symbols")
    expect(tradingConfiguration).not.toHaveProperty("evaluators")
    expect(tradingConfiguration).not.toHaveProperty("strategies")

    const dcaConfig = tradingConfiguration.config as Record<string, unknown>
    expect(dcaConfig.trigger_mode).toBe("Always trigger long")
    expect(dcaConfig.use_init_entry_orders).toBe(true)
    expect(dcaConfig.trading_pairs).toEqual(["BTC/USDC", "ETH/USDC"])
    expect(dcaConfig.time_frames).toEqual(["1h"])
  })

  it("builds a market making strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_market_making")
    expect(action.id).toBe("ua-manual-strategy_create_market_making")

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDT")

    const marketMakingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(marketMakingConfiguration.configuration_type).toBe("market_making")

    const pairSettings = marketMakingConfiguration.pair_settings as Array<
      Record<string, unknown>
    >
    expect(pairSettings).toHaveLength(1)
    expect(pairSettings[0].trading_pair).toBe("BTC/USDT")
    expect(pairSettings[0].exchange).toBe("binance")
    expect(pairSettings[0].min_spread).toBe(5)
    expect(pairSettings[0].max_spread).toBe(20)
  })

  it("builds a generic process OctoBot strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_generic_process")
    expect(action.id).toBe("ua-manual-strategy_create_generic_process")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")
    expect(strategy.id).toMatch(CANONICAL_UUID_V4_PATTERN)

    const genericProcessConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(genericProcessConfiguration.configuration_type).toBe("generic_process")
    expect(genericProcessConfiguration).not.toHaveProperty("profile_data")
  })
})

describe("buildUserActionTemplateJson", () => {
  it("returns pretty-printed JSON", () => {
    const json = buildUserActionTemplateJson("automation_stop")
    expect(JSON.parse(json).configuration.action_type).toBe("automation_stop")
  })
})

describe("userActionTemplateKeyFromActionType", () => {
  it("returns the action type unchanged", () => {
    expect(userActionTemplateKeyFromActionType("account_edit")).toBe(
      "account_edit",
    )
  })
})

describe("buildAccountEditUserActionJson", () => {
  it("embeds the account configuration", () => {
    const account: Account = {
      id: "acc-1",
      name: "Main",
      is_simulated: true,
      created_at: "2024-01-01T00:00:00.000Z",
    }
    const json = JSON.parse(buildAccountEditUserActionJson(account))
    expect(json.configuration.id).toBe("acc-1")
    expect(json.configuration.configuration).toEqual(account)
  })
})

describe("buildExchangeConfigEditUserActionJson", () => {
  it("embeds the exchange config", () => {
    const config: ExchangeConfig = {
      id: "cfg-1",
      name: "Binance",
      exchange: "binance",
      sandboxed: false,
    }
    const json = JSON.parse(buildExchangeConfigEditUserActionJson(config))
    expect(json.configuration.id).toBe("cfg-1")
  })
})

describe("buildStrategyEditUserActionJson", () => {
  it("embeds the strategy configuration", () => {
    const strategy: Strategy = {
      id: "strat-1",
      version: "1.0.0",
      name: "Alpha",
      reference_market: "USDT",
      configuration: {
        configuration_type: "generic_process",
        profile_data: {},
      },
    } as Strategy
    const json = JSON.parse(buildStrategyEditUserActionJson(strategy))
    expect(json.configuration.id).toBe("strat-1")
  })
})

describe("buildAutomationStopUserActionJson", () => {
  it("targets the automation id", () => {
    const json = JSON.parse(buildAutomationStopUserActionJson("auto-1"))
    expect(json.configuration).toEqual({
      action_type: "automation_stop",
      id: "auto-1",
    })
  })
})

describe("buildAutomationSignalUserActionJson", () => {
  it("includes the selected signal type", () => {
    const json = JSON.parse(
      buildAutomationSignalUserActionJson("auto-1", "actions"),
    )
    expect(json.configuration.signal_type).toBe("actions")
  })
})

describe("buildAutomationCreateUserActionJsonForAccount", () => {
  it("binds the account reference", () => {
    const account: Account = {
      id: "acc-1",
      name: "Main",
      is_simulated: true,
      created_at: "2024-01-01T00:00:00.000Z",
    }
    const json = JSON.parse(
      buildAutomationCreateUserActionJsonForAccount(account),
    )
    expect(json.configuration.configuration.accounts).toEqual([{ id: "acc-1" }])
    expect(json.configuration.configuration.id).toMatch(
      CANONICAL_UUID_V4_PATTERN,
    )
  })
})

describe("buildAutomationCreateUserActionJsonForStrategy", () => {
  it("binds the strategy reference", () => {
    const strategy: Strategy = {
      id: "strat-1",
      version: "2.0.0",
      name: "Grid",
      reference_market: "USDT",
      configuration: {
        configuration_type: "trading_tentacles",
        name: "GridTradingMode",
        config: { pair_settings: [] },
      },
    } as Strategy
    const json = JSON.parse(
      buildAutomationCreateUserActionJsonForStrategy(strategy),
    )
    expect(json.configuration.configuration.strategy).toEqual({
      id: "strat-1",
      version: "2.0.0",
      emit_signals: false,
    })
    expect(json.configuration.configuration.id).toMatch(
      CANONICAL_UUID_V4_PATTERN,
    )
  })
})
